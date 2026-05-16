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

class UpbitKeyCheck(BaseModel):
    accessKey: str = ""
    secretKey: str = ""

def clean_api_key(value: str) -> str:
    return (value or "").strip().replace("\u200b", "").replace("\ufeff", "")

def user_can_real_trade(user) -> bool:
    return user.role == "owner" or user.plan in ["trading_pro", "ultimate"]

def explain_upbit_auth_error(raw_error) -> str:
    text = str(raw_error or "")
    lowered = text.lower()
    if "out_of_scope" in lowered or "permission" in lowered:
        return "API 키 권한이 부족합니다. 업비트 Open API에서 자산조회와 주문하기 권한을 켜야 합니다."
    if "invalid_access_key" in lowered or "no_authorization" in lowered:
        return "Access Key가 맞지 않거나 만료된 키입니다. 업비트에서 새 키를 발급해 다시 입력하세요."
    if "jwt" in lowered or "signature" in lowered or "secret" in lowered:
        return "Secret Key가 맞지 않거나 복사 중 공백/누락이 있습니다. Secret Key는 재확인이 불가하므로 새 키 발급이 가장 안전합니다."
    if "ip" in lowered or "blocked" in lowered or "not allowed" in lowered:
        return "허용 IP가 맞지 않습니다. 업비트 Open API 키에 Zenthex 서버의 공인 IP를 등록해야 합니다."
    return "업비트 인증에 실패했습니다. 자산조회/주문 권한, 허용 IP, Access/Secret 복사 상태를 확인하세요."

def check_upbit_key(access_key: str, secret_key: str):
    upbit = pyupbit.Upbit(access_key, secret_key)
    balances = upbit.get_balances()
    if balances is None:
        return None, None, "업비트가 잔고 정보를 반환하지 않았습니다. 대부분 허용 IP 불일치, 권한 부족, 키 복사 오류입니다."
    if isinstance(balances, dict):
        return None, balances, explain_upbit_auth_error(balances)
    if not isinstance(balances, list):
        return None, balances, explain_upbit_auth_error(balances)
    krw_balance = 0.0
    for row in balances:
        if row.get("currency") == "KRW":
            krw_balance = float(row.get("balance") or 0)
            break
    return upbit, krw_balance, None

def run_upbit_key_validation(config: UpbitKeyCheck, Authorization: str, db: Session, purpose: str):
    if not Authorization:
        return {"status": "error", "message": f"키 {purpose}은 로그인 후 사용할 수 있습니다.", "verified": False}
    user = get_current_user(Authorization.replace("Bearer ", ""), db)
    if not user_can_real_trade(user):
        return {"status": "error", "message": f"키 {purpose}과 실거래는 Trading Pro 또는 Ultimate 구독 권한이 필요합니다.", "verified": False}

    access_key = clean_api_key(config.accessKey)
    secret_key = clean_api_key(config.secretKey)
    if not access_key or not secret_key:
        return {"status": "error", "message": "업비트 Access Key와 Secret Key를 모두 입력해야 합니다.", "verified": False}

    try:
        _, krw_balance, auth_error = check_upbit_key(access_key, secret_key)
        if auth_error:
            return {
                "status": "error",
                "message": auth_error,
                "verified": False,
                "checklist": [
                    "업비트 Open API 권한에서 자산조회와 주문하기가 켜져 있는지 확인",
                    "출금 권한은 꺼져 있어야 함",
                    "키에 등록한 허용 IP가 Zenthex가 실행되는 서버의 공인 IP와 같은지 확인",
                    "Secret Key는 발급 직후 한 번만 보이므로 복사 실수 시 새 키 발급",
                ],
            }
        return {
            "status": "success",
            "message": f"업비트 키 {purpose} 성공. 조회 가능한 KRW 잔고는 약 {float(krw_balance or 0):,.0f}원입니다. 이제 실거래 시작을 누를 수 있습니다.",
            "verified": True,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": explain_upbit_auth_error(e),
            "verified": False,
            "checklist": [
                "Access Key가 새로 발급한 키와 같은지 확인",
                "Secret Key 앞뒤 공백과 줄바꿈이 없는지 확인",
                "업비트 키의 허용 IP에 현재 배포 서버 공인 IP 등록",
                "자산조회/주문하기 권한 확인",
            ],
        }

@router.post("/check-key")
async def check_key(config: UpbitKeyCheck, Authorization: str = Header(None), db: Session = Depends(get_db)):
    return run_upbit_key_validation(config, Authorization, db, "진단")

@router.post("/verify-key")
async def verify_key(config: UpbitKeyCheck, Authorization: str = Header(None), db: Session = Depends(get_db)):
    return run_upbit_key_validation(config, Authorization, db, "인증")

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
        access_key = clean_api_key(config.accessKey)
        secret_key = clean_api_key(config.secretKey)
        if not access_key or not secret_key:
            return {"status": "error", "message": "업비트 Access Key와 Secret Key가 필요합니다."}
        try:
            upbit, real_krw, auth_error = check_upbit_key(access_key, secret_key)
            if auth_error:
                log_trade(f"[Real Auth Error] {auth_error}")
                return {"status": "error", "message": auth_error}
            bot_state.upbit = upbit
            bot_state.balance = float(real_krw or 0)
            bot_state.is_real_key = True
            log_trade("[Real Mode] 업비트 실거래 모드가 활성화되었습니다. 출금 권한 없는 API 키만 사용하세요.")
        except Exception as e:
            bot_state.trading_mode = "practice"
            bot_state.is_real_key = False
            message = explain_upbit_auth_error(e)
            log_trade(f"[Real Auth Error] {message} / raw={e}")
            return {"status": "error", "message": message}
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
