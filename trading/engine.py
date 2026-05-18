import time
import asyncio
import pyupbit
from mobile.push import send_push_notification
from admin.router import admin_state

class TradingState:
    IDLE = "IDLE"
    SCANNING = "SCANNING"
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
        self.entry_krw = 0.0
        self.active_ticker = "KRW-BTC"
        self.ticker_mode = "auto"
        self.selected_ticker = "KRW-BTC"
        self.signal_candidates = []
        self.target_yield = 1.01
        self.stop_loss_yield = 0.994
        self.exit_mode = "fixed"
        self.trailing_start_yield = 1.005
        self.trailing_drop_pct = 0.004
        self.peak_yield = 1.0
        self.investment_mode = "all_krw"
        self.investment_amount = 50000.0
        self.investment_ratio = 0.5
        self.rotate_existing_accepted = False
        self.rotated_holdings = False
        self.daily_max_loss_pct = 0.05
        self.consecutive_loss_count = 0
        self.max_consecutive_loss = 3
        self.initial_daily_balance = self.balance
        self.last_order_uuid = ""
        self.last_order_side = ""
        self.last_order_status = "대기"
        self.decision_note = "대기 중입니다. 시작하면 전체 KRW 마켓을 스캔합니다."
        self.entry_rule = "매수: 24시간 상승, 6시간 상승, 1분/3분 단기 상승, 거래량 급증, 과열·급락 위험 필터 통과"
        self.exit_rule = "매도: 고정 목표 도달 또는 추적 익절 조건 충족 시 전량 매도, 손절선 도달 시 전량 매도 후 재스캔"
        self.risk_rule = "리스크: 최소 주문 5,000원, 일일 최대 손실 5%, 연속 손절 3회 제한"
        self.current_score = 0.0
        self.logs = ["[System] Zenthex Signal Guard 대기 중: 업비트 전체 KRW 마켓을 스캔합니다."]

bot_state = BotState()

