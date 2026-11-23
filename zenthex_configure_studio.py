#!/usr/bin/env python3
"""Configure the AWS image provider interactively; never prints or uploads the key."""
import getpass
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time
from zenthex_live_test import ENV_PATH, GUARD, read_env, request_json, write_env


def valid_api_key(key):
    # Accept both legacy and current key prefixes, but never terminal controls.
    return 20 <= len(key) <= 4096 and all(33 <= ord(c) <= 126 for c in key) and not any(c in key for c in "\"'\\")


def check_idle():
    if read_env().get('ZENTHEX_ENABLE_LIVE_TRADING', 'false').lower() == 'true':
        raise SystemExit('실거래가 활성화되어 있습니다. 설정을 변경하지 않았습니다.')
    code, state = request_json('http://127.0.0.1:8000/api/modules/status')
    if code != 200 or not isinstance(state, dict):
        raise SystemExit('현재 작업 상태를 확인하지 못했습니다. 변경하지 않았습니다.')
    deployment = state.get('deployment', {})
    trading = state.get('trading', {})
    if (deployment.get('engineState') != 'STOPPED'
            or any(deployment.get(k) is not False for k in ('engineTaskActive', 'hasPosition', 'studioBusy'))
            or trading.get('liveEnabled') is not False
            or trading.get('recoveryRequired') is not False or GUARD.exists()):
        raise SystemExit('거래·생성 작업 또는 주문 복구 상태를 먼저 확인하세요. 변경하지 않았습니다.')


def main():
    if os.geteuid() != 0:
        raise SystemExit('AWS SSH에서 sudo python3 zenthex_configure_studio.py 로 실행하세요.')
    check_idle()
    print('키를 붙여넣고 Enter를 한 번 누르세요. 글자와 별표는 표시되지 않습니다.')
    key=getpass.getpass('Google AI Studio API 키: ')
    if not valid_api_key(key):
        raise SystemExit('공백·제어문자 또는 잘못된 문자가 포함된 키입니다. 저장하지 않았습니다. 키만 다시 복사해 실행하세요.')
    model=input('이미지 모델 [gemini-3.1-flash-image]: ').strip() or 'gemini-3.1-flash-image'
    if not model.startswith('gemini-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-._' for c in model):
        raise SystemExit('모델 이름을 확인하세요. 저장하지 않았습니다.')
    check_idle()
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
