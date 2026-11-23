"""Runtime capability facts; configuration is never presented as a successful API call."""
import importlib.util
import os
from fastapi import APIRouter
from trading.orders import recovery_required
from trading import router as trading_routes
from studio import router as studio_routes

router = APIRouter(prefix="/api/modules", tags=["modules"])


def studio_capability():
    configured = bool((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip())
    try:
        sdk = importlib.util.find_spec("google.genai") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        sdk = False
    return {
        "configured": configured, "sdkAvailable": sdk,
        "state": "unverified" if configured and sdk else "configuration_required",
        "message": "생성 요청으로 API 연결을 확인하세요." if configured and sdk else "AI 이미지 생성 연결 설정이 필요합니다. 대표에게 문의하세요.",
        "imageGeneration": configured and sdk, "dimensionAccurateModel": False,
    }


@router.get("/status")
def module_status():
    enabled = os.getenv("ZENTHEX_ENABLE_LIVE_TRADING", "false").lower() == "true"
    recovery = recovery_required()
    return {
        "deployment": {
            "engineState": trading_routes.bot_state.state,
            "engineTaskActive": trading_routes.ENGINE_TASK is not None and not trading_routes.ENGINE_TASK.done(),
            "hasPosition": bool(trading_routes.bot_state.held_btc or trading_routes.bot_state.avg_buy_price),
            "studioBusy": studio_routes.GENERATION_LOCK.locked(),
        },
        "studio": studio_capability(),
        "trading": {
            "liveEnabled": enabled, "recoveryRequired": recovery,
            "upbit": {"implemented": True, "ordersEnabled": enabled and not recovery,
                      "state": "recovery_required" if recovery else "key_verification_required" if enabled else "locked"},
            "bithumb": {"implemented": False, "ordersEnabled": False, "state": "readonly"},
            "binance": {"implemented": False, "ordersEnabled": False, "state": "readonly"},
        },
        "stock": {"research": True, "ordersEnabled": False, "state": "research",
                  "message": "과거 데이터 전략 검증과 대표 계좌 조회를 제공합니다. 실시간 주식 자동주문은 아직 구현되지 않았습니다."},
    }
