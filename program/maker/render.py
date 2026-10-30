"""Turn a story file + recorded voice lines into the finished video.

Usage:
  python -m maker.render STORY.txt --voices work/voice/out --out out/
  python -m maker.render STORY.txt --preview-voices --scenes 1-6 --out out/   (local test with quick Kokoro voices)

What it does, per scene:
  background from PLACE, cast acting the MOOD, lip sync to each line, MrBeast-style cuts between
  wide and close shots, CAMERA move, big on-screen TEXT, whoosh on every cut, SFX, mood music.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import random
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

import numpy as np

from .backgrounds import FLOOR, H, W, build
from .characters import (MOOD_EXPRESSION, TIMING, blend_pose, character, idle_pose, is_blinking,
                         talk_pose)
from .sound import RATE, music, sfx
from .story import Scene, Story, load
from .voice import mouth_track, save_wav, tighten_pauses

FPS = 24
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Anton, 'Inter Display', 'DejaVu Sans', sans-serif"
LEAD, TAIL, GAP = 0.22, 0.35, 0.16      # seconds: before the first line, after the last, between lines

CAST_X = {1: [960], 2: [700, 1220], 3: [560, 960, 1360]}
CAST_SCALE = 0.95


# ---------------------------------------------------------------- timeline
@dataclass
class LineClip:
    speaker: str
    text: str
    start: float          # seconds from the start of the scene
    audio: np.ndarray
    mouth: list
    shot: str = "wide"

    @property
    def end(self):
        return self.start + len(self.audio) / RATE


@dataclass
class SceneClip:
    scene: Scene
    start: float          # seconds from the start of the video
    duration: float
    lines: list = field(default_factory=list)


def _load_wav(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def _trim(a, thresh=0.02):
    idx = np.where(np.abs(a) > thresh * (np.abs(a).max() or 1))[0]
    if not len(idx):
        return a
    return a[max(0, idx[0] - int(0.03 * RATE)):min(len(a), idx[-1] + int(0.06 * RATE))]


def preview_voice(speaker, text):
    """Fast stand-in voice for local previews (the real run uses Chatterbox)."""
    from .voice import speak
    v = json.load(open(os.path.join(os.path.dirname(HERE), "voices.json")))[speaker]
    import re
    return speak(re.sub(r"\[[a-z]+\]", "", text), v["kokoro_voice"], 1.0)


def build_timeline(st: Story, voices_dir: str | None, scene_filter=None):
    from .cast_voices import line_id
    clips, t = [], 0.0
    for s in st.scenes:
        if scene_filter and s.number not in scene_filter:
            continue
        cur = LEAD
        lines = []
        for i, ln in enumerate(s.lines):
            if voices_dir:
                a = _load_wav(os.path.join(voices_dir, line_id(s.number, i) + ".wav"))
            else:
                a = preview_voice(ln.speaker, ln.text)
            a = _trim(tighten_pauses(a))
            lines.append(LineClip(ln.speaker, ln.text, cur, a, mouth_track(a, FPS)))
            cur += len(a) / RATE + GAP
        dur = cur - GAP + TAIL
        choose_shots(s, lines)
        clips.append(SceneClip(s, t, dur, lines))
        t += dur
    return clips


def choose_shots(s: Scene, lines):
    """MrBeast-style editing: start wide, then cut between close-ups on whoever talks and wide shots."""
    for i, ln in enumerate(lines):
        dur = len(ln.audio) / RATE
        if len(s.cast) == 1:
            ln.shot = "close" if i % 2 else "medium"
        elif i == 0:
            ln.shot = "wide"
        elif dur < 1.1:
            ln.shot = lines[i - 1].shot
        elif s.mood in ("shock", "scary") and ("!" in ln.text or "[gasp]" in ln.text):
            ln.shot = "punch"
        else:
            ln.shot = "close" if i % 2 else "medium"


# ---------------------------------------------------------------- acting
REACT = {  # how listeners react to a mood
    "shock": {"KAI": "shock", "IRIS": "shock", "BOB": "shock"},
    "scary": {"KAI": "scared", "IRIS": "scared", "BOB": "scared"},
    "funny": {"KAI": "happy", "IRIS": "smirk", "BOB": "happy"},
    "tense": {"KAI": "serious", "IRIS": "serious", "BOB": "default"},
    "sad": {"KAI": "sad", "IRIS": "sad", "BOB": "sad"},
    "curious": {"KAI": "curious", "IRIS": "default", "BOB": "curious"},
    "epic": {"KAI": "happy", "IRIS": "smirk", "BOB": "default"},
    "calm": {"KAI": "default", "IRIS": "default", "BOB": "default"},
}


def speaker_expression(name, text, mood):
    t = text.lower()
    if "[laugh]" in t or "[chuckle]" in t:
        return "happy"
    if "[gasp]" in t:
        return "shock"
    if "[sigh]" in t:
        return "sad" if mood == "sad" else "annoyed"
    if mood in ("funny", "epic") and name == "IRIS":
        return "smirk"
    return MOOD_EXPRESSION.get(mood, "default")


def listener_expression(name, mood, speaker, t_in_line):
    ex = REACT.get(mood, {}).get(name, "default")
    if mood == "funny" and speaker == "BOB" and name == "IRIS":
        ex = "annoyed"
    if t_in_line < TIMING[name]["delay"] + 0.15:     # slow characters react a moment late
        return "default"
    return ex


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def cast_svg(sc: SceneClip, t: float, xs):
    """All cast members at time t (seconds into the scene)."""
    s = sc.scene
    current = None
    for ln in sc.lines:
        if ln.start - 0.05 <= t < ln.end + GAP:
            current = ln
            break
    out = []
    for name, x in zip(s.cast, xs):
        tm = TIMING[name]
        g = sc.start + t                      # global time keeps breathing/blinking continuous
        blink = is_blinking(g, name)
        if current and current.speaker == name and t < current.end:
            lt = t - current.start
            fi = int(lt * FPS)
            level = current.mouth[fi] if 0 <= fi < len(current.mouth) else 0.0
            k = _ease(lt / tm["move"])
            pose = blend_pose(idle_pose(g, name), talk_pose(g, name), k)
            low = current.text.lower()
            if ("[gasp]" in low or (s.mood == "shock" and "!" in low)) and lt < 0.9:
                pose = blend_pose(pose, "shock", _ease(1 - abs(lt - 0.35) / 0.55), name)
            elif "[sigh]" in low and lt < 1.2:
                pose = blend_pose(pose, "shrug", _ease(1 - abs(lt - 0.5) / 0.7), name)
            out.append(character(name, x, FLOOR, CAST_SCALE, pose, speaker_expression(name, current.text, s.mood),
                                 talking=level, blink=blink and level < 0.15))
        else:
            spk = current.speaker if current else None
            lt = (t - current.start) if current else t
            ex = listener_expression(name, s.mood, spk, lt)
            pose = idle_pose(g, name)
            if s.beat in ("twist", "peak") or s.mood == "shock":
                r = t - LEAD - tm["delay"]
                if 0 < r < 1.3:
                    pose = blend_pose(pose, "shock" if s.mood != "scary" else "scared",
                                      _ease(min(r / tm["move"], (1.3 - r) / 0.4)), name)
            out.append(character(name, x, FLOOR, CAST_SCALE, pose, ex, blink=blink))
    return "".join(out)


# ---------------------------------------------------------------- camera
SHOTS = {"wide": 1.0, "medium": 1.22, "close": 1.6, "punch": 1.9}


def camera(sc: SceneClip, t: float, xs):
    s = sc.scene
    current = next((ln for ln in sc.lines if ln.start - 0.05 <= t < ln.end + GAP), None)
    shot = current.shot if current else (sc.lines[0].shot if sc.lines else "wide")
    z = SHOTS[shot]
    if shot in ("close", "punch") and current and current.speaker in s.cast:
        fx = xs[s.cast.index(current.speaker)]
        fy = FLOOR - 470 * CAST_SCALE if shot == "close" else FLOOR - 530 * CAST_SCALE
    elif shot == "medium" and current and current.speaker in s.cast:
        fx = 0.6 * xs[s.cast.index(current.speaker)] + 0.4 * 960
        fy = 600
    else:
        fx, fy = 960, 540
    p = t / max(sc.duration, 0.1)
    move = s.camera
    if move == "zoom-in":
        z *= 1 + 0.1 * _ease(p)
    elif move == "zoom-out":
        z *= 1.1 - 0.1 * _ease(p)
    elif move == "slow-push":
        z *= 1 + 0.06 * p
    elif move == "pan-left":
        z *= 1.08
        fx += 70 - 140 * _ease(p)
    elif move == "pan-right":
        z *= 1.08
        fx += -70 + 140 * _ease(p)
    if current:      # gentle drift during a line keeps shots alive
        z *= 1 + 0.025 * _ease((t - current.start) / max(current.end - current.start, 0.3))
    dx = dy = 0.0
    if move == "shake" or shot == "punch":
        amp = 14 * max(0.0, 1 - t / 1.2) + 3
        rnd = random.Random(int(t * FPS) + s.number * 1000)
        dx, dy = rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)
    hw, hh = W / (2 * z), H / (2 * z)
    fx = min(max(fx, hw), W - hw)
    fy = min(max(fy, hh), H - hh)
    tx, ty = W / 2 - z * fx + dx, H / 2 - z * fy + dy
    return f"translate({tx:.1f} {ty:.1f}) scale({z:.4f})"


# ---------------------------------------------------------------- on-screen text
def big_text(text, t):
    """MrBeast-style big number: pops in, holds, then sits small in the corner."""
    if not text:
        return ""
    esc = text.replace("&", "&amp;").replace("<", "&lt;")
    if t < 2.3:
        k = min(1.0, t / 0.18)
        s = 0.5 + 0.7 * k - 0.2 * max(0.0, min(1.0, (t - 0.18) / 0.12))
        fade = 1.0 if t < 2.0 else max(0.0, (2.3 - t) / 0.3)
        size = 170 if len(text) <= 10 else 120
        return (f'<g transform="translate(960 230) rotate(-3) scale({s:.3f})" opacity="{fade:.2f}">'
                f'<text x="8" y="10" text-anchor="middle" font-family="{FONT}" font-weight="900" font-size="{size}" '
                f'fill="#000" opacity=".35">{esc}</text>'
                f'<text x="0" y="0" text-anchor="middle" font-family="{FONT}" font-weight="900" font-size="{size}" '
                f'fill="#ffd23f" stroke="#111" stroke-width="16" paint-order="stroke" stroke-linejoin="round">{esc}</text></g>')
    k = min(1.0, (t - 2.3) / 0.2)
    return (f'<g opacity="{k:.2f}"><text x="60" y="110" font-family="{FONT}" font-weight="900" font-size="72" '
            f'fill="#ffd23f" stroke="#111" stroke-width="10" paint-order="stroke" stroke-linejoin="round">{esc}</text></g>')


# ---------------------------------------------------------------- frames
def scene_frames(sc: SceneClip, frame_dir: str, persistent_text: str):
    s = sc.scene
    xs = CAST_X[min(3, max(1, len(s.cast)))][:len(s.cast)]
    back, front, overlay = build(s.place, s.extras, s.number, xs)
    n = int(round(sc.duration * FPS))
    for f in range(n):
        t = f / FPS
        text = big_text(s.text, t) if s.text else (big_text(persistent_text, 3.0) if persistent_text else "")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
               f'<g transform="{camera(sc, t, xs)}">{back}{cast_svg(sc, t, xs)}{front}</g>{overlay}{text}</svg>')
        with open(os.path.join(frame_dir, f"f{f:05d}.svg"), "w") as fh:
            fh.write(svg)
    return n


def _render_scene(args):
    sc, out_mp4, persistent_text, tmp_root = args
    d = tempfile.mkdtemp(prefix=f"scene{sc.scene.number:03d}_", dir=tmp_root)
    try:
        scene_frames(sc, d, persistent_text)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(d, "f%05d.svg"),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-r", str(FPS), out_mp4], check=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return sc.scene.number


# ---------------------------------------------------------------- audio
def mix_audio(clips, total):
    n = int(total * RATE) + RATE
    voice = np.zeros(n, np.float32)
    effects = np.zeros(n, np.float32)
    for ci, sc in enumerate(clips):
        base = int(sc.start * RATE)
        for ln in sc.lines:
            i = base + int(ln.start * RATE)
            voice[i:i + len(ln.audio)] += ln.audio[:max(0, n - i)]
        if ci > 0:                                   # whoosh on every cut
            w = sfx("whoosh") * 0.22
            j = max(0, base - int(0.18 * RATE))
            effects[j:j + len(w)] += w[:max(0, n - j)]
        for k, name in enumerate(sc.scene.sfx):
            x = sfx(name) * (0.35 if name in ("crowd", "wind", "fire", "water") else 0.45)
            j = base + int((0.05 + 0.35 * k) * RATE)
            effects[j:j + len(x)] += x[:max(0, n - j)]
        if sc.scene.text:
            x = sfx("pop") * 0.4
            effects[base:base + len(x)] += x[:max(0, n - base)]
        if ci + 1 < len(clips) and clips[ci + 1].scene.beat == "peak":   # build-up before the biggest moment
            x = sfx("riser") * 0.3
            j = int((sc.start + sc.duration) * RATE) - len(x)
            if j > 0:
                effects[j:j + len(x)] += x
    # music: one track per MUSIC style, crossfaded at changes, ducked under speech
    mus = np.zeros(n, np.float32)
    style, seg_start = None, 0
    segments = []
    for sc in clips:
        if sc.scene.music != style:
            if style is not None:
                segments.append((style, seg_start, int(sc.start * RATE)))
            style, seg_start = sc.scene.music, int(sc.start * RATE)
    segments.append((style, seg_start, n))
    fade = int(0.8 * RATE)
    for st, a, b in segments:
        if st in (None, "none"):
            continue
        a0 = max(0, a - fade // 2)
        b0 = min(n, b + fade // 2)
        m = music(st, (b0 - a0) / RATE + 0.1)[:b0 - a0].copy()
        ramp = np.linspace(0, 1, min(fade, len(m)), dtype=np.float32)
        m[:len(ramp)] *= ramp
        m[len(m) - len(ramp):] *= ramp[::-1]
        mus[a0:a0 + len(m)] += m
    env = np.abs(voice)
    k = int(0.25 * RATE)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = voice * 1.0 + effects + mus * 0.16 * duck
    peak = float(np.abs(mix).max()) or 1
    return (mix / peak * 0.95).astype(np.float32)


# ---------------------------------------------------------------- main
def render(story_path, voices_dir, out_dir, scene_filter=None, workers=None):
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors:\n  " + "\n  ".join(st.errors))
    os.makedirs(out_dir, exist_ok=True)
    clips = build_timeline(st, voices_dir, scene_filter)
    total = sum(c.duration for c in clips)
    print(f"{len(clips)} scenes, {total / 60:.1f} minutes", flush=True)
    tmp_root = tempfile.mkdtemp(prefix="render_", dir=os.environ.get("RENDER_TMP"))
    # the latest on-screen TEXT stays small in the corner (e.g. the current price level)
    jobs, last_text = [], ""
    for sc in clips:
        jobs.append((sc, os.path.join(tmp_root, f"scene_{sc.scene.number:03d}.mp4"), last_text, tmp_root))
        if sc.scene.text and st.format in ("price-ladder", "survival", "every-level", "ranked"):
            last_text = sc.scene.text if (sc.scene.text.startswith("$") or sc.scene.text.upper().startswith(("DAY", "#", "NO."))) else last_text
    workers = workers or max(1, (os.cpu_count() or 2))
    with mp.Pool(workers) as pool:
        for i, num in enumerate(pool.imap_unordered(_render_scene, jobs), 1):
            print(f"  scene {num} done ({i}/{len(jobs)})", flush=True)
    listing = os.path.join(tmp_root, "list.txt")
    with open(listing, "w") as f:
        for _, mp4, _, _ in jobs:
            f.write(f"file '{mp4}'\n")
    video_only = os.path.join(tmp_root, "video.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", video_only],
                   check=True)
    wav = os.path.join(tmp_root, "audio.wav")
    save_wav(wav, mix_audio(clips, total))
    out_mp4 = os.path.join(out_dir, "video.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video_only, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", out_mp4], check=True)
    shutil.rmtree(tmp_root, ignore_errors=True)
    print("wrote", out_mp4, flush=True)
    return out_mp4


def _parse_scenes(spec):
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--voices", help="folder with line_SSS_LL.wav files from the voice recording step")
    ap.add_argument("--preview-voices", action="store_true", help="local test: quick Kokoro voices instead")
    ap.add_argument("--scenes", help="only these scenes, e.g. 1-6 or 1,12,24")
    ap.add_argument("--out", default="out")
    ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if not a.voices and not a.preview_voices:
        sys.exit("give --voices DIR, or --preview-voices for a quick local test")
    render(a.story, a.voices, a.out, _parse_scenes(a.scenes), a.workers)
