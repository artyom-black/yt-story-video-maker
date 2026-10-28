"""Channel profile picture (800x800) and banner (2560x1440, everything important inside the
1546x423 centre area that every device shows).

Usage:  python -m maker.channel_art out_dir
"""
from __future__ import annotations

import math
import os
import subprocess
import sys

from .backgrounds import _c, _e, _l, _p, _r, castle, tree
from .characters import character, pose_for

FONT = "Anton, 'Inter Display', 'DejaVu Sans', sans-serif"
TAGLINE = "WE SURVIVE HISTORY SO YOU DON'T HAVE TO"

POP = """<defs>
<filter id="pop" x="-20%" y="-20%" width="140%" height="140%">
  <feMorphology in="SourceAlpha" operator="dilate" radius="7" result="fat"/>
  <feFlood flood-color="#ffffff"/><feComposite in2="fat" operator="in" result="outline"/>
  <feMerge><feMergeNode in="outline"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<radialGradient id="portal" cx="50%" cy="50%" r="50%">
  <stop offset="0" stop-color="#fff6c8"/><stop offset=".35" stop-color="#ffd23f"/>
  <stop offset=".7" stop-color="#ff8a1c"/><stop offset="1" stop-color="#7a2bd6" stop-opacity="0"/>
</radialGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#3a2a7a"/><stop offset=".55" stop-color="#c2537a"/><stop offset="1" stop-color="#f2a65a"/>
</linearGradient>
</defs>"""


