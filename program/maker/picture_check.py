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
  "people_in_red": <how many people wear mostly red clothes>,
  "young_men_with_short_black_hair": <how many>,
  "broken_body": <true if any person or animal has two heads, extra or missing arms, hands or legs, or two bodies melted together>,
  "face_mixed": <true if a person's face has an animal part or object growing out of it>,
  "floating": <true if an animal, a person or a heavy object hangs in the air with nothing holding it>,
  "indoors": <true if the scene is inside a building or room>,
  "has_text": <true if there are written words or letters>,
  "what_i_see": "<one short sentence>"}}"""

INDOOR = r"\b(inside|indoors|HOUSE|BEDCHAMBER|GREAT HALL|room|hall|chapel|church|kitchen|cellar|stable|hut|longhouse|tower room)\b"
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
    if yes("floating"):
        problems.append("something floating in the air")
    if yes("has_text"):
        problems.append("written text in the picture")
    if num("people_in_red") > max(n_kai, 0) + 0:
        problems.append(f"{num('people_in_red')} people in red (only Kai may wear red)")
    if n_kai and num("young_men_with_short_black_hair") > n_kai:
        problems.append("Kai appears more often than he should")
    want_in = bool(re.search(INDOOR, description, re.I)) and not re.search(OUTDOOR, description, re.I)
    want_out = bool(re.search(OUTDOOR, description, re.I)) and not re.search(INDOOR, description, re.I)
    if "indoors" in d and want_in and not yes("indoors"):
        problems.append("should be indoors but is drawn outside")
    if "indoors" in d and want_out and yes("indoors"):
        problems.append("should be outdoors but is drawn inside")
    return {"ok": not problems, "problems": problems, "seen": str(d.get("what_i_see", ""))}


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
