"""Draw one picture again using an existing picture as the exact model for the character's body.

    python -m maker.edit_pic OUT_DIR   (uses main-character.jpg and program/characters/stick/edit_src.png)
"""
from __future__ import annotations

import os
import sys

from .art_lab import generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
REFS = [os.path.join(REPO, "main-character.jpg"), os.path.join(ROOT, "characters", "stick", "edit_src.png"),
        os.path.join(ROOT, "characters", "stick", "edit_src2.png")]
INSTRUCTION = ("The same stick figure character as in image 1: exactly the same round white head, messy brown hair, "
               "brown patched tunic with a rope belt, and exactly the same thin white legs with a black outline and small "
               "feet. His face exactly like image 2: dirty, sweaty, sad and exhausted, with mud on his cheek and tunic. "
               "His body shows he is completely exhausted: shoulders dropped, back bent forward, both arms hanging down "
               "limp at his sides, one hand loosely dragging a sickle on the ground, knees slightly bent, as if he could "
               "collapse any second. He stands in the middle, his whole body from head to feet visible, about the same size "
               "as in image 1. Background: a beautiful wide medieval harvest field at night under one big full moon and a "
               "dark blue sky full of stars, the whole field cut, many neat rows of tied golden wheat bundles standing in "
               "stooks going far into the distance, a wooden cart piled high with wheat behind him, and far away a small "
               "village with straw roofs and warm glowing windows. Moonlight makes the wheat glow softly. Same drawing "
               "style as image 1. Only one moon. 16:9 picture. Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for seed in (5, 6, 7, 8):
        open(os.path.join(out, f"edit_{seed}.png"), "wb").write(generate(INSTRUCTION, 1280, 720, seed=seed, refs=REFS))
        print("drew", seed, flush=True)
