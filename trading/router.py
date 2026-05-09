import pyupbit
import asyncio
from trading.engine import bot_state, TradingState, scalping_loop, log_trade
from security.crypto import encrypt_api_key, decrypt_api_key

router = APIRouter(prefix="/api/finance", tags=["finance"])

class StartConfig(BaseModel):
    accessKey: str
    secretKey: str
    targetYield: float
    investmentMode: str = "fixed" # "fixed" or "ratio"
    investmentAmount: float = 50000.0
    investmentRatio: float = 0.5 

class ManualTrade(BaseModel):
    type: str # 'buy' or 'sell'
    amount: float

@router.post("/start")
async def start_bot(config: StartConfig):
    if bot_state.state not in [TradingState.STOPPED, TradingState.ERROR]:
        return {"status": "error", "message": "Bot is already running"}
    
    bot_state.target_yield = config.targetYield
    bot_state.investment_mode = config.investmentMode
    bot_state.investment_amount = config.investmentAmount
    bot_state.investment_ratio = config.investmentRatio
    bot_state.consecutive_loss_count = 0 # reset
    
    try:
        if config.accessKey and config.secretKey:
            # 실거래 시작 시 복호화된 키를 메모리에만 로드
            bot_state.upbit = pyupbit.Upbit(config.accessKey, config.secretKey)
            bot_state.is_real_key = True
            
            # DB에는 암호화하여 저장 추천 (이후 영속성 필요 시)
            # encrypted_access = encrypt_api_key(config.accessKey)
            # encrypted_secret = encrypt_api_key(config.secretKey)
            
            real_krw = bot_state.upbit.get_balance("KRW")
            if real_krw is not None and real_krw > 0:
                bot_state.balance = real_krw 
            log_trade(f"[위험] 🔥 실제 업비트 인증 완료! 모드:{config.investmentMode}. 실거래 스캘핑을 시작합니다.")
        else:
            bot_state.is_real_key = False
            log_trade(f"[알림] 순수 모의 백테스트 모드 ({config.investmentMode})로 구동합니다.")
    except Exception as e:
        bot_state.is_real_key = False
        log_trade(f"API 인증 실패. 모의 모드로 전환합니다. {e}")

    asyncio.create_task(scalping_loop())
    return {"status": "success", "message": "Bot Engine Started"}

@router.post("/manual_trade")
async def manual_trade(trade: ManualTrade):
    current_price = pyupbit.get_current_price("KRW-BTC") or 80000000
    if trade.type == "buy":
        if bot_state.balance >= trade.amount:
            buy_qty = trade.amount / current_price
            bot_state.held_btc += buy_qty * 0.9995
            bot_state.avg_buy_price = current_price 
            bot_state.balance -= trade.amount
            log_trade(f"🕹️ [수동 매수 완료] {trade.amount:,}원 시장가 진입. (체결가: {current_price:,}원)")
        else:
            log_trade(f"❌ [주문 실패] 잔고 부족 (현재 잔고: {bot_state.balance:,.0f}원)")
    elif trade.type == "sell":
        if bot_state.held_btc > 0:
            sell_amount = (bot_state.held_btc * current_price) * 0.9995
            bot_state.balance += sell_amount
            bot_state.held_btc = 0
            bot_state.avg_buy_price = 0
            log_trade(f"🕹️ [수동 매도 완료] 전량 시장가 매도. (회수 금액: {sell_amount:,.0f}원)")
        else:
            log_trade(f"❌ [주문 실패] 보유 중인 가상자산이 없습니다.")

    return {"status": "success"}

@router.post("/stop")
async def stop_bot():
    bot_state.state = TradingState.STOPPED
    log_trade("사용자 요청에 의해 매매 엔진 가동을 중단합니다.")
    return {"status": "success", "message": "Bot Engine Stopped"}

@router.get("/status")
async def status():
    current_price = pyupbit.get_current_price("KRW-BTC") or 80000000
    est_balance = bot_state.balance
    if bot_state.held_btc > 0:
        est_balance += (bot_state.held_btc * current_price)

    return {
        "isRunning": bot_state.state not in [TradingState.STOPPED, TradingState.ERROR],
        "state": bot_state.state,
        "isRealKey": bot_state.is_real_key,
        "currentBtcPrice": current_price,
        "balance": bot_state.balance,
        "estBalance": est_balance,
        "avgBuyPrice": bot_state.avg_buy_price,
        "logs": bot_state.logs[-15:]
    }
