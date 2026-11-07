#!/usr/bin/env bash
# Run on the Ubuntu VPS after the updated source is deployed.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "sudo bash deploy/configure_runtime.sh <고정 IPv4>"; exit 1; fi
if [ "$#" -ne 1 ]; then echo "AWS에 연결한 고정 IPv4 하나를 인수로 넣으세요."; exit 1; fi
python3 - "$1" <<'PY'
import ipaddress
import os
import shutil
import sys
import time
from pathlib import Path

ip = ipaddress.IPv4Address(sys.argv[1])
if not ip.is_global:
    raise SystemExit("유효한 공인 IPv4가 아닙니다.")
path = Path('/etc/zenthex/zenthex.env')
if not path.is_file():
    raise SystemExit("먼저 setup_vps.sh로 설치해야 합니다.")
updates = {
    'ZENTHEX_SERVER_PUBLIC_IP': str(ip),
    'ZENTHEX_ENABLE_LIVE_TRADING': 'false',
    'ZENTHEX_TRADING_STATE_DIR': '/var/lib/zenthex/trading',
}
shutil.copy2(path, path.with_name(f'zenthex.env.backup-{time.time_ns()}'))
result = []
for line in path.read_text().splitlines():
    key = line.split('=', 1)[0]
    if key in updates:
        continue
    result.append(line)
result.extend(f'{key}={value}' for key, value in updates.items())
path.write_text('\n'.join(result) + '\n')
os.chmod(path, 0o640)
print(f'발신 IP 기준값 설정 완료: {ip}. 실거래 잠금 유지.')
PY
systemctl restart zenthex
systemctl is-active zenthex
