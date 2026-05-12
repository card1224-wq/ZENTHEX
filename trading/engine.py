import time
import asyncio
import pyupbit
from mobile.push import send_push_notification
from admin.router import admin_state

class TradingState:
    IDLE = "IDLE"
    BUYING = "BUYING"
    HOLDING = "HOLDING"
    SELLING = "SELLING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"

class BotState:
    def __init__(self):
        self.state = TradingState.STOPPED
        self.is_real_key = False
        self.trading_mode = "practice"
        self.upbit = None
        self.balance = 1000000.0
        self.held_btc = 0.0
        self.avg_buy_price = 0.0
        self.active_ticker = "KRW-BTC"
        self.ticker_mode = "auto"
        self.selected_ticker = "KRW-BTC"
        self.signal_candidates = []
        self.target_yield = 1.01
        self.investment_mode = "fixed"
        self.investment_amount = 50000.0
        self.investment_ratio = 0.5
        self.daily_max_loss_pct = 0.05
        self.consecutive_loss_count = 0
        self.max_consecutive_loss = 3
        self.initial_daily_balance = self.balance
        self.logs = ["[System] Zenthex Signal Guard 대기 중: 업비트 전체 KRW 마켓을 스캔합니다."]

bot_state = BotState()

def log_trade(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    bot_state.logs.append(full_msg)
    if len(bot_state.logs) > 80:
        bot_state.logs.pop(0)

def ticker_currency(ticker: str) -> str:
    return ticker.split("-", 1)[1] if "-" in ticker else ticker

def get_current_price(ticker: str) -> float:
    try:
        return float(pyupbit.get_current_price(ticker) or 0)
    except Exception:
        return 0.0

def scan_upbit_candidates(limit: int = 5):
    """Signal scanner. It filters momentum candidates, not guaranteed profit."""
    try:
        markets = pyupbit.get_tickers(fiat="KRW")[:80]
        candidates = []
        for ticker in markets:
            try:
                ohlcv = pyupbit.get_ohlcv(ticker, interval="minute60", count=6)
                if ohlcv is None or len(ohlcv) < 2:
                    continue
                first = float(ohlcv["close"].iloc[0])
                last = float(ohlcv["close"].iloc[-1])
                volume = float(ohlcv["volume"].tail(3).sum())
                if first <= 0:
                    continue
                momentum = (last / first) - 1.0
                score = momentum * 100000 + min(volume, 1000000) / 1000000
                if momentum > 0:
                    candidates.append({"ticker": ticker, "momentum": momentum, "price": last, "score": score})
            except Exception:
                continue
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:limit]
    except Exception as e:
        log_trade(f"[Signal Guard] 전체 코인 스캔 실패, BTC 기준으로 전환합니다: {e}")
        price = get_current_price("KRW-BTC") or 80000000
        return [{"ticker": "KRW-BTC", "momentum": 0, "price": price, "score": 0}]

async def refresh_real_balances():
    if not bot_state.upbit:
        return
    try:
        bot_state.balance = float(bot_state.upbit.get_balance("KRW") or 0)
        bot_state.held_btc = float(bot_state.upbit.get_balance(ticker_currency(bot_state.active_ticker)) or 0)
    except Exception as e:
        log_trade(f"[Exchange] 잔고 조회 실패: {e}")

