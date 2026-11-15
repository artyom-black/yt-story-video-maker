"""Redraw one small part of a finished picture (a wrong hand, an extra leg) and keep everything else.

Usage:  python -m maker.edit_patch IMAGE "x0,y0,x1,y1" "what the part should show" COUNT OUT_DIR
The box is cut out, redrawn by the picture model with the cut-out as image 0, and pasted back with soft edges.
Writes OUT_DIR/patch_1.png ... (the whole picture, fixed) and OUT_DIR/patch_crops.jpg.
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

from .art_lab import generate


def main(src, box, what, count, out):
    os.makedirs(out, exist_ok=True)
    x0, y0, x1, y1 = [int(v) for v in box.split(",")]
    full = Image.open(src).convert("RGB")
    crop = full.crop((x0, y0, x1, y1))
    w, h = crop.size
    ref = os.path.join(out, "crop_in.png")
    crop.resize((w * 2, h * 2), Image.LANCZOS).save(ref)
    prompt = ("Redraw image 0 exactly: the same flat 2D cartoon style, the same colours, outlines, framing and every "
              f"shape in the same place, with only this change: {what}. Nothing else changes. No text.")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((w // 8, h // 8, w - w // 8, h - h // 8), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) // 16))
    made = []
    for i in range(1, count + 1):
        try:
            png = generate(prompt, w * 2, h * 2, random.randint(1, 10**9), refs=[ref])
        except Exception as ex:
            print("version", i, "failed:", str(ex)[:200])
            continue
        p = os.path.join(out, f"new_{i}.png")
        open(p, "wb").write(png)
        new = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
        fixed = full.copy()
        fixed.paste(Image.composite(new, crop, mask), (x0, y0))
        fixed.save(os.path.join(out, f"patch_{i}.png"))
        made.append(fixed.crop((x0, y0, x1, y1)))
    if made:
        sheet = Image.new("RGB", (w * (len(made) + 1), h), "white")
        sheet.paste(crop, (0, 0))
        for k, m in enumerate(made, 1):
            sheet.paste(m, (k * w, 0))
        sheet.save(os.path.join(out, "patch_crops.jpg"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
