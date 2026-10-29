"""Kai's narration: one recording per scene, in the locked voice (voices.json), acted to the scene's mood.

Step 1 (main Python):  python -m maker.narration plan STORY.txt WORK_DIR   -> reference clip + jobs.json
Step 2 (Chatterbox):   .venv-tts/bin/python maker/voice_lab_cb.py WORK_DIR/jobs.json OUT_DIR [--shard I/N]
Recordings are named scene_XXX.wav. Existing recordings are skipped (resumable).
"""
from __future__ import annotations

import json
import os
import sys

from .script import load
from .voice import save_wav, speak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTING = {"shock": 0.8, "gross": 0.7, "funny": 0.7, "tense": 0.6, "epic": 0.65, "sad": 0.5, "calm": 0.45,
          "curious": 0.55, "happy": 0.65}


def plan(story_path, work, done_dir=None):
    st = load(story_path)
    if st.errors:
        raise SystemExit("story has errors: " + "; ".join(st.errors))
    v = json.load(open(os.path.join(ROOT, "voices.json")))["KAI"]
    os.makedirs(work, exist_ok=True)
    ref = os.path.join(work, "ref_kai.wav")
    save_wav(ref, speak(v["ref_text"], v["kokoro_voice"], v["ref_speed"], v["ref_gap"]))
    jobs = []
    for s in st.scenes:
        out = f"scene_{s.number:03d}.wav"
        if done_dir and os.path.exists(os.path.join(done_dir, out)):
            continue
        jobs.append({"who": "KAI", "text": s.line, "mood": s.mood, "ref": ref, "seed": v["seed"],
                     "exaggeration": ACTING.get(s.mood, 0.55), "out": out})
    json.dump(jobs, open(os.path.join(work, "jobs.json"), "w"), indent=1)
    print(len(jobs), "lines to record")


if __name__ == "__main__":
    plan(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
