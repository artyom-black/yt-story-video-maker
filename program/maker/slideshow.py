"""The editor: turns a story's pictures and narration into a finished MrBeast-style video.

Every decision follows fixed rules, so nothing is random:
- one picture per scene, on screen exactly as long as Kai's line (+ a short breath);
- camera: every picture moves (slow push-in, pull-out or pan, alternating); shocking moments get a fast
  punch-zoom and a shake on the key word; funny moments a small bounce;
- key words (TEXT) pop up on the exact moment Kai says them, always in the same style;
- sounds: one fixed sound per role for the whole video (the same hit, the same whoosh, the same pop), from the
  measured kit, placed so the hit lands on the word; a whoosh only when the section changes;
- music: one track per mood (tense / funny / calm / sad / epic), at most a handful per video, crossfaded when
  the mood changes, ducked under the voice;
- loudness: voice first, everything at YouTube's -14 LUFS.

Usage:  python -m maker.slideshow STORY.txt ASSETS_DIR KIT_DIR CANDIDATES_DIR OUT_DIR
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageFilter

from .editor import text_layer
from .script import load

W, H, FPS = 1920, 1080, 30
SR = 48000
BREATH = 0.22                  # pause after each line
SECTION_PAUSE = 0.45           # extra pause when the music / section changes
ROLE_FILE = {"hit": "hit_1.wav", "whoosh": "whoosh_4.wav", "pop": "pop_3.wav", "sting": "sting_4.wav",
             "ding": "ding_2.wav"}
ROLE_GAIN = {"hit": -5, "whoosh": -12, "pop": -11, "sting": -8, "ding": -10}
MUSIC_FOLDERS = {"tense": ["music_suspense", "music_epic"], "funny": ["music_funny", "music_comedy", "music_quirky"],
                 "calm": ["music_medieval", "music_playful"], "sad": ["music_medieval", "music_suspense"],
                 "epic": ["music_epic", "music_suspense"]}
MUSIC_DB = -21


# ---------- audio helpers ----------

def load_audio(path, mono=True):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def clean_voice(a):
    """Trim silence at both ends and shorten long pauses inside the line."""
    hop = SR // 100
    n = len(a) // hop
    env = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    on = np.where(env > 0.03 * env.max())[0]
    if not len(on):
        return a
    a = a[max(0, on[0] - 3) * hop:(on[-1] + 6) * hop]
    env = env[max(0, on[0] - 3):on[-1] + 6]
    quiet = env < 0.03 * env.max()
    out, i = [], 0
    while i < len(env):
        j = i
        while j < len(env) and quiet[j] == quiet[i]:
            j += 1
        seg = a[i * hop:j * hop]
        if quiet[i] and (j - i) > 35:                # pauses longer than 0.35 s become 0.3 s
            k = int(0.3 * SR)
            seg = np.concatenate([seg[:k // 2], seg[-(k - k // 2):]])
        out.append(seg)
        i = j
    a = np.concatenate(out)
    return (a / max(1e-6, float(np.abs(a).max())) * 0.89).astype(np.float32)


def voiced_times(a):
    hop = SR // 100
    n = len(a) // hop
    env = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    return np.where(env > 0.08 * env.max())[0] / 100.0


NUMBER_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
                "9": "nine", "10": "ten", "11": "eleven", "12": "noon", "1/10": "tenth", "100%": "hundred"}


def _spoken_forms(word):
    """How a TEXT pop may be said out loud: '4 AM' -> 'four', '1346' -> 'thirteen', '12 PM' -> 'noon'."""
    import re
    w = word.lower().split()[0] if word else ""
    forms = [w]
    if w in NUMBER_WORDS:
        forms.insert(0, NUMBER_WORDS[w])
    m = re.match(r"^1(\d)\d\d$", w)                       # years like 1346 are said "thirteen forty-six"
    if m:
        forms.insert(0, ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                         "eighteen", "nineteen"][int(m.group(1))])
    if w.endswith("s") and w[:-1].isdigit():                 # "MID 20s" -> "twenties"
        forms.insert(0, "twent")
    return forms


def word_time(line, word, a):
    """When a word is said: its share of the text, spread over the voiced parts of the recording."""
    import re
    s = re.sub(r"\[[^\]]+\]", "", line).strip().lower()
    i = s.find(word.lower()) if word else -1
    forms = [] if i >= 0 else [f for tok in (word.split() if word else []) for f in _spoken_forms(tok)]
    for form in forms:
        i = s.find(form)
        if i >= 0:
            break
    if i < 0:
        return 0.12
    v = voiced_times(a)
    if not len(v):
        return 0.12
    k = min(len(v) - 1, int(len(v) * i / max(1, len(s))))
    return float(v[k]) - 0.03


def phrase_starts(a, min_gap=0.16):
    """Times where Kai starts a new phrase after a short pause: natural places to cut."""
    hop = SR // 100
    n = len(a) // hop
    env = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    on = env > 0.06 * env.max()
    out, silent = [], 0
    for i, v in enumerate(on):
        if v:
            if silent >= min_gap * 100 and i > 30:
                out.append(i / 100)
            silent = 0
        else:
            silent += 1
    return out


def db(x):
    return 10 ** (x / 20)


# ---------- the plan ----------

MIN_MUSIC_RUN = 20.0          # seconds: music never changes more often than this


def smooth_music(st, voices):
    """The music mood of every scene. Short mood flips are merged into the music around them, so the music
    changes rarely and only for real sections (professional videos don't switch tracks every 15 seconds)."""
    moods, cur = [], "tense"
    for s in st.scenes:
        if s.music not in ("same", ""):
            cur = s.music
        moods.append(cur)
    dur = [len(v) / SR + BREATH for v in voices]
    for _ in range(10):
        runs, i = [], 0
        while i < len(moods):
            j = i
            while j < len(moods) and moods[j] == moods[i]:
                j += 1
            runs.append((i, j, sum(dur[i:j])))
            i = j
        short = [r for k, r in enumerate(runs) if r[2] < MIN_MUSIC_RUN and 0 < k < len(runs) - 1]  # keep the hook
        if not short or len(runs) == 1:
            break
        a, b, _ = min(short, key=lambda r: r[2])
        # join the shorter neighbour, so the bigger sections keep their music
        before = next(r for r in runs if r[1] == a)
        after = next(r for r in runs if r[0] == b)
        fill = moods[before[0]] if before[2] <= after[2] else moods[after[0]]
        for k in range(a, b):
            moods[k] = fill
    return moods

def make_plan(st, assets, kit_dir, cands):
    kit = {c["kit_file"]: c for ch in json.load(open(os.path.join(kit_dir, "kit.json")))["roles"].values() for c in ch}
    music_info = json.load(open(os.path.join(kit_dir, "kit.json")))["music"]
    from .pictures import picture_files
    files = picture_files(st, assets)
    voices = [clean_voice(load_audio(os.path.join(assets, "voice", s.voice_file))) for s in st.scenes]
    moods = smooth_music(st, voices)
    t = 0.1
    scenes, sfx, music_runs = [], [], []
    prev_music = None
    side = 0
    for idx, s in enumerate(st.scenes):
        voice = voices[idx]
        mood_music = moods[idx]
        section_change = prev_music is not None and mood_music != prev_music
        if section_change:
            t += SECTION_PAUSE
        start = t
        dur = len(voice) / SR + BREATH
        tt = word_time(s.line, s.text, voice) if s.text else None
        pics, switch = [], []
        for k, (word, _pic) in enumerate(s.all_pictures):
            key = f"scene_{s.number:03d}" + ("" if k == 0 else f"x{k + 1}")
            pics.append(files[key])
            switch.append(0.0 if k == 0 else (word_time(s.line, word, voice) if word else None))
        # pictures without a word share the remaining time evenly
        for k in range(1, len(switch)):
            if switch[k] is None:
                switch[k] = dur * k / len(switch)
        order = sorted(range(len(pics)), key=lambda k: switch[k])
        pics, switch = [pics[k] for k in order], [max(0.0, switch[k]) for k in order]
        cam = s.camera or ("punch" if s.mood == "shock" or s.sfx == "hit" else
                           ["push", "pan", "pull", "push", "pan"][idx % 5])
        side = 1 - side if s.text else side
        scenes.append({"n": s.number, "start": start, "dur": dur, "pics": pics, "switch": switch,
                       "camera": cam, "mood": s.mood,
                       "text": s.text, "text_at": tt, "text_side": side, "voice": voice,
                       "phrases": phrase_starts(voice)})
        # sounds, each placed on its hit
        if section_change or s.sfx == "whoosh":
            sfx.append((start, "whoosh"))
        if s.sfx in ("hit", "sting", "ding"):
            sfx.append((start + (tt if tt is not None else 0.05), s.sfx))
        if s.text and s.sfx not in ("hit", "sting", "ding"):
            sfx.append((start + tt, "pop"))
        if not music_runs or music_runs[-1]["mood"] != mood_music:
            music_runs.append({"mood": mood_music, "start": start})
        prev_music = mood_music
        t = start + dur
    length = t + 0.6
    # sounds -> files, placed so the kit sound's hit lands on the moment
    placed = []
    for when, role in sfx:
        f = ROLE_FILE[role]
        if f in kit:
            placed.append((max(0.0, when - kit[f]["hit_at"]), os.path.join(kit_dir, f), ROLE_GAIN[role]))
    # music: one track per mood, fixed for the whole video
    by_mood = json.load(open(os.path.join(kit_dir, "kit.json"))).get("music_by_mood", {})
    chosen = {}
    used = set()
    for run in music_runs:
        m = run["mood"]
        if m == "none" or m in chosen:
            continue
        for tr in by_mood.get(m, []):                          # best-matching track not used by another mood
            if tr["file"].split("__")[-1] not in used:
                chosen[m] = os.path.join(cands, tr["file"])
                used.add(tr["file"].split("__")[-1])
                break
    for i, run in enumerate(music_runs):
        run["end"] = music_runs[i + 1]["start"] if i + 1 < len(music_runs) else length
        run["file"] = chosen.get(run["mood"])
    return scenes, placed, music_runs, length


# ---------- audio mix ----------

def mix(scenes, placed, music_runs, length, out_wav):
    n = int(length * SR)
    voice = np.zeros(n, np.float32)
    for sc in scenes:
        i = int(sc["start"] * SR)
        v = sc["voice"][:max(0, n - i)]
        voice[i:i + len(v)] += v
    fx = np.zeros(n, np.float32)
    for when, path, gain in placed:
        a = load_audio(path) * db(gain)
        i = int(when * SR)
        a = a[:max(0, n - i)]
        fx[i:i + len(a)] += a
    music = np.zeros(n, np.float32)
    offsets = {}
    fade = int(1.0 * SR)
    for run in music_runs:
        if not run.get("file"):
            continue
        track = load_audio(run["file"])
        off = offsets.get(run["file"], int(1.0 * SR))       # skip the first second, continue where it left off
        a0, a1 = int(run["start"] * SR), int(run["end"] * SR)
        seg_len = a1 - a0 + fade
        idx = (np.arange(seg_len) + off) % len(track)
        seg = track[idx].copy()
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        end = min(n, a0 + seg_len)
        music[a0:end] += seg[:end - a0]
        offsets[run["file"]] = off + (a1 - a0)
    # duck the music (and loud effects) while Kai talks
    hop = SR // 100
    env = np.sqrt(np.convolve(voice ** 2, np.ones(hop) / hop, mode="same"))
    talking = (env > 0.02).astype(np.float32)
    k = int(0.25 * SR)
    smooth = np.convolve(talking, np.ones(k) / k, mode="same").clip(0, 1)
    music *= db(MUSIC_DB) * (1 - 0.55 * smooth)
    fx *= (1 - 0.3 * smooth)
    mixed = voice + fx + music
    mixed /= max(1.0, float(np.abs(mixed).max()) / 0.95)
    raw = mixed.astype(np.float32).tobytes()
    # pass 1: measure; pass 2: exact -14 LUFS (YouTube's level) with a true-peak limit
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           input=raw, capture_output=True, check=True).stderr.decode()
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    tmp = out_wav + ".raw.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-af", af, "-ar", str(SR), "-ac", "2", tmp], input=raw, check=True)
    os.replace(tmp, out_wav)


