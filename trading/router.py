from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from fastapi import HTTPException
from sqlalchemy.orm import Session
import asyncio
import os
import urllib.request
import pyupbit

from auth.router import get_current_user
from database.session import get_db
from trading.engine import bot_state, TradingState, scalping_loop, log_trade

router = APIRouter(prefix="/api/finance", tags=["finance"])

class StartConfig(BaseModel):
    accessKey: str = ""
    secretKey: str = ""
    targetYield: float
    exitMode: str = "fixed"
    trailingStartYield: float = 1.005
    trailingDropPct: float = 0.004
    investmentMode: str = "all_krw"
    investmentAmount: float = 50000.0
    investmentRatio: float = 0.5
    entryMode: str = "single"
    entrySlices: int = 1
    addEntryDropPct: float = 0.005
    rotateExistingAccepted: bool = False
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

def detect_outbound_ip() -> str:
    with urllib.request.urlopen("https://api.ipify.org", timeout=4) as response:
        return response.read().decode("utf-8").strip()

@router.get("/server-ip")
async def server_ip():
    public_ip = (os.getenv("ZENTHEX_SERVER_PUBLIC_IP") or "").strip()
    source = "env"
    if not public_ip:
        try:
            public_ip = detect_outbound_ip()
            source = "auto_detected"
        except Exception:
            public_ip = ""
    if not public_ip:
        return {
            "status": "missing",
            "server_ip": "",
            "is_fixed": False,
            "message": "Zenthex 서버 공인 IP가 아직 설정되지 않았습니다. 실거래 서버에서 확인한 고정 IP를 ZENTHEX_SERVER_PUBLIC_IP 환경변수에 넣어야 합니다.",
        }
    if source != "env":
        return {
            "status": "warning",
            "server_ip": public_ip,
            "source": source,
            "is_fixed": False,
            "message": "현재 IP는 자동 감지값입니다. 운영 실거래에서는 바뀌면 안 되므로 고정 서버 IP를 ZENTHEX_SERVER_PUBLIC_IP에 설정해야 합니다.",
        }
    return {
        "status": "success",
        "server_ip": public_ip,
        "source": source,
        "is_fixed": True,
        "message": "이 IP를 Upbit Open API 허용 IP에 등록하세요.",
    }

@router.get("/server-ip/verify")
async def verify_server_ip():
    configured_ip = (os.getenv("ZENTHEX_SERVER_PUBLIC_IP") or "").strip()
    try:
        outbound_ip = detect_outbound_ip()
    except Exception as exc:
        return {
            "status": "error",
            "configured_ip": configured_ip,
            "outbound_ip": "",
            "matches": False,
            "message": f"실제 outbound IP를 확인하지 못했습니다: {exc}",
        }
    if not configured_ip:
        return {
            "status": "missing",
            "configured_ip": "",
            "outbound_ip": outbound_ip,
            "matches": False,
            "message": "ZENTHEX_SERVER_PUBLIC_IP가 비어 있습니다. 표시 IP가 아니라 실제 고정 IP를 서버 환경변수에 설정해야 합니다.",
        }
    matches = configured_ip == outbound_ip
    return {
        "status": "success" if matches else "mismatch",
        "configured_ip": configured_ip,
        "outbound_ip": outbound_ip,
        "matches": matches,
        "message": "표시 IP와 실제 outbound IP가 일치합니다." if matches else "표시 IP와 실제 outbound IP가 다릅니다. Upbit 허용 IP에는 실제 outbound IP가 필요하며, 실거래 전 고정 IP 라우팅을 확인해야 합니다.",
    }

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

def build_upbit_account_summary(upbit):
    balances = upbit.get_balances()
    if balances is None or isinstance(balances, dict) or not isinstance(balances, list):
        return None, explain_upbit_auth_error(balances)

    cash_balance = 0.0
    coin_value = 0.0
    invested_value = 0.0
    positions = []
    for row in balances:
        currency = row.get("currency")
        qty = float(row.get("balance") or 0)
        locked = float(row.get("locked") or 0)
        total_qty = qty + locked
        if currency == "KRW":
            cash_balance = qty
            continue
        if not currency or total_qty <= 0:
            continue
        ticker = f"KRW-{currency}"
        price = pyupbit.get_current_price(ticker) or 0
        if not price:
            continue
        avg_price = float(row.get("avg_buy_price") or 0)
        valuation = total_qty * float(price)
        if valuation < 1:
            continue
        entry_value = avg_price * total_qty if avg_price else 0
        pnl = valuation - entry_value if entry_value else 0
        pnl_pct = pnl / entry_value if entry_value else 0
        invested_value += entry_value
        coin_value += valuation
        positions.append({
            "ticker": ticker,
            "qty": total_qty,
            "availableQty": qty,
            "lockedQty": locked,
            "avgBuyPrice": avg_price,
            "entryKrw": entry_value,
            "currentPrice": float(price),
            "valuation": valuation,
            "pnl": pnl,
            "pnlPct": pnl_pct,
            "targetPrice": 0,
            "stopPrice": 0,
            "status": "UPBIT HOLDING",
        })

    positions.sort(key=lambda item: item["valuation"], reverse=True)
    est_balance = cash_balance + coin_value
    total_pnl = coin_value - invested_value if invested_value else 0
    total_pnl_pct = total_pnl / invested_value if invested_value else 0
    return {
        "cashBalance": cash_balance,
        "coinValue": coin_value,
        "estBalance": est_balance,
        "investedValue": invested_value,
        "totalPnl": total_pnl,
        "totalPnlPct": total_pnl_pct,
        "positions": positions,
    }, None

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

