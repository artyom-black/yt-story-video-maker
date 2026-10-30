"""Measure a voice without listening: median pitch (Hz) and the longest silent gap (s)."""
from __future__ import annotations

import numpy as np

from .voice import RATE


def pitch_hz(a: np.ndarray, rate: int = RATE) -> float:
    """Median fundamental frequency of the voiced parts (simple autocorrelation)."""
    win, hop = int(0.04 * rate), int(0.01 * rate)
    lo, hi = int(rate / 300), int(rate / 65)          # search 65..300 Hz
    f0 = []
    loud = np.sqrt(np.mean(a ** 2)) or 1e-9
    for i in range(0, len(a) - win, hop):
        seg = a[i:i + win] - a[i:i + win].mean()
        if np.sqrt(np.mean(seg ** 2)) < 0.5 * loud:
            continue
        ac = np.correlate(seg, seg, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.45:
            f0.append(rate / lag)
    return float(np.median(f0)) if f0 else 0.0


def longest_gap(a: np.ndarray, rate: int = RATE) -> float:
    """Longest stretch of near-silence inside the speech (ignores the very start and end)."""
    hop = int(0.01 * rate)
    env = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
    quiet = env < 0.04 * (env.max() or 1)
    idx = np.where(~quiet)[0]
    if not len(idx):
        return 0.0
    quiet = quiet[idx[0]:idx[-1]]
    best = run = 0
    for q in quiet:
        run = run + 1 if q else 0
        best = max(best, run)
    return best * 0.01


def describe(hz: float) -> str:
    if hz < 105:
        return "deep"
    if hz < 125:
        return "medium-deep"
    if hz < 150:
        return "medium"
    return "light / young"
