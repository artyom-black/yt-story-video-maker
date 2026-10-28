"""Character showcase video: every movement of the cast in one clip, for checking.

Usage:  python -m maker.showcase out.mp4
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from .characters import (POSES, EXPRESSIONS, blend_pose, character, idle_pose, is_blinking,
                         mouth_open)
from .side_view import (WALK_LEG_KEYS, character_side, side_run_pose, side_walk_pose,
                        stride_speed)

W, H, FPS = 1920, 1080, 24
CAST = ("KAI", "IRIS", "BOB")
SEED = {"KAI": 0.0, "IRIS": 0.37, "BOB": 0.71}
X = {"KAI": 480, "IRIS": 960, "BOB": 1440}
FLOOR = 1010
SCALE = 1.12


# ---------------------------------------------------------------- backdrops
def room():
    return (f'<rect width="{W}" height="{H}" fill="#e9e2d6"/>'
            f'<rect y="{FLOOR - 20}" width="{W}" height="{H - FLOOR + 20}" fill="#cfc4b2"/>'
            f'<rect y="{FLOOR - 24}" width="{W}" height="6" fill="#b9ad99"/>')


def caption(title, sub=""):
    w = max(len(title) * 26, len(sub) * 15) + 80
    return (f'<rect x="{(W - w) / 2}" y="34" width="{w}" height="{96 if sub else 70}" rx="16" fill="#26262b" opacity=".86"/>'
            f'<text x="{W / 2}" y="82" text-anchor="middle" font-family="DejaVu Sans, Arial" font-weight="bold" '
            f'font-size="40" fill="#fff">{title}</text>'
            + (f'<text x="{W / 2}" y="116" text-anchor="middle" font-family="DejaVu Sans, Arial" font-size="24" '
               f'fill="#d8d2c8">{sub}</text>' if sub else ""))


def outdoors(t, speed, ground=900):
    def layer(sp, spacing, draw):
        off = (t * sp) % spacing
        return "".join(draw(x - off) for x in range(0, W + 2 * spacing, spacing))
    hill = lambda x: f'<ellipse cx="{x}" cy="{ground - 60}" rx="420" ry="230" fill="#a6bb93"/>'
    tree = lambda x: (f'<rect x="{x - 16}" y="{ground - 260}" width="32" height="260" fill="#6b4e2e" stroke="#26262b" stroke-width="5"/>'
                      f'<circle cx="{x}" cy="{ground - 330}" r="120" fill="#5f7f4a" stroke="#26262b" stroke-width="5"/>')
    tuft = lambda x: (f'<path d="M{x} {ground + 60} l12 -30 l8 30 l10 -24 l6 24" fill="none" stroke="#5f7f4a" '
                      f'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<rect width="{W}" height="{H}" fill="#bcd9e6"/>' + layer(speed * 0.12, 700, hill)
            + f'<rect y="{ground - 40}" width="{W}" height="60" fill="#9bb38a"/>' + layer(speed * 0.45, 640, tree)
            + f'<rect y="{ground}" width="{W}" height="{H - ground}" fill="#86a06f"/>'
            + f'<rect y="{ground}" width="{W}" height="14" fill="#c9b892"/>' + layer(speed, 260, tuft))


# ---------------------------------------------------------------- sections
def section_idle(t, d):
    return room() + "".join(character(n, X[n], FLOOR, SCALE, idle_pose(t, SEED[n]), blink=is_blinking(t, SEED[n]))
                            for n in CAST) + caption("Standing", "breathing and blinking")


TALK = [("KAI", "curious", {"IRIS": "smirk", "BOB": "default"}),
        ("IRIS", "default", {"KAI": "curious", "BOB": "annoyed"}),
        ("BOB", "happy", {"KAI": "happy", "IRIS": "annoyed"})]


def section_talk(t, d):
    i = min(int(t / (d / 3)), 2)
    speaker, expr, others = TALK[i]
    lt = t - i * d / 3
    out = room()
    for n in CAST:
        if n == speaker:
            pose = idle_pose(t, SEED[n], blend_pose("stand", "explain", min(1, lt / 0.5)))
            out += character(n, X[n], FLOOR, SCALE, pose, expr, talking=mouth_open(t, SEED[n] * 9),
                             blink=is_blinking(t, SEED[n]))
        else:
            out += character(n, X[n], FLOOR, SCALE, idle_pose(t, SEED[n]), others[n], blink=is_blinking(t, SEED[n]))
    return out + caption("Talking", f"{speaker} speaks, the others react")


def section_expressions(t, d):
    names = list(EXPRESSIONS)
    i = min(int(t / (d / len(names))), len(names) - 1)
    ex = names[i]
    # close-up: bigger and lower so faces fill the frame
    return room() + "".join(character(n, X[n], 1720, 2.0, idle_pose(t, SEED[n]), ex,
                                      blink=is_blinking(t, SEED[n]) and ex == "default")
                            for n in CAST) + caption("Expressions", ex)


def section_poses(t, d):
    names = [p for p in POSES if p != "run"] + ["stand"]
    step = d / (len(names) - 1)
    i = min(int(t / step), len(names) - 2)
    lt = (t - i * step) / step
    move = min(1.0, lt / 0.35)                  # first 35% of each step: move into the new pose
    a, b = names[i], names[i + 1]
    expr = {"shock": "shock", "scared": "scared", "facepalm": "annoyed", "wave": "happy",
            "shrug": "smirk", "explain": "default", "point": "curious"}.get(b, "default")
    out = room()
    for n in CAST:
        pose = idle_pose(t, SEED[n], blend_pose(a, b, move))
        out += character(n, X[n], FLOOR, SCALE, pose, expr if move > 0.5 else "default",
                         blink=is_blinking(t, SEED[n]))
    return out + caption("Poses", b)


WALK_STRIDE, RUN_STRIDE = 1.05, 0.5
WALK_SPEED = stride_speed(WALK_LEG_KEYS, 0.95, WALK_STRIDE)
RUN_SPEED = stride_speed(scale=0.95, stride_seconds=RUN_STRIDE)


def section_walk(t, d):
    out = outdoors(t, WALK_SPEED)
    for n, x, off, ex in (("BOB", 470, 0.5, "smirk"), ("IRIS", 900, 0.25, "default"), ("KAI", 1330, 0.0, "curious")):
        out += character_side(n, x, 906, 0.95, side_walk_pose(t / WALK_STRIDE + off), ex,
                              talking=(n == "KAI" and mouth_open(t)), blink=is_blinking(t, SEED[n]))
    return out + caption("Walking", "side view")


def section_run(t, d):
    out = outdoors(t, RUN_SPEED)
    for n, x, off, ex in (("BOB", 470, 0.5, "serious"), ("IRIS", 900, 0.25, "default"), ("KAI", 1330, 0.0, "shock")):
        out += character_side(n, x, 906, 0.95, side_run_pose(t / RUN_STRIDE + off), ex, blink=is_blinking(t, SEED[n]))
    return out + caption("Running", "side view")


SECTIONS = [(section_idle, 4), (section_talk, 10.5), (section_expressions, 15.3),
            (section_poses, 17.6), (section_walk, 7), (section_run, 7)]


def render(out_mp4: str):
    tmp = tempfile.mkdtemp(prefix="showcase_")
    n = 0
    for fn, dur in SECTIONS:
        for f in range(int(dur * FPS)):
            t = f / FPS
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
                   f'{fn(t, dur)}</svg>')
            with open(f"{tmp}/f{n:05d}.svg", "w") as fh:
                fh.write(svg)
            n += 1
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%05d.svg",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out_mp4],
                   check=True)
    shutil.rmtree(tmp)
    print(f"wrote {out_mp4} ({n} frames, {n / FPS:.0f}s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "showcase.mp4")
