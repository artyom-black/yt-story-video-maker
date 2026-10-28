"""Draw the main cast as SVG, from one definition per character.

Every scene uses this same code, so KAI, IRIS and BOB always look identical.
Poses only move the arms and legs; faces, hair and clothes never change.

Usage:  python -m maker.characters out.svg      (draws the cast line-up)
"""
from __future__ import annotations

import math
import sys

INK = "#26262b"      # outline colour
LW = 5               # outline width

CAST = {
    "KAI": {
        "role": "the curious one",
        "skin": "#e8b894", "hair": "#1f1f22",
        "top": "#c8642b", "top_shade": "#a6501f",
        "pants": "#2f3b55", "shoes": "#2a2a2e", "shoe_accent": "#c8642b",
        "half_w": 58, "label": "#c8642b",
    },
    "IRIS": {
        "role": "the smart one",
        "skin": "#b98060", "hair": "#3e2716",
        "top": "#2f7f78", "top_shade": "#25655f", "inner": "#ece6da",
        "pants": "#2b2b33", "shoes": "#e7e2d8", "shoe_accent": "#2f7f78",
        "half_w": 54, "label": "#2f7f78",
    },
    "BOB": {
        "role": "the funny one",
        "skin": "#e2ae86", "hair": "#6b4423",
        "top": "#8c3b2e", "top_shade": "#6f2e24", "inner": "#d6b04a",
        "beanie": "#556b3d", "beanie_band": "#46592f",
        "pants": "#3f4c63", "shoes": "#5a3d26", "shoe_accent": "#3b2818",
        "half_w": 74, "label": "#b8902f",
    },
}

# Pose = joint angles in degrees (0 = straight down, positive = outward from body).
POSES = {
    "stand": {"upper": 10, "fore": 4, "hip": 3},
}


def _limb(points, colour, width):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points)
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{width + 2 * LW}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def _arm(side, c, pose):
    sx, sy = side * (c["half_w"] - 8), -478
    a1 = math.radians(pose["upper"])
    ex, ey = sx + side * 100 * math.sin(a1), sy + 100 * math.cos(a1)
    a2 = math.radians(pose["fore"])
    hx, hy = ex + side * 92 * math.sin(a2), ey + 92 * math.cos(a2)
    return (_limb([(sx, sy), (ex, ey), (hx, hy)], c["top"], 30)
            + f'<circle cx="{hx:.1f}" cy="{hy + 8:.1f}" r="13" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>')


def _leg(side, c, pose):
    hx, hy = side * 26, -255
    a = math.radians(pose["hip"])
    fx, fy = hx + side * 225 * math.sin(a), hy + 225 * math.cos(a)
    shoe = (f'<path d="M{fx - side * 20:.1f} {fy - 16:.1f} L{fx + side * 30:.1f} {fy - 14:.1f} '
            f'Q{fx + side * 56:.1f} {fy + 2:.1f} {fx + side * 52:.1f} {fy + 16:.1f} '
            f'L{fx - side * 24:.1f} {fy + 16:.1f} Z" fill="{c["shoes"]}" stroke="{INK}" '
            f'stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M{fx - side * 20:.1f} {fy + 7:.1f} L{fx + side * 48:.1f} {fy + 7:.1f}" '
            f'stroke="{c["shoe_accent"]}" stroke-width="4"/>')
    return _limb([(hx, hy), (fx, fy - 6)], c["pants"], 40) + shoe


def _torso(c):
    w = c["half_w"]
    body = (f"M{-w + 16} -492 Q{-w} -490 {-w} -470 L{-w + 6} -252 Q0 -242 {w - 6} -252 "
            f"L{w} -470 Q{w} -490 {w - 16} -492 Q0 -502 {-w + 16} -492 Z")
    shade = f"M{w * 0.45:.0f} -496 Q{w} -490 {w} -470 L{w - 6} -252 Q{w * 0.6:.0f} -248 {w * 0.45:.0f} -247 Z"
    return (f'<path d="{body}" fill="{c["top"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="{shade}" fill="{c["top_shade"]}"/>'
            f'<path d="{body}" fill="none" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')


def _eyes(dx=20, y=-582):
    return "".join(f'<ellipse cx="{s * dx}" cy="{y}" rx="5.5" ry="7.5" fill="{INK}"/>' for s in (-1, 1))


def _line(d, w=4):
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def _head(c, extra_back="", extra_front=""):
    s = c["skin"]
    return (extra_back
            + f'<rect x="-15" y="-522" width="30" height="36" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
            + "".join(f'<ellipse cx="{x}" cy="-578" rx="9" ry="13" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>' for x in (-56, 56))
            + f'<ellipse cx="0" cy="-578" rx="56" ry="65" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
            + extra_front)


