"""Validate the server's IPv4 path; configuration alone never proves a static IP."""
import asyncio
import ipaddress
import os
import urllib.request


IPV4_SOURCES = ("https://api4.ipify.org", "https://checkip.amazonaws.com")


def public_ipv4(value: str) -> str:
    ip = ipaddress.IPv4Address(value.strip())
    if not ip.is_global:
        raise ValueError("A public IPv4 address is required")
    return str(ip)


def configured_server_ip() -> tuple[str, str]:
    value = os.getenv("ZENTHEX_SERVER_PUBLIC_IP", "").strip()
    if not value:
        return "", "unset"
    try:
        return public_ipv4(value), "env"
    except ValueError:
        return "", "invalid"


def detect_outbound_ip() -> str:
    for url in IPV4_SOURCES:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "zenthex-ip-check"})
            with urllib.request.urlopen(request, timeout=4) as response:
                return public_ipv4(response.read(128).decode("ascii").strip())
        except (OSError, ValueError, UnicodeError):
            continue
    raise RuntimeError("서버의 실제 공인 IPv4를 확인하지 못했습니다.")


async def verify_server_ip() -> dict:
    configured_ip, source = configured_server_ip()
    observed = []
    if configured_ip:
        for _ in range(3):
            try:
                observed.append(await asyncio.to_thread(detect_outbound_ip))
            except Exception:
                pass
    complete = len(observed) == 3
    stable = complete and len(set(observed)) == 1
    matches = stable and observed[0] == configured_ip
    if not configured_ip:
        message = "서버 환경변수 ZENTHEX_SERVER_PUBLIC_IP에 AWS에 연결한 고정 IPv4를 설정하세요."
    elif matches:
        message = f"현재 발신 IPv4가 설정값 {configured_ip}와 3회 일치합니다. AWS의 고정 IP 연결은 별도로 유지해야 합니다."
    elif not complete:
        message = "실제 발신 IPv4를 3회 모두 확인하지 못했습니다. 실거래를 시작할 수 없습니다."
    else:
        message = "설정한 IPv4와 실제 발신 경로가 일치하지 않습니다. AWS 연결과 서버 설정을 확인하세요."
    return {
        "status": "success" if matches else "error",
        "configured_ip": configured_ip,
        "configured_source": source,
        "outbound_ip": observed[-1] if observed else None,
        "observed_ips": sorted(set(observed)),
        "successful_checks": len(observed),
        "matches": matches,
        "is_stable": stable,
        "message": message,
    }
