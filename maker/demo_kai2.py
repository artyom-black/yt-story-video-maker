"""Kai demo v2: same scene, with every weak point of v1 fixed.

- characters lit like the scene (colour cast, firelight from the fire side, rim light), shadow under the shoes,
  outline matched to the background
- face locked to the master in every picture; a sharp close-up picture for the hook
- blinking; two hand gestures in the talking shot, switched on the phrases; mouths from Rhubarb
- a faster hook

Usage:  python -m maker.demo_kai2 ART VOICES SOUNDS BACKGROUND RHUBARB out.mp4
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image

from .demo_kai import LINES, snd, spoken, word_time
from .editor import (EYES, MOUTH, Rig, Shot, apply_patch, blink_times, is_blinking, mix_audio, phrases, render,
                     rhubarb, scene_light, shape_at, text_layer, wav_seconds)
from .motion import FLOOR_Y, OUT_H, OUT_W, STAGE_H, STAGE_W, Camera

FIRE_X = 0.50          # where the fire is in the hut background (share of the width)


def load_set(art, name, light, height, full_body=True, mouths=False):
    """Rigs for a picture: {(mouth_shape, blinking): Rig}. Only the eyes / mouth area ever changes."""
    base = Image.open(os.path.join(art, f"{name}.png")).convert("RGB")
    box = json.load(open(os.path.join(art, f"{name}_face_box.json")))["box"]
    cut = os.path.join(art, f"{name}_cut.png")
    shapes = {"X": base}
    if mouths:
        for sh in "BCDEFG":
            p = os.path.join(art, f"{name}_{sh}.png")
            if os.path.exists(p):
                shapes[sh] = apply_patch(base, base, box, p, MOUTH)
        shapes["A"] = base
        shapes["H"] = shapes.get("C", base)
    blink_png = os.path.join(art, f"{name}_blink.png")
    out = {}
    for sh, img in shapes.items():
        out[(sh, False)] = Rig(cut, height, full_body, rgb_override=img, light=light)
        if os.path.exists(blink_png):
            out[(sh, True)] = Rig(cut, height, full_body, rgb_override=apply_patch(img, base, box, blink_png, EYES),
                                  light=light)
    return out


def main(art, voices, sounds, bg, rhubarb_exe, out):
    lines_def = list(LINES)
    gap, t, lines = 0.18, 0.12, []
    for ln in lines_def:
        wav = os.path.join(voices, ln["out"])
        d = wav_seconds(wav)
        lines.append({**ln, "wav": wav, "start": t, "len": d})
        t += d + gap
    length = t + 0.3
    l1, l2, l3, l4 = lines
    W, H = OUT_W, OUT_H
    x = int(STAGE_W * 0.30)
    light_full = scene_light(bg, 0.30, FIRE_X)
    head_y = FLOOR_Y - 1000 + 150

    hook = load_set(art, "hook", scene_light(bg, 0.42, FIRE_X), 1350, full_body=False)
    bread = load_set(art, "bread", light_full, 1000)
    talk_a = load_set(art, "talkA", light_full, 1000, mouths=True)
    talk_b = load_set(art, "talkB", light_full, 1000, mouths=True)
    laugh = load_set(art, "laugh", light_full, 1000)

    def simple(rigs, start, end, seed):
        blinks = blink_times(0, end - start, seed)
        return lambda local: (rigs.get(("X", is_blinking(local, blinks)), rigs[("X", False)]), local)

    shots, sfx, flashes = [], [], []

    # 1. hook: sharp close-up, starts on the strong words
    t1347 = word_time(l1["start"], l1, "thirteen")
    tone = word_time(l1["start"], l1, "ONE")
    cam = Camera()
    cam.key(0, 1.25, STAGE_W * 0.42, STAGE_H * 0.36, 0)
    cam.key(0.01, 1.25, STAGE_W * 0.42, STAGE_H * 0.36, 0)
    cam.key(t1347, 1.12, STAGE_W * 0.45, STAGE_H * 0.42, 0.3)
    cam.key(tone, 1.6, STAGE_W * 0.42, STAGE_H * 0.33, 0.1)
    cam.shake(0.0, 0.35, 22)
    cam.shake(tone, 0.35, 20)
    shots.append(Shot(0, l2["start"], bg, kind="shocked", x=int(STAGE_W * 0.40), camera=cam,
                      pick=simple(hook, 0, l2["start"], 3),
                      texts=[(0.25, text_layer("$1 CHALLENGE", 120, "#ffffff"), W * 0.74, H * 0.16),
                             (t1347, text_layer("1347", 190, "#ffffff"), W * 0.75, H * 0.40),
                             (tone, text_layer("$1", 330), W * 0.76, H * 0.70)]))
    sfx += [(0.0, snd(sounds, "sfx_impact", "big-cinematic-impact"), -4),
            (0.25, snd(sounds, "sfx_pop", "hard-pop-click"), -8),
            (t1347, snd(sounds, "sfx_pop", "hard-pop-click"), -6),
            (tone - 0.05, snd(sounds, "sfx_impact", "movie-impact-intro-presentation"), -5)]
    flashes.append(tone)

    # 2. the stone bread
    s2 = l2["start"]
    tday = word_time(0, l2, "whole day")
    tst = word_time(0, l2, "STONES")
    cam = Camera()
    cam.key(0, 1.25, x + 160, STAGE_H / 2 + 80, 0)
    cam.key(0.01, 1.25, x + 160, STAGE_H / 2 + 80, 0)
    cam.key(tday, 1.5, x + 130, head_y + 330, 0.6)
    cam.key(tst, 2.0, x + 130, head_y + 260, 0.1)
    cam.shake(tst, 0.4, 26)
    shots.append(Shot(s2, l3["start"], bg, kind="disgusted", x=x, camera=cam, pick=simple(bread, s2, l3["start"], 5),
                      texts=[(tday, text_layer("1 DAY OF WORK", 120, "#ffffff"), W * 0.70, H * 0.20),
                             (tst, text_layer("STONES?!", 230), W * 0.70, H * 0.72)]))
    sfx += [(s2 - 0.12, snd(sounds, "sfx_whoosh", "cinematic-whoosh-fast-transition"), -7),
            (s2 + tday, snd(sounds, "sfx_pop", "explainer-video-pops-whoosh-light-pop"), -8),
            (s2 + tst - 0.03, snd(sounds, "sfx_record-scratch", "vinyl-stop-fast-scratch"), -6)]
    flashes.append(s2 + tst)

    # 3. talking: two gestures switched on the phrases, mouths from Rhubarb, blinking
    s3 = l3["start"]
    cues = rhubarb(l3["wav"], spoken(l3["text"]), rhubarb_exe)
    starts = phrases(l3["wav"]) or [0.0]
    blinks = blink_times(0, l4["start"] - s3, 7)

    def talk_pick(local):
        k = max([i for i, st in enumerate(starts) if st <= local] or [0])
        rigs = talk_a if k % 2 == 0 else talk_b
        since = local - (starts[k] if k < len(starts) else 0)
        key = (shape_at(cues, local), is_blinking(local, blinks))
        return rigs.get(key) or rigs.get((key[0], False)) or rigs[("X", False)], (since if k else local)

    xt = int(STAGE_W * 0.42)
    treal = word_time(0, l3, "actually")
    cam = Camera()
    cam.key(0, 1.85, xt - 40, head_y + 190, 0)
    cam.key(0.01, 1.85, xt - 40, head_y + 190, 0)
    cam.key(l3["len"], 2.1, xt - 40, head_y + 150, l3["len"])
    shots.append(Shot(s3, l4["start"], bg, kind="talk", x=xt, blur_bg=9, camera=cam, pick=talk_pick,
                      texts=[(treal, text_layer("100% REAL", 150), W * 0.76, H * 0.30)]))
    sfx += [(s3 - 0.1, snd(sounds, "sfx_whoosh", "cinematic-whoosh-fast-transition"), -9),
            (s3 + treal, snd(sounds, "sfx_ding", "explainer-video-game-reveal"), -8)]

    # 4. the laugh and the promise
    s4 = l4["start"]
    tking = word_time(0, l4, "KING")
    cam = Camera()
    cam.key(0, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    cam.key(0.01, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    cam.key(tking, 2.0, x, head_y + 140, 0.12)
    cam.shake(tking, 0.45, 28)
    shots.append(Shot(s4, length, bg, laugh[("X", False)], "laughing", x=x, camera=cam,
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
    main(*sys.argv[1:7])
