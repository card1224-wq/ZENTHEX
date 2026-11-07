"""Offline regressions: no credentials, exchange calls, or live orders."""
import asyncio
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

_sandbox = tempfile.TemporaryDirectory(prefix="zenthex-tests-")
os.environ["ZENTHEX_DATABASE_URL"] = "sqlite:///" + str(Path(_sandbox.name) / "test.db")
os.environ["ZENTHEX_TRADING_STATE_DIR"] = str(Path(_sandbox.name) / "orders")

from fastapi import HTTPException
from trading import engine, network, orders
from trading import router as routes


def fill(qty=0.1, funds=10000, fee=5, state="done"):
    return {"state": state, "executed_volume": str(qty), "paid_fee": str(fee),
            "trades": [{"volume": str(qty), "funds": str(funds)}]}


class SafetyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        engine.bot_state.__dict__.clear()
        engine.bot_state.__dict__.update(engine.BotState().__dict__)
        engine.admin_state.global_kill_switch = False
        routes.ENGINE_TASK = None
        orders.clear_guard()

    async def test_configuration_alone_does_not_claim_fixed_ip(self):
        with patch.dict(os.environ, {"ZENTHEX_SERVER_PUBLIC_IP": "8.8.8.8"}):
            result = await routes.server_ip()
        self.assertTrue(result["configured"])
        self.assertFalse(result["is_fixed"])

    async def test_ip_requires_three_matching_successes(self):
        with patch.dict(os.environ, {"ZENTHEX_SERVER_PUBLIC_IP": "8.8.8.8"}), patch.object(network, "detect_outbound_ip", side_effect=["8.8.8.8", OSError(), "8.8.8.8"]):
            result = await network.verify_server_ip()
        self.assertFalse(result["matches"])
        self.assertEqual(result["successful_checks"], 2)

    async def test_three_matching_ip_observations(self):
        with patch.dict(os.environ, {"ZENTHEX_SERVER_PUBLIC_IP": "8.8.8.8"}), patch.object(network, "detect_outbound_ip", return_value="8.8.8.8"):
            self.assertTrue((await network.verify_server_ip())["matches"])

    async def test_mismatched_ip_blocks_start_before_state_reset(self):
        engine.bot_state.balance = 12345
        owner = SimpleNamespace(id=1, role="owner", plan="ultimate")
        with patch.dict(os.environ, {"ZENTHEX_ENABLE_LIVE_TRADING": "true"}), patch.object(routes, "require_trading_permission", return_value=owner), patch.object(routes, "verify_server_ip", AsyncMock(return_value={"matches": False, "message": "mismatch"})):
            with self.assertRaises(HTTPException) as error:
                await routes._start_bot(routes.StartConfig(targetYield=1.01, tradingMode="real", realAccepted=True), "Bearer test", None)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(engine.bot_state.balance, 12345)

    async def test_private_or_missing_ip_rejected(self):
        for value in ["", "172.26.14.119", "::1", "not-an-ip"]:
            with patch.dict(os.environ, {"ZENTHEX_SERVER_PUBLIC_IP": value}):
                self.assertEqual(network.configured_server_ip()[0], "")

    async def test_another_subscriber_cannot_control_engine(self):
        engine.bot_state.trading_mode = "real"
        engine.bot_state.owner_user_id = 1
        other = SimpleNamespace(id=2, role="user", plan="trading_pro")
        with patch.object(routes, "get_current_user", return_value=other):
            with self.assertRaises(HTTPException) as error:
                routes.require_real_status_permission("Bearer test", None)
        self.assertEqual(error.exception.status_code, 403)

    async def test_live_state_cannot_be_mutated_by_practice_manual_route(self):
        engine.bot_state.trading_mode = "real"
        engine.bot_state.owner_user_id = 1
        owner = SimpleNamespace(id=1, role="owner", plan="ultimate")
        with patch.object(routes, "get_current_user", return_value=owner):
            with self.assertRaises(HTTPException):
                await routes.manual_trade(routes.ManualTrade(type="sell", amount=1), "Bearer test", None)

    async def test_scan_failure_never_fabricates_btc_entry(self):
        with patch.object(engine.pyupbit, "get_tickers", side_effect=OSError("offline")):
            self.assertEqual(engine.scan_upbit_candidates(), [])

    async def test_wait_for_fill_does_not_treat_acceptance_as_execution(self):
        client = Mock()
        client.get_order.side_effect = [{"state": "wait"}, fill()]
        result = await orders.wait_for_fill(client, "test-order", poll=0)
        self.assertEqual(client.get_order.call_count, 2)
        self.assertEqual(result["quantity"], 0.1)

    async def test_timeout_never_returns_estimated_profit(self):
        client = Mock()
        client.get_order.return_value = {"state": "wait"}
        with self.assertRaises(RuntimeError):
            await orders.wait_for_fill(client, "test-order", timeout=0)

    async def test_incomplete_or_inconsistent_trade_data_rejected(self):
        for data in [{"state": "done", "executed_volume": "1"}, {**fill(), "executed_volume": "2"}, fill(funds=float("nan"))]:
            client = Mock()
            client.get_order.return_value = data
            with self.assertRaises(RuntimeError):
                await orders.wait_for_fill(client, "test-order")

    async def test_buy_tracks_only_this_engine_fill_not_existing_account_coins(self):
        bot = engine.bot_state
        bot.trading_mode = "real"
        bot.state = engine.TradingState.BUYING
        bot.upbit = Mock()
        bot.upbit.buy_market_order.return_value = {"uuid": "new-order"}
        bot.upbit.get_order.return_value = fill()
        bot.upbit.get_balance.return_value = 900000  # unrelated account balances
        bot.held_btc = 0.02
        bot.entry_krw = 2000
        bot.entry_cost_krw = 2001
        await engine.execute_entry_order(10000, 100000, "test")
        self.assertAlmostEqual(bot.held_btc, 0.12)
        self.assertEqual(bot.entry_cost_krw, 12006)
        self.assertTrue(orders.recovery_required())

    async def test_partial_sell_preserves_recovery_guard(self):
        bot = engine.bot_state
        bot.trading_mode = "real"
        bot.held_btc = 0.2
        bot.avg_buy_price = 100000
        bot.entry_cost_krw = 20010
        bot.upbit = Mock()
        bot.upbit.sell_market_order.return_value = {"uuid": "partial"}
        bot.upbit.get_order.return_value = fill(qty=0.1, state="cancel")
        with patch.object(engine, "get_current_price", return_value=100000):
            with self.assertRaises(RuntimeError):
                await engine.sell_current_position("test")
        self.assertAlmostEqual(bot.held_btc, 0.1)
        self.assertTrue(orders.recovery_required())

    async def test_sell_profit_uses_confirmed_funds_and_fees(self):
        bot = engine.bot_state
        bot.trading_mode = "real"
        bot.held_btc = 0.1
        bot.avg_buy_price = 100000
        bot.entry_cost_krw = 10005
        bot.upbit = Mock()
        bot.upbit.sell_market_order.return_value = {"uuid": "sold"}
        bot.upbit.get_order.return_value = fill(funds=11000, fee=5.5)
        bot.upbit.get_balance.return_value = 77777
        with patch.object(engine, "get_current_price", return_value=999999), patch.object(engine, "record_closed_trade") as record:
            ok, pnl = await engine.sell_current_position("test")
        self.assertTrue(ok)
        self.assertAlmostEqual(pnl, ((10994.5 / 10005) - 1) * 100)
        self.assertEqual(record.call_args.args[2], 10994.5)
        self.assertFalse(orders.recovery_required())

    async def test_recovery_guard_blocks_new_engine_even_after_memory_reset(self):
        orders.save_guard("buy_pending", order_uuid="unknown-order")
        with self.assertRaises(HTTPException) as error:
            await routes._start_bot(routes.StartConfig(targetYield=1.01), None, None)
        self.assertEqual(error.exception.status_code, 409)

    async def test_pausing_during_scan_prevents_late_buy(self):
        bot = engine.bot_state
        def scan(*args):
            bot.state = engine.TradingState.STOPPED
            return [{"ticker": "KRW-BTC", "price": 100000, "score": 1, "momentum": 0.1}]
        with patch.object(engine, "get_current_price", return_value=100000), patch.object(engine, "market_regime_allows_entry", return_value=(True, "test")), patch.object(engine, "scan_upbit_candidates", side_effect=scan), patch.object(engine, "execute_entry_order", AsyncMock()) as buy:
            await engine.scalping_loop()
        buy.assert_not_called()
        self.assertEqual(bot.state, engine.TradingState.STOPPED)


if __name__ == "__main__":
    unittest.main()