# ---------- pictures and camera ----------

def ease(t):
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def camera(kind, t, dur, text_at, n):
    """(zoom, centre_x, centre_y) as shares of the picture, for time t inside a scene."""
    p = ease(t / max(dur, 0.01))
    rng = np.random.default_rng(n)
    fx, fy = 0.5 + rng.uniform(-0.06, 0.06), 0.45 + rng.uniform(-0.04, 0.04)
    if kind == "push":
        z = 1.04 + 0.12 * p
    elif kind == "pull":
        z = 1.16 - 0.12 * p
    elif kind == "pan":
        z = 1.14
        fx = 0.44 + 0.12 * p if n % 2 else 0.56 - 0.12 * p
    elif kind == "punch":
        hit = text_at if text_at is not None else 0.05
        if t < hit:
            z = 1.04 + 0.04 * ease(t / max(hit, 0.01))           # slow creep towards the moment
        elif t < hit + 0.08:
            z = 1.08 + 0.22 * (t - hit) / 0.08                  # the fast punch-in on the word
        else:
            z = 1.30 - 0.05 * ease((t - hit - 0.08) / max(0.01, dur - hit - 0.08))
    else:
        z = 1.05
    dx = dy = 0.0
    if kind == "punch":
        hit = text_at if text_at is not None else 0.05
        if hit <= t < hit + 0.35:                               # shake on the hit
            f = 1 - (t - hit) / 0.35
            dx, dy = 0.012 * f * math.sin(t * 90), 0.012 * f * math.cos(t * 75)
    return z, fx + dx, fy + dy


