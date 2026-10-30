"""Write upload.txt: everything to copy into YouTube when uploading."""
import sys

from .story import load


def write(story_path, out_path):
    st = load(story_path)
    lines = [
        "TITLE (copy into YouTube):", st.title, "",
        "DESCRIPTION (copy into YouTube):", st.description, "",
        "Sources:", *[f"- {s}" for s in st.sources], "",
        "TAGS:", ", ".join(st.tags), "",
        "UPLOAD SETTINGS:",
        "- Audience: No, it's not made for kids",
        "- Altered or synthetic content: No (it is a cartoon, not realistic footage). Voices are AI-generated.",
        "- Thumbnail: pick the best of thumbnail_1/2/3.png; use 'Test & compare' to try all three",
    ]
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    write(sys.argv[1], sys.argv[2])
