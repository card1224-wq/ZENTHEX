# Zenthex Stock Master Plan

## 1. Service Position

Zenthex is one SaaS company with three service lines:

- Zenthex Studio: AI architecture and 3D visualization
- Zenthex Trading: crypto auto-trading for Upbit, Bithumb, and Binance
- Zenthex Stock: stock auto-trading for domestic and later overseas equities

Zenthex Stock is not a separate company at the MVP stage. It is a third product line inside Zenthex. A legal subsidiary can be considered later only if revenue, compliance, operations, or investment structure requires it.

## 2. Why Stock Must Be Separate From Crypto

Stock trading must not be mixed directly into the current crypto engine.

- Stocks have market open and close times.
- Stocks use broker APIs, not exchange APIs.
- Order types, tick sizes, account rules, fees, tax, and settlement are different.
- Domestic and overseas stocks have different calendars and currency risks.
- Stock automation needs stricter compliance wording than a simple crypto signal page.

Therefore the correct structure is:

```text
Zenthex
├── Zenthex Studio
├── Zenthex Trading
│   ├── Upbit
│   ├── Bithumb
│   └── Binance
└── Zenthex Stock
    ├── Korea Investment Securities
    ├── Kiwoom Securities
    └── Overseas stock connector later
```

## 3. First Broker Recommendation

Recommended first target: Korea Investment Securities Open API.

Reason:

- REST and WebSocket style is better for a server-based SaaS.
- Domestic stock, overseas stock, and quote/order APIs can be expanded in one direction.
- It is easier to design with FastAPI workers than a PC-only automation model.

Kiwoom can be reviewed later because it is popular in Korea, but its PC/Windows dependency can make SaaS operation harder.

## 4. Core User Flow

1. User subscribes to Stock Pro or Ultimate.
2. User connects a brokerage API key.
3. Zenthex verifies lookup/order permission.
4. User starts Paper Trading first.
5. The engine scans domestic stocks during market hours.
6. The engine selects candidates by trend, volume, volatility, and risk.
7. The engine buys only when the entry rule is satisfied.
8. The engine sells when target profit, trailing protection, stop loss, or market close rule is triggered.
9. Mobile and web screens show current holdings, realized PnL, unrealized PnL, and engine status.

## 5. Candidate Selection Formula

The first formula should be conservative.

- Trading value filter
- Current price above short moving averages
- 1m/3m/5m momentum confirmation
- Volume surge with price rising, not falling
- Gap-up chase protection
- Market index guard, such as KOSPI/KOSDAQ short-term direction
- Volatility cap
- Stop-loss cooldown per stock

The engine must wait when no stock passes the rising-confirmation checks.

## 6. Risk Manager

Required controls:

- Paper Trading default before live orders
- Per-position stop loss
- Target profit sell
- Trailing profit protection
- Daily maximum loss
- Maximum trades per day
- Maximum capital per stock
- Duplicate order prevention
- Market close forced review or liquidation setting
- Owner emergency stop
- Full order and decision logs

Zenthex Stock must never use wording such as guaranteed profit, no loss, or investment advice.

## 7. Product Plans

Initial plan proposal:

- Stock Basic: watchlist, scanner, paper trading
- Stock Pro: broker connection, live order gate, mobile status
- Ultimate: Studio + Crypto Trading + Stock

Pricing can be reviewed after the crypto engine stabilizes. Do not sell Stock Pro live trading until Paper Trading and risk logs are proven.

## 8. MVP Milestones

1. Stock public product page and master plan
2. Stock screen skeleton
3. Broker API selection and environment variables
4. Paper Trading stock simulator
5. Domestic stock quote scanner
6. Strategy and risk-manager logs
7. Owner launch review checks
8. Subscription gate
9. Broker key verification
10. Small live-order test
11. Mobile status view
12. Production compliance review

## 9. Current Build Status

This build introduces the blueprint and UI/route skeleton only.

Live stock orders are intentionally disabled until the broker connector, paper trading, market-hours scheduler, and stock-specific risk disclosure are complete.
