"""Music and sound effects made by code: free, no copyright claims, same every time.

music(style, seconds) -> looping background track for a MUSIC style
sfx(name)             -> one sound effect for an SFX name
All audio is mono float32 at RATE.
"""
from __future__ import annotations

import functools

import numpy as np
from scipy.signal import butter, lfilter

RATE = 24000
A4 = 440.0
NOTE = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}


def hz(name: str) -> float:
    """'A3', 'C#4' ... -> frequency."""
    n, octave = name[:-1], int(name[-1])
    return A4 * 2 ** ((NOTE[n] + (octave - 4) * 12) / 12)


def _t(sec):
    return np.arange(int(sec * RATE)) / RATE


def _env(n, a=0.01, d=0.1, s=0.7, r=0.2, length=None):
    length = length or n / RATE
    t = np.arange(n) / RATE
    e = np.ones(n) * s
    e[t < a] = t[t < a] / max(a, 1e-4)
    m = (t >= a) & (t < a + d)
    e[m] = 1 - (1 - s) * (t[m] - a) / max(d, 1e-4)
    rel = t > length - r
    e[rel] *= np.clip((length - t[rel]) / max(r, 1e-4), 0, 1)
    return e


def _lp(x, cutoff):
    b, a = butter(2, min(cutoff / (RATE / 2), 0.99), "low")
    return lfilter(b, a, x)


def _hp(x, cutoff):
    b, a = butter(2, min(cutoff / (RATE / 2), 0.99), "high")
    return lfilter(b, a, x)


def _bp(x, lo, hi):
    b, a = butter(2, [lo / (RATE / 2), min(hi / (RATE / 2), 0.99)], "band")
    return lfilter(b, a, x)


# ---------------------------------------------------------------- instruments
def pad(freqs, sec, bright=1800, level=0.18):
    t = _t(sec)
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            ph = 2 * np.pi * f * (1 + det) * t
            x += 2 * ((ph / (2 * np.pi)) % 1) - 1          # saw
    x = _lp(x / (3 * len(freqs)), bright)
    return x * _env(len(t), a=min(0.4, sec / 3), d=0.2, s=0.9, r=min(0.4, sec / 3)) * level


def pluck(f, sec, level=0.3, damp=0.996):
    """Karplus-Strong plucked string."""
    n = int(sec * RATE)
    p = max(2, int(RATE / f))
    rng = np.random.default_rng(int(f * 10))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out * level


@functools.lru_cache(maxsize=256)
def _pluck_cached(f, sec, level, damp):
    return pluck(f, sec, level, damp)


def bass(f, sec, level=0.32):
    t = _t(sec)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return x * _env(len(t), 0.005, 0.08, 0.7, 0.05) * level


def tuba(f, sec, level=0.3):
    t = _t(sec)
    x = _lp(np.sign(np.sin(2 * np.pi * f * t)) * 0.6 + np.sin(2 * np.pi * f * t), 600)
    return x * _env(len(t), 0.02, 0.1, 0.6, 0.06) * level


def kick(level=0.6):
    t = _t(0.35)
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 9) * level


def snare(level=0.35):
    t = _t(0.22)
    rng = np.random.default_rng(3)
    x = _bp(rng.uniform(-1, 1, len(t)), 1200, 6000) * 1.5 + 0.3 * np.sin(2 * np.pi * 190 * t)
    return x * np.exp(-t * 22) * level


def hat(level=0.12):
    t = _t(0.06)
    rng = np.random.default_rng(5)
    return _hp(rng.uniform(-1, 1, len(t)), 7000) * np.exp(-t * 60) * level


def wood(level=0.25):
    t = _t(0.08)
    return np.sin(2 * np.pi * 900 * t) * np.exp(-t * 70) * level


def timpani(f=hz("A1"), level=0.5):
    t = _t(1.2)
    rng = np.random.default_rng(9)
    x = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) + 0.2 * _lp(rng.uniform(-1, 1, len(t)), 300)
    return x * np.exp(-t * 3.5) * level


def _put(buf, x, at):
    i = int(at * RATE)
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n]


# ---------------------------------------------------------------- music styles
# chord = list of note names; each style: bpm, chords (one per bar), what plays
STYLES = {
    "mystery": {"bpm": 84, "chords": [["A2", "E3", "C4"], ["F2", "C3", "A3"], ["D2", "A2", "F3"], ["E2", "B2", "G#3"]]},
    "tension": {"bpm": 100, "chords": [["A1", "E2", "A2"], ["A1", "E2", "A#2"], ["A1", "E2", "A2"], ["G#1", "D#2", "G#2"]]},
    "action": {"bpm": 132, "chords": [["A2", "E3", "A3"], ["F2", "C3", "A3"], ["C3", "G3", "C4"], ["G2", "D3", "B3"]]},
    "comedy": {"bpm": 120, "chords": [["C3", "E3", "G3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"], ["G2", "B2", "D3"]]},
    "sad": {"bpm": 68, "chords": [["A2", "C3", "E3"], ["F2", "A2", "C3"], ["C3", "E3", "G3"], ["G2", "B2", "D3"]]},
    "epic": {"bpm": 92, "chords": [["A2", "E3", "A3", "C4"], ["F2", "C3", "F3", "A3"], ["C3", "G3", "C4", "E4"], ["G2", "D3", "G3", "B3"]]},
    "calm": {"bpm": 80, "chords": [["C3", "E3", "G3"], ["G2", "B2", "D3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"]]},
}


