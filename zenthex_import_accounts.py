#!/usr/bin/env python3
"""Import the verified two-account Render snapshot into the existing empty AWS DB.

Default: inspect only. --apply: back up AWS and import accounts in one transaction.
Does not change environment variables, passwords, plans, app code, or trading flags.
Expired account verification/reset codes are deliberately not copied.
"""
import argparse
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.request

SOURCE = Path("/home/ubuntu/zenthex-incoming-99b1485cbd4bb56c/incoming.db")
EXPECTED_SHA256 = "510c97f50ca4a455f7a8c857d37d6ceb61a4f91f2ef2f9dfc89616b394354b7e"
ENV_PATH = Path("/etc/zenthex/zenthex.env")
TABLES = {"users", "trade_records", "billing_history", "subscriptions", "support_tickets"}
CODES = {"phone_verification_code", "email_verification_code", "password_reset_code"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def counts(db):
    names = [row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    require(set(names) == TABLES, "Unexpected DB tables; inspect before migrating")
    return {name: db.execute("SELECT COUNT(*) FROM " + quote(name)).fetchone()[0]
            for name in sorted(names)}


def source_rows(data, expected_hash):
    require(len(data) <= 20 * 1024 * 1024, "Backup size exceeds limit")
    require(hashlib.sha256(data).hexdigest() == expected_hash, "Source SHA256 does not match verified transfer")
    with closing(sqlite3.connect(":memory:")) as db:
        db.deserialize(data)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        require([tuple(row) for row in db.execute("PRAGMA quick_check")] == [("ok",)], "Source DB integrity failed")
        table_counts = counts(db)
        require(table_counts["users"] == 2 and sum(table_counts.values()) == 2,
                "Snapshot is not two accounts with empty history tables")
        rows = [dict(row) for row in db.execute("SELECT * FROM users ORDER BY id")]
    require(all({"id", "email", "hashed_password"} <= row.keys() for row in rows), "Required account columns missing")
    emails = [str(row["email"] or "").strip().lower() for row in rows]
    require(all("@" in email for email in emails) and len(set(emails)) == 2, "Missing or duplicate account emails")
    require(all(isinstance(row["id"], int) and row["id"] > 0 for row in rows), "Invalid account IDs")
    for row in rows:
        require(bool(re.fullmatch(r"[0-9a-f]{64}", str(row["hashed_password"] or ""))),
                "Unexpected password format; do not overwrite or reset it")
        require(all(not value for name, value in row.items() if "key" in name.lower() or "secret" in name.lower()),
                "Exchange credentials exist; a separate encrypted-key migration is required")
    return rows


def read_env():
    result = {}
    for line in ENV_PATH.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip("\"'")
    return result


def preflight(env):
    require(env.get("ZENTHEX_ENABLE_LIVE_TRADING", "false").lower() == "false", "Live trading must remain disabled")
    require(env.get("ZENTHEX_SERVER_PUBLIC_IP") == "13.124.81.242", "AWS IP setting mismatch")
    require(not Path("/var/lib/zenthex/trading/live-position.json").exists(), "Position/order guard exists; reconcile it first")
    require(len(env.get("ZENTHEX_TOKEN_SECRET", "")) >= 32, "Individual AWS token secret required")
    unit = Path("/etc/systemd/system/zenthex.service").read_text()
    require("--host 127.0.0.1" in unit and "--workers 1" in unit, "Expected single local AWS app worker")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:8000/api/finance/status", timeout=30) as response:
        state = json.load(response)
    require(state.get("state") == "STOPPED", "AWS engine must be completely stopped")
    module_path = Path("/opt/zenthex/app/auth/hash.py")
    spec = importlib.util.spec_from_file_location("zenthex_import_password_check", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probe = "local-compatibility-check-not-a-user-password"
    require(module.verify_password(probe, hashlib.sha256(probe.encode()).hexdigest()), "Installed app cannot verify legacy passwords")
    require(module.get_password_hash(probe).startswith("pbkdf2_sha256$"), "Install the improved password module first")
    require("/etc/zenthex/zenthex.env" in unit, "Service environment file differs")
    pid = int(subprocess.run(["systemctl", "show", "zenthex", "--property=MainPID", "--value"],
                             check=True, capture_output=True, text=True).stdout.strip())
    require(pid > 0, "AWS service is not running")
    running = dict(item.split(b"=", 1) for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in item)
    for key in ["ZENTHEX_DATABASE_URL", "ZENTHEX_TOKEN_SECRET", "ZENTHEX_ENABLE_LIVE_TRADING"]:
        require(running.get(key.encode()) == env.get(key, "").encode(), "Running service environment differs; check deployment first")


def prepare_rows(rows, target):
    require(not target.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' LIMIT 1").fetchone(),
            "Unexpected DB triggers; inspect before insertion")
    info = list(target.execute("PRAGMA table_info(users)"))
    columns = {row[1] for row in info}
    required = {row[1] for row in info if row[3] and row[4] is None and not row[5]}
    result = []
    for original in rows:
        require(not (original.keys() - columns), "Account schema differs; no fields were dropped")
        row = dict(original)
        for name in CODES & columns:
            row[name] = None
        require(required <= row.keys(), "Required AWS account fields missing from source")
        result.append(row)
    return result


def same_accounts(target, expected):
    cursor = target.execute("SELECT * FROM users ORDER BY id")
    names = [column[0] for column in cursor.description]
    actual = [dict(zip(names, row)) for row in cursor.fetchall()]
    return len(actual) == len(expected) and all(
        all(account.get(key) == value for key, value in wanted.items())
        for account, wanted in zip(actual, expected))


def migrate(data, target_path, backup_root, check, *, apply=False, expected_hash=EXPECTED_SHA256):
    """All parameters except paths/check are fixed by the production CLI."""
    originals = source_rows(data, expected_hash)
    target_path = Path(target_path)
    require(target_path.is_absolute() and target_path.is_file() and not target_path.is_symlink(), "Existing absolute AWS DB path required")
    check()
    mode = "rw" if apply else "ro"
    with closing(sqlite3.connect(target_path.as_uri() + "?mode=" + mode, uri=True, timeout=10)) as db:
        require(db.execute("PRAGMA quick_check").fetchall() == [("ok",)], "AWS DB integrity failed")
        if apply:
            db.execute("BEGIN IMMEDIATE")
        try:
            before = counts(db)
            prepared = prepare_rows(originals, db)
            if before["users"] == 2 and sum(before.values()) == 2 and same_accounts(db, prepared):
                if apply:
                    db.rollback()
                return {"status": "already_imported", "users": 2, "changed": False}
            require(sum(before.values()) == 0, "AWS DB contains data; refusing to replace existing accounts/history")
            if not apply:
                return {"status": "ready", "source_users": 2, "aws_users": 0, "changed": False}
            check()
            backup_root = Path(backup_root)
            require(not backup_root.is_symlink(), "Unexpected backup directory symlink")
            backup_root.mkdir(parents=True, mode=0o700, exist_ok=True)
            backup = backup_root / ("accounts-" + str(time.time_ns()))
            backup.mkdir(mode=0o700)
            # Read through another connection: backup on a writer's own active
            # transaction can block indefinitely. BEGIN IMMEDIATE prevents other writers.
            with closing(sqlite3.connect(target_path.as_uri() + "?mode=ro", uri=True, timeout=10)) as reader:
                with closing(sqlite3.connect(backup / "aws-before.db")) as out:
                    reader.backup(out)
                    require(out.execute("PRAGMA quick_check").fetchall() == [("ok",)]
                            and counts(out) == before, "AWS backup verification failed")
            (backup / "aws-before.db").chmod(0o600)
            (backup / "render-received.db").write_bytes(data)
            (backup / "render-received.db").chmod(0o600)
            for row in prepared:
                names = list(row)
                db.execute("INSERT INTO users (" + ",".join(map(quote, names)) + ") VALUES (" +
                           ",".join("?" for _ in names) + ")", [row[name] for name in names])
            require(same_accounts(db, prepared), "Account field verification failed")
            after = counts(db)
            require(after["users"] == 2 and sum(after.values()) == 2, "Unexpected post-import counts")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(), "Foreign-key verification failed")
            # A metadata write failure must also roll back the account insertion.
            receipt = {"source_sha256": expected_hash, "before": before, "after": after,
                       "verification_codes_cleared": sorted(CODES), "trading_flags_changed": False}
            (backup / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            (backup / "receipt.json").chmod(0o600)
            check()
            db.commit()
            return {"status": "imported", "users": 2, "backup": str(backup), "changed": True}
        except BaseException:
            db.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require(os.geteuid() == 0, "Run with sudo on the AWS server")
    env = read_env()
    value = env.get("ZENTHEX_DATABASE_URL", "")
    require(value.startswith("sqlite:////") and "?" not in value, "Expected existing absolute SQLite DB setting")
    target = Path(value[len("sqlite:///"):])
    original_env = ENV_PATH.read_bytes()

    def check():
        require(ENV_PATH.read_bytes() == original_env, "Runtime settings changed during migration")
        preflight(env)

    result = migrate(SOURCE.read_bytes(), target, Path("/var/backups/zenthex-security"), check, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False))
    print("Passwords and account fields preserved; stale verification/reset codes cleared on import.")
    print("Live trading remains disabled. No exchange orders or application code changes.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        # Do not include SQLite exception text that might embed an account value.
        if isinstance(error, sqlite3.Error):
            raise SystemExit("MIGRATION STOPPED: SQLite validation failed; account changes rolled back")
        raise SystemExit("MIGRATION STOPPED: " + str(error))
