# Zenthex Launch Review

This checklist is the master review gate before uploading or publishing Zenthex.

## Required

- Homepage shows one clear Zenthex brand experience, not a split demo screen.
- Homepage hero must always introduce Zenthex as a public brand, not change into "Zenthex Control" for the owner.
- Logged-in homepage navigation must show My Page, Customer Center, and Logout instead of only Login.
- Owner homepage actions must open Studio workspace, Trading engine, CEO dashboard, and My Page instead of trial-only actions.
- Customer Center must exist for account, subscription, Studio, Trading, and Upbit key guidance.
- No public page contains "demo" copy for the production-facing flow.
- Login and signup pages do not expose owner email or owner account guidance.
- Owner email is controlled by `ZENTHEX_OWNER_EMAILS`, with `7foliath@naver.com` kept as the built-in owner fallback.
- Owner account has Ultimate access without payment, but email verification still requires a code.
- Only the owner account can access CEO operations, user management, launch review, and emergency stop.
- Paid subscribers can run only the product their plan unlocks: Studio Pro for Studio, Trading Pro for Trading, Ultimate for both.
- Signup includes name, email, password confirmation, birth date, phone number, phone code, and password hint question/answer.
- Phone verification is completed before normal user signup. Local/test builds use the fixed verification code `122492` when no SMS provider is configured.
- Email verification, ID lookup, password hint, and password reset routes exist.
- Login tokens must survive server restarts or safely clear themselves in the browser.
- Studio trial is limited to one generation per IP per day.
- Studio trial/free users receive view-only previews without model download URLs.
- Studio should not fail with "Invalid token" when a stale browser token exists; it should retry as trial or ask for login depending on the action.
- Studio owner and Studio Pro/Ultimate users must see full-access wording, no trial-only wording, and GLB download access when the backend returns a model URL.
- Trading Pro must not unlock Studio export. Studio Pro must not unlock real trading.
- Studio must show the Zenthex mark, not old HL/Habilab branding.
- Trading trial does not show API key inputs.
- Real trading is shown only to owner or Trading Pro/Ultimate users.
- Real trading must show an Upbit key verification button, not only a diagnostic button.
- Secret Key should stay hidden by default but have a temporary view button so users can confirm copied text.
- Real trading start should require key verification and then re-check the key on the backend before placing live orders.
- Trading owner and Trading Pro/Ultimate users must land on the real-trade permission view, not a trial-only view.
- Real trading key check must explain likely Upbit failures: allowed IP mismatch, missing asset/order permission, wrong Access Key, wrong Secret Key.
- Trading screen must show the Zenthex FastAPI server public IP from `ZENTHEX_SERVER_PUBLIC_IP` with a copy button for Upbit allowed IP registration.
- Public docs must explain that GitHub Pages is not the trading server and cannot provide the Upbit outbound IP.
- Trading includes short scalping targets and high-risk target options: +10%, +30%, +50%.
- Trading investment mode supports Upbit KRW all-in, KRW ratio, and fixed amount.
- Real trading scanner must not freeze the API while it scans the market.
- Real trading may sell only the quantity bought by the current Zenthex engine run unless the user explicitly opts into rotating existing holdings.
- Owner dashboard includes subscriber management: list users, change plan/role, and delete duplicate or withdrawn accounts.
- Mock payment cannot unlock paid plans unless explicitly enabled.
- Database migrations include the latest auth, phone, billing, and usage columns.
- Production data must be separated from GitHub uploads with a persistent database before paid users join.
- Monthly auto-renewal billing must store current subscription state separately from receipt history.
- CEO review must separate no-cost validation, low-cost launch testing, and paid production operating costs.
- The current full architecture and launch risks must be maintained in `ZENTHEX_MASTER_PLAN.md`.

## Recommended Before Public Launch

- Configure real SMTP delivery.
- Connect a production SMS provider.
- Connect persistent PostgreSQL or another production database before real paid users.
- Test mobile signup, Studio trial, Trading structure view, owner login, My Page receipts, and admin user deletion.
- Add production payment provider.
- Confirm expected monthly operating costs: database, server, storage, AI generation, GPU worker, email/SMS, monitoring, and payment fees.
- Add persistent queue/storage for Studio jobs.
- Add Studio job history and admin cleanup for generated files.
- Add Binance Spot connector only after Upbit real-order safety checks are proven.
- Add separate opt-in for selling/rotating coins the user already holds, because it is riskier than using available KRW cash.

## Owner Review Screen

After logging in as the owner, open:

```text
/admin.html
```

The "Launch Review" panel calls:

```text
GET /api/admin/review
```

Use it before every GitHub upload or deployment.
