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
    out = [("costume", costume, None,
            f"Full body character design of {KAI_ID}. He wears {st.costume}. Standing relaxed, facing the viewer, a "
            f"friendly face, the whole body from head to shoes visible. Image 0 shows his exact face and hair: keep "
            f"them exactly the same. Plain light grey background. {STYLE}", 768, 1024, [FACE_REF])]
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
            if re.search(r"\bKAI\b", pic):
                text, used = cast_in(kai_in(pic), st.cast, 2)
                prompt = (f"{text}. {_place_rule(st)} Kai wears exactly the clothes from image 1: "
                          f"{st.costume}. Keep his face and hair exactly as in image 0. {ONLY_KAI_RED} "
                          f"16:9 picture. {STYLE}")
                refs = [FACE_REF, costume_ref] + [cast_ref(cast_paths[n]) for n in used]
            else:
                text, used = cast_in(pic, st.cast, 0)
                prompt = f"{text}. {_place_rule(st)} {ONLY_KAI_RED} 16:9 picture. {STYLE}"
                refs = [cast_ref(cast_paths[n]) for n in used]
            check_desc = pic                         # what the checker reads: cast names spelled out
            for n_, d_ in st.cast.items():
                check_desc = re.sub(rf"\b{re.escape(n_)}\b", f"{n_.lower()} ({d_})", check_desc)
            out.append((f"scene {s.number}{k}", _named(path, prompt), prompt, W, H, refs, check_desc))
    for i, idea in enumerate(st.thumbnail_ideas[:3]):
        path = os.path.join(assets, "pictures", f"thumb_{i + 1}.png")
        prompt = (f"{kai_in(idea)}. Kai wears {st.costume}. Keep his face and hair exactly as in image 0. "
                  f"{THUMB_STYLE}")
        out.append((f"thumbnail {i + 1}", _named(path, prompt), prompt, W, H, [FACE_REF, costume_ref], idea))
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


def redo_requests(slug):
    """stories/redo.txt, one line per video:  001-medieval-peasant-day: 1 1b 12 32b"""
    want = set()
    path = os.path.join(ROOT, "stories", "redo.txt")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            name, _, rest = line.partition(":")
            if name.strip() == slug:
                want |= {w.strip().lower() for w in re.split(r"[ ,]+", rest) if w.strip()}
    return want


def run(story_path, assets):
    from .picture_check import check
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors: " + "; ".join(st.errors))
    slug = os.path.splitext(os.path.basename(story_path))[0]
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
        if name.startswith("cast ") and os.path.exists(path):
            small_ref(path, cast_ref(path))

    # pictures you asked to redo in stories/redo.txt (each request is done once)
    for name, path, *_ in todo:
        lab = label(_key(path)).lower()
        if lab in redo_requests(slug) and redone.get(lab) != os.path.basename(path) and os.path.exists(path):
            os.remove(path)
            redone[lab] = "pending"

    done, stopped = 0, ""
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
                for attempt in range(3):            # draw, check, and draw again if the checker finds a mistake
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
                    if desc is None:                 # the costume sheet is not checked
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
              "kept_with_problems": sorted(label(_key(k)) for k, v in checks.items()
                                           if v.get("status") == "kept_with_problems")}
    json.dump(status, open(os.path.join(assets, "pictures_status.json"), "w"), indent=1)
    print(status)
    return status


def sheets(st, assets, checks, per=24):
    """Picture sheets: every picture with its number (the numbers you can put in stories/redo.txt).
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
