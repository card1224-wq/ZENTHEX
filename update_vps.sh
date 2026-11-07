#!/usr/bin/env bash
# Zenthex 코드 업데이트 (DB / 환경변수 / 업로드 파일은 그대로 유지)
# 사용법: 새 코드 폴더(main.py 가 있는 폴더) 안에서
#   sudo bash deploy/update_vps.sh
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "sudo bash deploy/update_vps.sh 로 실행하세요."; exit 1; fi

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/zenthex/app

if [ -f /var/lib/zenthex/zenthex.db ]; then
  cp /var/lib/zenthex/zenthex.db "/var/lib/zenthex/zenthex-backup-$(date +%Y%m%d-%H%M%S).db"
fi

if [ -f /var/lib/zenthex/trading/live-position.json ]; then
  echo "실주문/보유 기록이 남아 업데이트를 중단합니다. 먼저 거래소와 보유 상태를 확인하세요."
  exit 1
fi

echo "주의: 실거래 봇이 코인을 보유 중이면 먼저 화면에서 '매도 후 정지'를 누른 뒤 업데이트하세요."
rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude 'uploads' --exclude '*.db' --exclude 'static/models' "$SRC_DIR"/ "$APP_DIR"/
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
chown -R zenthex:zenthex /opt/zenthex
systemctl restart zenthex
sleep 4
curl -fsS http://127.0.0.1:8000/api/health && echo "" && echo "업데이트 완료"
