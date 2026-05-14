# Zenthex SaaS

Zenthex is an AI SaaS platform with Zenthex Studio and Zenthex Trading.

## Features

- Zenthex Studio: prompt and 2D drawing to AI 3D workspace
- Studio trial: anonymous users get 1 generation per IP per day
- Studio preview protection: trial/free users receive view-only previews without download URLs
- Zenthex Trading: risk-managed strategy experience and Signal Guard
- Upbit: live market scan, strategy experience, and gated real trading
- Binance: next exchange integration target, gated the same way as Upbit for real orders
- Owner dashboard for the email configured in `ZENTHEX_OWNER_EMAILS`
- Email verification, ID lookup, password reset
- My Page with billing history and receipt print view
- SMTP mail delivery through environment variables
- Protected dev outbox and mock payment controls for safer public uploads

## Trading Direction

Current production test target is Upbit because KRW markets and all listed coin scanning are already wired into the experience. Binance should be added as the next connector with the same safety structure:

- Public: exchange status, market scan preview, strategy explanation
- Paid: real trading, API key registration, order execution
- Required safety: order-only API key, withdrawal permission disabled, risk agreement, owner kill switch
- First Binance scope: spot trading only, small order tests, no futures until risk controls are proven

## Signal Guard Formula

The trading experience does not promise profit. It uses 24h strength as a broad filter, then ranks short-term scalping signals:

- 24h price change
- recent 6h momentum
- 24h traded value
- 1m / 3m / 5m momentum
- short-term volume surge
- short-term breakout
- 1m moving-average trend
- volatility filter
- drawdown from 24h high

Default scalping targets should be small, such as +0.3% to +1.0%, with a tight stop loss around -0.6%. Practice mode can rotate away from weak candidates into stronger candidates. Real rotation should require a separate opt-in because it can sell assets from a user's account.

## Run Locally

```powershell
pip install -r requirements.txt
python main.py
```

Open:

```text
http://127.0.0.1:8080/
```

## Environment

Copy `.env.example` to `.env` locally and fill SMTP values. Do not commit `.env`.
For production, set `ZENTHEX_OWNER_EMAILS` in the server environment to the CEO email address.

```env
ZENTHEX_OWNER_EMAILS=owner@example.com
ZENTHEX_SMTP_HOST=smtp.example.com
ZENTHEX_SMTP_PORT=587
ZENTHEX_SMTP_SSL=false
ZENTHEX_SMTP_USER=no-reply@example.com
ZENTHEX_SMTP_PASSWORD=change-me
ZENTHEX_SMTP_FROM="Zenthex <no-reply@example.com>"
ZENTHEX_ENABLE_DEV_OUTBOX=false
ZENTHEX_ENABLE_MOCK_PAYMENT=false
```

## Do Not Commit

- `.env`
- `zenthex.db`
- `uploads/`
- `__pycache__/`
- generated model files in `static/models/`
