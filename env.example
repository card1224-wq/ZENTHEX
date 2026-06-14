import base64
import hashlib
import hmac
import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request


BITHUMB_BASE = "https://api.bithumb.com"


def clean_key(value: str) -> str:
    return (value or "").strip().replace("\u200b", "").replace("\ufeff", "")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _query_string(params: dict | None) -> str:
    if not params:
        return ""
    return urllib.parse.urlencode(params)


def build_bithumb_jwt(access_key: str, secret_key: str, query: str = "") -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
    }
    if query:
        payload["query_hash"] = hashlib.sha512(query.encode("utf-8")).hexdigest()
        payload["query_hash_alg"] = "SHA512"

    signing_input = ".".join(
        [
            _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def explain_bithumb_error(raw_error) -> str:
    text = str(raw_error or "")
    lowered = text.lower()
    if "notallowip" in lowered or "ip" in lowered:
        return "Bithumb API allowed IP does not match. Add the Zenthex server outbound IP in Bithumb API settings."
    if "out_of_scope" in lowered or "scope" in lowered:
        return "Bithumb API permission is not enough. Enable asset lookup and order permission only; keep withdrawal disabled."
    if "jwt" in lowered or "signature" in lowered or "verification" in lowered:
        return "Bithumb Secret Key or JWT signature is invalid. Reissue the key if the secret may have been copied incorrectly."
    if "access" in lowered or "key" in lowered or "unauthorized" in lowered or "401" in lowered:
        return "Bithumb API Key is invalid, expired, or blocked by permission/IP settings."
    return "Bithumb authentication failed. Check API Key, Secret Key, permissions, and allowed IP."


def _request(method: str, path: str, access_key: str = "", secret_key: str = "", params: dict | None = None):
    query = _query_string(params)
    url = f"{BITHUMB_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json; charset=utf-8", "accept": "application/json"}
    if method == "GET" and query:
        url = f"{url}?{query}"
    if access_key and secret_key:
        token = build_bithumb_jwt(access_key, secret_key, query)
        headers["Authorization"] = f"Bearer {token}"
    if method in ["POST", "DELETE"]:
        data = json.dumps(params or {}, separators=(",", ":")).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return exc.code, parsed
    except Exception as exc:
        return 0, str(exc)


def get_bithumb_current_price(ticker: str) -> float:
    status, data = _request("GET", "/v1/ticker", params={"markets": ticker})
    if status == 200 and isinstance(data, list) and data:
        return float(data[0].get("trade_price") or 0)
    return 0.0


class BithumbClient:
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = clean_key(access_key)
        self.secret_key = clean_key(secret_key)

    def get_balances(self):
        status, data = _request("GET", "/v1/accounts", self.access_key, self.secret_key)
        if status == 200 and isinstance(data, list):
            return data
        return {"error": data, "message": explain_bithumb_error(data)}

    def get_balance(self, currency: str) -> float:
        balances = self.get_balances()
        if not isinstance(balances, list):
            return 0.0
        target = currency.replace("KRW-", "")
        for row in balances:
            if row.get("currency") == target:
                return float(row.get("balance") or 0)
        return 0.0

    def buy_market_order(self, ticker: str, amount_krw: float):
        params = {
            "market": ticker,
            "side": "bid",
            "price": str(int(amount_krw)),
            "order_type": "price",
        }
        status, data = _request("POST", "/v2/orders", self.access_key, self.secret_key, params)
        if status in [200, 201] and isinstance(data, dict):
            return data
        return {"error": data, "message": explain_bithumb_error(data)}

    def sell_market_order(self, ticker: str, volume: float):
        params = {
            "market": ticker,
            "side": "ask",
            "volume": f"{volume:.12f}".rstrip("0").rstrip("."),
            "order_type": "market",
        }
        status, data = _request("POST", "/v2/orders", self.access_key, self.secret_key, params)
        if status in [200, 201] and isinstance(data, dict):
            return data
        return {"error": data, "message": explain_bithumb_error(data)}


def check_bithumb_key(access_key: str, secret_key: str):
    client = BithumbClient(access_key, secret_key)
    balances = client.get_balances()
    if not isinstance(balances, list):
        return {
            "status": "error",
            "message": explain_bithumb_error(balances),
            "verified": False,
            "checklist": [
                "Enable Bithumb asset lookup and order permissions",
                "Keep withdrawal permission disabled",
                "Register the Zenthex server outbound IP",
                "Remove spaces or line breaks around Secret Key",
            ],
        }

    krw_balance = 0.0
    asset_count = 0
    for row in balances:
        currency = row.get("currency")
        balance = float(row.get("balance") or 0)
        locked = float(row.get("locked") or 0)
        if currency == "KRW":
            krw_balance = balance
        elif balance + locked > 0:
            asset_count += 1

    return {
        "status": "success",
        "message": f"Bithumb key verified. KRW balance is about {krw_balance:,.0f} KRW and held assets are {asset_count}.",
        "verified": True,
        "cashBalance": krw_balance,
        "assetCount": asset_count,
    }


def build_bithumb_account_summary(access_key: str, secret_key: str):
    client = BithumbClient(access_key, secret_key)
    balances = client.get_balances()
    if not isinstance(balances, list):
        return {"status": "error", "message": explain_bithumb_error(balances)}

    cash_balance = 0.0
    positions = []
    for row in balances:
        currency = row.get("currency")
        balance = float(row.get("balance") or 0)
        locked = float(row.get("locked") or 0)
        total_qty = balance + locked
        if currency == "KRW":
            cash_balance = balance
            continue
        if not currency or total_qty <= 0:
            continue
        ticker = f"KRW-{currency}"
        price = get_bithumb_current_price(ticker)
        avg_price = float(row.get("avg_buy_price") or 0)
        valuation = total_qty * price if price else 0
        entry_value = avg_price * total_qty if avg_price else 0
        pnl = valuation - entry_value if entry_value else 0
        pnl_pct = pnl / entry_value if entry_value else 0
        positions.append(
            {
                "ticker": ticker,
                "qty": total_qty,
                "availableQty": balance,
                "lockedQty": locked,
                "avgBuyPrice": avg_price,
                "currentPrice": price,
                "valuation": valuation,
                "pnl": pnl,
                "pnlPct": pnl_pct,
                "status": "BITHUMB HOLDING",
            }
        )

    coin_value = sum(item.get("valuation", 0) for item in positions)
    invested_value = sum((item.get("avgBuyPrice", 0) or 0) * (item.get("qty", 0) or 0) for item in positions)
    total_pnl = coin_value - invested_value if invested_value else 0
    return {
        "status": "success",
        "message": "Bithumb account connected.",
        "cashBalance": cash_balance,
        "coinValue": coin_value,
        "estBalance": cash_balance + coin_value,
        "investedValue": invested_value,
        "totalPnl": total_pnl,
        "totalPnlPct": total_pnl / invested_value if invested_value else 0,
        "positions": positions,
    }
