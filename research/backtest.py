"""Fixed-rule historical research. No exchange orders, optimisation or live promotion."""
from math import isfinite


def validate_bars(bars):
    if not 200 <= len(bars) <= 20000:
        raise ValueError('완료된 봉 200~20,000개가 필요합니다.')
    previous = None
    for b in bars:
        if previous is not None and b['time'] <= previous:
            raise ValueError('time은 중복 없이 시간 오름차순이어야 합니다.')
        previous = b['time']
        values = [b[k] for k in ('open', 'high', 'low', 'close')]
        if not all(isfinite(v) and v > 0 for v in values):
            raise ValueError('가격은 유한한 양수여야 합니다.')
        if b['high'] < max(values) or b['low'] > min(values):
            raise ValueError('OHLC 가격 범위가 맞지 않습니다.')


def replay(bars, start, end, fee, slip, allow_short=False):
    """Signal from prior closes, execution at next open. Full-notional, unlevered."""
    equity = peak = 1.0
    max_dd = 0.0
    side, entry, entry_equity, entry_index = 0, 0., 1., 0
    trades = []
    cost = fee + slip
    for i in range(start, end):
        prior = [b['close'] for b in bars[i-60:i]]
        fast = sum(prior[-20:]) / 20
        slow = sum(prior) / 60
        desired = 1 if fast > slow and prior[-1] > fast else (-1 if allow_short and fast < slow and prior[-1] < fast else 0)
        if side and desired != side:
            equity = max(0., entry_equity * (1 + side * (bars[i]['open'] / entry - 1) - cost * bars[i]['open'] / entry))
            trades.append({'entryIndex': entry_index, 'exitIndex': i, 'side': 'long' if side == 1 else 'short',
                           'pnlPctInitial': (equity - entry_equity/(1-cost))*100, 'netReturnPct': round((equity / (entry_equity / (1-cost)) - 1)*100, 6)})
            side = 0
        if not side and desired and equity > 0:
            side, entry, entry_equity, entry_index = desired, bars[i]['open'], equity * (1-cost), i
        # Conservative intrabar drawdown: adverse extreme before any favorable extreme.
        worst = (bars[i]['low'] if side == 1 else bars[i]['high']) if side else 0
        low_equity = max(0., entry_equity*(1+side*(worst/entry-1)-cost*worst/entry)) if side else equity
        max_dd = max(max_dd, 1-low_equity/peak)
        mark = max(0., entry_equity*(1+side*(bars[i]['close']/entry-1)-cost*bars[i]['close']/entry)) if side else equity
        peak = max(peak, mark)
        if side and low_equity <= 0:
            raise ValueError('모형의 자본 소진 범위입니다. 이 자료의 숏 검증은 지원하지 않습니다.')
    if side:
        price = bars[end-1]['close']
        equity = max(0., entry_equity*(1+side*(price/entry-1)-cost*price/entry))
        trades.append({'entryIndex': entry_index, 'exitIndex': end-1, 'side': 'long' if side == 1 else 'short',
                       'pnlPctInitial': (equity - entry_equity/(1-cost))*100, 'netReturnPct': round((equity/(entry_equity/(1-cost))-1)*100, 6)})
    gains = sum(max(t['pnlPctInitial'], 0) for t in trades)
    losses = -sum(min(t['pnlPctInitial'], 0) for t in trades)
    baseline = ((1-cost)*bars[end-1]['close']/bars[start]['open']*(1-cost)-1)*100
    return {'returnPct': round((equity-1)*100, 4), 'maxDrawdownPct': round(max_dd*100, 4),
            'buyHoldReturnPct': round(baseline, 4), 'tradeCount': len(trades),
            'winRatePct': round(100*sum(t['netReturnPct']>0 for t in trades)/len(trades), 2) if trades else 0,
            'profitFactor': round(gains/losses, 4) if losses else None,
            'trades': trades[-100:], 'from': bars[start]['time'], 'to': bars[end-1]['time']}


def run_research(bars, market, fee, slip):
    validate_bars(bars)
    split = int(len(bars)*.7)
    short = market == 'binance_futures'
    training = replay(bars, 60, split, fee, slip, short)
    validation = replay(bars, split, len(bars), fee, slip, short)
    stress = replay(bars, split, len(bars), fee*2, slip*2, short)
    checks = {
        'positiveValidation': validation['returnPct'] > 0,
        'beatsBuyHold': validation['returnPct'] > validation['buyHoldReturnPct'],
        'drawdownUnder10Pct': validation['maxDrawdownPct'] <= 10,
        'atLeast50ValidationTrades': validation['tradeCount'] >= 50,
        'profitFactorAtLeast1_2': validation['profitFactor'] is not None and validation['profitFactor'] >= 1.2,
        'positiveDoubleCosts': stress['returnPct'] > 0,
    }
    return {'strategy': 'ma20-ma60-v1', 'market': market, 'training': training, 'validation': validation,
            'doubleCostValidation': stress, 'checks': checks,
            'decision': '추가 검증 후보' if all(checks.values()) else '연구 기준 미달',
            'liveEligible': False, 'leverage': 1,
            'assumptions': ['완료된 봉만 입력해야 합니다. 70% 연구 / 30% 미사용 구간으로 분리합니다.',
             '이전 봉 종가 신호 → 다음 봉 시가 체결. 진입·청산 양쪽 수수료와 슬리피지 반영.',
             '고정 이동평균 추세 전략이며 기존 업비트 실시간 스캐너의 성과가 아닙니다.',
             '봉 내부 저가/고가로 손실폭을 추정합니다. 실제 체결·유동성은 재현하지 않습니다.',
             '배당·세금·환전·기업행사·공매도 비용·펀딩·유지증거금·강제청산은 미반영입니다.',
             '바이낸스는 1배 롱/숏 방향 연구입니다. 실제 선물 순수익이나 청산 검증이 아닙니다.',
             '단일 구간 통과로 판매/실거래를 허용하지 않습니다. 여러 기간·종목과 전진 모의매매 검증이 필요합니다.']}
