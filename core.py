from __future__ import annotations
from pine_numeric import pine_cmp
from dataclasses import dataclass
from typing import Any
import math
import numpy as np
import pandas as pd
LOOKBACK = 400
BUILD = 'V4.6 REBUILD'
ENGINE_REFERENCE = 'G. Balance Zones Pro v0.5.3.6'
BAL_SCAN_STEP_PCT = 1.0
BAL_MAX_ZONES = 9
BAL_MIN_COMPATIBLE_HITS = 1
BAL_VALIDATION_A = 10
BAL_VALIDATION_B = 5
BAL_BREAK_SOURCE = 'Close'
BAL_MIN_STRENGTH = 0.0
BAL_ATR_LENGTH = 14
BAL_ENABLE_INDEPENDENT_VALIDATION = True
BAL_INDEPENDENT_COOLDOWN_BARS = 6
BAL_MIN_REACTION_ATR = 0.2
BAL_ZONE_WIDTH_MODE = 'ATR'
BAL_ZONE_HALF_ATR = 0.2
BAL_ZONE_HEIGHT_PCT = 0.07
BAL_ZONE_HALF_TICKS = 12
BAL_ZONE_HEIGHT_RANGE_PCT = 1.0
BAL_SPACING_MODE = 'Range %'
BAL_MIN_SPACING_RANGE_PCT = 8.0
BAL_MIN_SPACING_ATR = 0.8
BAL_MIN_SPACING_PRICE_PCT = 0.2
BAL_CLUSTER_ADJACENT_LEVELS = False
BAL_CLUSTER_RADIUS_STEPS = 1.5
BAL_CLUSTER_MIN_STRENGTH_RATIO = 0.7
BAL_UPDATE_FREQUENCY_BARS = 1
BAL_RETAIN_PREVIOUS_ZONES = True
BAL_RETENTION_STRENGTH = 25.0
BAL_RETENTION_TOLERANCE_STEPS = 1.5

@dataclass(frozen=True)
class BalanceZone:
    center: float
    half: float
    pct_range: float
    strength: float
    hits: int
    support_hits: int
    resistance_hits: int
    dwell: int
    last_hit_age: int
    independent_tests: int
    independent_successes: int
    independent_support_success: int
    independent_resistance_success: int
    independent_breaks: int
    reliability: float
    engine: str = 'A'

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def wilder_atr(data: pd.DataFrame, length: int=BAL_ATR_LENGTH) -> pd.Series:
    """Equivalente operativo di ta.atr(): True Range + Wilder RMA."""
    if data.empty:
        return pd.Series(dtype=float)
    high = data['high'].astype(float)
    low = data['low'].astype(float)
    close = data['close'].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1, skipna=True)
    atr = pd.Series(np.nan, index=tr.index, dtype=float)
    if pine_cmp(len(tr), int(length), 'Lt'):
        return atr
    atr.iloc[length - 1] = float(tr.iloc[:length].mean())
    for i in range(length, len(tr)):
        atr.iloc[i] = (float(atr.iloc[i - 1]) * (length - 1) + float(tr.iloc[i])) / float(length)
    return atr

def _mintick_floor(data: pd.DataFrame) -> float:
    """
    Yahoo non espone syminfo.mintick.
    Con la geometria default ATR questa soglia non entra praticamente mai nel calcolo;
    manteniamo un epsilon numerico solo come protezione da zero.
    """
    if data.empty:
        return 1e-12
    ref = abs(float(data['close'].iloc[-1]))
    return max(1e-12, ref * 1e-12)

