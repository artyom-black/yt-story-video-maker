"""Kai demo v2: the same scene with every weak point of v1 fixed.

- lit like the scene, shadow under the shoes, outline matched to the background
- face locked to the master; a sharp close-up picture for the hook
- lip sync in EVERY shot where he speaks; 3-4 face changes per sentence (eyes / eyebrows); blinking;
  two hand gestures in the talking shot, switched on the phrases
- cut-away pictures that SHOW what he talks about
- sounds from the measured sound kit, each placed on its hit, always under the voice
- a faster hook

Usage:  python -m maker.demo_kai2 ART VOICES KIT CANDIDATES BACKGROUND RHUBARB out.mp4
"""
from __future__ import annotations

import functools
import json
import os
import sys

from PIL import Image

from .demo_kai import LINES, spoken, word_time
from .editor import (EYES, MOUTH, Rig, Shot, apply_patch, blink_times, is_blinking, mix_audio, phrases, render,
                     rhubarb, scene_light, shape_at, text_layer, wav_seconds)
from .motion import FLOOR_Y, OUT_H, OUT_W, STAGE_H, STAGE_W, Camera, background

FIRE_X = 0.50          # where the fire is in the hut background (share of the width)


class Face:
    """All versions of one picture: mouth shape x blink x expression. Built only when first needed."""

    def __init__(self, art, name, light, height, full_body=True):
        self.art, self.name, self.light, self.height, self.full_body = art, name, light, height, full_body
        self.base = Image.open(os.path.join(art, f"{name}.png")).convert("RGB")
        self.box = json.load(open(os.path.join(art, f"{name}_face_box.json")))["box"]
        self.cut = os.path.join(art, f"{name}_cut.png")

    def _p(self, key):
        p = os.path.join(self.art, f"{self.name}_{key}.png")
        return p if os.path.exists(p) else None

    @functools.lru_cache(maxsize=64)
    def rig(self, mouth="X", blink=False, expr=None):
        img = self.base
        if expr and self._p(f"x_{expr}"):
            img = apply_patch(img, self.base, self.box, self._p(f"x_{expr}"), EYES)
        m = {"A": None, "X": None, "H": "C"}.get(mouth, mouth)
        if m and self._p(m):
            img = apply_patch(img, self.base, self.box, self._p(m), MOUTH)
        if blink and self._p("blink"):
            img = apply_patch(img, self.base, self.box, self._p("blink"), EYES)
        return Rig(self.cut, self.height, self.full_body, rgb_override=img, light=self.light)


class Kit:
    def __init__(self, kit_dir):
        self.dir = kit_dir
        self.info = {c["kit_file"]: c for ch in json.load(open(os.path.join(kit_dir, "kit.json")))["roles"].values()
                     for c in ch}

    def at(self, event_time, kit_file, gain_db):
        """Place a kit sound so that its hit lands exactly on event_time."""
        return (max(0.0, event_time - self.info[kit_file]["hit_at"]), os.path.join(self.dir, kit_file), gain_db)


def speaking(face, line, cues, exprs, blinks, start_offset=0.0):
    """pick(local) for a shot where the character speaks a line: lip sync + face changes + blinks."""
    def pick(local):
        lt = local - start_offset
        expr = None
        for t, e in exprs:
            if t <= lt:
                expr = e
        return face.rig(shape_at(cues, lt), is_blinking(local, blinks), expr), local
    return pick


