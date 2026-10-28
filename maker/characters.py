"""Draw the main cast as SVG, from one definition per character.

Every scene uses this same code, so KAI, IRIS and BOB always look identical.
Poses move arms, legs and lean; expressions change eyes, brows and mouth.
Hair, clothes and colours never change.

Usage:
  python -m maker.characters lineup out.svg    the three in their default pose
  python -m maker.characters sheet out.svg     every pose and expression, for checking
"""
from __future__ import annotations

import math
import sys

INK = "#26262b"      # outline colour
LW = 5               # outline width
MOUTH = "#5a1f22"

CAST = {
    "KAI": {
        "role": "the curious one",
        "skin": "#e8b894", "hair": "#1f1f22",
        "top": "#c8642b", "top_shade": "#a6501f",
        "pants": "#2f3b55", "shoes": "#2a2a2e", "shoe_accent": "#c8642b",
        "half_w": 58, "label": "#c8642b",
        # signature eyebrows: (inner, middle, outer) offsets, per side (screen-left, screen-right)
        "brows": ((0, -7, 1), (0, -7, 1)),
        "mouth": "smile",
    },
    "IRIS": {
        "role": "the smart one",
        "skin": "#b98060", "hair": "#3e2716",
        "top": "#2f7f78", "top_shade": "#25655f", "inner": "#ece6da",
        "pants": "#2b2b33", "shoes": "#e7e2d8", "shoe_accent": "#2f7f78",
        "half_w": 54, "label": "#2f7f78",
        "brows": ((0, 0, 0), (-1, -8, -2)),
        "mouth": "smile",
    },
    "BOB": {
        "role": "the clueless one",
        "skin": "#e2ae86", "hair": "#8a5a2b", "head": (61, 63),
        "top": "#8c3b2e", "top_shade": "#6f2e24", "inner": "#d6b04a",
        "beanie": "#556b3d", "beanie_band": "#46592f",
        "pants": "#3f4c63", "shoes": "#5a3d26", "shoe_accent": "#3b2818",
        "half_w": 74, "label": "#b8902f",
        "brows": ((-3, -9, -2), (-3, -9, -2)),
        "mouth": "dopey",
    },
}

