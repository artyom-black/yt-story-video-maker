"""Which story to make: the one pasted into new-story.txt (or a story file named by hand).

The video's short name (slug) comes from the story's number and title, e.g.
"002-1-vs-1000000-life-in-the-middle-ages". The number is one more than the videos already in old-stories/.
Prints the path; with GITHUB_OUTPUT set, also writes story=..., slug=... and title=...
"""
import os
import re
import sys

NEW = "new-story.txt"
OLD = "old-stories"
EMPTY_NOTE = "// Paste your next story here (made with template.txt), then save. The program does the rest.\n"


def has_story(path=NEW):
    if not os.path.isfile(path):
        return False
    text = "".join(l for l in open(path, encoding="utf-8") if not l.strip().startswith("//"))
    return bool(re.search(r"^\s*TITLE\s*:", text, re.M))


def title_of(path):
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*TITLE\s*:\s*(.+)", line)
        if m:
            return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0]


def number():
    made = [f for f in os.listdir(OLD) if re.match(r"\d{3} ", f)] if os.path.isdir(OLD) else []
    return len(made) + 1


def slug_for(path):
    words = re.sub(r"[^a-z0-9]+", "-", title_of(path).lower().replace(",", "")).strip("-")
    return f"{number():03d}-{words[:60].strip('-')}"


def pick(name: str = "") -> str:
    name = name.strip()
    if name:
        if os.path.isfile(name):
            return name
        raise SystemExit(f"story '{name}' not found")
    if not has_story():
        raise SystemExit(f"no story waiting: paste one into {NEW}")
    return NEW


if __name__ == "__main__":
    path = pick(sys.argv[1] if len(sys.argv) > 1 else "")
    slug = slug_for(path)
    print(path, slug)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"story={path}\nslug={slug}\ntitle={title_of(path)}\n")
