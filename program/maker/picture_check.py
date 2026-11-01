"""The picture checker: a vision AI looks at every new picture before it goes into a video.

It catches what the drawing AI gets wrong: two heads, an animal's face melted into a person, things
floating in the air, extra people in Kai's red, a picture that doesn't match the sentence. A picture
that fails is drawn again (pictures.py).

Uses a Cloudflare Workers AI vision model (a check costs about a quarter of what drawing a picture
costs, from the same free daily allowance).

Test on pictures that already exist:
    python -m maker.picture_check test STORY.txt ASSETS_DIR [MODEL] [key key ...]
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import time

import requests
from PIL import Image

MODEL = os.environ.get("CHECK_MODEL", "@cf/meta/llama-4-scout-17b-16e-instruct")

QUESTION = """Look carefully at this cartoon picture and answer these questions about what you SEE.
Answer with JSON only, no other text:
{{"people": <how many people are in the picture>,
  "people_with_messy_brown_hair": <how many people have messy brown hair>,
  "broken_body": <true if any person or animal has two heads, extra or missing arms, hands, fingers or legs, twisted broken-looking fingers, or two bodies melted together>,
  "size_wrong": <true if sizes are clearly unreal: a person as big as a house, a grown man drawn as small as a child next to others, or food, a cup or a tool bigger than a person's chest>,
  "face_mixed": <true if a person has an animal's head or face, or an animal part or object growing out of their face>,
  "animal_mixed": <true if any animal looks like two different animals mixed together, e.g. a cow with sheep wool or a dog with a bird's beak>,
  "through_body": <true if a pole, bed post, sword or other object goes straight through a person's body>,
  "fire_in_wrong_place": <true if fire burns in a bowl or bucket of water, in a basin, on the floor, in the air or on a person, instead of in a fireplace, fire pit, torch, candle, lamp or campfire>,
  "two_suns_or_moons": <true if there is more than one sun or more than one moon in the sky>,
  "floating": <true if an animal, a person or an object (a bowl, a cup, a tool) hangs in the air with no hand, table or floor holding it>,
  "indoors": <true if the scene is inside a building or room>,
  "has_text": <true if there are written words or letters>,
  "looks_like_a_photo": <true if it looks like a real photograph or a photorealistic 3D render, not a drawn cartoon>,
  "what_i_see": "<one short sentence>"}}"""

INDOOR = r"\b(inside|indoors|HUT|HOUSE|BEDCHAMBER|GREAT HALL|room|hall|chapel|church|kitchen|cellar|stable|hut|longhouse|tower room)\b"
OUTDOOR = r"\b(field|lane|village|forest|stream|river|meadow|yard|outside|outdoor|battlefield|harbour|road|sky|hill|garden)\b"


def _image_data_url(path, max_w=768):
    im = Image.open(path).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _ask(text, data_url, model):
    acc, tok = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    head = {"Authorization": f"Bearer {tok}"}
    messages = [{"role": "user", "content": [{"type": "text", "text": text},
                                             {"type": "image_url", "image_url": {"url": data_url}}]}]
    last = ""
    for attempt in range(3):
        # the OpenAI-style endpoint first, then the native one
        for url, body in (
            (f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/v1/chat/completions",
             {"model": model, "messages": messages, "max_tokens": 300, "temperature": 0}),
            (f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}",
             {"messages": messages, "max_tokens": 300, "temperature": 0}),
        ):
            r = requests.post(url, headers=head, json=body, timeout=120)
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            if r.status_code == 200:
                d = r.json()
                if "choices" in d:
                    return d["choices"][0]["message"]["content"]
                res = d.get("result") or {}
                out = res.get("response")
                if isinstance(out, (dict, list)):
                    return json.dumps(out)
                if out:
                    return out
            if r.status_code == 429 and ("daily" in r.text.lower() or "neuron" in r.text.lower()):
                raise RuntimeError("FREE DAILY ALLOWANCE USED UP (resets 00:00 UTC = 04:00 Armenia). " + last)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("checker gave up: " + last)


def _parse(answer, description, n_kai):
    m = re.search(r"\{.*\}", answer, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:
        d = {}
    if not d:
        return {"ok": True, "problems": ["(checker answer unreadable, picture kept)"], "seen": answer[:120]}
    num = lambda k: int(d.get(k) or 0) if str(d.get(k, 0)).strip("-").isdigit() else 0
    yes = lambda k: d.get(k) is True or str(d.get(k)).lower() == "true"
    problems = []
    if yes("broken_body"):
        problems.append("broken body (extra head/limbs or merged bodies)")
    if yes("face_mixed"):
        problems.append("a face mixed with an animal or object")
    if yes("size_wrong"):
        problems.append("sizes are unreal (a giant or tiny person, giant food)")
    if yes("animal_mixed"):
        problems.append("an animal mixed from two animals")
    if yes("through_body"):
        problems.append("an object goes through a body")
    if yes("fire_in_wrong_place"):
        problems.append("fire burning in a place that makes no sense")
    if yes("two_suns_or_moons"):
        problems.append("two moons or two suns")
    if re.search(r"\bno (people|humans)\b", description, re.I) and num("people") > 0:
        problems.append(f"{num('people')} people in a picture that should have none")
    if yes("floating"):
        problems.append("something floating in the air")
    if yes("looks_like_a_photo"):
        problems.append("looks like a real photo, not our cartoon style")
    if yes("has_text"):
        problems.append("written text in the picture")
    if n_kai and num("people_with_messy_brown_hair") > n_kai:
        problems.append("Kai appears more often than he should")
    want_in = bool(re.search(INDOOR, description, re.I)) and not re.search(OUTDOOR, description, re.I)
    want_out = bool(re.search(OUTDOOR, description, re.I)) and not re.search(INDOOR, description, re.I)
    if "indoors" in d and want_in and not yes("indoors"):
        problems.append("should be indoors but is drawn outside")
    if "indoors" in d and want_out and yes("indoors"):
        problems.append("should be outdoors but is drawn inside")
    severe = any(w in p_ for p_ in problems for w in ("broken body", "face mixed", "real photo", "Kai appears", "two animals", "through a body", "fire burning", "sizes are unreal"))
    return {"ok": not problems, "severe": severe, "problems": problems, "seen": str(d.get("what_i_see", ""))}


def check(path, description, has_kai, model=MODEL):
    """{'ok': bool, 'problems': [...], 'seen': str}. Raises on the daily allowance (caller stops).
    The vision AI only describes what it sees (counts, yes/no); the rules decide, so it can't nitpick."""
    n_kai = (2 if ("RICH KAI" in description and re.search(r"(?<!RICH )\bKAI\b", description)) else 1) if has_kai else 0
    return _parse(_ask(QUESTION, _image_data_url(path), model), description, n_kai)


