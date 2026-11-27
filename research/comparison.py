"""Fixed, long-only 1-minute research; independent of the live scanner/orders."""
from math import isfinite
from research.backtest import validate_bars

STRATEGIES = (
    ('momentum_proxy_v1', '돌파 즉시 진입 · 비교용 단순 모형', False),
    ('momentum_cost_v1', '같은 돌파 신호 + 비용 제한', True),
    ('pullback_cost_v1', '돌파 후 눌림·재상승 + 비용 제한', True),
)
TARGET = .012
STOP = .006
MIN_EDGE = .003


def validate_minutes(bars):
    validate_bars(bars)
    if len(bars) < 500:
        raise ValueError('완료된 1분봉 500~20,000개가 필요합니다.')
    for i, bar in enumerate(bars):
        volume = bar.get('volume', -1)
        if not isinstance(volume, (int, float)) or not isfinite(volume) or volume < 0:
            raise ValueError('각 봉의 유한한 0 이상 거래량이 필요합니다.')
        if i and bar['time'] - bars[i-1]['time'] != 60_000:
            raise ValueError('연속된 1분봉만 지원합니다. 누락 봉을 임의 생성하지 마세요.')


def signal(bars, i, strategy):
    # Only completed bars before the execution bar i are visible here.
    if i < 30:
        return False
    prior = bars[i-30:i]
    closes = [b['close'] for b in prior]
    average = lambda n: sum(closes[-n:])/n
    volume_base = sum(b['volume'] for b in prior[-12:-3])/9
    if volume_base <= 0:
        return False
    volume_ratio = (sum(b['volume'] for b in prior[-3:])/3)/volume_base
    if strategy != 'pullback_cost_v1':
        return (closes[-1] > max(b['high'] for b in prior[-6:-1])
                and closes[-1] > average(5) > average(10) > average(20)
                and volume_ratio >= 1.2)
    impulse = prior[-4]
    old_high = max(b['high'] for b in prior[-9:-4])
    correction = prior[-3:-1]
    retracement = 1 - min(b['low'] for b in correction)/impulse['close']
    older_ma = sum(closes[-25:-5])/20
    return (impulse['close'] > old_high and .002 <= retracement <= .008
            and min(b['close'] for b in correction) < impulse['close']
            and closes[-1] > prior[-2]['high'] and closes[-1] > average(20) > older_ma
            and volume_ratio >= 1.2)


def weak_signal(bars, i):
    # Two consecutive completed down candles, checked only after entry + two bars.
    return (bars[i-1]['close'] < bars[i-2]['close'] < bars[i-3]['close']
            and bars[i-1]['close']/bars[i-3]['close']-1 <= -.0025)


def replay_comparison(bars, start, end, strategy, fee, slip, spread, use_filter):
    cost = fee + slip + spread/2
    equity = peak = 1.
    max_dd = 0.
    position = None
    cooldown = start
    trades = []
    rejected = signals = 0
    for i in range(start, end):
        bar = bars[i]
        if position is None and i >= cooldown and signal(bars, i, strategy):
            signals += 1
            if use_filter and TARGET - (2*(fee+slip)+spread) < MIN_EDGE:
                rejected += 1
            else:
                position = dict(index=i, price=bar['open'], before=equity,
                                units=equity*(1-cost)/bar['open'])
        if position is None:
            continue
        p = position
        stop, target = p['price']*(1-STOP), p['price']*(1+TARGET)
        price = reason = None
        # Existing orders: opening gap first; then prior-close discretionary exit.
        if bar['open'] <= stop:
            price, reason = bar['open'], 'gap_stop'
        elif bar['open'] >= target:
            price, reason = target, 'gap_target'
        elif i >= p['index']+2 and weak_signal(bars, i):
            price, reason = bar['open'], 'weak'
        elif i >= p['index']+30:
            price, reason = bar['open'], 'timeout'
        elif bar['low'] <= stop:
            price, reason = stop, 'stop'
        elif bar['high'] >= target:
            price, reason = target, 'target'
        # No low after an open exit. For intrabar target, assume adverse extreme first.
        adverse = price if reason in {'gap_stop', 'gap_target', 'weak', 'timeout'} else (
            max(stop, bar['low']) if reason in {'stop', 'target'} else bar['low'])
        worst = p['units']*adverse*(1-cost)
        max_dd = max(max_dd, 1-worst/peak)
        if price is not None:
            equity = p['units']*price*(1-cost)
            trades.append(dict(entryIndex=p['index'], exitIndex=i, entryTime=bars[p['index']]['time'],
                               exitTime=bar['time'], exitReason=reason, holdMinutes=i-p['index'],
                               netReturnPct=(equity/p['before']-1)*100,
                               pnlPctInitial=(equity-p['before'])*100))
            position = None
            cooldown = i+5
            peak = max(peak, equity)
        else:
            peak = max(peak, p['units']*bar['close']*(1-cost))
    if position:
        p = position
        equity = p['units']*bars[end-1]['close']*(1-cost)
        max_dd = max(max_dd, 1-equity/peak)
        trades.append(dict(entryIndex=p['index'], exitIndex=end-1, entryTime=bars[p['index']]['time'],
                           exitTime=bars[end-1]['time'], exitReason='period_end', holdMinutes=end-1-p['index'],
                           netReturnPct=(equity/p['before']-1)*100, pnlPctInitial=(equity-p['before'])*100))
    wins = [t for t in trades if t['netReturnPct'] > 0]
    losses = [t for t in trades if t['netReturnPct'] < 0]
    gains = sum(t['pnlPctInitial'] for t in wins)
    loss = -sum(t['pnlPctInitial'] for t in losses)
    return dict(returnPct=round((equity-1)*100, 6), maxDrawdownPct=round(max_dd*100, 6),
                tradeCount=len(trades), winRatePct=round(len(wins)/len(trades)*100, 2) if trades else None,
                averageWinPct=sum(t['netReturnPct'] for t in wins)/len(wins) if wins else None,
                averageLossPct=sum(t['netReturnPct'] for t in losses)/len(losses) if losses else None,
                expectancyPct=sum(t['netReturnPct'] for t in trades)/len(trades) if trades else None,
                profitFactor=gains/loss if loss else None, signalCount=signals, costRejected=rejected,
                trades=trades[-100:], fromTime=bars[start]['time'], toTime=bars[end-1]['time'])


