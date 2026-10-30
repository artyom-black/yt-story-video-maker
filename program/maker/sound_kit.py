"""Build the sound kit by measuring every candidate sound (nobody has to listen to hundreds of files).

For each candidate: length, loudness, where the main hit is, how sharp the attack is, how much low end
(a "boom"), how bright it is, and whether it is a tone (a ding) or noise (a whoosh). Each role has rules;
sounds that break them (too long, too quiet, wrong shape) are rejected, the rest are ranked, trimmed to
their hit with a short fade, and saved as WAV with a known loudness. kit.json records what was chosen
and why, so the same kit can be rebuilt on GitHub from the original files.

Usage:  python -m maker.sound_kit CANDIDATES_DIR KIT_DIR
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

import numpy as np

SR = 48000

# role: (folders to look in, max length after trim, rules)
ROLES = {
    "pop":     (["sfx_pop", "sfx_cartoon", "sfx_magic", "sfx_ding"], 0.45,
                dict(attack_max=0.04, bright_min=600, tonal=None)),
    "hit":     (["sfx_impact", "sfx_boom", "sfx_punch"], 1.4,
                dict(attack_max=0.04, low_min=0.30, tonal=None)),
    "whoosh":  (["sfx_whoosh", "sfx_transition"], 1.0,
                dict(peak_min=0.05, peak_max=1.0, tonal=None)),
    "sting":   (["sfx_record-scratch", "sfx_fail", "sfx_cartoon"], 1.3,
                dict(attack_max=0.08, tonal=None)),
    "ding":    (["sfx_ding", "sfx_bell", "sfx_magic"], 1.4,
                dict(attack_max=0.03, tonal=True, bright_min=900)),
}
AVOID = ("church", "door", "horn", "game", "small", "voice", "laugh", "meow", "fart", "kiss", "sneeze", "monster", "zombie", "scream", "child", "kids",
         "crowd", "applause", "loop", "ambience", "rain", "engine", "helicopter", "laser", "gun", "8-bit", "arcade",
         "game-over", "horror", "creepy", "evil", "alarm", "siren", "notification", "message", "phone", "doorbell")


def load(path: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def envelope(a, hop=480):
    n = len(a) // hop
    return np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)


def features(a: np.ndarray) -> dict:
    env = envelope(a)                                   # 10 ms steps
    if not len(env) or env.max() < 1e-4:
        return {"silent": True}
    db = 20 * np.log10(env / env.max())
    peak = int(np.argmax(env))
    on = int(np.argmax(db > -30))                       # where the sound really starts
    after = np.where(db[peak:] < -30)[0]
    tail = (after[0] if len(after) else len(db) - peak) / 100
    seg = a[on * 480:min(len(a), (peak + int(tail * 100)) * 480)]
    spec = np.abs(np.fft.rfft(seg[:SR * 2] * np.hanning(min(len(seg), SR * 2)))) if len(seg) > 256 else np.ones(10)
    freqs = np.fft.rfftfreq(min(len(seg), SR * 2), 1 / SR) if len(seg) > 256 else np.linspace(0, SR / 2, 10)
    power = spec ** 2
    total = power.sum() + 1e-12
    centroid = float((freqs * power).sum() / total)
    low = float(power[freqs < 200].sum() / total)
    flat = float(np.exp(np.mean(np.log(power + 1e-12))) / (np.mean(power) + 1e-12))   # 1 = noise, 0 = pure tone
    rms_db = float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)) if len(seg) else -99
    return {"silent": False, "start": on / 100, "peak": peak / 100, "attack": max(0.0, (peak - on) / 100),
            "tail": tail, "length": len(a) / SR, "centroid": centroid, "low": low, "flatness": flat,
            "rms_db": rms_db, "peak_db": float(20 * np.log10(np.abs(a).max() + 1e-9))}


NAME_HINTS = {   # the file name must also say it is this kind of sound (measurements alone pick odd things)
    "pop": ("pop", "click"),
    "hit": ("impact", "hit", "boom", "punch", "slam", "thud"),
    "whoosh": ("whoosh", "woosh", "swoosh", "sweep", "swish", "zoom"),
    "sting": ("scratch", "fail", "trombone", "disappoint"),
    "ding": ("ding", "bell", "sparkle", "chime", "reveal", "glitter", "achievement"),
}


def fits(role: str, f: dict, name: str) -> tuple[bool, str]:
    _, max_len, r = ROLES[role]
    if name.split("-")[0].isdigit():
        return False, "no name"
    if not any(h in name for h in NAME_HINTS[role]):
        return False, "name says another kind of sound"
    if f.get("silent") or f["rms_db"] < -45:
        return False, "almost silent"
    if any(w in name for w in AVOID):
        return False, "unsuitable kind (name)"
    if "attack_max" in r and f["attack"] > r["attack_max"]:
        return False, f"soft attack {f['attack']:.2f}s"
    if "low_min" in r and f["low"] < r["low_min"]:
        return False, f"no boom (low {f['low']:.2f})"
    if "bright_min" in r and f["centroid"] < r["bright_min"]:
        return False, f"dull ({f['centroid']:.0f} Hz)"
    if "peak_min" in r and not (r["peak_min"] <= f["attack"] <= r["peak_max"]):
        return False, f"whoosh peak at {f['attack']:.2f}s"
    if r.get("tonal") is True and f["flatness"] > 0.12:
        return False, f"not a tone (flatness {f['flatness']:.2f})"
    if r.get("tonal") is False and f["flatness"] < 0.02:
        return False, "too tonal for a whoosh"
    return True, "ok"


def score(role: str, f: dict) -> float:
    _, max_len, _ = ROLES[role]
    s = 0.0
    s -= abs(min(f["tail"], 4) - max_len * 0.6)          # natural length close to what the role needs
    s += 0.02 * (f["rms_db"] + 30)                      # prefer full, confident sounds
    if role == "hit":
        s += 3 * f["low"] + 0.03 * (f["rms_db"] + 20) + (0.5 if any(w in "cinematic epic movie big deep" for w in []) else 0)
    if role == "pop":
        s -= f["attack"] * 20
    if role == "sting":
        s -= 0.5 * f["tail"]                            # quick stings, not slow ones
    if role == "whoosh":
        s -= abs(f["attack"] - 0.45)                    # build-up of about half a second before the cut
    return s


def trim(a: np.ndarray, f: dict, role: str) -> np.ndarray:
    _, max_len, _ = ROLES[role]
    start = max(0, int((f["start"] - 0.01) * SR))
    if role == "whoosh":                                # centre the whoosh on its loudest moment
        start = max(0, int((f["peak"] - max_len / 2) * SR))
    end = min(len(a), start + int(max_len * SR))
    seg = a[start:end].copy()
    fade = min(len(seg), int(0.12 * SR))
    seg[-fade:] *= np.linspace(1, 0, fade) ** 2
    seg[:int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    # loudness: every kit sound at -20 dB RMS over its first 0.5 s, so gains in the mixer mean the same thing
    head = seg[:int(0.5 * SR)]
    gain = 10 ** ((-20 - 20 * np.log10(np.sqrt(np.mean(head ** 2)) + 1e-9)) / 20)
    seg = np.clip(seg * gain, -0.98, 0.98)
    return seg


def save_wav(path, a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    path], input=a.astype(np.float32).tobytes(), check=True)


VIDEO_MOODS = {   # our MUSIC tags -> Mixkit mood pages that describe them
    "tense": ["mysterious", "tension", "suspenseful", "ominous", "cautious"],
    "funny": ["humorous", "quirky", "silly", "mischievous", "playful"],
    "calm": ["pastoral", "peaceful", "calm", "playful"],
    "sad": ["melancholic", "sombre", "sad"],
    "epic": ["epic", "heroic", "triumphant"],
}
BAD_MUSIC = ("techno", "dance", "edm", "trap", "rap", "hip-hop", "dubstep", "rock", "metal", "party", "club", "house",
             "disco", "reggaeton", "funk", "sexy", "christmas", "xmas", "sci-fi", "cyber", "synthwave", "lofi", "lo-fi",
             "acid", "horror", "fright", "games", "corporate")


GOOD_GENRES = {   # genres that fit a history story; per mood
    "tense": ("film score", "atmospheres", "drone music", "orchestral hybrid", "orchestral", "cinematic", "classical"),
    "funny": ("comedy", "classical", "jazz", "acoustic", "folk", "contemporary folk", "world", "film score"),
    "calm": ("folk", "contemporary folk", "acoustic", "classical", "world", "film score", "piano", "ambient"),
    "sad": ("film score", "classical", "piano", "ambient", "atmospheres", "world"),
    "epic": ("film score", "orchestral hybrid", "orchestral", "march & military", "classical"),
}


def music_by_mood(cands_dir: str, analysed: list[dict]) -> dict:
    """For each video mood: tracks ranked by how many matching mood pages list them, keeping only genres
    that fit a history story (no pop, corporate, children's, hip hop, electronic...)."""
    ok = {m["key"]: m for m in analysed if m["ok"]}
    genre = {}
    src = os.path.join(cands_dir, "sources.json")
    if os.path.exists(src):
        for x in json.load(open(src)):
            if "file" in x:
                genre[os.path.basename(x["file"]).split("__")[-1]] = (x.get("genre") or "").lower()
    out = {}
    for mood, pages in VIDEO_MOODS.items():
        count, files = {}, {}
        for page in pages:
            for p in glob.glob(os.path.join(cands_dir, "mood_" + page, "*.mp3")):
                name, key = os.path.basename(p).split("__")[0], os.path.basename(p).split("__")[-1]
                if any(b in name for b in BAD_MUSIC) or key not in ok:
                    continue
                if genre.get(key) not in GOOD_GENRES[mood]:
                    continue
                count[key] = count.get(key, 0) + 1
                files[key] = (os.path.relpath(p, cands_dir), name)
        # most matching mood pages first, then the steadiest track (a calm bed under the voice)
        # best-fitting genre first (the order in GOOD_GENRES), then most matching mood pages, then the steadiest
        order = {g: i for i, g in enumerate(GOOD_GENRES[mood])}
        ranked = sorted(count, key=lambda k: (order.get(genre.get(k), 99), -count[k], ok[k]["loudness_spread"]))
        out[mood] = [{"file": files[k][0], "name": files[k][1], "genre": genre.get(k), "pages": count[k]}
                     for k in ranked[:5]]
    return out


def pick_music(cands_dir: str) -> list[dict]:
    """Music: keep tracks that start within 1 s, have no long silences and steady loudness."""
    out = []
    for p in sorted(glob.glob(os.path.join(cands_dir, "music_*", "*.mp3")) +
                    glob.glob(os.path.join(cands_dir, "mood_*", "*.mp3"))):
        a = load(p)
        env = envelope(a, 4800)                         # 100 ms steps
        if len(env) < 300:
            continue
        db = 20 * np.log10(env / env.max())
        first = int(np.argmax(db > -25)) / 10
        quiet = float((db[int(first * 10):] < -30).mean())
        spread = float(np.std(db[int(first * 10):int(first * 10) + 600]))
        name = os.path.basename(p)
        out.append({"file": os.path.relpath(p, cands_dir), "name": name, "key": name.split("__")[-1],
                    "starts_at": first, "quiet_share": quiet,
                    "loudness_spread": spread, "ok": first < 2.0 and quiet < 0.10 and spread < 6.5})
    return out


def build(cands_dir: str, kit_dir: str, per_role: int = 4):
    os.makedirs(kit_dir, exist_ok=True)
    report = {"roles": {}, "rejected": {}, "music": []}
    seen = set()
    for role, (folders, _, _) in ROLES.items():
        ranked = []
        for folder in folders:
            for p in sorted(glob.glob(os.path.join(cands_dir, folder, "*.mp3"))):
                name = os.path.basename(p).split("__")[0]
                key = os.path.basename(p).split("__")[-1]
                a = load(p)
                f = features(a)
                ok, why = fits(role, f, name)
                if not ok:
                    report["rejected"].setdefault(role, []).append(f"{name}: {why}")
                    continue
                ranked.append((score(role, f), p, name, key, f, a))
        ranked.sort(key=lambda r: -r[0])
        chosen = []
        for sc, p, name, key, f, a in ranked:
            if key in seen or len(chosen) >= per_role:
                continue
            seen.add(key)
            out = os.path.join(kit_dir, f"{role}_{len(chosen) + 1}.wav")
            seg = trim(a, f, role)
            save_wav(out, seg)
            t0 = max(0.0, f["peak"] - ROLES[role][1] / 2) if role == "whoosh" else max(0.0, f["start"] - 0.01)
            chosen.append({"kit_file": os.path.basename(out), "source": os.path.relpath(p, cands_dir), "name": name,
                           "trimmed_seconds": round(len(seg) / SR, 2), "hit_at": round(f["peak"] - t0, 3), "attack": f["attack"], "tail": f["tail"],
                           "low": round(f["low"], 2), "brightness_hz": round(f["centroid"]),
                           "noise_vs_tone": round(f["flatness"], 3), "score": round(sc, 2)})
        report["roles"][role] = chosen
    report["music"] = pick_music(cands_dir)
    report["music_by_mood"] = music_by_mood(cands_dir, report["music"])
    with open(os.path.join(kit_dir, "kit.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    for role, ch in report["roles"].items():
        print(role, [c["name"] for c in ch])
    for mood, tracks in report["music_by_mood"].items():
        print("music", mood, [(t["name"], t["genre"], t["pages"]) for t in tracks])


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
