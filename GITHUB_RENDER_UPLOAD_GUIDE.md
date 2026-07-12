# Zenthex GitHub + Render Upload Guide

## What GitHub should contain

The GitHub repository that Render deploys must contain these files in the same app root:

```text
main.py
requirements.txt
render.yaml
Procfile
runtime.txt
static/
auth/
studio/
trading/
stock/
database/
billing/
admin/
support/
mobile/
legal/
security/
```

## What requirements.txt must contain

`requirements.txt` must contain only Python package names:

```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pydantic
pydantic[email]
email-validator
passlib
pyupbit
google-generativeai
google-genai
opencv-python-headless
numpy
cryptography
slowapi
python-multipart
aiofiles
trimesh
```

Do not paste environment variables, master plan text, launch review text, or checklists into `requirements.txt`.

## What goes into Render Environment Variables

These values belong in Render Settings -> Environment:

```text
ZENTHEX_OWNER_EMAILS=7foliath@naver.com
ZENTHEX_DATABASE_URL=sqlite:///./zenthex.db
ZENTHEX_SERVER_PUBLIC_IP=74.220.52.254
GEMINI_API_KEY=
ZENTHEX_GOOGLE_AI_STUDIO_MODEL=gemini-3.1-flash-image
ZENTHEX_ENABLE_DEV_OUTBOX=false
ZENTHEX_ENABLE_MOCK_PAYMENT=false
```

Real API keys, SMTP passwords, payment keys, and exchange keys must not be committed to GitHub.

## Render settings

Use these values:

```text
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT

Health Check Path:
/api/health
```

Root Directory:

```text
Blank: when main.py is visible at the GitHub repository root.
zenthex-saas-upload: when main.py is inside a zenthex-saas-upload folder.
```

## Current product direction to preserve

- Zenthex Studio: Google AI Studio/Gemini based architecture and 3D visualization path.
- Zenthex Trading: Upbit, Bithumb, and future Binance strategy engine with risk controls.
- Zenthex Stock: future stock strategy line for long-term/value/growth/catalyst review.
- Owner email: `7foliath@naver.com`.
- Fixed displayed server IP basis: `74.220.52.254`.
- Trading and Stock must never promise guaranteed profit.
