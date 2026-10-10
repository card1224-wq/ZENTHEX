"""Zenthex Trading 성적표.

모든 수치는 수수료를 뺀 '실제 손익' 기준입니다.
우상향 여부는 감이 아니라 아래 숫자(기대값, 손익비, 최대 낙폭)로 판단합니다.
"""

MIN_TRADES_FOR_VERDICT = 20


def compute_performance(trades: list[dict]) -> dict:
    """trades: 오래된 것부터 정렬된 [{pnl_krw, pnl_pct, ...}] 목록."""
    count = len(trades)
    if count == 0:
        return {
            "tradeCount": 0,
            "verdict": "no_data",
            "verdictText": "아직 완료된 거래가 없습니다. 체험 모드로 먼저 거래 기록을 쌓으세요.",
            "equityCurve": [],
        }

    pnl_pcts = [float(t.get("pnl_pct") or 0.0) for t in trades]
    pnl_krws = [float(t.get("pnl_krw") or 0.0) for t in trades]
    wins = [p for p in pnl_pcts if p > 0]
    losses = [p for p in pnl_pcts if p <= 0]

    win_rate = len(wins) / count
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    expectancy = sum(pnl_pcts) / count

    gross_win_krw = sum(p for p in pnl_krws if p > 0)
    gross_loss_krw = abs(sum(p for p in pnl_krws if p <= 0))
    profit_factor = (gross_win_krw / gross_loss_krw) if gross_loss_krw > 0 else None

    # 손익분기 승률: 평균 수익과 평균 손실 크기로 본전이 되는 승률
    if avg_win + avg_loss > 0:
        breakeven_win_rate = avg_loss / (avg_win + avg_loss)
    else:
        breakeven_win_rate = None

    equity = []
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in pnl_krws:
        running += value
        equity.append(round(running, 2))
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)

    if count < MIN_TRADES_FOR_VERDICT:
        verdict = "not_enough"
        verdict_text = f"거래 {count}회: 판단하기엔 아직 적습니다. {MIN_TRADES_FOR_VERDICT}회 이상 쌓인 뒤 판단하세요."
    elif expectancy > 0 and (profit_factor is None or profit_factor >= 1.2):
        verdict = "uptrend"
        verdict_text = "우상향 신호: 수수료를 빼고도 1회 평균 손익이 플러스입니다. 투자금은 천천히 늘리세요."
    elif expectancy > 0:
        verdict = "weak_positive"
        verdict_text = "약한 플러스: 이익이 손실을 근소하게 앞섭니다. 투자금을 늘리기 전에 더 지켜보세요."
    else:
        verdict = "downtrend"
        verdict_text = "우하향: 수수료를 빼면 손실 구조입니다. 실거래 금액을 늘리지 말고 설정을 조정하세요."

    return {
        "tradeCount": count,
        "winCount": len(wins),
        "lossCount": len(losses),
        "winRate": win_rate,
        "avgWinPct": avg_win,
        "avgLossPct": avg_loss,
        "expectancyPct": expectancy,
        "breakevenWinRate": breakeven_win_rate,
        "profitFactor": profit_factor,
        "totalPnlKrw": running,
        "maxDrawdownKrw": max_drawdown,
        "verdict": verdict,
        "verdictText": verdict_text,
        "equityCurve": equity[-200:],
    }
