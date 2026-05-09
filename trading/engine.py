import time
import asyncio
import pyupbit
from pydantic import BaseModel
from mobile.push import send_push_notification
from admin.router import admin_state

# 주문 상태 머신 (IDLE, BUYING, HOLDING, SELLING, ERROR, STOPPED)
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
        self.upbit = None
        
        # 잔고 및 포지션
        self.balance = 10000.0  # 모의 초기자본
        self.held_btc = 0.0
        self.avg_buy_price = 0.0
        
        # 설정값
        self.target_yield = 1.01
        self.investment_mode = "fixed" # "fixed" or "ratio"
        self.investment_amount = 50000.0 # 고정일 때 쓸 금액
        self.investment_ratio = 0.5 # 비율일 때 쓸 비율 (50%)
        
        # 리스크 매니저
        self.daily_max_loss_pct = 0.05 # 1일 최대 손실 허용 (5%)
        self.consecutive_loss_count = 0 
        self.max_consecutive_loss = 3
        self.initial_daily_balance = self.balance
        
        self.logs = ["[System] 트레이딩 터미널 대기중 (모듈화 완료)..."]

bot_state = BotState()

def log_trade(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    bot_state.logs.append(full_msg)
    if len(bot_state.logs) > 50:
        bot_state.logs.pop(0)

# 핵심 엔진 스캘핑 루프
async def scalping_loop():
    log_trade("실시간 시세 감시 및 리스크매니저 기반 단타 엔진(5초 주기) 시작...")
    bot_state.state = TradingState.IDLE
    bot_state.initial_daily_balance = bot_state.balance
    
    while bot_state.state not in [TradingState.ERROR, TradingState.STOPPED]:
        try:
            # === GLOBAL KILL SWITCH CHECK ===
            if admin_state.global_kill_switch:
                log_trade("⚠️ [SYSTEM] Admin Kill Switch 활성화 중. 모든 트레이딩 동작 강제 대기 (신규 매수/매도 금지, 포지션 유지)")
                await asyncio.sleep(5)
                continue
            
            current_price = pyupbit.get_current_price("KRW-BTC")
            if current_price is None:
                await asyncio.sleep(5)
                continue
                
            # 리스크 매니저 - 일일 손실률 체크
            est_total = bot_state.balance + (bot_state.held_btc * current_price)
            if est_total < bot_state.initial_daily_balance * (1.0 - bot_state.daily_max_loss_pct):
                log_trade(f"🚨 [리스크 매니저] 일일 최대 손실 한도 도달! 즉시 시스템 강제 종료.")
                send_push_notification("로스컷 조기 종료", "일일 최대 손실 한도 도달로 봇이 정지되었습니다.")
                bot_state.state = TradingState.ERROR
                break
                
            if bot_state.consecutive_loss_count >= bot_state.max_consecutive_loss:
                 log_trade(f"🚨 [리스크 매니저] 연속 손절 횟수 초과! 매매 강제 중단.")
                 send_push_notification("연속 손절 제한 도달", "연속 손절 설정치에 도달하여 시스템이 강제 중단되었습니다.")
                 bot_state.state = TradingState.ERROR
                 break

            if bot_state.state == TradingState.IDLE and bot_state.held_btc == 0:
                # BUY LOGIC
                if time.time() % 30 < 5:  # Trigger condition (Demo fast trigger)
                    bot_state.state = TradingState.BUYING
                    
                    # 투자금 계산 (고정 금액 vs 비율)
                    invest_krw = 0.0
                    if bot_state.investment_mode == "fixed":
                        invest_krw = min(bot_state.investment_amount, bot_state.balance * 0.99)
                    else:
                        invest_krw = bot_state.balance * bot_state.investment_ratio * 0.99

                    if bot_state.is_real_key:
                        res = bot_state.upbit.buy_market_order("KRW-BTC", invest_krw)
                        if res and 'error' not in res:
                            await asyncio.sleep(1)
                            bot_state.held_btc = bot_state.upbit.get_balance("BTC")
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.avg_buy_price = current_price
                            bot_state.state = TradingState.HOLDING
                            log_trade(f"🔥 [실거래 자동매수] {invest_krw:,}원 진입 완료 (체결가: {current_price:,}원)")
                        else:
                            log_trade(f"❌ [에러] 실거래 매수 실패: {res}")
                            bot_state.state = TradingState.IDLE
                    else:
                        buy_qty = invest_krw / current_price
                        bot_state.held_btc = buy_qty * 0.9995
                        bot_state.avg_buy_price = current_price
                        bot_state.balance -= invest_krw
                        bot_state.state = TradingState.HOLDING
                        log_trade(f"🟢 [모의 자동매수] {invest_krw:,.0f}원 진입 완료. (체결가: {current_price:,}원)")

            elif bot_state.state == TradingState.HOLDING:
                # SELL LOGIC
                current_yield = current_price / bot_state.avg_buy_price
                if current_yield >= bot_state.target_yield:
                    bot_state.state = TradingState.SELLING
                    if bot_state.is_real_key:
                        res = bot_state.upbit.sell_market_order("KRW-BTC", bot_state.held_btc)
                        if res and 'error' not in res:
                            await asyncio.sleep(1)
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.held_btc = 0.0
                            bot_state.avg_buy_price = 0
                            profit_pct = (current_yield - 1.0) * 100
                            bot_state.consecutive_loss_count = 0 # reset
                            bot_state.state = TradingState.IDLE
                            log_trade(f"🔥 [실거래 자동 익절] 목표 수익률 달성 (+{profit_pct:.2f}%).")
                            
                            # 엔진 자동 종료 (요구사항)
                            bot_state.state = TradingState.STOPPED
                            log_trade(f"🔔 [PUSH 알림] 익절 완료 및 엔진 자동 종료.")
                            send_push_notification("수익 실현 완료", f"목표 수익 달성. (+{profit_pct:.2f}%) 엔진가동 중단.")
                        else:
                             log_trade(f"❌ [에러] 실거래 익절 실패: {res}")
                             bot_state.state = TradingState.HOLDING
                    else:
                        sell_amount = (bot_state.held_btc * current_price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        bot_state.avg_buy_price = 0
                        profit_pct = (current_yield - 1.0) * 100
                        bot_state.consecutive_loss_count = 0
                        bot_state.state = TradingState.IDLE
                        log_trade(f"🔴 [모의 자동 익절] 목표 수익 도달 (+{profit_pct:.2f}%).")
                        
                        bot_state.state = TradingState.STOPPED
                        log_trade(f"🔔 [PUSH 알림] 모의 익절 완료 및 봇 종료.")
                        send_push_notification("모의투자 목표 달성", f"테스트 투자가 성공적으로 익절 되었습니다. (+{profit_pct:.2f}%)")

                elif current_yield <= 0.98: # Stop loss (2%)
                    bot_state.state = TradingState.SELLING
                    if bot_state.is_real_key:
                        res = bot_state.upbit.sell_market_order("KRW-BTC", bot_state.held_btc)
                        if res and 'error' not in res:
                            await asyncio.sleep(1)
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.held_btc = 0.0
                            bot_state.avg_buy_price = 0
                            loss_pct = (1.0 - current_yield) * 100
                            bot_state.consecutive_loss_count += 1
                            bot_state.state = TradingState.IDLE
                            log_trade(f"⚠️ [실거래 자동 손절] 하락 추세 감지 (-{loss_pct:.2f}%). 즉시 매도.")
                    else:
                        sell_amount = (bot_state.held_btc * current_price) * 0.9995
                        bot_state.balance += sell_amount
                        bot_state.held_btc = 0
                        bot_state.avg_buy_price = 0
                        loss_pct = (1.0 - current_yield) * 100
                        bot_state.consecutive_loss_count += 1
                        bot_state.state = TradingState.IDLE
                        log_trade(f"⚠️ [모의 자동 손절매] 하락(-{loss_pct:.2f}%). 즉시 매도. (연속손절: {bot_state.consecutive_loss_count})")

        except Exception as e:
            log_trade(f"🚨 네트워크/시스템 에러: {e}")
            bot_state.state = TradingState.ERROR
        
        await asyncio.sleep(5)
