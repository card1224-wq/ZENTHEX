# Zenthex SaaS

Zenthex is an AI SaaS platform with Zenthex Studio and Zenthex Trading.

## Features

- Zenthex Studio: prompt and 2D drawing to AI 3D workspace
- Zenthex Trading: risk-managed strategy experience and Signal Guard
- Owner dashboard for `7foliath@naver.com`
- Email verification, ID lookup, password reset
- My Page with billing history and receipt print view
- SMTP mail delivery through environment variables

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

```env
ZENTHEX_OWNER_EMAILS=7foliath@naver.com
ZENTHEX_SMTP_HOST=smtp.example.com
ZENTHEX_SMTP_PORT=587
ZENTHEX_SMTP_SSL=false
ZENTHEX_SMTP_USER=no-reply@example.com
ZENTHEX_SMTP_PASSWORD=change-me
ZENTHEX_SMTP_FROM="Zenthex <no-reply@example.com>"
```

## Do Not Commit

- `.env`
- `zenthex.db`
- `uploads/`
- `__pycache__/`
- generated model files in `static/models/`
