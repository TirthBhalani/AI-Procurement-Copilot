import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from evals.quality import grounded_references
from src.data_access import get_request
from src.solution import analyze_request
from test_rules import risk


class EvaluationTests(unittest.TestCase):
    def baseline(self):
        with patch('src.tools.get_vendor_risk', side_effect=risk):
            return analyze_request(get_request('REQ-1002'), mode='offline')

    def test_grounded_output_resolves_to_records(self):
        self.assertTrue(grounded_references(self.baseline()))

    def test_fake_reference_fails_grounding(self):
        result = self.baseline()
        result.evidence[0].reference = 'software_catalog.csv:SW-FAKE'
        self.assertFalse(grounded_references(result))

    def test_fabricated_budget_fails_grounding(self):
        result = self.baseline()
        for evidence in result.evidence:
            if (evidence.reference or '').startswith('department_budgets.csv:'):
                evidence.finding = 'Available $999,999.00; purchase is affordable.'
        self.assertFalse(grounded_references(result))

    def test_partial_report_retains_failure_and_unattempted_architecture(self):
        from evals.compare import save_reports
        row = dict(case_id='PUB-01', architecture='single', passed=False, latency_ms=12,
                   llm_calls=1, tool_calls=7, failures='Daily provider quota exhausted')
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            summary = save_reports(output, [row], [], mode='live', case_hash='example',
                                   case_count=16, repeats=1, status='blocked_provider_quota')
            self.assertEqual(summary['attempted_runs'], 1)
            self.assertEqual(summary['planned_runs'], 32)
            self.assertEqual(summary['architectures']['staged']['total'], 0)
            self.assertIsNone(summary['architectures']['staged']['mean_latency_ms'])
            self.assertIn(row['failures'], (output/'comparison.csv').read_text())
            self.assertEqual(json.loads((output/'summary.json').read_text())['status'], 'blocked_provider_quota')


if __name__ == '__main__':
    unittest.main()
