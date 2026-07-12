from fastapi import APIRouter

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/status")
async def stock_status():
    return {
        "status": "planned",
        "service": "Zenthex Stock",
        "phase": "blueprint",
        "message": "Zenthex Stock is designed as a separate long-term stock strategy service line. Live brokerage orders are not enabled in this build.",
        "supported_brokers_plan": [
            {
                "name": "Korea Investment Securities",
                "priority": 1,
                "reason": "REST and WebSocket Open API are suitable for a server-based SaaS architecture.",
            },
            {
                "name": "Kiwoom Securities",
                "priority": 2,
                "reason": "Popular domestic stock automation API, but Windows/PC dependency must be reviewed before SaaS use.",
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
            {"item": "Broker API selected", "ready": False, "note": "KIS is the recommended first target."},
            {"item": "Paper trading simulator", "ready": False, "note": "Must be built before live stock orders."},
            {"item": "Market-hours scheduler", "ready": False, "note": "Domestic stocks require session-aware execution."},
            {"item": "Risk disclosure", "ready": False, "note": "Stock-specific risk wording must be added."},
            {"item": "Subscription gate", "ready": False, "note": "Stock Pro or Ultimate permission should unlock this line."},
        ],
    }
