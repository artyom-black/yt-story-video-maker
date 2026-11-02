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
REPO = os.path.dirname(ROOT)
FACE_REF = os.path.join(REPO, "main-character.jpg")   # set from the story's CHARACTER line in jobs()


def face_ref(st):
    p = os.path.join(REPO, st.character) if getattr(st, "character", "") else ""
    return p if p and os.path.exists(p) else FACE_REF


# The channel's look: simple stick figures in detailed, colourful painted worlds (like the big explainer channels).
KAI_ID = ("the main character, a stick figure man exactly like image 0: a big round white head with a black outline, "
          "small black dot eyes, simple eyebrows and mouth, messy brown hair, thin black line arms and legs")
STYLE = ("Simple 2D stick figure cartoon in a clean, popular YouTube history explainer style: every person is a simple "
         "stick figure with a big round white head, small dot eyes, simple expressive eyebrows and mouth, and thin "
         "black line arms and legs, wearing simple flat-coloured clothes of the time. Every face is a plain flat white "
         "circle with tiny black dot eyes and a simple line mouth: no skin colour, no shading, no nose. The backgrounds are detailed, "
         "colourful, painted 2D cartoon scenes with bold clean outlines and soft light. Clear and easy to read. "
         "Absolutely no text, no letters, no words, no captions, no watermark.")
THUMB_STYLE = ("YouTube thumbnail in the same stick figure style: one big character with an extreme, clear facial "
               "expression, very bright colours, strong contrast, a detailed but uncluttered painted background. "
               "Absolutely no text, no letters, no words.")
W, H = 1280, 720
ONLY_KAI_RED = ""
SIZE_RULE = ("Real-life sizes: grown-ups are taller than children, doors are a bit taller than people, houses are much "
             "taller than people, animals, food, cups and tools are their real size next to a person.")
FACE_RULE = ("Only the main character has messy brown hair: every other person has clearly different hair (another "
             "colour or style, a headscarf, a beard or bald), so nobody looks like him. Every person and animal has a "
             "normal body: one head, two arms, two legs, animals with the right number of legs, nothing floating.")


def _place_rule(st):
    """Only what the line describes. The story's ERA is NOT pasted in (it put the same village, manor house,
    windmill and crowds into every picture); the period is given in a few words only."""
    period = (st.era.split(":")[0] if st.era else "the past").strip()
    return (f"Draw exactly and only what is described above: the place, the light and the framing; indoors stays "
            f"indoors, dark stays dark, a close-up stays a close-up. Show ONLY the people and animals the "
            f"description names: no extra people, no crowds, no extra animals, no buildings, windows or "
            f"landscape the description does not mention. Everything belongs to {period}: nothing modern; houses are "
            f"small medieval cottages of wood and mud with thick straw roofs. If the description names no place, draw a "
            f"simple medieval outdoor background (a wheat field or a muddy village lane under the sky): never a modern "
            f"room, never an empty white background. Objects and animals never have faces.")


CHECK_VERSION = 8          # raise when the checker learns a new kind of mistake: old pictures get looked at again


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
    return re.sub(r"\bKAI\b", "the main character (the stick figure in image 0 and image 1)", text)


def kai_refs(text, st, costume_ref, costume_rich_ref):
    """Kai's face + the right costume(s). 'KAI' = the normal costume, 'RICH KAI' = COSTUME_RICH.
    Returns (text with Kai explained, refs, index of the next free reference image)."""
    rich = "RICH KAI" in text
    poor = bool(re.search(r"(?<!RICH )\bKAI\b", text))
    if rich and poor:
        text = text.replace("RICH KAI", "Kai in his rich clothes (image 2)")
        text = re.sub(r"\bKAI\b", "Kai in his poor clothes (image 1)", text)
        return (text + ". Both are the same young man, with exactly the face and hair from image 0",
                [FACE_REF, costume_ref, costume_rich_ref], 3)
    if rich:
        return text.replace("RICH KAI", "the main character (the stick figure in image 0 and image 1)"), [FACE_REF, costume_rich_ref], 2
    if poor:
        return kai_in(text), [FACE_REF, costume_ref], 2
    return text, [], 0