# ---------- the camera operator: several shots inside every picture ----------

FACE_CASCADE = None
MAX_SHOT = 1.5          # never hold one framing longer than this
MIN_SHOT = 0.7


def analyse_picture(path):
    """Where things are in a picture (shares of width/height): Kai's face, and the most eye-catching
    other spots (objects), so the editor can cut between wide, face and detail shots."""
    global FACE_CASCADE
    import cv2
    if FACE_CASCADE is None:
        xml = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models",
                           "lbpcascade_animeface.xml")
        FACE_CASCADE = cv2.CascadeClassifier(xml) if os.path.exists(xml) else False
    im = cv2.imread(path)
    h, w = im.shape[:2]
    face = None
    if FACE_CASCADE is not False:
        g = cv2.equalizeHist(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
        found = [tuple(r) for r in FACE_CASCADE.detectMultiScale(g, 1.05, 3, minSize=(max(24, w // 40),) * 2)]
        big = cv2.resize(g, None, fx=1.6, fy=1.6)              # a second, looser look for turned faces
        found += [tuple(int(v / 1.6) for v in r) for r in FACE_CASCADE.detectMultiScale(big, 1.04, 2,
                                                                                         minSize=(40, 40))]
        best, best_score = None, 0.0
        for x, y, fw, fh in found:
            patch = im[y + fh // 3:y + 2 * fh // 3, x + fw // 4:x + 3 * fw // 4].reshape(-1, 3).astype(float)
            if not len(patch):
                continue
            b_, g_, r_ = patch.mean(axis=0)
            if not (r_ > 110 and r_ > g_ > b_ * 0.9):            # must look like skin (not a cow, not a wall)
                continue
            score = (fh / h) * (1.4 - (y + fh / 2) / h)          # big, and high in the picture
            if score > best_score:
                best, best_score = (x, y, fw, fh), score
        if best:
            x, y, fw, fh = best
            face = ((x + fw / 2) / w, (y + fh / 2) / h, fh / h)
    # eye-catching spots: strong local contrast and colour, away from the face
    small = cv2.resize(im, (160, 90)).astype(np.float32)
    blur = cv2.GaussianBlur(small, (0, 0), 6)
    sal = np.abs(small - blur).sum(axis=2) + 0.4 * cv2.cvtColor(small.astype(np.uint8), cv2.COLOR_BGR2HSV)[:, :, 1]
    sal = cv2.GaussianBlur(sal, (0, 0), 5)
    if face:                                           # a detail shot never lands on Kai's body or legs
        fx, fy, fs = int(face[0] * 160), int(face[1] * 90), max(6, int(face[2] * 90))
        sal[max(0, fy - fs):, max(0, fx - 2 * fs):fx + 2 * fs] = 0
    spots = []
    for _ in range(2):
        yy, xx = np.unravel_index(np.argmax(sal), sal.shape)
        cx, cy = (xx + 0.5) / 160, (yy + 0.5) / 90
        spots.append((cx, cy))
        sal[max(0, yy - 22):yy + 22, max(0, xx - 40):xx + 40] = 0
        if face:
            fx, fy = int(face[0] * 160), int(face[1] * 90)
            sal[max(0, fy - 20):fy + 20, max(0, fx - 30):fx + 30] = 0
    return {"face": face, "spots": spots}


def plan_shots(sc, info):
    """Cut the scene into shots of 0.7-1.5 s on the rhythm of Kai's voice, each with its own framing."""
    dur = sc["dur"]
    cuts = sorted(set([0.0] + [p for p in sc["phrases"] if 0.5 < p < dur - 0.5] +
                      ([sc["text_at"]] if sc["text_at"] and 0.4 < sc["text_at"] < dur - 0.4 else [])))
    pts = []
    for i, c in enumerate(cuts):                         # split long pieces, drop pieces that are too short
        end = cuts[i + 1] if i + 1 < len(cuts) else dur
        n = max(1, math.ceil((end - c) / MAX_SHOT))
        pts += [c + k * (end - c) / n for k in range(n)]
    shots = [pts[0]]
    for p in pts[1:]:
        if p - shots[-1] >= MIN_SHOT and dur - p >= MIN_SHOT:
            shots.append(p)
    face = info["face"]
    order = (["face", "wide", "detail", "face", "medium", "detail2"] if sc["mood"] == "shock" else
             ["wide", "face", "detail", "medium", "face", "detail2"])
    if not face:
        order = ["wide", "detail", "medium", "detail2"]
    out = []
    for i, st in enumerate(shots):
        kind = order[i % len(order)]
        if sc["text_at"] is not None and abs(st - sc["text_at"]) < 0.05:
            kind = "face" if face else "detail"          # the key word: punch into the face
        if out and kind == out[-1]["kind"]:
            kind = order[(i + 1) % len(order)]
        end = shots[i + 1] if i + 1 < len(shots) else dur
        out.append({"start": st, "end": end, "kind": kind,
                    "punch": sc["text_at"] is not None and abs(st - sc["text_at"]) < 0.05})
    return out


def framing(kind, info, aspect):
    """(zoom, centre_x, centre_y) for a kind of shot."""
    face = info["face"]
    if kind == "face" and face:
        z = min(2.6, max(1.6, 0.42 / face[2]))
        return z, face[0], face[1] + (0.5 - 0.42) / z      # eyes slightly above the middle
    if kind == "medium" and face:
        z = 1.45                                          # waist-up: the face sits in the top third
        return z, face[0], face[1] + (0.5 - 0.30) / z
    if kind in ("detail", "detail2"):
        sp = info["spots"][0 if kind == "detail" else -1]
        z, cx, cy = 1.9, sp[0], sp[1]
        if face:                     # never cut Kai's body in half: move the detail shot clear of him
            half = 0.5 / z
            body_l, body_r = face[0] - 1.3 * face[2] * 9 / 16, face[0] + 1.3 * face[2] * 9 / 16
            if cx - half < body_r and cx + half > body_l:
                right, left = body_r + half, body_l - half
                cx = right if right <= 1 - half else left if left >= half else None
                if cx is None:
                    return 1.45, face[0], face[1] + (0.5 - 0.30) / 1.45   # no room: waist-up shot instead
        return z, cx, cy
    if kind == "medium":
        return 1.35, 0.5, 0.5
    return 1.0, 0.5, 0.5


def render_scene(job):
    sc, out = job["scene"], job["out"]
    tmp = out + ".tmp.mp4"
    pics, infos = [], []
    for p in sc["pics"]:
        im = Image.open(p).convert("RGB")
        s = max(2400 / im.width, 1350 / im.height)
        pics.append(im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS))
        infos.append(analyse_picture(p))
    # one segment per picture (a new picture on its word), and shots inside each segment
    sw = list(sc.get("switch") or [0.0]) + [sc["dur"]]
    segs = []
    for k in range(len(pics)):
        a, b = sw[k], sw[k + 1]
        if b - a < 0.35 and segs:                         # too short to see: merge into the previous one
            segs[-1]["end"] = b
            continue
        sub = dict(sc, dur=b - a, phrases=[p - a for p in sc["phrases"] if a < p < b],
                   text_at=(sc["text_at"] - a) if sc["text_at"] is not None and a <= sc["text_at"] < b else None,
                   mood=sc["mood"] if k == 0 else "calm")
        shots = plan_shots(sub, infos[k])
        if k > 0 and shots:
            shots[0]["kind"] = "wide" if shots[0]["kind"] != "face" else "face"   # first show what it is
        segs.append({"start": a, "end": b, "pic": k, "shots": shots})
    layer = text_layer(sc["text"].upper(), 175) if sc["text"] else None
    frames = sc["frames"]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for f in range(frames):
        t = f / FPS
        seg = next(x for x in reversed(segs) if x["start"] <= t + 1e-6)
        im, info = pics[seg["pic"]], infos[seg["pic"]]
        lt = t - seg["start"]
        shot = next(x for x in reversed(seg["shots"]) if x["start"] <= lt + 1e-6)
        z, cx, cy = framing(shot["kind"], info, W / H)
        local = lt - shot["start"]
        length = max(0.01, shot["end"] - shot["start"])
        z *= 1.0 + 0.05 * ease(local / length)            # every shot slowly pushes in
        if shot["punch"] and local < 0.08:                # punch-in on the key word
            z *= 0.82 + 0.18 * local / 0.08
        dx = dy = 0.0
        first = seg is segs[0] and shot is seg["shots"][0]
        if (shot["punch"] or (sc["camera"] == "punch" and first)) and local < 0.35:
            fade = 1 - local / 0.35                       # shake on the hit
            dx, dy = 0.01 * fade * math.sin(t * 90), 0.01 * fade * math.cos(t * 75)
        vw, vh = im.width / z, im.width / z * H / W
        x0 = min(max((cx + dx) * im.width - vw / 2, 0), im.width - vw)
        y0 = min(max((cy + dy) * im.height - vh / 2, 0), im.height - vh)
        fr = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + vw, y0 + vh))
        if z > 1.5:
            fr = fr.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
        fr = fr.convert("RGBA")
        if layer is not None and t >= sc["text_at"]:
            since = t - sc["text_at"]
            if since < 0.18:
                q = since / 0.18
                sc_ = 0.4 + 0.85 * q if q < 0.7 else 1.0 + 0.2 * (1 - q) / 0.3
            else:
                sc_ = 1.0
            fade = min(1.0, max(0.0, (sc["dur"] - t) / 0.15))
            L = layer.resize((max(1, int(layer.width * sc_)), max(1, int(layer.height * sc_))), Image.BICUBIC)
            L = L.rotate(-3 if sc["text_side"] else 3, resample=Image.BICUBIC, expand=True)
            if fade < 1:
                L.putalpha(L.split()[3].point(lambda v: int(v * fade)))
            cx_ = W * (0.27 if sc["text_side"] else 0.73)
            fr.alpha_composite(L, (int(cx_ - L.width / 2), int(H * 0.80 - L.height / 2)))
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"scene {sc['n']} failed")
    os.replace(tmp, out)
    return out


# ---------- thumbnails ----------

def thumbnails(st, assets, out_dir):
    from .pictures import picture_files
    files = picture_files(st, assets)
    paths = []
    for i in range(3):
        p = files.get(f"thumb_{i + 1}", "")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((1280, 720), Image.LANCZOS)
        from PIL import ImageEnhance
        im = ImageEnhance.Color(im).enhance(1.25)
        im = ImageEnhance.Contrast(im).enhance(1.12).convert("RGBA")
        layer = text_layer(st.thumbnail_text.upper(), 190)
        if layer.width > 600:
            s = 600 / layer.width
            layer = layer.resize((600, int(layer.height * s)))
        x = 40 if i % 2 == 0 else 1280 - layer.width - 40
        im.alpha_composite(layer.rotate(-4 if i % 2 == 0 else 4, expand=True, resample=Image.BICUBIC), (x, 30))
        out = os.path.join(out_dir, f"thumbnail_{i + 1}.png")
        im.convert("RGB").save(out)
        paths.append(out)
    return paths


def upload_text(st, out_dir, length):
    lines = ["TITLE:", st.title, "", "DESCRIPTION:", st.description, "", "Sources:",
             *[f"- {s}" for s in st.sources], "", "TAGS:", ", ".join(st.tags), "",
             "SETTINGS:", "- Audience: No, it's not made for kids",
             "- Altered or synthetic content: No (cartoon illustrations, not realistic). Narration voice is AI.",
             "- Thumbnail: upload all three with 'Test & compare'",
             f"- Length: {int(length // 60)}:{int(length % 60):02d}"]
    with open(os.path.join(out_dir, "upload.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


# ---------- main ----------

def build(story_path, assets, kit_dir, cands, out_dir, workers=None):
    st = load(story_path)
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "_scenes")
    os.makedirs(work, exist_ok=True)
    scenes, placed, music_runs, length = make_plan(st, assets, kit_dir, cands)
    # scenes start where the previous one ends, so the joined video matches the audio exactly
    jobs = []
    for i, sc in enumerate(scenes):
        end = scenes[i + 1]["start"] if i + 1 < len(scenes) else length
        sc2 = dict(sc)
        f0, f1 = round(sc["start"] * FPS), round(end * FPS)      # frame-exact, so picture and sound never drift
        sc2["frames"] = f1 - f0
        sc2["dur"] = (f1 - f0) / FPS
        sc2.pop("voice")
        jobs.append({"scene": sc2, "out": os.path.join(work, f"s{i:03d}.mp4")})
    first = scenes[0]["start"]
    with Pool(workers or os.cpu_count()) as pool:
        files = pool.map(render_scene, jobs)
    lead = os.path.join(work, "lead.mp4")                     # the tiny gap before the first line
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}",
                    "-frames:v", str(max(1, round(first * FPS))), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "19", "-pix_fmt", "yuv420p", lead], check=True)
    with open(os.path.join(work, "list.txt"), "w") as f:
        for p in [lead] + files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    silent = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(work, "list.txt"), "-c", "copy", silent], check=True)
    audio = os.path.join(work, "audio.wav")
    mix(scenes, placed, music_runs, length, audio)
    final = os.path.join(out_dir, "video.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", silent, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", final + ".tmp.mp4"], check=True)
    os.replace(final + ".tmp.mp4", final)
    thumbnails(st, assets, out_dir)
    upload_text(st, out_dir, length)
    json.dump({"length": length, "music": [{k: v for k, v in r.items()} for r in music_runs],
               "sounds": len(placed)}, open(os.path.join(out_dir, "edit.json"), "w"), indent=1)
    shutil.rmtree(work, ignore_errors=True)
    print("wrote", final, f"{length / 60:.1f} min")
    return final


if __name__ == "__main__":
    build(*sys.argv[1:6])
