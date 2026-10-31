"""The MrBeast sound pack: one fixed sound for every kind of moment, the same in every video.

MrBeast-style edits have a sound on almost everything, but never a random one: every cut gets a short
whoosh, every word on screen a pop, every big reveal a riser that sucks in and a boom, money a sparkle, being
poor a sad "wah", jokes a record scratch. Viewers learn the language of the sounds, so the same moment must
always sound the same.

Each role lists the exact files (by Mixkit id) in order of preference; the first one that exists in the
candidates folder is used. Every sound is measured, trimmed to its useful part, given the same loudness and
saved with "hit_at" (the moment that must land on the word; for a riser it's the end).

Usage:  python -m maker.sfx_pack CANDIDATES_DIR PACK_DIR
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

import numpy as np

SR = 48000

# role: (candidate files by name and id, max seconds, how to find the hit, loudness dB RMS)
PACK = {
    "cut":     ([("sfx_whoosh", "fast-whoosh-transition__1486"), ("sfx_whoosh", "cinematic-whoosh-fast-transition__1491"),
                 ("sfx_transition", "short-transition-sweep__3115"), ("sfx_whoosh", "air-woosh__1492"),
                 ("sfx_transition", "fast-small-sweep-transition__1714")], 0.7, "peak", -22, 3),
    "swoosh":  ([("sfx_transition", "cinematic-whoosh-fast-transition__166"), ("sfx_transition", "fast-transitions-swoosh__2638"),
                 ("sfx_whoosh", "movie-whoosh-impact-presentation__1493")], 1.2, "peak", -19, 1),
    "pop":     ([("sfx_pop", "hard-pop-click__3005"), ("sfx_pop", "dry-pop-up-notification-alert__2925"),
                 ("sfx_pop", "bubble-pop-up-alert-notification__2356")], 0.35, "onset", -19, 1),
    "boom":    ([("sfx_impact", "big-cinematic-impact__2908"), ("sfx_impact", "epic-movie-impact__773"),
                 ("sfx_impact", "movie-trailer-epic-impact__2198"), ("sfx_impact", "deep-heartbeat-impact__2182")],
                2.2, "onset", -15, 1),
    "riser":   ([("sfx_impact", "reverse-cinematic-impact-trailer__2900"), ("sfx_suspense", "cinematic-suspense-swell__686"),
                 ("sfx_suspense", "trailer-cinematic-suspense-swell__1046")], 1.4, "end", -21, 1),
    "scratch": ([("sfx_record-scratch", "vinyl-stop-fast-scratch__711"), ("sfx_record-scratch", "dj-record-swipe__710"),
                 ("sfx_record-scratch", "vinyl-record-small-scratch__709")], 0.9, "onset", -18, 1),
    "money":   ([("sfx_magic", "magic-glitter-shot__867"), ("sfx_bell", "achievement-bell__110"),
                 ("sfx_magic", "fantasy-game-success-notification__2633")], 1.4, "onset", -19, 1),
    "poor":    ([("sfx_cartoon", "trombone-disappoint__2894"), ("sfx_fail", "funny-fail-low-tone__472"),
                 ("sfx_fail", "slow-sad-trombone-fail__2964")], 1.8, "onset", -19, 1),
    "ding":    ([("sfx_bell", "service-bell__1569"), ("sfx_ding", "christmas-magic-bell-hit__235"),
                 ("sfx_bell", "cooking-bell-ding__621")], 1.0, "onset", -21, 1),
    "splat":   ([("sfx_cartoon", "funny-cartoon-fast-splat__391"), ("sfx_cartoon", "game-blood-pop-slide__2193")],
                0.8, "onset", -19, 1),
    "boing":   ([("sfx_cartoon", "boing-hit-sound__92"), ("sfx_cartoon", "soft-quick-punch__2885")], 0.7, "onset", -21, 1),
    "gasp":    ([("sfx_gasp", "cartoon-surprise-gasp__968"), ("sfx_gasp", "male-astonished-gasp__967")], 1.0, "onset", -20, 1),
}


def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def env(a, hop=240):
    n = len(a) // hop
    return np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12), hop


def cut(a, max_s, hit):
    e, hop = env(a)
    if not len(e):
        return a, 0.0
    on = np.where(e > 0.08 * e.max())[0]
    start = max(0, on[0] - 2) * hop if len(on) else 0
    if hit == "end":                       # a riser: keep the last max_s seconds up to its loudest point
        peak = int(np.argmax(e)) * hop
        a = a[max(0, peak - int(max_s * SR)):peak + int(0.03 * SR)]
        hit_at = len(a) / SR - 0.03
    else:
        a = a[start:start + int(max_s * SR)]
        e2, _ = env(a)
        hit_at = (int(np.argmax(e2)) * hop / SR) if hit == "peak" else 0.01
    f = min(len(a) // 3, int(0.12 * SR))   # short fade out, tiny fade in
    if f > 0:
        a[-f:] *= np.linspace(1, 0, f)
    g = min(len(a) // 10, int(0.004 * SR))
    if g > 0:
        a[:g] *= np.linspace(0, 1, g)
    return a, hit_at


def save(path, a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=a.astype(np.float32).tobytes(), check=True)


def build(cands, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pack = {}
    for role, (wanted, max_s, hit, loud, n_variants) in PACK.items():
        pack[role] = []
        for folder, stem in wanted:
            hits = glob.glob(os.path.join(cands, folder, stem + ".*")) or glob.glob(os.path.join(cands, "*", stem + ".*"))
            if not hits:
                continue
            a, hit_at = cut(load(hits[0]), max_s, hit)
            rms = float(np.sqrt((a ** 2).mean() + 1e-12))
            a = a * (10 ** (loud / 20) / rms)
            a = a / max(1.0, float(np.abs(a).max()) / 0.98)
            out = os.path.join(out_dir, f"{role}_{len(pack[role]) + 1}.wav")
            save(out, a)
            pack[role].append({"file": os.path.basename(out), "source": os.path.basename(hits[0]),
                               "hit_at": round(hit_at, 3), "length": round(len(a) / SR, 3)})
            if len(pack[role]) >= n_variants:
                break
        print(f"{role:8s} {[p['source'] for p in pack[role]]}")
    json.dump(pack, open(os.path.join(out_dir, "pack.json"), "w"), indent=1)
    return pack


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
