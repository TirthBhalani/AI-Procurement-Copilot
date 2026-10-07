from __future__ import annotations

import os
import unittest
from unittest.mock import patch, Mock

from src.agents import Advisory, ModelUnavailable, infer
from src.data_access import get_request
from src.solution import analyze_request
from src.telemetry import RunTelemetryCounter
from test_rules import risk


def advisory(**changes):
    payload = dict(use_case_summary='Review training support for Finance.',
                   overlap_assessment='no_obvious_overlap', alternative_ids=[],
                   evidence_indices=[0, 1], additional_reviews=[],
                   questions_for_human=['Confirm the training scope.'])
    payload.update(changes)
    return Advisory(**payload)


class AgentTests(unittest.TestCase):
    def execute(self, arch='single', output=None, mode='live'):
        def stub(payload, role, telemetry):
            telemetry.record_llm_call()
            return output or advisory()
        with patch('src.tools.get_vendor_risk', side_effect=risk), patch('src.agents.infer', side_effect=stub):
            return analyze_request(get_request('REQ-1010'), arch, mode=mode)

    def test_single_stage_calls_one_model(self):
        result = self.execute()
        self.assertEqual(result.telemetry.llm_calls, 1)
        self.assertEqual(result.execution_mode, 'live_model')

    def test_staged_has_actual_analyst_handoff(self):
        seen = []
        def stub(payload, role, telemetry):
            seen.append(dict(payload))
            telemetry.record_llm_call()
            return advisory()
        with patch('src.tools.get_vendor_risk', side_effect=risk), patch('src.agents.infer', side_effect=stub):
            result = analyze_request(get_request('REQ-1010'), 'staged', mode='live')
        self.assertEqual(result.telemetry.llm_calls, 2)
        self.assertNotIn('analyst_handoff', seen[0])
        self.assertIn('analyst_handoff', seen[1])
        self.assertEqual([t['stage'] for t in result.trace[-2:]], ['analyst', 'reviewer'])

    def test_model_cannot_remove_manager(self):
        result = self.execute(output=advisory(additional_reviews=['Security']))
        self.assertIn('Manager', result.required_approvals)
        self.assertIn('Security', result.required_approvals)
        self.assertTrue(result.human_review_required)

    def test_rejects_unknown_catalog_alternative(self):
        with self.assertRaises(ModelUnavailable):
            self.execute(output=advisory(alternative_ids=['SW-FAKE']))

    def test_rejects_invalid_evidence_index(self):
        with self.assertRaises(ModelUnavailable):
            self.execute(output=advisory(evidence_indices=[99999]))

    def test_rejects_uncited_interpretation(self):
        with self.assertRaises(ModelUnavailable):
            self.execute(output=advisory(evidence_indices=[]))

    def test_auto_failure_is_visible_and_safe(self):
        with patch('src.tools.get_vendor_risk', side_effect=risk), patch('src.agents.infer', side_effect=ModelUnavailable('Unavailable')):
            result = analyze_request(get_request('REQ-1005'), mode='auto')
        self.assertEqual(result.execution_mode, 'rules_only')
        self.assertIn('model_unavailable', result.risk_flags)
        self.assertIn('budget_insufficient', result.risk_flags)
        self.assertTrue(result.warnings)

    def test_live_failure_is_not_counted_as_agent_success(self):
        with patch('src.tools.get_vendor_risk', side_effect=risk), patch('src.agents.infer', side_effect=ModelUnavailable('Unavailable')):
            with self.assertRaises(ModelUnavailable):
                analyze_request(get_request('REQ-1010'), mode='live')

    def test_provider_exception_does_not_expose_secret(self):
        import requests
        with patch.dict(os.environ, {'MODEL_PROVIDER':'groq', 'GROQ_API_KEY':'test-secret'}), patch('src.agents.requests.post', side_effect=requests.ConnectionError('test-secret')):
            with self.assertRaises(ModelUnavailable) as caught:
                infer({}, 'test', RunTelemetryCounter())
        self.assertNotIn('test-secret', str(caught.exception))

    def test_truncated_provider_output_is_rejected(self):
        response = Mock()
        response.json.return_value = {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}
        with patch.dict(os.environ, {'MODEL_PROVIDER':'groq', 'GROQ_API_KEY':'test-secret'}), patch('src.agents.requests.post', return_value=response):
            with self.assertRaises(ModelUnavailable):
                infer({}, 'test', RunTelemetryCounter())

    def test_rate_limit_retry_counts_each_http_attempt(self):
        limited = Mock(status_code=429, headers={'retry-after':'1'})
        success = Mock(status_code=200)
        success.json.return_value = {'choices':[{'finish_reason':'stop', 'message':{'content':advisory().model_dump_json()}}]}
        telemetry = RunTelemetryCounter()
        with patch.dict(os.environ, {'MODEL_PROVIDER':'groq', 'GROQ_API_KEY':'test-secret'}), patch('src.agents.requests.post', side_effect=[limited, success]), patch('src.agents.time.sleep') as pause:
            infer({}, 'test', telemetry)
        self.assertEqual(telemetry.llm_calls, 2)
        pause.assert_called_once()

    def test_schema_generation_retry_is_bounded(self):
        import requests
        response = Mock(status_code=400)
        response.json.return_value = {'error': {'code':'json_validate_failed'}}
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        telemetry = RunTelemetryCounter()
        with patch.dict(os.environ, {'MODEL_PROVIDER':'groq', 'GROQ_API_KEY':'test-secret'}), patch('src.agents.requests.post', return_value=response):
            with self.assertRaises(ModelUnavailable):
                infer({}, 'test', telemetry)
        self.assertEqual(telemetry.llm_calls, 3)

    def test_model_cannot_invent_cfo_approval(self):
        with self.assertRaises(ModelUnavailable):
            self.execute(output=advisory(additional_reviews=['CFO']))

    def test_non_json_evidence_fails_before_provider_call(self):
        with patch.dict(os.environ, {'MODEL_PROVIDER':'groq', 'GROQ_API_KEY':'test-secret'}), patch('src.agents.requests.post') as post:
            with self.assertRaises(ModelUnavailable):
                infer({'bad': float('nan')}, 'test', RunTelemetryCounter())
            post.assert_not_called()

    def test_unverified_capacity_claim_is_rejected(self):
        with self.assertRaisesRegex(ModelUnavailable, 'spare capacity'):
            self.execute(output=advisory(use_case_summary='Existing software has spare capacity for this purchase.'))

    def test_capacity_question_is_allowed(self):
        result = self.execute(output=advisory(questions_for_human=['Is there verified spare capacity?']))
        self.assertEqual(result.execution_mode, 'live_model')

    def test_missing_integrations_cannot_become_none(self):
        from src.agents import validate_advisory
        from src.tools import gather
        from src.rules import apply_rules
        request = dict(get_request('REQ-1010'))
        request['requested_integrations'] = None
        with patch('src.tools.get_vendor_risk', side_effect=risk):
            pack = gather(request, RunTelemetryCounter())
        with self.assertRaisesRegex(ModelUnavailable, 'integrations'):
            validate_advisory(advisory(use_case_summary='Training with no required integrations.'), pack, apply_rules(pack))

    def test_rounded_shortfall_is_rejected(self):
        from src.agents import validate_advisory
        from src.tools import gather
        from src.rules import apply_rules
        request = dict(get_request('REQ-1010'))
        request.update(requester_id='E001', annual_cost_usd=25000.01)
        with patch('src.tools.get_vendor_risk', side_effect=risk):
            pack = gather(request, RunTelemetryCounter())
        with self.assertRaisesRegex(ModelUnavailable, 'shortfall'):
            validate_advisory(advisory(questions_for_human=['Is a $10,000 shortfall approved?']), pack, apply_rules(pack))


if __name__ == '__main__':
    unittest.main()
