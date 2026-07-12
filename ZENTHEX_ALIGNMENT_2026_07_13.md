# Zenthex Alignment 2026-07-13

This document records the current direction without replacing the existing master plan.

## 1. Fixed Company Direction

Zenthex remains one SaaS company with three product lines:

- Zenthex Studio
- Zenthex Trading
- Zenthex Stock

The product direction must not jump randomly from one request to another. New requests are treated as refinements to the master plan, not as a reset.

## 2. Zenthex Studio

Current goal:

- Show an immediate architecture-style result from user prompts or uploaded floor-plan images.
- Use Google AI Studio / Gemini / Nano Banana image generation as the first practical result source.
- Treat real GLB/OBJ 3D model generation as the later 3D Worker stage.

Current implementation direction:

- `GEMINI_API_KEY` or `GOOGLE_API_KEY` must be configured on the server.
- Studio tries the Gemini Interactions image API first.
- If that fails, Studio falls back to the older Gemini content-generation path.
- If no API key exists, Studio falls back to the built-in preview and clearly explains that the real AI image provider is not configured.

Official API basis checked:

- Google documents Nano Banana as Gemini native image generation.
- `gemini-3.1-flash-image` is the default Zenthex image model for this build.

## 3. Zenthex Trading

Trading must never promise guaranteed profit. The correct product language is:

> Zenthex Trading is a risk-managed auto-trading tool designed to seek profit opportunities from rising-confirmation signals. It is not investment advice and does not guarantee profit.

Strategy direction:

- Scan KRW crypto markets.
- Avoid falling coins.
- Enter only when 24h/6h trend, 1m/3m/5m momentum, volume, orderbook, and market guard agree.
- Stay in a coin while it keeps rising.
- Sell when target profit is reached.
- In trailing mode, keep holding while profit expands, then sell when profit falls from the peak.
- After a small profit is reached, move the protection line close to breakeven to reduce profit turning into loss.
- After take-profit, optionally restart scanning automatically.
- If a position loses strength, exit and search for a stronger candidate.

Current reinforcement:

- Profit protection now activates earlier by default.
- Default trailing protection is tighter.
- Exit explanations now say that the engine protects profit after roughly +0.15% instead of waiting for a larger move.

Risk controls that must remain:

- No guaranteed-profit wording.
- Daily loss limit.
- Consecutive stop-loss limit.
- Stop-loss cooldown per coin.
- CEO kill switch.
- Real trading requires login and Trading Pro or Ultimate.
- API keys must use no withdrawal permission.

## 4. Zenthex Stock

Stock is the third product line, not a replacement for Trading.

Stock must be split into two strategies:

### Day Stock

- Korea and US market-hours aware.
- Designed for intraday opportunities.
- Uses market guard, volume expansion, trend, VWAP/MA, and catalyst checks.
- Must close or force-review before market close.

### Long Stock

- Future-oriented long/swing strategy.
- Looks for stocks with one-month or longer uptrend potential.
- Uses earnings improvement, sector growth, valuation discount, institutional/foreign flow, and catalyst checks.
- Holds while the thesis remains valid.
- Exits when the thesis breaks, trend fails, valuation becomes excessive, or risk rules trigger.

Current implementation status:

- Stock page and API show the Korea/US, day/long direction.
- Live stock orders remain disabled.
- Paper Trading, market-hours scheduler, broker connector, and stock risk disclosure must be completed before live stock orders.

## 5. Deployment Direction

GitHub stores code. Render runs the FastAPI server.

GitHub uploads must not erase:

- `requirements.txt` package list
- `render.yaml`
- `main.py`
- Studio / Trading / Stock routes
- Owner email `7foliath@naver.com`
- Fixed displayed IP basis `74.220.52.254`
- Risk disclosure

Environment variables such as `GEMINI_API_KEY`, database URL, SMTP keys, payment keys, and future broker keys belong in Render environment variables, not in GitHub files.
