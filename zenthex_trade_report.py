#!/usr/bin/env python3
"""Read local decision records without contacting an exchange or changing trading."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time


def summarize(path, hours=24, mode='real'):
    cutoff = time.time() - hours * 3600
    events, malformed = [], 0
    for file in [path.with_name(path.name + '.' + str(n)) for n in (3, 2, 1)] + [path]:
        if not file.exists():
            continue
        with file.open(encoding='ascii') as lines:
            for line in lines:
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(row.get('time'), (int, float)):
                        raise ValueError('invalid record')
                    if row['time'] >= cutoff and (mode == 'all' or row.get('mode') == mode):
                        events.append(row)
                except (ValueError, TypeError):
                    malformed += 1
    events.sort(key=lambda row: row['time'])
    closed = [row for row in events if row.get('event') == 'exit_fill']
    reasons = {}
    for row in closed:
        tag = row.get('exit_tag', 'unknown')
        group = reasons.setdefault(tag, {'count': 0, 'pnl_krw': 0.0})
        group['count'] += 1
        group['pnl_krw'] += row.get('pnl_krw', 0)
    return {
        'window_hours': hours, 'mode': mode, 'events': len(events),
        'event_counts': dict(Counter(row.get('event', 'unknown') for row in events)),
        'entry_check_reasons': dict(Counter(row.get('code', 'unknown') for row in events if row.get('event') == 'entry_check')),
        'closed_trades': len(closed), 'pnl_krw': sum(row.get('pnl_krw', 0) for row in closed),
        'by_exit_tag': reasons, 'malformed_lines': malformed,
        'recent_trades': closed[-10:],
        'recent_decisions': [row for row in events if row.get('event') in {'entry_check', 'signal'}][-10:],
        'scope': 'Recorded events only; older trades are not reconstructed. No profit validation.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', type=Path, default=Path('/var/lib/zenthex/trading/decisions.jsonl'))
    parser.add_argument('--hours', type=float, default=24)
    parser.add_argument('--mode', choices=('real', 'practice', 'all'), default='real')
    args = parser.parse_args()
    if not 0 < args.hours <= 8760:
        parser.error('--hours must be between 0 and 8760')
    print(json.dumps(summarize(args.path, args.hours, args.mode), ensure_ascii=True, indent=2))