# ---------------------------------------------------------------- poses
# Angles in degrees. 0 = hanging straight down, 90 = straight out sideways,
# 180 = straight up. Positive = away from the body, negative = across the body.
# arm = (upper arm, forearm), leg = (thigh, shin). L = screen-left, R = screen-right.
# lean = whole upper body tilt, tilt = head tilt, drop = lower the body (bent knees).
POSES = {
    "stand":  {"L": (10, 4), "R": (10, 4), "Lleg": (3, 3), "Rleg": (3, 3)},
    "point":  {"L": (10, 4), "R": (82, 88), "Lleg": (3, 3), "Rleg": (5, 5), "lean": 3},
    "shrug":  {"L": (22, 115), "R": (22, 115), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": -6},
    "shock":  {"L": (140, 170), "R": (140, 170), "Lleg": (9, 9), "Rleg": (9, 9), "lean": -2},
    "wave":   {"L": (10, 4), "R": (125, 168), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 5},
    "scared": {"L": (-12, -150), "R": (-12, -150), "Lleg": (2, 6), "Rleg": (2, 6), "drop": 14, "tilt": -4},
    "explain": {"L": (18, 70), "R": (14, 4), "Lleg": (3, 3), "Rleg": (4, 4), "tilt": 3},
    "run":    {"L": (28, 150), "R": (32, -35), "Lleg": (5, 3), "Rleg": (-12, 30, 0.45, 0.85),
               "lean": 9, "tilt": 5, "fx": "speed"},
    "facepalm": {"L": (10, 4), "R": (150, -102), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 8},
}

POSES["idle"] = POSES["stand"]

# Arm tuples may have up to 5 values: (upper, forearm, upper_len, fore_len, show_hand).
CROSSED = (10, -98, 1.0, 1.02)             # Iris: arms folded across the chest
CROSSED_TOP = (12, -106, 1.0, 1.0)
POCKET = (5, -14, 1.0, 0.62, 0)            # Bob: hands in his jeans pockets

# Each character performs the same pose in their own way.
POSE_STYLE = {
    "KAI": {   # big, open, energetic
        "idle":     {"L": (13, 7), "R": (13, 7), "Lleg": (4, 4), "Rleg": (4, 4)},
        "point":    {"L": (34, 125), "R": (86, 94), "Lleg": (3, 3), "Rleg": (8, 8), "lean": 6, "tilt": 5},
        "shrug":    {"L": (38, 132), "R": (38, 132), "Lleg": (5, 5), "Rleg": (5, 5), "tilt": -10, "drop": -6},
        "shock":    {"L": (150, -120), "R": (150, -120), "Lleg": (11, 11), "Rleg": (11, 11), "lean": -3, "drop": -10},
        "wave":     {"L": (14, 6), "R": (162, 176), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 8},
        "scared":   {"L": (62, -150), "R": (62, -150), "Lleg": (8, 10), "Rleg": (8, 10), "drop": 34, "tilt": -8},
        "explain":  {"L": (46, 96), "R": (46, 96), "Lleg": (4, 4), "Rleg": (4, 4), "tilt": 4},
        "facepalm": {"L": (140, -115), "R": (140, -115), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 10, "drop": 8},
    },
    "IRIS": {  # contained and precise: arms folded, one hand does the talking
        "idle":     {"L": CROSSED_TOP, "R": CROSSED, "Lleg": (3, 3), "Rleg": (2, 2), "tilt": 2},
        "point":    {"L": CROSSED, "R": (80, 84), "Lleg": (3, 3), "Rleg": (4, 4), "tilt": -3},
        "shrug":    {"L": CROSSED, "R": (24, 104), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": -6},
        "shock":    {"L": CROSSED, "R": (155, -80, 1.0, 0.8), "Lleg": (4, 4), "Rleg": (4, 4), "lean": -4},
        "wave":     {"L": CROSSED, "R": (60, 150), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 4},
        "scared":   {"L": (-12, -150), "R": (-12, -150), "Lleg": (2, 6), "Rleg": (2, 6), "drop": 10, "tilt": -3},
        "explain":  {"L": CROSSED, "R": (36, 122), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 3},
        "facepalm": {"L": CROSSED, "R": (150, -102), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 10},
    },
    "BOB": {   # lazy: hands in pockets, slouched, minimum effort (except when he panics)
        "idle":     {"L": POCKET, "R": POCKET, "Lleg": (5, 5), "Rleg": (5, 5), "lean": -3, "tilt": 5},
        "point":    {"L": POCKET, "R": (56, 62), "Lleg": (5, 5), "Rleg": (5, 5), "lean": -3, "tilt": 6},
        "shrug":    {"L": (16, 96), "R": (16, 96), "Lleg": (5, 5), "Rleg": (5, 5), "tilt": 15, "lean": -3},
        "shock":    {"L": (152, 176), "R": (152, 176), "Lleg": (13, 13), "Rleg": (13, 13), "lean": -7},
        "wave":     {"L": POCKET, "R": (150, -100, 1.0, 0.8), "Lleg": (5, 5), "Rleg": (5, 5), "lean": -3, "tilt": 4},
        "scared":   {"L": (155, -92, 1.0, 0.8), "R": (155, -92, 1.0, 0.8), "Lleg": (6, 9), "Rleg": (6, 9), "drop": 12},
        "explain":  {"L": POCKET, "R": (40, 72), "Lleg": (5, 5), "Rleg": (5, 5), "lean": -3, "tilt": 6},
        "facepalm": {"L": POCKET, "R": (150, -102), "Lleg": (5, 5), "Rleg": (5, 5), "lean": -4, "tilt": -8},
    },
}

# How each character moves through time.
#   move  = seconds to get into a new pose, delay = how late they react,
#   breath/amp/sway = idle breathing period (s), breathing size, side-to-side sway,
#   talk_rate = mouth movements per second
TIMING = {
    "KAI":  {"move": 0.18, "delay": 0.0, "breath": 2.4, "amp": 3.0, "sway": 3.0, "talk_rate": 7.5},
    "IRIS": {"move": 0.32, "delay": 0.08, "breath": 3.6, "amp": 1.8, "sway": 0.8, "talk_rate": 6.0},
    "BOB":  {"move": 0.55, "delay": 0.3, "breath": 4.4, "amp": 3.5, "sway": 2.2, "talk_rate": 4.6},
}


def pose_for(name: str, pose) -> dict:
    if isinstance(pose, dict):
        return pose
    return POSE_STYLE.get(name, {}).get(pose) or POSES[pose]


# ---------------------------------------------------------------- expressions
# The 9 expression names the story engine uses. HOW each one looks is different per character
# (see ACTING below): same emotion, three different personalities.
EXPRESSIONS = ["default", "happy", "shock", "scared", "sad", "annoyed", "curious", "smirk", "serious"]

# story MOOD -> expression for the speaker
MOOD_EXPRESSION = {
    "curious": "curious", "funny": "happy", "tense": "serious", "scary": "scared",
    "sad": "sad", "epic": "default", "calm": "default", "shock": "shock",
}

# eyes: normal | wide | huge | happy | closed | squint | half (droopy lids) | roll | one-squint
# look: where the pupils point (dx, dy)
# brows: sig (the character's own) | up | upup | angry | worried | worried2 | one-up | one-angry | flat
# mouth: smile | closed-smile | neutral | flat-side | frown | wobbly | smirk | grin | big-grin | laugh
#        | O | big-O | small-o
ACTING = {
    # KAI: big, fast, open reactions. Everything is a bit "too much".
    "KAI": {
        "default": ("normal", (0, 0), "sig", "smile"),
        "happy":   ("happy", (0, 0), "up", "big-grin"),
        "shock":   ("huge", (0, 0), "upup", "big-O"),
        "scared":  ("huge", (0, 3), "worried2", "wobbly"),
        "sad":     ("normal", (0, 4), "worried2", "frown"),
        "annoyed": ("squint", (0, 0), "angry", "flat-side"),
        "curious": ("wide", (4, -3), "up", "small-o"),
        "smirk":   ("normal", (3, 0), "one-up", "smirk"),
        "serious": ("normal", (0, 0), "angry", "neutral"),
    },
    # IRIS: small, controlled, a little smug. Closed mouth, one eyebrow, eye-rolls.
    "IRIS": {
        "default": ("normal", (0, 0), "sig", "smile"),
        "happy":   ("happy", (0, 0), "flat", "closed-smile"),
        "shock":   ("tall", (0, 0), "up", "small-o"),
        "scared":  ("tall", (-6, 0), "worried", "neutral"),
        "sad":     ("half", (0, 2), "worried", "frown"),
        "annoyed": ("roll", (0, 0), "flat", "flat-side"),
        "curious": ("normal", (4, 0), "one-up", "smirk"),
        "smirk":   ("half", (2, 0), "one-up", "smirk"),
        "serious": ("normal", (0, 0), "angry", "neutral"),
    },
    # BOB: the lovable clueless one. Slow to get it, blank stares, a dopey grin, a huge laugh.
    "BOB": {
        "default": ("normal", (0, 0), "sig", "dopey"),
        "happy":   ("happy", (0, 0), "up", "laugh"),
        "shock":   ("tiny", (0, 0), "upup", "O"),
        "scared":  ("clench", (0, 0), "worried2", "wobbly"),
        "sad":     ("normal", (0, 4), "worried2", "frown"),
        "annoyed": ("one-squint", (0, 0), "one-angry", "flat-side"),
        "curious": ("normal", (5, -4), "one-up", "small-o"),
        "smirk":   ("half", (3, 0), "one-up", "smirk"),
        "serious": ("normal", (0, 0), "angry", "neutral"),
    },
}

TALK_MOUTH = {"KAI": "talk-big", "IRIS": "talk", "BOB": "talk-small"}

BROWS = {
    "up": ((-8, -14, -6), (-8, -14, -6)),
    "upup": ((-15, -23, -12), (-15, -23, -12)),
    "angry": ((7, 0, -6), (7, 0, -6)),
    "worried": ((-9, -4, 5), (-9, -4, 5)),
    "worried2": ((-15, -8, 8), (-15, -8, 8)),
    "one-up": ((1, 0, 1), (-7, -17, -7)),
    "one-angry": ((8, 1, -5), (-4, -11, -3)),
    "flat": ((1, 0, 1), (1, 0, 1)),
}


def face_spec(name: str, expression: str):
    return ACTING[name].get(expression, ACTING[name]["default"])


# ---------------------------------------------------------------- drawing helpers
def _line(d, w=4, colour=INK):
    return (f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def _limb(points, colour, width):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points)
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{width + 2 * LW}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def _step(x, y, side, angle, length):
    a = math.radians(angle)
    return x + side * length * math.sin(a), y + length * math.cos(a)


def _arm(side, c, upper, fore, upper_len=1.0, fore_len=1.0, hand=1):
    """A length < 1 reads as that part of the arm pointing towards the camera.
    hand=0 hides the hand (hands in pockets)."""
    sx, sy = side * (c["half_w"] - 8), -478
    ex, ey = _step(sx, sy, side, upper, 100 * upper_len)
    hx, hy = _step(ex, ey, side, fore, 92 * fore_len)
    ux, uy = _step(hx, hy, side, fore, 9)          # hand sits at the end of the sleeve
    return (_limb([(sx, sy), (ex, ey), (hx, hy)], c["top"], 30)
            + (f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="13" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>'
               if hand else ""))


def _leg(side, c, thigh, shin, drop, thigh_len=1.0, shin_len=1.0):
    """thigh_len < 1 shortens the thigh, which reads as a knee lifted towards the camera."""
    hx, hy = side * 26, -255 + drop
    kx, ky = _step(hx, hy, side, thigh, 112 * thigh_len)
    fx, fy = _step(kx, ky, side, shin, (113 - drop) * shin_len)
    shoe = (f'<path d="M{fx - side * 20:.1f} {fy - 10:.1f} L{fx + side * 30:.1f} {fy - 8:.1f} '
            f'Q{fx + side * 56:.1f} {fy + 8:.1f} {fx + side * 52:.1f} {fy + 22:.1f} '
            f'L{fx - side * 24:.1f} {fy + 22:.1f} Z" fill="{c["shoes"]}" stroke="{INK}" '
            f'stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M{fx - side * 20:.1f} {fy + 13:.1f} L{fx + side * 48:.1f} {fy + 13:.1f}" '
            f'stroke="{c["shoe_accent"]}" stroke-width="4"/>')
    return _limb([(hx, hy), (kx, ky), (fx, fy - 2)], c["pants"], 40) + shoe


def _torso(c):
    w = c["half_w"]
    body = (f"M{-w + 16} -492 Q{-w} -490 {-w} -470 L{-w + 6} -252 Q0 -242 {w - 6} -252 "
            f"L{w} -470 Q{w} -490 {w - 16} -492 Q0 -502 {-w + 16} -492 Z")
    shade = f"M{w * 0.45:.0f} -496 Q{w} -490 {w} -470 L{w - 6} -252 Q{w * 0.6:.0f} -248 {w * 0.45:.0f} -247 Z"
    return (f'<path d="{body}" fill="{c["top"]}"/>'
            f'<path d="{shade}" fill="{c["top_shade"]}"/>'
            f'<path d="{body}" fill="none" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')


# ---------------------------------------------------------------- faces
def _eyes(kind, dx, y, look=(0, 0)):
    lx, ly = look
    out = []
    for i, s in enumerate((-1, 1)):
        x = s * dx
        k = kind
        if kind == "one-squint":
            k = "squint" if i == 0 else "normal"
        if k == "tall":        # Iris: sharp, stretched "wait, what?" eyes
            out.append(f'<ellipse cx="{x + lx * 0.5:.1f}" cy="{y + ly * 0.5:.1f}" rx="5" ry="10.5" fill="{INK}"/>')
        elif k == "tiny":      # Bob: blank pinpoint stare, brain loading
            out.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{INK}"/>')
        elif k == "clench":    # Bob: eyes squeezed shut  > <
            d = (f"M{x - 8} {y - 6} L{x + 5} {y} L{x - 8} {y + 6}" if s < 0
                 else f"M{x + 8} {y - 6} L{x - 5} {y} L{x + 8} {y + 6}")
            out.append(_line(d, 4.5))
        elif k in ("wide", "huge"):
            r = 11 if k == "wide" else 14
            out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                       f'<circle cx="{x + lx * 0.6:.1f}" cy="{y + 1 + ly * 0.6:.1f}" r="5.5" fill="{INK}"/>')
        elif k == "roll":
            out.append(f'<circle cx="{x}" cy="{y}" r="10" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                       f'<circle cx="{x + 2}" cy="{y - 5}" r="5" fill="{INK}"/>'
                       + _line(f"M{x - 11} {y - 3} Q{x} {y - 8} {x + 11} {y - 3}", 4))
        elif k == "half":
            out.append(f'<ellipse cx="{x + lx:.1f}" cy="{y + 2 + ly:.1f}" rx="5.5" ry="5" fill="{INK}"/>'
                       + _line(f"M{x - 10} {y - 2} Q{x} {y - 4} {x + 10} {y - 2}", 4.5))
        elif k == "happy":
            out.append(_line(f"M{x - 8} {y + 3} Q{x} {y - 7} {x + 8} {y + 3}", 4.5))
        elif k == "closed":
            out.append(_line(f"M{x - 8} {y} Q{x} {y + 5} {x + 8} {y}", 4.5))
        elif k == "squint":
            out.append(_line(f"M{x - 8} {y} L{x + 8} {y}", 4.5))
        else:
            out.append(f'<ellipse cx="{x + lx:.1f}" cy="{y + ly:.1f}" rx="5.5" ry="7.5" fill="{INK}"/>')
    return "".join(out)


def _brows(offsets, y=-603):
    out = []
    for s, (di, dm, do) in zip((-1, 1), offsets):
        out.append(_line(f"M{s * 10} {y + di} Q{s * 21} {y + dm} {s * 32} {y + do}", 4.5))
    return "".join(out)


def _mouth(kind, y, beard=False):
    dark = f'fill="{MOUTH}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"'
    teeth = lambda x1, x2, y1, y2: f'<path d="M{x1} {y1} L{x2} {y1} L{x2 - 2} {y2} L{x1 + 2} {y2} Z" fill="#fff"/>'
    if kind == "grin":
        return f'<path d="M-18 {y - 4} Q1 {y + 20} 20 {y - 4} Z" {dark}/>' + teeth(-15, 17, y - 3, y + 3)
    if kind == "big-grin":
        return f'<path d="M-22 {y - 6} Q1 {y + 28} 24 {y - 6} Z" {dark}/>' + teeth(-18, 20, y - 5, y + 2)
    if kind == "laugh":
        return (f'<path d="M-24 {y - 8} Q1 {y + 36} 26 {y - 8} Z" {dark}/>' + teeth(-20, 22, y - 7, y)
                + f'<ellipse cx="2" cy="{y + 14}" rx="10" ry="5" fill="#d9707a"/>')
    if kind == "dopey":
        return (f'<path d="M-13 {y - 3} Q2 {y + 13} 17 {y - 4} Q2 {y + 3} -13 {y - 3} Z" {dark}/>'
                f'<path d="M-9 {y - 1} Q2 {y + 2} 13 {y - 2} L12 {y + 1} Q2 {y + 4} -8 {y + 1} Z" fill="#fff"/>')
    if kind == "O":
        return f'<ellipse cx="2" cy="{y + 2}" rx="8" ry="11" {dark}/>'
    if kind == "big-O":
        return f'<ellipse cx="2" cy="{y + 4}" rx="11" ry="16" {dark}/>'
    if kind == "small-o":
        return f'<ellipse cx="2" cy="{y}" rx="5" ry="6" {dark}/>'
    if kind == "talk":
        return f'<ellipse cx="2" cy="{y + 1}" rx="10" ry="7" {dark}/>'
    if kind == "talk-big":
        return f'<path d="M-14 {y - 3} Q2 {y + 18} 18 {y - 3} Z" {dark}/>' + teeth(-11, 15, y - 2, y + 2)
    if kind == "talk-small":
        return f'<ellipse cx="4" cy="{y + 1}" rx="8" ry="4.5" {dark}/>'
    if kind == "smirk" and beard:
        return (f'<path d="M-14 {y + 6} Q4 {y + 16} 22 {y} Q4 {y + 10} -14 {y + 6} Z" fill="#fff" '
                f'stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>')
    w = 5 if beard else 4
    lines = {
        "smile": f"M-12 {y - 2} Q2 {y + 7} 16 {y - 3}",
        "closed-smile": f"M-17 {y - 4} Q2 {y + 9} 21 {y - 5}",
        "neutral": f"M-10 {y + 1} L12 {y + 1}",
        "flat-side": f"M-2 {y + 2} L20 {y - 2}",
        "frown": f"M-12 {y + 6} Q2 {y - 3} 16 {y + 7}",
        "wobbly": f"M-14 {y + 3} q4 -5 8 0 q4 5 8 0 q4 -5 8 0",
        "smirk": f"M-10 {y + 1} Q6 {y + 4} 18 {y - 6}",
    }
    return _line(lines.get(kind, lines["neutral"]), w)


def _face(name, c, expression, talking, blink=False):
    eyes, look, brows, mouth = face_spec(name, expression)
    if blink and eyes not in ("happy", "closed"):
        eyes = "closed"
    brow_off = c["brows"] if brows == "sig" else BROWS[brows]
    # talking: True, or a loudness 0..1 from the voice track (lip sync)
    level = 1.0 if talking is True else float(talking or 0)
    if level >= 0.55:
        mouth = TALK_MOUTH[name]
    elif level >= 0.15:
        mouth = "talk-small" if name != "IRIS" else "small-o"
    if name == "BOB":
        # Bob's brows sit lower and move less, so even fully raised they stay below the beanie
        bob_off = tuple(tuple(round(v * 0.6) for v in side) for side in brow_off)
        return _eyes(eyes, 24, -584, look), _brows(bob_off, -600), _mouth(mouth, -542)
    if name == "IRIS":
        return _eyes(eyes, 22, -583, look), _brows(brow_off, -604), _mouth(mouth, -544)
    return _eyes(eyes, 20, -582, look), _brows(brow_off, -603), _mouth(mouth, -544)


def _head(c, back, front):
    s = c["skin"]
    rx, ry = c.get("head", (56, 65))
    return (back
            + "".join(f'<ellipse cx="{x}" cy="-578" rx="9" ry="13" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
                      for x in (-rx, rx))
            + f'<ellipse cx="0" cy="-578" rx="{rx}" ry="{ry}" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
            + front)


def _nose(y=-568):
    return _line(f"M2 {y} Q7 {y + 8} 1 {y + 12}", 3)


# ---------------------------------------------------------------- the three characters
def _kai(c, face):
    eyes, brows, mouth = face
    hood = (f'<path d="M-34 -494 Q0 -466 34 -494 Q24 -510 0 -510 Q-24 -510 -34 -494 Z" '
            f'fill="{c["top_shade"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    body = (_torso(c) + hood + _line("M-12 -486 L-14 -440 M12 -486 L14 -440", 3)
            + f'<path d="M-34 -340 L34 -340 L40 -290 L-40 -290 Z" fill="{c["top_shade"]}" '
              f'stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    # wolf cut: shaggy layered volume on top, choppy bangs, longer layers flaring out at the sides
    hair = (f'<path d="M-60 -536 L-71 -560 L-62 -565 L-75 -592 L-64 -598 L-73 -628 Q-60 -676 0 -678 '
            f'Q60 -676 73 -628 L64 -598 L75 -592 L62 -565 L71 -560 L60 -536 L53 -562 L56 -606 '
            f'L47 -628 L40 -614 L30 -627 L20 -613 L10 -627 L0 -614 L-10 -627 L-20 -613 L-30 -627 '
            f'L-40 -614 L-47 -628 L-56 -606 L-53 -562 Z" '
            f'fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
            + _line("M-34 -660 Q-8 -672 22 -664", 3, "#4a4a52") + _line("M-62 -600 Q-58 -620 -52 -634", 3, "#4a4a52")
            + _line("M62 -600 Q58 -620 52 -634", 3, "#4a4a52"))
    return body, _head(c, "", hair + eyes + brows + _nose() + mouth)


def _iris(c, face):
    eyes, brows, mouth = face
    body = (_torso(c)
            + f'<path d="M-20 -494 L20 -494 L18 -252 L-18 -252 Z" fill="{c["inner"]}" stroke="{INK}" stroke-width="4"/>'
            + _line("M-20 -494 L-30 -420 L-22 -252 M20 -494 L30 -420 L22 -252", 4))
    back = (f'<path d="M44 -626 C100 -648 122 -588 106 -526 C96 -562 80 -588 54 -594 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M-62 -580 Q-70 -662 0 -662 Q70 -662 62 -580 Q64 -556 52 -544 Q46 -566 40 -578 '
            f'L-40 -578 Q-46 -566 -52 -544 Q-64 -556 -62 -580 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    fringe = (f'<path d="M-58 -580 Q-66 -656 0 -658 Q64 -656 58 -588 Q36 -630 -6 -620 Q-38 -612 -58 -580 Z" '
              f'fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    glasses = "".join(f'<rect x="{x}" y="-595" width="32" height="24" rx="6" fill="none" '
                      f'stroke="{INK}" stroke-width="4"/>' for x in (-38, 6)) + _line("M-6 -584 L6 -584", 3)
    return body, _head(c, back, fringe + eyes + glasses + brows + _nose(-566) + mouth)


def _bob(c, face):
    eyes, brows, mouth = face
    w = c["half_w"]
    stripe = lambda d: _line(d, 3, c["top_shade"])
    body = (_torso(c)
            + "".join(stripe(f"M{-w + 4} {y} L-26 {y} M26 {y} L{w - 4} {y}") for y in (-440, -380, -320))
            + "".join(stripe(f"M{x} -488 L{x} -256") for x in (-w + 22, w - 22))
            + f'<path d="M-26 -496 L26 -496 L24 -250 L-24 -250 Z" fill="{c["inner"]}" stroke="{INK}" stroke-width="4"/>')
    hair = "".join(f'<path d="{d}" fill="{c["hair"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                   for d in ("M-60 -622 L-70 -600 L-56 -608 L-60 -590 L-46 -606 L-44 -622 Z",
                             "M60 -622 L70 -600 L56 -608 L60 -590 L46 -606 L44 -622 Z",
                             "M-20 -616 L-14 -598 L-6 -610 L2 -594 L8 -610 L16 -598 L20 -616 Z"))
    beanie = (f'<path d="M-60 -620 Q-60 -688 0 -690 Q60 -688 60 -620 Z" fill="{c["beanie"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>'
              f'<rect x="-64" y="-638" width="128" height="24" rx="8" fill="{c["beanie_band"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>')
    return body, _head(c, "", eyes + _nose(-570) + mouth + hair + beanie + brows)


def _speed_lines():
    """Motion lines behind the runner and a dust puff at the planted foot."""
    lines = "".join(_line(f"M{x1} {y} L{x2} {y}", 5, "#9b948a")
                    for x1, x2, y in ((-215, -120, -470), (-245, -125, -400), (-205, -115, -330),
                                      (-235, -130, -255), (-190, -120, -180)))
    dust = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#d8d1c4" stroke="#9b948a" stroke-width="3"/>'
                   for x, y, r in ((-95, -14, 20), (-128, -24, 15), (-155, -12, 11)))
    return dust + lines


