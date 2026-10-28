"""Side (profile) view of the cast, for running and walking.

Same characters, same colours, same hair and clothes as the front view in characters.py,
just turned 90 degrees. Facing right by default; flip=True faces left.

Angles here mean: 0 = straight down, positive = forward (towards where they face).
"""
from __future__ import annotations

import math

from .characters import CAST, INK, LW, MOUTH, _limb, _line, face_spec

HIP_Y, SHOULDER_Y = -255, -478


def _shade(hex_colour, f=0.78):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def _fwd(x, y, angle, length):
    a = math.radians(angle)
    return x + length * math.sin(a), y + length * math.cos(a)


def _arm(c, upper, fore, fore_len=1.0, back=False):
    sx, sy = (-4 if back else 2), SHOULDER_Y
    ex, ey = _fwd(sx, sy, upper, 100)
    hx, hy = _fwd(ex, ey, fore, 92 * fore_len)
    ux, uy = _fwd(hx, hy, fore, 9)
    sleeve = _shade(c["top"]) if back else c["top"]
    skin = _shade(c["skin"], 0.88) if back else c["skin"]
    return (_limb([(sx, sy), (ex, ey), (hx, hy)], sleeve, 30)
            + f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="13" fill="{skin}" stroke="{INK}" stroke-width="{LW}"/>')


# shoe outline with the ankle at (0, 0), toes pointing along +x and the sole along +y
SHOE = "M-22 -14 L18 -16 Q44 -8 50 8 Q50 18 42 18 L-22 18 Q-28 2 -22 -14 Z"
SHOE_SOLE = ((-20, 18), (46, 18))


def _foot_rot(foot):
    """foot = direction heel->toe in our angle system (90 = flat, toes forward)."""
    return 90 - foot


def _leg(c, thigh, shin, foot, drop, back=False):
    hx, hy = 0, HIP_Y + drop
    kx, ky = _fwd(hx, hy, thigh, 112)
    fx, fy = _fwd(kx, ky, shin, 113)
    pants = _shade(c["pants"]) if back else c["pants"]
    shoes = _shade(c["shoes"]) if back else c["shoes"]
    accent = _shade(c["shoe_accent"]) if back else c["shoe_accent"]
    # the foot hinges at the ankle: flat on the ground, toes down when the heel kicks up
    shoe = (f'<g transform="translate({fx:.1f} {fy:.1f}) rotate({_foot_rot(foot):.1f})">'
            f'<path d="{SHOE}" fill="{shoes}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
            f'<path d="M-19 12 L46 12" stroke="{accent}" stroke-width="4"/></g>')
    # trouser leg ends square and slightly above the ankle, so no rounded end pokes out of the shoe
    ax, ay = _fwd(kx, ky, shin, 113 - 10)
    d = f"M{hx:.1f} {hy:.1f} L{kx:.1f} {ky:.1f} L{ax:.1f} {ay:.1f}"
    leg = (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{40 + 2 * LW}" '
           f'stroke-linecap="butt" stroke-linejoin="round"/>'
           f'<path d="{d}" fill="none" stroke="{pants}" stroke-width="40" '
           f'stroke-linecap="butt" stroke-linejoin="round"/>')
    return leg + shoe


def _foot_bottom(thigh, shin, foot, drop):
    """Lowest point of the shoe (ground contact)."""
    kx, ky = _fwd(0, HIP_Y + drop, thigh, 112)
    fx, fy = _fwd(kx, ky, shin, 113)
    r = math.radians(_foot_rot(foot))
    return max(fy + px * math.sin(r) + py * math.cos(r) for px, py in SHOE_SOLE)


# ---------------------------------------------------------------- profile faces
def _eye(kind, x, y):
    if kind == "tall":
        return f'<ellipse cx="{x + 1}" cy="{y}" rx="4.5" ry="10" fill="{INK}"/>'
    if kind == "tiny":
        return f'<circle cx="{x + 1}" cy="{y}" r="3" fill="{INK}"/>'
    if kind == "clench":
        return _line(f"M{x + 7} {y - 6} L{x - 5} {y} L{x + 7} {y + 6}", 4.5)
    if kind in ("huge", "roll"):
        r = 13 if kind == "huge" else 10
        py = -5 if kind == "roll" else 1
        return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                f'<circle cx="{x + 4}" cy="{y + py}" r="5.5" fill="{INK}"/>')
    if kind == "half":
        return (f'<ellipse cx="{x + 1}" cy="{y + 2}" rx="5" ry="5" fill="{INK}"/>'
                + _line(f"M{x - 9} {y - 2} Q{x} {y - 4} {x + 9} {y - 3}", 4.5))
    if kind == "closed":
        return _line(f"M{x - 7} {y} Q{x} {y + 5} {x + 7} {y}", 4.5)
    if kind == "wide":
        return (f'<circle cx="{x}" cy="{y}" r="10" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
                f'<circle cx="{x + 3}" cy="{y + 1}" r="5" fill="{INK}"/>')
    if kind == "happy":
        return _line(f"M{x - 7} {y + 3} Q{x} {y - 6} {x + 7} {y + 3}", 4.5)
    if kind == "squint":
        return _line(f"M{x - 7} {y} L{x + 7} {y}", 4.5)
    return f'<ellipse cx="{x}" cy="{y}" rx="5" ry="7.5" fill="{INK}"/>'


