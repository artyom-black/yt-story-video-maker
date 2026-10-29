"""Art lab: try the AI art style with Cloudflare Workers AI (free daily allowance).

Draws a small test set: a few emotions for each character (on a plain background, then cut out)
and two empty backgrounds. Uses our approved code-drawn designs as reference pictures so the AI
keeps the hair, clothes and colours.

Needs env CF_ACCOUNT_ID and CF_API_TOKEN.
Usage:  python -m maker.art_lab out_dir [--set test]
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import time

import requests

from .characters import CAST, _svg, character, pose_for

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
URL = "https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/" + MODEL

STYLE = ("2D cartoon illustration for an adult animated comedy series, clean bold black outlines, "
         "flat colours with soft cel shading, expressive face, appealing proportions, high quality, "
         "no text, no watermark")

LOOK = {
    "KAI": ("a young man in his twenties, short black side-swept hair with the fringe falling to one side, "
            "light skin, a {hoodie} hoodie with a front pocket and drawstrings, dark blue jeans, dark grey sneakers"),
    "IRIS": ("a young woman in her twenties, dark brown hair in a ponytail, brown skin, rectangular glasses, "
             "a teal jacket over a white t-shirt, black jeans, white sneakers"),
    "BOB": ("a big friendly young man in his twenties, round face, no beard, an olive green beanie with messy brown "
            "hair poking out, a red flannel shirt open over a mustard yellow t-shirt, blue jeans, brown boots"),
}

TEST_EMOTIONS = {
    "neutral": "standing relaxed, slight friendly smile, mouth closed",
    "talking": "standing, talking with one hand raised in a gesture, mouth open mid-word",
    "shocked": "extremely shocked, eyes wide, jaw dropped, hands on head",
    "laughing": "laughing hard, eyes closed, mouth wide open, holding his belly",
    "scared": "terrified, leaning back, hands up in front of the body, trembling",
}

# Orange hoodies are what every Ink Explainer copy uses, so Kai gets a new colour. Two to choose from:
KAI_HOODIES = {"blue": "bright royal blue", "yellow": "bright sunflower yellow"}

SELFIE = ("Three friends taking a selfie together, faces big and close to the camera, slightly from above. "
          "Left: {kai}, holding the phone with an outstretched arm, big excited grin. "
          "Middle: {iris}, smug look with one eyebrow raised. "
          "Right: {bob}, shocked, looking the wrong way. "
          "Behind them a glowing swirling time portal with a medieval castle and a pyramid inside it. "
          "Image 0 is the first friend, image 1 the second, image 2 the third: keep their hair, faces and clothes. "
          "Square composition, vivid colours. ")

TEST_BACKGROUNDS = {
    "hut": "inside a poor medieval peasant longhouse, earth floor with straw, a fire pit with smoke, wooden walls, "
           "a cow at the far end, warm light, empty of people, wide shot",
    "castle_hall": "a medieval castle great hall, long wooden feast table with a roast swan, stone walls with red "
                   "banners, tall windows, a golden throne, empty of people, wide shot",
}


def reference_png(name: str, path: str):
    """Our approved design, drawn by code, as a small reference picture (< 512 px)."""
    svg = _svg(420, 500, character(name, 210, 485, 0.66, pose_for(name, "idle")), bg="#ffffff")
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f.name, path], check=True)
    os.remove(f.name)


def generate(prompt: str, width: int, height: int, seed: int, refs=()):
    acc, tok = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    files = {"prompt": (None, prompt), "width": (None, str(width)), "height": (None, str(height)),
             "seed": (None, str(seed))}
    for i, ref in enumerate(refs[:4]):
        files[f"input_image_{i}"] = (os.path.basename(ref), open(ref, "rb"), "image/png")
    for attempt in range(3):
        r = requests.post(URL.format(acc=acc), headers={"Authorization": f"Bearer {tok}"}, files=files, timeout=180)
        if r.status_code == 200:
            ctype = r.headers.get("content-type", "")
            if ctype.startswith("image/"):
                return r.content
            data = r.json()
            img = (data.get("result") or {}).get("image") or data.get("image")
            if img:
                return base64.b64decode(img)
            raise RuntimeError(f"no image in response: {str(data)[:300]}")
        if r.status_code in (429, 500, 502, 503):
            time.sleep(10 * (attempt + 1))
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
    raise RuntimeError("gave up after retries")


def cut_out(src: str, dst: str):
    """Remove the plain background so the character can stand in any scene."""
    from rembg import remove
    with open(src, "rb") as f:
        out = remove(f.read())
    with open(dst, "wb") as f:
        f.write(out)


def run_test(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    log = []
    refs = {}
    for name in LOOK:
        refs[name] = os.path.join(out_dir, f"ref_{name.lower()}.png")
        reference_png(name, refs[name])

    def draw(path, prompt, w, h, seed, refs_used, cut=True):
        t0 = time.time()
        try:
            with open(path, "wb") as f:
                f.write(generate(prompt, w, h, seed=seed, refs=refs_used))
            log.append({"file": os.path.basename(path), "seconds": round(time.time() - t0, 1)})
            if cut:
                try:
                    cut_out(path, path.replace(".png", "_cut.png"))
                except Exception as ex:          # cut-out is a nice-to-have in the test
                    log.append({"file": os.path.basename(path), "cutout_error": str(ex)[:200]})
        except Exception as ex:
            log.append({"file": os.path.basename(path), "error": str(ex)[:400]})
        print(log[-1], flush=True)

    looks = {f"kai_{c}": LOOK["KAI"].format(hoodie=h) for c, h in KAI_HOODIES.items()}
    looks.update({"iris": LOOK["IRIS"], "bob": LOOK["BOB"]})
    for key, look in looks.items():
        name = key.split("_")[0].upper()
        versions = 1 if name == "KAI" else 2             # Kai already gets two looks
        note = (" The hoodie colour is different from image 0: use the colour written here." if name == "KAI" else "")
        for emo, action in TEST_EMOTIONS.items():
            for v in range(versions):
                prompt = (f"Full body character, {look}, {action}. Same character, same face, hair and outfit as in "
                          f"image 0.{note} Plain light grey background. {STYLE}")
                draw(os.path.join(out_dir, f"{key}_{emo}_{v + 1}.png"), prompt, 768, 1024, 100 + v * 7, [refs[name]])
    # the profile picture: a selfie of the trio
    for v in range(3):
        prompt = SELFIE.format(kai=looks["kai_blue"], iris=LOOK["IRIS"], bob=LOOK["BOB"]) + STYLE
        draw(os.path.join(out_dir, f"selfie_{v + 1}.png"), prompt, 1024, 1024, 500 + v * 13,
             [refs["KAI"], refs["IRIS"], refs["BOB"]], cut=False)
    for key, desc in TEST_BACKGROUNDS.items():
        for v in range(2):
            path = os.path.join(out_dir, f"bg_{key}_{v + 1}.png")
            try:
                with open(path, "wb") as f:
                    f.write(generate(f"{desc}. {STYLE}", 1344, 768, seed=300 + v * 11))
                log.append({"file": os.path.basename(path)})
            except Exception as ex:
                log.append({"file": os.path.basename(path), "error": str(ex)[:400]})
            print(log[-1], flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


if __name__ == "__main__":
    run_test(sys.argv[1] if len(sys.argv) > 1 else "art_test")
