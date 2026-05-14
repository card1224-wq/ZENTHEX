# Zenthex Launch Review

This checklist is the master review gate before uploading or publishing Zenthex.

## Required

- Homepage shows one clear Zenthex brand experience, not a split demo screen.
- No public page contains "demo" copy for the production-facing flow.
- Login and signup pages do not expose owner email or owner account guidance.
- `ZENTHEX_OWNER_EMAILS` is set on the server environment.
- Signup includes name, email, password confirmation, birth date, phone number, and password hint question/answer.
- Phone verification is completed before normal user signup.
- Email verification, ID lookup, password hint, and password reset routes exist.
- Studio trial is limited to one generation per IP per day.
- Studio trial/free users receive view-only previews without model download URLs.
- Trading trial does not show API key inputs.
- Real trading is shown only to owner/admin or Trading Pro/Ultimate users.
- Mock payment cannot unlock paid plans unless explicitly enabled.
- Database migrations include the latest auth, phone, billing, and usage columns.

## Recommended Before Public Launch

- Configure real SMTP delivery.
- Connect a production SMS provider.
- Test mobile signup, Studio trial, Trading structure view, owner login, and My Page receipts.
- Add production payment provider.
- Add persistent queue/storage for Studio jobs.
- Add Binance Spot connector only after Upbit real-order safety checks are proven.

## Owner Review Screen

After logging in as the owner, open:

```text
/admin.html
```

The "출시 전 검토" panel calls:

```text
GET /api/admin/review
```

Use it before every GitHub upload or deployment.