def _up(name, octaves):
    return name[:-1] + str(int(name[-1]) + octaves)


@functools.lru_cache(maxsize=16)
def loop(style: str) -> np.ndarray:
    """8 bars of music for a style; loops seamlessly."""
    cfg = STYLES[style]
    beat = 60 / cfg["bpm"]
    bar = beat * 4
    bars = cfg["chords"] * 2
    out = np.zeros(int(bar * len(bars) * RATE) + RATE)
    for bi, chord in enumerate(bars):
        t0 = bi * bar
        root = chord[0]
        freqs = [hz(n) for n in chord]
        if style in ("mystery", "sad", "calm", "epic", "tension"):
            _put(out, pad(freqs[1:], bar + 0.3, 1400 if style != "epic" else 2400,
                          0.13 if style != "epic" else 0.2), t0)
        if style == "mystery":
            for k in range(8):
                n = chord[(k * 2) % len(chord)]
                _put(out, _pluck_cached(hz(_up(n, 1)), beat, 0.22, 0.995), t0 + k * beat / 2)
            _put(out, bass(hz(root), bar * 0.95, 0.22), t0)
        elif style == "tension":
            for k in range(8):
                _put(out, bass(hz(_up(root, 1)), beat / 2 * 0.8, 0.2), t0 + k * beat / 2)
            for k in (0, 0.35):
                _put(out, kick(0.5), t0 + k * beat * 2)
                _put(out, kick(0.5), t0 + beat * 2 + k * beat * 2)
        elif style == "action":
            for k in range(8):
                _put(out, bass(hz(root), beat / 2 * 0.9, 0.3), t0 + k * beat / 2)
                _put(out, hat(), t0 + k * beat / 2 + beat / 4)
            for k in range(4):
                _put(out, kick(), t0 + k * beat)
            _put(out, snare(), t0 + beat)
            _put(out, snare(), t0 + 3 * beat)
            _put(out, pad([hz(_up(n, 1)) for n in chord[1:]], bar, 2600, 0.1), t0)
        elif style == "comedy":
            _put(out, tuba(hz(root), beat * 0.6), t0)
            _put(out, tuba(hz(chord[2]), beat * 0.6), t0 + 2 * beat)
            for k, n in enumerate([chord[0], chord[1], chord[2], chord[1]] * 2):
                _put(out, _pluck_cached(hz(_up(n, 2)), beat / 2, 0.2, 0.99), t0 + k * beat / 2)
            _put(out, wood(), t0 + beat)
            _put(out, wood(), t0 + 3 * beat)
            _put(out, wood(0.15), t0 + 3.5 * beat)
        elif style in ("sad", "calm"):
            for k, n in enumerate(chord + [chord[1]]):
                _put(out, _pluck_cached(hz(_up(n, 1)), beat * 1.5, 0.17, 0.997), t0 + k * beat)
            _put(out, bass(hz(root), bar * 0.95, 0.15), t0)
        elif style == "epic":
            _put(out, timpani(hz(_up(root, -1)) if int(root[-1]) > 1 else hz(root)), t0)
            _put(out, timpani(hz(_up(root, -1)) if int(root[-1]) > 1 else hz(root), 0.3), t0 + 2.5 * beat)
            _put(out, bass(hz(root), bar * 0.95, 0.25), t0)
            for k in range(4):
                _put(out, _pluck_cached(hz(_up(chord[k % len(chord)], 1)), beat, 0.14, 0.997), t0 + k * beat)
    n = int(bar * len(bars) * RATE)
    tail = out[n:n + RATE]
    out = out[:n]
    out[:len(tail)] += tail          # wrap the ringing tail to the start so the loop is seamless
    peak = np.abs(out).max() or 1
    return (out / peak * 0.8).astype(np.float32)


def music(style: str, seconds: float) -> np.ndarray:
    if style not in STYLES:
        return np.zeros(int(seconds * RATE), np.float32)
    lp = loop(style)
    reps = int(np.ceil(seconds * RATE / len(lp)))
    return np.tile(lp, reps)[:int(seconds * RATE)]