def _brow(kind, x, y, scale=1.0):
    d = {"up": (-8, -13, -5), "upup": (-14, -21, -11), "one-up": (-8, -15, -6), "angry": (-6, 0, 6),
         "one-angry": (-6, 0, 6), "worried": (5, -4, -8), "worried2": (8, -6, -13),
         "flat": (0, 0, 0)}.get(kind, (0, -6, 1))
    # drawn from the back of the brow (x - 10) to the front (x + 10)
    d = [v * scale for v in d]
    return _line(f"M{x - 11} {y + d[2]:.1f} Q{x} {y + d[1]:.1f} {x + 11} {y + d[0]:.1f}", 4.5)


def _mouth(kind, x, y, beard=False):
    dark = f'fill="{MOUTH}" stroke="{INK}" stroke-width="3.5"'
    kind = {"big-grin": "grin", "laugh": "grin", "dopey": "grin", "closed-smile": "smile", "flat-side": "neutral",
            "wobbly": "frown", "talk-big": "talk-big", "talk-small": "talk-small"}.get(kind, kind)
    if kind in ("O", "big-O", "talk", "talk-big", "talk-small", "small-o"):
        r = {"O": (6, 10), "big-O": (8, 13), "talk": (7, 6), "talk-big": (9, 8), "talk-small": (6, 3.5),
             "small-o": (4, 5)}[kind]
        return f'<ellipse cx="{x + 4}" cy="{y + 1}" rx="{r[0]}" ry="{r[1]}" {dark}/>'
    if kind == "grin":
        return (f'<path d="M{x - 8} {y - 3} Q{x + 6} {y + 14} {x + 14} {y - 4} Z" {dark}/>'
                f'<path d="M{x - 6} {y - 2} L{x + 12} {y - 3} L{x + 10} {y + 2} L{x - 4} {y + 2} Z" fill="#fff"/>')
    w = 5 if beard else 4
    shapes = {"smile": f"M{x - 8} {y - 2} Q{x + 4} {y + 6} {x + 14} {y - 3}",
              "frown": f"M{x - 8} {y + 5} Q{x + 4} {y - 3} {x + 14} {y + 6}",
              "smirk": f"M{x - 8} {y + 1} Q{x + 6} {y + 3} {x + 14} {y - 6}"}
    return _line(shapes.get(kind, f"M{x - 6} {y + 1} L{x + 13} {y + 1}"), w)