_EFFECTS = {"speed": _speed_lines}



def run_pose(phase: float) -> dict:
    """One moment of the run cycle. phase 0..1 = one full stride (left step + right step).

    Each knee lifts in turn, the opposite arm pumps up, and the body bounces.
    """
    lift_l = max(0.0, math.sin(2 * math.pi * phase))
    lift_r = max(0.0, -math.sin(2 * math.pi * phase))

    def leg(lift):
        # knee comes up towards the camera: short thigh, shin hanging under the knee
        return (2 - 6 * lift, 2 - 4 * lift, 1 - 0.62 * lift, 1 - 0.22 * lift)

    def arm(up):
        # elbows stay tucked in; the hand pumps up to the chest, then back down to the hip
        return (14 + 4 * up, 8 - 170 * up, 0.95, 0.72 - 0.17 * up)

    # the arm opposite to the lifted knee comes up
    swing = 0.5 + 0.5 * math.sin(2 * math.pi * phase)          # 1 = left knee up
    bounce = abs(math.sin(2 * math.pi * phase))
    return {"L": arm(1 - swing), "R": arm(swing),
            "Lleg": leg(lift_l), "Rleg": leg(lift_r),
            "drop": 14 - 14 * bounce, "lean": 0, "tilt": 2 * math.sin(2 * math.pi * phase)}



