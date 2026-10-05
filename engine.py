from pine_numeric import pine_cmp
'Port V12 CLOSED. Experimental until parity against TradingView snapshots.'
import math
import numpy as np
import pandas as pd
from core import wilder_atr, _evaluate_compatible, _evaluate_independent, BalanceZone, _normalize_ohlc
from fast_compatible import evaluate as _evaluate_compatible, future_extremes
PHASES = {'EARLY', 'FRESH', 'TRANSITION'}

def phase(signal, trend, mem, ha, inv, seq):
    bull = pine_cmp(trend, 1, 'Eq') and pine_cmp(ha, 1, 'Eq')
    fresh = bull and pine_cmp(signal, 1, 'Eq') and (pine_cmp(0, mem, 'LtE') and pine_cmp(mem, 3, 'Lt'))
    return 'FRESH' if fresh else 'EARLY' if bull and pine_cmp(inv, 1, 'Eq') and pine_cmp(seq, 1, 'Eq') else 'TRANSITION' if pine_cmp(ha, 1, 'Eq') and (pine_cmp(1, seq, 'LtE') and pine_cmp(seq, 2, 'LtE')) and pine_cmp(trend, -1, 'Eq') else 'MATURE' if bull else 'WAIT'

def timing(data):
    c = data.close

    def wma(x, n):
        w = np.arange(1, n + 1)
        return x.rolling(n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True)
    hma = wma(2 * wma(c, 8) - wma(c, 16), 4)
    bull = pine_cmp(hma, hma.shift(1), 'Gt')
    hc = data[['open', 'high', 'low', 'close']].mean(axis=1).to_numpy()
    ho = np.empty(len(data))
    ho[0] = (data.open.iloc[0] + c.iloc[0]) / 2
    for i in range(1, len(data)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    green = pine_cmp(hc, ho, 'GtE')
    rows = []
    lastlong = lastshort = None
    lastchange = None
    seq = 0
    for i in range(len(data)):
        b = bool(bull.iloc[i])
        prev = bool(bull.iloc[i - 1]) if i else False
        if i and pine_cmp(b, prev, 'NotEq'):
            lastchange = i
            if b:
                lastlong = i
            else:
                lastshort = i
        signal = 0
        if lastlong is not None and lastshort is not None:
            if pine_cmp(i - lastlong, 3, 'Lt') and pine_cmp(lastlong, lastshort, 'Gt'):
                signal = 1
            elif pine_cmp(i - lastshort, 3, 'Lt') and pine_cmp(lastshort, lastlong, 'Gt'):
                signal = -1
        inv = 0
        if i and pine_cmp(green[i], green[i - 1], 'NotEq'):
            seq = 1
            inv = 1 if green[i] else -1
        else:
            seq = seq + 1 if seq else 1
        rows.append(dict(HS=signal, HT=1 if b else -1, MEM=i - lastchange if lastchange is not None else -1, HA=1 if green[i] else -1, INV=inv, SEQ=seq, HMA=hma.iloc[i]))
    return pd.DataFrame(rows, index=data.index)

def auto_half(d, atr, center, discovery, valid, scan, tick):
    l, h, c = (d.low.to_numpy(), d.high.to_numpy(), d.close.to_numpy())
    a = atr.to_numpy()
    n = len(d) - 1
    ds = []
    last = None
    top = center + discovery
    bottom = center - discovery
    for off in range(valid + 1, scan):
        j = n - off
        above = pine_cmp(c[j - 1], top, 'Gt')
        below = pine_cmp(c[j - 1], bottom, 'Lt')
        if not (pine_cmp(l[j], top, 'LtE') and pine_cmp(h[j], bottom, 'GtE') and (above or below) and (last is None or pine_cmp(off - last, 6, 'GtE'))):
            continue
        at = max(a[j] if np.isfinite(a[j]) else tick, tick)
        distance = min(abs((l[j] if above else h[j]) - center), discovery)
        failed = pine_cmp(c[j], bottom, 'Lt') if above else pine_cmp(c[j], top, 'Gt')
        success = False
        for k in range(1, valid + 1):
            if success or failed:
                break
            q = j + k
            if pine_cmp(c[q], bottom, 'Lt') if above else pine_cmp(c[q], top, 'Gt'):
                failed = True
            elif pine_cmp(h[q] - center if above else center - l[q], at * 0.2, 'GtE'):
                success = True
        if success:
            ds.append(distance / at)
        last = off
    if pine_cmp(len(ds), 3, 'Lt'):
        return discovery
    med = np.median(ds)
    mad = np.median(np.abs(np.array(ds) - med))
    return max(tick, min(discovery, max(tick, atr.iloc[-1] * (med + 1.4826 * mad))))

def zones(d, atr, valid, engine, old, tick):
    n = len(d) - 1
    scan = min(400, n)
    window = d.iloc[-400:]
    lo = window.low.min()
    rng = max(window.high.max() - lo, tick * 10)
    moves = np.abs(np.diff(d.close.iloc[max(0, n - scan):n].to_numpy()))
    discovery = max(tick, float(np.median(moves)))
    future_min, future_max = future_extremes(d.close.to_numpy(float), valid)
    candidates = []
    for pct in range(101):
        center = lo + rng * pct / 100
        stats = _evaluate_compatible(d, center, discovery, scan, 1, valid, future_min=future_min, future_max=future_max)
        if pine_cmp(stats[2], 1, 'GtE'):
            candidates.append((center, stats[-1]))
    chosen = []
    used = set()
    spacing = max(tick, rng * 0.08)

    def add(k):
        center = candidates[k][0]
        if any((pine_cmp(round(float(abs(center - z.center)), 9), round(float(spacing), 9), 'Lt') for z in chosen)):
            return
        half = auto_half(d, atr, center, discovery, valid, scan, tick)
        sup, res, hits, dwell, age, strength = _evaluate_compatible(d, center, half, scan, 1, valid, future_min=future_min, future_max=future_max)
        tests, succ, ss, rs, br, rel = _evaluate_independent(d, atr, center, half, scan, 1, valid, tick)
        chosen.append(BalanceZone(center, half, 100 * (center - lo) / rng, strength, hits, sup, res, dwell, age, tests, succ, ss, rs, br, rel, engine))
        used.add(k)
    for z in old:
        available = [k for k in range(len(candidates)) if k not in used]
        if pine_cmp(len(chosen), 9, 'GtE') or not available:
            break
        k = min(available, key=lambda k: abs(candidates[k][0] - z.center))
        if pine_cmp(abs(candidates[k][0] - z.center), rng * 0.015, 'LtE') and pine_cmp(candidates[k][1], 25, 'GtE'):
            add(k)
    for k in sorted(range(len(candidates)), key=lambda k: (-candidates[k][1], k)):
        if pine_cmp(len(chosen), 9, 'GtE'):
            break
        if k not in used:
            add(k)
    return sorted(chosen, key=lambda z: z.center)

def snapshot(d, atr, oldA, oldB, tick):
    a = zones(d, atr, 10, 'A', oldA, tick)
    b = zones(d, atr, 5, 'B', oldB, tick)
    visible = a + [z for z in b if not any((pine_cmp(z.center + z.half, x.center - x.half, 'GtE') and pine_cmp(z.center - z.half, x.center + x.half, 'LtE') for x in a))]
    best = None
    bestscore = -1
    for z in visible:
        bottom, top = (z.center - z.half, z.center + z.half)
        touches = low = high = last = 0
        for off in range(3):
            row = d.iloc[-1 - off]
            prev = d.close.iloc[-2 - off]
            if pine_cmp(row.low, top, 'LtE') and pine_cmp(row.high, bottom, 'GtE'):
                touches += 1
                t = 3
                if pine_cmp(prev, top, 'Gt'):
                    low += 1
                    t = 4 if pine_cmp(row.close, bottom, 'Lt') else 1
                elif pine_cmp(prev, bottom, 'Lt'):
                    high += 1
                    t = 4 if pine_cmp(row.close, top, 'Gt') else 2
                if not last:
                    last = t
        if pine_cmp(touches, 2, 'Lt'):
            continue
        score = 0.45 * 100 * touches / 3 + 0.35 * z.strength + 0.2 * (z.reliability if math.isfinite(z.reliability) else 50)
        if pine_cmp(score, bestscore, 'LtE'):
            continue
        bestscore = score
        p = d.close.iloc[-1]
        distance = max(bottom - p, p - top, 0) / atr.iloc[-1]
        profile = 'CROSS' if pine_cmp(last, 4, 'Eq') else 'SUPPORT_TEST' if pine_cmp(low, high, 'Gt') else 'RESISTANCE_TEST' if pine_cmp(high, low, 'Gt') else 'INSIDE' if pine_cmp(last, 3, 'Eq') else 'MIXED' if pine_cmp(low, 0, 'Gt') else 'INSIDE'
        best = dict(BAL=z.center, HALF=z.half, STATE='ACTIVE' if pine_cmp(distance, 0, 'Eq') else 'NEAR', DIST=distance, TOUCH=touches, LOW=low, HIGH=high, PROFILE=profile, ENGINE=z.engine, SCORE=bestscore)
    return (best, a, b)

def replay(data, ticker, start=None, mode='restart', tick=0.0001, progress=None):
    d = _normalize_ohlc(data)
    atr = wilder_atr(d)
    t = timing(d)
    a = []
    b = []
    rows = []
    for i in range(60, len(d)):
        if mode == 'restart' and start is not None and d.index[i] < pd.Timestamp(start):
            continue
        state = t.iloc[i].to_dict()
        ph = phase(state['HS'], state['HT'], state['MEM'], state['HA'], state['INV'], state['SEQ'])
        # Restart has no retained zones. Non-target phases cannot emit events.
        # Persistent must still update zones on every session.
        if mode == 'restart' and ph not in PHASES:
            if progress:
                progress(i, len(d))
            continue
        if pine_cmp(mode, 'restart', 'Eq'):
            a = []
            b = []
        snap, a, b = snapshot(d.iloc[:i + 1], atr.iloc[:i + 1], a, b, tick)
        if progress:
            progress(i, len(d))
        if start is not None and pine_cmp(d.index[i], pd.Timestamp(start), 'Lt'):
            continue
        if snap is None:
            continue
        if ph not in PHASES or pine_cmp(snap['DIST'], 1.5, 'Gt'):
            continue
        row = dict(Date=d.index[i], Ticker=ticker, PHASE=ph, Close=d.close.iloc[i], **snap, **state)
        row['SLOPE'] = (t.HMA.iloc[i] - t.HMA.iloc[i - 1]) / atr.iloc[i]
        row['RET12'] = (d.close.iloc[i - 1] - d.close.iloc[i - 13]) / atr.iloc[i]
        entry = d.open.iloc[i + 1] if pine_cmp(i + 1, len(d), 'Lt') else np.nan
        row['EntryOpen'] = entry
        for horizon in (1, 3, 5, 10, 20):
            complete = pine_cmp(i + horizon, len(d), 'Lt')
            future = d.iloc[i + 1:i + horizon + 1]
            row[f'CloseRet{horizon}'] = 100 * (d.close.iloc[i + horizon] / d.close.iloc[i] - 1) if complete else np.nan
            row[f'OpenRet{horizon}'] = 100 * (d.close.iloc[i + horizon] / entry - 1) if complete else np.nan
            row[f'MFE{horizon}'] = 100 * (future.high.max() / entry - 1) if complete else np.nan
            row[f'MAE{horizon}'] = 100 * (future.low.min() / entry - 1) if complete else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
