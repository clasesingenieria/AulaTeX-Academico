import unittest
from unittest.mock import patch
from scripts.aulatex.itesca_activity_portal import _normalized_link, _same_host_url, _sanitize, inspect_activity, PortalInspectionError


class PortalAdapterTests(unittest.TestCase):
    def test_boundaries_block_other_host_and_embedded_credentials(self):
        for url in ['https://other.example/mod/assign/view.php?id=2910', 'http://cursos3.e-itesca.edu.mx/', 'https://u:p@cursos3.e-itesca.edu.mx/']:
            with self.assertRaises(PortalInspectionError):
                _same_host_url(url)

    def test_links_do_not_export_session_or_mutating_actions(self):
        self.assertEqual(_normalized_link('https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id=2910&sesskey=SECRET&action=editsubmission'), 'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id=2910')
        self.assertIsNone(_normalized_link('https://cursos3.e-itesca.edu.mx/login/logout.php?sesskey=SECRET'))

    def test_identity_and_token_are_removed(self):
        result = _sanitize('Hola Ana Pérez; matrícula: 12345 token=secret', ('Ana Pérez',))
        for forbidden in ('Ana Pérez', '12345', 'secret'):
            self.assertNotIn(forbidden, result)

    def test_adapter_returns_invocation_result(self):
        with patch('scripts.aulatex.itesca_activity_portal._inspect', return_value={'read_only':True}):
            self.assertEqual(inspect_activity('.', '.aulatex-temp/test'), {'read_only':True})


if __name__ == '__main__': unittest.main()