def blend_pose(a, b, t: float, name: str | None = None) -> dict:
    """Smoothly move from pose a to pose b. t = 0..1 (eased)."""
    pa = pose_for(name, a) if name else (POSES[a] if isinstance(a, str) else a)
    pb = pose_for(name, b) if name else (POSES[b] if isinstance(b, str) else b)
    t = max(0.0, min(1.0, t))
    t = t * t * (3 - 2 * t)
    out = {}
    for k in ("L", "R", "Lleg", "Rleg"):
        va, vb = list(pa[k]), list(pb[k])
        n = max(len(va), len(vb))
        defaults = [0, 0, 1.0, 1.0, 1]
        va += defaults[len(va):n]
        vb += defaults[len(vb):n]
        vals = [x + (y - x) * t for x, y in zip(va, vb)]
        if n >= 5:  # hand visibility switches halfway
            vals[4] = vb[4] if t > 0.5 else va[4]
        out[k] = tuple(vals)
    for k in ("lean", "tilt", "drop"):
        out[k] = pa.get(k, 0) + (pb.get(k, 0) - pa.get(k, 0)) * t
    out["fx"] = pb.get("fx") if t > 0.5 else pa.get("fx")
    return out


def idle_pose(t: float, name: str, base="idle") -> dict:
    """Standing still but alive: breathing and sway in the character's own rhythm."""
    tm = TIMING[name]
    seed = {"KAI": 0.0, "IRIS": 0.37, "BOB": 0.71}[name]
    p = dict(pose_for(name, base))
    breath = math.sin(2 * math.pi * (t / tm["breath"] + seed))
    p["drop"] = p.get("drop", 0) + tm["amp"] * breath
    p["tilt"] = p.get("tilt", 0) + tm["sway"] * math.sin(2 * math.pi * (t / (tm["breath"] * 1.6) + seed))
    if name == "KAI":   # can't keep still: little weight shifts
        p["lean"] = p.get("lean", 0) + 2.0 * math.sin(2 * math.pi * t / 1.9)
    p["L"] = (p["L"][0] + 0.6 * tm["amp"] * breath, *p["L"][1:])
    p["R"] = (p["R"][0] + 0.6 * tm["amp"] * breath, *p["R"][1:])
    return p


