#!/usr/bin/env bash
# Compatibility entrypoint: use the tested isolated deployment controller.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(id -u)" -ne 0 ]; then echo "sudo bash deploy/update_vps.sh 로 실행하세요."; exit 1; fi
python3 deploy/install_auto_update.py
systemctl start zenthex-auto-update.service
journalctl -u zenthex-auto-update -n 40 --no-pager