def main(art, voices, kit_dir, cands, bg, rhubarb_exe, out):
    kit = Kit(kit_dir)
    gap, t, lines = 0.18, 0.12, []
    for ln in LINES:
        wav = os.path.join(voices, ln["out"])
        d = wav_seconds(wav)
        lines.append({**ln, "wav": wav, "start": t, "len": d})
        t += d + gap
    length = t + 0.3
    l1, l2, l3, l4 = lines
    for ln in lines:
        ln["cues"] = rhubarb(ln["wav"], spoken(ln["text"]), rhubarb_exe)
    W, H = OUT_W, OUT_H
    x = int(STAGE_W * 0.30)
    light_full = scene_light(bg, 0.30, FIRE_X)
    head_y = FLOOR_Y - 1000 + 150

    hook = Face(art, "hook", scene_light(bg, 0.42, FIRE_X), 1350, full_body=False)
    bread = Face(art, "bread", light_full, 1000)
    talk_a = Face(art, "talkA", light_full, 1000)
    talk_b = Face(art, "talkB", light_full, 1000)
    laugh = Face(art, "laugh", light_full, 1000)

    shots, sfx, flashes = [], [], []
    wt = lambda ln, w: word_time(0, ln, w)                      # time of a word inside its line

    # 1. hook: sharp close-up, lip sync, disbelief -> panic
    t1347, tone = l1["start"] + wt(l1, "thirteen"), l1["start"] + wt(l1, "ONE")
    cam = Camera()
    cam.key(0, 1.25, STAGE_W * 0.42, STAGE_H * 0.36, 0)
    cam.key(0.01, 1.25, STAGE_W * 0.42, STAGE_H * 0.36, 0)
    cam.key(t1347, 1.12, STAGE_W * 0.45, STAGE_H * 0.42, 0.3)
    cam.key(tone, 1.6, STAGE_W * 0.42, STAGE_H * 0.33, 0.1)
    cam.shake(0.0, 0.3, 18)
    cam.shake(tone, 0.35, 20)
    shots.append(Shot(0, l2["start"], bg, kind="shocked", x=int(STAGE_W * 0.40), camera=cam,
                      pick=speaking(hook, l1, l1["cues"], [(wt(l1, "thirteen"), "disbelief"), (wt(l1, "ONE"), "panic")],
                                    blink_times(0, l2["start"], 3), l1["start"]),
                      texts=[(0.2, text_layer("$1 CHALLENGE", 120, "#ffffff"), W * 0.74, H * 0.16),
                             (t1347, text_layer("1347", 190, "#ffffff"), W * 0.75, H * 0.40),
                             (tone, text_layer("$1", 330), W * 0.76, H * 0.70)]))
    sfx += [kit.at(0.05, "hit_1.wav", -3), kit.at(0.2, "pop_3.wav", -6), kit.at(t1347, "pop_3.wav", -6),
            kit.at(tone, "hit_1.wav", -1)]
    flashes.append(tone)

    # 2. the stone bread, with a cut-away to a whole day of work
    s2 = l2["start"]
    tday, tst = wt(l2, "whole day"), wt(l2, "STONES")
    cam = Camera()
    cam.key(0, 1.25, x + 160, STAGE_H / 2 + 80, 0)
    cam.key(0.01, 1.25, x + 160, STAGE_H / 2 + 80, 0)
    cam.key(tst, 2.0, x + 130, head_y + 260, 0.1)
    cam.shake(tst, 0.4, 26)
    bread_pick = speaking(bread, l2, l2["cues"], [(tday, "confused"), (tst, "outraged")], blink_times(0, 9, 5))
    shots.append(Shot(s2, l3["start"], bg, kind="disgusted", x=x, camera=cam, pick=bread_pick,
                      texts=[(tst, text_layer("STONES?!", 230), W * 0.70, H * 0.72)]))
    work_bg = os.path.join(art, "cut_work.png")
    if os.path.exists(work_bg):                                 # SHOW the day of work while he says it
        cw = Camera()
        cw.key(0, 1.0, STAGE_W / 2, STAGE_H / 2, 0)
        cw.key(0.01, 1.0, STAGE_W / 2, STAGE_H / 2, 0)
        cw.key(1.3, 1.12, STAGE_W / 2 + 80, STAGE_H / 2, 1.3)    # slow push, documentary style
        end_cut = min(s2 + tst - 0.15, s2 + tday + 1.4)
        shots.insert(len(shots) - 1, Shot(s2 + tday - 0.1, end_cut, work_bg, camera=cw,
                                          pick=lambda local: (None, local),
                                          texts=[(0.05, text_layer("1 DAY OF WORK", 140, "#ffffff"), W * 0.5, H * 0.18)]))
        sfx.append(kit.at(s2 + tday - 0.1, "whoosh_4.wav", -10))
    sfx += [kit.at(s2, "whoosh_4.wav", -8), kit.at(s2 + tst, "sting_4.wav", -5)]
    flashes.append(s2 + tst)

    # 3. talking: two gestures on the phrases, lip sync, face changes, and a cut-away to the broken tooth
    s3 = l3["start"]
    starts = phrases(l3["wav"]) or [0.0]
    blinks = blink_times(0, l4["start"] - s3, 7)
    exprs = [(0.0, "knowing"), (wt(l3, "Medieval"), "serious"), (wt(l3, "broke"), "amazed")]

    def talk_pick(local):
        k = max([i for i, st in enumerate(starts) if st <= local] or [0])
        face = talk_a if k % 2 == 0 else talk_b
        expr = None
        for tt, e in exprs:
            if tt <= local:
                expr = e
        since = local - starts[k] if k else local
        return face.rig(shape_at(l3["cues"], local), is_blinking(local, blinks), expr), since

    xt = int(STAGE_W * 0.42)
    treal = wt(l3, "actually")
    cam = Camera()
    cam.key(0, 1.85, xt - 40, head_y + 190, 0)
    cam.key(0.01, 1.85, xt - 40, head_y + 190, 0)
    cam.key(l3["len"], 2.1, xt - 40, head_y + 150, l3["len"])
    shots.append(Shot(s3, l4["start"], bg, kind="talk", x=xt, blur_bg=9, camera=cam, pick=talk_pick,
                      texts=[(treal, text_layer("100% REAL", 150), W * 0.76, H * 0.30)]))
    tooth_bg = os.path.join(art, "cut_tooth.png")
    if os.path.exists(tooth_bg):
        tb = wt(l3, "broke")
        ct = Camera()
        ct.key(0, 1.0, STAGE_W / 2, STAGE_H / 2, 0)
        ct.key(0.01, 1.0, STAGE_W / 2, STAGE_H / 2, 0)
        ct.key(0.15, 1.18, STAGE_W / 2, STAGE_H / 2, 0.15)       # quick punch-in on the tooth
        ct.shake(0.15, 0.25, 12)
        shots.insert(len(shots) - 1, Shot(s3 + tb, min(l4["start"], s3 + tb + 1.3), tooth_bg, camera=ct,
                                          pick=lambda local: (None, local)))
        sfx.append(kit.at(s3 + tb + 0.15, "hit_2.wav", -6))
    sfx += [kit.at(s3, "whoosh_4.wav", -9), kit.at(s3 + treal, "ding_2.wav", -9)]

    # 4. the laugh and the promise: lip sync, smug face at the end
    s4 = l4["start"]
    tking = wt(l4, "KING")
    cam = Camera()
    cam.key(0, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    cam.key(0.01, 1.4, x + 250, STAGE_H / 2 + 150, 0)
    cam.key(tking, 2.0, x, head_y + 140, 0.12)
    cam.shake(tking, 0.45, 28)
    shots.append(Shot(s4, length, bg, kind="laughing", x=x, camera=cam,
                      pick=speaking(laugh, l4, l4["cues"], [(wt(l4, "survive"), "smug")], []),
                      texts=[(tking, text_layer("$1 TO KING?", 200), W * 0.68, H * 0.66)]))
    sfx += [kit.at(s4, "whoosh_4.wav", -9), kit.at(s4 + tking, "hit_1.wav", -1)]
    flashes.append(s4 + tking)

    # cut-aways are listed after the scene they interrupt, so the renderer shows them on top, then the scene resumes
    cutaways = [sh for sh in shots if sh.pick and sh.pick(0)[0] is None]
    shots = [sh for sh in shots if sh not in cutaways] + cutaways
    music = None
    info = json.load(open(os.path.join(kit_dir, "kit.json")))["music"]
    for want in ("kidding-around", "keep-smiling", "upbeat-jazz"):
        m = [mm for mm in info if mm["ok"] and mm["name"].startswith(want)]
        if m:
            music = os.path.join(cands, m[0]["file"])
            break
    audio = out.replace(".mp4", ".wav")
    mix_audio(audio, length, [(ln["start"], ln["wav"], 0) for ln in lines], sfx, music, music_db=-20)
    render(shots, length, audio, out, flash_at=flashes)
    print("wrote", out, f"{length:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:8])
