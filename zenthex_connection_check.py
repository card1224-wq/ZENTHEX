#!/usr/bin/env python3
"""Read-only AWS / public Render cutover checks. Never arms trading or sends orders."""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import urllib.error
import urllib.request

AWS = "https://13.124.81.242"
PUBLIC = "https://zenthex-saas.onrender.com"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(origin, path):
    request = urllib.request.Request(origin + path, headers={"Cache-Control": "no-cache"})
    try:
        with opener.open(request, timeout=40) as response:
            data = response.read(1024 * 1024)
            try:
                data = json.loads(data)
            except (ValueError, UnicodeDecodeError):
                data = None
            return response.status, data, response.headers
    except urllib.error.HTTPError as exc:
        return exc.code, None, exc.headers


def require(condition, message):
    if not condition:
        raise RuntimeError(message)
    print("PASS:", message)


def check_public(origin, gateway=False, outbound=False):
    code, health, headers = get(origin, "/api/health")
    require(code == 200 and isinstance(health, dict) and health.get("status") == "ok"
            and health.get("service") == "zenthex-saas", origin + " HTTPS / 앱 상태")
    if gateway:
        require(headers.get("X-Zenthex-Backend") == "aws", "기존 Render 주소의 요청이 AWS로 전달됨")
        code, state, _ = get(origin, "/_gateway/health")
        require(code == 200 and isinstance(state, dict) and state.get("mode") == "render-gateway",
                "Render 전달 서버 상태")
    code, info, _ = get(origin, "/api/finance/server-ip")
    require(code == 200 and isinstance(info, dict) and info.get("server_ip") == "13.124.81.242",
            "화면에서 조회하는 거래 서버 IP = 13.124.81.242")
    for route in ["/api/auth/signup", "/api/auth/password/question", "/api/auth/dev/outbox", "/api/auth/phone/send-code"]:
        code, _, _ = get(origin, route)
        require(code == 403, "개인 시험용 접근 보호 " + route)
    for route in ["/finance.html", "/studio.html", "/stock.html", "/research.html", "/login.html"]:
        code, _, _ = get(origin, route)
        require(code == 200, "페이지 응답 " + route)
    if outbound:
        code, info, _ = get(origin, "/api/finance/server-ip/verify")
        require(code == 200 and isinstance(info, dict) and info.get("matches") is True
                and info.get("successful_checks") == 3 and info.get("outbound_ip") == "13.124.81.242",
                "실제 거래 서버 발신 IP가 3회 모두 AWS 고정 IP와 일치")


def check_aws_local():
    env = {}
    for line in Path("/etc/zenthex/zenthex.env").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip("\"'")
    require(env.get("ZENTHEX_SERVER_PUBLIC_IP") == "13.124.81.242", "AWS 고정 IP 환경 설정")
    require(env.get("ZENTHEX_ENABLE_LIVE_TRADING", "false").lower() == "false", "전환 전 실거래 잠금 유지")
    secret = env.get("ZENTHEX_TOKEN_SECRET", "")
    require(len(secret) >= 32 and secret != "zenthex-local-dev-token-secret", "개별 로그인 서명 비밀키 설정")
    crypto = env.get("ZENTHEX_CRYPTO_KEY", "")
    require(len(crypto.encode()) >= 32 and not crypto.startswith("zenthex_super_secret"), "개별 API 키 암호화 비밀키 설정")
    require(env.get("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() == "false", "개발용 인증 정보 노출 차단 설정")
    require(env.get("ZENTHEX_ENABLE_MOCK_PAYMENT", "false").lower() == "false", "모의 결제 차단 설정")
    require(not Path("/var/lib/zenthex/trading/live-position.json").exists(), "보유·미확정 주문 보호 기록 없음")
    unit = Path("/etc/systemd/system/zenthex.service").read_text()
    require("--host 127.0.0.1" in unit and "--workers 1" in unit, "외부 8000 포트 미노출 / 단일 엔진 설정")
    code, state, _ = get("http://127.0.0.1:8000", "/api/finance/status")
    require(code == 200 and isinstance(state, dict) and state.get("state") == "STOPPED", "AWS 엔진 완전 정지 상태")
    result = subprocess.run(["systemctl", "is-active", "zenthex-cert-renew.timer"], capture_output=True, text=True)
    require(result.returncode == 0 and result.stdout.strip() == "active", "인증서 자동 갱신 타이머 활성화")
    db_url = env.get("ZENTHEX_DATABASE_URL", "")
    require(db_url.startswith("sqlite:////"), "기존 AWS DB 절대 경로 설정")
    db_path = Path(db_url[len("sqlite:///"):])
    require(db_path.is_file(), "기존 AWS DB 존재 (새 DB 생성하지 않음)")
    with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: db.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0]
                  for name in ["users", "trade_records", "billing_history", "subscriptions", "support_tickets"] if name in tables}
    print("AWS 데이터 건수:", json.dumps(counts, ensure_ascii=False))
    print("Render의 기존 계정·결제·작업 파일과 비교가 필요합니다. 이 검사는 데이터를 이전하거나 지우지 않습니다.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws-local", action="store_true", help="AWS SSH에서 sudo로 기존 환경과 DB를 읽기만 함")
    parser.add_argument("--public", action="store_true", help="전환 후 기존 Render 주소가 AWS로 연결되는지 확인")
    parser.add_argument("--verify-outbound", action="store_true", help="추가로 실제 AWS 발신 IP 3회 확인 (주문 없음)")
    args = parser.parse_args()
    try:
        if args.aws_local:
            check_aws_local()
        check_public(PUBLIC if args.public else AWS, gateway=args.public, outbound=args.verify_outbound)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        raise SystemExit("CHECK FAILED: " + str(exc))
    print("검사 완료. 설정·계정·DB·실거래 권한을 변경하지 않았고 거래소 주문을 보내지 않았습니다.")


if __name__ == "__main__":
    main()
