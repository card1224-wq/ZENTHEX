"""Numerical and integration regressions; no real credentials or orders."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from research.backtest import run_research, replay
from stock import toss_client
from stock.router import toss_account_summary


def series(drift=0., count=1000):
    rows=[]
    price=100.
    for i in range(count):
        new=price*(1+drift)
        rows.append(dict(time=1_700_000_000_000+i*3_600_000, open=price, high=max(price,new)*1.001, low=min(price,new)*.999, close=new))
        price=new
    return rows

class ResearchTests(unittest.TestCase):
    def test_flat_data_does_not_fabricate_profit_or_trades(self):
        r=run_research(series(), 'upbit', .0005,.0005)
        self.assertEqual(r['validation']['tradeCount'],0)
        self.assertEqual(r['validation']['returnPct'],0)
        self.assertFalse(r['liveEligible'])
        self.assertEqual(r['decision'],'연구 기준 미달')

    def test_short_only_in_futures_research(self):
        data=series(-.001)
        self.assertEqual(run_research(data,'upbit',.0005,.0005)['validation']['tradeCount'],0)
        r=run_research(data,'binance_futures',.0005,.0005)
        self.assertGreater(r['validation']['returnPct'],0)
        self.assertEqual(r['validation']['trades'][0]['side'],'short')
        self.assertFalse(r['liveEligible'])

    def test_next_open_price_and_both_costs(self):
        data=series(.001)
        # Exactly one validation bar: signal uses prior bars, entry=open, exit=close.
        r=replay(data, 700,701,.001,.001)
        expected=((1-.002)*(1.001-.002*1.001)-1)*100
        self.assertAlmostEqual(r['returnPct'],expected,places=4)

    def test_current_bar_cannot_change_entry_direction(self):
        data=series(.001)
        data[700]['close']=90.;data[700]['low']=89.
        r=replay(data,700,701,0,0,True)
        self.assertEqual(r['trades'][0]['side'],'long')
        self.assertLess(r['returnPct'],0)

    def test_more_costs_reduce_unlevered_trend_result(self):
        r=run_research(series(.001),'stock',.001,.001)
        self.assertLess(r['doubleCostValidation']['returnPct'],r['validation']['returnPct'])
        self.assertFalse(r['checks']['atLeast50ValidationTrades'])

    def test_drawdown_uses_adverse_extreme(self):
        data=series(.001);data[700]['low']=data[700]['open']*.8
        r=replay(data,700,701,0,0)
        self.assertGreaterEqual(r['maxDrawdownPct'],20-1e-8)

    def test_invalid_or_duplicated_bars_rejected(self):
        data=series();data[500]['time']=data[499]['time']
        with self.assertRaises(ValueError):run_research(data,'upbit',0,0)
        data=series();data[50]['high']=1
        with self.assertRaises(ValueError):run_research(data,'stock',0,0)

    def test_short_extreme_capital_exhaustion_is_not_hidden(self):
        data=series(-.001);data[700]['high']=data[700]['open']*3
        with self.assertRaises(ValueError):replay(data,700,701,0,0,True)

class TossTests(unittest.IsolatedAsyncioTestCase):
    async def test_other_user_cannot_read_owner_account(self):
        with patch('stock.router.require_current_user', return_value=SimpleNamespace(role='user')), patch.object(toss_client,'account_summary') as read:
            with self.assertRaises(HTTPException) as ctx:await toss_account_summary('Bearer test',None)
            self.assertEqual(ctx.exception.status_code,403);read.assert_not_called()

    async def test_token_cached_and_only_account_and_holdings_read(self):
        toss_client._cached=None
        accounts=[{'accountSeq':7,'accountNo':'12345678901','accountType':'BROKERAGE'}]
        with patch.dict(os.environ,{'ZENTHEX_TOSS_CLIENT_ID':'test-id','ZENTHEX_TOSS_CLIENT_SECRET':'test-secret','ZENTHEX_TOSS_ACCOUNT_SEQ':'7'}), patch.object(toss_client,'_request',side_effect=[{'access_token':'mock','expires_in':86400},{'result':accounts},{'result':{'items':[]}},{'result':accounts},{'result':{'items':[]}}]) as request:
            a=toss_client.account_summary();toss_client.account_summary()
            paths=[c.args[0] for c in request.call_args_list]
            self.assertEqual(paths.count('/oauth2/token'),1)
            self.assertEqual(set(paths),{'/oauth2/token','/api/v1/accounts','/api/v1/holdings'})
            self.assertFalse(a['ordersEnabled']);self.assertNotIn('12345678901',str(a))
            self.assertEqual(request.call_args_list[2].args[1]['X-Tossinvest-Account'],'7')
        toss_client._cached=None

    async def test_does_not_choose_a_random_account(self):
        accounts=[{'accountSeq':7,'accountNo':'12345678901'}]
        with patch.dict(os.environ,{'ZENTHEX_TOSS_ACCOUNT_SEQ':''}),patch.object(toss_client,'_token',return_value='mock'),patch.object(toss_client,'_request',return_value={'result':accounts}) as request:
            result=toss_client.account_summary();self.assertIsNone(result['holdings']);self.assertEqual(request.call_count,1)