def _zone_half(center: float, rng: float, atr_now: float, mintick: float, *, zone_width_mode: str=BAL_ZONE_WIDTH_MODE, zone_half_atr: float=BAL_ZONE_HALF_ATR, zone_height_pct: float=BAL_ZONE_HEIGHT_PCT, zone_half_ticks: int=BAL_ZONE_HALF_TICKS, zone_height_range_pct: float=BAL_ZONE_HEIGHT_RANGE_PCT) -> float:
    """Porting diretto di f_zoneHalf()."""
    half = mintick
    if pine_cmp(zone_width_mode, 'Percent Price', 'Eq'):
        half = center * float(zone_height_pct) / 200.0
    elif pine_cmp(zone_width_mode, 'ATR', 'Eq'):
        half = max(mintick, float(atr_now) * float(zone_half_atr))
    elif pine_cmp(zone_width_mode, 'Ticks', 'Eq'):
        half = mintick * int(zone_half_ticks)
    else:
        half = float(rng) * float(zone_height_range_pct) / 200.0
    return max(mintick, float(half))

def _min_spacing(ref_price: float, rng: float, atr_now: float, mintick: float, *, spacing_mode: str=BAL_SPACING_MODE, min_spacing_range_pct: float=BAL_MIN_SPACING_RANGE_PCT, min_spacing_atr: float=BAL_MIN_SPACING_ATR, min_spacing_price_pct: float=BAL_MIN_SPACING_PRICE_PCT) -> float:
    """Porting diretto di f_minSpacing()."""
    if pine_cmp(spacing_mode, 'ATR', 'Eq'):
        return max(mintick, float(atr_now) * float(min_spacing_atr))
    if pine_cmp(spacing_mode, 'Percent Price', 'Eq'):
        return max(mintick, float(ref_price) * float(min_spacing_price_pct) / 100.0)
    return max(mintick, float(rng) * float(min_spacing_range_pct) / 100.0)

def _future_extremes(values: np.ndarray, validation_bars: int) -> tuple[np.ndarray, np.ndarray]:
    """Min/max delle successive validation_bars barre, in ordine cronologico."""
    n = len(values)
    fmin = np.full(n, np.nan, dtype=float)
    fmax = np.full(n, np.nan, dtype=float)
    vb = int(validation_bars)
    for pos in range(n):
        a = pos + 1
        b = min(n, pos + vb + 1)
        if pine_cmp(a, b, 'Lt'):
            window = values[a:b]
            fmin[pos] = float(np.nanmin(window))
            fmax[pos] = float(np.nanmax(window))
    return (fmin, fmax)