def kai_clothes(text, st):
    rich = "RICH KAI" in text
    poor = bool(re.search(r"(?<!RICH )\bKAI\b", text))
    if rich and poor:
        return (f"Poor Kai wears exactly the clothes from image 1: {st.costume}. Rich Kai wears exactly the clothes "
                f"from image 2: {st.costume_rich}. Both of them are dressed in deep red. ")
    if rich:
        return (f"Kai wears exactly the clothes from image 1: {st.costume_rich}. Keep his face and hair exactly as "
                f"in image 0. ")
    if poor:
        return (f"The main character is a stick figure exactly like image 0: a big round flat white head, small dot "
                f"eyes, two thin black eyebrows, messy brown hair with a clean hairline (nothing on his forehead), and arms and legs drawn as thin black lines. He wears exactly the clothes "
                f"from image 1: {st.costume}. He is a grown man, always drawn in this same simple way. His face and body "
                f"show exactly the feeling described above (tired, scared, angry, happy...), never a default smile. ")
    return ""


def cast_slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def cast_in(text, cast, first_index):
    """Replace each CAST name written in capitals (THE COW -> 'the cow (the same one as in image 2: ...)').
    Returns (new text, [cast names used, in image order]). Max 4 reference images in total."""
    used = []
    found = []
    for name in cast:
        m = re.search(rf"\b{re.escape(name)}\b", text)
        if m:
            found.append((m.start(), -len(name), name))
    for _pos, _l, name in sorted(found):                     # in the order they appear in the sentence
        if first_index + len(used) < 4 and not is_place(cast[name]):
            idx = first_index + len(used)
            used.append(name)
            text = re.sub(rf"\b{re.escape(name)}\b",
                          f"{name.lower()} (exactly the same one as in image {idx}: {cast[name]})", text, count=1)
            text = re.sub(rf"\b{re.escape(name)}\b", name.lower(), text)
        else:                                                # no image slot left: describe it in words
            text = re.sub(rf"\b{re.escape(name)}\b", f"{name.lower()} ({cast[name]})", text, count=1)
            text = re.sub(rf"\b{re.escape(name)}\b", name.lower(), text)
    return text, used


def is_place(desc):
    """Places (a room, a house) are described in words, not shown as a reference picture: a reference picture of
    a room makes the AI copy its exact camera view and any people in it into every picture."""
    return not re.search(r"stick figure|\bman\b|\bwoman\b|\bboy\b|\bgirl\b|\bcow\b|\box(en)?\b|\bdog\b|"
                         r"\bhorse\b|\bpig\b|\bsheep\b|\bgoat\b|\bcat\b|\bbird\b|\bfalcon\b", desc, re.I)


def cast_ref(path):
    """The small reference copy of a cast picture."""
    return path[:-4] + "_ref.png"


def _named(path, prompt):
    """scene_007.png -> scene_007_<hash of the prompt>.png, so a changed prompt makes a new picture."""
    import hashlib
    root, ext = os.path.splitext(path)
    return f"{root}_{hashlib.sha1(prompt.encode()).hexdigest()[:8]}{ext}"


def picture_files(st, assets):
    """{key: path} for every picture: 'costume', 'scene_007', 'scene_007b', 'thumb_1'."""
    out = {}
    for name, path, prompt, *_ in jobs(st, assets):
        key = os.path.splitext(os.path.basename(path))[0].rsplit("_", 1)[0] if name != "costume" else "costume"
        out[key] = path
    return out


SPLIT = re.compile(r"^split (?:image|screen):\s*on the left (.+?);?\s*,?\s*on the right (.+)$", re.I | re.S)


def split_prompt(pic, st, costume_ref, costume_rich_ref, cast_paths, thumb=False):
    """'split image: on the left X, on the right Y' -> two pictures drawn separately and put side by side.
    (Drawing both halves in one go mixes them up: Kai with a cow's head, two Kais in one body.)"""
    m = SPLIT.match(pic.strip())
    if not m:
        return None
    halves = []
    for part in (m.group(1).strip(" ,;"), m.group(2).strip(" ,;")):
        text, refs, first = kai_refs(part, st, costume_ref, costume_rich_ref)
        text, used = cast_in(text, st.cast, first)
        refs = refs + [cast_ref(cast_paths[n]) for n in used]
        if thumb:
            prompt = f"{text}. One person only. {kai_clothes(part, st)}Tall picture. {THUMB_STYLE}"
        else:
            prompt = (f"{text}. One person only. {_place_rule(st)} {kai_clothes(part, st)}{ONLY_KAI_RED} {FACE_RULE} {SIZE_RULE} "
                      f"Tall picture. {STYLE}")
        halves.append([prompt, refs])
    return "SPLIT||" + json.dumps(halves)


