import unittest
from unittest.mock import patch

import zenthex_configure_studio as configure


class StudioConfigurationTests(unittest.TestCase):
    def test_both_key_prefixes_are_supported(self):
        for key in ('AQ.' + 'a' * 40, 'AIza' + 'b' * 40):
            self.assertTrue(configure.valid_api_key(key))

    def test_control_characters_and_whitespace_are_rejected(self):
        for code in list(range(33)) + [127, 160, 0x200b]:
            self.assertFalse(configure.valid_api_key('AQ.' + 'a' * 30 + chr(code)))
        self.assertFalse(configure.valid_api_key('AQ.' + 'a' * 30 + '\x1b[200~'))

    def test_env_quoting_and_invalid_lengths_are_rejected(self):
        for key in ('short', 'a' * 4097, 'a' * 30 + '"', 'a' * 30 + "'", 'a' * 30 + '\\'):
            self.assertFalse(configure.valid_api_key(key))

    def test_idle_check_fails_closed_on_missing_flags_and_active_work(self):
        state = {
            'deployment': {'engineState': 'STOPPED', 'engineTaskActive': False,
                           'hasPosition': False, 'studioBusy': False},
            'trading': {'liveEnabled': False, 'recoveryRequired': False},
        }
        with patch.object(configure, 'read_env', return_value={}), \
                patch.object(configure, 'request_json', return_value=(200, state)), \
                patch.object(configure.GUARD.__class__, 'exists', return_value=False):
            configure.check_idle()
            for field in ('engineTaskActive', 'hasPosition', 'studioBusy'):
                state['deployment'][field] = True
                with self.assertRaises(SystemExit):
                    configure.check_idle()
                state['deployment'][field] = False
            del state['trading']['recoveryRequired']
            with self.assertRaises(SystemExit):
                configure.check_idle()


if __name__ == '__main__':
    unittest.main()
