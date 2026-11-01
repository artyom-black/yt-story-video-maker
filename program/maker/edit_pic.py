"""Fix one detail in an existing picture without changing anything else (the AI gets the picture as image 0).

    python -m maker.edit_pic OUT_DIR       (uses program/characters/stick/edit_src.png and INSTRUCTION below)
"""
from __future__ import annotations

import os
import sys

from .art_lab import generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "characters", "stick", "edit_src.png")
INSTRUCTION = ("Exactly the same picture as image 0, same composition, same character, same ox, same colours and "
               "style. Change only his footwear: replace the boots with simple flat medieval leather wrap shoes, "
               "low, soft and shapeless, tied around the ankle with thin leather straps, no heels, no soles, no laces. "
               "Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for seed in (5, 6, 7):
        open(os.path.join(out, f"edit_{seed}.png"), "wb").write(generate(INSTRUCTION, 1280, 720, seed=seed, refs=[SRC]))
        print("edited", seed, flush=True)
