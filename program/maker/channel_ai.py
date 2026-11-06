"""Channel art drawn with the same AI and the same Kai as the videos.

    profile_N.png  800x800   Kai's face, for the round channel picture
    banner_N.png   2560x1440 Kai through history, channel name inside the 1546x423 centre area every device shows

Usage:  python -m maker.channel_ai OUT_DIR "KAI FILMS" 4
"""
from __future__ import annotations

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import pictures as P

FONT = os.path.join(P.ROOT, "fonts", "Anton-Regular.ttf")
TAGLINE = "REAL HISTORY. ONE STICKMAN."

PROFILE = (
    f"{P.HEAD}Simple funny stick figure icon of {P.KAI_ID}, seen from the waist up, big in the middle of a square "
    "picture, wearing his brown peasant tunic, holding a round loaf of bread up next to his face with one small white "
    "hand and giving a thumbs up with the other, a cheeky happy smile. Plain pure white background, nothing else, "
    "no ground, no shadow. Square picture. No text, no letters.")

BANNER = (
    f"{P.HEAD}A very wide, short picture on a plain pure white background with nothing else: seven copies of "
    f"{P.KAI_ID} standing in one row from left to right, evenly spaced, each one small enough to be seen whole from "
    "head to feet, each a different person from history doing something funny: a medieval peasant swinging a sickle, "
    "a knight tripping over his own sword, an Egyptian pharaoh in a striped headdress pointing proudly, a Viking with "
    "a round helmet shouting and holding up a shield, a Roman soldier in a red cape marching, a caveman in a fur "
    "holding a club and looking confused, and a pirate with an eye patch laughing. Every one has the same white round "
    "head, messy brown hair, dot eyes and a funny clear face. No ground, no scenery, plain white background. "
    "Very wide picture. No text, no letters.")


def profile(src, dst):
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im.resize((800, 800), Image.LANCZOS).save(dst)


def banner(src, dst, name):
    """Like the big stick figure channels: a white banner with a row of characters, no text. The drawn strip fills
    exactly the 1546x423 centre that every device shows; the rest of the 2560x1440 is plain white."""
    strip = Image.open(src).convert("RGB")
    im = Image.new("RGB", (2560, 1440), (255, 255, 255))
    im.paste(strip.resize((1546, 424), Image.LANCZOS), (507, 508))
    im.save(dst)


def main(out, name, count):
    os.makedirs(out, exist_ok=True)
    refs = [P.small_ref(P.FACE_REF, os.path.join(out, "_kai_ref.png"))]
    for n in range(1, count + 1):
        for kind, prompt, w, h in (("profile", PROFILE, 1024, 1024), ("banner", BANNER, 1920, 528)):
            raw = os.path.join(out, f"_{kind}_{n}_raw.png")
            try:
                P.draw(prompt, w, h, seed=random.randint(1, 10 ** 6), refs=refs, out=raw)
            except Exception as ex:
                print(f"{kind} {n} failed: {str(ex)[:150]}", flush=True)
                continue
            if kind == "profile":
                profile(raw, os.path.join(out, f"profile_{n}.png"))
            else:
                banner(raw, os.path.join(out, f"banner_{n}.png"), name)
            os.remove(raw)
            print("drew", kind, n, flush=True)
    os.remove(refs[0])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "KAI FILMS", int(sys.argv[3]) if len(sys.argv) > 3 else 4)
