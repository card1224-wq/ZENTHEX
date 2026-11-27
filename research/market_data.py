"""Public candles only; fixed URL and bounded pagination, no credentials."""
from datetime import datetime, timezone
import time
import urllib.parse
from trading.binance_client import _request_json


def upbit_minutes(ticker):
    cursor = None
    found = {}
    now = time.time()*1000
    for _ in range(6):
        query = dict(market=ticker, count=200)
        if cursor:
            query['to'] = cursor
        rows = _request_json('https://api.upbit.com/v1/candles/minutes/1?' + urllib.parse.urlencode(query))
        if not isinstance(rows,list) or not rows:
            break
        oldest = None
        for row in rows:
            stamp = datetime.fromisoformat(row['candle_date_time_utc']).replace(tzinfo=timezone.utc)
            ms = int(stamp.timestamp()*1000)
            oldest = stamp if oldest is None or stamp < oldest else oldest
            if ms+60000 <= now:
                found[ms] = dict(time=ms,open=float(row['opening_price']),high=float(row['high_price']),
                                 low=float(row['low_price']),close=float(row['trade_price']),
                                 volume=float(row['candle_acc_trade_volume']))
        next_cursor = oldest.isoformat() if oldest else None
        if next_cursor == cursor or len(found)>=1000:
            break
        cursor = next_cursor
    return dict(source='Upbit '+ticker+' completed 1m',ticker=ticker,interval='1m',
                bars=[found[k] for k in sorted(found)[-1000:]])
