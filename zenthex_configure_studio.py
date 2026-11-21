#!/usr/bin/env python3
"""Configure the AWS image provider interactively; never prints or uploads the key."""
import getpass
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time
from zenthex_live_test import ENV_PATH, read_env, request_json, write_env


def main():
    if os.geteuid() != 0:
        raise SystemExit('AWS SSH에서 sudo python3 zenthex_configure_studio.py 로 실행하세요.')
    env=read_env()
    if env.get('ZENTHEX_ENABLE_LIVE_TRADING','false').lower() == 'true':
        raise SystemExit('실거래가 활성화되어 있어 재시작하지 않습니다. 거래 중이 아닌 배포 단계에서 설정하세요.')
    code, state=request_json('http://127.0.0.1:8000/api/finance/status')
    if code != 200 or state.get('state') != 'STOPPED' or state.get('heldBtc'):
        raise SystemExit('엔진 정지 및 보유 상태를 확인하지 못했습니다. 변경하지 않았습니다.')
    key=getpass.getpass('Google AI Studio API 키 (입력은 화면에 표시되지 않음): ').strip()
    if len(key)<20 or any(c.isspace() for c in key):
        raise SystemExit('키 형식을 확인하세요. 저장하지 않았습니다.')
    model=input('이미지 모델 [gemini-3.1-flash-image]: ').strip() or 'gemini-3.1-flash-image'
    if not model.startswith('gemini-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-._' for c in model):
        raise SystemExit('모델 이름을 확인하세요. 저장하지 않았습니다.')
    backup=Path('/var/backups/zenthex-security')/('studio-'+str(time.time_ns()))
    backup.mkdir(mode=0o700,parents=True)
    shutil.copy2(ENV_PATH,backup/'zenthex.env')
    os.chmod(backup/'zenthex.env',0o600)
    write_env({'GEMINI_API_KEY':key,'ZENTHEX_GOOGLE_AI_STUDIO_MODEL':model})
    del key
    subprocess.run(['systemctl','restart','zenthex'],check=True)
    print('AWS Studio 설정 저장 완료. 키는 출력하지 않았습니다.')
    print('웹의 실제 생성 요청으로 모델 권한·결제 한도를 확인하세요. 설정만으로 생성 성공을 보장하지 않습니다.')


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('AWS SSH에서 sudo python3 zenthex_configure_studio.py 로 실행하세요.')
    with open('/run/zenthex-deploy.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('배포/설정 작업 중입니다. 완료 후 다시 실행하세요.')
        main()
