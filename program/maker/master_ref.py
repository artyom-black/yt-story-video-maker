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

THIN = ("Character reference for a YouTube history explainer video, one single character, simple stick figure "
        "style like popular animated explainer channels: a big round white head with a clean black outline, two "
        "round white eyes with small black pupils, simple eyebrows, a small mouth, messy short brown hair. He is a "
        "poor medieval peasant: a simple patched brown wool tunic down to his knees drawn as one flat shape, a "
        "rope belt, arms and legs drawn as single thin black lines, small round hands, simple brown cloth shoes. "
        "Big head, small body. Clean confident lines, flat colours, likeable. Standing facing the viewer, a tired "
        "but friendly face, the whole body from head to feet visible, centred. Pure plain white background, "
        "nothing else, no shadow. Absolutely no text, no letters, no watermark.")

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "characters", "stick", "kai_v1.png")
    for seed in (11, 22, 33, 44, 55, 66):
        data = generate(THIN, 768, 1024, seed=seed)
        open(os.path.join(out, f"master_{seed}.png"), "wb").write(data)
        print("drew", seed, flush=True)