def _test(story, assets, model, keys):
    import glob
    from .script import load
    st = load(story)
    files = {}
    for f in sorted(glob.glob(os.path.join(assets, "pictures", "scene_*.png"))):
        files[os.path.basename(f).rsplit("_", 1)[0]] = f       # scene_014x2_<hash>.png -> scene_014x2
    desc = {}
    for s in st.scenes:
        for i, (_w, pic) in enumerate(s.all_pictures):
            desc[f"scene_{s.number:03d}" + ("" if i == 0 else f"x{i + 1}")] = pic
    keys = keys or [k for k in files if k.startswith("scene_") and os.path.exists(files[k])]
    out = {}
    for k in keys:
        p = files.get(k)
        if not p or not os.path.exists(p):
            print(f"{k}: no file")
            continue
        t0 = time.time()
        res = check(p, desc[k], bool(re.search(r"\bKAI\b", desc[k])), model)
        out[k] = res
        print(f"{k:14s} {'OK  ' if res['ok'] else 'REDO'} {time.time() - t0:4.1f}s  {res['seen'][:90]}")
        for pr in res["problems"]:
            print(f"{'':20s}- {pr}")
    json.dump(out, open("check_test.json", "w"), indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "test":
        a = sys.argv[2:]
        _test(a[0], a[1], a[2] if len(a) > 2 else MODEL, a[3:])
