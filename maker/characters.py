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
        "role": "the funny one",
        "skin": "#e2ae86", "hair": "#6b4423",
        "top": "#8c3b2e", "top_shade": "#6f2e24", "inner": "#d6b04a",
        "beanie": "#556b3d", "beanie_band": "#46592f",
        "pants": "#3f4c63", "shoes": "#5a3d26", "shoe_accent": "#3b2818",
        "half_w": 74, "label": "#b8902f",
        "brows": ((0, 0, 1), (-2, -12, -4)),
        "mouth": "smirk",
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
    "run":    {"L": (35, 110), "R": (-25, 60), "Lleg": (28, -8), "Rleg": (-6, 28), "lean": 4, "drop": 18},
    "facepalm": {"L": (10, 4), "R": (150, -102), "Lleg": (3, 3), "Rleg": (3, 3), "tilt": 8},
}

# ---------------------------------------------------------------- expressions
EXPRESSIONS = {
    #            eyes       brows       mouth
    "default":  ("normal",  None,       None),
    "happy":    ("happy",   None,       "grin"),
    "shock":    ("wide",    "up",       "O"),
    "scared":   ("wide",    "worried",  "O"),
    "sad":      ("normal",  "worried",  "frown"),
    "annoyed":  ("squint",  "angry",    "neutral"),
    "curious":  ("normal",  "up",       "small-o"),
    "smirk":    ("normal",  None,       "smirk"),
    "serious":  ("normal",  "angry",    "neutral"),
}

# story MOOD -> expression for the speaker
MOOD_EXPRESSION = {
    "curious": "curious", "funny": "happy", "tense": "serious", "scary": "scared",
    "sad": "sad", "epic": "default", "calm": "default", "shock": "shock",
}

BROWS = {
    "up": ((-8, -14, -6), (-8, -14, -6)),
    "angry": ((7, 0, -6), (7, 0, -6)),
    "worried": ((-9, -4, 5), (-9, -4, 5)),
}


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


