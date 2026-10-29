"""What is still missing for a story: prints need_pictures=... and need_voice=... (for GitHub outputs)."""
import json
import os
import sys

from .pictures import jobs
from .script import load

if __name__ == "__main__":
    st = load(sys.argv[1])
    pics, voice = sys.argv[2], sys.argv[3]
    todo = jobs(st, pics)
    have_p = sum(os.path.exists(j[1]) for j in todo)
    have_v = sum(os.path.exists(os.path.join(voice, s.voice_file)) for s in st.scenes)
    print(f"pictures: {have_p} of {len(todo)}   narration: {have_v} of {len(st.scenes)}", file=sys.stderr)
    print(f"need_pictures={'true' if have_p < len(todo) else 'false'}")
    print(f"need_voice={'true' if have_v < len(st.scenes) else 'false'}")
    print(f"pictures_done={have_p}\npictures_total={len(todo)}\nvoice_done={have_v}\nvoice_total={len(st.scenes)}")
