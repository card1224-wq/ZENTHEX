#!/usr/bin/env python3
"""Public-repository pull deployment. Installed controller is root-owned, builds run unprivileged.

No credentials, production databases or trading settings are read by build/test processes.
Never restarts an armed/live engine. The timer retries a deferred commit later.
"""
import argparse
import fcntl
import grp
import json
import math
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import urllib.error

REPO = 'https://github.com/card1224-wq/ZENTHEX.git'
BUILD_USER = 'zenthex-build'
BUILD_HOME = Path('/var/lib/zenthex-build')
CHECKOUT = BUILD_HOME / 'repository'
APP = Path('/opt/zenthex/app')
RELEASES = Path('/opt/zenthex/releases')
ENV = Path('/etc/zenthex/zenthex.env')
STATE = Path('/var/lib/zenthex-deploy')
SHARED_STUDIO = Path('/var/lib/zenthex/studio')


class DeployDeferred(RuntimeError):
    pass


def command(args, *, build=False, timeout=1200, capture=False):
    if build:
        args = ['runuser', '-u', BUILD_USER, '--', 'env', '-i',
                'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME='+str(BUILD_HOME), 'LANG=C.UTF-8'] + list(args)
    return subprocess.run(args, check=True, timeout=timeout, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def json_get(path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8000'+path, timeout=15) as response:
        return json.load(response)


def read_env():
    return {k.strip(): v.strip().strip('\"\'') for line in ENV.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#') and '=' in line
            for k, v in [line.split('=', 1)]}


def deployment_blocked(modules):
    if not isinstance(modules, dict):
        raise DeployDeferred('서버 상태 응답 형식을 확인할 수 없어 배포 보류')
    # Support the previously shipped studio.deployment response during upgrade.
    # Missing or malformed fields are never interpreted as an idle engine.
    studio = modules.get('studio')
    state = modules.get('deployment') if 'deployment' in modules else studio.get('deployment') if isinstance(studio, dict) else None
    trading = modules.get('trading')
    if not isinstance(state, dict) or not isinstance(trading, dict):
        raise DeployDeferred('배포 상태 정보가 없습니다. 앱을 중지하거나 교체하지 않습니다.')
    flags = ['engineTaskActive', 'hasPosition', 'studioBusy']
    if (not isinstance(state.get('engineState'), str)
            or any(type(state.get(k)) is not bool for k in flags)
            or type(trading.get('liveEnabled')) is not bool):
        raise DeployDeferred('배포 상태 정보가 불완전하여 배포 보류')
    return state['engineState'] != 'STOPPED' or any(state[k] for k in flags) or trading['liveEnabled']


def legacy_blocked(state):
    if not isinstance(state, dict) or not isinstance(state.get('state'), str) or type(state.get('isRunning')) is not bool:
        raise DeployDeferred('이전 서버의 엔진 정지 상태를 확인할 수 없습니다.')
    for key in ['heldBtc', 'avgBuyPrice']:
        value = state.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise DeployDeferred('이전 서버의 보유 상태를 확인할 수 없습니다.')
    return state['state'] != 'STOPPED' or state['isRunning'] or state['heldBtc'] != 0 or state['avgBuyPrice'] != 0


def idle_check():
    config = read_env()
    if config.get('ZENTHEX_ENABLE_LIVE_TRADING', '').lower() != 'false':
        raise DeployDeferred('실거래 활성화 중: 자동 배포 보류. 설정은 변경하지 않습니다.')
    pid = int(command(['systemctl', 'show', 'zenthex', '-p', 'MainPID', '--value'], capture=True).strip())
    runtime = dict(row.split(b'=', 1) for row in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in row)
    if runtime.get(b'ZENTHEX_ENABLE_LIVE_TRADING', b'').lower() != b'false':
        raise DeployDeferred('실행 중인 서버의 실거래 잠금이 확인되지 않아 배포 보류')
    guard = Path(config.get('ZENTHEX_TRADING_STATE_DIR', '/var/lib/zenthex/trading')) / 'live-position.json'
    if guard.exists():
        raise DeployDeferred('주문/보유 복구 기록이 있어 배포 보류')
    try:
        modules = json_get('/api/modules/status')
        blocked = deployment_blocked(modules)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        # Bootstrap the already installed, pre-capabilities build only when it is stopped.
        state = json_get('/api/finance/status')
        blocked = legacy_blocked(state)
    if blocked:
        raise DeployDeferred('엔진 또는 Studio 작업 중: 자동 배포 보류')
    return config, guard


def valid_member(member):
    path = PurePosixPath(member.name)
    if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
        raise RuntimeError('지원하지 않는 저장소 경로/링크')
    return not (any(p in {'.git', '.venv', '__pycache__', 'uploads', 'runtime-state'} for p in path.parts)
                or path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.pyc'}
                or path.name == '.env' or path.name.startswith('.env.') and path.name != '.env.example'
                or path.parts[:2] == ('static', 'models'))


def prepare(source, revision, destination):
    """Only called as the isolated build account, never as root."""
    if os.geteuid() == 0:
        raise RuntimeError('빌드/테스트를 root로 실행할 수 없습니다.')
    archive = destination.parent / ('source-'+revision+'.tar')
    subprocess.run(['git', '-C', str(source), 'archive', '--format=tar', '-o', str(archive), revision], check=True)
    destination.mkdir(mode=0o750)
    try:
        with tarfile.open(archive) as bundle:
            entries = bundle.getmembers()
            if sum(m.size for m in entries) > 250*1024*1024:
                raise RuntimeError('소스 크기 제한 초과')
            for member in entries:
                if valid_member(member):
                    bundle.extract(member, destination, filter='data')
    finally:
        archive.unlink(missing_ok=True)
    for required in ['main.py', 'modules_status.py', 'research/router.py', 'stock/toss_client.py', 'trading/orders.py', 'tests/test_trading_safety.py']:
        if not (destination/required).is_file():
            raise RuntimeError('올바른 폴더의 필수 파일이 없습니다: '+required)
    (destination/'RELEASE').write_text(revision+'\n')
    subprocess.run([sys.executable, '-m', 'venv', str(destination/'.venv')], check=True)
    python = str(destination/'.venv/bin/python')
    subprocess.run([python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(destination/'requirements.txt'), 'httpx==0.28.1'], check=True, timeout=1200)
    with tempfile.TemporaryDirectory(prefix='verify-', dir=BUILD_HOME) as temp:
        env = dict(os.environ, ZENTHEX_DATABASE_URL='sqlite:////'+str(Path(temp)/'verify.db').lstrip('/'),
                   ZENTHEX_TRADING_STATE_DIR=str(Path(temp)/'orders'),
                   ZENTHEX_ENABLE_LIVE_TRADING='false', ZENTHEX_TOKEN_SECRET='offline-verification-token-only')
        subprocess.run([python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=destination, env=env, check=True, timeout=180)
        subprocess.run([python, 'deploy/verify_app.py'], cwd=destination, env=env, check=True, timeout=45)
    # Move the venv later without embedding its old location in the production executable:
    # the launcher invokes its Python explicitly, never the pip/uvicorn entrypoint scripts.


def switch(target):
    link = APP.with_name('app.next')
    link.unlink(missing_ok=True)
    link.symlink_to(target, target_is_directory=True)
    os.replace(link, APP)


def private_backup(config):
    uri = config.get('ZENTHEX_DATABASE_URL', '')
    if not uri.startswith('sqlite:////'):
        raise RuntimeError('현재 자동 배포는 기존 절대 경로 SQLite DB만 지원합니다.')
    db_path = Path(uri[len('sqlite:///'):])
    if not db_path.is_file():
        raise RuntimeError('기존 DB를 찾지 못했습니다. 새 DB를 만들지 않습니다.')
    backup = Path('/var/backups/zenthex-security') / ('deploy-'+str(time.time_ns()))
    backup.mkdir(mode=0o700, parents=True)
    with sqlite3.connect(db_path.as_uri()+'?mode=ro', uri=True) as source:
        with sqlite3.connect(backup/'zenthex.db') as dest:
            source.backup(dest)
    os.chmod(backup/'zenthex.db', 0o600)
    return backup


def promote(candidate, revision):
    config, guard = idle_check()
    # Preserve outputs outside releases. Only fixed data directories, never DB/env/key files.
    shared = SHARED_STUDIO
    uid, gid = pwd.getpwnam('zenthex').pw_uid, grp.getgrnam('zenthex').gr_gid
    shared.mkdir(mode=0o750, parents=True, exist_ok=True)
    os.chown(shared, uid, gid)
    for relative, name in [('uploads', 'uploads'), ('static/models', 'models')]:
        dest = shared/name
        current = APP/relative
        if not dest.exists():
            if current.is_dir():
                shutil.copytree(current, dest, symlinks=True)
            else:
                dest.mkdir(mode=0o750)
            for item in [dest, *dest.rglob('*')]:
                os.chown(item, uid, gid, follow_symlinks=False)
        path = candidate/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                raise RuntimeError('빌드 출력에 예상하지 않은 링크가 있습니다.')
            path.rmdir()  # Imported app creates empty output directories during isolated tests.
        path.symlink_to(dest, target_is_directory=True)
    # Existing production DB/credentials are never copied into or overwritten by a release.
    idle_check()
    command(['systemctl', 'stop', 'zenthex'])
    old = None
    try:
        if guard.exists():
            raise RuntimeError('정지 직전 주문 복구 기록 발생: 배포 중단')
        backup = private_backup(config)
        RELEASES.mkdir(parents=True, exist_ok=True)
        # The service has UMask=0027: a root-owned 0750 parent otherwise blocks
        # the zenthex user from both the new release and the rollback baseline.
        os.chown(RELEASES, 0, gid)
        os.chmod(RELEASES, 0o750)
        final = RELEASES/revision
        if final.exists():
            if APP.resolve() == final.resolve():
                raise RuntimeError('실행 경로와 같은 릴리스는 덮어쓰지 않습니다.')
            # Preserve a failed inactive build; allow an explicit retry of that commit.
            final.rename(RELEASES/('failed-'+revision+'-'+str(time.time_ns())))
        # venv Python links are copied as links; chown never follows them.
        shutil.copytree(candidate, final, symlinks=True)
        for item in [final, *final.rglob('*')]:
            os.chown(item, 0, gid, follow_symlinks=False)
        if APP.is_symlink():
            old = APP.resolve()
        else:
            old = RELEASES/('baseline-'+str(time.time_ns()))
            APP.rename(old)
        switch(final)
        command(['systemctl', 'start', 'zenthex'])
        for _ in range(30):
            try:
                health = json_get('/api/health')
                if health.get('status') == 'ok' and health.get('release') == revision:
                    modules = json_get('/api/modules/status')
                    if modules['trading']['liveEnabled']:
                        raise RuntimeError('실거래 설정이 예상과 다릅니다.')
                    STATE.mkdir(mode=0o700, exist_ok=True)
                    (STATE/'last-success').write_text(revision)
                    (STATE/'last-failed').unlink(missing_ok=True)
                    print('배포 완료:', revision, 'DB 백업:', backup, flush=True)
                    return
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(1)
        raise RuntimeError('새 릴리스 상태 검사 실패')
    except Exception:
        if old is not None:
            switch(old)
        command(['systemctl', 'restart', 'zenthex'])
        raise


def update():
    if os.geteuid() != 0:
        raise RuntimeError('설치된 systemd 서비스로 실행하세요.')
    idle_check()
    if not (CHECKOUT/'.git').is_dir():
        command(['git', 'clone', '--no-checkout', '--depth=1', '--branch=main', REPO, str(CHECKOUT)], build=True)
    command(['git', '-C', str(CHECKOUT), 'fetch', '--depth=1', 'origin', 'main'], build=True, timeout=120)
    rev = command(['git', '-C', str(CHECKOUT), 'rev-parse', 'FETCH_HEAD'], build=True, capture=True).strip()
    if not re.fullmatch('[0-9a-f]{40}', rev):
        raise RuntimeError('잘못된 커밋 ID')
    current = APP/'RELEASE'
    if current.is_file() and current.read_text().strip() == rev:
        print('최신 코드입니다.'); return
    if (STATE/'last-failed').is_file() and (STATE/'last-failed').read_text().strip() == rev:
        print('이 커밋은 검사/배포에 실패했습니다. 다음 수정 커밋을 기다립니다.'); return
    build = BUILD_HOME/('release-'+rev)
    if build.exists():
        shutil.rmtree(build)
    try:
        command(['/usr/bin/python3', '/usr/local/lib/zenthex/auto_update.py', '--prepare', str(CHECKOUT), rev, str(build)], build=True, timeout=1800)
        promote(build, rev)
    except DeployDeferred:
        raise
    except Exception:
        STATE.mkdir(mode=0o700, exist_ok=True)
        (STATE/'last-failed').write_text(rev)
        raise
    finally:
        if build.exists():
            shutil.rmtree(build)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', nargs=3)
    parser.add_argument('--retry', action='store_true')
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare(Path(args.prepare[0]), args.prepare[1], Path(args.prepare[2]))
        else:
            with open('/run/zenthex-deploy.lock', 'w') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if args.retry:
                    (STATE/'last-failed').unlink(missing_ok=True)
                update()
    except DeployDeferred as error:
        print('배포 보류:', error)
    except BlockingIOError:
        print('다른 배포가 진행 중입니다.')
    except Exception as error:
        print('배포 보류/실패:', type(error).__name__, str(error), file=sys.stderr)
        sys.exit(1)
