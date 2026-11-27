"""Research isolation, cost arithmetic and chronology. Synthetic fixtures are not performance evidence."""
import math
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from research.comparison import compare_strategies, replay_comparison, signal, validate_minutes
from research.router import router


def bars(count=1000):
    return [dict(time=1700000000000+i*60000,open=100.,high=100.,low=100.,close=100.,volume=1.) for i in range(count)]


class ComparisonTests(unittest.TestCase):
    def test_flat_series_does_not_invent_trades_or_winner(self):
        result=compare_strategies(bars(),.0005,.0005,.005)
        self.assertFalse(result['liveEligible'])
        self.assertEqual(len(result['results']),3)
        for row in result['results']:
            self.assertEqual(row['validation']['tradeCount'],0)
            self.assertIsNone(row['validation']['winRatePct'])
            self.assertIsNone(row['validation']['expectancyPct'])
            self.assertFalse(row['liveEligible'])
            self.assertEqual(row['decision'],'연구 기준 미달')

    def test_volume_missing_negative_or_infinite_rejected(self):
        for invalid in (None,-1,math.inf):
            data=bars();data[20]['volume']=invalid if invalid is not None else -1
            with self.assertRaises(ValueError):validate_minutes(data)
        data=bars();del data[20]['volume']
        with self.assertRaises(ValueError):validate_minutes(data)

    def test_gaps_duplicates_and_wrong_interval_rejected(self):
        for change in (0,120000,3600000):
            data=bars();data[4]['time']=data[3]['time']+change
            with self.assertRaises(ValueError):validate_minutes(data)

    def test_cost_and_length_validation(self):
        for cost in (-.001,math.nan,math.inf,.11):
            with self.assertRaises(ValueError):compare_strategies(bars(),cost,0,0)
        with self.assertRaises(ValueError):compare_strategies(bars(499),0,0,0)

    def test_current_execution_bar_cannot_change_signal(self):
        data=bars()
        for i in range(30):
            price=100+i*.1
            data[i].update(open=price,high=price,low=price,close=price,volume=2 if i>=27 else 1)
        self.assertTrue(signal(data,30,'momentum_proxy_v1'))
        data[30].update(open=1,low=1,high=1000,close=1000,volume=100000)
        self.assertTrue(signal(data,30,'momentum_proxy_v1'))
        # Appending future observations cannot affect earlier signals.
        prefix=[signal(data,i,'pullback_cost_v1') for i in range(30,60)]
        data[60:].clear()
        self.assertEqual(prefix,[signal(data,i,'pullback_cost_v1') for i in range(30,60)])

    def test_pullback_requires_impulse_retracement_and_reclaim(self):
        data=bars(500)
        data[26].update(open=100,close=102,high=102,low=100,volume=5)
        data[27].update(open=102,close=101.6,high=102,low=101.5,volume=2)
        data[28].update(open=101.6,close=101.7,high=101.8,low=101.5,volume=2)
        data[29].update(open=101.7,close=102,high=102,low=101.7,volume=4)
        self.assertTrue(signal(data,30,'pullback_cost_v1'))
        data[29]['close']=101.7
        self.assertFalse(signal(data,30,'pullback_cost_v1'))

    def run_one(self, data, start=30, end=31, fee=.001, slip=.002, spread=.004, filtered=False):
        with patch('research.comparison.signal',side_effect=lambda b,i,s:i==start):
            return replay_comparison(data,start,end,'momentum_proxy_v1',fee,slip,spread,filtered)

    def test_next_open_and_costs_both_sides_spread_not_doubled(self):
        data=bars();data[30].update(open=110,low=110,high=110,close=110)
        result=self.run_one(data)
        cost=.001+.002+.004/2
        self.assertAlmostEqual(result['returnPct'],((1-cost)**2-1)*100,places=6)
        self.assertEqual(result['trades'][0]['entryTime'],data[30]['time'])
        self.assertEqual(result['trades'][0]['exitReason'],'period_end')

    def test_stop_first_when_both_intrabar_levels_touched(self):
        data=bars();data[30].update(high=103,low=98)
        result=self.run_one(data,fee=0,slip=0,spread=0)
        self.assertEqual(result['trades'][0]['exitReason'],'stop')
        self.assertAlmostEqual(result['returnPct'],-.6)

    def test_gap_stop_executes_at_open_instead_of_better_stop(self):
        data=bars();data[31].update(open=98,close=98,high=98,low=98)
        result=self.run_one(data,end=32,fee=0,slip=0,spread=0)
        self.assertEqual(result['trades'][0]['exitReason'],'gap_stop')
        self.assertAlmostEqual(result['returnPct'],-2)

    def test_open_exit_does_not_use_later_low_for_drawdown(self):
        data=bars();data[31].update(open=103,close=103,high=103,low=1)
        result=self.run_one(data,end=32,fee=0,slip=0,spread=0)
        self.assertEqual(result['trades'][0]['exitReason'],'gap_target')
        self.assertEqual(result['maxDrawdownPct'],0)

    def test_cost_filter_rejects_same_signal_without_fabricating_pnl(self):
        data=bars()
        filtered=self.run_one(data,spread=.012,filtered=True)
        baseline=self.run_one(data,spread=.012)
        self.assertEqual(filtered['tradeCount'],0)
        self.assertEqual(filtered['costRejected'],1)
        self.assertEqual(filtered['returnPct'],0)
        self.assertLess(baseline['returnPct'],0)

    def test_train_and_validation_do_not_share_positions(self):
        data=bars()
        with patch('research.comparison.signal',return_value=True):
            result=compare_strategies(data,0,0,0)
        for row in result['results']:
            self.assertLess(row['training']['trades'][-1]['exitIndex'],700)
            self.assertGreaterEqual(row['validation']['trades'][0]['entryIndex'],700)

    def test_api_validates_data_and_returns_research_only(self):
        app=FastAPI();app.include_router(router);client=TestClient(app)
        body=dict(feeBps=5,slippageBps=5,spreadBps=50,bars=bars(500))
        r=client.post('/api/research/compare',json=body)
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse(r.json()['liveEligible'])
        for update in ({'market':'binance_futures'},{'feeBps':-1},{'secretKey':'not-allowed'}):
            self.assertEqual(client.post('/api/research/compare',json={**body,**update}).status_code,422)
        body['bars'][-1]['time']=9999999999999
        self.assertEqual(client.post('/api/research/compare',json=body).status_code,422)

    def test_public_candles_are_bounded_sorted_deduplicated_and_complete(self):
        from datetime import datetime, timezone
        from research.market_data import upbit_minutes
        def row(ms):
            return dict(candle_date_time_utc=datetime.fromtimestamp(ms/1000,timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),opening_price=100,high_price=101,low_price=99,trade_price=100,candle_acc_trade_volume=10)
        base=1700000040000
        with patch('research.market_data.time.time',return_value=(base+60000)/1000),patch('research.market_data._request_json',side_effect=[[row(base+60000),row(base),row(base-60000)],[row(base-60000),row(base-120000)],[]]) as call:
            result=upbit_minutes('KRW-BTC')
        self.assertEqual([r['time'] for r in result['bars']],[base-120000,base-60000,base])
        self.assertEqual(call.call_count,3)
        self.assertTrue(all(c.args[0].startswith('https://api.upbit.com/v1/candles/minutes/1?') for c in call.call_args_list))

    def test_public_route_rejects_arbitrary_url_and_hides_upstream_error(self):
        app=FastAPI();app.include_router(router);client=TestClient(app)
        with patch('research.router.upbit_minutes',side_effect=RuntimeError('sensitive upstream response')) as fetch:
            self.assertEqual(client.get('/api/research/upbit-minutes?ticker=https://bad.invalid').status_code,422)
            fetch.assert_not_called()
            r=client.get('/api/research/upbit-minutes?ticker=KRW-BTC')
            self.assertEqual(r.status_code,502)
            self.assertNotIn('sensitive',r.text)

    def test_mobile_comparison_ui(self):
        from pathlib import Path
        import subprocess
        import shutil
        if not shutil.which('node'):self.skipTest('Node unavailable')
        subprocess.run(['node','tests/strategy_comparison_check.cjs'],cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True,text=True)
