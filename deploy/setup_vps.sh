#!/usr/bin/env bash
# Zenthex 서울 VPS 최초 설치 스크립트 (Ubuntu 22.04 / 24.04)
# 사용법: 앱 폴더(main.py 가 있는 폴더) 안에서
#   sudo bash deploy/setup_vps.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "sudo bash deploy/setup_vps.sh 로 실행하세요."; exit 1; fi

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/zenthex/app
ENV_FILE=/etc/zenthex/zenthex.env

echo "[1/7] 필수 프로그램 설치"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx rsync curl libgl1 libglib2.0-0

echo "[2/7] zenthex 사용자와 폴더 준비"
id zenthex >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin zenthex
mkdir -p "$APP_DIR" /var/lib/zenthex /etc/zenthex

echo "[3/7] 앱 파일 복사"
if [ "$SRC_DIR" != "$APP_DIR" ]; then
  rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude 'uploads' --exclude '*.db' "$SRC_DIR"/ "$APP_DIR"/
fi
mkdir -p "$APP_DIR/uploads" "$APP_DIR/static/models"

echo "[4/7] 파이썬 패키지 설치 (몇 분 걸립니다)"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[5/7] 환경변수 파일 준비"
PUBLIC_IP="$(curl -4 -fsS --max-time 8 https://api4.ipify.org || curl -4 -fsS --max-time 8 https://checkip.amazonaws.com || true)"
PUBLIC_IP="$(echo "$PUBLIC_IP" | tr -d '[:space:]')"
if [ ! -f "$ENV_FILE" ]; then
  cp "$APP_DIR/deploy/zenthex.env.example" "$ENV_FILE"
  TOKEN_SECRET="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
  CRYPTO_KEY="$(python3 -c 'import secrets;print(secrets.token_hex(16))')"
  sed -i "s|^ZENTHEX_TOKEN_SECRET=.*|ZENTHEX_TOKEN_SECRET=${TOKEN_SECRET}|" "$ENV_FILE"
  sed -i "s|^ZENTHEX_CRYPTO_KEY=.*|ZENTHEX_CRYPTO_KEY=${CRYPTO_KEY}|" "$ENV_FILE"
fi
if [ -n "$PUBLIC_IP" ]; then
  sed -i "s|^ZENTHEX_SERVER_PUBLIC_IP=.*|ZENTHEX_SERVER_PUBLIC_IP=${PUBLIC_IP}|" "$ENV_FILE"
fi
chown root:zenthex "$ENV_FILE"; chmod 640 "$ENV_FILE"
chown -R zenthex:zenthex /opt/zenthex /var/lib/zenthex

echo "[6/7] 서비스 등록 (서버가 재부팅돼도 자동 실행)"
sed "s|__APP_DIR__|$APP_DIR|g" "$APP_DIR/deploy/zenthex.service" > /etc/systemd/system/zenthex.service
cp "$APP_DIR/deploy/nginx-zenthex.conf" /etc/nginx/sites-available/zenthex
ln -sf /etc/nginx/sites-available/zenthex /etc/nginx/sites-enabled/zenthex
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now zenthex
systemctl restart nginx

echo "[7/7] 동작 확인"
sleep 4
if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
  echo ""
  echo "=============================================="
  echo " Zenthex 설치 완료"
  echo " 홈페이지 주소 : http://${PUBLIC_IP}"
  echo " 거래소 허용 IP: ${PUBLIC_IP}"
  echo " (Lightsail 고정 IP가 이 값과 같은지 확인하세요)"
  echo " Gemini 키 입력: sudo nano /etc/zenthex/zenthex.env  -> 저장 후 sudo systemctl restart zenthex"
  echo "=============================================="
else
  echo "서비스 시작 실패. 아래 로그를 확인하세요:"
  journalctl -u zenthex -n 50 --no-pager
  exit 1
fi
