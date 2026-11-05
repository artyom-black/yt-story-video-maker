"""Draw a few new versions of single pictures, without making the video, so they can be approved one by one.

Usage:  python -m maker.try_picture STORY.txt ASSETS_DIR "1c, 25" 4 OUT_DIR
Writes  OUT_DIR/1c_1.png ... OUT_DIR/1c_4.png and OUT_DIR/prompts.json
An approved version is copied to ready-to-upload/<title>/kept/scene_001x3_kept.png and is then used as it is.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys

from . import pictures as P
from .script import load


def main(story, assets, labels, count, out):
    st = load(story)
    todo = P.jobs(st, assets)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(todo[0][1]):
        P.small_ref(todo[0][1], os.path.join(assets, "costume_ref.png"))
    for name, path, *_ in todo:
        if name.startswith("cast ") and os.path.exists(path):
            P.small_ref(path, P.cast_ref(path))
    # pictures that were kept by hand have no prompt here: build the drawing job without the kept file
    kept_dir = P.kept_dir(st)
    hidden = kept_dir + ".hidden"
    if os.path.isdir(kept_dir):
        os.rename(kept_dir, hidden)
    try:
        todo = P.jobs(st, assets)
    finally:
        if os.path.isdir(hidden):
            os.rename(hidden, kept_dir)
    wanted = [w.strip().lower() for w in re.split(r"[ ,;]+", labels) if w.strip()]
    prompts = {}
    for name, path, prompt, w, h, refs, desc in todo:
        lab = P.label(P._key(path)).lower()
        if lab not in wanted:
            continue
        prompts[lab] = {"file": P._key(path) + "_kept.png", "prompt": prompt}
        for n in range(count):
            dst = os.path.join(out, f"{lab}_{n + 1}.png")
            try:
                P.draw(prompt, w, h, seed=random.randint(1, 10 ** 6), refs=refs, out=dst)
                print("drew", dst, flush=True)
            except Exception as ex:
                print(f"{lab} try {n + 1} failed: {str(ex)[:150]}", flush=True)
    json.dump(prompts, open(os.path.join(out, "prompts.json"), "w"), indent=1)
    missing = set(wanted) - set(prompts)
    if missing:
        print("unknown picture numbers:", ", ".join(sorted(missing)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
