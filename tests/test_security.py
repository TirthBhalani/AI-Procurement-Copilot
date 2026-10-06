import json
import os
import unittest
from unittest.mock import patch

from src.security import scrub
from src.solution import analyze_request
from src.data_access import get_request
from test_rules import risk


class SecretTests(unittest.TestCase):
    def test_nested_token_redaction(self):
        secret = 'gsk_' + 'x' * 30
        result = scrub({'notes': ['Do not forward ' + secret]})
        self.assertNotIn(secret, json.dumps(result))
        self.assertIn('[REDACTED]', json.dumps(result))
        self.assertNotIn(secret, json.dumps(scrub({secret: 'accidental key name'})))

    def test_exact_configured_key_is_redacted(self):
        with patch.dict(os.environ, {'GROQ_API_KEY':'synthetic-configured-value'}):
            self.assertEqual(scrub('synthetic-configured-value'), '[REDACTED]')

    def test_request_and_vendor_notes_do_not_leak_into_trace(self):
        secret = 'gsk_' + 'y' * 30
        req = dict(get_request('REQ-1010'))
        req['business_justification'] = 'Training. Accidental token: ' + secret
        def vendor(name):
            record = risk(name)
            record['notes'] = 'Accidental vendor token: ' + secret
            return record
        with patch('src.tools.get_vendor_risk', side_effect=vendor):
            result = analyze_request(req, mode='offline')
        self.assertNotIn(secret, result.model_dump_json())
        self.assertIn('secret_redacted', result.risk_flags)


if __name__ == '__main__':
    unittest.main()
