"""Vectorized compatible tests; the scalar evaluator remains the reference."""
import math
import numpy as np
from pine_numeric import pine_cmp


def future_extremes(close, valid):
    n = len(close)
    low = np.full(n, np.nan)
    high = np.full(n, np.nan)
    # Only positions with a full validation window can enter compatible tests.
    if n > valid:
        windows = np.lib.stride_tricks.sliding_window_view(close[1:], valid)
        low[:len(windows)] = np.nanmin(windows, axis=1)
        high[:len(windows)] = np.nanmax(windows, axis=1)
    return low, high


def evaluate(data, center, half, scan_limit, step_bars, valid_bars,
             *, future_min=None, future_max=None):
    if step_bars != 1:
        raise ValueError('Fast compatible evaluator requires Daily step 1')
    lows, highs, closes = (data[x].to_numpy(float) for x in ('low', 'high', 'close'))
    if future_min is None or future_max is None:
        future_min, future_max = future_extremes(closes, valid_bars)
    offsets = np.arange(valid_bars + 1, scan_limit, dtype=int)
    positions = len(data) - 1 - offsets
    keep = (positions >= 0) & (positions + valid_bars < len(data))
    offsets, positions = offsets[keep], positions[keep]
    top, bottom = float(center + half), float(center - half)
    overlap = pine_cmp(lows[positions], top, 'LtE') & pine_cmp(highs[positions], bottom, 'GtE')
    support = pine_cmp(closes[positions], center, 'GtE')
    broken = np.where(support, pine_cmp(future_min[positions], bottom, 'Lt'),
                      pine_cmp(future_max[positions], top, 'Gt'))
    held = overlap & ~broken
    sup = int(np.count_nonzero(held & support))
    res = int(np.count_nonzero(held & ~support))
    hits, dwell = sup + res, int(np.count_nonzero(overlap))
    age = int(offsets[held].min()) if hits else 99999
    strength = 100 * (
        .5 * (1 - math.exp(-hits / 18.0))
        + .15 * (1 - math.exp(-dwell / 45.0))
        + .12 * min(sup, res) / max(1.0, float(max(sup, res)))
        + .13 * (math.exp(-age / 200.0) if hits else 0)
        + .1 * min(1.0, hits / max(1.0, float(dwell))))
    return sup, res, hits, dwell, age, min(100.0, max(0.0, strength))