def log_trade(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    bot_state.logs.append(full_msg)
    if len(bot_state.logs) > 80:
        bot_state.logs.pop(0)

def remember_order(result, side: str):
    bot_state.last_order_side = side
    if isinstance(result, dict):
        bot_state.last_order_uuid = str(result.get("uuid") or "")
        bot_state.last_order_status = str(result.get("state") or "requested")
    else:
        bot_state.last_order_uuid = ""
        bot_state.last_order_status = "requested"

def ticker_currency(ticker: str) -> str:
    return ticker.split("-", 1)[1] if "-" in ticker else ticker

def get_current_price(ticker: str) -> float:
    try:
        return float(pyupbit.get_current_price(ticker) or 0)
    except Exception:
        return 0.0

def get_real_balance(currency: str) -> float:
    if not bot_state.upbit:
        return 0.0
    try:
        return float(bot_state.upbit.get_balance(currency) or 0)
    except Exception as e:
        log_trade(f"[Exchange] {currency} 잔고 조회 실패: {e}")
        return 0.0

def krw_ticker_for_currency(currency: str) -> str:
    return f"KRW-{currency}"

async def liquidate_existing_holdings():
    if not bot_state.upbit:
        return
    if not bot_state.rotate_existing_accepted:
        log_trade("[Rotation Guard] 보유 코인 정리 동의가 없어 기존 보유 코인은 매도하지 않습니다.")
        return
    balances = await asyncio.to_thread(bot_state.upbit.get_balances)
    markets = set(await asyncio.to_thread(pyupbit.get_tickers, fiat="KRW"))
    if not isinstance(balances, list):
        log_trade(f"[Rotation Error] 보유 코인 조회 실패: {balances}")
        return
    sell_count = 0
    for row in balances:
        currency = row.get("currency")
        if not currency or currency == "KRW":
            continue
        ticker = krw_ticker_for_currency(currency)
        if ticker not in markets:
            log_trade(f"[Rotation Skip] {currency}는 KRW 마켓이 없어 자동 매도하지 않습니다.")
            continue
        qty = float(row.get("balance") or 0)
        locked = float(row.get("locked") or 0)
        if qty <= 0 or locked > 0:
            log_trade(f"[Rotation Skip] {ticker} 매도 가능 수량이 없거나 미체결 잠금 수량이 있습니다.")
            continue
        price = get_current_price(ticker)
        if qty * price < 5000:
            log_trade(f"[Rotation Skip] {ticker} 평가금액이 5,000원 미만입니다.")
            continue
        log_trade(f"[Rotation Sell Request] 기존 보유 {ticker} {qty:.8f}개 시장가 매도 요청")
        result = await asyncio.to_thread(bot_state.upbit.sell_market_order, ticker, qty)
        if not result or (isinstance(result, dict) and result.get("error")):
            log_trade(f"[Rotation Sell Error] {ticker} 매도 실패: {result}")
            continue
        remember_order(result, f"ROTATE SELL {ticker}")
        sell_count += 1
        await asyncio.sleep(0.7)
    await refresh_real_balances()
    bot_state.rotated_holdings = True
    log_trade(f"[Rotation Complete] 기존 보유 코인 정리 완료: {sell_count}개 매도 요청, 사용 가능 KRW {bot_state.balance:,.0f}원")

def scan_upbit_candidates(limit: int = 5):
    """Scalping scanner. It filters 24h strength, then ranks 1/3/5m entry signals."""
    try:
        markets = pyupbit.get_tickers(fiat="KRW")
        pre_candidates = []
        candidates = []
        for ticker in markets:
            try:
                hourly = pyupbit.get_ohlcv(ticker, interval="minute60", count=25)
                if hourly is None:
                    continue
                if len(hourly) < 12:
                    continue
                closes = hourly["close"]
                volumes = hourly["volume"]
                first = float(closes.iloc[0])
                last = float(closes.iloc[-1])
                close_6h = float(closes.iloc[-7]) if len(closes) >= 7 else first
                high_24h = float(hourly["high"].max())
                low_24h = float(hourly["low"].min())
                value_24h = float((closes * volumes).sum())
                recent_volume = float(volumes.tail(3).mean())
                previous_volume = float(volumes.iloc[-9:-3].mean() or 1)
                ma12 = float(closes.tail(12).mean())
                ma24 = float(closes.tail(24).mean()) if len(closes) >= 24 else ma12
                if first <= 0 or close_6h <= 0 or low_24h <= 0 or high_24h <= 0:
                    continue

                change_24h = (last / first) - 1.0
                momentum_6h = (last / close_6h) - 1.0
                volume_surge = recent_volume / max(previous_volume, 1e-9)
                volatility = (high_24h / low_24h) - 1.0
                drawdown = (high_24h - last) / high_24h
                trend_bonus = 1.0 if last > ma12 > ma24 else 0.0

                if change_24h <= 0.015 or momentum_6h <= 0 or value_24h < 300_000_000:
                    continue
                if volatility > 0.45 or drawdown > 0.18:
                    continue
                rough_score = (
                    change_24h * 12
                    + momentum_6h * 8
                    + min(volume_surge, 4.0) * 0.04
                    + trend_bonus * 0.08
                    - volatility * 0.18
                    - drawdown * 0.35
                )
                pre_candidates.append({
                    "ticker": ticker,
                    "momentum": change_24h,
                    "momentum6h": momentum_6h,
                    "volumeSurge": volume_surge,
                    "value24h": value_24h,
                    "volatility": volatility,
                    "drawdown": drawdown,
                    "price": last,
                    "roughScore": rough_score,
                })
            except Exception:
                continue

        pre_candidates.sort(key=lambda item: item["roughScore"], reverse=True)
        for base in pre_candidates[:12]:
            ticker = base["ticker"]
            try:
                minute1 = pyupbit.get_ohlcv(ticker, interval="minute1", count=20)
                minute3 = pyupbit.get_ohlcv(ticker, interval="minute3", count=20)
                minute5 = pyupbit.get_ohlcv(ticker, interval="minute5", count=20)
                if minute1 is None or minute3 is None or minute5 is None:
                    continue
                if len(minute1) < 10 or len(minute3) < 10 or len(minute5) < 10:
                    continue
                c1 = minute1["close"]
                v1 = minute1["volume"]
                c3 = minute3["close"]
                c5 = minute5["close"]
                last1 = float(c1.iloc[-1])
                prev_high_5 = float(c1.iloc[-6:-1].max())
                minute1_momentum = (last1 / float(c1.iloc[-4])) - 1.0
                minute3_momentum = (float(c3.iloc[-1]) / float(c3.iloc[-4])) - 1.0
                minute5_momentum = (float(c5.iloc[-1]) / float(c5.iloc[-4])) - 1.0
                recent_tick_volume = float(v1.tail(3).mean())
                previous_tick_volume = float(v1.iloc[-12:-3].mean() or 1)
                tick_volume_surge = recent_tick_volume / max(previous_tick_volume, 1e-9)
                ma5 = float(c1.tail(5).mean())
                ma10 = float(c1.tail(10).mean())
                breakout = 1.0 if last1 > prev_high_5 else 0.0
                short_trend = 1.0 if last1 > ma5 > ma10 else 0.0

                if minute1_momentum <= 0 or minute3_momentum <= 0 or minute5_momentum < -0.002:
                    continue
                if tick_volume_surge < 1.4 and not breakout:
                    continue

                score = (
                    base["roughScore"]
                    + minute1_momentum * 40
                    + minute3_momentum * 24
                    + minute5_momentum * 14
                    + min(tick_volume_surge, 5.0) * 0.12
                    + breakout * 0.22
                    + short_trend * 0.18
                )
                candidates.append({
                    "ticker": ticker,
                    "momentum": base["momentum"],
                    "momentum6h": base["momentum6h"],
                    "volumeSurge": base["volumeSurge"],
                    "tickVolumeSurge": tick_volume_surge,
                    "minute1Momentum": minute1_momentum,
                    "minute3Momentum": minute3_momentum,
                    "minute5Momentum": minute5_momentum,
                    "breakout": breakout,
                    "shortTrend": short_trend,
                    "value24h": base["value24h"],
                    "volatility": base["volatility"],
                    "drawdown": base["drawdown"],
                    "price": base["price"],
                    "score": score,
                })
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
    bot_state.decision_note = f"{mode_label} 엔진 시작. 상승 후보를 찾기 위해 전체 KRW 마켓을 확인합니다."
    bot_state.current_score = 0.0
    bot_state.state = TradingState.IDLE
    if bot_state.trading_mode == "real":
        await refresh_real_balances()
    bot_state.initial_daily_balance = bot_state.balance

    while bot_state.state not in [TradingState.ERROR, TradingState.STOPPED]:
        try:
            if admin_state.global_kill_switch:
                bot_state.decision_note = "대표 긴급 정지가 켜져 있어 신규 매매를 차단하고 있습니다."
                log_trade("[CEO Kill Switch] 전체 정지 활성화. 신규 매매를 차단합니다.")
                await asyncio.sleep(5)
                continue

            price = get_current_price(bot_state.active_ticker) or 80000000
            est_total = bot_state.balance + (bot_state.held_btc * price)
            if est_total < bot_state.initial_daily_balance * (1.0 - bot_state.daily_max_loss_pct):
                bot_state.decision_note = "일일 최대 손실 한도에 도달해 엔진을 정지합니다."
                log_trade("[Risk Manager] 일일 최대 손실 한도 도달. 엔진을 정지합니다.")
                send_push_notification("Zenthex Trading 정지", "일일 최대 손실 한도에 도달해 엔진을 정지했습니다.")
                bot_state.state = TradingState.ERROR
                break

            if bot_state.consecutive_loss_count >= bot_state.max_consecutive_loss:
                bot_state.decision_note = "연속 손절 제한에 도달해 엔진을 정지합니다."
                log_trade("[Risk Manager] 연속 손절 제한 도달. 엔진을 정지합니다.")
                send_push_notification("Zenthex Trading 정지", "연속 손절 제한에 도달했습니다.")
                bot_state.state = TradingState.ERROR
                break

            if bot_state.state == TradingState.IDLE and bot_state.avg_buy_price == 0:
                if bot_state.ticker_mode == "manual":
                    bot_state.active_ticker = bot_state.selected_ticker or "KRW-BTC"
                    price = get_current_price(bot_state.active_ticker) or price
                    bot_state.signal_candidates = [{"ticker": bot_state.active_ticker, "momentum": 0, "price": price, "score": 0, "reason": "직접 선택"}]
                    bot_state.decision_note = f"{bot_state.active_ticker} 직접 선택. 전체 스캔 없이 빠른 진입 조건을 확인합니다."
                    bot_state.current_score = 0.0
                    log_trade(f"[Quick Entry] 사용자 선택 코인 {bot_state.active_ticker}로 전체 스캔 없이 바로 진입 검증을 시작합니다.")
                else:
                    bot_state.state = TradingState.SCANNING
                    bot_state.decision_note = "업비트 KRW 전체 마켓 스캔 중입니다. 24h/6h 상승, 1m/3m/5m 힘, 거래량 급증을 비교합니다."
                    log_trade("[Signal Guard] 업비트 KRW 전체 마켓 스캔 중입니다. 실거래 주문 전 후보를 검증합니다.")
                    candidates = await asyncio.to_thread(scan_upbit_candidates)
                    bot_state.signal_candidates = candidates
                    if not candidates:
                        bot_state.decision_note = "조건을 통과한 코인이 없어 대기합니다. 무리한 진입 없이 10초 후 다시 스캔합니다."
                        log_trade("[Signal Guard] 조건을 통과한 코인이 없습니다. 10초 후 다시 스캔합니다.")
                        bot_state.state = TradingState.IDLE
                        await asyncio.sleep(10)
                        continue
                    chosen = candidates[0]
                    bot_state.active_ticker = chosen["ticker"]
                    price = chosen["price"] or get_current_price(bot_state.active_ticker) or price
                    bot_state.current_score = float(chosen.get("score", 0) or 0)
                    bot_state.decision_note = (
                        f"{bot_state.active_ticker} 선택: 1분 {chosen.get('minute1Momentum', 0) * 100:.2f}%, "
                        f"3분 {chosen.get('minute3Momentum', 0) * 100:.2f}%, 거래량 {chosen.get('tickVolumeSurge', 0):.1f}x. "
                        "목표가와 손절가를 잡고 진입합니다."
                    )
                    log_trade(
                        f"[Scalping Signal] {bot_state.active_ticker} / "
                        f"1m +{chosen.get('minute1Momentum', 0) * 100:.2f}% / "
                        f"3m +{chosen.get('minute3Momentum', 0) * 100:.2f}% / "
                        f"거래량 {chosen.get('tickVolumeSurge', 0):.1f}x / "
                        f"24h +{chosen['momentum'] * 100:.2f}%"
                    )

                bot_state.state = TradingState.BUYING
                bot_state.decision_note = f"{bot_state.active_ticker} 매수 준비 중입니다. 투자금과 리스크 한도를 확인합니다."
                if bot_state.trading_mode == "real":
                    if bot_state.investment_mode == "rotate_holdings" and not bot_state.rotated_holdings:
                        await liquidate_existing_holdings()
                    await refresh_real_balances()
                    log_trade(f"[Real Balance] 사용 가능 KRW {bot_state.balance:,.0f}원")

                if bot_state.investment_mode in ["all_krw", "rotate_holdings"]:
                    invest_krw = bot_state.balance * 0.99
                elif bot_state.investment_mode == "fixed":
                    invest_krw = min(bot_state.investment_amount, bot_state.balance * 0.99)
                else:
                    invest_krw = bot_state.balance * bot_state.investment_ratio * 0.99

                if invest_krw < 5000:
                    bot_state.decision_note = "주문 가능 금액이 5,000원 미만이라 엔진을 정지합니다."
                    log_trade("[Risk Manager] 주문 가능 금액이 부족합니다. 최소 5,000원 이상으로 설정하세요.")
                    bot_state.state = TradingState.ERROR
                    break

                if bot_state.trading_mode == "real":
                    before_qty = get_real_balance(ticker_currency(bot_state.active_ticker))
                    bot_state.decision_note = f"{bot_state.active_ticker} 실매수 요청 중입니다. 주문 결과를 확인합니다."
                    log_trade(f"[Real Buy Request] {bot_state.active_ticker} 시장가 매수 요청: {invest_krw:,.0f}원")
                    result = await asyncio.to_thread(bot_state.upbit.buy_market_order, bot_state.active_ticker, invest_krw)
                    if not result or (isinstance(result, dict) and result.get("error")):
                        log_trade(f"[Real Buy Error] 매수 주문 실패: {result}")
                        bot_state.state = TradingState.ERROR
                        break
                    remember_order(result, "BUY")
                    await asyncio.sleep(1)
                    await refresh_real_balances()
                    after_qty = get_real_balance(ticker_currency(bot_state.active_ticker))
                    bot_state.held_btc = max(after_qty - before_qty, 0)
                    if bot_state.held_btc <= 0:
                        log_trade("[Real Buy Error] 매수 요청 후 체결 수량을 확인하지 못했습니다. 업비트 주문 내역을 확인하세요.")
                        bot_state.state = TradingState.ERROR
                        break
                    bot_state.avg_buy_price = price
                    bot_state.entry_krw = invest_krw
                    bot_state.peak_yield = 1.0
                    bot_state.decision_note = f"{bot_state.active_ticker} 실매수 완료. 목표가 도달 또는 손절선 이탈 여부를 2초마다 확인합니다."
                    log_trade(f"[Real Entry] {bot_state.active_ticker} {invest_krw:,.0f}원 실매수 요청 완료. 기준가 {price:,.0f}원")
                else:
                    buy_qty = invest_krw / price
                    bot_state.held_btc = buy_qty * 0.9995
                    bot_state.avg_buy_price = price
                    bot_state.entry_krw = invest_krw
                    bot_state.peak_yield = 1.0
                    bot_state.balance -= invest_krw
                    bot_state.decision_note = f"{bot_state.active_ticker} 체험 진입 완료. 목표가 도달 또는 손절선 이탈 여부를 2초마다 확인합니다."
                    log_trade(f"[Strategy Entry] {bot_state.active_ticker} {invest_krw:,.0f}원 진입. 체결가 {price:,.0f}원")
                bot_state.state = TradingState.HOLDING

            elif bot_state.state == TradingState.HOLDING:
                current_yield = price / bot_state.avg_buy_price if bot_state.avg_buy_price else 1.0
                if current_yield > bot_state.peak_yield:
                    bot_state.peak_yield = current_yield
                trailing_ready = bot_state.exit_mode == "trailing" and bot_state.peak_yield >= bot_state.trailing_start_yield
                trailing_exit_yield = bot_state.peak_yield - bot_state.trailing_drop_pct
                should_take_profit = current_yield >= bot_state.target_yield
                if bot_state.exit_mode == "trailing":
                    should_take_profit = trailing_ready and current_yield <= trailing_exit_yield
                    bot_state.decision_note = (
                        f"{bot_state.active_ticker} 추적 익절 감시 중: 현재 {(current_yield - 1.0) * 100:.3f}%, "
                        f"최고 {(bot_state.peak_yield - 1.0) * 100:.3f}%, 익절 발동선 {(trailing_exit_yield - 1.0) * 100:.3f}%"
                    )
                else:
                    bot_state.decision_note = (
                        f"{bot_state.active_ticker} 보유 감시 중: 현재 {(current_yield - 1.0) * 100:.3f}%, "
                        f"목표 {(bot_state.target_yield - 1.0) * 100:.2f}%, 손절 {(bot_state.stop_loss_yield - 1.0) * 100:.2f}%"
                    )
                if bot_state.trading_mode == "practice" and current_yield < 1.003:
                    replacement = await asyncio.to_thread(scan_upbit_candidates, 1)
                    if replacement and replacement[0]["ticker"] != bot_state.active_ticker and replacement[0]["score"] > 0.55:
                        sell_amount = (bot_state.held_btc * price) * 0.9995
                        bot_state.balance += sell_amount
                        old_ticker = bot_state.active_ticker
                        bot_state.held_btc = 0
                        bot_state.avg_buy_price = 0
                        bot_state.entry_krw = 0
                        bot_state.peak_yield = 1.0
                        bot_state.state = TradingState.IDLE
                        bot_state.decision_note = f"{old_ticker}보다 강한 후보가 보여 교체 대기합니다."
                        log_trade(f"[Rotation] {old_ticker} 힘이 약해 더 강한 후보 {replacement[0]['ticker']}로 교체 대기")
                        await asyncio.sleep(1)
                        continue
                if should_take_profit:
                    bot_state.state = TradingState.SELLING
                    profit_pct = (current_yield - 1.0) * 100
                    if bot_state.exit_mode == "trailing":
                        peak_pct = (bot_state.peak_yield - 1.0) * 100
                        bot_state.decision_note = f"추적 익절 발동. 최고 +{peak_pct:.2f}%에서 현재 +{profit_pct:.2f}%로 밀려 전량 매도 후 엔진을 종료합니다."
                    else:
                        bot_state.decision_note = f"목표 수익률 +{profit_pct:.2f}% 도달. 전량 매도 후 엔진을 종료합니다."
                    if bot_state.trading_mode == "real":
                        sell_qty = bot_state.held_btc
                        if sell_qty <= 0:
                            log_trade("[Real Sell Error] 매도 가능한 보유 수량이 없습니다. 엔진을 정지합니다.")
                            bot_state.state = TradingState.ERROR
                            break
                        result = await asyncio.to_thread(bot_state.upbit.sell_market_order, bot_state.active_ticker, sell_qty)
                        if not result or (isinstance(result, dict) and result.get("error")):
                            log_trade(f"[Real Sell Error] 매도 주문 실패: {result}")
                            bot_state.state = TradingState.ERROR
                            break
                        remember_order(result, "SELL")
                        await asyncio.sleep(1)
                        await refresh_real_balances()
                        bot_state.held_btc = 0
                        log_trade(f"[Real Take Profit] {bot_state.active_ticker} 목표 수익률 도달 +{profit_pct:.2f}%. 실매도 후 엔진 종료.")
                    else:
                        sell_amount = (bot_state.held_btc * price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        log_trade(f"[Take Profit] {bot_state.active_ticker} 목표 수익률 도달 +{profit_pct:.2f}%. 자동 매도 후 엔진 종료.")
                    bot_state.avg_buy_price = 0
                    bot_state.entry_krw = 0
                    bot_state.peak_yield = 1.0
                    bot_state.consecutive_loss_count = 0
                    bot_state.state = TradingState.STOPPED
                    send_push_notification("목표 수익률 도달", f"{bot_state.active_ticker} +{profit_pct:.2f}% 달성. 엔진을 종료했습니다.")

                elif current_yield <= bot_state.stop_loss_yield:
                    bot_state.state = TradingState.SELLING
                    loss_pct = (1.0 - current_yield) * 100
                    bot_state.decision_note = f"손절선 -{loss_pct:.2f}% 도달. 전량 매도 후 다시 기회를 찾습니다."
                    if bot_state.trading_mode == "real":
                        sell_qty = bot_state.held_btc
                        if sell_qty <= 0:
                            log_trade("[Real Stop Error] 손절 매도 가능한 보유 수량이 없습니다. 엔진을 정지합니다.")
                            bot_state.state = TradingState.ERROR
                            break
                        result = await asyncio.to_thread(bot_state.upbit.sell_market_order, bot_state.active_ticker, sell_qty)
                        if not result or (isinstance(result, dict) and result.get("error")):
                            log_trade(f"[Real Stop Error] 손절 주문 실패: {result}")
                            bot_state.state = TradingState.ERROR
                            break
                        remember_order(result, "STOP SELL")
                        await asyncio.sleep(1)
                        await refresh_real_balances()
                        bot_state.held_btc = 0
                        log_trade(f"[Real Stop Loss] {bot_state.active_ticker} -{loss_pct:.2f}%. 실매도 후 엔진을 완전 정지합니다.")
                    else:
                        sell_amount = (bot_state.held_btc * price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        log_trade(f"[Stop Loss] {bot_state.active_ticker} -{loss_pct:.2f}%. 손절 후 대기 상태로 복귀.")
                    bot_state.avg_buy_price = 0
                    bot_state.entry_krw = 0
                    bot_state.peak_yield = 1.0
                    bot_state.consecutive_loss_count += 1
                    if bot_state.trading_mode == "real":
                        bot_state.state = TradingState.STOPPED
                        bot_state.decision_note = "손절 매도 후 실거래 엔진을 완전 정지했습니다. 다시 시작하려면 사용자가 직접 실거래 시작을 눌러야 합니다."
                        send_push_notification("Zenthex Trading 손절 정지", f"{bot_state.active_ticker} -{loss_pct:.2f}% 손절 후 엔진을 정지했습니다.")
                    else:
                        bot_state.state = TradingState.IDLE

        except Exception as e:
            bot_state.decision_note = f"시스템 오류로 엔진이 멈췄습니다: {e}"
            log_trade(f"[System Error] {e}")
            bot_state.state = TradingState.ERROR

        await asyncio.sleep(2)
