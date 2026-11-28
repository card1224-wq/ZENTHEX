"""Web navigation continuity and one live weakness exit; never real credentials/orders."""
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch,AsyncMock
from trading import engine

ROOT=Path(__file__).resolve().parents[1]

class WebHouseholdTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for dynamic navigation')
    def test_household_link_survives_authenticated_and_anonymous_nav_render(self):
        source=(ROOT/'static/index.html').read_text()
        function=re.search(r'    function renderNav\(u\)\{.*?\n    \}',source,re.S).group(0)
        code="const assert=require('assert');const navActions={innerHTML:''};function isOwner(u){return u&&u.role==='owner';}\n"+function+"\nfor(const u of [null,{role:'owner'},{role:'user'}]){renderNav(u);assert(navActions.innerHTML.includes('href=\"/household.html\"'));}"
        subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)

class LiveExitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original=engine.bot_state
        engine.bot_state=engine.BotState()
        engine.admin_state.global_kill_switch=False
    def tearDown(self):engine.bot_state=self.original

    async def verify_exit(self, mode, auto_restart, realized):
        b=engine.bot_state;b.trading_mode=mode;b.auto_restart_after_profit=auto_restart
        b.balance=10000;b.held_btc=1;b.entry_cost_krw=100;b.avg_buy_price=100
        calls=0
        def price(*args):
            nonlocal calls
            calls+=1
            if calls>1:
                b.state=engine.TradingState.ERROR
                raise RuntimeError('unexpected second trading iteration')
            b.state=engine.TradingState.HOLDING
            return 99.7
        async def sell(*args):
            b.held_btc=0;b.avg_buy_price=0
            return True,realized
        with patch.object(engine,'get_current_price',side_effect=price),patch.object(engine,'refresh_real_balances',new_callable=AsyncMock),patch.object(engine,'position_momentum_is_weak',return_value=(True,'test')),patch.object(engine,'sell_current_position',side_effect=sell) as close,patch.object(engine,'record_decision'),patch.object(engine.asyncio,'sleep',new_callable=AsyncMock),patch.object(engine,'send_push_notification'):
            await engine.scalping_loop()
        self.assertEqual(close.await_count,1)
        self.assertEqual(b.state,engine.TradingState.STOPPED)
        self.assertEqual(calls,1)

    async def test_live_weak_loss_stops_even_if_profit_restart_was_enabled(self):
        await self.verify_exit('real',True,-.4)
    async def test_live_weak_exit_respects_single_trade_with_restart_disabled(self):
        await self.verify_exit('real',False,-.4)
    async def test_bithumb_live_weak_exit_also_stops(self):
        await self.verify_exit('bithumb_real',False,-.4)
    async def test_live_weak_positive_fill_still_stops_for_review(self):
        await self.verify_exit('real',False,.01)
