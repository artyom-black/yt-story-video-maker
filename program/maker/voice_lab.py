"""Voice lab, step 1 (main Python): make a short reference clip per candidate voice with Kokoro.
Chatterbox-Turbo then copies the voice's sound from that clip and performs the lines with emotion
(step 2: maker/voice_lab_cb.py, which runs in its own environment with torch).

Usage:  python -m maker.voice_lab refs_dir jobs.json
"""
from __future__ import annotations

import json
import os
import sys

from .voice import save_wav, speak

CANDIDATES = {
    "KAI": ["am_puck", "am_liam", "am_echo"],
    "IRIS": ["af_heart", "af_bella", "bf_emma"],
    "BOB": ["am_onyx", "am_fenrir", "bm_lewis"],
    "NARRATOR": ["bm_george", "am_michael", "bm_fable"],
}

# A 10-second read per character; Chatterbox copies the delivery as well as the voice.
REF_TEXT = ("Okay, so here's the thing. Nobody tells you how weird the past really was. "
            "I mean it. Every single day was a little adventure, and most of them were terrible.")
REF_TEXT_BY = {
    # Bob (the lovable dumb one): one long, flowing, rambling thought, no forced pauses
    "BOB": ("So like, if the moon is so big, why doesn't it just fall down on us, you know, because "
            "I dropped my phone yesterday and it fell really fast, so I think the moon is just being lazy "
            "or something, and honestly I kind of respect that."),
}
REF_SPEED = {"BOB": 0.96}
REF_GAP = {"BOB": 0.0}

# Round 4 for Bob: blends between a lighter and a fuller voice, aiming for "not too manly, not too young"
# (measured pitch with maker/voice_measure.py: all 133-141 Hz; Kai is ~106 Hz)
CANDIDATES_ROUND2 = {"BOB": ["am_liam:0.5+am_eric:0.5", "am_eric:0.6+am_michael:0.4",
                             "am_echo:0.4+am_eric:0.6", "am_eric:0.5+am_fenrir:0.5"]}

# The same lines as the first audition, now written for a performer:
# punctuation for rhythm, and [laugh] [chuckle] [sigh] [gasp] for real reactions.
LINES = {
    "KAI": [("calm", "Wait... so people back then just drank beer... for breakfast?"),
            ("shock", "[gasp] Hold on. Hold on! They used WHAT as toilet paper?!"),
            ("funny", "[laugh] Okay, okay, I take it back! Modern life is amazing.")],
    "IRIS": [("calm", "Actually, the water was so dirty that weak beer was the safer choice."),
             ("shock", "Oh no. Kai... that is not a sponge."),
             ("funny", "Congratulations, Bob. [chuckle] You just invented the first toilet tax.")],
    "BOB": [("calm", "Wait, so if they didn't have phones back then, how did they know what time it was, like, did they just guess?"),
            ("shock", "Hold on, hold on, the sun is a star? Since when? Why did nobody tell me that!"),
            ("funny", "[chuckle] Okay, but what if we just take the whole castle with us, like, in a really big bag?")],
    "NARRATOR": [("calm", "In the year thirteen forty-seven, a ship arrived in Sicily."),
                 ("shock", "Nobody on board was alive."),
                 ("epic", "And what it carried... would kill half of Europe.")],
}

# How strongly Chatterbox should act each mood (0 = flat, 1 = very dramatic)
EXAGGERATION = {"calm": 0.45, "shock": 0.85, "funny": 0.7, "epic": 0.65}


def from_lines(refs_dir, jobs_path, lines_file):
    """Record given lines in the locked voices (voices.json), e.g. for a demo."""
    voices = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices.json")))
    acting = {"shock": 0.85, "scary": 0.75, "tense": 0.6, "funny": 0.7, "epic": 0.65, "sad": 0.5,
              "calm": 0.45, "curious": 0.55}
    lines = json.load(open(lines_file))
    os.makedirs(refs_dir, exist_ok=True)
    refs, jobs = {}, []
    for ln in lines:
        who = ln["who"]
        if who not in refs:
            v = voices[who]
            refs[who] = os.path.join(refs_dir, f"ref_{who.lower()}.wav")
            save_wav(refs[who], speak(v["ref_text"], v["kokoro_voice"], v["ref_speed"], v["ref_gap"]))
        jobs.append({"who": who, "option": "-", "voice": voices[who]["kokoro_voice"], "mood": ln["mood"],
                     "text": ln["text"], "ref": refs[who], "exaggeration": acting.get(ln["mood"], 0.55),
                     "seed": voices[who]["seed"], "out": ln["out"]})
    with open(jobs_path, "w") as f:
        json.dump(jobs, f, indent=1)
    print(len(jobs), "jobs")


def main(refs_dir, jobs_path):
    if os.environ.get("LINES_FILE"):
        return from_lines(refs_dir, jobs_path, os.environ["LINES_FILE"])
    os.makedirs(refs_dir, exist_ok=True)
    jobs = []
    only = [w for w in os.environ.get("ONLY", "").split(",") if w]
    cands = {w: CANDIDATES_ROUND2.get(w, CANDIDATES[w]) for w in only} if only else CANDIDATES
    for who, voices in cands.items():
        for vi, voice in enumerate(voices):
            ref = os.path.join(refs_dir, f"ref_{who.lower()}_{vi}.wav")
            save_wav(ref, speak(REF_TEXT_BY.get(who, REF_TEXT), voice, REF_SPEED.get(who, 1.0), REF_GAP.get(who, 0.12)))
            for li, (mood, text) in enumerate(LINES[who]):
                jobs.append({"who": who, "option": "ABCD"[vi], "voice": voice, "mood": mood, "text": text,
                             "ref": ref, "exaggeration": EXAGGERATION[mood], "seed": 7,
                             "out": f"{who.lower()}_{'ABCD'[vi]}_{li}_{mood}.wav"})
    with open(jobs_path, "w") as f:
        json.dump(jobs, f, indent=1)
    print(len(jobs), "jobs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
