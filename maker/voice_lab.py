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

# A lively 10-second read so the reference carries some energy, not a flat list of words.
REF_TEXT = ("Okay, so here's the thing. Nobody tells you how weird the past really was. "
            "I mean it. Every single day was a little adventure, and most of them were terrible.")

# The same lines as the first audition, now written for a performer:
# punctuation for rhythm, and [laugh] [chuckle] [sigh] [gasp] for real reactions.
LINES = {
    "KAI": [("calm", "Wait... so people back then just drank beer... for breakfast?"),
            ("shock", "[gasp] Hold on. Hold on! They used WHAT as toilet paper?!"),
            ("funny", "[laugh] Okay, okay, I take it back! Modern life is amazing.")],
    "IRIS": [("calm", "Actually, the water was so dirty that weak beer was the safer choice."),
             ("shock", "Oh no. Kai... that is not a sponge."),
             ("funny", "Congratulations, Bob. [chuckle] You just invented the first toilet tax.")],
    "BOB": [("calm", "[sigh] Cool. So we're stuck here. Great. Love that for us."),
            ("shock", "Nope. Nope! Absolutely not. I'm going home."),
            ("funny", "A medieval dentist? [chuckle] So... a guy with pliers. And confidence.")],
    "NARRATOR": [("calm", "In the year thirteen forty-seven, a ship arrived in Sicily."),
                 ("shock", "Nobody on board was alive."),
                 ("epic", "And what it carried... would kill half of Europe.")],
}

# How strongly Chatterbox should act each mood (0 = flat, 1 = very dramatic)
EXAGGERATION = {"calm": 0.45, "shock": 0.85, "funny": 0.7, "epic": 0.65}


def main(refs_dir, jobs_path):
    os.makedirs(refs_dir, exist_ok=True)
    jobs = []
    for who, voices in CANDIDATES.items():
        for vi, voice in enumerate(voices):
            ref = os.path.join(refs_dir, f"ref_{voice}.wav")
            save_wav(ref, speak(REF_TEXT, voice, 1.0))
            for li, (mood, text) in enumerate(LINES[who]):
                jobs.append({"who": who, "option": "ABC"[vi], "voice": voice, "mood": mood, "text": text,
                             "ref": ref, "exaggeration": EXAGGERATION[mood], "seed": 7,
                             "out": f"{who.lower()}_{'ABC'[vi]}_{li}_{mood}.wav"})
    with open(jobs_path, "w") as f:
        json.dump(jobs, f, indent=1)
    print(len(jobs), "jobs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