@router.post("/account-summary")
async def account_summary(config: UpbitKeyCheck, Authorization: str = Header(None), db: Session = Depends(get_db)):
    if not Authorization:
        return {"status": "error", "message": "업비트 잔고 조회는 로그인 후 사용할 수 있습니다."}
    user = get_current_user(Authorization.replace("Bearer ", ""), db)
    if not user_can_real_trade(user):
        return {"status": "error", "message": "업비트 잔고 조회는 Trading Pro 또는 Ultimate 구독 권한이 필요합니다."}

    access_key = clean_api_key(config.accessKey)
    secret_key = clean_api_key(config.secretKey)
    if not access_key or not secret_key:
        return {"status": "error", "message": "업비트 Access Key와 Secret Key를 모두 입력해야 합니다."}

    try:
        upbit = pyupbit.Upbit(access_key, secret_key)
        summary, error = await asyncio.to_thread(build_upbit_account_summary, upbit)
        if error:
            return {"status": "error", "message": error}
        return {"status": "success", "message": "업비트 잔고와 수익률을 불러왔습니다.", **summary}
    except Exception as e:
        return {"status": "error", "message": explain_upbit_auth_error(e)}

@router.post("/start")
async def start_bot(config: StartConfig, Authorization: str = Header(None), db: Session = Depends(get_db)):
    if bot_state.state not in [TradingState.STOPPED, TradingState.ERROR]:
        return {"status": "error", "message": "Bot is already running"}

    bot_state.target_yield = config.targetYield
    bot_state.exit_mode = config.exitMode if config.exitMode in ["fixed", "trailing"] else "fixed"
    bot_state.trailing_start_yield = max(config.trailingStartYield, 1.001)
    bot_state.trailing_drop_pct = min(max(config.trailingDropPct, 0.001), 0.05)
    bot_state.peak_yield = 1.0
    bot_state.investment_mode = config.investmentMode if config.investmentMode in ["all_krw", "fixed", "ratio", "rotate_holdings"] else "all_krw"
    bot_state.investment_amount = config.investmentAmount
    bot_state.investment_ratio = config.investmentRatio
    bot_state.entry_mode = config.entryMode if config.entryMode in ["single", "split"] else "single"
    bot_state.entry_slices = min(max(int(config.entrySlices or 1), 1), 10) if bot_state.entry_mode == "split" else 1
    bot_state.add_entry_drop_pct = min(max(float(config.addEntryDropPct or 0.005), 0.001), 0.05)
    bot_state.ticker_mode = config.tickerMode if config.tickerMode in ["auto", "manual"] else "auto"
    bot_state.selected_ticker = config.selectedTicker if config.selectedTicker.startswith("KRW-") else "KRW-BTC"
    bot_state.trading_mode = config.tradingMode if config.tradingMode in ["practice", "real"] else "practice"
    bot_state.consecutive_loss_count = 0
    bot_state.held_btc = 0
    bot_state.avg_buy_price = 0
    bot_state.entry_krw = 0
    bot_state.entry_count = 0
    bot_state.planned_total_krw = 0
    bot_state.upbit = None
    bot_state.is_real_key = False
    bot_state.last_order_uuid = ""
    bot_state.last_order_side = ""
    bot_state.last_order_status = "대기"
    bot_state.rotate_existing_accepted = config.rotateExistingAccepted
    bot_state.rotated_holdings = False
    if bot_state.entry_mode == "split":
        bot_state.risk_rule = f"리스크: 총 투자금을 {bot_state.entry_slices}회로 나누어 진입, 평균가 대비 {bot_state.add_entry_drop_pct * 100:.1f}% 구간마다 추가 진입, 전체 손절선과 일일 손실 제한 적용"
    else:
        bot_state.risk_rule = "리스크: 최소 주문 5,000원, 일일 최대 손실 5%, 연속 손절 3회 제한"

    if bot_state.trading_mode == "real":
        if not Authorization:
            return {"status": "error", "message": "실거래는 로그인 후 Trading Pro 또는 Ultimate 구독이 필요합니다."}
        user = get_current_user(Authorization.replace("Bearer ", ""), db)
        if not user_can_real_trade(user):
            return {"status": "error", "message": "실거래는 Trading Pro 또는 Ultimate 구독 후 사용할 수 있습니다."}
        if not config.realAccepted:
            return {"status": "error", "message": "실거래 위험 확인 체크가 필요합니다."}
        if bot_state.investment_mode == "rotate_holdings" and not config.rotateExistingAccepted:
            return {"status": "error", "message": "보유 코인 정리 후 재진입은 별도 위험 확인 체크가 필요합니다."}
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

