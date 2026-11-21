#!/usr/bin/env python3
"""HTTPS for the existing single-owner test VPS; no exchange orders or live flag changes."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request


PASSWORD_MODULE = "import hashlib\nimport hmac\nimport secrets\n\nITERATIONS = 600000\n\n\ndef get_password_hash(password: str) -> str:\n    salt = secrets.token_hex(16)\n    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()\n    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'\n\n\ndef verify_password(password: str, hashed_password: str) -> bool:\n    try:\n        if hashed_password.startswith('pbkdf2_sha256$'):\n            algorithm, count, salt, expected = hashed_password.split('$')\n            count = int(count)\n            if not 100000 <= count <= 2000000 or len(salt) != 32 or len(expected) != 64:\n                return False\n            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), count).hex()\n            return hmac.compare_digest(actual, expected)\n        if len(hashed_password) == 64:\n            return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), hashed_password)\n    except (AttributeError, TypeError, ValueError):\n        return False\n    return False\n"

def public_ip(value):
    address = ipaddress.IPv4Address(value)
    if not address.is_global:
        raise argparse.ArgumentTypeError('공인 IPv4가 필요합니다.')
    return str(address)


def proxy():
    return '''proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;'''


def nginx_config(ip, tls=False, cert_dir=None):
    ip = public_ip(ip)
    challenge = '''location ^~ /.well-known/acme-challenge/ {
        root /var/lib/zenthex-acme;
        try_files $uri =404;
    }'''
    protected = '''# Private owner testing only. Repair the underlying account flows before public signup.
    location ~ ^/api/auth/(signup(?:/|$)|password(?:/|$)|dev(?:/|$)|phone(?:/|$)) { return 403; }
    location ~ /\\. { return 404; }
    location = /api/auth/login {
        limit_req zone=zenthex_login burst=5 nodelay;
        limit_req_status 429;
        ''' + proxy() + '''
    }
    location / {
        ''' + proxy() + '''
    }'''
    common = '''server_tokens off;
    client_max_body_size 25M;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header Referrer-Policy same-origin always;'''
    result = 'limit_req_zone $binary_remote_addr zone=zenthex_login:10m rate=5r/m;\n'
    result += f'''server {{
    listen 80 default_server;
    server_name {ip};
    {common}
    {challenge}
'''
    if tls:
        result += f'    location / {{ return 308 https://{ip}$request_uri; }}\n}}\n'
        cert_dir = cert_dir or f'/etc/letsencrypt/live/zenthex-ip-{ip}'
        result += f'''server {{
    listen 443 ssl default_server;
    server_name {ip};
    ssl_certificate {cert_dir}/fullchain.pem;
    ssl_certificate_key {cert_dir}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    {common}
    {protected}
}}
'''
    else:
        result += protected + '\n}\n'
    return result


def run(*args):
    subprocess.run(args, check=True)


def write_file(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.')
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def install_nginx(content):
    path = Path('/etc/nginx/sites-available/zenthex')
    previous = path.read_text()
    write_file(path, content)
    try:
        run('nginx', '-t')
        run('systemctl', 'reload', 'nginx')
    except BaseException:
        write_file(path, previous)
        run('nginx', '-t')
        run('systemctl', 'reload', 'nginx')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ip', type=public_ip)
    parser.add_argument('--email')
    parser.add_argument('--print-nginx', action='store_true', help='출력만 하며 서버를 변경하지 않음')
    args = parser.parse_args()
    if args.print_nginx:
        print(nginx_config(args.ip, tls=True), end='')
        return
    if os.geteuid() != 0:
        raise SystemExit('sudo python3 zenthex_https_setup.py <IP> --email <본인 이메일>')
    if not args.email:
        env_path=Path('/etc/zenthex/zenthex.env')
        if env_path.is_file():
            for line in env_path.read_text().splitlines():
                if line.startswith('ZENTHEX_OWNER_EMAILS='):
                    args.email=line.split('=',1)[1].strip().strip(chr(34)+chr(39)).split(',')[0].strip()
                    break
    if not args.email or '@' not in args.email or any(c.isspace() for c in args.email):
        raise SystemExit('인증서 관리용 본인 이메일을 --email로 입력하세요.')
    site = Path('/etc/nginx/sites-available/zenthex')
    enabled = Path('/etc/nginx/sites-enabled/zenthex')
    if not site.is_file() or not enabled.exists() or enabled.resolve() != site.resolve():
        raise SystemExit('기존 Zenthex nginx 설정 경로가 다릅니다. 자동 변경을 중단합니다.')
    if Path('/var/lib/zenthex/trading/live-position.json').exists():
        raise SystemExit('보유/미확정 실주문 기록이 있습니다. 거래소 대조 후 진행하세요.')
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5) as response:
        if json.load(response).get('status') != 'ok':
            raise SystemExit('기존 프로그램 상태를 먼저 확인하세요.')
    with urllib.request.urlopen('http://127.0.0.1:8000/api/finance/status', timeout=5) as response:
        if json.load(response).get('state') != 'STOPPED':
            raise SystemExit('엔진을 먼저 완전 정지하세요. 매매 중 설정을 변경하지 않습니다.')
    backup = Path('/var/backups/zenthex-security') / str(time.time_ns())
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(site, backup/'nginx-zenthex.conf')
    run('nginx', '-t')
    run('apt-get', 'update')
    run('apt-get', 'install', '-y', 'python3-venv', 'curl', 'ca-certificates')
    certbot = '/opt/zenthex-certbot/bin/certbot'
    if not Path(certbot).exists():
        run('python3', '-m', 'venv', '/opt/zenthex-certbot')
    run('/opt/zenthex-certbot/bin/pip', 'install', '--upgrade', 'certbot>=5.4,<6')
    run(certbot, '--version')
    Path('/var/lib/zenthex-acme/.well-known/acme-challenge').mkdir(parents=True, exist_ok=True)
    install_nginx(nginx_config(args.ip))
    # If issuance fails, the existing HTTP app stays available with the private-test guards.
    name = 'zenthex-ip-'+args.ip
    run(certbot, 'certonly', '--non-interactive', '--agree-tos', '--email', args.email,
        '--webroot', '--webroot-path', '/var/lib/zenthex-acme', '--ip-address', args.ip,
        '--required-profile', 'shortlived', '--cert-name', name, '--keep-until-expiring')
    install_nginx(nginx_config(args.ip, tls=True))
    hook = '/usr/local/sbin/zenthex-certificate-reload'
    write_file(hook, '#!/bin/sh\nset -eu\n/usr/sbin/nginx -t\n/usr/bin/systemctl reload nginx\n', 0o755)
    write_file('/etc/systemd/system/zenthex-cert-renew.service', f'''[Unit]
Description=Renew Zenthex IP certificate
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart={certbot} renew --cert-name {name} --quiet --deploy-hook {hook}
''')
    write_file('/etc/systemd/system/zenthex-cert-renew.timer', '''[Unit]
Description=Check Zenthex certificate every six hours
[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
RandomizedDelaySec=1800
Persistent=true
[Install]
WantedBy=timers.target
''')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', '--now', 'zenthex-cert-renew.timer')
    run(certbot, 'renew', '--cert-name', name, '--dry-run', '--run-deploy-hooks', '--deploy-hook', hook)
    run('curl', '--noproxy', '*', '--connect-to', f'{args.ip}:443:127.0.0.1:443',
        '-fsS', '--max-time', '10', f'https://{args.ip}/api/health')
    # Migrate newly-set passwords without invalidating existing legacy-password logins.
    source_hash = Path(__file__).resolve().parent / 'auth/hash.py'
    app_hash = Path('/opt/zenthex/app/auth/hash.py')
    if not source_hash.is_file() or not app_hash.is_file():
        raise SystemExit('HTTPS는 설정됐지만 auth/hash.py 경로가 다릅니다. 비밀번호 모듈 설치를 중단합니다.')
    shutil.copy2(source_hash, backup/'source-auth-hash.py')
    shutil.copy2(app_hash, backup/'app-auth-hash.py')
    try:
        write_file(source_hash, PASSWORD_MODULE)
        write_file(app_hash, PASSWORD_MODULE)
        run('systemctl', 'restart', 'zenthex')
        ready = False
        for _ in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2) as response:
                    if json.load(response).get('status') == 'ok':
                        ready = True
                        break
            except OSError:
                pass
            time.sleep(1)
        if not ready:
            raise RuntimeError('비밀번호 모듈 적용 후 앱 상태 검사 실패')
    except BaseException:
        shutil.copy2(backup/'source-auth-hash.py',source_hash)
        shutil.copy2(backup/'app-auth-hash.py',app_hash)
        run('systemctl','restart','zenthex')
        raise
    # Keep the local repair manifest from reverting the new compatible password module.
    manifest_path = source_hash.parent.parent / 'UPDATE_MANIFEST.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        rows = [row for row in manifest['files'] if row['path'] != 'auth/hash.py']
        rows.append({'path':'auth/hash.py','sha256':hashlib.sha256(PASSWORD_MODULE.encode()).hexdigest()})
        manifest['files'] = rows
        manifest['securityOverlay'] = '2026-11-21-private-test'
        shutil.copy2(manifest_path,backup/'UPDATE_MANIFEST.json')
        write_file(manifest_path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('새 비밀번호는 솔트와 PBKDF2로 저장합니다. 기존 비밀번호 로그인은 호환됩니다.')
    print('\n서버 내부 HTTPS·인증서 신뢰 검사 완료. 외부 443 포트와 브라우저 접속은 별도 확인해야 합니다.')
    print('HTTPS 주소: https://'+args.ip+'/finance.html')
    print('개인 시험 중 공개 가입·전화 인증·비밀번호 초기화·개발 outbox는 외부에서 차단됩니다.')
    print('기존 로그인 유지. 기존 계정이 없거나 비밀번호를 잊었다면 서버에서 별도로 복구해야 합니다.')
    print('실거래 설정은 변경하지 않았습니다. nginx 원본 백업:', backup)


if __name__ == '__main__':
    main()
