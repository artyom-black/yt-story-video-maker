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

QUESTION = """You are the strict quality checker for a cartoon YouTube video. The picture was drawn by an
image AI from this description:

"{desc}"

{kai}
Look very carefully at the picture and check for these mistakes:
1. A person or animal with the wrong number of heads, faces, arms, hands or legs, or two bodies melted together.
2. A person's face mixed with an animal or object (for example an animal nose growing out of a person's face).
3. An animal or heavy object floating in the air with nothing holding it up.
4. {red}
5. The picture clearly does not show what the description asks for (wrong place, wrong main subject, a dark or indoor scene drawn outdoors in daylight).
6. Any written words, letters or signs.

Small style details are fine. Only report real, clearly visible mistakes a viewer would notice.
Answer with JSON only, no other text:
{{"what_i_see": "<one short sentence>", "problems": ["<each real mistake, short>"], "verdict": "ok" or "redo"}}"""

KAI_NOTE = ("The main character Kai is a young man with short black hair who wears a deep red tunic. "
            "There must be exactly one Kai.")
RED_KAI = "Kai appears twice, or someone who is not Kai also wears red clothes."
RED_NO_KAI = "Anyone wears bright red clothes (no red-dressed person should be in this picture)."


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


def _parse(answer):
    m = re.search(r"\{.*\}", answer, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:
        d = {}
    problems = [str(p) for p in d.get("problems") or [] if str(p).strip()]
    verdict = str(d.get("verdict", "")).lower()
    ok = verdict == "ok" or (verdict != "redo" and not problems)
    if not d:
        ok, problems = True, ["(checker answer unreadable, picture kept): " + answer[:120]]
    return {"ok": ok, "problems": problems, "seen": d.get("what_i_see", "")}


def check(path, description, has_kai, model=MODEL):
    """{'ok': bool, 'problems': [...], 'seen': str}. Raises on the daily allowance (caller stops)."""
    text = QUESTION.format(desc=description, kai=KAI_NOTE if has_kai else "Kai is NOT in this picture.",
                           red=RED_KAI if has_kai else RED_NO_KAI)
    return _parse(_ask(text, _image_data_url(path), model))


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
