from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
import asyncio
import pyupbit

from auth.router import get_current_user
from database.session import get_db
from trading.engine import bot_state, TradingState, scalping_loop, log_trade

router = APIRouter(prefix="/api/finance", tags=["finance"])

class StartConfig(BaseModel):
    accessKey: str = ""
    secretKey: str = ""
    targetYield: float
    investmentMode: str = "all_krw"
    investmentAmount: float = 50000.0
    investmentRatio: float = 0.5
    tickerMode: str = "auto"
    selectedTicker: str = "KRW-BTC"
    tradingMode: str = "practice"
    realAccepted: bool = False

class ManualTrade(BaseModel):
    type: str
    amount: float

def user_can_real_trade(user) -> bool:
    return user.role in ["owner", "admin"] or user.plan in ["trading_pro", "ultimate"]

@router.post("/start")
async def start_bot(config: StartConfig, Authorization: str = Header(None), db: Session = Depends(get_db)):
    if bot_state.state not in [TradingState.STOPPED, TradingState.ERROR]:
        return {"status": "error", "message": "Bot is already running"}

    bot_state.target_yield = config.targetYield
    bot_state.investment_mode = config.investmentMode if config.investmentMode in ["all_krw", "fixed", "ratio"] else "all_krw"
    bot_state.investment_amount = config.investmentAmount
    bot_state.investment_ratio = config.investmentRatio
    bot_state.ticker_mode = config.tickerMode if config.tickerMode in ["auto", "manual"] else "auto"
    bot_state.selected_ticker = config.selectedTicker if config.selectedTicker.startswith("KRW-") else "KRW-BTC"
    bot_state.trading_mode = config.tradingMode if config.tradingMode in ["practice", "real"] else "practice"
    bot_state.consecutive_loss_count = 0
    bot_state.held_btc = 0
    bot_state.avg_buy_price = 0
    bot_state.upbit = None
    bot_state.is_real_key = False

    if bot_state.trading_mode == "real":
        if not Authorization:
            return {"status": "error", "message": "실거래는 로그인 후 Trading Pro 또는 Ultimate 구독이 필요합니다."}
        user = get_current_user(Authorization.replace("Bearer ", ""), db)
        if not user_can_real_trade(user):
            return {"status": "error", "message": "실거래는 Trading Pro 또는 Ultimate 구독 후 사용할 수 있습니다."}
        if not config.realAccepted:
            return {"status": "error", "message": "실거래 위험 확인 체크가 필요합니다."}
        if not config.accessKey or not config.secretKey:
            return {"status": "error", "message": "업비트 Access Key와 Secret Key가 필요합니다."}
        try:
            bot_state.upbit = pyupbit.Upbit(config.accessKey, config.secretKey)
            real_krw = bot_state.upbit.get_balance("KRW")
            if real_krw is None:
                return {"status": "error", "message": "API 키 확인에 실패했습니다. 조회/주문 권한과 허용 IP를 확인하세요."}
            bot_state.balance = float(real_krw or 0)
            bot_state.is_real_key = True
            log_trade("[Real Mode] 업비트 실거래 모드가 활성화되었습니다. 출금 권한 없는 API 키만 사용하세요.")
        except Exception as e:
            bot_state.trading_mode = "practice"
            bot_state.is_real_key = False
            return {"status": "error", "message": f"API 키 인증 실패: {e}"}
    else:
        bot_state.balance = max(bot_state.balance, 1000000.0)
        log_trade("[Practice Mode] 전략 체험 모드로 시작합니다.")

    asyncio.create_task(scalping_loop())
    return {"status": "success", "message": "Signal Guard Started", "tradingMode": bot_state.trading_mode}

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
        "tradingMode": bot_state.trading_mode,
        "activeTicker": bot_state.active_ticker,
        "tickerMode": bot_state.ticker_mode,
        "selectedTicker": bot_state.selected_ticker,
        "signalCandidates": bot_state.signal_candidates,
        "currentBtcPrice": current_price,
        "currentPrice": current_price,
        "balance": bot_state.balance,
        "estBalance": est_balance,
        "heldBtc": bot_state.held_btc,
        "avgBuyPrice": bot_state.avg_buy_price,
        "logs": bot_state.logs[-20:],
    }