def require_real_status_permission(Authorization: str | None, db: Session):
    if bot_state.trading_mode != "real" and not bot_state.is_real_key:
        return None
    if not Authorization:
        raise HTTPException(status_code=401, detail="실거래 상태 조회는 로그인이 필요합니다.")
    user = get_current_user(Authorization.replace("Bearer ", ""), db)
    if not user_can_real_trade(user):
        raise HTTPException(status_code=403, detail="실거래 상태 조회는 Trading Pro 또는 Ultimate 권한이 필요합니다.")
    return user

@router.post("/stop")
async def stop_bot(Authorization: str = Header(None), db: Session = Depends(get_db)):
    require_real_status_permission(Authorization, db)
    bot_state.state = TradingState.STOPPED
    bot_state.decision_note = "사용자가 엔진을 일시정지했습니다. 보유 코인은 매도하지 않고 유지합니다."
    log_trade("[User Pause] 사용자 요청으로 엔진을 일시정지합니다. 보유 코인은 매도하지 않습니다.")
    return {"status": "success", "message": "Bot Engine Paused. Holdings were not sold."}

@router.post("/sell-and-stop")
async def sell_and_stop_bot(Authorization: str = Header(None), db: Session = Depends(get_db)):
    require_real_status_permission(Authorization, db)
    current_price = pyupbit.get_current_price(bot_state.active_ticker) or 0
    sell_qty = float(bot_state.held_btc or 0)

    if sell_qty <= 0:
        bot_state.state = TradingState.STOPPED
        bot_state.decision_note = "매도할 Zenthex 보유 수량이 없어 엔진만 종료했습니다."
        log_trade("[User Sell Exit] 매도할 Zenthex 보유 수량이 없어 엔진만 종료합니다.")
        return {"status": "success", "message": "매도할 Zenthex 보유 수량이 없어 엔진만 종료했습니다."}

    bot_state.state = TradingState.SELLING
    bot_state.decision_note = "사용자 요청으로 현재 Zenthex 보유 수량을 시장가 매도한 뒤 엔진을 종료합니다."
    try:
        if bot_state.trading_mode == "real":
            if not bot_state.upbit:
                bot_state.state = TradingState.ERROR
                return {"status": "error", "message": "실거래 연결 정보가 없어 시장가 매도를 실행할 수 없습니다. 업비트에서 직접 보유 수량을 확인하세요."}
            result = await asyncio.to_thread(bot_state.upbit.sell_market_order, bot_state.active_ticker, sell_qty)
            if not result or (isinstance(result, dict) and result.get("error")):
                bot_state.state = TradingState.ERROR
                log_trade(f"[User Sell Exit Error] 매도 주문 실패: {result}")
                return {"status": "error", "message": f"매도 주문 실패: {result}"}
            from trading.engine import remember_order, reset_position_tracking, refresh_real_balances
            remember_order(result, "USER SELL EXIT")
            await asyncio.sleep(1)
            await refresh_real_balances()
            reset_position_tracking()
            bot_state.state = TradingState.STOPPED
            log_trade(f"[User Sell Exit] {bot_state.active_ticker} {sell_qty:.8f}개 시장가 매도 후 엔진 종료.")
            return {"status": "success", "message": "현재 Zenthex 보유 수량을 시장가 매도하고 엔진을 종료했습니다."}

        sell_amount = (sell_qty * current_price) * 0.9995
        bot_state.balance += sell_amount
        from trading.engine import reset_position_tracking
        reset_position_tracking()
        bot_state.state = TradingState.STOPPED
        log_trade(f"[User Sell Exit] 체험 보유 수량 전량 매도 후 엔진 종료. 회수금 {sell_amount:,.0f}원")
        return {"status": "success", "message": "체험 보유 수량을 전량 매도하고 엔진을 종료했습니다."}
    except Exception as exc:
        bot_state.state = TradingState.ERROR
        log_trade(f"[User Sell Exit Error] {exc}")
        return {"status": "error", "message": f"전량 매도 후 종료 중 오류가 발생했습니다: {exc}"}