def _arm(side, c, upper, fore):
    sx, sy = side * (c["half_w"] - 8), -478
    ex, ey = _step(sx, sy, side, upper, 100)
    hx, hy = _step(ex, ey, side, fore, 92)
    ux, uy = _step(hx, hy, side, fore, 9)          # hand sits at the end of the sleeve
    return (_limb([(sx, sy), (ex, ey), (hx, hy)], c["top"], 30)
            + f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="13" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>')


def _leg(side, c, thigh, shin, drop):
    hx, hy = side * 26, -255 + drop
    kx, ky = _step(hx, hy, side, thigh, 112)
    fx, fy = _step(kx, ky, side, shin, 113 - drop)
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
def _eyes(kind, dx, y):
    out = []
    for s in (-1, 1):
        x = s * dx
        if kind == "wide":
            out.append(f'<circle cx="{x}" cy="{y}" r="11" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                       f'<circle cx="{x}" cy="{y + 1}" r="5" fill="{INK}"/>')
        elif kind == "happy":
            out.append(_line(f"M{x - 8} {y + 3} Q{x} {y - 7} {x + 8} {y + 3}", 4.5))
        elif kind == "squint":
            out.append(_line(f"M{x - 8} {y} L{x + 8} {y}", 4.5))
        else:
            out.append(f'<ellipse cx="{x}" cy="{y}" rx="5.5" ry="7.5" fill="{INK}"/>')
    return "".join(out)


def _brows(offsets, y=-603):
    out = []
    for s, (di, dm, do) in zip((-1, 1), offsets):
        out.append(_line(f"M{s * 10} {y + di} Q{s * 21} {y + dm} {s * 32} {y + do}", 4.5))
    return "".join(out)


def _mouth(kind, y, beard=False):
    dark = f'fill="{MOUTH}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"'
    if kind == "grin":
        return (f'<path d="M-18 {y - 4} Q1 {y + 20} 20 {y - 4} Z" {dark}/>'
                f'<path d="M-15 {y - 3} L17 {y - 3} L15 {y + 3} L-13 {y + 3} Z" fill="#fff"/>')
    if kind == "O":
        return f'<ellipse cx="2" cy="{y + 2}" rx="8" ry="11" {dark}/>'
    if kind == "small-o":
        return f'<ellipse cx="2" cy="{y}" rx="5" ry="6" {dark}/>'
    if kind == "talk":
        return f'<ellipse cx="2" cy="{y + 1}" rx="10" ry="7" {dark}/>'
    if kind == "smirk" and beard:
        return (f'<path d="M-14 {y + 6} Q4 {y + 16} 22 {y} Q4 {y + 10} -14 {y + 6} Z" fill="#fff" '
                f'stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>')
    w = 5 if beard else 4
    lines = {
        "smile": f"M-12 {y - 2} Q2 {y + 7} 16 {y - 3}",
        "neutral": f"M-10 {y + 1} L12 {y + 1}",
        "frown": f"M-12 {y + 6} Q2 {y - 3} 16 {y + 7}",
        "smirk": f"M-10 {y + 1} Q6 {y + 4} 18 {y - 6}",
    }
    return _line(lines.get(kind, lines["neutral"]), w)


def _face(name, c, expression, talking):
    eyes, brows, mouth = EXPRESSIONS[expression]
    brow_off = BROWS[brows] if brows else c["brows"]
    mouth = "talk" if talking else (mouth or c["mouth"])
    if name == "BOB":
        return _eyes(eyes, 21, -584), _brows(brow_off, -604), _mouth(mouth, -540, beard=True)
    if name == "IRIS":
        return _eyes(eyes, 22, -583), _brows(brow_off, -604), _mouth(mouth, -544)
    return _eyes(eyes, 20, -582), _brows(brow_off, -603), _mouth(mouth, -544)


def _head(c, back, front):
    s = c["skin"]
    return (back
            + "".join(f'<ellipse cx="{x}" cy="-578" rx="9" ry="13" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
                      for x in (-56, 56))
            + f'<ellipse cx="0" cy="-578" rx="56" ry="65" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
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
    hair = (f'<path d="M-58 -588 Q-64 -652 0 -654 Q64 -652 58 -588 Q52 -618 32 -624 L24 -604 L10 -628 '
            f'L-6 -606 L-22 -630 L-34 -608 Q-54 -614 -58 -588 Z" fill="{c["hair"]}" stroke="{INK}" '
            f'stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M-4 -652 C-10 -688 24 -702 42 -688 C24 -686 18 -672 16 -652 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
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
    beard = (f'<path d="M-56 -578 Q-58 -506 0 -502 Q58 -506 56 -578 Q50 -548 26 -546 Q0 -556 -26 -546 '
             f'Q-50 -548 -56 -578 Z" fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    beanie = (f'<path d="M-60 -612 Q-60 -680 0 -682 Q60 -680 60 -612 Z" fill="{c["beanie"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>'
              f'<rect x="-64" y="-630" width="128" height="24" rx="8" fill="{c["beanie_band"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>')
    return body, _head(c, "", eyes + _nose(-570) + beard + mouth + beanie + brows)


BUILD = {"KAI": _kai, "IRIS": _iris, "BOB": _bob}


def character(name: str, x: float, y: float, scale: float = 1.0, pose: str = "stand",
              expression: str = "default", talking: bool = False, flip: bool = False) -> str:
    """SVG group for one character with feet at (x, y). flip=True mirrors left/right."""
    c = CAST[name]
    p = POSES[pose]
    drop, lean, tilt = p.get("drop", 0), p.get("lean", 0), p.get("tilt", 0)
    body, head = BUILD[name](c, _face(name, c, expression, talking))
    neck = f'<rect x="-15" y="-522" width="30" height="36" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>'
    arms = _arm(-1, c, *p["L"]) + _arm(1, c, *p["R"])
    legs = _leg(-1, c, *p["Lleg"], drop) + _leg(1, c, *p["Rleg"], drop)
    upper = (f'<g transform="translate(0 {drop}) rotate({lean} 0 -255)">'
             f'{neck}{body}<g transform="rotate({tilt} 0 -515)">{head}</g>{arms}</g>')
    sx = -scale if flip else scale
    return f'<g transform="translate({x} {y}) scale({sx} {scale})">{legs}{upper}</g>'


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
