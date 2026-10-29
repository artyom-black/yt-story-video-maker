"""Voice lab, step 2: Chatterbox-Turbo performs every line, copying each voice from its reference clip.
Runs in its own environment (torch + chatterbox-tts), so it imports nothing from the rest of the maker.

Usage:  .venv-tts/bin/python maker/voice_lab_cb.py jobs.json out_dir [--shard I/N]
With --shard, only every N-th job starting at I is recorded (to split the work over machines).
"""
import inspect
import json
import os
import sys
import time
import wave


def _words(text):
    import re
    text = re.sub(r"\[[^\]]+\]", "", text.lower())
    return re.findall(r"[a-z']+", text)


def match_score(said, wanted):
    """Share of the wanted words that were really said (in order), 0..1."""
    import difflib
    a, b = _words(wanted), _words(said)
    if not a:
        return 1.0
    sm = difflib.SequenceMatcher(None, a, b)
    return sum(m.size for m in sm.get_matching_blocks()) / len(a)


def main(jobs_path, out_dir, shard=None, check=False):
    import numpy as np
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    from huggingface_hub import snapshot_download

    os.makedirs(out_dir, exist_ok=True)
    path = snapshot_download(repo_id="ResembleAI/chatterbox-turbo", token=None)
    model = ChatterboxTurboTTS.from_local(path, device="cpu")
    params = inspect.signature(model.generate).parameters
    print("generate() accepts:", list(params), flush=True)

    asr = None
    if check:                                   # listen back to every line and redo it if words are missing
        from faster_whisper import WhisperModel
        asr = WhisperModel("base.en", device="cpu", compute_type="int8")
    jobs = json.load(open(jobs_path))
    if shard:
        k, n = (int(x) for x in shard.split("/"))
        jobs = jobs[k::n]
    for i, job in enumerate(jobs):
        t0 = time.time()
        torch.manual_seed(int(job.get("seed", 0)))
        kwargs = {"audio_prompt_path": job["ref"]}
        if "exaggeration" in params:
            kwargs["exaggeration"] = job["exaggeration"]
        if "cfg_weight" in params:
            kwargs["cfg_weight"] = 0.3 if job["mood"] in ("shock", "funny") else 0.5
        out_path = os.path.join(out_dir, job["out"])
        if os.path.exists(out_path):
            continue
        best, best_score, said = None, -1.0, ""
        for attempt in range(4 if asr else 1):
            torch.manual_seed(int(job.get("seed", 0)) + attempt * 101)
            wav = model.generate(job["text"], **kwargs)
            a = wav.detach().cpu().numpy().reshape(-1)
            a = np.clip(a / max(1e-6, float(np.abs(a).max())) * 0.9, -1, 1)
            if not asr:
                best = a
                break
            import librosa
            a16 = librosa.resample(a.astype(np.float32), orig_sr=int(model.sr), target_sr=16000)
            segs, _ = asr.transcribe(a16, language="en", beam_size=1)
            said = " ".join(sg.text for sg in segs)
            sc = match_score(said, job["text"])
            if sc > best_score:
                best, best_score = a, sc
            if sc >= 0.92:
                break
        with wave.open(os.path.join(out_dir, job["out"]), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(int(model.sr))
            w.writeframes((best * 32767).astype(np.int16).tobytes())
        note = f" words ok {best_score:.0%}" if asr else ""
        print(f"[{i + 1}/{len(jobs)}] {job['out']}  {time.time() - t0:.1f}s{note}", flush=True)
        if asr and best_score < 0.92:
            print(f"   WARNING best take still misses words: wanted '{job['text']}' heard '{said}'", flush=True)
    if not shard:
        json.dump(jobs, open(os.path.join(out_dir, "jobs.json"), "w"), indent=1)


if __name__ == "__main__":
    shard = sys.argv[sys.argv.index("--shard") + 1] if "--shard" in sys.argv else None
    main(sys.argv[1], sys.argv[2], shard, check="--check" in sys.argv)