@router.get("/status")
async def status(Authorization: str = Header(None), db: Session = Depends(get_db)):
    require_real_status_permission(Authorization, db)
    current_price = pyupbit.get_current_price(bot_state.active_ticker) or 80000000
    coin_value = bot_state.held_btc * current_price if bot_state.held_btc > 0 else 0
    est_balance = bot_state.balance + coin_value
    current_yield = ((current_price / bot_state.avg_buy_price) - 1.0) if bot_state.avg_buy_price else 0
    target_price = bot_state.avg_buy_price * bot_state.target_yield if bot_state.avg_buy_price else 0
    stop_price = bot_state.avg_buy_price * bot_state.stop_loss_yield if bot_state.avg_buy_price else 0
    initial_balance = bot_state.initial_daily_balance or bot_state.balance or 0
    total_pnl = est_balance - initial_balance if initial_balance else 0
    total_pnl_pct = (total_pnl / initial_balance) if initial_balance else 0
    position_pnl = coin_value - bot_state.entry_krw if bot_state.entry_krw and coin_value else 0
    position_pnl_pct = (position_pnl / bot_state.entry_krw) if bot_state.entry_krw else current_yield
    positions = []
    if bot_state.trading_mode == "real" and bot_state.upbit:
        try:
            summary, _ = await asyncio.to_thread(build_upbit_account_summary, bot_state.upbit)
            if summary:
                positions = summary["positions"]
                for item in positions:
                    if item["ticker"] == bot_state.active_ticker:
                        item["targetPrice"] = target_price
                        item["stopPrice"] = stop_price
                        item["status"] = bot_state.state
                bot_state.balance = summary["cashBalance"]
                coin_value = summary["coinValue"]
                est_balance = summary["estBalance"]
                total_pnl = summary["totalPnl"]
                total_pnl_pct = summary["totalPnlPct"]
        except Exception:
            pass
    if not positions and (bot_state.held_btc > 0 or bot_state.avg_buy_price > 0):
        positions.append({
            "ticker": bot_state.active_ticker,
            "qty": bot_state.held_btc,
            "avgBuyPrice": bot_state.avg_buy_price,
            "entryKrw": bot_state.entry_krw,
            "currentPrice": current_price,
            "valuation": coin_value,
            "pnl": position_pnl,
            "pnlPct": position_pnl_pct,
            "targetPrice": target_price,
            "stopPrice": stop_price,
            "peakYield": bot_state.peak_yield,
            "status": bot_state.state,
        })
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
        "cashBalance": bot_state.balance,
        "coinValue": coin_value,
        "initialBalance": initial_balance,
        "totalPnl": total_pnl,
        "totalPnlPct": total_pnl_pct,
        "heldBtc": bot_state.held_btc,
        "avgBuyPrice": bot_state.avg_buy_price,
        "entryKrw": bot_state.entry_krw,
        "positionPnl": position_pnl,
        "positionPnlPct": position_pnl_pct,
        "positions": positions,
        "currentYield": current_yield,
        "targetYield": bot_state.target_yield,
        "exitMode": bot_state.exit_mode,
        "trailingStartYield": bot_state.trailing_start_yield,
        "trailingDropPct": bot_state.trailing_drop_pct,
        "peakYield": bot_state.peak_yield,
        "investmentMode": bot_state.investment_mode,
        "entryMode": bot_state.entry_mode,
        "entrySlices": bot_state.entry_slices,
        "entryCount": bot_state.entry_count,
        "plannedTotalKrw": bot_state.planned_total_krw,
        "addEntryDropPct": bot_state.add_entry_drop_pct,
        "rotateExistingAccepted": bot_state.rotate_existing_accepted,
        "targetPrice": target_price,
        "stopLossYield": bot_state.stop_loss_yield,
        "stopPrice": stop_price,
        "lastOrderUuid": bot_state.last_order_uuid,
        "lastOrderSide": bot_state.last_order_side,
        "lastOrderStatus": bot_state.last_order_status,
        "decisionNote": bot_state.decision_note,
        "marketGuardNote": bot_state.market_guard_note,
        "cooldownCount": len(bot_state.cooldowns),
        "entryRule": bot_state.entry_rule,
        "exitRule": bot_state.exit_rule,
        "riskRule": bot_state.risk_rule,
        "currentScore": bot_state.current_score,
        "pollIntervalSeconds": 2,
        "logs": bot_state.logs[-20:],
    }
