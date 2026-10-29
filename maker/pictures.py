"""Pictures for a story: the costume master, one picture per scene, and three thumbnail pictures.

Uses Cloudflare Workers AI (free daily allowance). Resumable: pictures that already exist in the assets
folder are skipped, so when the daily allowance runs out the next run simply continues.

Usage:  python -m maker.pictures STORY.txt ASSETS_DIR
Writes  ASSETS_DIR/pictures_status.json  {"done": n, "total": m, "complete": bool}
"""
from __future__ import annotations

import json
import os
import re
import sys

from PIL import Image

from .art_lab import generate
from .script import load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_REF = os.path.join(ROOT, "characters", "ai", "kai_face_ref.png")

KAI_ID = ("a young man about 22 years old, slim, light skin, short black side-swept hair with the fringe falling to "
          "one side, clean-shaven, friendly expressive face")
STYLE = ("High quality 2D animated comedy illustration for adults, bold clean outlines, rich cel shading with soft "
         "light, cinematic composition, expressive faces, vivid but natural colours, professional studio quality. "
         "Absolutely no text, no letters, no words, no captions, no watermark.")
THUMB_STYLE = ("YouTube thumbnail illustration: one huge close-up subject filling most of the frame, extreme facial "
               "expression, very bright saturated colours, strong contrast, simple uncluttered background, bold clean "
               "outlines, cel shading. Absolutely no text, no letters, no words.")
W, H = 1280, 720


class AllowanceUsedUp(Exception):
    pass


def _gen(prompt, w, h, seed, refs, out):
    try:
        data = generate(prompt, w, h, seed=seed, refs=refs)
    except RuntimeError as ex:
        if "ALLOWANCE" in str(ex) or "429" in str(ex):
            raise AllowanceUsedUp(str(ex))
        raise
    tmp = out + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, out)


def small_ref(src, dst, max_side=500):
    im = Image.open(src).convert("RGB")
    s = max_side / max(im.size)
    im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS).save(dst)
    return dst


def kai_in(text: str) -> str:
    return re.sub(r"\bKAI\b", "Kai (the young man shown in the reference images)", text)


def jobs(st, assets):
    """Every picture the video needs, in the order they are made."""
    costume = os.path.join(assets, "costume.png")
    costume_ref = os.path.join(assets, "costume_ref.png")
    out = [("costume", costume,
            f"Full body character design of {KAI_ID}. He wears {st.costume}. Standing relaxed, facing the viewer, a "
            f"friendly face, the whole body from head to shoes visible. Image 0 shows his exact face and hair: keep "
            f"them exactly the same. Plain light grey background. {STYLE}", 768, 1024, [FACE_REF])]
    for s in st.scenes:
        for k, pic in (("", s.picture), ("b", s.picture2)):
            if not pic:
                continue
            path = os.path.join(assets, "pictures", f"scene_{s.number:03d}{k}.png")
            if s.has_kai or "KAI" in pic:
                prompt = (f"{kai_in(pic)}. Setting: {st.era}. Kai wears exactly the clothes from image 1: "
                          f"{st.costume}. Keep his face and hair exactly as in image 0. Other people wear plain "
                          f"clothes of the time. Wide 16:9 scene. {STYLE}")
                refs = [FACE_REF, costume_ref]
            else:
                prompt = f"{pic}. Setting: {st.era}. Wide 16:9 scene. {STYLE}"
                refs = []
            out.append((f"scene {s.number}{k}", path, prompt, W, H, refs))
    for i, idea in enumerate(st.thumbnail_ideas[:3]):
        path = os.path.join(assets, "pictures", f"thumb_{i + 1}.png")
        prompt = (f"{kai_in(idea)}. Kai wears {st.costume}. Keep his face and hair exactly as in image 0. "
                  f"{THUMB_STYLE}")
        out.append((f"thumbnail {i + 1}", path, prompt, W, H, [FACE_REF, costume_ref]))
    return out


def run(story_path, assets):
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors: " + "; ".join(st.errors))
    os.makedirs(os.path.join(assets, "pictures"), exist_ok=True)
    todo = jobs(st, assets)
    if os.path.exists(os.path.join(assets, "costume.png")):
        small_ref(os.path.join(assets, "costume.png"), os.path.join(assets, "costume_ref.png"))
    done = 0
    stopped = ""
    for i, (name, path, prompt, w, h, refs) in enumerate(todo):
        if os.path.exists(path):
            done += 1
            continue
        try:
            _gen(prompt, w, h, seed=1000 + i * 17, refs=refs, out=path)
            done += 1
            print(f"[{done}/{len(todo)}] {name}", flush=True)
        except AllowanceUsedUp as ex:
            stopped = str(ex)[:200]
            print("Daily picture allowance used up - the next run continues from here.", flush=True)
            break
        except Exception as ex:                      # a refused prompt: try once more with a different seed
            try:
                _gen(prompt + " Friendly and tasteful.", w, h, seed=5000 + i * 31, refs=refs, out=path)
                done += 1
            except Exception as ex2:
                print(f"{name}: failed ({str(ex2)[:150]})", flush=True)
        if name == "costume" and os.path.exists(path):
            small_ref(path, os.path.join(assets, "costume_ref.png"))
    status = {"done": done, "total": len(todo), "complete": done == len(todo), "stopped": stopped}
    json.dump(status, open(os.path.join(assets, "pictures_status.json"), "w"), indent=1)
    print(status)
    return status


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