def draw_kai(c, pose):
    hood = (f'<path d="M-34 -494 Q0 -466 34 -494 Q24 -510 0 -510 Q-24 -510 -34 -494 Z" '
            f'fill="{c["top_shade"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    strings = _line("M-12 -486 L-14 -440 M12 -486 L14 -440", 3)
    pocket = (f'<path d="M-34 -340 L34 -340 L40 -290 L-40 -290 Z" fill="{c["top_shade"]}" '
              f'stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    hair = (f'<path d="M-58 -588 Q-64 -652 0 -654 Q64 -652 58 -588 Q52 -618 32 -624 L24 -604 L10 -628 '
            f'L-6 -606 L-22 -630 L-34 -608 Q-54 -614 -58 -588 Z" fill="{c["hair"]}" stroke="{INK}" '
            f'stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M-4 -652 C-10 -688 24 -702 42 -688 C24 -686 18 -672 16 -652 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    face = (_eyes() + _line("M-31 -602 Q-21 -609 -10 -603") + _line("M10 -603 Q21 -610 31 -602")
            + _line("M2 -568 Q6 -560 1 -556", 3)
            + _line("M-10 -544 Q2 -538 14 -546"))
    return (_leg(-1, c, pose) + _leg(1, c, pose) + _torso(c) + hood + strings + pocket
            + _arm(-1, c, pose) + _arm(1, c, pose) + _head(c, extra_front=hair + face))


def draw_iris(c, pose):
    inner = (f'<path d="M-20 -494 L20 -494 L18 -252 L-18 -252 Z" fill="{c["inner"]}" stroke="{INK}" '
             f'stroke-width="4"/>' + _line("M-20 -494 L-30 -420 L-22 -252 M20 -494 L30 -420 L22 -252", 4))
    back = (f'<path d="M44 -626 C100 -648 122 -588 106 -526 C96 -562 80 -588 54 -594 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M-62 -580 Q-70 -662 0 -662 Q70 -662 62 -580 Q64 -556 52 -544 Q46 -566 40 -578 L-40 -578 Q-46 -566 -52 -544 Q-64 -556 -62 -580 Z" fill="{c["hair"]}" '
            f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    fringe = (f'<path d="M-58 -580 Q-66 -656 0 -658 Q64 -656 58 -588 Q36 -630 -6 -620 Q-38 -612 -58 -580 Z" '
              f'fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    glasses = "".join(f'<rect x="{x}" y="-594" width="32" height="22" rx="6" fill="none" '
                      f'stroke="{INK}" stroke-width="4"/>' for x in (-38, 6)) + _line("M-6 -584 L6 -584", 3)
    face = (_eyes(22, -583) + glasses + _line("M-34 -604 L-12 -603") + _line("M12 -604 Q23 -612 34 -606")
            + _line("M1 -566 Q5 -558 0 -554", 3) + _line("M-12 -544 Q2 -536 16 -546"))
    return (_leg(-1, c, pose) + _leg(1, c, pose) + _torso(c) + inner
            + _arm(-1, c, pose) + _arm(1, c, pose) + _head(c, back, fringe + face))


def draw_bob(c, pose):
    w = c["half_w"]
    tee = f'<path d="M-26 -496 L26 -496 L24 -250 L-24 -250 Z" fill="{c["inner"]}" stroke="{INK}" stroke-width="4"/>'
    checks = "".join(_line(f"M{-w + 4} {y} L{-26} {y} M26 {y} L{w - 4} {y}", 3).replace(INK, c["top_shade"])
                     for y in (-440, -380, -320))
    checks += "".join(_line(f"M{x} -488 L{x} -256", 3).replace(INK, c["top_shade"]) for x in (-w + 22, w - 22))
    beanie = (f'<path d="M-60 -596 Q-60 -668 0 -670 Q60 -668 60 -596 Z" fill="{c["beanie"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>'
              f'<rect x="-64" y="-612" width="128" height="24" rx="8" fill="{c["beanie_band"]}" stroke="{INK}" '
              f'stroke-width="{LW}"/>')
    beard = (f'<path d="M-56 -578 Q-58 -506 0 -502 Q58 -506 56 -578 Q50 -548 26 -546 Q0 -556 -26 -546 '
             f'Q-50 -548 -56 -578 Z" fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    mouth = (f'<path d="M-14 -538 Q4 -528 22 -544 Q4 -534 -14 -538 Z" fill="#ffffff" stroke="{INK}" '
             f'stroke-width="3.5" stroke-linejoin="round"/>')
    face = (_eyes(21, -584) + _line("M-32 -603 L-11 -601") + _line("M11 -605 Q22 -617 33 -609")
            + _line("M2 -570 Q7 -562 1 -558", 3) + beard + mouth)
    return (_leg(-1, c, pose) + _leg(1, c, pose) + _torso(c) + tee + checks
            + _arm(-1, c, pose) + _arm(1, c, pose) + _head(c, extra_front=face + beanie))


DRAW = {"KAI": draw_kai, "IRIS": draw_iris, "BOB": draw_bob}


def character(name: str, x: float, y: float, scale: float = 1.0, pose: str = "stand") -> str:
    """SVG group for one character, feet at (x, y)."""
    c = CAST[name]
    return f'<g transform="translate({x},{y}) scale({scale})">{DRAW[name](c, POSES[pose])}</g>'


def lineup() -> str:
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 900" width="1500" height="900">',
             '<rect width="1500" height="900" fill="#ece7df"/>',
             '<ellipse cx="750" cy="792" rx="620" ry="20" fill="#000" opacity=".08"/>']
    for x, name in ((330, "KAI"), (750, "IRIS"), (1170, "BOB")):
        c = CAST[name]
        parts.append(character(name, x, 790))
        parts.append(f'<text x="{x}" y="845" text-anchor="middle" font-family="DejaVu Sans, Arial" '
                     f'font-weight="bold" font-size="40" fill="{c["label"]}">{name}</text>'
                     f'<text x="{x}" y="878" text-anchor="middle" font-family="DejaVu Sans, Arial" '
                     f'font-size="21" fill="#5f5a52">{c["role"]}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "characters/trio.svg"
    with open(out, "w") as f:
        f.write(lineup())
    print("wrote", out)