def talk_pose(t: float, name: str) -> dict:
    """Gestures while speaking, in each character's style."""
    p = dict(idle_pose(t, name, "explain"))
    if name == "KAI":     # both hands, fast, big
        p["L"] = (46 + 14 * math.sin(5.1 * t), 96 + 30 * math.sin(5.1 * t + 1.2))
        p["R"] = (46 + 14 * math.sin(4.3 * t + 2), 96 + 30 * math.sin(4.3 * t + 0.4))
        p["tilt"] = 4 * math.sin(2.7 * t)
    elif name == "IRIS":  # one hand making points, on the beat
        beat = abs(math.sin(3.0 * t)) ** 3
        p["R"] = (34 + 8 * beat, 118 - 26 * beat)
    else:                 # Bob: lazy hand, slow head wobble
        p["R"] = (38 + 8 * math.sin(1.7 * t), 70 + 18 * math.sin(1.7 * t + 0.8))
        p["tilt"] = 6 + 5 * math.sin(1.3 * t)
    return p


def is_blinking(t: float, name: str) -> bool:
    """A quick blink every few seconds; Bob blinks slower and longer."""
    period = {"KAI": 2.6, "IRIS": 3.8, "BOB": 4.6}[name]
    length = {"KAI": 0.1, "IRIS": 0.12, "BOB": 0.25}[name]
    seed = {"KAI": 0.3, "IRIS": 1.4, "BOB": 2.2}[name]
    return (t + seed) % period < length


