"""The Kai demo: about 20 seconds in MrBeast style, to judge the approach.

Usage:  python -m maker.demo_kai SPRITES ART VOICES SOUNDS BACKGROUND RHUBARB out.mp4
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

from .editor import Rig, Shot, mix_audio, mouth_images, render, rhubarb, scene_light, text_layer, wav_seconds
from .motion import FLOOR_Y, STAGE_H, STAGE_W, Camera, OUT_W, OUT_H

LINES = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "demo", "kai_demo_lines.json")))


def spoken(text):
    return re.sub(r"\[[^\]]+\]", "", text).strip()


_VOICED = {}


def voiced_times(wav):
    """Times (seconds) of every 10 ms step where the voice is actually sounding."""
    if wav not in _VOICED:
        import wave
        import numpy as np
        with wave.open(wav) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
            rate = w.getframerate()
        hop = rate // 100
        env = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
        _VOICED[wav] = np.where(env > 0.08 * env.max())[0] / 100.0
    return _VOICED[wav]


def word_time(line_start, line, word):
    """When a word is said: its position in the text, spread over the voiced parts of the recording only
    (so pauses and gasps don't push the timing off)."""
    s = spoken(line["text"])
    i = max(0, s.lower().find(word.lower()))
    v = voiced_times(line["wav"])
    k = min(len(v) - 1, int(len(v) * i / max(1, len(s))))
    return line_start + float(v[k]) - 0.04


def snd(sounds, folder, name):
    hits = sorted(glob.glob(os.path.join(sounds, folder, name + "__*.mp3")))
    return hits[0] if hits else None


def main(sprites, art, voices, sounds, bg, rhubarb_exe, out):
    gap = 0.18
    t = 0.12
    lines = []
    for ln in LINES:
        wav = os.path.join(voices, ln["out"])
        d = wav_seconds(wav)
        lines.append({**ln, "wav": wav, "start": t, "len": d})
        t += d + gap
    length = t + 0.35                                    # abrupt ending, MrBeast style
    l1, l2, l3, l4 = lines

    # characters
    L = scene_light(bg, 0.30, 0.50)                   # the fire is in the middle of the hut
    shocked = Rig(os.path.join(sprites, "kai_shocked_1_cut.png"), 1000, light=L)
    laughing = Rig(os.path.join(sprites, "kai_laughing_1_cut.png"), 1000, light=L)
    bread = Rig(os.path.join(art, "kai_bread_1_cut.png"), 1000, light=L)
    box = json.load(open(os.path.join(art, "face_box.json")))["box"]
    mouths = mouth_images(os.path.join(art, "kai_talkbase.png"), box, art, "kai_mouth_")
    talk = {k: Rig(os.path.join(art, "kai_talkbase_cut.png"), 1000, rgb_override=v, light=scene_light(bg, 0.42, 0.50))
            for k, v in mouths.items()}
    cues = rhubarb(l3["wav"], spoken(l3["text"]), rhubarb_exe)

    x = int(STAGE_W * 0.30)
    head_y = FLOOR_Y - 1000 + 150
    shots, sfx, flashes = [], [], []
    W, H = OUT_W, OUT_H

    # 1. hook: straight into the shocked face
    cam = Camera()
    cam.key(0, 2.2, x, head_y + 110, 0)
    cam.key(0.01, 2.2, x, head_y + 110, 0)
    t1347 = word_time(l1["start"], l1, "thirteen")
    tone = word_time(l1["start"], l1, "ONE")
    cam.key(t1347, 1.5, x, head_y + 300, 0.25)
    cam.key(tone, 2.4, x, head_y + 110, 0.10)
    cam.shake(0.0, 0.4, 24)
    cam.shake(tone, 0.35, 20)
    shots.append(Shot(0, l2["start"], bg, shocked, "shocked", x=x, camera=cam,
                      texts=[(0.2, text_layer("$1 CHALLENGE", 110, "#ffffff"), W * 0.72, H * 0.12),
                             (t1347, text_layer("1347", 170, "#ffffff"), W * 0.72, H * 0.30),
                             (tone, text_layer("$1", 330), W * 0.73, H * 0.58)]))
    sfx += [(0.0, snd(sounds, "sfx_impact", "big-cinematic-impact"), -4),
            (0.2, snd(sounds, "sfx_pop", "hard-pop-click"), -8),
            (t1347, snd(sounds, "sfx_pop", "hard-pop-click"), -6),
            (tone - 0.05, snd(sounds, "sfx_impact", "movie-impact-intro-presentation"), -5)]
    flashes.append(tone)

    # 2. the stone bread
    s2 = l2["start"]
    cam = Camera()
    cam.key(0, 1.15, x + 150, STAGE_H / 2 + 60, 0)
    cam.key(0.01, 1.15, x + 150, STAGE_H / 2 + 60, 0)
    tday = word_time(0, l2, "whole day")
    tst = word_time(0, l2, "STONES")
    cam.key(tday, 1.45, x + 120, head_y + 330, 0.6)
    cam.key(tst, 2.3, x + 120, head_y + 240, 0.1)
    cam.shake(tst, 0.4, 26)
    shots.append(Shot(s2, l3["start"], bg, bread, "disgusted", x=x, camera=cam,
                      texts=[(tday, text_layer("1 DAY OF WORK", 120, "#ffffff"), W * 0.70, H * 0.20),
                             (tst, text_layer("STONES?!", 230), W * 0.70, H * 0.72)]))
    sfx += [(s2 - 0.12, snd(sounds, "sfx_whoosh", "cinematic-whoosh-fast-transition"), -7),
            (s2 + tday, snd(sounds, "sfx_pop", "explainer-video-pops-whoosh-light-pop"), -8),
            (s2 + tst - 0.03, snd(sounds, "sfx_record-scratch", "vinyl-stop-fast-scratch"), -6)]
    flashes.append(s2 + tst)

    # 3. talking close-up with lip sync (background blurred for depth)
    s3 = l3["start"]
    cam = Camera()
    xt = int(STAGE_W * 0.42)
    cam.key(0, 1.85, xt - 40, head_y + 190, 0)
    cam.key(0.01, 1.85, xt - 40, head_y + 190, 0)
    cam.key(l3["len"], 2.1, xt - 40, head_y + 150, l3["len"])        # slow push-in while he explains
    treal = word_time(0, l3, "actually")
    shots.append(Shot(s3, l4["start"], bg, None, "talk", x=xt, talk=talk, cues=cues,
                      blur_bg=9, camera=cam,
                      texts=[(treal, text_layer("100% REAL", 150), W * 0.76, H * 0.30)]))
    sfx += [(s3 - 0.1, snd(sounds, "sfx_whoosh", "cinematic-whoosh-fast-transition"), -9),
            (s3 + treal, snd(sounds, "sfx_ding", "explainer-video-game-reveal"), -8)]

    # 4. the laugh and the king promise
    s4 = l4["start"]
    cam = Camera()
    cam.key(0, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    cam.key(0.01, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    tking = word_time(0, l4, "KING")
    cam.key(tking, 2.0, x, head_y + 140, 0.12)
    cam.shake(tking, 0.45, 28)
    shots.append(Shot(s4, length, bg, laughing, "laughing", x=x, camera=cam,
                      texts=[(tking, text_layer("$1 TO KING?", 200), W * 0.68, H * 0.66)]))
    sfx += [(s4 - 0.1, snd(sounds, "sfx_whoosh", "cinematic-whoosh-fast-transition"), -9),
            (s4 + tking - 0.05, snd(sounds, "sfx_impact", "epic-movie-impact"), -4)]
    flashes.append(s4 + tking)

    voice_tracks = [(ln["start"], ln["wav"], 0) for ln in lines]
    sfx = [s for s in sfx if s[1]]
    music = snd(sounds, "music_funny", "kidding-around") or snd(sounds, "music_funny", "comical")
    audio = out.replace(".mp4", ".wav")
    mix_audio(audio, length, voice_tracks, sfx, music)
    render(shots, length, audio, out, flash_at=flashes)
    print("wrote", out, f"{length:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:8])
