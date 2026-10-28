"""Voice lab, step 2: Chatterbox-Turbo performs every line, copying each voice from its reference clip.
Runs in its own environment (torch + chatterbox-tts), so it imports nothing from the rest of the maker.

Usage:  .venv-tts/bin/python maker/voice_lab_cb.py jobs.json out_dir
"""
import inspect
import json
import os
import sys
import time
import wave


def main(jobs_path, out_dir):
    import numpy as np
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    from huggingface_hub import snapshot_download

    os.makedirs(out_dir, exist_ok=True)
    path = snapshot_download(repo_id="ResembleAI/chatterbox-turbo", token=None)
    model = ChatterboxTurboTTS.from_local(path, device="cpu")
    params = inspect.signature(model.generate).parameters
    print("generate() accepts:", list(params), flush=True)

    jobs = json.load(open(jobs_path))
    for i, job in enumerate(jobs):
        t0 = time.time()
        torch.manual_seed(int(job.get("seed", 0)))
        kwargs = {"audio_prompt_path": job["ref"]}
        if "exaggeration" in params:
            kwargs["exaggeration"] = job["exaggeration"]
        if "cfg_weight" in params:
            kwargs["cfg_weight"] = 0.3 if job["mood"] in ("shock", "funny") else 0.5
        wav = model.generate(job["text"], **kwargs)
        a = wav.detach().cpu().numpy().reshape(-1)
        a = np.clip(a / max(1e-6, float(np.abs(a).max())) * 0.9, -1, 1)
        with wave.open(os.path.join(out_dir, job["out"]), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(int(model.sr))
            w.writeframes((a * 32767).astype(np.int16).tobytes())
        print(f"[{i + 1}/{len(jobs)}] {job['out']}  {time.time() - t0:.1f}s", flush=True)
    json.dump(jobs, open(os.path.join(out_dir, "jobs.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