async def scalping_loop():
    mode_label = "실거래" if bot_state.trading_mode == "real" else "전략 체험"
    log_trade(f"[Signal Guard] {mode_label} 엔진 시작: 코인 선택 -> 조건 검증 -> 목표 도달 시 자동 종료")
    bot_state.state = TradingState.IDLE
    if bot_state.trading_mode == "real":
        await refresh_real_balances()
    bot_state.initial_daily_balance = bot_state.balance

    while bot_state.state not in [TradingState.ERROR, TradingState.STOPPED]:
        try:
            if admin_state.global_kill_switch:
                log_trade("[CEO Kill Switch] 전체 정지 활성화. 신규 매매를 차단합니다.")
                await asyncio.sleep(5)
                continue

            price = get_current_price(bot_state.active_ticker) or 80000000
            est_total = bot_state.balance + (bot_state.held_btc * price)
            if est_total < bot_state.initial_daily_balance * (1.0 - bot_state.daily_max_loss_pct):
                log_trade("[Risk Manager] 일일 최대 손실 한도 도달. 엔진을 정지합니다.")
                send_push_notification("Zenthex Trading 정지", "일일 최대 손실 한도에 도달해 엔진을 정지했습니다.")
                bot_state.state = TradingState.ERROR
                break

            if bot_state.consecutive_loss_count >= bot_state.max_consecutive_loss:
                log_trade("[Risk Manager] 연속 손절 제한 도달. 엔진을 정지합니다.")
                send_push_notification("Zenthex Trading 정지", "연속 손절 제한에 도달했습니다.")
                bot_state.state = TradingState.ERROR
                break

            if bot_state.state == TradingState.IDLE and bot_state.held_btc == 0:
                candidates = scan_upbit_candidates()
                bot_state.signal_candidates = candidates
                if bot_state.ticker_mode == "manual":
                    bot_state.active_ticker = bot_state.selected_ticker or "KRW-BTC"
                    price = get_current_price(bot_state.active_ticker) or price
                    log_trade(f"[Signal Guard] 사용자 선택 코인: {bot_state.active_ticker}")
                else:
                    chosen = candidates[0]
                    bot_state.active_ticker = chosen["ticker"]
                    price = chosen["price"] or get_current_price(bot_state.active_ticker) or price
                    log_trade(f"[Signal Guard] 상승 후보 선정: {bot_state.active_ticker} / 최근 모멘텀 {chosen['momentum'] * 100:.2f}%")

                bot_state.state = TradingState.BUYING
                if bot_state.trading_mode == "real":
                    await refresh_real_balances()

                if bot_state.investment_mode == "fixed":
                    invest_krw = min(bot_state.investment_amount, bot_state.balance * 0.99)
                else:
                    invest_krw = bot_state.balance * bot_state.investment_ratio * 0.99

                if invest_krw < 5000:
                    log_trade("[Risk Manager] 주문 가능 금액이 부족합니다. 최소 5,000원 이상으로 설정하세요.")
                    bot_state.state = TradingState.ERROR
                    break

                if bot_state.trading_mode == "real":
                    result = bot_state.upbit.buy_market_order(bot_state.active_ticker, invest_krw)
                    if not result or (isinstance(result, dict) and result.get("error")):
                        log_trade(f"[Real Buy Error] 매수 주문 실패: {result}")
                        bot_state.state = TradingState.ERROR
                        break
                    await asyncio.sleep(1)
                    await refresh_real_balances()
                    bot_state.avg_buy_price = price
                    log_trade(f"[Real Entry] {bot_state.active_ticker} {invest_krw:,.0f}원 실매수 요청 완료. 기준가 {price:,.0f}원")
                else:
                    buy_qty = invest_krw / price
                    bot_state.held_btc = buy_qty * 0.9995
                    bot_state.avg_buy_price = price
                    bot_state.balance -= invest_krw
                    log_trade(f"[Strategy Entry] {bot_state.active_ticker} {invest_krw:,.0f}원 진입. 체결가 {price:,.0f}원")
                bot_state.state = TradingState.HOLDING

            elif bot_state.state == TradingState.HOLDING:
                current_yield = price / bot_state.avg_buy_price if bot_state.avg_buy_price else 1.0
                if current_yield >= bot_state.target_yield:
                    bot_state.state = TradingState.SELLING
                    profit_pct = (current_yield - 1.0) * 100
                    if bot_state.trading_mode == "real":
                        result = bot_state.upbit.sell_market_order(bot_state.active_ticker, bot_state.held_btc)
                        if not result or (isinstance(result, dict) and result.get("error")):
                            log_trade(f"[Real Sell Error] 매도 주문 실패: {result}")
                            bot_state.state = TradingState.ERROR
                            break
                        await asyncio.sleep(1)
                        await refresh_real_balances()
                        log_trade(f"[Real Take Profit] {bot_state.active_ticker} 목표 수익률 도달 +{profit_pct:.2f}%. 실매도 후 엔진 종료.")
                    else:
                        sell_amount = (bot_state.held_btc * price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        log_trade(f"[Take Profit] {bot_state.active_ticker} 목표 수익률 도달 +{profit_pct:.2f}%. 자동 매도 후 엔진 종료.")
                    bot_state.avg_buy_price = 0
                    bot_state.consecutive_loss_count = 0
                    bot_state.state = TradingState.STOPPED
                    send_push_notification("목표 수익률 도달", f"{bot_state.active_ticker} +{profit_pct:.2f}% 달성. 엔진을 종료했습니다.")

                elif current_yield <= 0.98:
                    bot_state.state = TradingState.SELLING
                    loss_pct = (1.0 - current_yield) * 100
                    if bot_state.trading_mode == "real":
                        result = bot_state.upbit.sell_market_order(bot_state.active_ticker, bot_state.held_btc)
                        if not result or (isinstance(result, dict) and result.get("error")):
                            log_trade(f"[Real Stop Error] 손절 주문 실패: {result}")
                            bot_state.state = TradingState.ERROR
                            break
                        await asyncio.sleep(1)
                        await refresh_real_balances()
                        log_trade(f"[Real Stop Loss] {bot_state.active_ticker} -{loss_pct:.2f}%. 실매도 후 대기 상태로 복귀.")
                    else:
                        sell_amount = (bot_state.held_btc * price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        log_trade(f"[Stop Loss] {bot_state.active_ticker} -{loss_pct:.2f}%. 손절 후 대기 상태로 복귀.")
                    bot_state.avg_buy_price = 0
                    bot_state.consecutive_loss_count += 1
                    bot_state.state = TradingState.IDLE

        except Exception as e:
            log_trade(f"[System Error] {e}")
            bot_state.state = TradingState.ERROR

        await asyncio.sleep(5)
