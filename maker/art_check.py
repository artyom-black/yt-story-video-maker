"""Close-up check sheet: for every picture, the whole figure plus zoomed crops of the head, the hands area
and the feet, side by side. Used to catch physics mistakes (feet pointing the wrong way, extra fingers,
a changed face) before anybody approves a picture.

Usage:  python -m maker.art_check out.jpg pic1.png pic2.png ...
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image, ImageDraw

ROW_H = 360


def figure_box(img: Image.Image):
    """Bounding box of the character: everything that differs clearly from the plain background colour."""
    a = np.asarray(img.convert("RGB")).astype(int)
    corners = np.array([a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]])
    bg = np.median(corners, axis=0)
    mask = np.abs(a - bg).sum(axis=2) > 40
    mask[-int(a.shape[0] * 0.03):] = False          # ignore the bottom edge
    ys, xs = np.where(mask)
    if not len(xs):
        return 0, 0, img.width, img.height
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def crops(img: Image.Image):
    x0, y0, x1, y1 = figure_box(img)
    h = y1 - y0
    pad = int(0.04 * h)
    W, H = img.size

    def box(a, b, c, d):
        return max(0, a), max(0, b), min(W, c), min(H, d)

    whole = img
    head = img.crop(box(x0 - pad, y0 - pad, x1 + pad, y0 + int(0.22 * h)))
    hands = img.crop(box(x0 - pad, y0 + int(0.25 * h), x1 + pad, y0 + int(0.60 * h)))
    feet = img.crop(box(x0 - pad, y0 + int(0.72 * h), x1 + pad, y1 + pad))
    return [whole, head, hands, feet]


def sheet(out: str, paths: list[str]):
    rows = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        parts = [c.resize((max(1, int(c.width * ROW_H / max(1, c.height))), ROW_H)) for c in crops(img)]
        w = sum(c.width for c in parts) + 10 * len(parts)
        row = Image.new("RGB", (w, ROW_H + 26), "white")
        x = 0
        for c in parts:
            row.paste(c, (x, 26))
            x += c.width + 10
        ImageDraw.Draw(row).text((6, 6), p.split("/")[-1], fill="black")
        rows.append(row)
    W = max(r.width for r in rows)
    out_img = Image.new("RGB", (W, sum(r.height for r in rows)), "white")
    y = 0
    for r in rows:
        out_img.paste(r, (0, y))
        y += r.height
    out_img.save(out, quality=88)


if __name__ == "__main__":
    sheet(sys.argv[1], sys.argv[2:])