def _profile_head(name, c, expression, talking, blink=False):
    eyes, _look, brows, mouth = face_spec(name, expression)
    eyes = {"one-squint": "squint"}.get(eyes, eyes)
    if blink and eyes not in ("happy", "closed"):
        eyes = "closed"
    level = 1.0 if talking is True else float(talking or 0)
    if level >= 0.55:
        mouth = {"KAI": "talk-big", "IRIS": "talk", "BOB": "talk-small"}[name]
    elif level >= 0.15:
        mouth = "talk-small"
    s = c["skin"]
    ear = (f'<path d="M-10 -592 Q-30 -594 -28 -576 Q-28 -560 -10 -562" fill="{_shade(s, 0.9)}" stroke="{INK}" '
           f'stroke-width="4" stroke-linejoin="round"/>' + _line("M-14 -584 Q-22 -580 -16 -570", 3))
    skull = f'<ellipse cx="4" cy="-578" rx="54" ry="65" fill="{s}" stroke="{INK}" stroke-width="{LW}"/>'
    nose = (f'<path d="M54 -598 L70 -570 Q66 -563 55 -563" fill="{s}" stroke="{INK}" stroke-width="{LW}" '
            f'stroke-linejoin="round"/><path d="M52 -598 L52 -562" stroke="{s}" stroke-width="8"/>')
    eye_y, brow_y, mouth_y = -584, -604, -545
    brow_kind = {"KAI": "up", "IRIS": "flat", "BOB": "up"}[name] if brows == "sig" else brows

    if name == "KAI":
        back = ""
        # wolf cut in profile: shaggy crown, choppy fringe, longer layers at the nape
        hair = (f'<path d="M-50 -528 L-62 -548 L-53 -553 L-67 -580 L-56 -586 L-64 -622 Q-52 -668 4 -672 '
                f'Q56 -670 66 -622 L57 -618 L51 -628 L43 -614 L35 -627 L26 -613 L14 -624 Q0 -614 -14 -606 '
                f'Q-24 -592 -30 -578 L-36 -556 L-40 -536 Z" fill="{c["hair"]}" stroke="{INK}" '
                f'stroke-width="{LW}" stroke-linejoin="round"/>'
                + _line("M-40 -650 Q-6 -668 30 -660", 3, "#4a4a52"))
        extra = ""
    elif name == "IRIS":
        back = (f'<path d="M-40 -636 C-120 -640 -128 -560 -104 -520 C-100 -560 -80 -590 -46 -596 Z" '
                f'fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>')
        hair = (f'<path d="M-50 -540 Q-66 -662 6 -662 Q60 -660 58 -600 Q36 -628 10 -618 Q-14 -610 -20 -580 '
                f'Q-30 -560 -50 -540 Z" fill="{c["hair"]}" stroke="{INK}" stroke-width="{LW}" '
                f'stroke-linejoin="round"/><circle cx="-44" cy="-618" r="9" fill="{_shade(c["hair"], 0.7)}"/>')
        extra = (f'<rect x="18" y="-596" width="30" height="24" rx="6" fill="none" stroke="{INK}" stroke-width="4"/>'
                 + _line("M18 -588 L-6 -586", 3.5))
    else:  # BOB: no beard, messy hair poking out under the beanie
        back = ""
        hair = (f'<path d="M-46 -622 L-64 -604 L-46 -608 L-56 -590 L-34 -606 L-30 -622 Z" fill="{c["hair"]}" '
                f'stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                f'<path d="M24 -620 L30 -602 L38 -614 L44 -604 L48 -620 Z" fill="{c["hair"]}" stroke="{INK}" '
                f'stroke-width="4" stroke-linejoin="round"/>'
                f'<path d="M-56 -620 Q-58 -692 4 -694 Q58 -692 60 -624 Z" fill="{c["beanie"]}" stroke="{INK}" '
                f'stroke-width="{LW}"/><rect x="-60" y="-640" width="124" height="24" rx="8" '
                f'fill="{c["beanie_band"]}" stroke="{INK}" stroke-width="{LW}"/>')
        extra = ""
        mouth_y = -541

    face = (_eye(eyes, 30, eye_y) + extra + _brow(brow_kind, 30, brow_y)
            + _mouth(mouth, 36, mouth_y, beard=(name == "BOB")))
    if name == "BOB":  # beanie must sit over the brow line, brows on top
        return back + skull + nose + ear + _eye(eyes, 30, eye_y) + hair + _mouth(mouth, 36, mouth_y) + _brow(brow_kind, 30, -600, 0.6)
    return back + skull + nose + ear + hair + face


