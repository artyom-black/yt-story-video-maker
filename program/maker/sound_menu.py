"""The sound menu: for every kind of moment, the 3 best professional sounds from the Sonniss library, played
over a picture in one short video, so a human picks the channel's signature sounds by ear.

The picks go into program/sound_choices.json ({"cut": "path/in/bundle.wav", ...}); sfx_pack.py then always uses
exactly those sounds. Until a role is picked, the editor uses the menu's option 1.

    python -m maker.sound_menu SONNISS_RAW_DIR OUT_DIR [PICTURE.png]
writes OUT_DIR/menu.json and OUT_DIR/sound_menu.mp4
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import numpy as np

from .sfx_pack import SR, cut, env, load

# role: (what it's for, words the file path must contain, words it must not, length range s, shape)
ROLES = {
    "cut":     ("every new picture", r"whoosh|swoosh|swish|whip|swipe", r"long|slow|loop|amb|wind|fire|metal|magic",
                (0.2, 0.9), "whoosh"),
    "swoosh":  ("a new part of the video", r"transition|whoosh|swoosh|sweep", r"loop|amb|wind|fire|magic",
                (0.6, 1.8), "whoosh"),
    "pop":     ("words popping on screen", r"pop|click|blip|ui|interface|tick", r"loop|amb|long|gun|glitch",
                (0.03, 0.35), "sharp"),
    "boom":    ("big reveals (with flash)", r"impact|boom|braam|sub ?drop|hit|trailer", r"loop|amb|gun|punch|body|wood|glass",
                (0.8, 3.5), "boom"),
    "riser":   ("the build-up before a reveal", r"riser|rise|uplifter|build|reverse|swell", r"loop|amb",
                (0.8, 3.0), "riser"),
    "scratch": ("jokes (record scratch)", r"scratch|record|vinyl|stop", r"loop|amb|paper|metal",
                (0.2, 1.5), "sharp"),
    "money":   ("$1,000,000 and money", r"coin|cash|money|register|ching|jackpot|treasure", r"loop|amb",
                (0.2, 2.5), "sharp"),
    "poor":    ("$1 and bad luck", r"fail|wrong|lose|lost|error|buzzer|sad|negative|denied", r"loop|amb",
                (0.3, 2.5), "sharp"),
    "ding":    ("numbers and facts", r"bell|ding|chime|correct|success|positive", r"loop|amb|church|door",
                (0.2, 2.0), "sharp"),
    "flash":   ("camera flash on freeze moments", r"shutter|camera|flash|photo", r"loop|amb",
                (0.05, 1.0), "sharp"),
}


def features(a):
    e, hop = env(a)
    if not len(e) or e.max() <= 0:
        return None
    on = np.where(e > 0.1 * e.max())[0]
    dur = (on[-1] - on[0] + 1) * hop / SR if len(on) else 0
    peak_at = int(np.argmax(e)) * hop / SR
    attack = (int(np.argmax(e)) - (on[0] if len(on) else 0)) * hop / SR
    spec = np.abs(np.fft.rfft(a[: min(len(a), SR * 3)]))
    freqs = np.fft.rfftfreq(min(len(a), SR * 3), 1 / SR)
    low = float(spec[freqs < 150].sum() / max(1e-9, spec.sum()))
    centroid = float((spec * freqs).sum() / max(1e-9, spec.sum()))
    third = max(1, len(e) // 3)
    rising = float(e[-third:].mean() / max(1e-9, e[:third].mean()))
    return dict(dur=dur, peak_at=peak_at, attack=attack, low=low, centroid=centroid, rising=rising,
                loud=float(20 * np.log10(e.max() + 1e-9)))


def score(shape, f):
    if shape == "whoosh":             # loudest in the middle, airy, not a bang
        mid = 1 - abs(f["peak_at"] / max(0.01, f["dur"]) - 0.55)
        return mid * 2 + min(f["centroid"], 4000) / 4000 - f["low"] * 2
    if shape == "sharp":              # instant attack, clean
        return 2 - f["attack"] * 20 + min(f["centroid"], 5000) / 5000
    if shape == "boom":               # instant attack, lots of low end
        return f["low"] * 6 - f["attack"] * 10 + 1
    if shape == "riser":              # gets louder towards the end
        return min(f["rising"], 20) / 4 - f["low"]
    return 0


def pick(raw_dir, per_role=3):
    files = []
    for root, _d, fs in os.walk(raw_dir):
        for f in fs:
            if f.lower().endswith((".wav", ".flac", ".aif", ".aiff", ".mp3", ".ogg")):
                files.append(os.path.join(root, f))
    out = {}
    for role, (_what, want, avoid, (lo, hi), shape) in ROLES.items():
        cands = [p for p in files if re.search(want, os.path.relpath(p, raw_dir), re.I)
                 and not re.search(avoid, os.path.relpath(p, raw_dir), re.I)]
        scored = []
        for p in cands[:400]:
            try:
                a = load(p)[: SR * 6]
            except Exception:
                continue
            f = features(a)
            if not f or not (lo <= f["dur"] <= hi) or f["loud"] < -40:
                continue
            scored.append((score(shape, f), p, f))
        scored.sort(key=lambda x: -x[0])
        chosen, vendors = [], set()
        for s, p, f in scored:                   # different studios, so the 3 options really differ
            vendor = os.path.relpath(p, raw_dir).split(os.sep)[0]
            if vendor in vendors and len(scored) > per_role * 2:
                continue
            chosen.append({"path": os.path.relpath(p, raw_dir), "score": round(s, 2), **{k: round(v, 3) for k, v in f.items()}})
            vendors.add(vendor)
            if len(chosen) >= per_role:
                break
        out[role] = chosen
        print(f"{role:8s} {len(cands):4d} candidates -> {[c['path'][-60:] for c in chosen]}")
    return out


def render_menu(raw_dir, menu, out_mp4, picture=None):
    """One card per option: title, what it's for, then the sound twice."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1280, 720
    try:
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        small = ImageFont.truetype("DejaVuSans.ttf", 34)
    except Exception:
        big = small = ImageFont.load_default()
    work = out_mp4 + ".parts"
    os.makedirs(work, exist_ok=True)
    parts = []
    bg = Image.open(picture).convert("RGB").resize((W, H)) if picture and os.path.exists(picture) else None
    for role, opts in menu.items():
        for i, o in enumerate(opts):
            im = bg.copy() if bg else Image.new("RGB", (W, H), (25, 25, 25))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 150))
            im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
            d = ImageDraw.Draw(im)
            title = f"{role.upper()}  -  option {i + 1}"
            d.text(((W - d.textlength(title, font=big)) / 2, 270), title, font=big, fill=(255, 215, 0))
            what = ROLES[role][0]
            d.text(((W - d.textlength(what, font=small)) / 2, 370), what, font=small, fill=(255, 255, 255))
            png = os.path.join(work, f"{role}_{i}.png")
            im.save(png)
            a, hit_at = cut(load(os.path.join(raw_dir, o["path"])), 3.0, "end" if role == "riser" else "onset")
            rms = float(np.sqrt((a ** 2).mean() + 1e-12))
            a = a * (10 ** (-18 / 20) / rms)
            a = a / max(1.0, float(np.abs(a).max()) / 0.98)
            gap = np.zeros(int(0.5 * SR), np.float32)
            track = np.concatenate([np.zeros(int(0.4 * SR), np.float32), a, gap, a, gap]).astype(np.float32)
            wav = os.path.join(work, f"{role}_{i}.wav")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                            wav], input=track.tobytes(), check=True)
            mp4 = os.path.join(work, f"{role}_{i}.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", png, "-i", wav, "-c:v", "libx264",
                            "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "48000",
                            "-ac", "2", "-shortest", mp4], check=True)
            parts.append(mp4)
    with open(os.path.join(work, "list.txt"), "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(work, "list.txt"), "-c", "copy", out_mp4], check=True)


if __name__ == "__main__":
    raw, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    menu = pick(raw)
    json.dump(menu, open(os.path.join(out, "menu.json"), "w"), indent=1)
    render_menu(raw, menu, os.path.join(out, "sound_menu.mp4"), sys.argv[3] if len(sys.argv) > 3 else None)
    print("wrote", os.path.join(out, "sound_menu.mp4"))
