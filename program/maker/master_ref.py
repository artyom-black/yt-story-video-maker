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

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for seed in (11, 22, 33, 44):
        open(os.path.join(out, f"master_{seed}.png"), "wb").write(generate(PROMPT, 768, 1024, seed=seed))
        print("drew", seed, flush=True)