def _evaluate_compatible(data: pd.DataFrame, center: float, half: float, scan_limit: int, step_bars: int, valid_bars: int, *, break_source: str=BAL_BREAK_SOURCE, future_min: np.ndarray | None=None, future_max: np.ndarray | None=None) -> tuple[int, int, int, int, int, float]:
    """
    Porting 1:1 della logica f_evaluateCompatibleV().
    In Python Daily step_bars=1, ma il parametro resta esplicito come nel Pine.
    """
    lows = data['low'].to_numpy(float)
    highs = data['high'].to_numpy(float)
    closes = data['close'].to_numpy(float)
    top = float(center + half)
    bottom = float(center - half)
    support_hits = 0
    resistance_hits = 0
    dwell_bars = 0
    nearest_hit_age: int | None = None
    hold_span = int(valid_bars) * int(step_bars)
    first_offset = hold_span + int(step_bars)
    last_offset = int(scan_limit) - int(step_bars)
    current = len(data) - 1
    if pine_cmp(break_source, 'Close', 'Eq'):
        break_low_arr = closes
        break_high_arr = closes
    else:
        break_low_arr = lows
        break_high_arr = highs
    if pine_cmp(last_offset, first_offset, 'GtE'):
        for i in range(first_offset, last_offset + 1, int(step_bars)):
            pos = current - i
            if pine_cmp(pos, 0, 'Lt') or pine_cmp(pos, len(data), 'GtE'):
                continue
            overlaps = pine_cmp(lows[pos], top, 'LtE') and pine_cmp(highs[pos], bottom, 'GtE')
            if not overlaps:
                continue
            dwell_bars += 1
            is_support = pine_cmp(closes[pos], center, 'GtE')
            end_pos = pos + int(valid_bars) * int(step_bars)
            if pine_cmp(end_pos, len(data), 'GtE'):
                continue
            broken = False
            if is_support:
                vals = break_low_arr[pos + int(step_bars):end_pos + 1:int(step_bars)]
                if vals.size and pine_cmp(float(np.nanmin(vals)), bottom, 'Lt'):
                    broken = True
            else:
                vals = break_high_arr[pos + int(step_bars):end_pos + 1:int(step_bars)]
                if vals.size and pine_cmp(float(np.nanmax(vals)), top, 'Gt'):
                    broken = True
            if not broken:
                if is_support:
                    support_hits += 1
                else:
                    resistance_hits += 1
                age = int(round(i / int(step_bars)))
                nearest_hit_age = age if nearest_hit_age is None else min(nearest_hit_age, age)
    hits = support_hits + resistance_hits
    hit_score = 1.0 - math.exp(-hits / 18.0)
    dwell_score = 1.0 - math.exp(-dwell_bars / 45.0)
    role_mix = min(support_hits, resistance_hits) / max(1.0, float(max(support_hits, resistance_hits)))
    freshness_score = 0.0 if nearest_hit_age is None else math.exp(-nearest_hit_age / 200.0)
    density_score = hits / max(1.0, float(dwell_bars))
    density_score = min(1.0, density_score)
    strength = 100.0 * (0.5 * hit_score + 0.15 * dwell_score + 0.12 * role_mix + 0.13 * freshness_score + 0.1 * density_score)
    strength = _clamp(strength, 0.0, 100.0)
    return (support_hits, resistance_hits, hits, dwell_bars, nearest_hit_age if nearest_hit_age is not None else 99999, strength)

def _evaluate_independent(data: pd.DataFrame, atr: pd.Series, center: float, half: float, scan_limit: int, step_bars: int, valid_bars: int, mintick: float, *, enable_independent_validation: bool=BAL_ENABLE_INDEPENDENT_VALIDATION, independent_cooldown_bars: int=BAL_INDEPENDENT_COOLDOWN_BARS, min_reaction_atr: float=BAL_MIN_REACTION_ATR, break_source: str=BAL_BREAK_SOURCE) -> tuple[int, int, int, int, int, float]:
    """Porting diretto di f_evaluateIndependentV()."""
    top = float(center + half)
    bottom = float(center - half)
    tests = 0
    successes = 0
    support_success = 0
    resistance_success = 0
    breaks = 0
    last_accepted_offset: int | None = None
    hold_span = int(valid_bars) * int(step_bars)
    cooldown_span = int(independent_cooldown_bars) * int(step_bars)
    first_offset = hold_span + int(step_bars)
    last_offset = int(scan_limit) - int(step_bars)
    if not enable_independent_validation or pine_cmp(last_offset, first_offset, 'Lt'):
        return (tests, successes, support_success, resistance_success, breaks, math.nan)
    lows = data['low'].to_numpy(float)
    highs = data['high'].to_numpy(float)
    closes = data['close'].to_numpy(float)
    atr_arr = atr.to_numpy(float)
    current = len(data) - 1
    for i in range(first_offset, last_offset + 1, int(step_bars)):
        pos = current - i
        prev_pos = current - (i + int(step_bars))
        if pine_cmp(pos, 0, 'Lt') or pine_cmp(prev_pos, 0, 'Lt'):
            continue
        overlaps = pine_cmp(lows[pos], top, 'LtE') and pine_cmp(highs[pos], bottom, 'GtE')
        previous_above = pine_cmp(closes[prev_pos], top, 'Gt')
        previous_below = pine_cmp(closes[prev_pos], bottom, 'Lt')
        independent_entry = overlaps and (previous_above or previous_below)
        cooldown_ok = last_accepted_offset is None or pine_cmp(abs(i - last_accepted_offset), cooldown_span, 'GtE')
        if not (independent_entry and cooldown_ok):
            continue
        is_support_test = previous_above
        broken = False
        max_away = 0.0
        atr_at_test = atr_arr[pos] if pine_cmp(pos, len(atr_arr), 'Lt') and math.isfinite(atr_arr[pos]) else mintick
        atr_at_test = max(float(atr_at_test), mintick)
        for k in range(1, int(valid_bars) + 1):
            target_offset = i - k * int(step_bars)
            if pine_cmp(target_offset, 0, 'Lt'):
                continue
            later_pos = current - target_offset
            if pine_cmp(later_pos, 0, 'Lt') or pine_cmp(later_pos, len(data), 'GtE'):
                continue
            break_low = closes[later_pos] if pine_cmp(break_source, 'Close', 'Eq') else lows[later_pos]
            break_high = closes[later_pos] if pine_cmp(break_source, 'Close', 'Eq') else highs[later_pos]
            if is_support_test:
                if pine_cmp(break_low, bottom, 'Lt'):
                    broken = True
                max_away = max(max_away, highs[later_pos] - center)
            else:
                if pine_cmp(break_high, top, 'Gt'):
                    broken = True
                max_away = max(max_away, center - lows[later_pos])
        reacted_enough = pine_cmp(max_away, atr_at_test * float(min_reaction_atr), 'GtE')
        success = not broken and reacted_enough
        tests += 1
        if success:
            successes += 1
            if is_support_test:
                support_success += 1
            else:
                resistance_success += 1
        if broken:
            breaks += 1
        last_accepted_offset = i
    reliability = 100.0 * successes / tests if pine_cmp(tests, 0, 'Gt') else math.nan
    return (tests, successes, support_success, resistance_success, breaks, reliability)

