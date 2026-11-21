#!/usr/bin/env python3
"""One-time AWS installation. No password reset, live flag change or exchange order."""
from pathlib import Path
import os
import pwd
import shutil
import subprocess
import sys


def install():
    if os.geteuid() != 0:
        raise SystemExit('AWS SSH에서 sudo python3 deploy/install_auto_update.py 로 실행하세요.')
    source = Path(__file__).resolve().parent
    if not (source/'auto_update.py').is_file():
        raise SystemExit('auto_update.py 파일이 없습니다.')
    if not Path('/etc/systemd/system/zenthex.service').is_file():
        raise SystemExit('기존 zenthex 서비스가 설치된 AWS에서 실행하세요.')
    try:
        user = pwd.getpwnam('zenthex-build')
    except KeyError:
        subprocess.run(['useradd', '--system', '--create-home', '--home-dir', '/var/lib/zenthex-build', '--shell', '/usr/sbin/nologin', 'zenthex-build'], check=True)
        user = pwd.getpwnam('zenthex-build')
    home = Path('/var/lib/zenthex-build')
    home.mkdir(mode=0o750, exist_ok=True)
    os.chown(home, user.pw_uid, user.pw_gid)
    dest = Path('/usr/local/lib/zenthex')
    dest.mkdir(mode=0o755, parents=True, exist_ok=True)
    shutil.copyfile(source/'auto_update.py', dest/'auto_update.py')
    os.chown(dest/'auto_update.py', 0, 0)
    os.chmod(dest/'auto_update.py', 0o644)
    # Python module launch survives release-directory moves (venv console scripts do not).
    unit = Path('/etc/systemd/system/zenthex.service.d')
    unit.mkdir(parents=True, exist_ok=True)
    (unit/'deployment.conf').write_text('''[Service]
ExecStart=
ExecStart=/opt/zenthex/app/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers
''')
    Path('/etc/systemd/system/zenthex-auto-update.service').write_text('''[Unit]
Description=Zenthex verified GitHub update (defers while trading is armed or busy)
After=network-online.target zenthex.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/zenthex/auto_update.py
TimeoutStartSec=40min
UMask=0027
Nice=10
CPUQuota=50%
MemoryMax=500M
''')
    Path('/etc/systemd/system/zenthex-auto-update.timer').write_text('''[Unit]
Description=Check Zenthex GitHub main every two minutes

[Timer]
OnBootSec=2min
OnUnitInactiveSec=2min
RandomizedDelaySec=15
Persistent=true

[Install]
WantedBy=timers.target
''')
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'zenthex-auto-update.timer'], check=True)
    print('자동 배포 타이머 설치 완료. 약 2분 간격으로 GitHub main을 확인합니다.')
    print('실거래 활성화·엔진 실행·보유/미확정 주문·Studio 생성 중에는 배포를 보류합니다.')
    print('지금 확인: sudo systemctl start zenthex-auto-update.service')
    print('결과 보기: sudo journalctl -u zenthex-auto-update -n 60 --no-pager')
    print('중지: sudo systemctl disable --now zenthex-auto-update.timer')


if __name__ == '__main__':
    install()
