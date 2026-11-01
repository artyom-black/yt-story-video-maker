"""Fix one detail in an existing picture without changing anything else (the AI gets the picture as image 0).

    python -m maker.edit_pic OUT_DIR       (uses program/characters/stick/edit_src.png and INSTRUCTION below)
"""
from __future__ import annotations

import os
import sys

from .art_lab import generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "characters", "stick", "edit_src.png")
INSTRUCTION = ("Exactly the same picture as image 0: the same composition, the same room, the same character, the same "
               "sleeping family, the same window, the same drawing style. Only two changes: 1) the whole picture is "
               "brighter, with warm orange firelight glowing on everything; 2) his face is more surprised and shocked, "
               "eyebrows raised high, eyes a bit wider, mouth open in a small 'wait, what?' shape. Keep his small dot "
               "eyes and his hand on his forehead. Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for seed in (5, 6, 7):
        open(os.path.join(out, f"edit_{seed}.png"), "wb").write(generate(INSTRUCTION, 1280, 720, seed=seed, refs=[SRC]))
        print("edited", seed, flush=True)
