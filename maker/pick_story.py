"""Pick the story to make: the one named, or else the first file in stories/new/ (alphabetical,
so name them 001-..., 002-...). Prints the path; with GITHUB_OUTPUT set, also writes story=... and slug=..."""
import os
import sys

NEW = os.path.join("stories", "new")


def pick(name: str = "") -> str:
    name = name.strip()
    if name:
        cand = [name, os.path.join(NEW, name), os.path.join(NEW, name + ".txt")]
        for c in cand:
            if os.path.isfile(c):
                return c
        raise SystemExit(f"story '{name}' not found in {NEW}/")
    files = sorted(f for f in os.listdir(NEW) if f.endswith(".txt")) if os.path.isdir(NEW) else []
    if not files:
        raise SystemExit(f"no story waiting: put a .txt file in {NEW}/")
    return os.path.join(NEW, files[0])


if __name__ == "__main__":
    path = pick(sys.argv[1] if len(sys.argv) > 1 else "")
    slug = os.path.splitext(os.path.basename(path))[0]
    print(path)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"story={path}\nslug={slug}\n")