def _profile_torso(name, c):
    t, sh = c["top"], c["top_shade"]
    if name == "BOB":
        body = "M-40 -494 Q-52 -470 -48 -420 L-44 -252 L46 -252 Q70 -320 58 -380 Q52 -470 30 -494 Q0 -504 -40 -494 Z"
    else:
        body = "M-36 -494 Q-48 -470 -44 -420 L-40 -252 L36 -252 Q42 -320 38 -380 Q44 -460 30 -494 Q0 -504 -36 -494 Z"
    out = (f'<path d="{body}" fill="{t}"/>'
           f'<path d="M-36 -494 Q-48 -470 -44 -420 L-40 -252 L-30 -252 L-30 -496 Z" fill="{sh}" opacity=".55"/>')
    if name == "KAI":
        out += (f'<path d="M-26 -502 Q-46 -490 -38 -470 Q-28 -484 -12 -500 Z" fill="{sh}" stroke="{INK}" stroke-width="4"/>'
                f'<path d="M8 -342 L38 -342 L40 -292 L6 -292 Z" fill="{sh}" stroke="{INK}" stroke-width="4"/>')
    elif name == "IRIS":
        out += f'<path d="M24 -494 Q40 -460 38 -380 Q40 -320 36 -252 L26 -252 Q30 -380 18 -494 Z" fill="{c["inner"]}"/>'
    else:
        out += (f'<path d="M26 -494 Q52 -470 58 -380 Q70 -320 46 -252 L34 -252 Q52 -330 40 -400 Q34 -470 14 -494 Z" '
                f'fill="{c["inner"]}"/>'
                + "".join(_line(f"M-44 {y} L30 {y}", 3, sh) for y in (-440, -380, -320)))
    return out + f'<path d="{body}" fill="none" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'


def character_side(name: str, x: float, y: float, scale: float = 1.0, pose: dict | None = None,
                   expression: str = "default", talking: bool = False, flip: bool = False,
                   blink: bool = False) -> str:
    """Profile view with feet at (x, y). pose keys: front_arm, back_arm, front_leg, back_leg
    (each (upper, lower) angle), lean, drop."""
    c = CAST[name]
    p = pose or WALK_STAND
    drop, lean = p.get("drop", 0), p.get("lean", 0)
    neck = f'<rect x="-10" y="-522" width="28" height="36" fill="{c["skin"]}" stroke="{INK}" stroke-width="{LW}"/>'
    head = _profile_head(name, c, expression, talking, blink)
    upper_back = _arm(c, *p["back_arm"], back=True)
    upper = (f'<g transform="translate(0 {drop}) rotate({lean} 0 {HIP_Y})">{upper_back}{neck}'
             f'{_profile_torso(name, c)}<g transform="rotate({p.get("tilt", 0)} 0 -515)">{head}</g></g>')
    front_arm = f'<g transform="translate(0 {drop}) rotate({lean} 0 {HIP_Y})">{_arm(c, *p["front_arm"])}</g>'
    legs_back = _leg(c, *p["back_leg"], drop, back=True)
    legs_front = _leg(c, *p["front_leg"], drop)
    # keep the lowest foot on the ground; "air" lifts the whole body for the hop between steps
    if "ground" in p:
        lift = p["ground"]
    else:
        lowest = max(_foot_bottom(*p["front_leg"], drop), _foot_bottom(*p["back_leg"], drop))
        lift = -lowest - p.get("air", 0)
    sx = -scale if flip else scale
    return (f'<g transform="translate({x} {y}) scale({sx} {scale}) translate(0 {lift:.1f})">'
            f'{legs_back}{upper}{legs_front}{front_arm}</g>')



