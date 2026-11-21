#!/usr/bin/env python3
"""Ubuntu: grant a two-hour, receive-only SSH key for one SQLite backup.

No running service, application database, firewall or existing SSH key is replaced.
The received backup is staged in a private directory, never imported automatically.
"""
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import os
from pathlib import Path
import secrets
import shutil


RECEIVER = r'''import fcntl, hashlib, os, signal, sqlite3, sys
from pathlib import Path

folder = Path(__file__).resolve().parent
partial, target = folder / "incoming.part", folder / "incoming.db"
marker = folder.name
created = False

def timeout(signum, frame):
    raise TimeoutError("Transfer exceeded 120 seconds")

signal.signal(signal.SIGALRM, timeout)
signal.alarm(120)
digest = hashlib.sha256()
size = 0
try:
    with partial.open("xb") as out:
        created = True
        os.chmod(partial, 0o600)
        while True:
            chunk = sys.stdin.buffer.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 20 * 1024 * 1024:
                raise ValueError("Backup exceeds 20 MiB")
            digest.update(chunk)
            out.write(chunk)
        out.flush()
        os.fsync(out.fileno())
    with partial.open("rb") as source:
        if source.read(16) != b"SQLite format 3\x00":
            raise ValueError("Not a SQLite backup")
    with sqlite3.connect(partial.as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
    # Linking is exclusive: another transfer can never overwrite a completed file.
    os.link(partial, target)
finally:
    if created:
        partial.unlink(missing_ok=True)
    signal.alarm(0)

# Revoke this grant only. Existing AWS/browser SSH entries remain unchanged.
authorized = Path.home() / ".ssh/authorized_keys"
if authorized.is_symlink():
    raise RuntimeError("Unexpected authorized_keys symlink; revoke grant manually")
with authorized.open("r+") as out:
    fcntl.flock(out, fcntl.LOCK_EX)
    rows = out.read().splitlines(keepends=True)
    out.seek(0)
    out.write("".join(row for row in rows if row.split()[-1:] != [marker]))
    out.truncate()
    out.flush()
    os.fsync(out.fileno())
print("RECEIVED:", target)
print("BYTES:", size)
print("SHA256:", digest.hexdigest())
print("TRANSFER KEY REVOKED. Application database unchanged.")
'''


def validate_key(value):
    fields = value.strip().split()
    if len(fields) < 2 or fields[0] != "ssh-ed25519":
        raise ValueError("Copy ssh-ed25519 and its complete public key from Render")
    raw = base64.b64decode(fields[1], validate=True)
    if len(raw) != 51 or not raw.startswith(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"):
        raise ValueError("Invalid Ed25519 public key")
    return "ssh-ed25519 " + fields[1]


def setup(home, public_key):
    key = validate_key(public_key)
    home = Path(home).resolve()
    # The forced command uses a simple trusted absolute path, without shell syntax.
    if any(char not in "/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in str(home)):
        raise ValueError("Unexpected home directory")
    ssh = home / ".ssh"
    if ssh.is_symlink():
        raise ValueError("Unexpected .ssh symlink")
    ssh.mkdir(mode=0o700, exist_ok=True)
    authorized = ssh / "authorized_keys"
    if authorized.is_symlink():
        raise ValueError("Unexpected authorized_keys symlink")
    directory = home / ("zenthex-incoming-" + secrets.token_hex(8))
    directory.mkdir(mode=0o700)
    receiver = directory / "receive.py"
    receiver.write_text(RECEIVER)
    receiver.chmod(0o600)
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y%m%d%H%M%SZ")
    command = "/usr/bin/python3 " + str(receiver)
    line = f'restrict,expiry-time="{expires}",command="{command}" {key} {directory.name}\n'
    if authorized.exists():
        shutil.copy2(authorized, directory / "authorized_keys.before")
        (directory / "authorized_keys.before").chmod(0o600)
    with authorized.open("a+") as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        out.seek(0)
        existing = out.read()
        if key in existing:
            raise ValueError("This key is already authorized; inspect the existing grant first")
        out.seek(0, os.SEEK_END)
        if existing and not existing.endswith("\n"):
            out.write("\n")
        out.write(line)
        out.flush()
        os.fsync(out.fileno())
    authorized.chmod(0o600)
    return directory


def main():
    import pwd
    if pwd.getpwuid(os.getuid()).pw_name != "ubuntu":
        raise SystemExit("Run as ubuntu in the AWS SSH window; do not use sudo or Render")
    print("PUBLIC KEY > ", end="", flush=True)
    with open("/dev/tty") as terminal:
        key = terminal.readline()
    directory = setup(Path.home(), key)
    print("READY:", directory)
    print("Only one backup can be received; no shell/port forwarding; expires in two hours.")
    print("The grant is removed after a successful transfer. Live database unchanged.")


if __name__ == "__main__":
    main()
