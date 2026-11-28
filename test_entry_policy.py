"""Execution guards and post-fill timing; synthetic data, no real orders."""
from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import patch,Mock,AsyncMock
import pandas as pd
from trading import engine
from trading.entry_policy import completed_frame,entry_depth_cost,KST


def book(ask=100.05,bid=100.,size=10000):
    return [dict(ask_price=ask+i*.01,bid_price=bid-i*.01,ask_size=size,bid_size=size) for i in range(3)]


def frame(count=8):
    index=pd.date_range('2026-11-27 09:00',periods=count,freq='min')
    return pd.DataFrame(dict(open=[100.]*count,high=[101.]*count,low=[98.]*count,
                             close=[100.]*count,volume=[10.]*count),index=index)


class PolicyTests(unittest.TestCase):
    def test_both_fees_and_reserve_included(self):
        r=entry_depth_cost(book(),10000,.0005,.006)
        expected=1-(10000/100.05*100*(1-.0005))/(10000*(1+.0005))
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['roundtrip_cost_pct'],expected*100)
        self.assertEqual(r['cost_reserve_pct'],.1)
        self.assertAlmostEqual(r['entry_cost_budget_pct'],.3)

    def test_observed_wide_spreads_blocked(self):
        for spread in (.0021,.0045,.005,.0057):
            r=entry_depth_cost(book(ask=100*(1+spread)),10000,.0005,.006)
            self.assertFalse(r['passed']);self.assertEqual(r['code'],'spread')

    def test_full_depth_cost_blocks_even_if_top_spread_is_small(self):
        units=book();units[0]['ask_size']=1;units[1]['ask_price']=101.;units[2]['ask_price']=102.
        r=entry_depth_cost(units,10000,.0005,.006)
        self.assertFalse(r['passed']);self.assertEqual(r['code'],'roundtrip_cost')

    def test_inadequate_bid_or_ask_depth_blocks(self):
        for side in ('ask_size','bid_size'):
            units=book()
            for r in units:r[side]=.01
            # Keep the depth-ratio check from hiding insufficient total asks.
            if side=='ask_size':
                for r in units:r['bid_size']=100
            r=entry_depth_cost(units,10000,0,.006)
            self.assertFalse(r['passed']);self.assertIn(r['code'],('ask_liquidity','bid_liquidity','bid_depth'))

    def test_smaller_stop_budget_tightens_cost_guard(self):
        r=entry_depth_cost(book(),10000,.0005,.002)
        self.assertFalse(r['passed']);self.assertEqual(r['code'],'roundtrip_cost')

    def test_malformed_crossed_unsorted_and_nan_depth_blocked(self):
        cases=[book(ask=99),book(ask=float('nan')),book(size=-1)]
        bad=book();bad[1]['bid_price']=101;cases.append(bad)
        bad=book();bad[1]['ask_price']=100.01;cases.append(bad)
        bad=book();del bad[0]['ask_size'];cases.append(bad)
        for units in cases:self.assertFalse(entry_depth_cost(units,10000,.0005,.006)['passed'])

    def test_invalid_amount_fee_and_stop_blocked(self):
        for amount,fee,stop in [(4999,.0005,.006),(float('nan'),.0005,.006),(10000,-1,.006),(10000,.0005,0)]:
            self.assertFalse(entry_depth_cost(book(),amount,fee,stop)['passed'])

    def test_forming_candle_is_removed_with_kst_naive_index(self):
        data=frame();data.iloc[-1,data.columns.get_loc('close')]=1e9
        result=completed_frame(data,1,datetime(2026,11,27,9,7,30,tzinfo=KST))
        self.assertEqual(len(result),7);self.assertEqual(result['close'].iloc[-1],100)

    def test_utc_index_and_kst_index_select_same_completed_rows(self):
        data=frame();aware=data.copy();aware.index=aware.index.tz_localize('Asia/Seoul').tz_convert('UTC')
        now=datetime(2026,11,27,9,7,30,tzinfo=KST)
        self.assertEqual(len(completed_frame(data,1,now)),len(completed_frame(aware,1,now)))

    def test_stale_gap_bad_prices_and_duplicate_times_rejected(self):
        now=datetime(2026,11,27,9,8,30,tzinfo=KST)
        bad=frame().iloc[:-2]
        with self.assertRaises(ValueError):completed_frame(bad,1,now)
        bad=frame().drop(frame().index[3])
        with self.assertRaises(ValueError):completed_frame(bad,1,now)
        bad=frame();bad.iloc[2,bad.columns.get_loc('high')]=1
        with self.assertRaises(ValueError):completed_frame(bad,1,now)
        bad=frame();bad.index=list(bad.index[:2])+[bad.index[1]]+list(bad.index[3:])
        with self.assertRaises(ValueError):completed_frame(bad,1,now)


class ExecutionPolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.old=engine.bot_state
        engine.bot_state=engine.BotState()
        engine.admin_state.global_kill_switch=False
        self.record=patch.object(engine,'record_decision',return_value=True);self.record.start()
    def tearDown(self):
        self.record.stop();engine.bot_state=self.old

    async def test_rejected_cost_never_submits_order_or_creates_guard(self):
        b=engine.bot_state;b.trading_mode='real';b.state=engine.TradingState.BUYING;b.upbit=Mock()
        with patch.object(engine.pyupbit,'get_orderbook',return_value={'orderbook_units':book(ask=100.5)}),patch.object(engine,'save_guard') as guard:
            self.assertFalse(await engine.execute_entry_order(10000,100,'test'))
        b.upbit.buy_market_order.assert_not_called();guard.assert_not_called()
        self.assertIn('spread',b.decision_note)

    async def test_pause_during_cost_lookup_blocks_late_buy(self):
        b=engine.bot_state;b.trading_mode='real';b.state=engine.TradingState.BUYING;b.upbit=Mock()
        def cost(*args):b.state=engine.TradingState.STOPPED;return True,'passed'
        with patch.object(engine,'orderbook_allows_entry',side_effect=cost),patch.object(engine,'save_guard') as guard:
            self.assertFalse(await engine.execute_entry_order(10000,100,'test'))
        b.upbit.buy_market_order.assert_not_called();guard.assert_not_called()

    async def test_weakness_does_not_use_pre_entry_candles(self):
        b=engine.bot_state;data=frame(6);data['close']=[100,99.9,99.8,99.7,99.6,99.5]
        b.entry_confirmed_at=datetime(2026,11,27,9,2,1,tzinfo=KST)
        with patch.object(engine.pyupbit,'get_ohlcv',return_value=data),patch.object(engine,'completed_frame',return_value=data):
            weak,_=engine.position_momentum_is_weak('KRW-BTC');self.assertFalse(weak)
            b.entry_confirmed_at=datetime(2026,11,27,9,1,tzinfo=KST)
            weak,_=engine.position_momentum_is_weak('KRW-BTC');self.assertTrue(weak)

    async def test_hard_stop_precedes_weakness_and_practice_rotation(self):
        b=engine.bot_state;b.balance=10000;b.max_consecutive_loss=1;b.held_btc=1;b.entry_cost_krw=100;b.avg_buy_price=100
        def price(*args):b.state=engine.TradingState.HOLDING;return 98.
        async def sell(*args):b.state=engine.TradingState.STOPPED;return True,-2.
        with patch.object(engine,'get_current_price',side_effect=price),patch.object(engine,'sell_current_position',side_effect=sell) as close,patch.object(engine,'position_momentum_is_weak') as weak,patch.object(engine,'scan_upbit_candidates') as scan,patch.object(engine.asyncio,'sleep',new_callable=AsyncMock),patch.object(engine,'send_push_notification'):
            await engine.scalping_loop()
        weak.assert_not_called();scan.assert_not_called();self.assertIn('STOP LOSS',close.call_args.args)

    async def test_manual_entry_rejects_already_weak_completed_candles(self):
        data=frame(6);data['close']=[100,100,100,100,99.9,99.8]
        with patch.object(engine,'get_current_price',return_value=100),patch.object(engine.pyupbit,'get_ohlcv',return_value=data),patch.object(engine,'completed_frame',return_value=data),patch.object(engine,'orderbook_allows_entry') as cost:
            ok,_=await engine.confirm_entry_signal('KRW-BTC',100)
        self.assertFalse(ok);cost.assert_not_called()