WALK_STAND = {"front_arm": (4, 4, 1.0), "back_arm": (-4, -2, 1.0), "front_leg": (3, 2, 90), "back_leg": (-3, -2, 90)}


# Key poses for ONE leg over one stride (phase 0..1), as (phase, thigh, shin).
# This is the classic animator's run cycle: contact, down, push-off, heel kick, passing, reach.
RUN_LEG_KEYS = [
    #  phase thigh shin foot   (foot: 90 = flat, >90 toes up, <90 toes pointing down)
    (0.00, 24, 6, 96),       # contact: lands on the front of the foot, just ahead of the hip
    (0.12, 10, -14, 90),     # down: knee bends to absorb the landing, foot flat
    (0.26, -10, -22, 88),    # support: body passes over the foot
    (0.38, -32, -40, 52),    # push-off: heel up, toes pushing the ground
    (0.55, -20, -100, 8),    # heel kick: foot flicks up behind, toes point down
    (0.70, 14, -96, 22),     # passing: knee comes forward, heel tucked high
    (0.84, 48, -42, 62),     # reach: knee high, foot swinging forward
]
WALK_LEG_KEYS = [
    (0.00, 18, 16, 108),     # heel strike, toes up
    (0.16, 6, 2, 90),        # foot flat
    (0.38, -14, -16, 84),    # body over the foot
    (0.52, -18, -44, 50),    # toe off
    (0.72, 6, -40, 62),      # passing, toes down
    (0.88, 20, 4, 96),       # swing forward
]


def _interp(keys, phase):
    """Smooth looping interpolation (Catmull-Rom) through the key poses."""
    phase %= 1.0
    n = len(keys)
    for i in range(n):
        p0 = keys[i][0]
        p1 = keys[(i + 1) % n][0] + (1.0 if i + 1 == n else 0.0)
        ph = phase if phase >= p0 else phase + 1.0
        if p0 <= ph < p1:
            t = (ph - p0) / (p1 - p0)
            a, b, c, d = keys[i - 1], keys[i], keys[(i + 1) % n], keys[(i + 2) % n]
            out = []
            for j in range(1, len(b)):
                v0, v1, v2, v3 = a[j], b[j], c[j], d[j]
                out.append(0.5 * ((2 * v1) + (-v0 + v2) * t + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t * t
                                  + (-v0 + 3 * v1 - 3 * v2 + v3) * t ** 3))
            return tuple(out)
    return tuple(keys[0][1:])


# Each character's own way of moving.
#   stride = seconds per full stride, arm = arm swing, bend = elbow angle, lean = forward lean,
#   hop = height of the in-air moment, kick = how high the heel kicks up, reach = stride length,
#   bounce = extra up-down in the walk, wobble = head/body wobble (Bob)
GAIT = {
    "KAI":  {"run": {"stride": 0.44, "arm": 40, "bend": 92, "lean": 17, "hop": 22, "kick": 1.12, "reach": 1.05},
             "walk": {"stride": 0.86, "arm": 22, "lean": 4, "bounce": 7, "reach": 1.0, "wobble": 0}},
    "IRIS": {"run": {"stride": 0.5, "arm": 28, "bend": 100, "lean": 11, "hop": 14, "kick": 0.95, "reach": 0.95},
             "walk": {"stride": 1.0, "arm": 12, "lean": 1, "bounce": 1, "reach": 0.9, "wobble": 0}},
    "BOB":  {"run": {"stride": 0.6, "arm": 48, "bend": 62, "lean": 6, "hop": 8, "kick": 0.7, "reach": 0.85,
                     "wobble": 6},
             "walk": {"stride": 1.22, "arm": 24, "lean": -3, "bounce": 3, "reach": 0.9, "wobble": 5}},
}
DEFAULT_GAIT = GAIT["IRIS"]


def _gait(name, kind):
    return (GAIT.get(name) or DEFAULT_GAIT)[kind]


