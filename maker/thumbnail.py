"""MrBeast-style thumbnails from the story's THUMBNAIL_IDEA lines.

Rules (from what works on YouTube): one or two huge faces with extreme emotions, very bright and
saturated colours, one clear object, a white outline so the subject pops, and 1-3 words of bold text.
An idea that names two characters becomes a split "vs" thumbnail.

Usage:  python -m maker.thumbnail STORY.txt out_dir
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

from .backgrounds import PROPS, _g, _has, pick_setting, time_of_day
from .characters import character, pose_for
from .story import load

TW, TH = 1280, 720
FONT = "Anton, 'Inter Display', 'DejaVu Sans', sans-serif"
NAMES = ("KAI", "IRIS", "BOB")

EMOTION = [  # (words, expression, pose)
    (("terrified", "scared", "panicking", "panic", "afraid"), "scared", "scared"),
    (("shocked", "horrified", "surprised", "staring", "looking down"), "shock", "shock"),
    (("miserable", "crying", "sad", "disgusted"), "sad", "shrug"),
    (("laughing", "happy", "excited", "cheering", "celebrating"), "happy", "wave"),
    (("smug", "proud", "confident"), "smirk", "explain"),
    (("angry", "furious", "annoyed"), "annoyed", "point"),
    (("pointing",), "curious", "point"),
]

POP_BG = [("#ffcf3f", "#ff7b1c"), ("#3fd2ff", "#1c5bff"), ("#ff5f6d", "#b3124a"), ("#7cff6b", "#16a34a"),
          ("#c084fc", "#6d28d9")]

FILTERS = """<defs>
<filter id="pop" x="-20%" y="-20%" width="140%" height="140%">
  <feMorphology in="SourceAlpha" operator="dilate" radius="9" result="fat"/>
  <feFlood flood-color="#ffffff"/><feComposite in2="fat" operator="in" result="outline"/>
  <feMerge><feMergeNode in="outline"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="vivid"><feColorMatrix type="saturate" values="1.7"/></filter>
<filter id="soft"><feGaussianBlur stdDeviation="3"/><feColorMatrix type="saturate" values="1.6"/></filter>
</defs>"""


def _emotion(text):
    t = text.lower()
    for words, ex, pose in EMOTION:
        if any(w in t for w in words):
            return ex, pose
    return "shock", "shock"


def _segments(idea):
    """Split an idea into one piece of text per character it mentions, in order."""
    marks = [(m.start(), m.group(0)) for m in re.finditer(r"\b(KAI|IRIS|BOB)\b", idea)]
    if not marks:
        return [("KAI", idea)]
    segs = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(idea)
        segs.append((name, idea[pos:end]))
    seen, out = set(), []
    for name, txt in segs:
        if name not in seen:
            out.append((name, txt))
            seen.add(name)
    return out[:2]


def _props_svg(text, x, y, scale, flip=False):
    """The single clearest object mentioned, drawn big."""
    t = text.lower()
    for keys, fn, where, size in PROPS:
        if any(_has(t, k) for k in keys):
            return _g(x, y, scale * size, fn(), flip=flip)
    return ""


def _background(text, colours, x0, w):
    setting = pick_setting(text)
    base, _indoor = setting(time_of_day(text), text.lower())
    # draw the 1920x1080 setting squeezed into the panel, blurred and over-saturated so faces pop
    sx = w / 1920
    return (f'<g transform="translate({x0} 0) scale({sx:.4f} {TH / 1080:.4f})" filter="url(#soft)">{base}</g>'
            f'<rect x="{x0}" y="0" width="{w}" height="{TH}" fill="url(#grad{x0})" opacity=".45"/>'
            f'<defs><radialGradient id="grad{x0}" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{colours[0]}"/>'
            f'<stop offset="1" stop-color="{colours[1]}"/></radialGradient></defs>')


def _text(words, x, y, size, anchor="middle", fill="#ffffff"):
    esc = words.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x + 6}" y="{y + 8}" text-anchor="{anchor}" font-family="{FONT}" font-weight="900" '
            f'font-size="{size}" fill="#000" opacity=".45">{esc}</text>'
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-weight="900" font-size="{size}" '
            f'fill="{fill}" stroke="#111" stroke-width="{size // 9}" paint-order="stroke" stroke-linejoin="round">{esc}</text>')


def make(idea: str, label: str, variant: int):
    segs = _segments(idea)
    parts = [FILTERS]
    if len(segs) == 2:                       # split "vs" layout
        for side, (name, txt) in enumerate(segs):
            x0 = side * TW // 2
            parts.append(f'<clipPath id="half{side}"><rect x="{x0}" y="0" width="{TW // 2}" height="{TH}"/></clipPath>')
            ex, pose = _emotion(txt)
            body = (_background(txt, POP_BG[(variant + side * 2) % len(POP_BG)], x0, TW // 2)
                    + _props_svg(txt, x0 + (90 if side == 0 else TW // 2 - 90), TH - 30, 0.95, flip=side == 1)
                    + f'<g filter="url(#pop)">{character(name, x0 + TW // 4, 70 + 690 * 1.85, 1.85, pose_for(name, pose), ex)}</g>')
            parts.append(f'<g clip-path="url(#half{side})"><g filter="url(#vivid)">{body}</g></g>')
        parts.append(f'<path d="M{TW / 2 - 10} 0 L{TW / 2 + 10} 0 L{TW / 2 + 10} {TH} L{TW / 2 - 10} {TH} Z" fill="#111"/>')
        if label:
            parts.append(_text(label, TW / 2, TH - 40, 118, fill="#ffd23f"))
    else:
        name, txt = segs[0]
        ex, pose = _emotion(txt)
        face_right = variant % 2 == 0
        cx = 880 if face_right else 400
        body = (_background(txt, POP_BG[variant % len(POP_BG)], 0, TW)
                + _props_svg(txt, 300 if face_right else 980, TH - 40, 1.25, flip=not face_right)
                + f'<g filter="url(#pop)">{character(name, cx, 60 + 690 * 2.2, 2.2, pose_for(name, pose), ex)}</g>')
        parts.append(f'<g filter="url(#vivid)">{body}</g>')
        if label:
            parts.append(_text(label, 320 if face_right else 960, 160, 122, fill="#ffd23f"))
        # big red arrow pointing at the object, a classic attention grabber
        ax = 470 if face_right else 810
        flip = 1 if face_right else -1
        parts.append(f'<g transform="translate({ax} 380) scale({-flip} 1) rotate(-35)">'
                     f'<path d="M0 0 L90 0 L90 -40 L170 30 L90 100 L90 60 L0 60 Z" fill="#ff2b2b" stroke="#111" '
                     f'stroke-width="9" stroke-linejoin="round"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TW} {TH}" width="{TW}" height="{TH}">'
            + "".join(parts) + "</svg>")


def make_all(story_path: str, out_dir: str):
    st = load(story_path)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, idea in enumerate(st.thumbnail_ideas[:3] or [st.title]):
        svg = os.path.join(out_dir, f"thumbnail_{i + 1}.svg")
        png = os.path.join(out_dir, f"thumbnail_{i + 1}.png")
        with open(svg, "w") as f:
            f.write(make(idea, st.thumbnail_text, i))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", svg, png], check=True)
        os.remove(svg)
        paths.append(png)
        print("wrote", png)
    return paths


if __name__ == "__main__":
    make_all(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