def _too_close_zone(candidate: float, zones: list[BalanceZone], spacing: float) -> bool:
    """Porting diretto di f_tooCloseZone()."""
    for z in zones:
        if pine_cmp(abs(float(candidate) - float(z.center)), float(spacing), 'Lt'):
            return True
    return False

def _cluster_center(peak_idx: int, centers: list[float], strengths: list[float], rng: float, *, cluster_adjacent_levels: bool=BAL_CLUSTER_ADJACENT_LEVELS, scan_step_pct: float=BAL_SCAN_STEP_PCT, cluster_radius_steps: float=BAL_CLUSTER_RADIUS_STEPS, cluster_min_strength_ratio: float=BAL_CLUSTER_MIN_STRENGTH_RATIO) -> float:
    """Porting diretto di f_clusterCenter()."""
    peak_center = float(centers[peak_idx])
    peak_strength = float(strengths[peak_idx])
    result = peak_center
    if cluster_adjacent_levels:
        radius_price = float(rng) * float(scan_step_pct) / 100.0 * float(cluster_radius_steps)
        weighted_sum = 0.0
        weight_total = 0.0
        for c, s in zip(centers, strengths):
            if pine_cmp(abs(float(c) - peak_center), radius_price, 'LtE') and pine_cmp(float(s), peak_strength * float(cluster_min_strength_ratio), 'GtE'):
                w = max(float(s), 0.01)
                weighted_sum += float(c) * w
                weight_total += w
        if pine_cmp(weight_total, 0, 'Gt'):
            result = weighted_sum / weight_total
    return result

def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    x = df.copy()
    x.columns = [str(c).lower().replace(' ', '_') for c in x.columns]
    required = ['open', 'high', 'low', 'close']
    if any((c not in x.columns for c in required)):
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    if 'volume' not in x.columns:
        x['volume'] = np.nan
    x = x[['open', 'high', 'low', 'close', 'volume']].copy()
    for c in x.columns:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna(subset=required)
    x = x[~x.index.duplicated(keep='last')].sort_index()
    return x
