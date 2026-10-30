"""Story scripts (format v2): Kai tells the story in first person, one picture per scene.

    TITLE: What Did Medieval Peasants Actually Do All Day?
    ERA: an English village in the 1340s
    COSTUME: a deep red rough wool tunic with a rope belt, brown wool trousers, leather wrap shoes
    THUMBNAIL_TEXT: 4 AM
    THUMBNAIL_IDEA: KAI exhausted and shocked, holding hard bread with stones in it, dark hut
    DESCRIPTION: ...
    TAGS: medieval, history, ...
    SOURCES: book or site; another one

    # SCENE 1
    PICTURE: KAI wakes up on straw in a dark hut, a cow breathing right next to his face, shocked
    MOOD: shock
    MUSIC: tense
    TEXT: 4 AM
    SFX: hit
    KAI: It's four in the morning, it's freezing, and something is breathing on my face.

PICTURE describes what the viewer sees (write KAI when he is in it; leave him out for a cut-away).
THEN: (at "word") another picture - shown from the moment Kai says that word (any number of THEN lines).
Optional per scene: CAMERA (push, pull, pan, punch, still).

Usage:  python -m maker.script check STORY.txt
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

MOODS = {"calm", "curious", "funny", "shock", "gross", "tense", "sad", "epic", "happy"}
MUSIC = {"tense", "funny", "calm", "epic", "sad", "none", "same"}
SFX = {"hit", "whoosh", "pop", "sting", "ding", "none"}
CAMERAS = {"push", "pull", "pan", "punch", "still"}
HEADER = ("CAST", "TITLE", "ERA", "COSTUME", "THUMBNAIL_TEXT", "THUMBNAIL_IDEA", "DESCRIPTION", "TAGS", "SOURCES", "FORMAT")


@dataclass
class Scene:
    number: int
    picture: str = ""
    picture2: str = ""
    mood: str = "calm"
    music: str = "same"
    text: str = ""
    sfx: str = "none"
    camera: str = ""
    line: str = ""
    extras: list = field(default_factory=list)       # [(word, picture)]: more pictures, each from a word on

    @property
    def all_pictures(self) -> list:
        """[(word or None, picture)] in order: the first picture, then one per THEN line."""
        out = [(None, self.picture)]
        if self.picture2:
            out.append((None, self.picture2))
        return out + list(self.extras)

    @property
    def spoken(self) -> str:
        return re.sub(r"\[[^\]]+\]", "", self.line).strip()

    @property
    def voice_file(self) -> str:
        """Recording name; it changes when the line or its mood changes, so edited lines are recorded again."""
        import hashlib
        h = hashlib.sha1(f"{self.line}|{self.mood}".encode()).hexdigest()[:8]
        return f"scene_{self.number:03d}_{h}.wav"

    @property
    def has_kai(self) -> bool:
        return bool(re.search(r"\bKAI\b", self.picture))


@dataclass
class Script:
    title: str = ""
    era: str = ""
    costume: str = ""
    thumbnail_text: str = ""
    thumbnail_ideas: list = field(default_factory=list)
    description: str = ""
    tags: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    format: str = ""
    cast: dict = field(default_factory=dict)          # {"COW": "a big brown cow with ..."}
    scenes: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(len(s.spoken.split()) for s in self.scenes)


def load(path: str) -> Script:
    sc = Script()
    cur = None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"#\s*SCENE\s+(\d+)", line, re.I)
        if m:
            cur = Scene(int(m.group(1)))
            sc.scenes.append(cur)
            continue
        if ":" not in line:
            sc.errors.append(f"line without a KEY: '{line[:50]}'")
            continue
        key, val = line.split(":", 1)
        key, val = key.strip().upper(), val.strip()
        if cur is None:
            if key == "CAST":
                n, _, d = val.partition("=")
                if not d.strip() or n.strip() != n.strip().upper():
                    sc.errors.append(f"CAST line must look like  CAST: THE COW = a big brown cow ...  ({val[:40]})")
                else:
                    sc.cast[n.strip()] = d.strip()
            elif key == "THUMBNAIL_IDEA":
                sc.thumbnail_ideas.append(val)
            elif key == "TAGS":
                sc.tags = [t.strip() for t in val.split(",") if t.strip()]
            elif key == "SOURCES":
                sc.sources = [t.strip() for t in val.split(";") if t.strip()]
            elif key in HEADER:
                setattr(sc, key.lower(), val)
            else:
                sc.errors.append(f"unknown header key {key}")
            continue
        if key == "KAI":
            cur.line = (cur.line + " " + val).strip()
        elif key == "THEN":
            m2 = re.match(r'\(\s*at\s+"([^"]+)"\s*\)\s*(.+)', val, re.I)
            cur.extras.append((m2.group(1), m2.group(2).strip()) if m2 else (None, val))
        elif key in ("PICTURE", "PICTURE2", "MOOD", "MUSIC", "TEXT", "SFX", "CAMERA"):
            setattr(cur, key.lower(), val.lower() if key in ("MOOD", "MUSIC", "SFX", "CAMERA") else val)
        else:
            sc.errors.append(f"scene {cur.number}: unknown key {key} (only KAI speaks)")
    check(sc)
    return sc


def check(sc: Script):
    for k in ("title", "era", "costume", "thumbnail_text", "description"):
        if not getattr(sc, k):
            sc.errors.append(f"missing {k.upper()}")
    if len(sc.thumbnail_ideas) < 1:
        sc.errors.append("add at least one THUMBNAIL_IDEA")
    if not sc.scenes:
        sc.errors.append("no scenes")
    for s in sc.scenes:
        where = f"scene {s.number}"
        if not s.picture:
            sc.errors.append(f"{where}: missing PICTURE")
        if not s.spoken:
            sc.errors.append(f"{where}: missing KAI line")
        if s.mood not in MOODS:
            sc.errors.append(f"{where}: MOOD must be one of {sorted(MOODS)}")
        if s.music not in MUSIC:
            sc.errors.append(f"{where}: MUSIC must be one of {sorted(MUSIC)}")
        if s.sfx not in SFX:
            sc.errors.append(f"{where}: SFX must be one of {sorted(SFX)}")
        if s.camera and s.camera not in CAMERAS:
            sc.errors.append(f"{where}: CAMERA must be one of {sorted(CAMERAS)}")
        if len(s.text) > 22:
            sc.warnings.append(f"{where}: TEXT is long ({len(s.text)} letters), keep it to 1-4 words")
        if s.text and s.text.lower().split()[0] not in s.spoken.lower() and not re.search(r"\d", s.text):
            sc.warnings.append(f"{where}: TEXT '{s.text}' is not said in the line, it will pop at the start")
        for word, pic in s.extras:
            if word and word.lower() not in s.spoken.lower():
                sc.errors.append(f"{where}: THEN (at \"{word}\") - that word is not in the line")
        n = len(s.spoken.split())
        if n > 45:
            sc.warnings.append(f"{where}: long line ({n} words) - split it or add PICTURE2")
    for name in sc.cast:
        uses = sum(len(re.findall(rf"\b{re.escape(name)}\b", p)) for s in sc.scenes for _w, p in s.all_pictures)
        if uses == 0:
            sc.warnings.append(f"CAST {name} is never used in a picture (write it in CAPITALS)")
    if sc.scenes and sc.scenes[0].music == "same":
        sc.scenes[0].music = "tense"
    if sc.words and not (1300 <= sc.words <= 2100):
        sc.warnings.append(f"{sc.words} words (aim 1,500-1,800 for about 10-12 minutes)")


if __name__ == "__main__":
    s = load(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
    print(f"{s.title}\n{len(s.scenes)} scenes, {s.words} words, about {s.words / 150:.1f} minutes")
    for e in s.errors:
        print("ERROR:", e)
    for w in s.warnings:
        print("warning:", w)
    sys.exit(1 if s.errors else 0)
