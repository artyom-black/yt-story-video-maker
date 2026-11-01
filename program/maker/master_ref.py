"""The main character's master reference picture (used as image 0 in every drawing).

    python -m maker.master_ref OUT_DIR   -> OUT_DIR/master_<seed>.png (a few tries to choose from)
"""
from __future__ import annotations

import os
import sys

from .art_lab import generate
from .char_options import STICK

PROMPT = (f"Character reference sheet, one single character. {STICK}. His signature: thick messy spiky jet-black "
          f"hair, a full mop with many tufts sticking up and out, covering the top of his head, no glasses. "
          f"Standing straight facing the viewer, arms relaxed at his sides, neutral friendly smile, the whole body "
          f"from head to feet visible, centred. Pure plain white background, nothing else, no shadow on the ground. "
          f"Absolutely no text, no letters, no watermark.")

THIN = ("The same character as in image 0: exactly the same round white face, dot eyes, smile and messy jet-black "
        "hair. Redraw him as a good-looking, appealing stick figure in a clean modern YouTube explainer style: "
        "thin elegant black outlines, slim thin stick arms and legs drawn as single thin black lines, small neat "
        "hands and small simple feet, a slim small body, nicely balanced proportions. Standing straight facing the "
        "viewer, arms relaxed at his sides, friendly smile, the whole body from head to feet visible, centred. "
        "Pure plain white background, nothing else, no shadow. Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "characters", "stick", "kai_v1.png")
    for seed in (11, 22, 33, 44, 55, 66):
        data = generate(THIN, 768, 1024, seed=seed, refs=[ref]) if os.path.exists(ref) else \
            generate(PROMPT, 768, 1024, seed=seed)
        open(os.path.join(out, f"master_{seed}.png"), "wb").write(data)
        print("drew", seed, flush=True)