def mouth_open(t: float, name: str) -> bool:
    """Talking mouth flap at the character's own speaking speed."""
    rate = TIMING[name]["talk_rate"]
    seed = {"KAI": 0.0, "IRIS": 2.0, "BOB": 4.0}[name]
    v = math.sin(2 * math.pi * rate * t + seed) + 0.6 * math.sin(2 * math.pi * rate * 0.35 * t + 2 * seed)
    return v > 0.15


BUILD = {"KAI": _kai, "IRIS": _iris, "BOB": _bob}


def character(name: str, x: float, y: float, scale: float = 1.0, pose: str | dict = "stand",
              expression: str = "default", talking: bool = False, flip: bool = False,
              blink: bool = False) -> str:
    """SVG group for one character with feet at (x, y). flip=True mirrors left/right."""
    c = CAST[name]
    p = pose_for(name, pose)
    drop, lean, tilt = p.get("drop", 0), p.get("lean", 0), p.get("tilt", 0)
    body, head = BUILD[name](c, _face(name, c, expression, talking, blink))
    neck = f'<rect x="-15" y="-522" width="30" height="36" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>'
    arms = _arm(-1, c, *p["L"]) + _arm(1, c, *p["R"])
    legs = (_leg(-1, c, *p["Lleg"][:2], drop, *p["Lleg"][2:])
            + _leg(1, c, *p["Rleg"][:2], drop, *p["Rleg"][2:]))
    fx = _EFFECTS[p["fx"]]() if p.get("fx") else ""
    upper = (f'<g transform="translate(0 {drop}) rotate({lean} 0 -255)">'
             f'{neck}{body}<g transform="rotate({tilt} 0 -515)">{head}</g>{arms}</g>')
    sx = -scale if flip else scale
    return f'<g transform="translate({x} {y}) scale({sx} {scale})">{fx}{legs}{upper}</g>'


