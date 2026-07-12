# Render Deploy Check

If Render says the service is stopped or the build fails at `requirements.txt`, check these first.

## GitHub upload rule

Upload the files in this project folder as the app source. The file named `requirements.txt` must stay as the Python package list. Do not replace `requirements.txt` with `.env.example`, environment variables, launch review notes, or the master plan.

Environment values such as `ZENTHEX_OWNER_EMAILS`, `ZENTHEX_DATABASE_URL`, `ZENTHEX_SERVER_PUBLIC_IP`, `GEMINI_API_KEY`, and SMTP/payment keys belong in Render's Environment Variables screen, not in `requirements.txt`.

## Correct requirements.txt

The first lines must be package names, not a design document:

```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pydantic
```

If line 3 contains Korean documentation text such as a launch review, the wrong file was uploaded as `requirements.txt`.

## Correct Render settings

- Root Directory: leave empty if `main.py` and `requirements.txt` are at the repository root.
- Root Directory: set to `zenthex-saas-upload` only if the whole folder was uploaded as a subfolder.
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`

## Important

GitHub Pages can show static files only. It cannot run FastAPI, login APIs, Studio generation APIs, Trading APIs, or Stock APIs. Render or another Python server must run the backend.

The current Zenthex direction remains:

- Studio: AI architecture and 3D visualization
- Trading: crypto strategy engine that avoids falling coins and uses target profit, stop loss, and risk controls
- Stock: long-term stock strategy line using valuation, growth, catalysts, earnings improvement, and trend checks

Do not remove:

- owner email fallback: `7foliath@naver.com`
- Studio / Trading / Stock homepage structure
- Trading Pro and Studio Pro permission separation
- fixed server IP display value: `74.220.52.254`
- risk disclosure that Trading and Stock do not guarantee profit
