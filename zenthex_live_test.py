#!/usr/bin/env python3
"""Arm a single-owner Upbit test after TLS checks; does not send exchange orders."""
import argparse
import getpass
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ENV_PATH = Path('/etc/zenthex/zenthex.env')
GUARD = Path('/var/lib/zenthex/trading/live-position.json')
OWNER_DEFAULT = '7foliath@naver.com'


def read_env(path=ENV_PATH):
    result = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip().strip('\"\'')
    return result


def request_json(url, post=False):
    req = urllib.request.Request(url, data=b'{}' if post else None,
                                 headers={'Content-Type':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=35) as response:
            return response.status, json.loads(response.read(65536))
    except urllib.error.HTTPError as error:
        return error.code, None


def preflight(ip, env):
    if not ipaddress.IPv4Address(ip).is_global or env.get('ZENTHEX_SERVER_PUBLIC_IP') != ip:
        raise RuntimeError('공인 IP와 서버 설정이 일치하지 않습니다.')
    if GUARD.exists():
        raise RuntimeError('보유/미확정 주문 기록이 남아 있습니다. 거래소 대조가 먼저입니다.')
    unit = Path('/etc/systemd/system/zenthex.service').read_text()
    if '--host 127.0.0.1' not in unit or '--workers 1' not in unit:
        raise RuntimeError('앱의 localhost 바인딩과 worker 1 설정을 확인하세요.')
    code, health = request_json(f'https://{ip}/api/health')
    if code != 200 or health.get('status') != 'ok':
        raise RuntimeError('신뢰할 수 있는 외부 HTTPS 연결 검사가 실패했습니다.')
    for route, post in [('/api/auth/signup',True),('/api/auth/password/reset',True),('/api/auth/dev/outbox',False),('/api/auth/phone/send-code',True)]:
        code, _ = request_json('https://'+ip+route,post)
        if code != 403:
            raise RuntimeError('개인 시험용 계정 보호가 적용되지 않았습니다: '+route)
    code, check = request_json(f'https://{ip}/api/finance/server-ip/verify')
    if code != 200 or not check.get('matches') or check.get('successful_checks') != 3:
        raise RuntimeError('실제 발신 IPv4가 설정값과 3회 일치하지 않습니다.')
    code, state = request_json('http://127.0.0.1:8000/api/finance/status')
    if code != 200 or state.get('state') != 'STOPPED':
        raise RuntimeError('엔진이 완전 정지 상태인지 먼저 확인하세요.')


def sqlite_path(env):
    value = env.get('ZENTHEX_DATABASE_URL','')
    if not value.startswith('sqlite:////'):
        raise RuntimeError('이 도구는 기존 VPS의 절대 경로 SQLite DB만 지원합니다.')
    path = Path(value[len('sqlite:///'):])
    if not path.is_file():
        raise RuntimeError('기존 DB를 찾지 못했습니다. 새 DB를 만들지 않습니다.')
    return path


def write_env(updates):
    old = ENV_PATH.stat()
    lines = [line for line in ENV_PATH.read_text().splitlines() if line.split('=',1)[0].strip() not in updates]
    lines.extend(key+'='+value for key,value in updates.items())
    fd, temporary = tempfile.mkstemp(dir=ENV_PATH.parent,prefix='zenthex.env.')
    try:
        with os.fdopen(fd,'w') as out:out.write('\n'.join(lines)+'\n')
        os.chmod(temporary,0o640)
        os.chown(temporary,old.st_uid,old.st_gid)
        os.replace(temporary,ENV_PATH)
    finally:Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ip')
    parser.add_argument('--owner-email',default=OWNER_DEFAULT)
    parser.add_argument('--arm',action='store_true',help='대표 비밀번호 재설정·세션 무효화·실거래 시작 권한 활성화. 주문은 보내지 않음')
    args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('sudo python3 zenthex_live_test.py <IP> [--arm]')
    env=read_env()
    allowed={OWNER_DEFAULT}|{x.strip().lower() for x in env.get('ZENTHEX_OWNER_EMAILS','').split(',') if x.strip()}
    email=args.owner_email.strip().lower()
    if email not in allowed:raise SystemExit('서버 설정에 등록된 대표 이메일만 사용할 수 있습니다.')
    preflight(args.ip,env)
    db_path=sqlite_path(env)
    print('HTTPS·외부 계정 보호·발신 IP·엔진 정지 확인 완료.')
    if not args.arm:
        print('점검만 수행했습니다. 실거래 설정과 DB를 변경하지 않았습니다.')
        return
    print('대표 계정:',email)
    print('새 비밀번호를 설정하고 기존 로그인 세션을 무효화합니다. 실제 매매 시작은 화면에서 직접 선택합니다.')
    password=getpass.getpass('새 대표 비밀번호 (12자 이상, 입력 내용은 보이지 않음): ')
    confirm=getpass.getpass('비밀번호 재입력: ')
    if len(password)<12 or password!=confirm:raise SystemExit('길이 또는 일치 확인 실패. 변경하지 않았습니다.')
    spec=importlib.util.spec_from_file_location('zenthex_password_hash','/opt/zenthex/app/auth/hash.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hashed=module.get_password_hash(password)
    if not hashed.startswith('pbkdf2_sha256$'):
        raise SystemExit('새 비밀번호 저장 모듈이 없습니다. HTTPS 설치를 먼저 완료하세요.')
    del password,confirm
    backup=Path('/var/backups/zenthex-security')/('live-'+str(time.time_ns()))
    backup.mkdir(parents=True,mode=0o700)
    shutil.copy2(ENV_PATH,backup/'zenthex.env')
    connection=sqlite3.connect(db_path)
    try:
        with sqlite3.connect(backup/'zenthex.db') as target:connection.backup(target)
        # Recheck immediately before changing settings. Never delete a position guard.
        preflight(args.ip,env)
        row=connection.execute('SELECT id FROM users WHERE lower(email)=?',(email,)).fetchone()
        with connection:
            if row:
                connection.execute("UPDATE users SET hashed_password=?, role='owner', plan='ultimate', approval_status='approved', is_active=1, password_reset_code=NULL, email_verification_code=NULL WHERE id=?",(hashed,row[0]))
            else:
                connection.execute("INSERT INTO users (email,hashed_password,full_name,role,plan,approval_status,is_active,email_verified,studio_generations_left) VALUES (?,?,'ZENTHEX Owner','owner','ultimate','approved',1,0,999999)",(email,hashed))
    finally:connection.close()
    write_env({'ZENTHEX_ENABLE_LIVE_TRADING':'true','ZENTHEX_TOKEN_SECRET':secrets.token_hex(32),
               'ZENTHEX_ENABLE_DEV_OUTBOX':'false','ZENTHEX_ENABLE_MOCK_PAYMENT':'false'})
    subprocess.run(['systemctl','restart','zenthex'],check=True)
    for _ in range(30):
        try:
            code,state=request_json('http://127.0.0.1:8000/api/finance/status')
            if code==200 and state.get('liveTradingEnabled'):
                print('대표 개인 실거래 시작 권한 활성화 완료. 코인 주문은 보내지 않았습니다.')
                print('기존 로그인은 만료됩니다. HTTPS 화면에서 새 비밀번호로 로그인하세요.')
                print('API 키와 투자금은 HTTPS 화면에 직접 입력하세요. 채팅·GitHub에 올리지 마세요.')
                print('백업:',backup)
                return
        except (OSError,ValueError):pass
        time.sleep(1)
    raise SystemExit('설정은 저장됐지만 재시작 확인에 실패했습니다. journalctl -u zenthex -n 40 --no-pager 로 확인하세요.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError) as exc:raise SystemExit('중단: '+str(exc))