def portal(cx, cy, r):
    rings = "".join(_e(cx, cy, r * k, r * k * 0.62, "none", "#ffffff", 6, f' opacity="{0.15 + 0.1 * i}"')
                    for i, k in enumerate((1.0, 0.82, 0.64, 0.46)))
    rays = "".join(_l(f"M{cx + r * 0.3 * math.cos(a):.0f} {cy + r * 0.19 * math.sin(a):.0f} "
                      f"L{cx + r * 1.15 * math.cos(a):.0f} {cy + r * 0.72 * math.sin(a):.0f}", "#fff3b0", 6)
                   for a in [i * math.pi / 9 for i in range(18)])
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.62:.0f}" fill="url(#portal)"/>' + f'<g opacity=".35">{rays}</g>' + rings


def pyramids(x, y, s=1.0):
    def pyr(px, h, col, shade):
        return (_p(f"M{px - h} 0 L{px} {-h} L{px + h} 0 Z", col) + _p(f"M{px} {-h} L{px + h} 0 L{px + h * 0.15} 0 Z", shade, "none"))
    body = pyr(0, 260, "#e3b765", "#c99a4a") + pyr(330, 190, "#e3b765", "#c99a4a") + pyr(-300, 150, "#e3b765", "#c99a4a")
    palm = (_l("M560 0 Q575 -140 545 -260", "#7a5230", 16)
            + "".join(_p(f"M545 -260 Q{545 + 90 * math.cos(a):.0f} {-300 + 40 * math.sin(a):.0f} {545 + 150 * math.cos(a):.0f} {-230 + 60 * math.sin(a):.0f}",
                         "none", "#3f7a3a", 14) for a in (0.2, 1.2, 2.2, 3.0, -0.6)))
    return f'<g transform="translate({x} {y}) scale({s})">{body}{palm}</g>'


def colosseum(x, y, s=1.0):
    body = _r(-260, -200, 520, 200, "#d9c7a0")
    for row, yy in enumerate((-190, -125, -60)):
        for i in range(9):
            ax = -235 + i * 56
            body += _p(f"M{ax} {yy + 55} L{ax} {yy + 18} Q{ax + 18} {yy} {ax + 36} {yy + 18} L{ax + 36} {yy + 55} Z", "#7d6a55", "#26262b", 3)
    return f'<g transform="translate({x} {y}) scale({s})">{body}</g>'


def text(words, x, y, size, fill="#ffd23f", anchor="middle"):
    esc = words.replace("&", "&amp;").replace("'", "&#39;")
    return (f'<text x="{x + 6}" y="{y + 8}" text-anchor="{anchor}" font-family="{FONT}" font-weight="900" font-size="{size}" '
            f'fill="#000" opacity=".4">{esc}</text>'
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-weight="900" font-size="{size}" '
            f'fill="{fill}" stroke="#111" stroke-width="{max(6, size // 9)}" paint-order="stroke" stroke-linejoin="round">{esc}</text>')


def trio(cx, feet_y, scale, spread):
    return (f'<g filter="url(#pop)">'
            + character("IRIS", cx - spread, feet_y, scale * 0.98, pose_for("IRIS", "explain"), "smirk")
            + character("BOB", cx + spread, feet_y, scale, pose_for("BOB", "shock"), "shock")
            + character("KAI", cx, feet_y + 10, scale * 1.04, pose_for("KAI", "wave"), "happy")
            + "</g>")


def banner():
    W, H = 2560, 1440
    ground = 1000
    out = [POP, f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']
    out.append("".join(_c(x, y, r, "#fff4dc", "none", 0, ' opacity=".7"')
                       for x, y, r in ((240, 180, 4), (520, 120, 3), (900, 210, 3), (1700, 150, 4), (2100, 230, 3), (2380, 120, 4))))
    out.append(f'<path d="M0 {ground} Q640 820 1280 900 T{W} 860 L{W} {H} L0 {H} Z" fill="#5b3f6e"/>')
    out.append(castle(640, ground - 10, 1.05))                  # Middle Ages on the left
    out.append(tree(330, ground, 0.8))
    out.append(pyramids(1980, ground - 20, 1.0))                 # Ancient Egypt on the right
    out.append(colosseum(2380, ground - 40, 0.55))               # Rome far right
    out.append(f'<rect x="0" y="{ground - 30}" width="{W}" height="{H - ground + 30}" fill="#3e2b50"/>')
    # the 1546x423 area every device shows: x 507-2053, y 508-931. Trio on the left, words on the right.
    out.append(portal(840, 720, 290))
    out.append(trio(840, 925, 0.56, 165))
    out.append(text("WE SURVIVE HISTORY", 1570, 705, 80, "#ffd23f"))
    out.append(text("SO YOU DON'T HAVE TO", 1570, 812, 68, "#ffffff"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(out)}</svg>'


def profile(variant="trio"):
    S = 800
    out = [POP, f'<rect width="{S}" height="{S}" fill="url(#sky)"/>', portal(400, 470, 420)]
    if variant == "trio":   # a tight "group photo": faces big, arms down so nobody covers anybody
        out.append('<g filter="url(#pop)">'
                   + character("IRIS", 215, 1290, 1.38, pose_for("IRIS", "idle"), "smirk")
                   + character("BOB", 590, 1300, 1.38, pose_for("BOB", "idle"), "default")
                   + character("KAI", 400, 1350, 1.5, pose_for("KAI", "idle"), "happy") + "</g>")
    else:
        out.append(f'<g filter="url(#pop)">{character("BOB", 400, 1560, 2.05, pose_for("BOB", "idle"), "shock")}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">{"".join(out)}</svg>'


def circle_preview(png_in, png_out):
    """How the profile picture looks as YouTube's small circle."""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", png_in, "-vf",
                    "scale=200:200,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                    "a='if(lte(hypot(X-100,Y-100),100),255,0)'", png_out], check=True)


def make(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    files = {"banner.png": banner(), "profile_trio.png": profile("trio"), "profile_bob.png": profile("bob")}
    for name, svg in files.items():
        p = os.path.join(out_dir, name.replace(".png", ".svg"))
        with open(p, "w") as f:
            f.write(svg)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", p, os.path.join(out_dir, name)], check=True)
        os.remove(p)
        print("wrote", os.path.join(out_dir, name))
    for v in ("trio", "bob"):
        circle_preview(os.path.join(out_dir, f"profile_{v}.png"), os.path.join(out_dir, f"profile_{v}_circle.png"))


if __name__ == "__main__":
    make(sys.argv[1] if len(sys.argv) > 1 else "channel")
