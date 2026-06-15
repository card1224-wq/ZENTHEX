# Zenthex Stock Master Plan

## 1. Service Position

Zenthex is one SaaS company with three service lines:

- Zenthex Studio: AI architecture and 3D visualization
- Zenthex Trading: crypto auto-trading for Upbit, Bithumb, and Binance
- Zenthex Stock: stock strategy automation for domestic stocks first and overseas stocks later

Zenthex Stock is not a separate company at the MVP stage. It is the third product line inside Zenthex. A legal subsidiary can be considered later only if revenue, compliance, operations, or investment structure requires it.

## 2. Why Stock Must Be Separate From Crypto

Stock automation must not be mixed directly into the current crypto engine.

- Stocks have market open and close times.
- Stocks use broker APIs, not exchange APIs.
- Order types, tick sizes, account rules, fees, tax, and settlement are different.
- Domestic and overseas stocks have different calendars and currency risks.
- Stock automation needs stricter compliance wording than a simple crypto signal page.

Correct product structure:

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

## 3. Investment Direction

Zenthex Trading and Zenthex Stock must use different strategies.

Zenthex Trading:

- short-term crypto strategy
- enter only after rising confirmation
- avoid falling coins
- sell by target profit, trailing protection, or stop loss
- never present profit as guaranteed

Zenthex Stock:

- longer-term strategy
- look for undervalued but improving companies
- consider future growth industries
- consider earnings improvement
- consider positive corporate or sector news
- consider institutional/foreign inflow when available
- avoid buying a falling stock only because it looks cheap
- manage risk when the original investment thesis breaks

The stock product should feel more like a future-oriented portfolio engine than a fast scalping engine.

## 4. First Broker Recommendation

Recommended first target: Korea Investment Securities Open API.

Reason:

- REST and WebSocket style is suitable for a server-based SaaS.
- Domestic stock, overseas stock, quote, and order APIs can expand in one direction.
- It is easier to design with FastAPI workers than a PC-only automation model.

Kiwoom can be reviewed later because it is popular in Korea, but its PC/Windows dependency can make SaaS operation harder.

## 5. Core User Flow

1. User subscribes to Stock Pro or Ultimate.
2. User connects a brokerage API key.
3. Zenthex verifies lookup/order permission.
4. User starts Paper Trading first.
5. The engine scans domestic stocks during market hours.
6. The engine selects candidates by valuation, trend, volume, catalyst, and risk.
7. The engine buys only when the entry rule is satisfied.
8. The engine sells or reduces when target profit, trailing protection, stop loss, market-close rule, or thesis-break rule is triggered.
9. Mobile and web screens show holdings, realized PnL, unrealized PnL, thesis status, and engine status.

## 6. Candidate Selection Formula

The first formula should be conservative and future-oriented.

- trading value filter
- current price above important trend lines
- medium-term trend confirmation
- valuation discount against growth or sector peers
- earnings growth or turnaround signal
- news/catalyst watchlist
- institutional/foreign buying flow when available
- volume increase with price stability or rising price
- gap-up chase protection
- KOSPI/KOSDAQ market guard
- volatility cap
- stop-loss cooldown per stock

The engine must wait when no stock passes the quality and risk checks.

## 7. Risk Manager

Required controls:

- Paper Trading default before live orders
- per-position stop loss
- target profit sell
- trailing profit protection
- thesis-break exit rule
- daily maximum loss
- maximum trades per day
- maximum capital per stock
- duplicate order prevention
- market-close forced review or liquidation setting
- owner emergency stop
- full order and decision logs

Zenthex Stock must never use wording such as guaranteed profit, no loss, or investment advice.

## 8. Product Plans

Initial plan proposal:

- Stock Basic: watchlist, scanner, paper trading
- Stock Pro: broker connection, live order gate, mobile status
- Ultimate: Studio + Crypto Trading + Stock after Stock is proven

Pricing can be reviewed after the crypto engine stabilizes. Do not sell Stock Pro live trading until Paper Trading and risk logs are proven.

## 9. MVP Milestones

1. Stock public product page and master plan
2. Stock screen skeleton
3. Broker API selection and environment variables
4. Paper Trading stock simulator
5. Domestic stock quote scanner
6. Value/growth/news candidate scoring
7. Strategy and risk-manager logs
8. Owner launch review checks
9. Subscription gate
10. Broker key verification
11. Small live-order test
12. Mobile status view
13. Production compliance review

## 10. Current Build Status

This build introduces the blueprint and UI/route skeleton only.

Live stock orders are intentionally disabled until the broker connector, paper trading, market-hours scheduler, and stock-specific risk disclosure are complete.
