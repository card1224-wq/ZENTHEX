# Zenthex Launch Review

This checklist is the master review gate before uploading or publishing Zenthex.

## Required

- Homepage shows one clear Zenthex brand experience, not a split demo screen.
- Homepage hero must always introduce Zenthex as a public brand, not change into "Zenthex Control" for the owner.
- Homepage must show visual Studio/Trading preview panels so the first screen is not text-only.
- Studio must show NanoBanana/Gemini generated images as the central main result, not as a small side preview.
- Studio must state that GLB/OBJ generation needs the later 3D Worker server while current output is AI building image/JPG.
- Logged-in homepage navigation must show My Page, Customer Center, and Logout instead of only Login.
- Owner homepage actions must open Studio workspace, Trading engine, CEO dashboard, and My Page instead of trial-only actions.
- Customer Center must exist for account, subscription, Studio, Trading, and Upbit key guidance.
- Customer Center must include an inquiry form, store tickets in the database, and allow the owner to manage ticket status/replies in the CEO dashboard.
- Trading must support split-entry mode so a configured total budget can be divided into multiple entries with average-price based take-profit/stop-loss.
- Split-entry mode must show max entry count, add-entry trigger, current entry count, and risk copy that it is not a guaranteed-profit formula.
- Trading stop controls must separate pause/hold from sell-and-stop so users do not accidentally market-sell a position.
- Trading must show the automatic selection criteria and use KST timestamps in system logs.
- Trading desktop layout must use three columns so quick execution, live status, and auxiliary settings do not stack into one long form.
- Trading scanner must reject volume-with-price-falling, recent red candles, and late entries too close to the 24h high.
- Trading scanner must wait instead of entering when no coin has positive 1m/3m/5m momentum and recent bullish candle confirmation.
- Trading split entry must add only into profitable rising positions, not average down into falling positions.
- Trading entry guard must block BTC/ETH broad-market short-term selloffs, weak orderbooks, and immediate post-signal price drops before buying.
- Trading must apply a cooldown after stop-loss so the same coin is not immediately re-entered by the scanner.
- Studio NanoBanana/Gemini failures must show a clear reason such as missing API key, missing package, empty image response, or API error.
- No public page contains "demo" copy for the production-facing flow.
- Login and signup pages do not expose owner email or owner account guidance.
- Owner email is controlled by `ZENTHEX_OWNER_EMAILS`, with `7foliath@naver.com` kept as the built-in owner fallback.
- Owner account has Ultimate access without payment, but email verification still requires a code.
- Only the owner account can access CEO operations, user management, launch review, and emergency stop.
- My Page must separate owner operations entry from subscriber product workspace. Subscribers must not see owner metrics, launch review, user management, or emergency stop controls.
- Paid subscribers can run only the product their plan unlocks: Studio Pro for Studio, Trading Pro for Trading, Ultimate for both.
- Signup includes name, email, password confirmation, birth date, phone number, phone code, and password hint question/answer.
- Normal user signup must enter an owner-approval pending state before login/service use.
- Phone verification is completed before normal user signup. Local/test builds use the fixed verification code `122492` when no SMS provider is configured.
- Email verification, ID lookup, password hint, and password reset routes exist.
- Login tokens must survive server restarts or safely clear themselves in the browser.
- Studio trial is limited to one generation per IP per day.
- Studio trial/free users receive view-only previews without model download URLs.
- Studio should not fail with "Invalid token" when a stale browser token exists; it should retry as trial or ask for login depending on the action.
- Studio owner and Studio Pro/Ultimate users must see full-access wording, no trial-only wording, and GLB download access when the backend returns a model URL.
- Studio owner and Studio Pro/Ultimate users should also be able to save the current preview as JPG.
- Studio prompt generation must visibly change the preview according to the prompt, including a dedicated apartment-style preview for "32평 아파트" prompts.
- Studio should call NanoBanana for immediate prompt image previews when `GEMINI_API_KEY` is configured, and clearly fall back when it is not.
- Studio must remain usable as a visual preview even if OpenCV/3D Worker dependencies are missing; GLB export should be clearly marked as requiring the worker.
- Trading Pro must not unlock Studio export. Studio Pro must not unlock real trading.
- Studio must show the Zenthex mark, not old HL/Habilab branding.
- Trading trial does not show API key inputs.
- Real trading is shown only to owner or Trading Pro/Ultimate users.
- Real trading must show an Upbit key verification button, not only a diagnostic button.
- Secret Key should stay hidden by default but have a temporary view button so users can confirm copied text.
- Real trading start should require key verification and then re-check the key on the backend before placing live orders.
- Trading owner and Trading Pro/Ultimate users must land on the real-trade permission view, not a trial-only view.
- Real trading key check must explain likely Upbit failures: allowed IP mismatch, missing asset/order permission, wrong Access Key, wrong Secret Key.
- Binance connector readiness must include Testnet/Live key diagnostics, key verification, balance lookup, Spot-only warning, and no Futures launch in the MVP.
- Trading screen must show the Zenthex FastAPI server public IP from `ZENTHEX_SERVER_PUBLIC_IP` with a copy button for Upbit allowed IP registration.
- Paid real trading must use a fixed outbound server IP. Current intended Zenthex fixed IP is `74.220.52.254`; auto-detected IP is a warning/reference only, and the server must actually route outbound Upbit requests through the same IP.
- Trading screen must verify configured IP versus actual outbound IP. If they differ, the deployment is not ready for Upbit live trading.
- Public docs must explain that GitHub Pages is not the trading server and cannot provide the Upbit outbound IP.
- Trading settings must show a compact summary for exit mode, target yield, capital mode, and coin selection so the strategy is readable at a glance.
- Trading must provide explicit Upbit/Binance exchange selection buttons before exchange-specific key setup.
- Trading's default screen should expose only the essential strategy controls; advanced controls such as trailing exit and existing-holdings rotation should be collapsed but automatically opened when selected.
- Trading must show a return-rate chart from the latest Upbit balance/status `totalPnlPct`, so users can monitor profit movement, not only coin holdings.
- Trading includes short scalping targets and high-risk target options: +10%, +30%, +50%.
- Trading investment mode supports KRW cash all-in, KRW cash ratio, fixed amount, and an explicit high-risk existing-holdings rotation mode.
- Real trading scanner must not freeze the API while it scans the market.
- Real trading may sell only the quantity bought by the current Zenthex engine run unless the user explicitly opts into rotating existing holdings.
- Real trading must stop completely after a stop-loss sell. It must not return to scanning or re-enter automatically unless a separate future auto-reentry option is explicitly enabled by the user.
- Existing-holdings rotation must require a separate checkbox and confirmation because it can sell coins already held in the Upbit account.
- Owner dashboard includes subscriber management: list users, change plan/role, and delete duplicate or withdrawn accounts.
- Owner dashboard includes customer inquiry management: list tickets, update status, and save replies or internal notes.
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
