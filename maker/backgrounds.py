"""Backgrounds drawn by code, in the same flat style as the cast.

A scene's PLACE text picks a SETTING (village, castle hall, town street...) and PROPS
(cow, fire, roast swan...) by keywords. EXTRAS adds simple background people.
Everything is plain SVG in a 1920x1080 frame. The floor line is where the cast stands.

When a story needs something new, add a setting or prop function here and a keyword for it.
"""
from __future__ import annotations

import math
import random
import re

INK = "#26262b"
LW = 5
W, H = 1920, 1080
FLOOR = 1000          # where feet stand (cast is drawn with feet at this y)


def _p(d, fill, stroke=INK, w=LW, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round"{extra}/>'


def _r(x, y, w, h, fill, rx=0, stroke=INK, sw=LW, extra=""):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def _c(x, y, r, fill, stroke=INK, sw=LW, extra=""):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'


def _e(x, y, rx, ry, fill, stroke=INK, sw=LW, extra=""):
    return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{extra}/>')


def _l(d, colour=INK, w=4):
    return f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def _g(x, y, s, body, flip=False):
    sx = -s if flip else s
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({sx:.3f} {s:.3f})">{body}</g>'


# ---------------------------------------------------------------- sky and light
SKIES = {
    "day": ("#a9d3e8", "#dcecf2"), "sunrise": ("#f2b98a", "#f9e3c4"), "sunset": ("#e6865f", "#f6c58f"),
    "night": ("#1f2740", "#3b4566"), "dusk": ("#7d6c9a", "#e0a98a"), "rain": ("#8d9aa6", "#bcc5cc"),
}


def time_of_day(place: str) -> str:
    p = place.lower()
    if "night" in p:
        return "night"
    if "dusk" in p or "evening" in p:
        return "dusk"
    if "sunset" in p or "late afternoon" in p:
        return "sunset"
    if "sunrise" in p or "dawn" in p or "morning" in p:
        return "sunrise"
    if "rain" in p or "storm" in p:
        return "rain"
    return "day"


def sky(tod):
    top, bottom = SKIES[tod]
    stars = ""
    if tod == "night":
        rnd = random.Random(7)
        stars = "".join(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 420):.0f}" r="{rnd.uniform(1.5, 3):.1f}" '
                        f'fill="#f4efe0" opacity=".8"/>' for _ in range(60))
        stars += _c(1600, 160, 48, "#f1ead2", "#d9d0b4", 4)
    elif tod in ("sunrise", "sunset"):
        stars = f'<circle cx="{1500 if tod == "sunset" else 380}" cy="560" r="110" fill="#ffd98f" opacity=".9"/>'
    elif tod == "day":
        stars = _c(1620, 170, 70, "#ffe08a", "#f2c35b", 4)
    return (f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
            f'<stop offset="1" stop-color="{bottom}"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars)


def light_overlay(tod, indoor):
    if tod == "night":
        return f'<rect width="{W}" height="{H}" fill="#101a3a" opacity="{0.35 if indoor else 0.28}"/>'
    if tod == "dusk":
        return f'<rect width="{W}" height="{H}" fill="#3a2a5a" opacity=".18"/>'
    if tod == "sunset":
        return f'<rect width="{W}" height="{H}" fill="#f08a4b" opacity=".10"/>'
    return ""


# ---------------------------------------------------------------- reusable scenery
def hills(y, colour, seed=1, amp=60):
    rnd = random.Random(seed)
    pts = [(x, y - rnd.uniform(0, amp)) for x in range(-100, W + 300, 300)]
    d = f"M-100 {H} L" + " L".join(f"{x} {yy:.0f}" for x, yy in pts) + f" L{W + 300} {H} Z"
    d = "M-100 " + str(H)
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        d += f" L{x0} {y0:.0f} Q{(x0 + x1) / 2} {min(y0, y1) - 40:.0f} {x1} {y1:.0f}"
    d += f" L{W + 300} {H} Z"
    return f'<path d="{d}" fill="{colour}"/>'


def ground(colour, y=FLOOR - 90, edge=None):
    out = f'<rect x="0" y="{y}" width="{W}" height="{H - y}" fill="{colour}"/>'
    if edge:
        out += f'<rect x="0" y="{y}" width="{W}" height="10" fill="{edge}"/>'
    return out


def tree(x, y, s=1.0):
    return _g(x, y, s, _r(-14, -170, 28, 170, "#6b4e2e") + _c(0, -230, 95, "#5f7f4a") + _c(-55, -190, 60, "#6b8c52")
              + _c(55, -195, 58, "#6b8c52"))


def hut(x, y, s=1.0, door=True):
    body = (_r(-120, -170, 240, 170, "#b08a5a") + _p("M-150 -165 L0 -290 L150 -165 Z", "#c9a95f")
            + _l("M-120 -230 L-60 -255 M120 -230 L60 -255", "#a8873f", 4))
    if door:
        body += _r(-30, -100, 60, 100, "#6b4a2b", 6)
    body += _r(60, -130, 36, 30, "#3b2a1c", 3)
    return _g(x, y, s, body)


def stone_house(x, y, s=1.0, colour="#d7c9ad"):
    body = (_r(-110, -260, 220, 260, colour) + _p("M-130 -255 L0 -340 L130 -255 Z", "#8c5a3c")
            + _r(-60, -210, 40, 50, "#3b2a1c", 3) + _r(20, -210, 40, 50, "#3b2a1c", 3)
            + _r(-30, -100, 60, 100, "#6b4a2b", 6)
            + _l("M-110 -130 L110 -130", "#b8a98d", 4))
    return _g(x, y, s, body)


def timber_house(x, y, s=1.0, colour="#efe3c6"):
    body = (_r(-120, -330, 240, 330, colour) + _p("M-140 -325 L0 -430 L140 -325 Z", "#7a4b33")
            + _l("M-120 -170 L120 -170 M-120 -330 L120 -170 M120 -330 L-120 -170 M-40 -330 L-40 0 M40 -330 L40 0",
                 "#5b3a26", 8)
            + _r(-95, -290, 45, 45, "#3b2a1c", 3) + _r(50, -290, 45, 45, "#3b2a1c", 3)
            + _r(-30, -110, 60, 110, "#6b4a2b", 6))
    return _g(x, y, s, body)


def church(x, y, s=1.0):
    body = (_r(-150, -230, 300, 230, "#cfc3a8") + _p("M-170 -225 L0 -320 L170 -225 Z", "#7d6a55")
            + _r(-240, -420, 110, 420, "#cfc3a8") + _p("M-255 -415 L-185 -520 L-115 -415 Z", "#7d6a55")
            + _p("M-205 -360 Q-185 -390 -165 -360 L-165 -320 L-205 -320 Z", "#3b2a1c")
            + _p("M-30 0 L-30 -90 Q0 -130 30 -90 L30 0 Z", "#6b4a2b"))
    return _g(x, y, s, body)


def castle(x, y, s=1.0):
    def tower(tx, h):
        battl = "".join(_r(tx - 70 + i * 35, -h - 35, 22, 35, "#bdb5a6") for i in range(4))
        return _r(tx - 70, -h, 140, h, "#bdb5a6") + battl + _r(tx - 15, -h + 60, 30, 50, "#3b3b45", 10)
    wall = _r(-300, -260, 600, 260, "#aaa292") + "".join(_r(-300 + i * 50, -295, 30, 35, "#aaa292") for i in range(12))
    gate = _p("M-70 0 L-70 -130 Q0 -200 70 -130 L70 0 Z", "#3b3b45")
    flags = "".join(_l(f"M{fx} {-fh} L{fx} {-fh - 90}", INK, 5) + _p(f"M{fx} {-fh - 90} L{fx + 60} {-fh - 75} L{fx} {-fh - 60} Z", "#b5413a", INK, 4)
                    for fx, fh in ((-300, 455), (300, 455)))
    return _g(x, y, s, wall + tower(-300, 420) + tower(300, 420) + gate + flags)


def stone_wall_bg(colour="#a8a092", mortar="#8f877a"):
    out = f'<rect width="{W}" height="{FLOOR - 80}" fill="{colour}"/>'
    for row in range(0, 14):
        yy = row * 70
        off = 0 if row % 2 else 70
        out += _l(f"M0 {yy} L{W} {yy}", mortar, 3)
        for xx in range(-off, W, 140):
            out += _l(f"M{xx} {yy} L{xx} {yy + 70}", mortar, 3)
    return out


def wood_wall_bg(colour="#9a7550", line="#7d5d3e"):
    out = f'<rect width="{W}" height="{FLOOR - 80}" fill="{colour}"/>'
    for xx in range(0, W, 120):
        out += _l(f"M{xx} 0 L{xx} {FLOOR - 80}", line, 4)
    out += _r(0, 0, W, 60, "#6b4a2b", 0)
    for xx in range(150, W, 420):
        out += _r(xx, 0, 40, FLOOR - 80, "#6b4a2b", 0, INK, 4)
    return out


def floor(colour, y=FLOOR - 80, lines=None):
    out = f'<rect x="0" y="{y}" width="{W}" height="{H - y}" fill="{colour}"/>' + _l(f"M0 {y} L{W} {y}", INK, 5)
    if lines:
        for xx in range(-400, W + 400, 160):
            out += _l(f"M{W / 2 + (xx - W / 2) * 0.4:.0f} {y} L{xx} {H}", lines, 3)
    return out


def straw_floor(y=FLOOR - 80):
    rnd = random.Random(3)
    out = floor("#c9b27a", y)
    for _ in range(90):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(y + 10, H)
        a = rnd.uniform(-0.6, 0.6)
        out += _l(f"M{x0:.0f} {y0:.0f} l{30 * math.cos(a):.0f} {30 * math.sin(a):.0f}", "#a8905a", 3)
    return out


def window(x, y, w=120, h=160, night=False):
    glass = "#1f2740" if night else "#bfe0ef"
    return (_r(x, y, w, h, glass, 6) + _l(f"M{x + w / 2} {y} L{x + w / 2} {y + h} M{x} {y + h / 2} L{x + w} {y + h / 2}", INK, 5))


def arch_window(x, y, w=110, h=200, night=False):
    glass = "#1f2740" if night else "#bfe0ef"
    return _p(f"M{x} {y + h} L{x} {y + w / 2} Q{x + w / 2} {y - w / 3} {x + w} {y + w / 2} L{x + w} {y + h} Z", glass)


# ---------------------------------------------------------------- settings
def set_village(tod, place):
    out = sky(tod) + hills(640, "#9fb48a", 2) + hills(720, "#8ea578", 5)
    out += church(1650, 760, 0.8) if "church" in place else ""
    for x, s in ((200, 0.9), (520, 0.75), (1350, 0.85), (1750, 0.7)):
        out += hut(x, 830, s)
    out += ground("#8c7a5a", 830, "#9e8b67")
    out += f'<path d="M700 {H} Q900 880 960 830 Q1020 880 1220 {H} Z" fill="#7a6a4c"/>'
    return out, False


def set_green(tod, place):
    out = sky(tod) + hills(660, "#9fb48a", 4)
    out += church(1600, 800, 0.9)
    out += hut(250, 800, 0.8) + hut(560, 790, 0.6)
    out += ground("#8ea578", 800, "#9fb48a")
    return out, False


def set_fields(tod, place):
    out = sky(tod) + hills(600, "#a9bb8f", 3, 40)
    if "manor" in place:
        out += stone_house(1560, 640, 0.8, "#d9ceb6")
    out += f'<rect x="0" y="640" width="{W}" height="{H - 640}" fill="#9c8656"/>'
    for i in range(9):   # long strips of land in perspective
        x0 = -300 + i * 300
        col = "#8f7a4c" if i % 2 else "#a89363"
        out += f'<path d="M{960 + (x0 - 960) * 0.15:.0f} 640 L{960 + (x0 + 300 - 960) * 0.15:.0f} 640 L{x0 + 300} {H} L{x0} {H} Z" fill="{col}"/>'
    out += tree(140, 700, 0.6) + tree(1820, 690, 0.5)
    return out, False


def set_mill(tod, place):
    out = sky(tod) + hills(640, "#9fb48a", 6)
    out += ground("#8ea578", 760, "#9fb48a")
    out += f'<path d="M0 860 Q500 820 960 880 T{W} 860 L{W} 960 Q1400 1000 960 950 T0 960 Z" fill="#6f9fbf" stroke="{INK}" stroke-width="5"/>'
    mill = (_r(-180, -330, 360, 330, "#cfc3a8") + _p("M-210 -325 L0 -450 L210 -325 Z", "#7d5a3c")
            + _r(-40, -130, 80, 130, "#6b4a2b", 6) + _r(-130, -260, 60, 60, "#3b2a1c", 3))
    wheel = _c(0, 0, 150, "#8b6a45") + _c(0, 0, 30, "#6b4a2b") + "".join(
        _l(f"M{150 * math.cos(a):.0f} {150 * math.sin(a):.0f} L{-150 * math.cos(a):.0f} {-150 * math.sin(a):.0f}", INK, 6)
        for a in (0, math.pi / 4, math.pi / 2, 3 * math.pi / 4))
    out += _g(1450, 820, 1.0, mill) + _g(1250, 760, 1.0, wheel)
    return out, False


def set_town(tod, place):
    out = sky(tod)
    for x, s, col in ((160, 0.95, "#efe3c6"), (450, 0.8, "#e8d7b5"), (1480, 0.85, "#efe3c6"), (1770, 1.0, "#e3d1ad")):
        out += timber_house(x, 830, s, col)
    out += church(980, 700, 0.55)
    out += ground("#9b8f7d", 830, "#aa9f8c")
    for xx in range(0, W, 90):   # cobbles
        out += _l(f"M{xx} 900 l40 0 M{xx + 45} 960 l40 0 M{xx + 20} 1030 l40 0", "#857a69", 4)
    if "cookshop" in place or "pie" in place:
        out += _g(1480, 830, 0.85, _r(-130, -120, 260, 30, "#b5413a") + _r(-120, -90, 240, 90, "#8b6a45"))
    if "market" in place:
        for mx in (640, 1280):
            out += _g(mx, 830, 0.8, _r(-110, -150, 220, 30, "#c9a95f") + _l("M-100 -120 L-100 0 M100 -120 L100 0", INK, 8)
                      + _r(-110, -60, 220, 60, "#8b6a45"))
    return out, False


def set_gate(tod, place):
    out = sky(tod) + hills(700, "#9fb48a", 8)
    wall = f'<rect x="0" y="380" width="{W}" height="460" fill="#aaa292" stroke="{INK}" stroke-width="5"/>'
    wall += "".join(_r(i * 80, 340, 50, 45, "#aaa292") for i in range(25))
    gate = _p("M760 840 L760 520 Q960 380 1160 520 L1160 840 Z", "#bcd7a8")
    gate += _l("M760 520 Q960 380 1160 520", INK, 6) + hills(840, "#8ea578", 9, 10)
    out += wall + gate + ground("#9b8f7d", 840, "#aa9f8c")
    return out, False


def set_castle_outside(tod, place):
    out = sky(tod) + hills(640, "#9fb48a", 11)
    out += castle(960, 780, 1.1)
    if "moat" in place or "chute" in place or "drawbridge" in place:
        out += f'<rect x="0" y="790" width="{W}" height="90" fill="#6f9fbf" stroke="{INK}" stroke-width="5"/>'
        if "chute" in place:
            out += _p("M1200 420 L1240 420 L1250 790 L1190 790 Z", "#8f877a") + _e(1220, 800, 60, 14, "#6b5a3a", "none")
    out += ground("#8ea578", 880, "#9fb48a")
    return out, False


def set_road(tod, place):
    out = sky(tod) + hills(620, "#a9bb8f", 12) + hills(700, "#9fb48a", 13)
    out += ground("#8ea578", 780, "#9fb48a")
    out += f'<path d="M0 820 L{W} 800 L{W} 940 L0 960 Z" fill="#8c7a5a"/>'
    out += tree(160, 800, 0.7) + tree(1780, 790, 0.6)
    return out, False


def set_tournament(tod, place):
    out = sky(tod) + hills(640, "#9fb48a", 14)
    for x, col in ((260, "#b5413a"), (620, "#3f6e9a"), (1320, "#d6b04a"), (1680, "#2f7f78")):
        out += _g(x, 790, 0.9, _p("M-130 0 L0 -260 L130 0 Z", col) + _p("M-130 0 L0 -260 L-60 0 Z", "#f4efe0", INK, 4)
                  + _l("M0 -260 L0 -320", INK, 5) + _p("M0 -320 L50 -305 L0 -290 Z", col, INK, 3))
    out += ground("#8ea578", 790, "#9fb48a")
    out += _r(0, 860, W, 18, "#8b6a45", 0, INK, 4)   # the tilt barrier
    return out, False


def set_battlefield(tod, place):
    t = "rain" if "rain" in place else tod
    out = sky(t) + hills(640, "#7f8c6c", 15) + hills(720, "#6f7a5c", 16)
    for x in (300, 1650):
        out += _g(x, 800, 0.7, _p("M-130 0 L0 -220 L130 0 Z", "#cfc3a8") + _l("M0 -220 L0 -280", INK, 5)
                  + _p("M0 -280 L60 -262 L0 -244 Z", "#b5413a", INK, 3))
    out += ground("#6b5a3e", 800, "#7a6a4c")
    if t == "rain":
        out += "".join(_l(f"M{x} {y} l-18 46", "#dfe6ea", 3) for x in range(0, W + 40, 70) for y in range(0, 900, 160))
    return out, False


def set_hut_inside(tod, place):
    out = wood_wall_bg("#8b6a48", "#715538")
    out += window(1500, 260, 120, 120, tod == "night")
    out += straw_floor()
    out += f'<path d="M0 0 L{W} 0 L{W} 70 L0 70 Z" fill="#5b4330"/>'
    if "smoke" in place or "fire" in place:
        out += "".join(f'<circle cx="{960 + 40 * math.sin(i)}" cy="{500 - i * 70}" r="{50 + i * 10}" fill="#d8d1c4" opacity="{0.35 - i * 0.05}"/>'
                       for i in range(6))
    return out, True


def set_workshop(tod, place):
    out = wood_wall_bg("#b28e62", "#94744d")
    out += window(240, 230, 220, 200, tod == "night")
    out += "".join(_l(f"M{x} 300 L{x} 380", INK, 5) + _r(x - 14, 380, 28, 40, "#8f877a", 4) for x in (1300, 1380, 1460, 1540))
    out += _r(1260, 290, 320, 14, "#6b4a2b", 0, INK, 4)
    out += floor("#8a6a48", lines="#755a3c")
    return out, True


def set_hall(tod, place):
    out = stone_wall_bg("#b3aa98", "#988f7f")
    for x in (260, 1560):
        out += arch_window(x, 220, 110, 230, tod == "night")
    for x, col in ((560, "#b5413a"), (1300, "#3f6e9a")):
        out += _p(f"M{x} 80 L{x + 120} 80 L{x + 120} 420 L{x + 60} 380 L{x} 420 Z", col)
        out += _l(f"M{x + 30} 150 L{x + 90} 150 M{x + 60} 150 L{x + 60} 300", "#d6b04a", 8)
    out += floor("#8f877a", lines="#7a7366")
    return out, True


def set_guild(tod, place):
    out = wood_wall_bg("#8a5f3e", "#6e4b31")
    for x in (380, 1420):
        out += arch_window(x, 200, 120, 240, tod == "night")
    out += f'<rect x="0" y="0" width="{W}" height="40" fill="#5b3a26"/>'
    out += floor("#7a5a3e", lines="#664a33")
    return out, True


def set_stone_room(tod, place):
    out = stone_wall_bg("#9f9686", "#877e70")
    out += arch_window(900, 200, 120, 220, tod == "night")
    if "millstone" in place or "paved" in place:
        out += floor("#8f877a")
        for i in range(30):
            cx = 120 + (i % 10) * 190 + (40 if (i // 10) % 2 else 0)
            cy = FLOOR - 40 + (i // 10) * 45
            out += _e(cx, cy, 80, 18, "#bdb5a6", INK, 4) + _e(cx, cy, 14, 4, "#6b6358", "none")
    else:
        out += floor("#8f877a", lines="#7a7366")
    return out, True


def set_garderobe(tod, place):
    out = stone_wall_bg("#9f9686", "#877e70")
    out += arch_window(1450, 260, 70, 140, tod == "night")
    seat = _r(-200, -170, 400, 170, "#aaa292") + _e(0, -170, 70, 18, "#3b3b45", INK, 5)
    out += floor("#8f877a") + _g(560, FLOOR - 30, 1.0, seat)
    return out, True


def set_tent(tod, place):
    out = f'<rect width="{W}" height="{H}" fill="#d9c7a0"/>'
    for x in range(-200, W + 200, 240):
        out += f'<path d="M960 -200 L{x} {FLOOR - 80} L{x + 120} {FLOOR - 80} Z" fill="#cdb98f"/>'
        out += _l(f"M960 -200 L{x} {FLOOR - 80}", "#b5a27a", 5)
    out += floor("#9c8656")
    return out, True


def set_bedroom(tod, place):
    out = stone_wall_bg("#b3aa98", "#988f7f")
    out += arch_window(260, 240, 110, 220, tod == "night")
    out += floor("#8f877a", lines="#7a7366")
    bed = (_r(-260, -150, 520, 150, "#7d4b33") + _r(-240, -190, 480, 60, "#efe3c6", 14)
           + _r(-280, -420, 30, 420, "#5b3a26") + _r(250, -420, 30, 420, "#5b3a26")
           + _r(-290, -440, 580, 40, "#b5413a") + _p("M-250 -400 Q-200 -250 -250 -150 L-250 -400 Z", "#b5413a"))
    out += _g(1450, FLOOR - 20, 0.95, bed)
    return out, True


def set_courtyard(tod, place):
    out = sky(tod)
    out += f'<rect x="0" y="260" width="{W}" height="600" fill="#aaa292" stroke="{INK}" stroke-width="5"/>'
    out += "".join(_r(i * 80, 220, 50, 45, "#aaa292") for i in range(25))
    out += "".join(arch_window(x, 420, 90, 160, tod == "night") for x in (300, 700, 1150, 1550))
    out += ground("#9b8f7d", 860, "#aa9f8c")
    return out, False


def set_plain(tod, place):
    return sky(tod) + hills(700, "#9fb48a", 20) + ground("#8ea578", 820, "#9fb48a"), False


# (keywords, setting). The first match wins, so more specific ones come first.
SETTINGS = [
    (("castle toilet", "stone seat with a hole", "tiny stone room"), set_garderobe),
    (("chute", "outside of a castle", "castle wall"), set_castle_outside),
    (("great hall", "throne room"), set_hall),
    (("bedroom", "bed with curtains"), set_bedroom),
    (("castle room", "stone castle room", "cold stone"), set_hall),
    (("courtyard",), set_courtyard),
    (("castle", "drawbridge", "moat"), set_castle_outside),
    (("abbey", "monastery", "stone room"), set_stone_room),
    (("guild hall",), set_guild),
    (("workshop", "craftsman's house", "shop at the front"), set_workshop),
    (("tent",), set_tent),
    (("tournament",), set_tournament),
    (("battlefield", "battle", "camp"), set_battlefield),
    (("inside", "interior"), set_hut_inside),
    (("town gate", "city gate", "gate"), set_gate),
    (("town", "street", "cookshop", "city"), set_town),
    (("watermill", "mill", "river"), set_mill),
    (("village green", "green", "market"), set_green),
    (("field", "fields", "farm", "plough"), set_fields),
    (("village", "mud road", "path"), set_village),
    (("road", "carts"), set_road),
]


def _has(text: str, key: str) -> bool:
    """Whole-word match ("ox" must not match "box")."""
    return re.search(r"(?<![a-z])" + re.escape(key.strip()) + r"(?![a-z])", text) is not None


def pick_setting(place: str):
    p = place.lower()
    for keys, fn in SETTINGS:
        if any(_has(p, k) for k in keys):
            return fn
    return set_plain


# ---------------------------------------------------------------- props
def p_cow(s=1.0):
    body = (_e(0, -150, 170, 85, "#f4efe0") + _e(-60, -170, 50, 35, "#3b3b45", "none") + _e(70, -130, 40, 28, "#3b3b45", "none")
            + _e(0, -150, 170, 85, "none") + "".join(_r(x, -90, 26, 90, "#f4efe0") for x in (-130, -80, 70, 120))
            + _e(185, -200, 60, 48, "#f4efe0") + _e(215, -185, 30, 22, "#e8b4a8") + _c(178, -215, 6, INK, "none")
            + _l("M160 -245 l-20 -30 M205 -245 l15 -30", INK, 6) + _l("M-170 -160 q-40 20 -30 70", INK, 5))
    return body


def p_pig():
    return (_e(0, -60, 90, 55, "#f0b6a8") + "".join(_r(x, -25, 20, 25, "#f0b6a8") for x in (-60, -20, 25, 55))
            + _e(95, -70, 28, 22, "#e89c8c") + _c(88, -72, 4, INK, "none") + _c(100, -72, 4, INK, "none")
            + _c(70, -90, 5, INK, "none") + _l("M-90 -70 q-25 -10 -15 -30", INK, 4))


def p_chicken():
    return (_e(0, -40, 32, 26, "#f4efe0") + _c(26, -66, 16, "#f4efe0") + _p("M40 -68 L56 -63 L40 -58 Z", "#e8a33a", INK, 3)
            + _p("M20 -82 l5 -12 l5 12 Z", "#c0392b", INK, 3) + _l("M-6 -14 L-10 0 M6 -14 L4 0", "#e8a33a", 4))


def p_goat():
    return (_e(0, -80, 80, 45, "#e8e2d4") + "".join(_r(x, -45, 16, 45, "#e8e2d4") for x in (-55, -25, 25, 50))
            + _e(85, -120, 32, 26, "#e8e2d4") + _l("M75 -142 q-10 -30 -30 -35 M92 -142 q0 -30 -15 -40", "#8b6a45", 6)
            + _c(92, -124, 4, INK, "none") + _l("M100 -100 l4 18", INK, 4))


def p_horse():
    body = (_e(0, -230, 190, 90, "#6b4a2b") + "".join(_r(x, -150, 30, 150, "#6b4a2b") for x in (-150, -100, 80, 130))
            + _p("M150 -270 L230 -420 L300 -400 L240 -250 Z", "#6b4a2b") + _e(275, -410, 55, 35, "#6b4a2b")
            + _c(270, -425, 7, INK, "none") + _p("M200 -400 L170 -300 L220 -290 L235 -390 Z", "#2f2219", INK, 3)
            + _l("M-190 -240 q-60 40 -40 140", "#2f2219", 14) + _r(-60, -320, 150, 60, "#b5413a", 10))
    return body


def p_oxen():
    one = (_e(0, -110, 120, 62, "#8b6a45") + "".join(_r(x, -60, 22, 60, "#8b6a45") for x in (-90, -55, 45, 80))
           + _e(125, -140, 42, 36, "#8b6a45") + _l("M110 -170 q-20 -30 -45 -25 M140 -170 q20 -30 45 -25", "#e8e2d4", 7)
           + _c(130, -145, 5, INK, "none"))
    return "".join(_g(i * -150, -i * 16, 1 - i * 0.12, one) for i in range(3, -1, -1))


def p_fire():
    return (_e(0, -10, 90, 22, "#5a5148") + "".join(_r(-70 + i * 35, -30, 30, 20, "#6b4a2b", 4) for i in range(4))
            + _p("M-55 -30 Q-60 -110 -10 -160 Q-20 -100 15 -90 Q20 -140 50 -170 Q80 -90 55 -30 Z", "#f28b2c", "#c45a1c", 4)
            + _p("M-25 -32 Q-25 -80 5 -110 Q10 -70 30 -60 Q45 -50 30 -32 Z", "#ffd25c", "none"))


def p_table(w=520):
    return (_r(-w / 2, -150, w, 28, "#8b6a45") + _r(-w / 2 + 20, -122, 26, 122, "#6b4a2b") + _r(w / 2 - 46, -122, 26, 122, "#6b4a2b"))


def p_long_table():
    return p_table(1100) + _r(-520, -152, 1040, 8, "#efe3c6", 0, "none")


def p_bread():
    return _e(0, -26, 52, 30, "#7a5230") + _l("M-25 -40 q10 -6 20 0 M5 -42 q10 -6 20 0", "#5b3a20", 4)


def p_jug():
    return (_p("M-30 0 L-40 -70 Q-40 -100 -20 -110 L-20 -130 L20 -130 L20 -110 Q40 -100 40 -70 L30 0 Z", "#b07a4a")
            + _l("M38 -100 q30 10 10 50", INK, 6))


def p_bucket():
    return _p("M-45 0 L-55 -90 L55 -90 L45 0 Z", "#8b6a45") + _l("M-55 -60 L55 -60 M-50 -25 L50 -25", INK, 4) + _e(0, -90, 55, 12, "#6f9fbf")


def p_pot():
    return (_e(0, -60, 80, 60, "#4a4440") + _e(0, -110, 70, 14, "#c9a95f") + _l("M-60 -110 q0 -60 60 -60 q60 0 60 60", INK, 4)
            + _l("M-20 -160 q10 -30 0 -50 M20 -160 q10 -30 0 -50", "#d8d1c4", 5))


def p_bowl():
    return _p("M-40 -30 Q0 10 40 -30 Z", "#8b6a45")


def p_throne():
    return (_r(-110, -420, 220, 420, "#d6b04a", 16) + _r(-80, -380, 160, 220, "#b5413a", 10)
            + _r(-140, -200, 280, 60, "#c9a043", 10) + _c(0, -440, 28, "#d6b04a") + _r(-110, -60, 220, 60, "#b8902f", 6))


def p_swan():
    return (_e(0, -40, 160, 40, "#c9a95f") + _e(0, -62, 110, 40, "#f4efe0") + _l("M80 -80 q60 -40 40 -120 q-10 -30 -40 -10", "#f4efe0", 18)
            + _l("M80 -80 q60 -40 40 -120 q-10 -30 -40 -10", INK, 4) + _p("M82 -212 L56 -200 L80 -194 Z", "#e8a33a", INK, 3))


def p_peacock():
    tail = "".join(_p(f"M0 -60 L{150 * math.cos(a):.0f} {-60 - 150 * math.sin(a):.0f} L{165 * math.cos(a + 0.12):.0f} {-60 - 165 * math.sin(a + 0.12):.0f} Z",
                      "#2f7f78", INK, 3) + _c(150 * math.cos(a + 0.06), -60 - 150 * math.sin(a + 0.06), 12, "#3f6e9a", "#d6b04a", 3)
                   for a in [math.pi * (0.1 + 0.1 * i) for i in range(9)])
    return (_e(0, -30, 150, 36, "#c9a95f") + tail + _e(0, -70, 60, 40, "#3f6e9a") + _l("M40 -90 q20 -50 0 -90", "#3f6e9a", 16)
            + _c(2, -182, 16, "#3f6e9a") + _l("M0 -198 l-6 -16 M6 -198 l6 -16", INK, 3))


def p_pie():
    return _e(0, -20, 60, 22, "#d9a35a") + _p("M-60 -22 Q0 -70 60 -22 Z", "#e8b46a") + _l("M-20 -40 l10 6 M10 -46 l10 6", "#a0703a", 3)


def p_tapestry():
    return (_r(-160, -560, 320, 420, "#7d3a3a") + _r(-140, -540, 280, 380, "#a8543f", 0, "#d6b04a", 6)
            + _c(0, -350, 70, "#d6b04a") + _l("M-60 -350 L60 -350 M0 -410 L0 -290", "#7d3a3a", 10) + _l("M-180 -560 L180 -560", "#5b3a26", 14))


def p_candles():
    return "".join(_r(x - 10, -90, 20, 90, "#efe3c6", 4) + _p(f"M{x} -92 q-12 -16 0 -34 q12 18 0 34 Z", "#ffd25c", "#f28b2c", 3)
                   for x in (-40, 0, 40))


def p_coins():
    return "".join(_e(x, -12 - (i % 2) * 8, 22, 9, "#d6b04a", INK, 3) for i, x in enumerate((-40, -10, 20, 45)))


def p_eggs():
    return _p("M-60 -10 Q0 30 60 -10 L50 -40 L-50 -40 Z", "#8b6a45") + "".join(_e(x, -48, 16, 20, "#f4efe0", INK, 3) for x in (-28, 0, 28))


def p_scroll():
    return _r(-70, -200, 140, 190, "#efe3c6", 6) + "".join(_l(f"M-45 {y} L45 {y}", "#8f877a", 4) for y in range(-170, -40, 22))


def p_plough():
    return (_l("M-200 -40 L120 -110", "#6b4a2b", 16) + _l("M-200 -40 L120 -110", INK, 3) + _p("M100 -120 L180 -20 L120 -10 Z", "#8f877a")
            + _l("M-200 -40 L-240 -160 M-200 -40 L-160 -150", "#6b4a2b", 10))


def p_barrel():
    return (_p("M-70 0 Q-90 -100 -70 -200 L70 -200 Q90 -100 70 0 Z", "#9a6b3e") + _l("M-80 -50 Q0 -40 80 -50 M-80 -150 Q0 -160 80 -150", "#5a5148", 8)
            + _e(0, -200, 70, 14, "#7d5530"))


def p_sacks():
    return "".join(_g(x, 0, s, _p("M-60 0 Q-70 -80 -30 -120 L30 -120 Q70 -80 60 0 Z", "#d9c7a0") + _l("M-30 -120 q30 -20 60 0", "#8b6a45", 5))
                   for x, s in ((-70, 1.0), (60, 0.85)))


def p_chainmail_stand():
    mail = (_p("M-80 -380 L80 -380 L110 -330 L90 -150 L-90 -150 L-110 -330 Z", "#9aa0a6")
            + "".join(_l(f"M{-85 + j * 3} {y} q8 -6 16 0 q8 6 16 0 q8 -6 16 0 q8 6 16 0 q8 -6 16 0 q8 6 16 0 q8 -6 16 0 q8 6 16 0 q8 -6 16 0 q8 6 16 0",
                             "#6f757b", 3) for j, y in enumerate(range(-350, -160, 22))))
    return _l("M0 -390 L0 0 M-60 0 L60 0", "#6b4a2b", 12) + mail


def p_padded_jacket():
    return (_l("M0 -390 L0 0 M-60 0 L60 0", "#6b4a2b", 12) + _p("M-80 -380 L80 -380 L100 -150 L-100 -150 Z", "#d9c7a0")
            + "".join(_l(f"M{x} -370 L{x} -160", "#b5a27a", 4) for x in (-50, -20, 10, 40)))


def p_sword_rack():
    swords = "".join(_l(f"M{x} -40 L{x} -300", "#c9ced3", 10) + _l(f"M{x - 30} -80 L{x + 30} -80", "#8b6a45", 9) for x in (-70, 0, 70))
    return _r(-130, -60, 260, 24, "#6b4a2b") + _r(-130, -20, 260, 20, "#6b4a2b") + swords


def p_shield():
    return _p("M-60 -200 L60 -200 L60 -110 Q60 -30 0 0 Q-60 -30 -60 -110 Z", "#3f6e9a") + _l("M0 -190 L0 -20 M-50 -130 L50 -130", "#d6b04a", 10)


def p_lances():
    return "".join(_l(f"M{x} 0 L{x + 60} -420", "#c9a95f", 12) for x in (-40, 0, 40))


def p_cart():
    wheel = lambda x: _c(x, -60, 60, "#8b6a45") + _c(x, -60, 12, "#6b4a2b") + _l(f"M{x - 60} -60 L{x + 60} -60 M{x} -120 L{x} 0", INK, 5)
    return _r(-180, -200, 360, 110, "#9a7550") + wheel(-110) + wheel(110) + _l("M180 -150 L300 -120", "#6b4a2b", 10)


def p_carts():
    return _g(-260, 0, 0.8, p_cart()) + _g(220, 0, 0.9, p_cart() + _r(-120, -300, 120, 100, "#7d4b33") + _r(10, -280, 140, 80, "#b5413a"))


def p_straw_beds():
    return "".join(_e(x, -18, 130, 26, "#d9c27a") + _l(f"M{x - 100} -22 l40 -6 M{x - 20} -26 l50 4 M{x + 50} -20 l40 -8", "#a8905a", 4)
                   for x in (-300, 0, 300))


def p_spices():
    return _r(-60, -80, 120, 80, "#d6b04a", 8) + _p("M-60 -80 L-40 -110 L80 -110 L60 -80 Z", "#e8c35a") + _c(-20, -96, 6, "#b5413a", "none") + _c(20, -96, 6, "#6b4a2b", "none")


def p_crown():
    return _r(-90, -40, 180, 40, "#b5413a", 10) + _p("M-70 -40 L-70 -110 L-35 -70 L0 -125 L35 -70 L70 -110 L70 -40 Z", "#d6b04a") + _c(0, -90, 9, "#b5413a", INK, 3)


def p_cup():
    return _p("M-25 -90 L25 -90 L15 -40 L-15 -40 Z", "#d6b04a") + _l("M0 -40 L0 -10 M-20 -8 L20 -8", INK, 8)


def p_scale():
    return (_l("M0 0 L0 -160 M-90 -160 L90 -160", "#8b6a45", 10) + _p("M-120 -100 Q-90 -70 -60 -100 Z", "#d6b04a")
            + _p("M60 -100 Q90 -70 120 -100 Z", "#d6b04a") + _l("M-90 -160 L-115 -100 M-90 -160 L-65 -100 M90 -160 L65 -100 M90 -160 L115 -100", INK, 3)
            + _e(-90, -112, 34, 18, "#7a5230", INK, 3))


def p_doctor_jar():
    return _p("M-35 0 L-35 -80 Q-35 -100 -15 -110 L-15 -125 L15 -125 L15 -110 Q35 -100 35 -80 L35 0 Z", "#bfe0ef") + _e(0, -40, 26, 30, "#b5413a", "none", 0, ' opacity=".7"')


def p_toilet():
    """Castle toilet: a stone seat with a dark hole, seen from the front."""
    return (_r(-170, -150, 340, 150, "#aaa292") + _e(0, -150, 120, 30, "#9b937f") + _e(0, -152, 70, 18, "#1c1c22", INK, 5)
            + _l("M-150 -100 L150 -100", "#8f877a", 4))


def p_banner():
    return _l("M0 0 L0 -500", "#6b4a2b", 10) + _p("M0 -500 L160 -470 L0 -430 Z", "#b5413a")


PROPS = [
    # (keywords, function, where, size): where = floor-left / floor-right / floor-back / table / wall-left / wall-right / centre-back
    (("cow", "heater"), p_cow, "floor-right", 0.95),
    (("pig",), p_pig, "floor-left", 1.0),
    (("chicken", "chickens", "hens"), p_chicken, "floor-left", 1.1),
    (("goat",), p_goat, "floor-left", 1.0),
    (("oxen", "ox"), p_oxen, "floor-back", 0.9),
    (("warhorse", "horse"), p_horse, "floor-right", 0.85),
    (("fire pit", "fire", "campfire"), p_fire, "floor-centre", 1.0),
    (("long table",), p_long_table, "table-long", 1.0),
    (("table", "counter"), p_table, "table", 1.0),
    (("throne",), p_throne, "centre-back", 1.0),
    (("swan",), p_swan, "on-table", 0.9),
    (("peacock",), p_peacock, "on-table", 0.9),
    (("bread", "loaf"), p_bread, "on-table", 1.2),
    (("pie", "pies"), p_pie, "on-table", 1.3),
    (("jug",), p_jug, "on-table", 1.0),
    (("clay pot", "pot of", "pottage", "cooking pot"), p_pot, "floor-centre", 1.0),
    (("bowl",), p_bowl, "on-table", 1.2),
    (("bucket",), p_bucket, "floor-left", 1.0),
    (("tapestry",), p_tapestry, "wall-left", 1.0),
    (("candle", "candles"), p_candles, "on-table", 1.1),
    (("coins", "coin"), p_coins, "on-table", 1.3),
    (("eggs",), p_eggs, "on-table", 1.1),
    (("list", "scroll", "rules"), p_scroll, "on-table", 0.8),
    (("plough",), p_plough, "floor-left", 1.0),
    (("barrel",), p_barrel, "floor-left", 1.0),
    (("grain",), p_sacks, "floor-left", 1.0),
    (("padded jacket",), p_padded_jacket, "floor-left", 1.0),
    (("chainmail on", "shirt of chainmail", "next to the chainmail"), p_chainmail_stand, "floor-right", 1.0),
    (("rack of swords", "swords"), p_sword_rack, "floor-left", 1.0),
    (("shield",), p_shield, "floor-left", 1.0),
    (("lance", "lances"), p_lances, "floor-right", 1.0),
    (("carts", "cart"), p_carts, "floor-back", 0.8),
    (("straw beds", "straw bed", "sleeping corner"), p_straw_beds, "floor-front", 1.0),
    (("sacks", "sack"), p_sacks, "floor-left", 1.0),
    (("spices", "golden box", "pepper"), p_spices, "on-table", 1.1),
    (("crown",), p_crown, "on-table", 1.0),
    (("cup",), p_cup, "on-table", 1.0),
    (("scale",), p_scale, "on-table", 1.0),
    (("jar",), p_doctor_jar, "on-table", 1.0),
    (("flag", "banner"), p_banner, "floor-back-left", 1.0),
    (("toilet", "toilet hole", "stone seat"), p_toilet, "floor-left", 1.0),
]


def pick_props(place: str):
    p = place.lower()
    found, used = [], set()
    for keys, fn, where, size in PROPS:
        if any(_has(p, k) for k in keys) and fn not in used:
            if fn is p_table and p_long_table in used:
                continue
            found.append((fn, where, size))
            used.add(fn)
    return found


def place_props(props, cast_xs):
    """Lay props out around the cast. Returns (behind_svg, front_svg)."""
    behind, front = [], []
    has_table = next(((fn, w) for fn, w, s in props if w in ("table", "table-long")), None)
    table_y = FLOOR - 130
    if has_table:
        fn, w = has_table
        if w == "table-long":
            behind.append(_g(960, table_y + 150, 1.0, fn()))
        else:
            behind.append(_g(960, table_y + 150, 1.0, fn()))
    on_table = [(fn, s) for fn, w, s in props if w == "on-table"]
    if on_table and not has_table:   # food etc. with no table mentioned: put a small table in
        behind.append(_g(960, table_y + 150, 1.0, p_table(560)))
        has_table = (p_table, "table")
    for i, (fn, s) in enumerate(on_table):
        x = 960 + (i - (len(on_table) - 1) / 2) * 200
        behind.append(_g(x, table_y + 4, s, fn()))
    candidates = {"floor-left": [200, 360, 120, 520], "floor-right": [1720, 1560, 1800, 1400],
                  "floor-back": [960, 1650, 270], "centre-back": [960, 1650, 270], "floor-back-left": [120, 300],
                  "floor-centre": [760, 1160, 960, 330, 1600], "floor-front": [960], "wall-left": [330, 1590, 960],
                  "wall-right": [1590, 330, 960]}
    used_x = []

    def choose(where):
        need_gap = 150 if where in ("wall-left", "wall-right", "floor-back", "centre-back", "floor-front") else 230
        for x in candidates.get(where, [960]):
            if all(abs(x - cx) >= need_gap for cx in cast_xs) and all(abs(x - ux) >= 220 for ux in used_x):
                return x
        for x in candidates.get(where, [960]):
            if all(abs(x - ux) >= 220 for ux in used_x):
                return x
        return candidates.get(where, [960])[0]

    for fn, where, s in props:
        if where in ("table", "table-long", "on-table"):
            continue
        x = choose(where)
        used_x.append(x)
        flip = x > 960     # props are drawn facing right; on the right side they turn to face the middle
        if where in ("wall-left", "wall-right"):
            behind.append(_g(x, FLOOR - 80, s, fn()))
        elif where in ("floor-back", "centre-back", "floor-back-left"):
            behind.append(_g(x, FLOOR - 70, s * 0.9, fn(), flip=flip))
        elif where == "floor-front":
            front.append(_g(x, H + 10, s, fn()))
        elif where == "floor-centre":
            behind.append(_g(x, FLOOR - 10, s * 0.85, fn()))
        else:
            behind.append(_g(x, FLOOR - 40, s, fn(), flip=flip))
    return "".join(behind), "".join(front)


# ---------------------------------------------------------------- extras (background people)
EXTRA_TOPS = ["#7d6a55", "#5f7f4a", "#8c5a3c", "#6a6f8a", "#9a7550", "#7a4b5e", "#b08a5a", "#55606b"]
EXTRA_SKIN = ["#e8b894", "#c98d63", "#b98060", "#e2ae86", "#a06e4e", "#f0c7a4"]


def extra_person(rnd, kind="peasant"):
    top = rnd.choice(EXTRA_TOPS)
    skin = rnd.choice(EXTRA_SKIN)
    hat = ""
    robe_len = -200
    if kind in ("noble", "official", "master"):
        top = rnd.choice(["#7d3a3a", "#3f4c63", "#2f5a4a", "#5b3a5e"])
        hat = _p("M-40 -440 Q0 -490 40 -440 L46 -425 L-46 -425 Z", "#26262b", INK, 4)
        robe_len = -40
    elif kind in ("soldier", "knight", "guard"):
        top = "#9aa0a6"
        hat = _p("M-42 -420 Q-44 -490 0 -492 Q44 -490 42 -420 Z", "#8f969c", INK, 4)
    elif kind == "monk":
        top = "#6b5a46"
        robe_len = -20
        hat = _p("M-48 -400 Q-50 -500 0 -500 Q50 -500 48 -400 Q0 -430 -48 -400 Z", "#5a4a38", INK, 4)
    elif rnd.random() < 0.4:
        hat = _p("M-46 -430 Q0 -480 46 -430 L50 -418 L-50 -418 Z", "#8b6a45", INK, 4)
    legs = _l("M-18 -200 L-22 0 M18 -200 L22 0", "#4a4440", 24) if robe_len < -100 else ""
    body = (legs + _p(f"M-52 -380 Q-60 -300 -58 {robe_len} L58 {robe_len} Q60 -300 52 -380 Q0 -400 -52 -380 Z", top)
            + _l("M-52 -370 L-70 -230 M52 -370 L70 -230", top, 22) + _l("M-52 -370 L-70 -230 M52 -370 L70 -230", INK, 2)
            + _e(0, -440, 40, 48, skin, INK, 4) + _c(-14, -444, 4, INK, "none") + _c(14, -444, 4, INK, "none")
            + _l("M-10 -418 q10 6 20 0", INK, 3) + hat)
    return body


def extras(text: str, seed: int, cast_xs):
    """Background people behind the cast, smaller and a little faded for depth."""
    if not text:
        return ""
    t = text.lower()
    kind = ("soldier" if any(k in t for k in ("soldier", "knight", "guard", "squire")) else
            "monk" if "monk" in t else
            "official" if any(k in t for k in ("official", "master", "noble", "guild")) else "peasant")
    if any(k in t for k in ("crowd", "villagers", "shoppers", "cheering", "people", "servants", "guild masters", "soldiers")):
        n = 7
    elif any(k in t for k in ("boy", "apprentice", "page")):
        n = 1
    else:
        n = 3
    rnd = random.Random(seed)
    xs = [rnd.uniform(120, W - 120) for _ in range(n * 3)]
    xs = [x for x in xs if all(abs(x - cx) > 170 for cx in cast_xs)][:n] or xs[:n]
    out = []
    for x in sorted(xs, key=lambda _: rnd.random()):
        s = rnd.uniform(0.5, 0.62)
        if any(k in t for k in ("boy", "page", "kids")):
            s *= 0.75
        out.append(f'<g opacity=".92">{_g(x, FLOOR - 70 - rnd.uniform(0, 25), s, extra_person(rnd, kind), flip=rnd.random() < 0.5)}</g>')
    return "".join(out)


# ---------------------------------------------------------------- the whole background
def build(place: str, extras_text: str = "", seed: int = 0, cast_xs=()):
    """Returns (behind_cast_svg, in_front_of_cast_svg, overlay_svg)."""
    tod = time_of_day(place)
    setting = pick_setting(place)
    base, indoor = setting(tod, place.lower())
    behind_props, front_props = place_props(pick_props(place), cast_xs)
    people = extras(extras_text, seed, cast_xs)
    return base + people + behind_props, front_props, light_overlay(tod, indoor)
