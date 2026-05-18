# Zenthex SaaS

Zenthex is an AI SaaS platform with Zenthex Studio and Zenthex Trading.

## Features

- Zenthex Studio: prompt and 2D drawing to AI 3D workspace
- Studio NanoBanana/Gemini image generation appears as the main result; true GLB/OBJ output is the later 3D Worker server stage
- Studio trial: anonymous users get 1 generation per IP per day
- Studio preview protection: trial/free users receive view-only previews without download URLs
- Zenthex Trading: risk-managed strategy experience and Signal Guard
- Trading split entry: divide a configured total budget into multiple entries and calculate take-profit/stop-loss from the average buy price
- Trading stop controls: pause keeps holdings, while sell-and-stop market-sells the current Zenthex position before ending the engine
- Upbit: live market scan, strategy experience, and gated real trading
- Binance: next exchange integration target, gated the same way as Upbit for real orders
- Owner dashboard for the email configured in `ZENTHEX_OWNER_EMAILS`
- Email verification, phone verification, ID lookup, password reset
- My Page with billing history and receipt print view
- SMTP mail delivery through environment variables
- Protected dev outbox and mock payment controls for safer public uploads
- Owner launch review system in the CEO dashboard
- Owner subscriber management: view accounts, change plan/role, and delete duplicate accounts
- Customer inquiry system: users can submit support tickets and the owner can manage status/replies in the CEO dashboard
- Owner account receives Ultimate access without payment, but still needs email code verification

Login tokens are signed so new logins continue to work after a server restart or redeploy. If an older browser token is still present from a previous build, Studio clears it and retries as a one-day trial instead of blocking the prompt flow with an invalid-token error. Real trading still requires a fresh valid login because it can place real orders.

Accounts are stored in the database, not in the static GitHub files. If the deployment starts with a new empty `zenthex.db`, an old browser login token can remain while the matching account no longer exists on the server. In that case the app now clears stale sessions and the login screen shows whether the email does not exist or the password is wrong. Production should use a persistent database through `ZENTHEX_DATABASE_URL`.

For paid launch, the deployment rule is: GitHub updates application code only; user accounts, passwords, subscriptions, receipts, Studio jobs, Trading settings, and encrypted API-key records stay in the persistent production database. Do not rely on a newly created server-local SQLite file after real users or payments exist.

Subscriptions should be monthly auto-renewal. Recommended providers are Toss Payments billing-key auto-payment for Korea and Stripe subscriptions for overseas cards. Payment webhooks should update subscription status, next billing date, failed-payment grace periods, cancellations, refunds, and receipt history.

The code supports PostgreSQL through `ZENTHEX_DATABASE_URL` and includes the PostgreSQL driver in `requirements.txt`. SQLite-only compatibility migrations are skipped automatically when PostgreSQL is used. See `PRODUCTION_DATABASE.md` for the production database checklist.

Cost review is part of the CEO launch gate. The project can stay low-cost during validation, but paid launch needs budget planning for database, hosting, storage, Studio AI/GPU work, email/SMS, monitoring, and payment fees. The current end-to-end architecture is summarized in `ZENTHEX_MASTER_PLAN.md`.

Studio and Trading refresh the current account on page load. Owner and paid users see full-access language inside the product screens according to their plan, while free or anonymous users see trial/subscription guidance. Product headers use Zenthex branding consistently.

The homepage hero stays as a public Zenthex brand introduction for every visitor, including the owner account. Owner operations are exposed through dashboard links and owner-only cards, not by replacing the main brand headline.

Owner and subscriber workspaces are separated. Subscribers use My Page for their own subscription, receipts, Studio, Trading, and support. The owner uses CEO Dashboard for user approval, plan changes, support management, launch review, emergency stop, and operational checks. Owner-only metrics or controls must not appear in subscriber screens.

Logged-in users see My Page, Customer Center, and Logout in the homepage navigation. The owner also sees CEO Dashboard. Logged-in users should not see only the anonymous Login/Trial navigation.

Role separation:

- Owner: can access CEO dashboard, subscriber management, launch review, emergency stop, Studio, and Trading without payment.
- Studio Pro: can use Studio generation/export features only.
- Trading Pro: can use Trading real-mode features only.
- Ultimate: can use Studio and Trading, but not CEO operations.
- Free or anonymous users: can access limited trial/structure views only.

## Account Verification

Signup collects name, email, password confirmation, birth date, phone number, and password hint question/answer. Phone verification is required before a normal user can complete signup. If SMS provider keys are not configured, the test build uses the fixed verification code `122492` so testing is not blocked. A production SMS provider such as Naver Cloud SENS, Aligo, or Twilio should be connected before public launch.

Normal users enter an owner-approval pending state after signup. The owner reviews identity details in the CEO dashboard and changes the account to approved before the user can log in and use paid services. The owner email remains automatically approved.

## Launch Review

The CEO dashboard includes a "출시 전 검토" panel. It checks core release risks such as owner account exposure, signup fields, phone verification, Studio trial lock, Trading real-trade lock, mock payment protection, and required database columns.

Detailed review criteria are in `PROJECT_REVIEW.md`.

The full representative master plan is in `ZENTHEX_MASTER_PLAN.md`.

## Customer Center

The Customer Center is not only an information page. Users can submit account, billing, Studio, Trading, Upbit, or general inquiries through `/customer.html`. Logged-in users can also view their own recent tickets. The owner can review incoming tickets, change status, and leave an internal reply from `/admin.html`.

