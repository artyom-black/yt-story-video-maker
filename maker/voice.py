"""Text to speech with Kokoro (free, runs on the CPU), one fixed voice per character.

Needs the model files in TTS_DIR (default: tools/tts):
  kokoro-v1.0.int8.onnx, voices-v1.0.bin, piper/espeak-ng (for phonemes)
The GitHub workflow downloads them; locally, run the same curl lines.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.environ.get("TTS_DIR", os.path.join(os.path.dirname(HERE), "tools", "tts"))
VOCAB = json.load(open(os.path.join(HERE, "kokoro_config.json")))["vocab"]
RATE = 24000

# Mood changes how a line is delivered: speed and how long the pause after it is.
MOOD_DELIVERY = {
    "shock": {"speed": 1.12, "pause": 0.25},
    "scary": {"speed": 0.95, "pause": 0.35},
    "tense": {"speed": 1.05, "pause": 0.25},
    "sad": {"speed": 0.9, "pause": 0.4},
    "funny": {"speed": 1.04, "pause": 0.3},
    "epic": {"speed": 0.95, "pause": 0.35},
    "calm": {"speed": 1.0, "pause": 0.3},
    "curious": {"speed": 1.02, "pause": 0.25},
}

_sess = None
_voices = None


def _phonemes(text: str) -> str:
    piper = os.path.join(TTS_DIR, "piper")
    env = dict(os.environ, LD_LIBRARY_PATH=piper)
    out = subprocess.run([os.path.join(piper, "espeak-ng"), f"--path={piper}", "-q", "--ipa", "-v", "en-us", text],
                         capture_output=True, text=True, env=env).stdout
    ph = " ".join(line.strip() for line in out.splitlines() if line.strip()).replace("_", "")
    return "".join(c for c in ph if c in VOCAB)


def _style(voice: str, n_tokens: int):
    """A voice name, or a blend like "am_echo:0.6+am_michael:0.4" (weights default to equal)."""
    parts = []
    for item in voice.split("+"):
        name, _, w = item.partition(":")
        parts.append((name.strip(), float(w) if w else 1.0))
    total = sum(w for _, w in parts)
    vecs = [_voices[n][min(n_tokens, len(_voices[n])) - 1] * (w / total) for n, w in parts]
    return sum(vecs)


def speak(text: str, voice: str, speed: float = 1.0, gap: float = 0.12) -> np.ndarray:
    """Return mono float32 audio at 24 kHz."""
    global _sess, _voices
    import onnxruntime as ort
    if _sess is None:
        _sess = ort.InferenceSession(os.path.join(TTS_DIR, "kokoro-v1.0.int8.onnx"))
        _voices = np.load(os.path.join(TTS_DIR, "voices-v1.0.bin"))
    names = [i.name for i in _sess.get_inputs()]
    tok_name = "tokens" if "tokens" in names else "input_ids"
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    audio = []
    for p in parts:
        ph = _phonemes(p)
        if p[-1] in ".!?":
            ph += p[-1]
        toks = [VOCAB[c] for c in ph if c in VOCAB][:510]
        style = _style(voice, len(toks))
        out = _sess.run(None, {tok_name: np.array([[0, *toks, 0]], dtype=np.int64),
                               "style": np.asarray(style, dtype=np.float32),
                               "speed": np.array([speed], dtype=np.float32)})[0].ravel()
        audio.append(out.astype(np.float32))
        if gap:
            audio.append(np.zeros(int(RATE * gap), dtype=np.float32))
    a = np.concatenate(audio) if audio else np.zeros(1, dtype=np.float32)
    peak = float(np.abs(a).max()) or 1.0
    return (a / peak * 0.9).astype(np.float32)


def tighten_pauses(audio: np.ndarray, max_gap: float = 0.26, keep: float = 0.2) -> np.ndarray:
    """Shorten unnaturally long silences inside a line (the "robotic cut" sound).
    Any pause longer than max_gap seconds is shortened to keep seconds; start and end are trimmed too."""
    hop = int(0.01 * RATE)
    env = np.array([np.sqrt(np.mean(audio[i:i + hop] ** 2)) for i in range(0, len(audio) - hop + 1, hop)])
    if not len(env):
        return audio
    quiet = env < 0.04 * (env.max() or 1)
    voiced = np.where(~quiet)[0]
    if not len(voiced):
        return audio
    out, i, n = [], voiced[0], voiced[-1] + 1
    while i < n:
        j = i
        while j < n and quiet[j] == quiet[i]:
            j += 1
        seg = audio[i * hop:j * hop]
        if quiet[i] and (j - i) * 0.01 > max_gap:
            k = int(keep * RATE)
            fade = np.linspace(1, 0, k // 2, dtype=np.float32)
            seg = np.concatenate([seg[:k // 2] * fade, seg[-(k - k // 2):] * fade[::-1][:k - k // 2]])
        out.append(seg)
        i = j
    return np.concatenate(out).astype(np.float32)


def mouth_track(audio: np.ndarray, fps: int = 24) -> list[float]:
    """Loudness per video frame, 0..1, used to open and close the mouth in sync with the voice."""
    n = int(np.ceil(len(audio) / RATE * fps))
    hop = RATE / fps
    vals = []
    for i in range(n):
        seg = audio[int(i * hop):int((i + 1) * hop)]
        vals.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    top = max(vals) or 1.0
    return [min(1.0, v / (0.55 * top)) for v in vals]


def save_wav(path: str, audio: np.ndarray):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
