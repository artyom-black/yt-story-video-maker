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
# Everybody except Kai stays out of his signature colour, so viewers always know who Kai is.
ONLY_KAI_RED = "Nobody except Kai wears red: other people wear plain brown, beige, grey or green clothes."
# added later; pictures drawn before it was added are kept (see "legacy" in jobs), new ones get it
FACE_RULE = ("Only Kai has Kai's face and black hair: every other person has a clearly different face, hair "
             "colour and age. Every person and animal has a normal body: one head, two arms, two legs.")


def _place_rule(st):
    """The scene's own place, light and framing come first; the era only adds period details.
    (Before this, the era's 'muddy lanes, fields, church' was drawn into every picture, so indoor
    and night scenes came out in a sunny street.)"""
    return (f"Draw exactly the place, light and framing described above: indoors stays indoors, dark stays "
            f"dark, a close-up stays a close-up; add no streets, fields or buildings the description does not "
            f"mention. Time period, only for clothes, tools and buildings: {st.era}.")


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
    return re.sub(r"\bKAI\b", "Kai (the young man in image 0 and image 1)", text)


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
        return text.replace("RICH KAI", "Kai (the young man in image 0 and image 1)"), [FACE_REF, costume_rich_ref], 2
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
        return (f"Kai wears exactly the clothes from image 1: {st.costume}. Keep his face and hair exactly as in "
                f"image 0. ")
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
        if first_index + len(used) < 4:
            idx = first_index + len(used)
            used.append(name)
            text = re.sub(rf"\b{re.escape(name)}\b",
                          f"{name.lower()} (exactly the same one as in image {idx}: {cast[name]})", text, count=1)
            text = re.sub(rf"\b{re.escape(name)}\b", name.lower(), text)
        else:                                                # no image slot left: describe it in words
            text = re.sub(rf"\b{re.escape(name)}\b", f"{name.lower()} ({cast[name]})", text, count=1)
            text = re.sub(rf"\b{re.escape(name)}\b", name.lower(), text)
    return text, used


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


def jobs(st, assets):
    """Every picture the video needs, in the order they are made."""
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
        prompt = (f"Reference design sheet of {desc}. One single subject, the whole subject clearly visible, "
                  f"seen from the front at a slight angle, plain light grey background. "
                  f"Time period: {st.era}. {STYLE}")
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
            prompt = f"{text}. {_place_rule(st)} {kai_clothes(pic, st)}{ONLY_KAI_RED} {FACE_RULE} 16:9 picture. {STYLE}"
            if os.path.exists(_named(path, legacy)):          # already drawn with the older rules: keep it
                prompt = legacy
            check_desc = pic                         # what the checker reads: cast names spelled out
            for n_, d_ in st.cast.items():
                check_desc = re.sub(rf"\b{re.escape(n_)}\b", f"{n_.lower()} ({d_})", check_desc)
            out.append((f"scene {s.number}{k}", _named(path, prompt), prompt, W, H, refs, check_desc))
    for i, idea in enumerate(st.thumbnail_ideas[:3]):
        path = os.path.join(assets, "pictures", f"thumb_{i + 1}.png")
        text, refs, first = kai_refs(idea, st, costume_ref, costume_rich_ref)
        text, used = cast_in(text, st.cast, first)
        refs = refs + [cast_ref(cast_paths[n]) for n in used]
        prompt = f"{text}. {kai_clothes(idea, st)}{THUMB_STYLE}"
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
            if os.path.exists(path) and (desc is None or checks.get(key, {}).get("status") != "unchecked"):
                done += 1
                continue
            lab = label(_key(path)).lower()
            extra = 104729 * (1 if redone.get(lab) == "pending" else 0)
            if not os.path.exists(path):
                best = None
                for attempt in range(2):            # draw, check, and draw once more if the checker finds a mistake
                    tmp = path + f".try{attempt}.png"
                    try:
                        _gen(prompt, w, h, seed=1000 + i * 17 + 7919 * attempt + extra, refs=refs, out=tmp)
                    except AllowanceUsedUp:
                        raise
                    except Exception:
                        try:
                            _gen(prompt + " Friendly and tasteful.", w, h, seed=5000 + i * 31 + 7919 * attempt + extra,
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
                        rejected += 0 if res["ok"] else 1
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
                    if res["ok"]:
                        break
                if best is None:
                    continue
                os.replace(best[0], path)
                checks[key] = {"status": "ok" if best[1]["ok"] else "kept_with_problems",
                               "problems": best[1]["problems"], "tries": attempt + 1}
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