## Trading Direction

Current production test target is Upbit because KRW markets and all listed coin scanning are already wired into the experience. Binance should be added as the next connector with the same safety structure:

- Public: exchange status, market scan preview, strategy explanation
- Paid: real trading, API key registration, order execution
- Required safety: order-only API key, withdrawal permission disabled, risk agreement, owner kill switch
- First Binance scope: spot trading only, small order tests, no futures until risk controls are proven

Upbit real-trading keys require asset lookup and order permissions, and the public IP address of the running Zenthex FastAPI server must be registered on the Upbit Open API key. GitHub Pages is not the trading server; it only serves static files. If authentication fails, the UI returns a more specific diagnostic for likely IP, permission, Access Key, or Secret Key problems. The Trading screen shows the configured Zenthex server IP from `ZENTHEX_SERVER_PUBLIC_IP`, or auto-detects the FastAPI server outbound IP through `api.ipify.org` when the environment value is empty. It includes "업비트 키 진단하기" for troubleshooting and "업비트 키 인증하기" for the live-trading gate. Secret Key is hidden by default, with a temporary view button for paste checks. The backend re-checks the key again when the real engine starts.

For real paid trading, the outbound IP should be fixed. Zenthex currently uses `74.220.52.254` as the intended fixed server IP value. The production server must actually route outbound Upbit requests through this same IP, and `ZENTHEX_SERVER_PUBLIC_IP=74.220.52.254` must be set in the server environment. If the displayed IP keeps changing, the deployment likely has no fixed outbound IP or the app is auto-detecting the current egress IP. Auto-detected IP is shown as a warning/reference only.

The Trading screen includes an outbound-IP verification check. It compares `ZENTHEX_SERVER_PUBLIC_IP` with the actual public IP seen from the FastAPI server. If the two values differ, do not treat the deployment as ready for Upbit live trading.

The Trading page keeps the long strategy form readable with a compact top summary for exit mode, target yield, capital mode, and coin selection. It also plots the latest Upbit balance/status `totalPnlPct` as a return-rate chart, so the user can watch profit movement instead of only reading current holdings.

Studio exports use two formats: GLB is the real 3D model file for 3D viewers/tools, while JPG is a flat image of the current preview screen. Owner, Studio Pro, and Ultimate users can use both export paths.

Studio prompt previews can use Gemini NanoBanana when `GEMINI_API_KEY` is configured. The immediate image preview uses `gemini-2.5-flash-image` by default through `ZENTHEX_NANOBANANA_MODEL`, then the local Three.js preview and optional GLB worker continue as the 3D layer. If no key is configured, the app falls back to the built-in visual preview instead of failing.

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

High-risk target options such as +10%, +30%, and +50% are available in the UI, but they are not normal scalping targets. They can keep the engine holding much longer and can expose the user to larger loss swings.

Investment modes:

- KRW cash all-in: uses only the available KRW cash balance in the Upbit account. If the account already holds coins and KRW cash is low, this mode may stop because there is not enough orderable KRW.
- KRW cash ratio: uses a percentage of available KRW cash. For example, 50% of 1,000,000 KRW means about 500,000 KRW is used.
- Fixed amount: uses a fixed KRW amount.
- Existing-holdings rotation: high-risk explicit mode that first sells KRW-market coins already held in the Upbit account, then uses the resulting KRW for a new entry. It requires a separate checkbox and confirmation.

Selling coins already held in the account and rotating that money into another coin is never the default. It is a separate explicit opt-in feature because it can realize losses and change the user's existing portfolio.

For real trading, the scanner runs outside the main API loop so the page can keep showing status while Upbit markets are being checked. The engine also tracks only the quantity bought by the current Zenthex run, so unrelated coins already held in the account are not sold by default.

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
For production, set `ZENTHEX_OWNER_EMAILS` in the server environment to the CEO email address. The current CEO email is `7foliath@naver.com`.

```env
ZENTHEX_OWNER_EMAILS=7foliath@naver.com
ZENTHEX_DATABASE_URL=sqlite:///./zenthex.db
ZENTHEX_SERVER_PUBLIC_IP=74.220.52.254
GEMINI_API_KEY=
ZENTHEX_NANOBANANA_MODEL=gemini-2.5-flash-image
ZENTHEX_SMTP_HOST=smtp.example.com
ZENTHEX_SMTP_PORT=587
ZENTHEX_SMTP_SSL=false
ZENTHEX_SMTP_USER=no-reply@example.com
ZENTHEX_SMTP_PASSWORD=change-me
ZENTHEX_SMTP_FROM="Zenthex <no-reply@example.com>"
ZENTHEX_ENABLE_DEV_OUTBOX=false
ZENTHEX_ENABLE_MOCK_PAYMENT=false
ZENTHEX_PAYMENT_PROVIDER=
ZENTHEX_TOSS_SECRET_KEY=
ZENTHEX_STRIPE_SECRET_KEY=
ZENTHEX_PAYMENT_WEBHOOK_SECRET=

# Future SMS provider values
ZENTHEX_SMS_PROVIDER=
ZENTHEX_SMS_ACCESS_KEY=
ZENTHEX_SMS_SECRET_KEY=
ZENTHEX_SMS_FROM=
```

## Do Not Commit

- `.env`
- `zenthex.db`
- `uploads/`
- `__pycache__/`
- generated model files in `static/models/`
