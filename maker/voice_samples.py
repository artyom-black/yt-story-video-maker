"""Voice audition videos: each character says the same 3 lines with several candidate voices.

Usage:  python -m maker.voice_samples out_dir
Makes one MP4 per character (KAI, IRIS, BOB, NARRATOR), with the face lip-syncing to the voice.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

from .characters import character, idle_pose, is_blinking
from .voice import RATE, mouth_track, save_wav, speak

FPS = 24
W, H = 1920, 1080

LINES = {
    "KAI": [("calm", "default", "Wait... so people back then just drank beer for breakfast?"),
            ("shock", "shock", "Hold on. They used WHAT as toilet paper?!"),
            ("funny", "happy", "Okay, okay, I take it back. Modern life is amazing.")],
    "IRIS": [("calm", "default", "Actually, the water was so dirty that weak beer was the safer choice."),
             ("shock", "shock", "Oh no. Kai. That is not a sponge."),
             ("funny", "smirk", "Congratulations, Bob. You just invented the first toilet tax.")],
    "BOB": [("calm", "default", "Cool. So we're stuck here. Great. Love that for us."),
            ("shock", "shock", "Nope. Absolutely not. I'm going home."),
            ("funny", "happy", "A medieval dentist? So, a guy with pliers and confidence.")],
    "NARRATOR": [("calm", None, "In the year thirteen forty seven, a ship arrived in Sicily."),
                 ("shock", None, "Nobody on board was alive."),
                 ("epic", None, "And what it carried would kill half of Europe.")],
}

CANDIDATES = {
    "KAI": ["am_puck", "am_liam", "am_echo", "am_adam"],
    "IRIS": ["af_heart", "af_bella", "bf_emma", "af_nicole"],
    "BOB": ["am_onyx", "am_fenrir", "am_eric", "bm_lewis"],
    "NARRATOR": ["bm_george", "am_michael", "bm_fable", "bm_daniel"],
}
SPEED = {"calm": 1.0, "shock": 1.12, "funny": 1.04, "epic": 0.94}
LABEL = "ABCD"


def _text(x, y, s, size, colour="#26262b", bold=False):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="DejaVu Sans, Arial" font-size="{size}" '
            f'fill="{colour}"{" font-weight=\"bold\"" if bold else ""}>{s}</text>')


def frame_svg(who, option, voice, mood, line, t, level, expr):
    out = [f'<rect width="{W}" height="{H}" fill="#e9e2d6"/>']
    if who == "NARRATOR":
        # narrator is never on screen: show a simple sound-wave so you can see the rhythm
        bars = "".join(f'<rect x="{760 + i * 28}" y="{540 - 10 - 160 * level * (0.4 + 0.6 * abs(np.sin(i * 1.7 + t * 9)))}" '
                       f'width="16" height="{20 + 320 * level * (0.4 + 0.6 * abs(np.sin(i * 1.7 + t * 9)))}" rx="8" '
                       f'fill="#26262b" opacity=".8"/>' for i in range(15))
        out.append(bars)
    else:
        out.append(character(who, W / 2, 1560, 2.0, idle_pose(t, who), expr, talking=level,
                             blink=is_blinking(t, who) and level < 0.15))
    out.append(f'<rect x="560" y="30" width="800" height="110" rx="18" fill="#26262b" opacity=".88"/>')
    out.append(_text(W / 2, 82, f"{who}  option {option}", 44, "#fff", True))
    out.append(_text(W / 2, 122, f"voice: {voice}   |   mood: {mood}", 26, "#d8d2c8"))
    out.append(f'<rect x="160" y="900" width="1600" height="120" rx="18" fill="#fff" opacity=".9"/>')
    out.append(_text(W / 2, 975, f'"{line}"', 34))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(out)}</svg>'


def make(who, out_dir):
    tmp = tempfile.mkdtemp(prefix=f"vs_{who}_")
    audio_parts, frames = [], 0
    for oi, voice in enumerate(CANDIDATES[who]):
        for mood, expr, line in LINES[who]:
            a = speak(line, voice, SPEED[mood])
            gap = np.zeros(int(RATE * 0.6), dtype=np.float32)
            clip = np.concatenate([np.zeros(int(RATE * 0.3), dtype=np.float32), a, gap])
            track = mouth_track(clip, FPS)
            for i, lv in enumerate(track):
                t = frames / FPS
                with open(f"{tmp}/f{frames:05d}.svg", "w") as fh:
                    fh.write(frame_svg(who, LABEL[oi], voice, mood, line, t, lv, expr or "default"))
                frames += 1
            # pad audio so it matches the frames exactly
            clip = np.concatenate([clip, np.zeros(max(0, int(len(track) * RATE / FPS) - len(clip)), np.float32)])
            audio_parts.append(clip[:int(len(track) * RATE / FPS)])
    wav = f"{tmp}/voice.wav"
    save_wav(wav, np.concatenate(audio_parts))
    out = os.path.join(out_dir, f"voices_{who.lower()}.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%05d.svg",
                    "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", out], check=True)
    shutil.rmtree(tmp)
    print("wrote", out, f"{frames / FPS:.0f}s")


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)
    for who in (sys.argv[2:] or CANDIDATES):
        make(who, out_dir)


# ---------------------------------------------------------------- auditions from recorded files
def load_audio(path: str) -> np.ndarray:
    """Decode any audio file to mono float32 at 24 kHz using ffmpeg."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def make_from_lab(who: str, lab_dir: str, out_dir: str, engine: str = "Chatterbox-Turbo"):
    """Audition video from voice-lab recordings (jobs.json + mp3 files)."""
    import json
    jobs = [j for j in json.load(open(os.path.join(lab_dir, "jobs.json"))) if j["who"] == who]
    expr = {"calm": "default", "shock": "shock", "funny": "happy", "epic": "default"}
    if who == "IRIS":
        expr["funny"] = "smirk"
    tmp = tempfile.mkdtemp(prefix=f"lab_{who}_")
    audio_parts, frames = [], 0
    for job in jobs:
        a = load_audio(os.path.join(lab_dir, job["out"].replace(".wav", ".mp3")))
        clip = np.concatenate([np.zeros(int(RATE * 0.3), np.float32), a, np.zeros(int(RATE * 0.7), np.float32)])
        track = mouth_track(clip, FPS)
        shown = job["text"].replace("[", "(").replace("]", ")")
        for lv in track:
            t = frames / FPS
            with open(f"{tmp}/f{frames:05d}.svg", "w") as fh:
                fh.write(frame_svg(who, job["option"], f'{job["voice"]} + {engine}', job["mood"], shown, t, lv,
                                   expr[job["mood"]]))
            frames += 1
        n = int(len(track) * RATE / FPS)
        audio_parts.append(np.concatenate([clip, np.zeros(max(0, n - len(clip)), np.float32)])[:n])
    wav = f"{tmp}/voice.wav"
    save_wav(wav, np.concatenate(audio_parts))
    out = os.path.join(out_dir, f"voices2_{who.lower()}.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%05d.svg",
                    "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    shutil.rmtree(tmp)
    print("wrote", out, f"{frames / FPS:.0f}s")
