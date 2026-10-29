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


# The rich look we want (what came out when the AI drew freely in the selfie test)
RICH_STYLE = ("high quality 2D character design for a modern adult animated comedy series, bold clean outlines, "
              "rich cel shading with soft highlights and shadows, detailed expressive face with expressive eyes, "
              "natural adult proportions, appealing and charismatic, vivid colours, professional studio quality, "
              "no text, no watermark")

KAI_DESIGN = ("a young man about 25 years old, slim, light skin, short black side-swept hair with the fringe falling "
              "to one side, friendly curious face, a {colour} hoodie with a front pocket and drawstrings, dark blue jeans, "
              "dark grey sneakers")
DESIGN_COLOURS = ["royal blue", "sunflower yellow", "deep red", "forest green"]


def run_design(out_dir: str):
    """Round 1 for Kai: fresh designs (no old reference), 2 per hoodie colour. The user picks the master."""
    os.makedirs(out_dir, exist_ok=True)
    log = []
    for colour in DESIGN_COLOURS:
        for v in range(2):
            prompt = (f"Full body character design of {KAI_DESIGN.format(colour=colour)}, standing in a relaxed natural "
                      f"pose, slight confident smile, front view turned slightly to the side, whole body visible from "
                      f"head to shoes, plain light grey background. {RICH_STYLE}")
            path = os.path.join(out_dir, f"kai_{colour.split()[-1]}_{colour.split()[0]}_{v + 1}.png")
            try:
                with open(path, "wb") as f:
                    f.write(generate(prompt, 768, 1024, seed=1000 + v * 37 + DESIGN_COLOURS.index(colour)))
                log.append({"file": os.path.basename(path), "prompt": prompt})
            except Exception as ex:
                log.append({"file": os.path.basename(path), "error": str(ex)[:400]})
            print(log[-1]["file"], log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


def run_kai_older(out_dir: str):
    """Round 2 for Kai: the chosen design (5, red) made about 26 years old. Same hair, hoodie and outfit."""
    os.makedirs(out_dir, exist_ok=True)
    ref = "characters/ai/kai_design5_ref.png"
    log = []
    look = KAI_DESIGN.replace("about 25 years old", "about 26 years old").format(colour="deep red")
    jobs = []
    for v in range(3):     # edits of design 5
        jobs.append((f"kai_older_edit_{v + 1}.png",
                     "The same character as in image 0, with exactly the same black side-swept hair, deep red hoodie, "
                     "dark blue jeans and dark grey sneakers, same pose and same art style, but make him look like a "
                     "man of about 26: a more defined jawline, slightly longer and less round face, adult features, "
                     "light stubble shadow, confident friendly grin. Full body, plain light grey background. "
                     + RICH_STYLE, [ref], 2000 + v * 41))
    for v in range(2):     # fresh drawings of the older Kai, design 5 as a guide
        jobs.append((f"kai_older_fresh_{v + 1}.png",
                     f"Full body character design of {look}, defined jawline, adult face, confident friendly grin, "
                     f"standing relaxed facing the viewer, whole body visible from head to shoes, plain light grey "
                     f"background. Keep the outfit and hair from image 0. {RICH_STYLE}", [ref], 2100 + v * 43))
    for name, prompt, refs, seed in jobs:
        path = os.path.join(out_dir, name)
        try:
            with open(path, "wb") as f:
                f.write(generate(prompt, 768, 1024, seed=seed, refs=refs))
            log.append({"file": name, "prompt": prompt})
        except Exception as ex:
            log.append({"file": name, "error": str(ex)[:400]})
        print(name, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


KAI_EMOTIONS = {
    "neutral": "standing relaxed, friendly smile, mouth closed",
    "talk_closed": "talking to a friend, one hand gesturing, mouth closed between words",
    "talk_open": "talking to a friend, one hand gesturing, mouth open mid-word",
    "excited": "super excited, big open grin, both fists up",
    "shocked": "extremely shocked, eyes wide, jaw dropped, both hands on his head",
    "laughing": "laughing hard, eyes squeezed shut, mouth wide open, one hand on his belly",
    "scared": "terrified, leaning back, hands up in front of him, eyes wide",
    "disgusted": "disgusted, face scrunched up, tongue out, leaning away",
    "thinking": "thinking, hand on chin, eyes looking up, mouth closed",
    "pointing": "pointing forward at something with one arm, curious amazed face, mouth open",
}


def run_kai_set(out_dir: str):
    """Kai's first emotion set, all drawn from the locked master (design D)."""
    os.makedirs(out_dir, exist_ok=True)
    ref = "characters/ai/kai_master_ref.png"
    log = []
    for emo, action in KAI_EMOTIONS.items():
        for v in range(2):
            name = f"kai_{emo}_{v + 1}.png"
            prompt = ("The exact same character as in image 0: same young face (about 22 years old, clean-shaven), "
                      "same short black side-swept hair, same deep red hoodie, dark blue jeans and dark grey sneakers, "
                      f"same art style. Now he is {action}. Full body, whole body visible from head to shoes, "
                      "plain light grey background. " + RICH_STYLE)
            path = os.path.join(out_dir, name)
            try:
                with open(path, "wb") as f:
                    f.write(generate(prompt, 768, 1024, seed=3000 + v * 53, refs=[ref]))
                log.append({"file": name, "prompt": prompt})
                try:
                    cut_out(path, path.replace(".png", "_cut.png"))
                except Exception as ex:
                    log.append({"file": name, "cutout_error": str(ex)[:200]})
            except Exception as ex:
                log.append({"file": name, "error": str(ex)[:400]})
            print(name, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


KAI_LOOK = ("the exact same character as in image 0: same young face (about 22 years old, clean-shaven), same short "
            "black side-swept hair with the fringe falling to the same side, same deep red hoodie with front pocket and "
            "drawstrings, same dark blue jeans and dark grey sneakers, same art style and colours")

TURNAROUND = {
    "front": "seen from the front, facing the viewer, both feet pointing towards the viewer",
    "3q_left": ("seen in three-quarter view: his whole body, hips, knees, feet and face are all turned towards the left "
                "side of the picture; both shoes point to the lower left, the far foot partly hidden behind the near foot"),
    "3q_right": ("seen in three-quarter view: his whole body, hips, knees, feet and face are all turned towards the right "
                 "side of the picture; both shoes point to the lower right, the far foot partly hidden behind the near foot"),
    "side_left": ("seen exactly from the side in profile, facing the left side of the picture; both shoes point to the "
                  "left, one foot slightly in front of the other, the far leg partly hidden"),
    "side_right": ("seen exactly from the side in profile, facing the right side of the picture; both shoes point to "
                   "the right, one foot slightly in front of the other, the far leg partly hidden"),
    "back": "seen from behind, his back to the viewer, back of his head and hood visible, both heels towards the viewer",
    "low_angle": ("dramatic worm's-eye view: the camera is on the floor looking steeply up at him, strong perspective, "
                  "big shoes close to the camera, his head small at the top, he looks down at the viewer"),
    "high_angle": ("dramatic bird's-eye view: the camera is high above looking steeply down at him, strong perspective, "
                   "his head and shoulders big, his feet small at the bottom, he looks up at the viewer"),
}


ANATOMY = ("Correct human anatomy and physics: the feet, knees and hips point the same way as the body, weight "
           "balanced, two hands with five fingers each, natural proportions.")


def run_kai_turnaround(out_dir: str):
    """Step 1 of the model sheet: neutral Kai from every angle, 2 versions each."""
    os.makedirs(out_dir, exist_ok=True)
    refs = ["characters/ai/kai_master_ref.png"]
    log = []
    only = [a for a in os.environ.get("ANGLES", "").split(",") if a]
    for angle, view in TURNAROUND.items():
        if only and angle not in only:
            continue
        for v in range(4):
            name = f"kai_turn_{angle}_{v + 1}.png"
            prompt = (f"Character turnaround sheet drawing of {KAI_LOOK}. He is standing relaxed in a natural pose with "
                      f"a calm friendly face, arms down, {view}. {ANATOMY} Full body, whole body visible from head to "
                      f"shoes, plain light grey background. {RICH_STYLE}")
            path = os.path.join(out_dir, name)
            try:
                with open(path, "wb") as f:
                    f.write(generate(prompt, 768, 1024, seed=5000 + v * 61, refs=refs))
                log.append({"file": name, "prompt": prompt})
            except Exception as ex:
                log.append({"file": name, "error": str(ex)[:400]})
            print(name, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


DESIGNS = {
    "iris": ("a smart confident young woman about 22 years old, slim, light brown skin, dark brown hair in a neat high "
             "ponytail, modern rectangular glasses, a fitted cobalt-blue blazer with the sleeves pushed up to the "
             "elbows over a white t-shirt, slim dark charcoal trousers, clean white sneakers, a slightly smug clever smile"),
    "bob": ("a big friendly clueless young man about 22 years old, tall and chubby with a round face, clean-shaven, "
            "messy light brown hair, a happy dopey grin, an oversized mustard-yellow puffer vest over a grey t-shirt, "
            "baggy khaki cargo pants, white sports socks pulled up with brown sandals"),
}


def run_designs(out_dir: str):
    """Fresh design round for Iris or Bob (env WHO=iris|bob): 8 versions, no reference. The user picks the master."""
    who = os.environ.get("WHO", "iris")
    os.makedirs(out_dir, exist_ok=True)
    log = []
    for v in range(8):
        name = f"{who}_design_{v + 1}.png"
        prompt = (f"Full body character design of {DESIGNS[who]}, standing relaxed in a natural pose facing the viewer, "
                  f"whole body visible from head to shoes, plain light grey background. {ANATOMY} {RICH_STYLE}")
        try:
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(generate(prompt, 768, 1024, seed=6000 + v * 71))
            log.append({"file": name, "prompt": prompt})
        except Exception as ex:
            log.append({"file": name, "error": str(ex)[:400]})
        print(name, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


MOUTHS = {   # Rhubarb Lip Sync mouth shapes (A and X = the closed base picture)
    "B": "lips slightly parted showing clenched teeth, as when saying 'ee' or 's'",
    "C": "mouth open medium, as when saying 'eh'",
    "D": "mouth wide open, jaw dropped, as when saying 'ah'",
    "E": "lips rounded open, as when saying 'oh'",
    "F": "lips pushed forward into a small round pucker, as when saying 'oo'",
    "G": "upper teeth resting on the lower lip, as when saying 'f'",
}


def run_demo_kai(out_dir: str):
    """Pictures for the Kai demo: two story shots with a prop, a talking base, and its mouth shapes."""
    from PIL import Image
    from .art_check import figure_box
    os.makedirs(out_dir, exist_ok=True)
    ref = ["characters/ai/kai_master_ref.png"]
    log = []

    def draw(name, prompt, w, h, seed, refs_used):
        path = os.path.join(out_dir, name)
        try:
            with open(path, "wb") as f:
                f.write(generate(prompt, w, h, seed=seed, refs=refs_used))
            log.append({"file": name, "prompt": prompt})
            print(name, "ok", flush=True)
            return path
        except Exception as ex:
            log.append({"file": name, "error": str(ex)[:400]})
            print(name, ex, flush=True)

    for v in range(2):   # story shot: the stone bread
        p = draw(f"kai_bread_{v + 1}.png",
                 f"{KAI_LOOK}. He holds up a hard dark brown medieval loaf of bread in one hand with small grey stones "
                 f"stuck in it, looking at it disgusted and shocked, mouth open. Full body, whole body visible from head "
                 f"to shoes. {ANATOMY} Plain light grey background. {RICH_STYLE}", 768, 1024, 7000 + v * 31, ref)
        if p:
            cut_out(p, p.replace(".png", "_cut.png"))
    base = draw("kai_talkbase.png",
                f"{KAI_LOOK}. Waist-up medium shot, three-quarter view, body and face turned slightly towards the left "
                f"side of the picture, explaining something calmly with one hand raised, mouth closed, eyes open. "
                f"{ANATOMY} Plain light grey background. {RICH_STYLE}", 768, 1024, 7100, ref)
    if base:
        cut_out(base, base.replace(".png", "_cut.png"))
        img = Image.open(base).convert("RGB")
        x0, y0, x1, y1 = figure_box(img)
        # the face: a square around the top of the figure (waist-up, so the head is roughly the top 40 %)
        side = min(512, int((y1 - y0) * 0.42))
        cx = (x0 + x1) // 2
        hx0 = max(0, min(img.width - side, cx - side // 2 - int(side * 0.05)))
        hy0 = max(0, y0 - int(side * 0.05))
        face = img.crop((hx0, hy0, hx0 + side, hy0 + side)).resize((512, 512), Image.LANCZOS)
        face_path = os.path.join(out_dir, "kai_talkbase_face.png")
        face.save(face_path)
        json.dump({"box": [hx0, hy0, side]}, open(os.path.join(out_dir, "face_box.json"), "w"))
        for shape, desc in MOUTHS.items():
            draw(f"kai_mouth_{shape}.png",
                 "Exactly the same picture as image 0: same face, eyes, eyebrows, hair, hoodie, lighting, framing and "
                 f"art style, nothing moved. Only the mouth changes: {desc}. {RICH_STYLE}",
                 512, 512, 7200, [face_path])
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


FACE_LOCK = ("Image 0 shows his whole look and outfit. Image 1 shows his exact face: keep that face exactly the same "
             "(same eyes, eyebrows, nose, face shape and hairline, about 22 years old, clean-shaven, not older, not angrier).")
KAI_REFS = ["characters/ai/kai_master_ref.png", "characters/ai/kai_face_ref.png"]

DEMO2_BASES = {   # name: (size, head share of the figure height, what he does)
    "hook": ((1024, 1024), 0.55, "Medium close-up from the chest up, filling the frame. He is extremely shocked: eyes wide, "
                                 "eyebrows raised, mouth open, both hands on his head."),
    "bread": ((768, 1024), 0.26, "Full body. He holds up a hard dark brown medieval loaf of bread in one hand with small grey "
                                 "stones stuck in it, looking at it with a disgusted surprised face, mouth open."),
    "talkA": ((768, 1024), 0.26, "Full body, three-quarter view turned slightly to the left side of the picture. He explains "
                                 "something with one hand raised palm up, mouth closed, eyes open, looking left."),
    "talkB": ((768, 1024), 0.26, "Full body, three-quarter view turned slightly to the left side of the picture, same stance. "
                                 "He makes a point by pointing his index finger up, mouth closed, eyes open, looking left."),
    "laugh": ((768, 1024), 0.26, "Full body. He laughs hard with eyes squeezed shut, mouth wide open, one hand on his belly."),
}


def face_square(img, head_frac):
    """(x, y, side): a square around the head, found from the figure's outline."""
    from .art_check import figure_box
    x0, y0, x1, y1 = figure_box(img)
    h = y1 - y0
    side = min(img.width, img.height, int(h * head_frac))
    top = img.crop((x0, y0, x1, y0 + max(10, int(h * head_frac * 0.7))))
    bx = figure_box(top)
    cx = x0 + (bx[0] + bx[2]) // 2
    x = max(0, min(img.width - side, cx - side // 2))
    y = max(0, min(img.height - side, y0 - int(side * 0.06)))
    return x, y, side


def run_demo2_bases(out_dir: str):
    """Demo v2, phase A: two candidates of each picture, face locked with two references."""
    os.makedirs(out_dir, exist_ok=True)
    log = []
    for name, ((w, h), _hf, action) in DEMO2_BASES.items():
        for v in range(2):
            fname = f"kai2_{name}_{v + 1}.png"
            prompt = f"{KAI_LOOK}. {FACE_LOCK} {action} {ANATOMY} Plain light grey background. {RICH_STYLE}"
            try:
                with open(os.path.join(out_dir, fname), "wb") as f:
                    f.write(generate(prompt, w, h, seed=8000 + v * 97, refs=KAI_REFS))
                log.append({"file": fname, "prompt": prompt})
            except Exception as ex:
                log.append({"file": fname, "error": str(ex)[:400]})
            print(fname, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


BLINK = "his eyes are fully closed in a relaxed blink, eyelids down, eyebrows unchanged"


def run_demo2_patches(out_dir: str):
    """Demo v2, phase B: for the chosen pictures (env PICKS, e.g. "hook=1,bread=2,talkA=1,talkB=2,laugh=1"),
    a cut-out, plus face crops edited for blinking and (talk pictures) every mouth shape."""
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    picks = dict(p.split("=") for p in os.environ["PICKS"].split(","))
    log = []
    for name, v in picks.items():
        src = f"characters/ai/demo2/kai2_{name}_{v}.png"
        base = os.path.join(out_dir, f"{name}.png")
        img = Image.open(src).convert("RGB")
        img.save(base)
        cut_out(base, base.replace(".png", "_cut.png"))
        x, y, side = face_square(img, DEMO2_BASES[name][1])
        face = img.crop((x, y, x + side, y + side)).resize((512, 512), Image.LANCZOS)
        face_path = os.path.join(out_dir, f"{name}_face.png")
        face.save(face_path)
        json.dump({"box": [x, y, side]}, open(os.path.join(out_dir, f"{name}_face_box.json"), "w"))
        edits = {} if name == "laugh" else {"blink": BLINK}
        if name.startswith("talk"):
            edits.update(MOUTHS)
        for key, desc in edits.items():
            fname = f"{name}_{key}.png"
            prompt = ("Exactly the same picture as image 0: same face, eyes, eyebrows, hair, clothes, lighting, framing "
                      f"and art style, nothing moved. Only change: {desc}. {RICH_STYLE}")
            try:
                with open(os.path.join(out_dir, fname), "wb") as f:
                    f.write(generate(prompt, 512, 512, seed=8200, refs=[face_path]))
                log.append({"file": fname})
            except Exception as ex:
                log.append({"file": fname, "error": str(ex)[:400]})
            print(fname, log[-1].get("error", "ok"), flush=True)
    with open(os.path.join(out_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=1)


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
    task = os.environ.get("TASK", "test")
    out = sys.argv[1] if len(sys.argv) > 1 else "art_test"
    {"test": run_test, "design": run_design, "kai_older": run_kai_older, "kai_set": run_kai_set, "kai_turnaround": run_kai_turnaround, "designs": run_designs, "demo_kai": run_demo_kai, "demo2_bases": run_demo2_bases, "demo2_patches": run_demo2_patches}[task](out)
