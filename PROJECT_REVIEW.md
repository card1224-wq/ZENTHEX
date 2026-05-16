# Zenthex Launch Review

This checklist is the master review gate before uploading or publishing Zenthex.

## Required

- Homepage shows one clear Zenthex brand experience, not a split demo screen.
- Homepage hero must always introduce Zenthex as a public brand, not change into "Zenthex Control" for the owner.
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
- Trading owner and Trading Pro/Ultimate users must land on the real-trade permission view, not a trial-only view.
- Real trading key check must explain likely Upbit failures: allowed IP mismatch, missing asset/order permission, wrong Access Key, wrong Secret Key.
- Trading includes short scalping targets and high-risk target options: +10%, +30%, +50%.
- Trading investment mode supports Upbit KRW all-in, KRW ratio, and fixed amount.
- Real trading scanner must not freeze the API while it scans the market.
- Real trading may sell only the quantity bought by the current Zenthex engine run unless the user explicitly opts into rotating existing holdings.
- Owner dashboard includes subscriber management: list users, change plan/role, and delete duplicate or withdrawn accounts.
- Mock payment cannot unlock paid plans unless explicitly enabled.
- Database migrations include the latest auth, phone, billing, and usage columns.

## Recommended Before Public Launch

- Configure real SMTP delivery.
- Connect a production SMS provider.
- Test mobile signup, Studio trial, Trading structure view, owner login, My Page receipts, and admin user deletion.
- Add production payment provider.
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