def compare_strategies(bars, fee, slip, spread):
    validate_minutes(bars)
    for cost in (fee, slip, spread):
        if not isfinite(cost) or not 0 <= cost <= .1:
            raise ValueError('비용은 각각 0~1,000bp 범위여야 합니다.')
    split = int(len(bars)*.7)
    results = []
    for key, label, filtered in STRATEGIES:
        training = replay_comparison(bars, 30, split, key, fee, slip, spread, filtered)
        validation = replay_comparison(bars, split, len(bars), key, fee, slip, spread, filtered)
        stress = replay_comparison(bars, split, len(bars), key, fee*2, slip*2, spread*2, filtered)
        checks = dict(positiveValidation=validation['returnPct'] > 0,
                      atLeast30Trades=validation['tradeCount'] >= 30,
                      profitFactorAtLeast1_2=(validation['profitFactor'] or 0) >= 1.2,
                      drawdownUnder10Pct=validation['maxDrawdownPct'] <= 10,
                      positiveDoubleCosts=stress['returnPct'] > 0)
        results.append(dict(strategy=key, label=label, training=training, validation=validation,
                            doubleCostValidation=stress, checks=checks,
                            decision='추가 검증 후보' if all(checks.values()) else '연구 기준 미달', liveEligible=False))
    return dict(schemaVersion=1, market='upbit', interval='1m', results=results, liveEligible=False,
                parameters=dict(targetGrossPct=TARGET*100, stopGrossPct=STOP*100,
                                minimumCostHeadroomPct=MIN_EDGE*100, maxHoldMinutes=30, cooldownMinutes=5),
                costs=dict(feeBpsPerSide=fee*10000, slippageBpsPerSide=slip*10000, roundTripSpreadBps=spread*10000),
                assumptions=['완료된 연속 1분봉 OHLCV만 입력. 앞 70% 연구/뒤 30% 검증, 각 구간은 현금으로 시작.',
                 '신호는 이전 완료 봉까지만 사용하고 다음 봉 시가에 진입. 같은 봉 손절/목표 동시 접촉은 손절 우선.',
                 '수수료·슬리피지는 편도, 전체 스프레드는 매수/매도에 절반씩 부과. 고정 가정이며 실제 호가 재현 아님.',
                 '비용 여유는 목표 폭에서 가정 비용을 뺀 값이며 예상 수익이나 통계적 우위가 아님.',
                 '세 모형은 동일 청산/비용/쿨다운 사용. 기존 실시간 전체 종목 스캐너·순위·미완성 봉을 재현하지 않음.',
                 '단일 종목 비교. 체결 잔량·지연·미체결·다중 종목 자금 배분은 미반영. 화면의 과거 11건 재현 아님.',
                 '고정 연구값으로 최적화하지 않음. 결과를 본 뒤 변경하면 새로운 미사용 기간과 여러 종목 검증 필요.',
                 '실제 주문·전략 자동 교체·수익 보장 없음. 통과해도 실거래 미승인.'])