# ---------------------------------------------------------------- preview sheets
def _svg(w, h, body, bg="#ece7df"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>')


def _label(x, y, text, size=21, colour="#5f5a52", bold=False):
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="DejaVu Sans, Arial" '
            f'font-size="{size}" fill="{colour}"{" font-weight=\"bold\"" if bold else ""}>{text}</text>')


def lineup() -> str:
    parts = ['<ellipse cx="750" cy="792" rx="620" ry="20" fill="#000" opacity=".08"/>']
    for x, name in ((330, "KAI"), (750, "IRIS"), (1170, "BOB")):
        parts.append(character(name, x, 790))
        parts.append(_label(x, 845, name, 40, CAST[name]["label"], True) + _label(x, 878, CAST[name]["role"]))
    return _svg(1500, 900, "".join(parts))


def sheet() -> str:
    """Rows: one per character. First block: poses. Second block: expressions (close-up)."""
    poses = list(POSES)
    exprs = list(EXPRESSIONS)
    cell = 210
    w = cell * len(poses)
    parts = []
    y = 40
    parts.append(_label(w / 2, y, "POSES", 30, "#26262b", True))
    for name in CAST:
        y += 360
        for i, pose in enumerate(poses):
            parts.append(character(name, cell * i + cell / 2, y, 0.48, pose))
            parts.append(_label(cell * i + cell / 2, y + 30, pose, 18))
    y += 90
    parts.append(_label(w / 2, y, "EXPRESSIONS", 30, "#26262b", True))
    ecell = w / len(exprs)
    for name in CAST:
        y += 230
        for i, ex in enumerate(exprs):
            cx = ecell * i + ecell / 2
            # close-up: scale 1.25 and only the head + shoulders show inside a clip
            parts.append(f'<clipPath id="c{name}{i}"><rect x="{cx - ecell / 2 + 6}" y="{y - 200}" '
                         f'width="{ecell - 12}" height="185" rx="12"/></clipPath>'
                         f'<rect x="{cx - ecell / 2 + 6}" y="{y - 200}" width="{ecell - 12}" height="185" rx="12" fill="#f7f3ec"/>'
                         f'<g clip-path="url(#c{name}{i})">{character(name, cx, y + 610, 1.25, "stand", ex)}</g>')
            parts.append(_label(cx, y + 6, ex, 17))
    y += 40
    return _svg(w, y, "".join(parts))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "lineup"
    out = sys.argv[2] if len(sys.argv) > 2 else f"characters/{'trio' if what == 'lineup' else 'sheet'}.svg"
    with open(out, "w") as f:
        f.write(lineup() if what == "lineup" else sheet())
    print("wrote", out)