def _leg_at(keys, phase, g):
    """Key-pose leg, adjusted for a character's stride length (reach) and heel kick."""
    th, sh, ft = _interp(keys, phase)
    th2 = th * g.get("reach", 1.0)
    sh2 = th2 - (th - sh) * g.get("kick", 1.0)
    return th2, sh2, ft + (sh2 - sh) * 0.5


def _pump_arm(swing, amount, bend, close=0.12, fore_len=0.85):
    """swing -1..1 (1 = arm forward). Elbow closes as the arm comes forward."""
    upper = amount * swing
    return upper, upper + bend + close * upper * 4, fore_len


def side_run_pose(phase: float, name: str | None = None) -> dict:
    """Run cycle in profile. phase 0..1 = one full stride (front leg lands at 0, back leg at 0.5)."""
    g = _gait(name, "run")
    swing = math.cos(2 * math.pi * (phase - 0.43))
    wob = g.get("wobble", 0) * math.sin(2 * math.pi * phase)
    return {"front_leg": _leg_at(RUN_LEG_KEYS, phase, g), "back_leg": _leg_at(RUN_LEG_KEYS, phase + 0.5, g),
            "front_arm": _pump_arm(swing, g["arm"], g["bend"]), "back_arm": _pump_arm(-swing, g["arm"], g["bend"]),
            "lean": g["lean"] + 0.4 * wob, "ground": _run_ground(phase, g),
            "tilt": -5 + 2 * math.sin(4 * math.pi * phase) + wob}


def _run_ground(phase, g=None):
    """Body height for the run: the supporting foot stays on the ground from contact (0) to
    push-off; then both feet are in the air until the other foot lands (0.5)."""
    g = g or DEFAULT_GAIT["run"]
    push = RUN_LEG_KEYS[3][0]
    half = phase % 0.5
    if half <= push:
        return -_foot_bottom(*_leg_at(RUN_LEG_KEYS, half, g), 0)
    u = (half - push) / (0.5 - push)
    start = -_foot_bottom(*_leg_at(RUN_LEG_KEYS, push, g), 0)
    end = -_foot_bottom(*_leg_at(RUN_LEG_KEYS, 0.0, g), 0)
    return start + (end - start) * u - g["hop"] * math.sin(math.pi * u)


def stride_speed(keys=None, scale=1.0, stride_seconds=None, name=None, kind=None):
    """Ground speed (px/s) that keeps the planted foot from sliding."""
    keys = keys or RUN_LEG_KEYS
    kind = kind or ("run" if keys is RUN_LEG_KEYS else "walk")
    g = _gait(name, kind)
    stride_seconds = stride_seconds or g["stride"]

    def foot_x(ph):
        th, sh, _ = _leg_at(keys, ph, g)
        kx, _ = _fwd(0, HIP_Y, th, 112)
        fx, _ = _fwd(kx, 0, sh, 113)
        return fx
    contact, lift = 0.0, keys[3][0]
    return (foot_x(contact) - foot_x(lift)) * scale / ((lift - contact) * stride_seconds)


def side_walk_pose(phase: float, name: str | None = None) -> dict:
    """Walk cycle in profile. phase 0..1 = one full stride."""
    g = _gait(name, "walk")
    swing = math.cos(2 * math.pi * (phase - 0.45))
    wob = g["wobble"] * math.sin(2 * math.pi * phase)
    bounce = g["bounce"] * (0.5 + 0.5 * math.cos(4 * math.pi * (phase - 0.3)))
    return {"front_leg": _leg_at(WALK_LEG_KEYS, phase, g), "back_leg": _leg_at(WALK_LEG_KEYS, phase + 0.5, g),
            "front_arm": _pump_arm(swing, g["arm"], 12, 0.1, 1.0), "back_arm": _pump_arm(-swing, g["arm"], 12, 0.1, 1.0),
            "lean": g["lean"] + 0.3 * wob, "air": bounce, "tilt": wob}
