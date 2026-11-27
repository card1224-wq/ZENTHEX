import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from trading import diagnostics
from zenthex_trade_report import summarize


class TradeDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'ZENTHEX_TRADING_STATE_DIR': self.temp.name})
        self.env.start()
        self.path = Path(self.temp.name) / 'decisions.jsonl'

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_credentials_and_raw_responses_are_not_recorded(self):
        diagnostics.record_decision('entry_check', ticker='KRW-MBL', mode='real',
                                    api_key='sensitive-test-value', response={'secret': 'secret'}, passed=False, code='spread')
        value = self.path.read_text()
        self.assertNotIn('sensitive-test-value', value)
        self.assertNotIn('secret', value)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_rotation_is_bounded_and_preserves_current_record(self):
        with patch.object(diagnostics, 'MAX_BYTES', 1):
            for number in range(7):
                self.assertTrue(diagnostics.record_decision('signal', mode='real', score=number))
        self.assertEqual(len(list(Path(self.temp.name).iterdir())), 4)
        self.assertEqual(json.loads(self.path.read_text())['score'], 6)

    def test_storage_failure_does_not_interrupt_trading(self):
        with patch.object(diagnostics.os, 'open', side_effect=OSError('disk unavailable')):
            self.assertFalse(diagnostics.record_decision('entry_fill', mode='real'))

    def test_nonfinite_values_are_not_encoded(self):
        diagnostics.record_decision('signal', mode='real', score=float('nan'))
        self.assertNotIn('score', json.loads(self.path.read_text()))

    def test_report_separates_modes_and_exit_reasons(self):
        diagnostics.record_decision('exit_fill', mode='real', pnl_krw=-98, exit_tag='WEAK EXIT')
        diagnostics.record_decision('exit_fill', mode='practice', pnl_krw=900, exit_tag='TAKE PROFIT')
        report = summarize(self.path)
        self.assertEqual(report['closed_trades'], 1)
        self.assertEqual(report['pnl_krw'], -98)
        self.assertEqual(report['by_exit_tag']['WEAK EXIT']['count'], 1)
        self.assertEqual(summarize(self.path, mode='all')['closed_trades'], 2)

    def test_partial_record_does_not_destroy_report(self):
        diagnostics.record_decision('entry_check', mode='real', passed=False, code='spread')
        with self.path.open('a') as out:
            out.write('{"partial":\n')
        report = summarize(self.path)
        self.assertEqual(report['malformed_lines'], 1)
        self.assertEqual(report['entry_check_reasons']['spread'], 1)
