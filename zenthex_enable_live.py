#!/usr/bin/env python3
"""Enable owner-only Upbit start permission, retaining account passwords. Does not place orders."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

from zenthex_live_test import ENV_PATH, preflight, read_env, request_json, sqlite_path, write_env


def validate_owner(env):
    emails = {'7foliath@naver.com'} | {s.strip().lower() for s in env.get('ZENTHEX_OWNER_EMAILS', '').split(',') if s.strip()}
    db = sqlite_path(env)
    with sqlite3.connect(db.as_uri()+'?mode=ro', uri=True) as c:
        rows = c.execute("SELECT email, role, approval_status, is_active FROM users WHERE role='owner'").fetchall()
    if not any(email.lower() in emails and role == 'owner' and approval == 'approved' and active for email, role, approval, active in rows):
        raise RuntimeError('등록된 대표 계정을 확인하지 못했습니다. 계정을 새로 만들거나 변경하지 않습니다.')


def enable(ip, apply=False):
    env = read_env()
    preflight(ip, env)
    validate_owner(env)
    print('HTTPS·발신 IP·정지 상태·대표 계정 확인 완료. 기존 비밀번호를 유지합니다.')
    if not apply:
        print('점검만 수행했습니다. 활성화: 같은 명령 뒤에 --enable 추가')
        return
    backup = Path('/var/backups/zenthex-security')/('live-permission-'+str(time.time_ns()))
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(ENV_PATH, backup/'zenthex.env')
    os.chmod(backup/'zenthex.env', 0o600)
    preflight(ip, env)
    write_env({'ZENTHEX_ENABLE_LIVE_TRADING':'true'})
    try:
        subprocess.run(['systemctl', 'restart', 'zenthex'], check=True)
        for _ in range(30):
            try:
                code, state = request_json('http://127.0.0.1:8000/api/finance/status')
                if code == 200 and state.get('liveTradingEnabled') and state.get('state') == 'STOPPED':
                    print('업비트 실거래 시작 권한 활성화 완료. 주문은 실행하지 않았습니다.')
                    print('대표 비밀번호·API 키·DB·자동매매 시작 상태는 변경하지 않았습니다.')
                    print('실거래 활성화 동안 자동 배포는 보류됩니다. 백업:', backup)
                    return
            except (OSError, ValueError):
                pass
            time.sleep(1)
        raise RuntimeError('활성화 후 서버 상태를 확인하지 못했습니다.')
    except Exception as error:
        # Do not restart a possibly active owner-started engine to undo an uncertain result.
        # The saved env backup supports manual recovery after checking the exchange.
        raise RuntimeError("설정은 저장됐지만 서버 확인이 실패했습니다. 시작 버튼을 누르지 말고 서버 상태를 확인하세요. 백업: " + str(backup)) from error



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ip')
    p.add_argument('--enable', action='store_true')
    args = p.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('AWS SSH에서 sudo python3 zenthex_enable_live.py 13.124.81.242 [--enable]')
    try:
        with open('/run/zenthex-deploy.lock', 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            enable(args.ip, args.enable)
    except BlockingIOError:
        raise SystemExit('배포/설정 작업이 진행 중입니다. 완료 후 다시 실행하세요.')
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit('중단: '+str(error))
