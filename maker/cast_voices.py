"""Record every spoken line of a story in the cast's fixed voices.

Step 1 (main Python):  python -m maker.cast_voices plan story.txt work/voice
    -> reference clips (Kokoro) + work/voice/jobs.json (one job per line)
Step 2 (Chatterbox env, can run in parallel shards):
    .venv-tts/bin/python maker/voice_lab_cb.py work/voice/jobs.json work/voice/out --shard 0/4
Step 3: the renderer reads work/voice/out/line_XXXX.wav
"""
from __future__ import annotations

import json
import os
import sys

from .story import load
from .voice import save_wav, speak

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = json.load(open(os.path.join(os.path.dirname(HERE), "voices.json")))

# How strongly each mood is acted (Chatterbox "exaggeration"; 0 = flat, 1 = very dramatic)
MOOD_ACTING = {"shock": 0.85, "scary": 0.75, "tense": 0.6, "funny": 0.7, "epic": 0.65,
               "sad": 0.5, "calm": 0.45, "curious": 0.55}


def line_id(scene_no: int, line_no: int) -> str:
    return f"line_{scene_no:03d}_{line_no:02d}"


def plan(story_path: str, work: str):
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors: " + "; ".join(st.errors))
    os.makedirs(work, exist_ok=True)
    refs = {}
    for who in ("KAI", "IRIS", "BOB"):
        v = VOICES[who]
        ref = os.path.join(work, f"ref_{who.lower()}.wav")
        save_wav(ref, speak(v["ref_text"], v["kokoro_voice"], v["ref_speed"], v["ref_gap"]))
        refs[who] = ref
    jobs = []
    for s in st.scenes:
        for i, ln in enumerate(s.lines):
            if ln.speaker not in refs:
                raise SystemExit(f"scene {s.number}: no voice for {ln.speaker}")
            jobs.append({"who": ln.speaker, "text": ln.text, "mood": s.mood, "ref": refs[ln.speaker],
                         "exaggeration": MOOD_ACTING.get(s.mood, 0.55), "seed": VOICES[ln.speaker]["seed"],
                         "out": line_id(s.number, i) + ".wav"})
    with open(os.path.join(work, "jobs.json"), "w") as f:
        json.dump(jobs, f, indent=1)
    print(f"{len(jobs)} lines to record")


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "plan":
        print(__doc__)
        sys.exit(2)
    plan(sys.argv[2], sys.argv[3])
