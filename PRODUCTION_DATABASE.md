import hashlib
import hmac
import time
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation


BINANCE_LIVE_BASE = "https://api.binance.com"
BINANCE_TESTNET_BASE = "https://testnet.binance.vision"


def clean_key(value: str) -> str:
    return (value or "").strip().replace("\u200b", "").replace("\ufeff", "")


def base_url(testnet: bool = False) -> str:
    return BINANCE_TESTNET_BASE if testnet else BINANCE_LIVE_BASE


def explain_binance_error(raw_error) -> str:
    text = str(raw_error or "")
    lowered = text.lower()
    if "-2015" in lowered or "invalid api-key" in lowered:
        return "Binance API 키, 허용 IP, 또는 권한이 맞지 않습니다. Spot 거래 권한과 Zenthex 서버 IP 등록을 확인하세요."
    if "signature" in lowered or "-1022" in lowered:
        return "Binance Secret Key 서명 검증에 실패했습니다. Secret Key 복사 상태를 확인하거나 새 키를 발급하세요."
    if "timestamp" in lowered or "-1021" in lowered:
        return "Binance 서버 시간과 Zenthex 서버 시간이 맞지 않습니다. 서버 시간 동기화가 필요합니다."
    if "ip" in lowered or "permission" in lowered or "restricted" in lowered:
        return "Binance API 키의 IP 제한 또는 권한 설정 문제입니다. 출금 권한은 끄고 Spot 거래/조회 권한만 켜세요."
    return "Binance 인증에 실패했습니다. API 키, Secret Key, Spot 권한, IP 화이트리스트, Testnet/Live 선택을 확인하세요."


def _request_json(url: str, headers: dict | None = None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=8) as response:
        import json

        return json.loads(response.read().decode("utf-8"))


def _signed_query(secret_key: str, params: dict) -> str:
    query = urllib.parse.urlencode(params)
    signature = hmac.new(secret_key.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{query}&signature={signature}"


def signed_get(path: str, access_key: str, secret_key: str, testnet: bool = False, params: dict | None = None):
    access_key = clean_key(access_key)
    secret_key = clean_key(secret_key)
    payload = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
    if params:
        payload.update(params)
    query = _signed_query(secret_key, payload)
    return _request_json(
        f"{base_url(testnet)}{path}?{query}",
        headers={"X-MBX-APIKEY": access_key},
    )


def public_get(path: str, testnet: bool = False, params: dict | None = None):
    query = urllib.parse.urlencode(params or {})
    url = f"{base_url(testnet)}{path}" + (f"?{query}" if query else "")
    return _request_json(url)


def check_binance_key(access_key: str, secret_key: str, testnet: bool = False):
    try:
        account = signed_get("/api/v3/account", access_key, secret_key, testnet=testnet)
        balances = account.get("balances", [])
        usdt_balance = Decimal("0")
        non_zero = []
        for row in balances:
            free = _to_decimal(row.get("free"))
            locked = _to_decimal(row.get("locked"))
            total = free + locked
            asset = row.get("asset")
            if asset == "USDT":
                usdt_balance = free
            if total > 0:
                non_zero.append({"asset": asset, "free": str(free), "locked": str(locked), "total": str(total)})
        return {
            "status": "success",
            "verified": True,
            "usdt_balance": float(usdt_balance),
            "assets": non_zero[:30],
            "message": f"Binance {'Testnet' if testnet else 'Live'} 키 인증 성공. 조회 가능한 USDT 잔고는 약 {float(usdt_balance):,.4f} USDT입니다.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "verified": False,
            "message": explain_binance_error(exc),
            "raw": str(exc),
            "checklist": [
                "Binance API Management에서 Spot & Margin Trading 권한 확인",
                "출금 권한은 반드시 끄기",
                "IP Restriction에 Zenthex 서버 outbound IP 등록",
                "Testnet 키와 Live 키를 섞어 쓰지 않았는지 확인",
                "Secret Key 앞뒤 공백과 줄바꿈 제거",
            ],
        }


def build_binance_account_summary(access_key: str, secret_key: str, testnet: bool = False):
    result = check_binance_key(access_key, secret_key, testnet=testnet)
    if result.get("status") != "success":
        return result
    assets = result.get("assets", [])
    return {
        "status": "success",
        "message": "Binance 잔고를 불러왔습니다. 자동매매 주문은 Spot 리스크 검증 후 열립니다.",
        "cashBalance": result.get("usdt_balance", 0),
        "quoteAsset": "USDT",
        "positions": assets,
    }


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")