def draw(prompt, w, h, seed, refs, out):
    """Draw one picture; a SPLIT prompt draws two halves and joins them with a white line in the middle."""
    if not prompt.startswith("SPLIT||"):
        return _gen(prompt, w, h, seed, refs, out)
    halves = json.loads(prompt[len("SPLIT||"):])
    hw = (w // 2) // 16 * 16
    parts = []
    for j, (pr, rf) in enumerate(halves):
        tmp = out + f".half{j}.png"
        _gen(pr, hw, h, seed + 101 * j, rf, tmp)
        parts.append(tmp)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    for j, tmp in enumerate(parts):
        im = Image.open(tmp).convert("RGB")
        s = max((w // 2) / im.width, h / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
        x0 = (im.width - w // 2) // 2
        canvas.paste(im.crop((x0, 0, x0 + w // 2, h)), (j * (w // 2), 0))
        os.remove(tmp)
    bar = max(6, w // 160)
    canvas.paste((255, 255, 255), (w // 2 - bar // 2, 0, w // 2 + bar // 2, h))
    canvas.save(out + ".part.png")
    os.replace(out + ".part.png", out)


def upgrade(path, prompt):
    """A picture that gets drawn again always gets today's rules (not the older prompt it was kept under)."""
    if prompt and not prompt.startswith("SPLIT||") and SIZE_RULE not in prompt:
        if FACE_RULE in prompt:
            prompt = prompt.replace(f"{FACE_RULE} 16:9", f"{FACE_RULE} {SIZE_RULE} 16:9")
        else:
            prompt = prompt.replace(f"{ONLY_KAI_RED} 16:9", f"{ONLY_KAI_RED} {FACE_RULE} {SIZE_RULE} 16:9")
        path = _named(path.rsplit("_", 1)[0] + ".png", prompt)
    return path, prompt


def jobs(st, assets):
    """Every picture the video needs, in the order they are made."""
    global FACE_REF
    FACE_REF = face_ref(st)
    costume = os.path.join(assets, "costume.png")
    costume_ref = os.path.join(assets, "costume_ref.png")
    costume_rich_ref = os.path.join(assets, "costume_rich_ref.png")
    out = [("costume", costume, None,
            f"Full body character design of {KAI_ID}. He wears {st.costume}. Standing relaxed, facing the viewer, a "
            f"friendly face, the whole body from head to shoes visible. Image 0 shows his exact face and hair: keep "
            f"them exactly the same. Plain light grey background. {STYLE}", 768, 1024, [FACE_REF])]
    if st.costume_rich:
        prompt = (f"Full body character design of {KAI_ID}. He wears {st.costume_rich}. Standing proudly, facing the "
                  f"viewer, a confident friendly face, the whole body from head to shoes visible. Image 0 shows his "
                  f"exact face and hair: keep them exactly the same. Plain light grey background. {STYLE}")
        out.append(("costume rich", _named(os.path.join(assets, "costume_rich.png"), prompt), prompt, 768, 1024,
                    [FACE_REF], None))
    # everyone and everything that comes back more than once gets one reference picture first
    cast_paths = {}
    for name, desc in st.cast.items():
        if is_place(desc):
            continue
        if re.search(r"stick figure|\bman\b|\bwoman\b|\bboy\b|\bgirl\b", desc):   # a person: alone, nothing around
            prompt = (f"Character reference of {desc}. One single person, the whole body from head to feet, standing "
                      f"facing the viewer, a calm normal face. Pure plain white background, nothing else. {STYLE}")
        elif re.search(r"\binside\b|\binterior\b|\broom\b", desc):               # a room: empty, no windows added
            prompt = (f"Reference picture of {desc}. Seen from inside, the whole room, empty: no people, no animals. "
                      f"Only the windows the description mentions, nothing outside. {STYLE}")
        else:                                                                          # a building, an animal
            prompt = (f"Reference picture of {desc}. One single subject, the whole subject clearly visible, no "
                      f"people. Plain simple background. {STYLE}")
        path = _named(os.path.join(assets, "cast", f"cast_{cast_slug(name)}.png"), prompt)
        cast_paths[name] = path
        out.append((f"cast {name.lower()}", path, prompt, 768, 768, [], None))
    for s in st.scenes:
        for i_pic, (_word, pic) in enumerate(s.all_pictures):
            k = "" if i_pic == 0 else f"x{i_pic + 1}"
            if not pic:
                continue
            path = os.path.join(assets, "pictures", f"scene_{s.number:03d}{k}.png")
            text, refs, first = kai_refs(pic, st, costume_ref, costume_rich_ref)
            text, used = cast_in(text, st.cast, first)
            refs = refs + [cast_ref(cast_paths[n]) for n in used]
            legacy = f"{text}. {_place_rule(st)} {kai_clothes(pic, st)}{ONLY_KAI_RED} 16:9 picture. {STYLE}"
            before = f"{text}. {_place_rule(st)} {kai_clothes(pic, st)}{ONLY_KAI_RED} {FACE_RULE} 16:9 picture. {STYLE}"
            place = _place_rule(st)
            if re.search(r"\bmodern\b|1[6-9]00s|laboratory|\b19\d\d\b|\b20\d\d\b", pic, re.I):
                place = "Draw exactly the place, time and light described above."      # a scene from another time
            if re.search(r"\b(night|midnight|dark)\b", pic, re.I) and not re.search(r"\b(dawn|sunrise|sunset)\b", pic, re.I):
                place += " It is night: dark, lit only by firelight, a lamp or the moon, no daylight anywhere."
            if re.search(r"\bno people\b|\bno humans\b", pic, re.I):
                place += " There are no people at all in this picture."
            prompt = (f"{text}. {place} {kai_clothes(pic, st)}{ONLY_KAI_RED} {FACE_RULE} {SIZE_RULE} "
                      f"16:9 picture. {STYLE}")
            v8 = prompt.replace(" If the description names no place, draw a simple medieval outdoor background (a wheat "
                                "field or a muddy village lane under the sky): never a modern room, never an empty white "
                                "background. Objects and animals never have faces.", "")
            asked = label(os.path.splitext(os.path.basename(path))[0]).lower() in redo_requests()
            for older in ([] if asked else (v8, before, legacy)):   # kept unless you asked to redraw it (the checker
                if os.path.exists(_named(path, older)):       # looks at it again and redraws it if it's wrong)
                    prompt = older
                    break
            sp = split_prompt(pic, st, costume_ref, costume_rich_ref, cast_paths)
            if sp:
                prompt = sp
            check_desc = pic                         # what the checker reads: cast names spelled out
            for n_, d_ in st.cast.items():
                check_desc = re.sub(rf"\b{re.escape(n_)}\b", f"{n_.lower()} ({d_})", check_desc)
            out.append((f"scene {s.number}{k}", _named(path, prompt), prompt, W, H, refs, check_desc))
    title_file = os.path.join(REPO, "thumbnail", re.sub(r'[\\/:*?"<>|]', "", st.title).strip() + ".png")
    for i, idea in enumerate([] if os.path.exists(title_file) else st.thumbnail_ideas[:3]):   # made by hand already
        path = os.path.join(assets, "pictures", f"thumb_{i + 1}.png")
        text, refs, first = kai_refs(idea, st, costume_ref, costume_rich_ref)
        text, used = cast_in(text, st.cast, first)
        refs = refs + [cast_ref(cast_paths[n]) for n in used]
        prompt = f"{text}. {kai_clothes(idea, st)}{THUMB_STYLE}"
        prompt = split_prompt(idea, st, costume_ref, costume_rich_ref, cast_paths, thumb=True) or prompt
        out.append((f"thumbnail {i + 1}", _named(path, prompt), prompt, W, H, refs, idea))
    # the costume entry: (name, path, prompt, w, h, refs) like the others
    c = out[0]
    out[0] = (c[0], _named(c[1], c[3]), c[3], c[4], c[5], c[6], None)
    return out


def _key(path):
    """pictures/scene_014x2_ab12cd34.png -> scene_014x2"""
    return os.path.basename(path).rsplit("_", 1)[0]


def label(key):
    """scene_014 -> '14', scene_014x2 -> '14b', thumb_1 -> 'T1' (the numbers on the picture sheet)."""
    m = re.match(r"scene_(\d+)(?:x(\d+))?$", key)
    if m:
        return str(int(m.group(1))) + ("" if not m.group(2) else "abcdefghij"[int(m.group(2)) - 1])
    m = re.match(r"thumb_(\d+)$", key)
    return f"T{m.group(1)}" if m else key


def redo_requests():
    """Pictures to draw again, typed when clicking Run (the REDO box), e.g. "12, 32b, T1"."""
    return {w.strip().lower() for w in re.split(r"[ ,;]+", os.environ.get("REDO", "")) if w.strip()}


def run(story_path, assets):
    from .picture_check import check
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors: " + "; ".join(st.errors))
    os.makedirs(os.path.join(assets, "pictures"), exist_ok=True)
    checks_path = os.path.join(assets, "checks.json")
    checks = json.load(open(checks_path)) if os.path.exists(checks_path) else {}
    redone_path = os.path.join(assets, "redone.json")
    redone = json.load(open(redone_path)) if os.path.exists(redone_path) else {}
    todo = jobs(st, assets)
    os.makedirs(os.path.join(assets, "cast"), exist_ok=True)
    if os.path.exists(todo[0][1]):
        small_ref(todo[0][1], os.path.join(assets, "costume_ref.png"))
    for name, path, *_ in todo:
        if name == "costume rich" and os.path.exists(path):
            small_ref(path, os.path.join(assets, "costume_rich_ref.png"))
        if name.startswith("cast ") and os.path.exists(path):
            small_ref(path, cast_ref(path))

    # pictures you asked to redo when clicking Run (each request is done once)
    for name, path, *_ in todo:
        lab = label(_key(path)).lower()
        if lab in redo_requests() and redone.get(lab) != os.path.basename(path) and os.path.exists(path):
            os.remove(path)
            redone[lab] = "pending"

    done, stopped = 0, ""
    tried, rejected, checker_on = 0, 0, True   # safety: a checker that rejects almost everything is switched off
    try:
        for i, (name, path, prompt, w, h, refs, desc) in enumerate(todo):
            key = os.path.basename(path)
            if os.path.exists(path) and desc is not None and checks.get(key, {}).get("v") != CHECK_VERSION \
                    and checks.get(key, {}).get("status") != "unchecked":
                try:                                  # drawn before the checker learned something new: look again
                    res = check(path, desc, bool(re.search(r"\bKAI\b", desc)))
                except RuntimeError as ex:
                    if "ALLOWANCE" in str(ex):
                        raise AllowanceUsedUp(str(ex))
                    res = {"ok": True, "problems": []}
                if res.get("severe"):
                    print(f"  {name}: re-check found {'; '.join(res['problems'])} - drawing it again", flush=True)
                    os.remove(path)
                    path, prompt = upgrade(path, prompt)
                    key = os.path.basename(path)
                else:
                    checks[key] = dict(checks.get(key, {}), v=CHECK_VERSION,
                                       status=checks.get(key, {}).get("status", "ok"))
            if os.path.exists(path) and (desc is None or checks.get(key, {}).get("status") != "unchecked"):
                done += 1
                continue
            lab = label(_key(path)).lower()
            extra = 104729 * (1 if redone.get(lab) == "pending" else 0)
            if not os.path.exists(path) and desc is not None:
                path, prompt = upgrade(path, prompt)
                key = os.path.basename(path)
            if not os.path.exists(path):
                best = None
                for attempt in range(3):            # draw, check, draw again if the checker finds a mistake
                    tmp = path + f".try{attempt}.png"
                    try:
                        draw(prompt, w, h, seed=1000 + i * 17 + 7919 * attempt + extra, refs=refs, out=tmp)
                    except AllowanceUsedUp:
                        raise
                    except Exception:
                        try:
                            draw(prompt if prompt.startswith("SPLIT||") else prompt + " Friendly and tasteful.", w, h, seed=5000 + i * 31 + 7919 * attempt + extra,
                                 refs=refs, out=tmp)
                        except AllowanceUsedUp:
                            raise
                        except Exception as ex2:
                            print(f"{name}: drawing failed ({str(ex2)[:150]})", flush=True)
                            continue
                    if desc is None or not checker_on:   # reference sheets are not checked
                        best = (tmp, {"ok": True, "problems": []})
                        break
                    try:
                        res = check(tmp, desc, bool(re.search(r"\bKAI\b", desc)))
                    except RuntimeError as ex:
                        if "ALLOWANCE" in str(ex):
                            os.replace(tmp, path)
                            checks[key] = {"status": "unchecked"}
                            raise AllowanceUsedUp(str(ex))
                        res = {"ok": True, "problems": ["checker error: " + str(ex)[:120]]}
                    if attempt == 0:
                        tried += 1
                        rejected += 1 if res.get("severe") else 0
                        if tried >= 12 and rejected / tried > 0.6 and checker_on:
                            checker_on = False
                            print("WARNING: the checker rejected most pictures - switched off for this run, "
                                  "pictures are kept as drawn", flush=True)
                    print(f"  {name} try {attempt + 1}: {'ok' if res['ok'] else 'REDO ' + '; '.join(res['problems'])}",
                          flush=True)
                    if best is None or (res["ok"] and not best[1]["ok"]) or \
                            (res["ok"] == best[1]["ok"] and len(res["problems"]) < len(best[1]["problems"])):
                        if best:
                            os.remove(best[0])
                        best = (tmp, res)
                    else:
                        os.remove(tmp)
                    if res["ok"] or (attempt >= 1 and not res.get("severe")):
                        break                       # small problems: 2 tries; monsters: 3 tries
                if best is None:
                    continue
                os.replace(best[0], path)
                checks[key] = {"status": "ok" if best[1]["ok"] else "bad" if best[1].get("severe") else "kept_with_problems",
                               "problems": best[1]["problems"], "tries": attempt + 1, "v": CHECK_VERSION}
                if redone.get(lab) == "pending":
                    redone[lab] = key
            else:                                    # drawn yesterday, but the check ran out of allowance
                res = check(path, desc, bool(re.search(r"\bKAI\b", desc)))
                if res["ok"]:
                    checks[key] = {"status": "ok", "problems": [], "tries": 1}
                else:
                    os.remove(path)
                    checks.pop(key, None)
                    continue
            done += 1
            print(f"[{done}/{len(todo)}] {name}", flush=True)
            if name == "costume":
                small_ref(path, os.path.join(assets, "costume_ref.png"))
            elif name == "costume rich":
                small_ref(path, os.path.join(assets, "costume_rich_ref.png"))
            elif name.startswith("cast "):
                small_ref(path, cast_ref(path))
    except AllowanceUsedUp as ex:
        stopped = str(ex)[:200]
        print("Daily picture allowance used up - the next run continues from here.", flush=True)
    for f in os.listdir(os.path.join(assets, "pictures")):
        if ".try" in f:
            os.remove(os.path.join(assets, "pictures", f))
    json.dump(checks, open(checks_path, "w"), indent=1)
    json.dump(redone, open(redone_path, "w"), indent=1)
    sheets(st, assets, checks)
    done = sum(1 for _n, pth, *_ in todo if os.path.exists(pth))     # all pictures that exist, not only this run's
    status = {"done": done, "total": len(todo), "complete": done == len(todo), "stopped": stopped,
              "checker": "on" if checker_on else "switched off (rejected too much)",
              "kept_with_problems": sorted(label(_key(k)) for k, v in checks.items()
                                           if v.get("status") == "kept_with_problems")}
    json.dump(status, open(os.path.join(assets, "pictures_status.json"), "w"), indent=1)
    print(status)
    return status


def sheets(st, assets, checks, per=24):
    """Picture sheets: every picture with its number (the numbers you can type in the REDO box when clicking Run).
    A red frame = the checker still saw a problem after 3 tries."""
    from PIL import ImageDraw, ImageFont
    out_dir = os.path.join(assets, "sheets")
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    items = [(label(_key(p)), p) for _n, p, *_ in jobs(st, assets)[1:] if os.path.exists(p)]
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    cols, tw, th = 4, 480, 270
    for n in range(0, len(items), per):
        part = items[n:n + per]
        rows = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), "white")
        d = ImageDraw.Draw(sheet)
        for i, (lab, p) in enumerate(part):
            x, y = (i % cols) * tw, (i // cols) * th
            sheet.paste(Image.open(p).convert("RGB").resize((tw - 6, th - 6)), (x + 3, y + 3))
            if checks.get(os.path.basename(p), {}).get("status") == "kept_with_problems":
                d.rectangle([x + 2, y + 2, x + tw - 3, y + th - 3], outline=(230, 0, 0), width=8)
            d.rectangle([x + 3, y + 3, x + 18 + 20 * len(lab), y + 44], fill=(0, 0, 0))
            d.text((x + 10, y + 7), lab, font=font, fill=(255, 255, 255))
        sheet.save(os.path.join(out_dir, f"sheet_{n // per + 1:02d}.jpg"), quality=85)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
