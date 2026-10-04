import unittest
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest
from test_rules import risk

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class UITests(unittest.TestCase):
    def test_sample_review_and_state_invalidation(self):
        with patch('src.tools.get_vendor_risk', side_effect=risk):
            app = AppTest.from_file(APP).run(timeout=20)
            self.assertFalse(app.exception)
            app.sidebar.selectbox[1].select('offline').run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['decision']['request_id'], 'REQ-1001')
            self.assertEqual(app.session_state['decision']['execution_mode'], 'rules_only')
            app.sidebar.selectbox[0].select('REQ-1005').run()
            self.assertNotIn('decision', app.session_state)

    def test_custom_request_form_is_available(self):
        app = AppTest.from_file(APP).run(timeout=20)
        app.sidebar.radio[0].set_value('Custom request').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(t.label == 'Annual cost (USD)' for t in app.text_input))


if __name__ == '__main__':
    unittest.main()
