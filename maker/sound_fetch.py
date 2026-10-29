"""Fetch candidate sound effects and music for the sound kit (runs on GitHub Actions, which has open internet).

Downloads the free Mixkit previews of each category page, with names, into out_dir/<category>/.
Mixkit's licence allows use in videos (incl. monetised YouTube) but not redistributing the files,
so the files are only kept temporarily for choosing, never published in the repo.

Usage:  python -m maker.sound_fetch out_dir
"""
from __future__ import annotations

import html
import json
import os
import re
import sys

import requests

SFX = ["whoosh", "transition", "pop", "cartoon", "impact", "boom", "drum-roll", "suspense", "cash-register",
       "ding", "record-scratch", "crowd", "gasp", "laugh", "fail", "magic", "punch", "medieval", "bell", "fire"]
MUSIC = ["comedy", "funny", "suspense", "epic", "medieval", "playful", "quirky"]
# mood pages: the video moods are picked from tracks that appear on several matching mood pages
MOODS = ["mysterious", "tension", "suspenseful", "ominous", "cautious", "humorous", "quirky", "silly",
         "mischievous", "playful", "pastoral", "peaceful", "calm", "melancholic", "sombre", "sad", "epic",
         "heroic", "triumphant"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def grab(page_url: str, folder: str, limit: int, log: list):
    r = requests.get(page_url, headers=UA, timeout=60)
    if r.status_code != 200:
        log.append({"page": page_url, "status": r.status_code})
        return
    text = r.text
    urls = list(dict.fromkeys(re.findall(r'https://assets\.mixkit\.co/[^"\'\s<>]+?\.mp3', text)))
    os.makedirs(folder, exist_ok=True)
    for u in urls[:limit]:
        # the visible title is usually close to the audio URL in the page
        i = text.find(u)
        near = text[max(0, i - 3000):i]
        titles = re.findall(r'<h2[^>]*>\s*([^<]{3,80}?)\s*</h2>', near) or re.findall(r'title="([^"]{3,80})"', near)
        name = html.unescape(titles[-1]).strip() if titles else os.path.basename(u)
        slug_m = re.search(r"mixkit-([a-z0-9-]+?)-(\d+)\.mp3", u)
        if slug_m:                                     # music previews carry the track name in the URL
            name = slug_m.group(1)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50] or "sound"
        fid = re.findall(r"(\d+)", u)
        fname = f"{slug}__{fid[0] if fid else len(log)}.mp3"
        try:
            a = requests.get(u, headers=UA, timeout=60)
            if a.status_code == 200 and len(a.content) > 2000:
                with open(os.path.join(folder, fname), "wb") as f:
                    f.write(a.content)
                log.append({"file": f"{os.path.basename(folder)}/{fname}", "name": name, "url": u})
        except Exception as ex:
            log.append({"url": u, "error": str(ex)[:200]})


def main(out):
    log = []
    for c in SFX:
        grab(f"https://mixkit.co/free-sound-effects/{c}/", os.path.join(out, "sfx_" + c), 24, log)
    for c in MUSIC:
        grab(f"https://mixkit.co/free-stock-music/tag/{c}/", os.path.join(out, "music_" + c), 10, log)
    for m in MOODS:
        grab(f"https://mixkit.co/free-stock-music/mood/{m}/", os.path.join(out, "mood_" + m), 15, log)
    with open(os.path.join(out, "sources.json"), "w") as f:
        json.dump(log, f, indent=1)
    print(sum(1 for x in log if "file" in x), "files")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sound_candidates")
