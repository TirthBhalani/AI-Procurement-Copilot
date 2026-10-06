import unittest
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


if __name__ == '__main__':
    unittest.main()
