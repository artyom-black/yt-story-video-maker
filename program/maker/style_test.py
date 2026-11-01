"""Quick look at the picture style: draws the main character in his costume, the cast, and the pictures of the
first 3 scenes of new-story.txt (checked by the picture checker), and puts them on one sheet.

    python -m maker.style_test OUT_DIR
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

from . import pictures

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    t = open("new-story.txt", encoding="utf-8").read()
    open(os.path.join(out, "story.txt"), "w").write(t[:t.index("# SCENE 4\n")])
    pictures.run(os.path.join(out, "story.txt"), out)
    files = []
    for root, _d, fs in os.walk(out):
        files += [os.path.join(root, f) for f in fs if f.endswith(".png") and "_ref" not in f and ".try" not in f]
    files.sort()
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    sheet = Image.new("RGB", (4 * 480, ((len(files) + 3) // 4) * 300), (20, 20, 20))
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((470, 265))
        x, y = (i % 4) * 480 + 5, (i // 4) * 300 + 30
        sheet.paste(im, (x, y))
        ImageDraw.Draw(sheet).text((x, y - 26), os.path.basename(f)[:40], font=font, fill=(255, 215, 0))
    sheet.save(os.path.join(out, "style_test.jpg"), quality=88)
