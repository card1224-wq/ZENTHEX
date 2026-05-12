from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
import pyupbit
from trading.engine import bot_state, TradingState, scalping_loop, log_trade

router = APIRouter(prefix="/api/finance", tags=["finance"])

class StartConfig(BaseModel):
    accessKey: str = ""
    secretKey: str = ""
    targetYield: float
    investmentMode: str = "fixed"
    investmentAmount: float = 50000.0
    investmentRatio: float = 0.5

class ManualTrade(BaseModel):
    type: str
    amount: float

@router.post("/start")
async def start_bot(config: StartConfig):
    if bot_state.state not in [TradingState.STOPPED, TradingState.ERROR]:
        return {"status": "error", "message": "Bot is already running"}

    bot_state.target_yield = config.targetYield
    bot_state.investment_mode = config.investmentMode
    bot_state.investment_amount = config.investmentAmount
    bot_state.investment_ratio = config.investmentRatio
    bot_state.consecutive_loss_count = 0
    bot_state.held_btc = 0
    bot_state.avg_buy_price = 0
    bot_state.is_real_key = False
    log_trade("[Notice] MVP는 전체 코인 스캐너 + Paper Trading 모드로 시작합니다. 실거래는 별도 검증 후 활성화하세요.")
    asyncio.create_task(scalping_loop())
    return {"status": "success", "message": "Signal Guard Paper Trading Started"}

@router.post("/manual_trade")
async def manual_trade(trade: ManualTrade):
    current_price = pyupbit.get_current_price(bot_state.active_ticker) or 80000000
    if trade.type == "buy" and bot_state.balance >= trade.amount:
        bot_state.held_btc += (trade.amount / current_price) * 0.9995
        bot_state.avg_buy_price = current_price
        bot_state.balance -= trade.amount
        log_trade(f"[Manual Buy] {bot_state.active_ticker} {trade.amount:,.0f}원 진입")
    elif trade.type == "sell" and bot_state.held_btc > 0:
        sell_amount = (bot_state.held_btc * current_price) * 0.9995
        bot_state.balance += sell_amount
        bot_state.held_btc = 0
        bot_state.avg_buy_price = 0
        log_trade(f"[Manual Sell] {bot_state.active_ticker} 전량 매도")
    else:
        log_trade("[Manual Trade] 주문 조건이 맞지 않습니다.")
    return {"status": "success"}

@router.post("/stop")
async def stop_bot():
    bot_state.state = TradingState.STOPPED
    log_trade("[User Stop] 사용자 요청으로 엔진을 중지합니다.")
    return {"status": "success", "message": "Bot Engine Stopped"}

@router.get("/status")
async def status():
    current_price = pyupbit.get_current_price(bot_state.active_ticker) or 80000000
    est_balance = bot_state.balance + (bot_state.held_btc * current_price if bot_state.held_btc > 0 else 0)
    return {
        "isRunning": bot_state.state not in [TradingState.STOPPED, TradingState.ERROR],
        "state": bot_state.state,
        "isRealKey": bot_state.is_real_key,
        "activeTicker": bot_state.active_ticker,
        "signalCandidates": bot_state.signal_candidates,
        "currentBtcPrice": current_price,
        "currentPrice": current_price,
        "balance": bot_state.balance,
        "estBalance": est_balance,
        "heldBtc": bot_state.held_btc,
        "avgBuyPrice": bot_state.avg_buy_price,
        "logs": bot_state.logs[-20:],
    }
