"""Fail closed on unknown order results. No exchange API credentials are persisted."""
import asyncio
import json
import math
import os
import time
from pathlib import Path


def guard_path() -> Path:
    return Path(os.getenv("ZENTHEX_TRADING_STATE_DIR", "runtime-state")) / "live-position.json"


def recovery_required() -> bool:
    return guard_path().exists()


def save_guard(event: str, **details):
    path = guard_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump({"event": event, "updated_at": time.time(), **details}, out)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)


def clear_guard():
    guard_path().unlink(missing_ok=True)


async def wait_for_fill(client, order_id: str, *, timeout: float = 20, poll: float = 0.5):
    if not order_id or not hasattr(client, "get_order"):
        raise RuntimeError("주문 확인용 ID/API가 없습니다. 거래소에서 주문을 확인하세요.")
    deadline = time.monotonic() + timeout
    while True:
        order = await asyncio.to_thread(client.get_order, order_id)
        if not isinstance(order, dict) or order.get("error"):
            raise RuntimeError("주문 조회 실패. 자동 재주문하지 않고 수동 확인을 기다립니다.")
        if order.get("state") in {"done", "cancel"}:
            trades = order.get("trades") or []
            qty = sum(float(t["volume"]) for t in trades)
            funds = sum(float(t["funds"]) for t in trades)
            fee = float(order.get("paid_fee") or 0)
            executed = float(order.get("executed_volume") or 0)
            values = (qty, funds, fee, executed)
            if not all(math.isfinite(v) for v in values) or qty <= 0 or funds <= 0 or fee < 0 or not math.isclose(qty, executed, rel_tol=1e-6, abs_tol=1e-12):
                raise RuntimeError("확정 체결량/대금/수수료가 불완전합니다. 거래소에서 확인하세요.")
            return {"quantity": qty, "funds": funds, "fee": fee, "state": order["state"]}
        if time.monotonic() >= deadline:
            raise RuntimeError("체결 확인 시간 초과. 주문이 살아 있을 수 있어 자동 재주문하지 않습니다.")
        await asyncio.sleep(poll)
