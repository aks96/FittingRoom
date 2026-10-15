"""Offline tests for safe setup failures, not live endpoint verification."""
import ssl
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from local_ai.setup_tls import check_trust


class SetupTrustTests(unittest.TestCase):
    def test_empty_trust_stops_with_official_helper_instructions(self):
        context = Mock()
        context.get_ca_certs.return_value = []
        with patch('local_ai.setup_tls.ssl.create_default_context', return_value=context):
            with self.assertRaisesRegex(RuntimeError, 'Install Certificates.command'):
                check_trust()

    def test_valid_trust_keeps_certificate_verification_enabled(self):
        context = ssl.create_default_context()
        with patch.object(context, 'get_ca_certs', return_value=[{'subject': 'test CA'}]):
            with patch('local_ai.setup_tls.ssl.create_default_context', return_value=context):
                self.assertEqual(check_trust(), 1)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_invalid_custom_configuration_fails_without_fallback(self):
        with patch('local_ai.setup_tls.ssl.create_default_context', side_effect=OSError('bad CA file')):
            with self.assertRaisesRegex(RuntimeError, 'verification remains enabled'):
                check_trust()

    def test_setup_checks_trust_before_first_download(self):
        root = Path(__file__).resolve().parents[1]
        setup = (root/'scripts/setup-ai.sh').read_text()
        self.assertLess(setup.index('local_ai/setup_tls.py'), setup.index('local_ai/source_integrity.py'))
        self.assertIn("'local_ai/setup_tls.py'", (root/'scripts/package-companion.mjs').read_text())


if __name__ == '__main__':
    unittest.main()
