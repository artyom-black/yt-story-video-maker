"""Doodle-style characters drawn by code: round head, huge expressive eyes, thick outlines, few details.

Usage:  python -m maker.doodle test BACKGROUND.png out.png
"""
from __future__ import annotations

import subprocess
import sys

INK = "#161210"
SKIN = "#f6d3b3"
SKIN_SHADE = "#e7b893"

LOOK = {
    "KAI": dict(top="#c8322b", top_shade="#9f2420", trim="#7d1b18", legs="#5b4a3a", shoes="#3b2a1f",
                hair="#14110f", hair_style="sideswept"),
}


def _p(d, fill, stroke=INK, w=9, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" {extra}/>'


def eyes(expr):
    """Huge expressive eyes. Returns SVG around a head centred at 0,0 (radius 150)."""
    if expr == "shocked":
        e = ""
        for x in (-58, 58):
            e += f'<ellipse cx="{x}" cy="-5" rx="46" ry="56" fill="#fff" stroke="{INK}" stroke-width="8"/>'
            e += f'<circle cx="{x}" cy="2" r="11" fill="{INK}"/>'
        e += _p("M-105 -88 Q-60 -122 -18 -96", "none", w=10)      # eyebrows shot up
        e += _p("M18 -96 Q60 -122 105 -88", "none", w=10)
        return e
    if expr == "happy":
        return (_p("M-95 -5 Q-58 -45 -20 -5", "none", w=11) + _p("M20 -5 Q58 -45 95 -5", "none", w=11)
                + _p("M-100 -70 Q-60 -88 -22 -72", "none", w=9) + _p("M22 -72 Q60 -88 100 -70", "none", w=9))
    e = ""
    for x in (-58, 58):
        e += f'<ellipse cx="{x}" cy="0" rx="36" ry="42" fill="#fff" stroke="{INK}" stroke-width="8"/>'
        e += f'<circle cx="{x + 6}" cy="6" r="14" fill="{INK}"/><circle cx="{x + 11}" cy="0" r="4" fill="#fff"/>'
    e += _p("M-96 -62 Q-60 -76 -24 -64", "none", w=9) + _p("M24 -64 Q60 -76 96 -62", "none", w=9)
    return e


def mouth(expr):
    if expr == "shocked":
        return (f'<ellipse cx="0" cy="88" rx="30" ry="40" fill="#5a1a18" stroke="{INK}" stroke-width="8"/>'
                f'<ellipse cx="0" cy="110" rx="18" ry="10" fill="#d9605a"/>')
    if expr == "happy":
        return _p("M-55 60 Q0 140 55 60 Z", "#5a1a18", w=8) + '<path d="M-30 98 Q0 118 30 98 Q0 108 -30 98 Z" fill="#d9605a"/>'
    return _p("M-30 78 Q0 98 30 78", "none", w=9)


def hair_kai():
    # black side-swept fringe falling to his right (viewer's left), a few spikes on top
    return (_p("M-150 -20 Q-165 -150 -40 -175 Q60 -195 135 -130 Q165 -95 150 -30 Q120 -95 60 -105 "
               "Q-10 -60 -95 -55 Q-70 -80 -60 -95 Q-110 -70 -150 -20 Z", "#14110f", w=9)
            + _p("M-20 -178 L5 -215 L25 -176", "#14110f", w=8) + _p("M40 -180 L78 -205 L80 -165", "#14110f", w=8))


def head(expr, name="KAI"):
    lk = LOOK[name]
    ears = (f'<ellipse cx="-150" cy="10" rx="22" ry="32" fill="{SKIN}" stroke="{INK}" stroke-width="8"/>'
            f'<ellipse cx="150" cy="10" rx="22" ry="32" fill="{SKIN}" stroke="{INK}" stroke-width="8"/>')
    face = f'<ellipse cx="0" cy="0" rx="150" ry="160" fill="{SKIN}" stroke="{INK}" stroke-width="10"/>'
    blush = '<ellipse cx="-95" cy="50" rx="22" ry="12" fill="#f0a08a" opacity=".55"/><ellipse cx="95" cy="50" rx="22" ry="12" fill="#f0a08a" opacity=".55"/>'
    return ears + face + blush + eyes(expr) + mouth(expr) + hair_kai()


def body_peasant(name="KAI", pose="coin"):
    lk = LOOK[name]
    # simple tunic body, rope belt, trousers, wrap shoes
    tunic = _p("M-120 0 Q-130 120 -135 260 L135 260 Q130 120 120 0 Q60 -25 0 -25 Q-60 -25 -120 0 Z", lk["top"], w=10)
    shade = '<path d="M40 -20 Q120 0 125 120 L130 255 L70 255 Q90 120 40 -20 Z" fill="#9f2420" opacity=".55"/>'
    belt = _p("M-132 180 Q0 200 132 180", "none", "#d8b66a", 14) + _p("M-20 192 L-35 240 M-5 194 L5 245", "none", "#d8b66a", 9)
    legs = (_p("M-100 258 L-95 420 L-25 420 L-20 258 Z", lk["legs"], w=9) + _p("M20 258 L25 420 L95 420 L100 258 Z", lk["legs"], w=9))
    shoes = (_p("M-110 415 Q-115 455 -10 455 Q-5 425 -25 415 Z", lk["shoes"], w=9)
             + _p("M110 415 Q115 455 10 455 Q5 425 25 415 Z", lk["shoes"], w=9))
    if pose == "coin":     # left arm raised holding a coin up, right arm at the cheek in shock
        arms = (_p("M-118 20 Q-230 0 -250 -150", "none", INK, 46) + _p("M-118 20 Q-230 0 -250 -150", "none", lk["top"], 30)
                + f'<circle cx="-252" cy="-170" r="30" fill="{SKIN}" stroke="{INK}" stroke-width="8"/>'
                + f'<circle cx="-262" cy="-225" r="30" fill="#f2c94c" stroke="{INK}" stroke-width="8"/>'
                + '<circle cx="-262" cy="-225" r="17" fill="none" stroke="#c99a2e" stroke-width="5"/>'
                + _p("M118 20 Q205 60 175 -110", "none", INK, 46) + _p("M118 20 Q205 60 175 -110", "none", lk["top"], 30)
                + f'<circle cx="170" cy="-125" r="30" fill="{SKIN}" stroke="{INK}" stroke-width="8"/>')
    else:
        arms = (_p("M-118 20 Q-150 120 -140 210", "none", INK, 46) + _p("M-118 20 Q-150 120 -140 210", "none", lk["top"], 30)
                + _p("M118 20 Q150 120 140 210", "none", INK, 46) + _p("M118 20 Q150 120 140 210", "none", lk["top"], 30))
    return legs + shoes + tunic + shade + belt + arms


def character(name, x, y, scale, expr="neutral", pose="stand"):
    """Feet at (x, y)."""
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            f'<ellipse cx="0" cy="455" rx="170" ry="22" fill="#000" opacity=".28"/>'
            f'<g transform="translate(0 -10)">{body_peasant(name, pose)}</g>'
            f'<g transform="translate(0 -170)">{head(expr, name)}</g>'
            f'</g>')


def test(bg, out):
    W, H = 1344, 768
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<image href="{bg}" x="0" y="0" width="{W}" height="{H}"/>'
           f'<rect width="{W}" height="{H}" fill="#2a1406" opacity=".12"/>'
           + character("KAI", 430, 690 - 455 * 0.62, 0.62, "shocked", "coin") +
           f'<radialGradient id="g"><stop offset="0" stop-color="#ffb35a" stop-opacity=".25"/><stop offset="1" stop-color="#ffb35a" stop-opacity="0"/></radialGradient>'
           f'<circle cx="680" cy="560" r="420" fill="url(#g)"/></svg>')
    with open(out + ".svg", "w") as f:
        f.write(svg)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out + ".svg", out], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "test":
        test(sys.argv[2], sys.argv[3])
