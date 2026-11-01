"""Draw one picture again using an existing picture as the exact model for the character's body.

    python -m maker.edit_pic OUT_DIR   (uses main-character.jpg and program/characters/stick/edit_src.png)
"""
from __future__ import annotations

import os
import sys

from .art_lab import generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
REFS = [os.path.join(REPO, "main-character.jpg"), os.path.join(ROOT, "characters", "stick", "edit_src.png")]
INSTRUCTION = ("The same stick figure character as in image 0 and image 1: exactly the same round white head, the same "
               "messy brown hair, the same brown patched tunic with a rope belt, and exactly the same legs as in image 1: "
               "two thin white legs with a black outline and small simple feet, drawn in exactly the same way. "
               "Night in a muddy medieval field under a dark blue sky with stars and a full moon. He stands in the mud, "
               "completely exhausted, shoulders down, bent forward, covered in mud and sweat, a sad destroyed face, "
               "holding a sickle hanging down in one hand. His whole body from head to feet is visible, centred, the "
               "same size and position in the picture as in image 1. Same drawing style as image 1. 16:9 picture. "
               "Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for seed in (5, 6, 7, 8):
        open(os.path.join(out, f"edit_{seed}.png"), "wb").write(generate(INSTRUCTION, 1280, 720, seed=seed, refs=REFS))
        print("drew", seed, flush=True)