# ---------------------------------------------------------------- sound effects
def _noise(sec, seed=1):
    return np.random.default_rng(seed).uniform(-1, 1, int(sec * RATE))


@functools.lru_cache(maxsize=32)
def sfx(name: str) -> np.ndarray:
    t = None
    if name == "whoosh":
        n = _noise(0.45, 2)
        t = _t(0.45)
        x = np.zeros_like(n)
        for i, f in enumerate(np.linspace(400, 3000, 9)):
            seg = slice(int(i * len(n) / 9), int((i + 1) * len(n) / 9))
            x[seg] = _bp(n, f * 0.7, f * 1.3)[seg]
        x *= np.sin(np.pi * t / t[-1]) ** 2 * 1.4
    elif name == "boom":
        t = _t(1.4)
        f = 35 + 60 * np.exp(-t * 6)
        x = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 2.5) + 0.4 * _lp(_noise(1.4, 3), 200) * np.exp(-t * 4)
    elif name == "crowd":
        t = _t(3.0)
        x = np.zeros_like(t)
        for k in range(14):
            n = _bp(_noise(3.0, 10 + k), 300 + k * 40, 900 + k * 60)
            x += n * (0.5 + 0.5 * np.sin(2 * np.pi * (1.5 + k * 0.37) * t + k)) ** 2
        x = x / 6 * _env(len(t), 0.4, 0.1, 1, 0.8)
    elif name == "swords":
        t = _t(0.9)
        x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2200, 6), (3100, 8), (4700, 11), (1500, 5)))
        x = x / 3 + _hp(_noise(0.9, 4), 3000) * np.exp(-t * 40)
        x = np.concatenate([x[:int(0.45 * RATE)], x[:int(0.45 * RATE)] * 0.8])
    elif name == "thunder":
        t = _t(3.0)
        x = _lp(_noise(3.0, 6), 180) * 3 * (np.exp(-t * 1.2) + 0.6 * np.exp(-np.abs(t - 0.4) * 6))
    elif name == "wind":
        t = _t(3.0)
        x = _bp(_noise(3.0, 7), 300, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.4 * t)) * _env(len(t), 0.8, 0.1, 1, 0.8)
    elif name == "fire":
        t = _t(3.0)
        x = _lp(_noise(3.0, 8), 900) * 0.4
        rng = np.random.default_rng(11)
        for at in rng.uniform(0, 2.9, 40):
            i = int(at * RATE)
            x[i:i + 120] += _hp(_noise(0.005, int(at * 100)), 2000) * 2
        x *= _env(len(t), 0.3, 0.1, 1, 0.5)
    elif name == "footsteps":
        t = _t(1.6)
        x = np.zeros_like(t)
        for k in range(4):
            step = _lp(_noise(0.09, 20 + k), 700) * np.exp(-_t(0.09) * 40) * 2
            i = int(k * 0.4 * RATE)
            x[i:i + len(step)] += step
    elif name == "water":
        t = _t(2.0)
        x = np.zeros_like(t)
        rng = np.random.default_rng(13)
        for at in rng.uniform(0, 1.9, 30):
            f0 = rng.uniform(500, 1400)
            tt = _t(0.06)
            b = np.sin(2 * np.pi * np.cumsum(f0 + 3000 * tt) / RATE) * np.exp(-tt * 50) * 0.5
            i = int(at * RATE)
            x[i:i + len(b)] += b
        x += _bp(_noise(2.0, 14), 400, 2000) * 0.3
    elif name == "ding":
        t = _t(2.2)
        x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((880, 1, 1.6), (1760, 0.4, 2.4), (2640, 0.2, 3.5)))
    elif name == "gasp":
        t = _t(0.5)
        x = _bp(_noise(0.5, 15), 900, 3500) * np.sin(np.pi * t / 0.5) ** 1.5 * 0.8
    elif name == "heartbeat":
        t = _t(1.6)
        x = np.zeros_like(t)
        for at, a in ((0.0, 1.0), (0.22, 0.7), (0.8, 1.0), (1.02, 0.7)):
            tt = _t(0.18)
            b = np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 25) * a
            i = int(at * RATE)
            x[i:i + len(b)] += b
    elif name == "pop":       # on-screen text appearing
        t = _t(0.12)
        f = 600 + 900 * t / 0.12
        x = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 30)
    elif name == "riser":     # before a big reveal
        t = _t(1.2)
        f = 200 + 1200 * (t / 1.2) ** 2
        x = (np.sin(2 * np.pi * np.cumsum(f) / RATE) * 0.4 + _bp(_noise(1.2, 16), 1500, 5000) * 0.5) * (t / 1.2) ** 2
    else:
        return np.zeros(1, np.float32)
    x = np.asarray(x, dtype=np.float64)
    peak = np.abs(x).max() or 1
    return (x / peak * 0.8).astype(np.float32)
