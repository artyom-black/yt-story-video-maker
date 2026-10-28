"""Side (profile) view of the cast, for running and walking.

Same characters, same colours, same hair and clothes as the front view in characters.py,
just turned 90 degrees. Facing right by default; flip=True faces left.

Angles here mean: 0 = straight down, positive = forward (towards where they face).
"""
from __future__ import annotations

import math

from .characters import CAST, EXPRESSIONS, INK, LW, MOUTH, _limb, _line

HIP_Y, SHOULDER_Y = -255, -478


def _shade(hex_colour, f=0.78):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def _fwd(x, y, angle, length):
    a = math.radians(angle)
    return x + length * math.sin(a), y + length * math.cos(a)


def _arm(c, upper, fore, back=False):
    sx, sy = (-4 if back else 2), SHOULDER_Y
    ex, ey = _fwd(sx, sy, upper, 100)
    hx, hy = _fwd(ex, ey, fore, 92)
    ux, uy = _fwd(hx, hy, fore, 9)
    sleeve = _shade(c["top"]) if back else c["top"]
    skin = _shade(c["skin"], 0.88) if back else c["skin"]
    return (_limb([(sx, sy), (ex, ey), (hx, hy)], sleeve, 30)
            + f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="13" fill="{skin}" stroke="{INK}" stroke-width="{LW}"/>')


def _leg(c, thigh, shin, drop, back=False):
    hx, hy = 0, HIP_Y + drop
    kx, ky = _fwd(hx, hy, thigh, 112)
    fx, fy = _fwd(kx, ky, shin, 113)
    pants = _shade(c["pants"]) if back else c["pants"]
    shoes = _shade(c["shoes"]) if back else c["shoes"]
    # the shoe follows the shin a little, so a lifted foot points down naturally
    tip = math.radians((shin - 0) * 0.5)
    tx, ty = fx + 52 * math.cos(tip), fy + 52 * math.sin(tip) * 0.3
    shoe = (f'<path d="M{fx - 18:.1f} {fy - 10:.1f} L{fx + 22:.1f} {fy - 10:.1f} '
            f'Q{tx + 4:.1f} {ty - 2:.1f} {tx:.1f} {ty + 14:.1f} L{fx - 20:.1f} {fy + 20:.1f} Z" '
            f'fill="{shoes}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
    return _limb([(hx, hy), (kx, ky), (fx, fy - 4)], pants, 40) + shoe


# ---------------------------------------------------------------- profile faces
def _eye(kind, x, y):
    if kind == "wide":
        return (f'<circle cx="{x}" cy="{y}" r="10" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                f'<circle cx="{x + 3}" cy="{y + 1}" r="5" fill="{INK}"/>')
    if kind == "happy":
        return _line(f"M{x - 7} {y + 3} Q{x} {y - 6} {x + 7} {y + 3}", 4.5)
    if kind == "squint":
        return _line(f"M{x - 7} {y} L{x + 7} {y}", 4.5)
    return f'<ellipse cx="{x}" cy="{y}" rx="5" ry="7.5" fill="{INK}"/>'


def _brow(kind, x, y):
    d = {"up": (-8, -13, -5), "angry": (-6, 0, 6), "worried": (5, -4, -8)}.get(kind, (0, -6, 1))
    # drawn from the back of the brow (x - 10) to the front (x + 10)
    return _line(f"M{x - 11} {y + d[2]} Q{x} {y + d[1]} {x + 11} {y + d[0]}", 4.5)


def _mouth(kind, x, y, beard=False):
    dark = f'fill="{MOUTH}" stroke="{INK}" stroke-width="3.5"'
    if kind in ("O", "talk", "small-o"):
        r = {"O": (6, 10), "talk": (7, 6), "small-o": (4, 5)}[kind]
        return f'<ellipse cx="{x + 4}" cy="{y + 1}" rx="{r[0]}" ry="{r[1]}" {dark}/>'
    if kind == "grin":
        return (f'<path d="M{x - 8} {y - 3} Q{x + 6} {y + 14} {x + 14} {y - 4} Z" {dark}/>'
                f'<path d="M{x - 6} {y - 2} L{x + 12} {y - 3} L{x + 10} {y + 2} L{x - 4} {y + 2} Z" fill="#fff"/>')
    w = 5 if beard else 4
    shapes = {"smile": f"M{x - 8} {y - 2} Q{x + 4} {y + 6} {x + 14} {y - 3}",
              "frown": f"M{x - 8} {y + 5} Q{x + 4} {y - 3} {x + 14} {y + 6}",
              "smirk": f"M{x - 8} {y + 1} Q{x + 6} {y + 3} {x + 14} {y - 6}"}
    return _line(shapes.get(kind, f"M{x - 6} {y + 1} L{x + 13} {y + 1}"), w)


def _profile_head(name, c, expression, talking):
    eyes, brows, mouth = EXPRESSIONS[expression]
    mouth = "talk" if talking else (mouth or c["mouth"])
    s = c["skin"]
    ear = (f'<path d="M-10 -592 Q-30 -594 -28 -576 Q-28 -560 -10 -562" fill="{_shade(s, 0.9)}" stroke="{INK}" '
           f'stroke-width="4" stroke-linejoin="round"/>' + _line("M-14 -584 Q-22 -580 -16 -570", 3))
    skull = f'<ellipse cx="4" cy="-578" rx="54" ry="65" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
    nose = (f'<path d="M54 -598 L70 -570 Q66 -563 55 -563" fill="{s}" stroke="{INK}" stroke-width="{LW}" '
            f'stroke-linejoin="round"/><path d="M52 -598 L52 -562" stroke="{s}" stroke-width="8"/>')
    eye_y, brow_y, mouth_y = -584, -604, -545
    brow_kind = brows or ("up" if name == "KAI" else None)

    if name == "KAI":
        back = ""
        hair = (f'<path d="M-50 -556 Q-64 -650 2 -654 Q52 -654 58 -604 Q44 -622 24 -614 L18 -632 '
                f'L4 -610 L-10 -634 L-22 -608 Q-36 -596 -50 -556 Z" fill="{c["hair"]}" stroke="{INK}" '
                f'stroke-width="{LW}" stroke-linejoin="round"/>'
                f'<path d="M-46 -612 L-72 -622 L-52 -596 L-74 -592 L-50 -572" fill="{c["hair"]}" '
                f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
                f'<path d="M-6 -652 C-14 -688 20 -704 40 -690 C22 -688 16 -672 14 -652 Z" fill="{c["hair"]}" '
                f'stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
        extra = ""
    elif name == "IRIS":
        back = (f'<path d="M-40 -636 C-120 -640 -128 -560 -104 -520 C-100 -560 -80 -590 -46 -596 Z" '
                f'fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
        hair = (f'<path d="M-50 -540 Q-66 -662 6 -662 Q60 -660 58 -600 Q36 -628 10 -618 Q-14 -610 -20 -580 '
                f'Q-30 -560 -50 -540 Z" fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" '
                f'stroke-linejoin="round"/><circle cx="-44" cy="-618" r="9" fill="{_shade(c["hair"], 0.7)}"/>')
        extra = (f'<rect x="18" y="-596" width="30" height="24" rx="6" fill="none" stroke="{INK}" stroke-width="4"/>'
                 + _line("M18 -588 L-6 -586", 3.5))
    else:  # BOB
        back = ""
        hair = (f'<path d="M-4 -572 Q-12 -522 22 -506 Q52 -500 60 -528 L58 -554 Q46 -550 36 -553 Q22 -557 12 -549 '
                f'Q0 -550 -4 -572 Z" fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
                f'<path d="M-56 -612 Q-58 -684 4 -686 Q58 -684 60 -616 Z" fill="{c["beanie"]}" stroke="{INK}" '
                f'stroke-width="{LW}"/><rect x="-60" y="-632" width="124" height="24" rx="8" '
                f'fill="{c["beanie_band"]}" stroke="{INK}" stroke-width="{LW}"/>')
        extra = ""
        mouth_y = -541

    face = (_eye(eyes, 30, eye_y) + extra + _brow(brow_kind, 30, brow_y)
            + _mouth(mouth, 36, mouth_y, beard=(name == "BOB")))
    if name == "BOB":  # beanie must sit over the brow line, brows on top
        return back + skull + nose + ear + _eye(eyes, 30, eye_y) + hair + _mouth(mouth, 36, mouth_y, True) + _brow(brow_kind, 30, brow_y)
    return back + skull + nose + ear + hair + face


def _profile_torso(name, c):
    t, sh = c["top"], c["top_shade"]
    if name == "BOB":
        body = "M-40 -494 Q-52 -470 -48 -420 L-44 -252 L46 -252 Q70 -320 58 -380 Q52 -470 30 -494 Q0 -504 -40 -494 Z"
    else:
        body = "M-36 -494 Q-48 -470 -44 -420 L-40 -252 L36 -252 Q42 -320 38 -380 Q44 -460 30 -494 Q0 -504 -36 -494 Z"
    out = (f'<path d="{body}" fill="{t}"/>'
           f'<path d="M-36 -494 Q-48 -470 -44 -420 L-40 -252 L-14 -252 L-16 -496 Z" fill="{sh}"/>')
    if name == "KAI":
        out += (f'<path d="M-30 -500 Q-58 -476 -42 -452 Q-30 -478 -14 -498 Z" fill="{sh}" stroke="{INK}" stroke-width="4"/>'
                f'<path d="M8 -342 L38 -342 L40 -292 L6 -292 Z" fill="{sh}" stroke="{INK}" stroke-width="4"/>')
    elif name == "IRIS":
        out += f'<path d="M24 -494 Q40 -460 38 -380 Q40 -320 36 -252 L26 -252 Q30 -380 18 -494 Z" fill="{c["inner"]}"/>'
    else:
        out += (f'<path d="M26 -494 Q52 -470 58 -380 Q70 -320 46 -252 L34 -252 Q52 -330 40 -400 Q34 -470 14 -494 Z" '
                f'fill="{c["inner"]}"/>'
                + "".join(_line(f"M-44 {y} L30 {y}", 3, sh) for y in (-440, -380, -320)))
    return out + f'<path d="{body}" fill="none" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'


def character_side(name: str, x: float, y: float, scale: float = 1.0, pose: dict | None = None,
                   expression: str = "default", talking: bool = False, flip: bool = False) -> str:
    """Profile view with feet at (x, y). pose keys: front_arm, back_arm, front_leg, back_leg
    (each (upper, lower) angle), lean, drop."""
    c = CAST[name]
    p = pose or WALK_STAND
    drop, lean = p.get("drop", 0), p.get("lean", 0)
    neck = f'<rect x="-10" y="-522" width="28" height="36" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>'
    head = _profile_head(name, c, expression, talking)
    upper_back = _arm(c, *p["back_arm"], back=True)
    upper = (f'<g transform="translate(0 {drop}) rotate({lean} 0 {HIP_Y})">{upper_back}{neck}'
             f'{_profile_torso(name, c)}<g transform="rotate({p.get("tilt", 0)} 0 -515)">{head}</g></g>')
    front_arm = f'<g transform="translate(0 {drop}) rotate({lean} 0 {HIP_Y})">{_arm(c, *p["front_arm"])}</g>'
    legs_back = _leg(c, *p["back_leg"], drop, back=True)
    legs_front = _leg(c, *p["front_leg"], drop)
    # keep the lowest foot on the ground; "air" lifts the whole body for the hop between steps
    lowest = max(_foot_bottom(*p["front_leg"], drop), _foot_bottom(*p["back_leg"], drop))
    lift = -lowest - p.get("air", 0)
    sx = -scale if flip else scale
    return (f'<g transform="translate({x} {y}) scale({sx} {scale}) translate(0 {lift:.1f})">'
            f'{legs_back}{upper}{legs_front}{front_arm}</g>')


def _foot_bottom(thigh, shin, drop):
    kx, ky = _fwd(0, HIP_Y + drop, thigh, 112)
    fx, fy = _fwd(kx, ky, shin, 113)
    return fy + 20


WALK_STAND = {"front_arm": (4, 4), "back_arm": (-4, -2), "front_leg": (3, 2), "back_leg": (-3, -2)}


def side_run_pose(phase: float) -> dict:
    """Run cycle in profile. phase 0..1 = one full stride."""
    a = 2 * math.pi * phase

    def leg(ph):
        thigh = 38 * math.sin(ph)
        # knee folds most while the leg swings forward from behind (recovery)
        fold = 20 + 95 * max(0.0, math.cos(ph)) ** 1.4
        return thigh, thigh - fold

    def arm(ph):
        upper = -42 * math.sin(ph)
        return upper, upper + 88       # elbow bent about 90 degrees

    return {"front_leg": leg(a), "back_leg": leg(a + math.pi),
            "front_arm": arm(a + math.pi), "back_arm": arm(a),
            "lean": 11, "drop": 0, "air": 14 * abs(math.cos(a)), "tilt": -4}


def side_walk_pose(phase: float) -> dict:
    """Walk cycle in profile. phase 0..1 = one full stride."""
    a = 2 * math.pi * phase

    def leg(ph):
        thigh = 22 * math.sin(ph)
        return thigh, thigh - (6 + 38 * max(0.0, math.cos(ph)) ** 2)

    def arm(ph):
        upper = -20 * math.sin(ph)
        return upper, upper + 14

    return {"front_leg": leg(a), "back_leg": leg(a + math.pi),
            "front_arm": arm(a + math.pi), "back_arm": arm(a),
            "lean": 2, "drop": 0}
