# Zenthex Production Database Plan

GitHub deploys must update code only. User accounts, passwords, subscriptions, receipts, Studio jobs, Trading settings, and encrypted exchange-key records must remain in a persistent production database.

## Required Production Setup

Use PostgreSQL before charging real users.

```env
ZENTHEX_DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

Many hosting providers expose `postgres://...`; the app normalizes that automatically.

## Why This Matters

Local SQLite creates `zenthex.db` on the running server. If a new deploy server starts with a fresh SQLite file, old accounts will not exist even though the browser still has a login token.

PostgreSQL keeps the data outside GitHub upload files, so code updates do not delete:

- user accounts
- subscription state
- monthly renewal status
- payment receipts
- Studio history
- Trading settings

## Subscription Storage

`billing_history` stores receipts.

`subscriptions` stores the current subscription:

- plan
- active/inactive/owner status
- provider
- provider subscription id
- next billing date
- last payment status

Monthly auto-renewal should be connected later through:

- Toss Payments billing key for Korea
- Stripe subscriptions for global cards
- payment webhooks for success, failure, cancellation, and refund events
