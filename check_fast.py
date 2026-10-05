"""Check the optimized Daily evaluator against its scalar reference."""
import numpy as np
import pandas as pd
from core import _evaluate_compatible
from fast_compatible import evaluate

rng = np.random.default_rng(14)
count = 0
for n in (20, 65, 420):
    close = 100 + rng.normal(size=n).cumsum()
    data = pd.DataFrame(dict(open=close, high=close+.7, low=close-.7, close=close))
    for valid in (5, 10):
        for center in np.linspace(close.min(), close.max(), 13):
            for half in (.0001, .7, 1.5):
                old = _evaluate_compatible(data, center, half, min(400, n-1), 1, valid)
                new = evaluate(data, center, half, min(400, n-1), 1, valid)
                assert old[:5] == new[:5], (old, new)
                assert abs(old[5] - new[5]) < 1e-12
                count += 1
print(f'PASS: {count} compatible evaluations match the scalar reference')
