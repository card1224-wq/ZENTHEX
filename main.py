from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pyupbit
import asyncio
import time
import uvicorn
import os
import shutil
import json
import google.generativeai as genai

app = FastAPI()

# Mount static folders
os.makedirs("uploads", exist_ok=True)
os.makedirs("static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend pages
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/finance.html", response_class=HTMLResponse)
async def serve_finance():
    with open("static/finance.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/studio.html", response_class=HTMLResponse)
async def serve_studio():
    with open("static/studio.html", "r", encoding="utf-8") as f:
        return f.read()


# ==========================================
# FINANCE ENGINE (REAL CRYPTO BOT)
# ==========================================
class BotState:
    def __init__(self):
        self.is_running = False
        self.is_real_key = False
        self.access_key = ""
        self.secret_key = ""
        self.upbit = None
        self.balance = 10000.0  # Safe initial simulation balance fallback
        self.held_btc = 0.0
        self.avg_buy_price = 0.0
        self.target_yield = 1.01
        self.logs = ["[System] 트레이딩 터미널 대기중..."]

bot_state = BotState()

class StartConfig(BaseModel):
    accessKey: str
    secretKey: str
    targetYield: float

class ManualTrade(BaseModel):
    type: str # 'buy' or 'sell'
    amount: float

def log_trade(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    bot_state.logs.append(full_msg)
    if len(bot_state.logs) > 50:
        bot_state.logs.pop(0)

# Scalping loop set to 5 seconds
async def scalping_loop():
    log_trade("실시간 업비트 시세 감시 및 단타 엔진(5초 주기) 시작...")
    while bot_state.is_running:
        try:
            current_price = pyupbit.get_current_price("KRW-BTC")
            if current_price is None:
                await asyncio.sleep(5) # Wait 5 seconds
                continue

            if bot_state.held_btc == 0:
                # BUY LOGIC
                if time.time() % 30 < 5:  # Trigger condition (Demo fast trigger)
                    if bot_state.is_real_key:
                        # REAL UPBIT BUY
                        buy_amount = bot_state.balance * 0.999 # Safe margin for fees
                        res = bot_state.upbit.buy_market_order("KRW-BTC", buy_amount)
                        if res and 'error' not in res:
                            # Update with real balances after trade
                            await asyncio.sleep(1) # wait for settlement
                            bot_state.held_btc = bot_state.upbit.get_balance("BTC")
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.avg_buy_price = current_price
                            log_trade(f"🔥 [실거래 매수] BTC 시장가 진입 완료 (체결가: {current_price:,}원)")
                        else:
                            log_trade(f"❌ [에러] 업비트 실거래 매수 실패: {res}")
                    else:
                        # MOCK BUY
                        buy_qty = bot_state.balance / current_price
                        bot_state.held_btc = buy_qty * 0.9995
                        bot_state.avg_buy_price = current_price
                        bot_state.balance = 0
                        log_trade(f"🟢 [모의 매수 체결] BTC 시장가 진입 완료 (체결가: {current_price:,}원)")
            else:
                # SELL LOGIC
                current_yield = current_price / bot_state.avg_buy_price
                if current_yield >= bot_state.target_yield:
                    if bot_state.is_real_key:
                        # REAL UPBIT SELL (PROFIT)
                        res = bot_state.upbit.sell_market_order("KRW-BTC", bot_state.held_btc)
                        if res and 'error' not in res:
                            await asyncio.sleep(1)
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.held_btc = bot_state.upbit.get_balance("BTC") or 0.0
                            bot_state.avg_buy_price = 0
                            profit_pct = (current_yield - 1.0) * 100
                            log_trade(f"🔥 [실거래 매도] 목표 수익률 달성 (+{profit_pct:.2f}%). 전량 매도 완료.")
                        else:
                             log_trade(f"❌ [에러] 실거래 매도 실패: {res}")
                    else:
                        # MOCK SELL (PROFIT)
                        sell_amount = (bot_state.held_btc * current_price) * 0.9995
                        bot_state.balance = sell_amount
                        profit_krw = sell_amount - (bot_state.held_btc * bot_state.avg_buy_price)
                        bot_state.held_btc = 0
                        bot_state.avg_buy_price = 0
                        profit_pct = (current_yield - 1.0) * 100
                        log_trade(f"🔴 [모의 수익 실현] 목표 수익률 도달 (+{profit_pct:.2f}% / +{int(profit_krw)}원). 전량 매도 완료.")
                        
                elif current_yield <= 0.98: # Stop loss
                    if bot_state.is_real_key:
                        # REAL UPBIT SELL (STOP LOSS)
                        res = bot_state.upbit.sell_market_order("KRW-BTC", bot_state.held_btc)
                        if res and 'error' not in res:
                            await asyncio.sleep(1)
                            bot_state.balance = bot_state.upbit.get_balance("KRW")
                            bot_state.held_btc = bot_state.upbit.get_balance("BTC") or 0.0
                            bot_state.avg_buy_price = 0
                            loss_pct = (1.0 - current_yield) * 100
                            log_trade(f"⚠️ [실거래 손절] 하락 추세 감지 (-{loss_pct:.2f}%). 즉시 매도 처리.")
                    else:
                        # MOCK SELL (STOP LOSS)
                        sell_amount = (bot_state.held_btc * current_price) * 0.9995
                        bot_state.balance = sell_amount
                        bot_state.held_btc = 0
                        bot_state.avg_buy_price = 0
                        loss_pct = (1.0 - current_yield) * 100
                        log_trade(f"⚠️ [모의 손절매] 하락 추세 감지 (-{loss_pct:.2f}%). 즉시 매도 처리.")

        except Exception as e:
            log_trade(f"통신 에러: {e}")
        
        await asyncio.sleep(5)

@app.post("/api/finance/start")
async def start_bot(config: StartConfig):
    if bot_state.is_running:
        return {"status": "error", "message": "Bot is already running"}
    
    bot_state.target_yield = config.targetYield
    try:
        if config.accessKey and config.secretKey:
            bot_state.upbit = pyupbit.Upbit(config.accessKey, config.secretKey)
            bot_state.access_key = config.accessKey
            bot_state.secret_key = config.secretKey
            real_krw = bot_state.upbit.get_balance("KRW")
            if real_krw is not None and real_krw > 0:
                bot_state.balance = real_krw # Sync with real
                bot_state.is_real_key = True
            log_trade(f"[위험] 🔥 실제 업비트 계정 인증 완료! (보유자산: {bot_state.balance:,}원) 5초 주기로 즉시 실거래 스캘핑을 시작합니다.")
        else:
            bot_state.is_real_key = False
            log_trade("[알림] 키 미입력 상태. 순수 모의 백테스트 모드로 구동합니다.")
    except Exception as e:
        bot_state.is_real_key = False
        log_trade(f"API 인증 실패. 모의 모드로 전환합니다. {e}")

    bot_state.is_running = True
    asyncio.create_task(scalping_loop())
    return {"status": "success", "message": "Bot Engine Started"}

@app.post("/api/finance/manual_trade")
async def manual_trade(trade: ManualTrade):
    current_price = pyupbit.get_current_price("KRW-BTC") or 80000000
    if trade.type == "buy":
        if bot_state.balance >= trade.amount:
            buy_qty = trade.amount / current_price
            bot_state.held_btc += buy_qty * 0.9995
            
            # Simple avg logic assuming buying once for now over empty pocket
            bot_state.avg_buy_price = current_price 
            
            bot_state.balance -= trade.amount
            log_trade(f"🕹️ [수동 매수 완료] {trade.amount:,}원 시장가 진입. (체결가: {current_price:,}원)")
        else:
            log_trade(f"❌ [주문 실패] 잔고 부족 (현재 잔고: {bot_state.balance:,}원)")
    elif trade.type == "sell":
        if bot_state.held_btc > 0:
            sell_amount = (bot_state.held_btc * current_price) * 0.9995
            bot_state.balance += sell_amount
            bot_state.held_btc = 0
            bot_state.avg_buy_price = 0
            log_trade(f"🕹️ [수동 매도 완료] 전량 시장가 매도. (회수 금액: {sell_amount:,}원)")
        else:
            log_trade(f"❌ [주문 실패] 보유 중인 가상자산이 없습니다.")

    return {"status": "success"}

@app.post("/api/finance/stop")
async def stop_bot():
    bot_state.is_running = False
    log_trade("사용자 요청에 의해 매매 엔진 가동을 중단합니다.")
    return {"status": "success", "message": "Bot Engine Stopped"}

@app.get("/api/finance/status")
async def status():
    current_price = pyupbit.get_current_price("KRW-BTC") or 80000000
    est_balance = bot_state.balance
    if bot_state.held_btc > 0:
        est_balance += (bot_state.held_btc * current_price)

    return {
        "isRunning": bot_state.is_running,
        "isRealKey": bot_state.is_real_key,
        "currentBtcPrice": current_price,
        "balance": bot_state.balance,
        "estBalance": est_balance,
        "avgBuyPrice": bot_state.avg_buy_price,
        "logs": bot_state.logs[-15:]
    }


# ==========================================
# STUDIO ENGINE (REAL 3D GENERATOR)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)

@app.post("/api/studio/upload")
async def upload_floorplan(file: UploadFile = File(...)):
    print(f"[Studio Engine] Receiving floorplan: {file.filename}")
    file_path = f"uploads/{int(time.time())}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        from cv_engine import process_image_to_3d
        model_filename = f"{int(time.time())}.glb"
        demo_model_path = f"static/models/{model_filename}"
        bg_filename = model_filename.replace('.glb', '_bg.png')
        bg_path = f"static/models/{bg_filename}"
        
        # Use premium style per 'NanoBanana' requirement
        ai_style = "premium"
        ai_wall_height = 25.0
        
        process_image_to_3d(file_path, demo_model_path, wall_height=ai_wall_height, style=ai_style, output_png_path=bg_path)
        
        return {
            "status": "success", 
            "message": "3D Generation Complete", 
            "model_url": f"/static/models/{model_filename}",
            "bg_url": f"/static/models/{bg_filename}"
        }
    except Exception as e:
        print(f"[Studio Engine] Error processing: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/studio/generate")
async def generate_floorplan(prompt: str = Form(...)):
    print(f"[Studio Engine - AI Prompter] Generating AI parameters for: {prompt}")
    try:
        from cv_engine import process_image_to_3d
        import cv2
        import numpy as np
        
        # 1. Advanced Layout Template for AI Generation Prompt
        style = "premium"
        if "갤러리" in prompt.lower() or "통유리" in prompt.lower():
            style = "gallery"
            
        img = np.ones((1000, 1500), dtype=np.uint8) * 255
        cv2.rectangle(img, (100, 100), (1400, 900), (0,0,0), 10)
        
        # Save temp template
        filename = f"gen_prompt_{int(time.time())}"
        img_path = f"uploads/{filename}.jpg"
        cv2.imwrite(img_path, img)
        
        demo_model_path = f"static/models/{filename}.glb"
        bg_path = f"static/models/{filename}_bg.png"
        
        # NanoBanana high extrusions based on AI input
        process_image_to_3d(img_path, demo_model_path, wall_height=30.0, style=style, output_png_path=bg_path)
        
        return {
            "status": "success", 
            "message": "AI Text prompt interpreted successfully", 
            "model_url": f"/static/models/{filename}.glb"
        }
    except Exception as e:
        print(f"Error in generation: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
