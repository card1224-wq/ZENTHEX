"""Bounded, private decision records; never persist credentials or raw API responses."""
import json
import math
import os
import threading
import time
from pathlib import Path

_lock = threading.Lock()
_last_warning = 0.0
MAX_BYTES = 5 * 1024 * 1024
FIELDS = {
    'ticker', 'mode', 'exchange', 'trade_id', 'passed', 'code', 'spread_pct',
    'bid_ask_ratio', 'signal_price', 'price', 'minute1_pct', 'minute3_pct',
    'minute5_pct', 'volume_ratio', 'score', 'quantity', 'funds_krw', 'fee_krw',
    'entry_cost_krw', 'exit_net_krw', 'pnl_krw', 'pnl_pct', 'hold_seconds',
    'observed_peak_pct', 'observed_min_pct', 'target_pct', 'stop_pct', 'exit_tag',
    'entry_count', 'candle_time',
}


def diagnostic_path():
    return Path(os.getenv('ZENTHEX_TRADING_STATE_DIR', 'runtime-state')) / 'decisions.jsonl'


def record_decision(event, **details):
    global _last_warning
    if event not in {'signal', 'entry_check', 'entry_fill', 'weak_check', 'exit_fill'}:
        return False
    # Only known scalar fields are accepted. Callers must not supply arbitrary
    # exception text, account objects, keys, order responses, or user prompts.
    row = {'schema': 1, 'time': time.time(), 'event': event}
    for name, value in details.items():
        if name not in FIELDS or value is None:
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if isinstance(value, str):
            value = value[:100]
        if isinstance(value, (str, int, float, bool)):
            row[name] = value
    try:
        data = (json.dumps(row, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
        with _lock:
            path = diagnostic_path()
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if path.exists() and path.stat().st_size + len(data) > MAX_BYTES:
                for number in (2, 1):
                    old = path.with_name(path.name + '.' + str(number))
                    if old.exists():
                        old.replace(path.with_name(path.name + '.' + str(number + 1)))
                path.replace(path.with_name(path.name + '.1'))
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'ab') as out:
                out.write(data)
        return True
    except (OSError, ValueError, TypeError):
        # Telemetry failure must never interrupt an order/position recovery path.
        now = time.monotonic()
        if now - _last_warning >= 60:
            print('[Diagnostics] WRITE_FAILED: decision recording unavailable', flush=True)
            _last_warning = now
        return False
