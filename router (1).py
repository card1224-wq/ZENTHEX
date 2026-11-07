import asyncio
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from auth.router import require_current_user
from database.session import get_db
from stock import toss_client

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/status")
async def stock_status():
    return {
        "status": "research",
        "service": "Zenthex Stock",
        "phase": "historical-research-and-owner-readonly",
        "message": "Zenthex Stock is designed as a separate long-term stock strategy service line. Live brokerage orders are not enabled in this build.",
        "toss": {"configured": toss_client.configured(), "ordersEnabled": False},
        "researchUrl": "/research.html",
        "supported_brokers_plan": [
            {
                "name": "Toss Securities",
                "priority": 0,
                "reason": "Owner-only accounts and holdings adapter added; real credentials have not been tested. No order adapter.",
            },
            {
                "name": "Korea Investment Securities",
                "priority": 1,
                "reason": "REST and WebSocket APIs exist. Customer-facing execution requires a separate scope and terms review.",
            },
            {
                "name": "Kiwoom Securities",
                "priority": 2,
                "reason": "A Linux-compatible REST API exists. No Kiwoom connector is implemented in this build.",
            },
        ],
        "strategy_lines": [
            {
                "name": "Day Stock",
                "market": "Korea / US market-hours aware",
                "goal": "Intraday entries that close or review before market close.",
                "filters": ["market guard", "volume expansion", "price above VWAP/MA", "news/catalyst check", "stop loss"],
            },
            {
                "name": "Long Stock",
                "market": "Korea / US swing and long-term",
                "goal": "Future-oriented holdings when trend, earnings, sector, and valuation agree.",
                "filters": ["1 month trend", "earnings improvement", "sector strength", "valuation discount", "thesis-break exit"],
            },
        ],
        "safety_rules": [
            "No profit guarantee",
            "Paper trading before live orders",
            "Market-hours aware engine",
            "Long-term thesis and catalyst review",
            "No buying only because a stock is falling",
            "Daily loss limit",
            "Per-position stop loss",
            "Owner kill switch",
            "Broker API keys must be encrypted before production",
        ],
    }


@router.get("/launch-check")
async def stock_launch_check():
    return {
        "status": "review_required",
        "checks": [
            {"item": "Broker API selected", "ready": False, "note": "Toss owner read-only adapter exists; no live order broker is enabled."},
            {"item": "Paper trading simulator", "ready": False, "note": "Historical CSV research is available; forward paper trading is not yet implemented."},
            {"item": "Market-hours scheduler", "ready": False, "note": "Domestic stocks require session-aware execution."},
            {"item": "Risk disclosure", "ready": False, "note": "Stock-specific risk wording must be added."},
            {"item": "Subscription gate", "ready": False, "note": "Stock Pro or Ultimate permission should unlock this line."},
        ],
    }


@router.get('/toss/account-summary')
async def toss_account_summary(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = require_current_user(Authorization, db)
    if user.role != 'owner':
        raise HTTPException(403, '대표 본인의 서버 설정 계좌만 조회할 수 있습니다.')
    if not toss_client.configured():
        raise HTTPException(503, '서버에 토스증권 API 설정이 없습니다.')
    try:
        return await asyncio.to_thread(toss_client.account_summary)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(502, '토스 조회 실패. 허용 IP·키·권한·선택 계좌를 확인하세요. 비밀키를 화면이나 GitHub에 올리지 마세요.')
