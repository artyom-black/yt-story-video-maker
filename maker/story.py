"""Read and check a story .txt file (format: docs/story-format.md).

Usage:  python -m maker.story stories/my-story.txt
Exit code 0 = OK (warnings allowed), 1 = errors found.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

MAIN_CAST = {"KAI", "IRIS", "BOB"}
BEATS = {"hook", "setup", "rise", "twist", "peak", "payoff", "outro"}
MOODS = {"curious", "funny", "tense", "scary", "sad", "epic", "calm", "shock"}
CAMERAS = {"still", "zoom-in", "zoom-out", "pan-left", "pan-right", "shake", "slow-push"}
MUSIC = {"mystery", "tension", "action", "comedy", "sad", "epic", "calm", "none"}
SFX = {"crowd", "whoosh", "boom", "swords", "thunder", "wind", "fire",
       "footsteps", "water", "ding", "gasp", "heartbeat"}
HEADER_KEYS = {"TITLE", "THUMBNAIL_TEXT", "THUMBNAIL_IDEA", "DESCRIPTION", "TAGS"}
SCENE_KEYS = {"BEAT", "PLACE", "CAST", "EXTRAS", "MOOD", "CAMERA", "MUSIC", "SFX"}

SCENE_RE = re.compile(r"^=+\s*SCENE\s+(\d+)\s*=+$", re.I)
LINE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_ -]*?)\s*:\s*(.*)$")


@dataclass
class Line:
    speaker: str
    text: str


@dataclass
class Scene:
    number: int
    beat: str = ""
    place: str = ""
    cast: list[str] = field(default_factory=list)
    extras: str = ""
    mood: str = ""
    camera: str = "still"
    music: str = ""          # filled with the previous scene's music if empty
    sfx: list[str] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(len(l.text.split()) for l in self.lines)


@dataclass
class Story:
    title: str = ""
    thumbnail_text: str = ""
    thumbnail_ideas: list[str] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(s.words for s in self.scenes)

    @property
    def minutes(self) -> float:
        return self.words / 140  # calm storytelling pace, words per minute

    @property
    def backup_cast(self) -> list[str]:
        seen = []
        for s in self.scenes:
            for c in s.cast:
                if c not in MAIN_CAST and c != "NONE" and c not in seen:
                    seen.append(c)
        return seen


def _clean(text: str) -> str:
    # Chat apps add markdown; strip it so pasted text still parses.
    text = text.replace("\r", "").replace("’", "'")
    out = []
    for raw in text.split("\n"):
        line = raw.strip().strip("`")
        line = re.sub(r"^\*\*(.+?)\*\*", r"\1", line)        # **KEY**: value
        line = re.sub(r"^\*\*(.+?):\*\*", r"\1:", line)       # **KEY:** value
        line = re.sub(r"^#+\s*", "", line)                    # ### === SCENE 1 ===
        out.append(line)
    return "\n".join(out)


def parse(text: str) -> Story:
    st = Story()
    cur: Scene | None = None
    for n, line in enumerate(_clean(text).split("\n"), 1):
        if not line:
            continue
        m = SCENE_RE.match(line)
        if m:
            cur = Scene(number=int(m.group(1)))
            st.scenes.append(cur)
            continue
        m = LINE_RE.match(line)
        if not m:
            st.warnings.append(f"line {n}: not understood, skipped: {line[:60]}")
            continue
        key, val = m.group(1).strip().upper().replace(" ", "_"), m.group(2).strip()
        if cur is None:
            if key == "TITLE":
                st.title = val
            elif key == "THUMBNAIL_TEXT":
                st.thumbnail_text = val
            elif key == "THUMBNAIL_IDEA":
                st.thumbnail_ideas.append(val)
            elif key == "DESCRIPTION":
                st.description = val
            elif key == "TAGS":
                st.tags = [t.strip() for t in val.split(",") if t.strip()]
            else:
                st.warnings.append(f"line {n}: unknown header key {key}")
            continue
        if key == "BEAT":
            cur.beat = val.lower()
        elif key == "PLACE":
            cur.place = val
        elif key == "CAST":
            cur.cast = [c.strip().upper() for c in val.split(",") if c.strip()]
        elif key == "EXTRAS":
            cur.extras = val
        elif key == "MOOD":
            cur.mood = val.lower()
        elif key == "CAMERA":
            cur.camera = val.lower()
        elif key == "MUSIC":
            cur.music = val.lower()
        elif key == "SFX":
            cur.sfx = [s.strip().lower() for s in val.split(",") if s.strip()]
        elif val:
            cur.lines.append(Line(key, val))
    _check(st)
    return st


def _check(st: Story) -> None:
    E, W = st.errors.append, st.warnings.append
    if not st.title:
        E("missing TITLE")
    elif len(st.title) > 70:
        W(f"TITLE is {len(st.title)} characters; YouTube cuts it after ~70")
    if not st.thumbnail_text:
        E("missing THUMBNAIL_TEXT")
    elif len(st.thumbnail_text) > 25:
        W("THUMBNAIL_TEXT is long; 3 words or fewer reads best on a phone")
    if len(st.thumbnail_ideas) < 3:
        W(f"only {len(st.thumbnail_ideas)} THUMBNAIL_IDEA lines; 3 gives you options to test")
    if not st.description:
        W("missing DESCRIPTION")
    if not st.scenes:
        E("no scenes found (each scene starts with === SCENE 1 ===)")
        return

    music = "mystery"
    since_twist = 0
    for i, s in enumerate(st.scenes):
        tag = f"scene {s.number}"
        if s.number != i + 1:
            W(f"{tag}: expected scene number {i + 1}")
        if s.beat not in BEATS:
            E(f"{tag}: BEAT '{s.beat}' must be one of {', '.join(sorted(BEATS))}")
        if not s.place:
            E(f"{tag}: missing PLACE")
        if not s.cast:
            E(f"{tag}: missing CAST (use NONE for no characters)")
        if s.mood not in MOODS:
            E(f"{tag}: MOOD '{s.mood}' must be one of {', '.join(sorted(MOODS))}")
        if s.camera not in CAMERAS:
            W(f"{tag}: CAMERA '{s.camera}' unknown, using still")
            s.camera = "still"
        if s.music:
            if s.music not in MUSIC:
                W(f"{tag}: MUSIC '{s.music}' unknown, keeping {music}")
                s.music = music
            music = s.music
        else:
            s.music = music
        bad = [x for x in s.sfx if x not in SFX]
        if bad:
            W(f"{tag}: unknown SFX {', '.join(bad)} (skipped)")
            s.sfx = [x for x in s.sfx if x in SFX]
        if not s.lines:
            E(f"{tag}: no spoken lines")
        for l in s.lines:
            if l.speaker != "NARRATOR" and l.speaker not in s.cast:
                E(f"{tag}: {l.speaker} speaks but is not in CAST")
        if s.lines and s.words < 15:
            W(f"{tag}: only {s.words} words; very short scenes can feel choppy")
        if s.words > 70:
            W(f"{tag}: {s.words} words; split it so the picture changes more often")
        since_twist = 0 if s.beat in ("twist", "peak") else since_twist + 1
        if since_twist == 12:
            W(f"{tag}: 12 scenes without a twist or peak; viewers may leave here")

    if st.scenes[0].beat != "hook":
        E("scene 1 must be BEAT: hook")
    if st.scenes[-1].beat not in ("payoff", "outro"):
        W("last scene should be BEAT: payoff or outro")
    if st.words < 1400:
        W(f"{st.words} spoken words (~{st.minutes:.1f} min); aim for 1,400-2,800 (10-20 min)")
    if st.words > 2800:
        W(f"{st.words} spoken words (~{st.minutes:.1f} min); over 20 min, consider cutting")


def load(path: str) -> Story:
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    st = load(argv[1])
    print(f"Title:   {st.title}")
    print(f"Scenes:  {len(st.scenes)}   Words: {st.words}   Length: ~{st.minutes:.1f} min")
    if st.backup_cast:
        print(f"Backup characters used: {', '.join(st.backup_cast)}")
    for w in st.warnings:
        print(f"WARNING  {w}")
    for e in st.errors:
        print(f"ERROR    {e}")
    print("RESULT: " + ("NOT OK, fix the errors above" if st.errors else "OK"))
    return 1 if st.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
