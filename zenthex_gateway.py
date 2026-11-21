"""Render entry point: one public address, one AWS application, no local trading engine.

Start only on Render: uvicorn zenthex_gateway:app --host 0.0.0.0 --port $PORT
The existing AWS main:app entry point is unchanged.
"""
from contextlib import asynccontextmanager
import asyncio
import ipaddress
import os
import re
from urllib.parse import unquote, urlsplit

import httpx
from starlette.applications import Starlette
from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route


DEFAULT_ORIGIN = "https://13.124.81.242"
MAX_BODY = 25 * 1024 * 1024
HOP_HEADERS = {
    b"connection", b"keep-alive", b"proxy-authenticate", b"proxy-authorization",
    b"te", b"trailer", b"transfer-encoding", b"upgrade", b"proxy-connection",
}
UNSAFE_AUTH = re.compile(r"^/api/auth/(signup|password|dev|phone)(/|$)", re.I)


def backend_origin(value):
    """Only HTTPS on this installation's fixed public IPv4; never a client URL."""
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or parsed.port not in (None, 443)):
        raise ValueError("ZENTHEX_BACKEND_ORIGIN must be an HTTPS IPv4 origin on port 443")
    address = ipaddress.IPv4Address(parsed.hostname or "")
    if not address.is_global:
        raise ValueError("AWS backend must have a public IPv4 address")
    return "https://" + str(address)


def connection_headers(headers):
    result = set(HOP_HEADERS)
    for key, value in headers:
        if key.lower() == b"connection":
            result.update(name.strip().lower() for name in value.split(b","))
    return result


def guarded_path(path):
    # Inspect decoded spellings too; nginx independently applies the same guards.
    for _ in range(4):
        normalized = re.sub(r"/+", "/", path.replace("\\", "/"))
        parts = []
        for part in normalized.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        normalized = "/" + "/".join(parts)
        if UNSAFE_AUTH.match(normalized):
            return 403
        if any(part.startswith(".") for part in parts):
            return 404
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    return None


def error(status, message):
    return JSONResponse({"status": "error", "message": message}, status_code=status,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@asynccontextmanager
async def lifespan(app):
    app.state.origin = backend_origin(os.getenv("ZENTHEX_BACKEND_ORIGIN", DEFAULT_ORIGIN))
    # Certificate verification is mandatory. No fallback origin or request retries.
    async with httpx.AsyncClient(
        verify=True, trust_env=False, follow_redirects=False,
        transport=httpx.AsyncHTTPTransport(retries=0, verify=True, trust_env=False),
        timeout=httpx.Timeout(120, connect=10, write=30, pool=10),
        limits=httpx.Limits(max_connections=40, max_keepalive_connections=10),
    ) as client:
        app.state.client = client
        yield


async def readiness(request):
    """Render health gate: reject a cutover to an unhealthy or unprotected backend."""
    origin = request.app.state.origin
    client = request.app.state.client
    try:
        health, server_ip, signup, dev = await asyncio.gather(*(
            client.send(httpx.Request("GET", origin + path, extensions={
                "timeout": {"connect": 4, "read": 4, "write": 4, "pool": 4}
            })) for path in [
                "/api/health", "/api/finance/server-ip", "/api/auth/signup", "/api/auth/dev/outbox"]
        ))
        if (health.status_code != 200 or health.json().get("status") != "ok"
                or health.json().get("service") != "zenthex-saas"
                or server_ip.status_code != 200
                or server_ip.json().get("server_ip") != urlsplit(origin).hostname
                or signup.status_code != 403 or dev.status_code != 403):
            return error(503, "AWS 서버 상태·고정 IP 설정·접근 보호를 확인하세요.")
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return error(503, "AWS HTTPS 연결을 확인하세요. 인증서 검증은 생략하지 않습니다.")
    return JSONResponse({"status": "ok", "mode": "render-gateway",
                         "backend_ip": urlsplit(origin).hostname},
                        headers={"Cache-Control": "no-store", "X-Zenthex-Backend": "aws"})


async def forward(request: Request):
    blocked = guarded_path(request.scope["path"])
    if blocked:
        return error(blocked, "개인 검증 단계에서는 이 경로를 사용할 수 없습니다.")
    if request.method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
        return error(405, "지원하지 않는 요청입니다.")
    try:
        if int(request.headers.get("content-length", "0")) > MAX_BODY:
            return error(413, "요청 크기는 25 MiB 이하여야 합니다.")
    except ValueError:
        return error(400, "잘못된 요청 크기입니다.")
    # Buffer within a fixed limit before contacting AWS; never partially submit an order.
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                return error(413, "요청 크기는 25 MiB 이하여야 합니다.")
            body.extend(chunk)
    except ClientDisconnect:
        return Response(status_code=400)

    origin = request.app.state.origin
    raw_path = request.scope.get("raw_path", request.url.path.encode("utf-8"))
    query = request.scope.get("query_string", b"")
    # copy_with(raw_path=...) fixes the authority even for //host or encoded paths.
    target = httpx.URL(origin).copy_with(raw_path=raw_path + (b"?" + query if query else b""))
    excluded = connection_headers(request.headers.raw) | {
        b"host", b"content-length", b"forwarded", b"x-real-ip", b"accept-encoding",
    }
    headers = [(key, value) for key, value in request.headers.raw
               if key.lower() not in excluded and not key.lower().startswith(b"x-forwarded-")]
    headers.append((b"accept-encoding", b"identity"))
    # Construct Request directly: a shared HTTPX cookie jar must never become another user's cookie.
    upstream_request = httpx.Request(request.method, target, headers=headers, content=bytes(body))
    try:
        upstream = await request.app.state.client.send(upstream_request, stream=True)
    except httpx.HTTPError:
        return error(502, "AWS 응답을 확인할 수 없습니다. 주문 요청은 자동 재전송하지 않습니다. 거래소 주문 내역을 확인하세요.")

    excluded = connection_headers(upstream.headers.raw) | {b"server", b"x-zenthex-backend"}
    response_headers = []
    for key, value in upstream.headers.raw:
        if key.lower() in excluded:
            continue
        if key.lower() == b"location":
            location = value.decode("latin-1")
            parsed = urlsplit(location)
            if parsed.hostname == urlsplit(origin).hostname:
                # Relative redirect keeps the public Render address in the browser.
                location = (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
                location += "#" + parsed.fragment if parsed.fragment else ""
                value = location.encode("latin-1")
        response_headers.append((key, value))
    if raw_path.startswith(b"/api/"):
        response_headers = [(k, v) for k, v in response_headers if k.lower() != b"cache-control"]
        response_headers.append((b"cache-control", b"no-store"))
    response_headers.append((b"x-zenthex-backend", b"aws"))

    async def stream():
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()

    response = StreamingResponse(stream(), status_code=upstream.status_code)
    response.raw_headers = response_headers
    return response


app = Starlette(lifespan=lifespan, routes=[
    Route("/_gateway/health", readiness, methods=["GET"]),
    Route("/{path:path}", forward, methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]),
])
