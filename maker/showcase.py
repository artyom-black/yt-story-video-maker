"""Character showcase video: every movement of the cast in one clip, for checking.

Usage:  python -m maker.showcase out.mp4
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from .characters import (EXPRESSIONS, POSE_STYLE, TIMING, blend_pose, character, idle_pose,
                         is_blinking, mouth_open, talk_pose)
from .side_view import (WALK_LEG_KEYS, _gait, character_side, side_run_pose, side_walk_pose,
                        stride_speed)

W, H, FPS = 1920, 1080, 24
CAST = ("KAI", "IRIS", "BOB")
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
    return room() + "".join(character(n, X[n], FLOOR, SCALE, idle_pose(t, n), blink=is_blinking(t, n))
                            for n in CAST) + caption("Standing", "Kai fidgets, Iris folds her arms, Bob slouches")


TALK = [("KAI", "curious", {"IRIS": "smirk", "BOB": "default"}),
        ("IRIS", "default", {"KAI": "curious", "BOB": "annoyed"}),
        ("BOB", "happy", {"KAI": "happy", "IRIS": "annoyed"})]


def _react(t, n, start):
    """Fraction 0..1 of how far a character has reacted, using their own speed and delay."""
    tm = TIMING[n]
    return max(0.0, min(1.0, (t - start - tm["delay"]) / tm["move"]))


def section_talk(t, d):
    seg = d / 3
    i = min(int(t / seg), 2)
    speaker, expr, others = TALK[i]
    lt = t - i * seg
    out = room()
    for n in CAST:
        if n == speaker:
            k = _react(lt, n, 0)
            pose = blend_pose(idle_pose(t, n), talk_pose(t, n), k)
            out += character(n, X[n], FLOOR, SCALE, pose, expr, talking=mouth_open(t, n), blink=is_blinking(t, n))
        else:
            ex = others[n] if _react(lt, n, 0.4) > 0.5 else "default"
            out += character(n, X[n], FLOOR, SCALE, idle_pose(t, n), ex, blink=is_blinking(t, n))
    return out + caption("Talking", f"{speaker} speaks, the others react in their own way")


def section_expressions(t, d):
    i = min(int(t / (d / len(EXPRESSIONS))), len(EXPRESSIONS) - 1)
    ex = EXPRESSIONS[i]
    lt = t - i * d / len(EXPRESSIONS)
    out = room()
    for n in CAST:
        shown = ex if _react(lt, n, 0) > 0.5 else (EXPRESSIONS[i - 1] if i else "default")
        out += character(n, X[n], 1720, 2.0, idle_pose(t, n), shown, blink=is_blinking(t, n) and shown == "default")
    return out + caption("Expressions", ex)


POSE_ORDER = ["idle", "point", "shrug", "shock", "wave", "scared", "explain", "facepalm", "idle"]
POSE_FACE = {"shock": "shock", "scared": "scared", "facepalm": "annoyed", "wave": "happy",
             "shrug": "smirk", "explain": "default", "point": "curious", "idle": "default"}


def section_poses(t, d):
    step = d / (len(POSE_ORDER) - 1)
    i = min(int(t / step), len(POSE_ORDER) - 2)
    lt = t - i * step
    a, b = POSE_ORDER[i], POSE_ORDER[i + 1]
    out = room()
    for n in CAST:
        k = _react(lt, n, 0)
        pose = blend_pose(idle_pose(t, n, a), idle_pose(t, n, b), k)
        face = POSE_FACE[b] if k > 0.5 else POSE_FACE[a]
        out += character(n, X[n], FLOOR, SCALE, pose, face, blink=is_blinking(t, n))
    return out + caption("Poses", b if b != "idle" else "back to standing")


LANE_H = 300


def lanes(t, kind, title):
    """Three stacked lanes, one per character, each moving at their own natural speed."""
    out = f'<rect width="{W}" height="{H}" fill="#bcd9e6"/>'
    keys = WALK_LEG_KEYS if kind == "walk" else None
    pose_fn = side_walk_pose if kind == "walk" else side_run_pose
    expr = {"walk": {"KAI": "curious", "IRIS": "default", "BOB": "default"},
            "run": {"KAI": "shock", "IRIS": "serious", "BOB": "scared"}}[kind]
    for row, n in enumerate(CAST):
        top = 150 + row * LANE_H
        ground = top + LANE_H - 30
        g = _gait(n, kind)
        speed = stride_speed(keys, 0.42, name=n, kind=kind)
        out += f'<svg x="0" y="{top}" width="{W}" height="{LANE_H}" viewBox="0 {ground - LANE_H + 30} {W} {LANE_H}">'
        out += outdoors_strip(t, speed, ground)
        out += character_side(n, 900, ground + 4, 0.42, pose_fn(t / g["stride"], n), expr[n],
                              talking=(kind == "walk" and n == "KAI" and mouth_open(t, n)), blink=is_blinking(t, n))
        out += '</svg>'
        out += (f'<text x="60" y="{top + 60}" font-family="DejaVu Sans, Arial" font-weight="bold" font-size="38" '
                f'fill="#26262b">{n}</text>')
    return out + caption(title, "each with their own gait and speed")


def outdoors_strip(t, speed, ground):
    def layer(sp, spacing, draw):
        off = (t * sp) % spacing
        return "".join(draw(x - off) for x in range(0, W + 2 * spacing, spacing))
    tree = lambda x: (f'<rect x="{x - 7}" y="{ground - 110}" width="14" height="110" fill="#6b4e2e" stroke="#26262b" stroke-width="3"/>'
                      f'<circle cx="{x}" cy="{ground - 140}" r="50" fill="#5f7f4a" stroke="#26262b" stroke-width="3"/>')
    tuft = lambda x: (f'<path d="M{x} {ground + 22} l6 -14 l4 14 l5 -11 l3 11" fill="none" stroke="#5f7f4a" '
                      f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<rect x="0" y="{ground - 400}" width="{W}" height="400" fill="#bcd9e6"/>'
            + f'<rect x="0" y="{ground - 40}" width="{W}" height="40" fill="#a6bb93"/>' + layer(speed * 0.45, 420, tree)
            + f'<rect y="{ground}" width="{W}" height="60" fill="#86a06f"/>'
            + f'<rect y="{ground}" width="{W}" height="7" fill="#c9b892"/>' + layer(speed, 180, tuft))


def section_walk(t, d):
    return lanes(t, "walk", "Walking")


def section_run(t, d):
    return lanes(t, "run", "Running")


SECTIONS = [(section_idle, 5), (section_talk, 12), (section_expressions, 18),
            (section_poses, 19.2), (section_walk, 7), (section_run, 7)]


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
