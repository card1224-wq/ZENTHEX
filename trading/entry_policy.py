"""Conservative entry checks, not a predictor of future returns."""
from datetime import datetime, timedelta, timezone
import math

KST = timezone(timedelta(hours=9))
ENTRY_POLICY_VERSION = 'closed-bars-depth-cost-v1'


def candle_start(stamp):
    value = stamp.to_pydatetime() if hasattr(stamp, 'to_pydatetime') else stamp
    if not isinstance(value, datetime):
        raise ValueError('invalid candle time')
    return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)


def completed_frame(frame, minutes, now=None):
    """pyupbit index is candle start in KST. Reject stale/gapped completed data."""
    if frame is None or frame.empty:
        raise ValueError('candle data missing')
    now = now or datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    span = timedelta(minutes=minutes)
    stamps = [candle_start(s) for s in frame.index]
    if any(b <= a for a,b in zip(stamps,stamps[1:])):
        raise ValueError('candle times not ordered')
    indices = [i for i,t in enumerate(stamps) if t+span <= now]
    if not indices:
        raise ValueError('no completed candles')
    result = frame.iloc[indices].copy()
    times = [stamps[i] for i in indices]
    if any(b-a != span for a,b in zip(times,times[1:])):
        raise ValueError('candle gap')
    if now-(times[-1]+span) >= span:
        raise ValueError('stale completed candles')
    for name in ('open','high','low','close','volume'):
        values = [float(v) for v in result[name]]
        if any(not math.isfinite(v) or v < 0 or (name != 'volume' and v == 0) for v in values):
            raise ValueError('invalid candle values')
    for _,r in result.iterrows():
        if r['high'] < max(r['open'],r['close'],r['low']) or r['low'] > min(r['open'],r['close'],r['high']):
            raise ValueError('invalid candle range')
    return result


def entry_depth_cost(units, spend, fee, stop_gap):
    """Immediate full ask-buy -> bid-sell loss including both fees and 0.10% reserve.

    Static liquidity can disappear. Limits restrict initial costs, never guarantee a stop fill.
    """
    if not all(math.isfinite(x) for x in (spend,fee,stop_gap)) or spend < 5000 or not 0<=fee<=.01 or not 0<stop_gap<1:
        return dict(passed=False,code='cost_inputs_invalid')
    if len(units)<3:
        return dict(passed=False,code='book_missing')
    levels=[];previous_ask=0.;previous_bid=math.inf
    try:
        for r in units:
            ask,bid,ask_size,bid_size=(float(r[k]) for k in ('ask_price','bid_price','ask_size','bid_size'))
            if (not all(math.isfinite(v) for v in (ask,bid,ask_size,bid_size))
                or ask<=0 or bid<=0 or ask_size<0 or bid_size<0 or ask<=bid
                or ask<previous_ask or bid>previous_bid):
                raise ValueError('invalid depth')
            levels.append((ask,bid,ask_size,bid_size));previous_ask,previous_bid=ask,bid
    except (KeyError,TypeError,ValueError):
        return dict(passed=False,code='book_price_invalid')
    spread=(levels[0][0]/levels[0][1]-1)
    ratio=sum(r[3] for r in levels[:5])/max(sum(r[2] for r in levels[:5]),1e-9)
    common=dict(spread_pct=spread*100,bid_ask_ratio=ratio)
    if spread>.002:
        return dict(**common,passed=False,code='spread')
    if ratio<.75:
        return dict(**common,passed=False,code='bid_depth')
    remaining,qty=spend,0.
    for ask,_,size,_ in levels:
        amount=min(remaining,ask*size);qty+=amount/ask;remaining-=amount
        if remaining<=spend*1e-10:break
    if remaining>spend*1e-10:
        return dict(**common,passed=False,code='ask_liquidity')
    remaining,gross=qty,0.
    for _,bid,_,size in levels:
        take=min(remaining,size);gross+=take*bid;remaining-=take
        if remaining<=qty*1e-10:break
    if remaining>qty*1e-10:
        return dict(**common,passed=False,code='bid_liquidity')
    roundtrip=1-gross*(1-fee)/(spend*(1+fee))
    budget=min(.003,stop_gap*.5)
    total=roundtrip+.001
    return dict(**common,roundtrip_cost_pct=roundtrip*100,cost_reserve_pct=.1,
                entry_cost_budget_pct=budget*100,passed=total<=budget+1e-12,
                code='passed' if total<=budget+1e-12 else 'roundtrip_cost')
