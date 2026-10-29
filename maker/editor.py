"""MrBeast-style editor for AI character sprites (first version, used for the Kai demo).

- Part-based body motion: each cut-out is split into legs, upper body and head, which move separately
  (laughing shakes the shoulders and tilts the head back, the feet stay planted; breathing moves the chest).
- Lip sync: Rhubarb Lip Sync reads the voice and picks one of the mouth shapes A-H/X for every moment;
  only the mouth area of the face changes, so nothing else can flicker.
- Editing: punch-zooms, shakes, pans, whoosh transitions, pop-up key words, sound effects on every beat,
  music ducked under the voice, loudness normalised for YouTube (-14 LUFS).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .motion import FLOOR_Y, FPS, OUT_H, OUT_W, STAGE_H, STAGE_W, Camera, background, shadow

FONT_PATHS = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "Anton-Regular.ttf"), "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",
              "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
              "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"]


# ---------- affine helper ----------

def affine(img: Image.Image, angle=0.0, pivot=(0, 0), sx=1.0, sy=1.0, tx=0.0, ty=0.0) -> Image.Image:
    """Rotate (degrees, positive = clockwise on screen) and scale around `pivot`, then move by (tx, ty)."""
    if not angle and sx == 1 and sy == 1 and not tx and not ty:
        return img
    th = math.radians(angle)
    c, s = math.cos(th), math.sin(th)
    # inverse of: p_out = pivot + R(th) S (p_in - pivot) + t   (y axis points down)
    m00, m01 = c / sx, s / sx
    m10, m11 = -s / sy, c / sy
    px, py = pivot
    qx, qy = px + tx, py + ty
    a, b = m00, m01
    d, e = m10, m11
    cc = px - a * qx - b * qy
    f = py - d * qx - e * qy
    return img.transform(img.size, Image.AFFINE, (a, b, cc, d, e, f), resample=Image.BICUBIC)


# ---------- rig ----------

class Rig:
    """A cut-out split into legs / upper body / head on soft seams. Anchored at the feet (or the bottom edge)."""

    PAD = 120

    def __init__(self, path: str, height: int, full_body=True, rgb_override: Image.Image | None = None):
        im = Image.open(path).convert("RGBA")
        if rgb_override is not None:
            rgb = rgb_override.convert("RGB").resize(im.size)
            im = Image.merge("RGBA", (*rgb.split(), im.split()[3]))
        box = im.getbbox()
        im = im.crop(box)
        s = height / im.height
        im = im.resize((max(1, int(im.width * s)), height), Image.LANCZOS)
        P = self.PAD
        canvas = Image.new("RGBA", (im.width + 2 * P, im.height + P), (0, 0, 0, 0))
        canvas.paste(im, (P, P))
        self.size = canvas.size
        a = np.asarray(canvas)[:, :, 3].astype(np.float32)
        H = im.height
        rows = (a > 20).sum(axis=1)
        if full_body:
            lo, hi = P + int(H * 0.12), P + int(H * 0.26)
            self.hip_y = P + int(H * 0.60)
        else:                                    # waist-up: no legs, the "hip" is the bottom edge
            lo, hi = P + int(H * 0.25), P + int(H * 0.48)
            self.hip_y = P + H
        self.neck_y = lo + int(np.argmin(rows[lo:hi]))
        cols = np.where(a[self.neck_y] > 20)[0]
        self.neck_x = int(cols.mean()) if len(cols) else canvas.width // 2
        cols = np.where(a[min(self.hip_y, a.shape[0] - 1)] > 20)[0]
        self.hip_x = int(cols.mean()) if len(cols) else canvas.width // 2
        feet = a[P + int(H * 0.9):P + H]
        cols = np.where(feet.sum(axis=0) > 0)[0]
        self.foot_x = int(cols.mean()) if len(cols) else canvas.width // 2
        self.bottom = P + H
        self.full_body = full_body
        self.legs = self._band(canvas, a, self.hip_y - 40, None, fade_top=0)
        self.torso = self._band(canvas, a, self.neck_y - 30, self.hip_y + 36, fade_bottom=36)
        self.head = self._band(canvas, a, None, self.neck_y + 26, fade_bottom=26)

    @staticmethod
    def _band(canvas, alpha, top, bottom, fade_top=0, fade_bottom=0):
        h = alpha.shape[0]
        w = np.ones(h, dtype=np.float32)
        y = np.arange(h)
        if top is not None:
            w[y < top] = 0
        if bottom is not None:
            w[y >= bottom] = 0
            if fade_bottom:
                band = (y >= bottom - fade_bottom) & (y < bottom)
                w[band] = (bottom - y[band]) / fade_bottom
        out = canvas.copy()
        new_a = (alpha * w[:, None]).clip(0, 255).astype(np.uint8)
        out.putalpha(Image.fromarray(new_a))
        return out

    def pose(self, torso_angle=0.0, torso_dx=0.0, torso_dy=0.0, chest=1.0, head_angle=0.0, head_dy=0.0):
        layers = Image.new("RGBA", self.size, (0, 0, 0, 0))
        if self.full_body:
            layers.alpha_composite(self.legs)
        hip = (self.hip_x, self.hip_y)
        head = affine(self.head, head_angle, (self.neck_x, self.neck_y), 1, 1, 0, head_dy)
        upper = self.torso.copy()
        upper.alpha_composite(head)
        upper = affine(upper, torso_angle, hip, 1.0, chest, torso_dx, torso_dy)
        layers.alpha_composite(upper)
        return layers


def acting(kind: str, t: float, since: float) -> tuple[dict, tuple]:
    """Body-part motion for a kind of acting. Returns (rig pose kwargs, whole-body (dx, dy, sx, sy))."""
    breath = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 3.0)
    p = dict(chest=1 + 0.012 * breath)
    dx = dy = 0.0
    sx = sy = 1.0
    if since < 0.16:                                         # pop-in on every pose change
        q = math.sin(since / 0.16 * math.pi)
        sy, sx = 1 + 0.05 * q, 1 - 0.03 * q
    if kind == "laughing":
        b = abs(math.sin(t * 2 * math.pi * 4.0))
        p.update(torso_dy=-6 * b, torso_angle=-1.2 + 0.8 * math.sin(t * 2 * math.pi * 4.0),
                 head_angle=-5 - 3 * b)                      # shoulders shake, head thrown back
    elif kind == "scared":
        p.update(torso_dx=3.5 * math.sin(t * 2 * math.pi * 12), torso_angle=-2.0,
                 head_angle=1.5 * math.sin(t * 2 * math.pi * 9))
    elif kind == "talk":
        p.update(head_angle=1.8 * math.sin(t * 2 * math.pi * 1.6), torso_angle=0.5 * math.sin(t * 2 * math.pi * 0.8),
                 head_dy=1.5 * math.sin(t * 2 * math.pi * 3.2))
    elif kind == "shocked":
        jerk = max(0.0, 1 - since / 0.3)
        p.update(head_angle=-4 * jerk - 0.8, torso_angle=-1.5 * jerk, torso_dy=-4 * jerk)
    elif kind == "disgusted":
        p.update(torso_angle=-2.5 * min(1, since / 0.25), head_angle=2.5 * min(1, since / 0.25) +
                 0.8 * math.sin(t * 2 * math.pi * 1.3))
    elif kind == "excited":
        if since < 0.55:
            dy = -math.sin(since / 0.55 * math.pi) * 140
        p.update(head_angle=2 * math.sin(t * 2 * math.pi * 2.2))
    else:
        p.update(head_angle=0.8 * math.sin(t * 2 * math.pi * 0.5))
    return p, (dx, dy, sx, sy)


# ---------- lip sync ----------

def rhubarb(wav: str, text: str, exe: str) -> list[tuple[float, str]]:
    """Mouth cues [(time, shape)] for a voice line."""
    dialog = wav + ".txt"
    with open(dialog, "w") as f:
        f.write(text)
    out = subprocess.run([exe, "-q", "-f", "tsv", "--extendedShapes", "GX", "-d", dialog, wav],
                         capture_output=True, text=True, check=True).stdout
    cues = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            cues.append((float(parts[0]), parts[1].strip()))
    return cues


def shape_at(cues, t):
    s = "X"
    for ct, cs in cues:
        if ct <= t:
            s = cs
        else:
            break
    return s


def mouth_images(base_png: str, face_box: list, mouth_dir: str, prefix: str) -> dict[str, Image.Image]:
    """Full talking-base pictures for every mouth shape: only the mouth area is taken from each edit."""
    base = Image.open(base_png).convert("RGB")
    hx0, hy0, side = face_box
    face = base.crop((hx0, hy0, hx0 + side, hy0 + side)).resize((512, 512), Image.LANCZOS)
    fa = np.asarray(face).astype(np.float32)
    out = {"A": base, "X": base}
    for shape in "BCDEFG":
        p = os.path.join(mouth_dir, f"{prefix}{shape}.png")
        if not os.path.exists(p):
            continue
        m = Image.open(p).convert("RGB").resize((512, 512), Image.LANCZOS)
        ma = np.asarray(m).astype(np.float32)
        diff = np.abs(ma - fa).sum(axis=2)
        region = np.zeros_like(diff)
        region[int(512 * 0.40):int(512 * 0.92), int(512 * 0.22):int(512 * 0.78)] = 1
        mask = ((diff > 45) * region * 255).astype(np.uint8)
        mask = Image.fromarray(mask).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(7))
        new_face = Image.composite(m, face, mask).resize((side, side), Image.LANCZOS)
        full = base.copy()
        full.paste(new_face, (hx0, hy0))
        out[shape] = full
    out["H"] = out.get("C", base)
    return out


# ---------- text ----------

def _font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def text_layer(words: str, size: int, fill="#ffd23f") -> Image.Image:
    font = _font(size)
    stroke = max(6, size // 11)
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    x0, y0, x1, y1 = d.textbbox((0, 0), words, font=font, stroke_width=stroke)
    w, h = x1 - x0 + 40, y1 - y0 + 40
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - x0 + 8, 20 - y0 + 10), words, font=font, fill=(0, 0, 0, 150),
                            stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(img).text((20 - x0, 20 - y0), words, font=font, fill=fill, stroke_width=stroke,
                             stroke_fill="#111111")
    return img


def draw_text(frame: Image.Image, layer: Image.Image, cx, cy, since, angle=-4):
    if since < 0:
        return
    if since < 0.2:
        q = since / 0.2
        sc = 0.35 + 0.8 * q if q < 0.75 else 1.15 - 0.6 * (q - 0.75)
    else:
        sc = 1.0 + 0.015 * math.sin(since * 6)
    im = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BICUBIC)
    im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ---------- audio ----------

def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def mix_audio(out_wav, length, voices, sfx, music=None, music_db=-21):
    """voices / sfx: [(start_seconds, path, gain_db)]. Music is ducked under the voices."""
    inputs, filters, labels = [], [], []
    for i, (t, p, g) in enumerate(voices + sfx):
        inputs += ["-i", p]
        ms = int(t * 1000)
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g}dB,"
                       f"adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    nv = len(voices)
    filters.append("".join(labels[:nv]) + f"amix=inputs={nv}:normalize=0[vox]")
    filters.append("[vox]asplit=2[vox1][vox2]")
    fx = "".join(labels[nv:])
    if music:
        mi = len(voices) + len(sfx)
        inputs += ["-i", music]
        filters.append(f"[{mi}:a]aresample=48000,aformat=channel_layouts=stereo,volume={music_db}dB,"
                       f"atrim=0:{length},afade=t=out:st={max(0, length - 1.0)}:d=1.0[mus]")
        filters.append("[mus][vox2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck]")
        filters.append(f"[vox1][duck]{fx}amix=inputs={2 + len(sfx)}:normalize=0[mixed]")
    else:
        filters.append(f"[vox1]{fx}amix=inputs={1 + len(sfx)}:normalize=0[mixed]")
    filters.append(f"[mixed]atrim=0:{length},loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-ar", "48000", out_wav], check=True)


# ---------- shots ----------

class Shot:
    """One camera shot: a background, a character rig (or talking frames), camera keys, text pops, length."""

    def __init__(self, start, end, bg, rig=None, kind="neutral", x=None, height=None, talk=None, cues=None,
                 blur_bg=0, camera=None, texts=(), bottom_anchor=False):
        self.start, self.end = start, end
        self.bg = background(bg).convert("RGBA")
        if blur_bg:
            self.bg = self.bg.filter(ImageFilter.GaussianBlur(blur_bg))
        self.rig, self.kind, self.x = rig, kind, x or STAGE_W // 2
        self.talk, self.cues = talk, cues or []
        self.camera = camera or Camera()
        self.texts = list(texts)                      # [(time, layer, cx, cy)]
        self.bottom_anchor = bottom_anchor

    def frame(self, t):
        local = t - self.start
        stage = self.bg.copy()
        rig = self.rig
        if self.talk:                                 # lip-synced talking rig
            rig = self.talk[shape_at(self.cues, local)]
        kw, (dx, dy, sx, sy) = acting(self.kind, t, local)
        body = rig.pose(**kw)
        if sx != 1 or sy != 1:
            body = affine(body, 0, (rig.foot_x, rig.bottom), sx, sy)
        if rig.full_body:
            sh = shadow(int((rig.size[0] - 2 * rig.PAD) * 0.6))
            stage.alpha_composite(sh, (int(self.x - sh.width / 2 + dx), int(FLOOR_Y - sh.height / 2)))
            pos = (int(self.x - rig.foot_x + dx), int(FLOOR_Y - rig.bottom + dy))
        else:
            pos = (int(self.x - rig.hip_x + dx), int(STAGE_H - rig.bottom + 40 + dy))
        stage.alpha_composite(body, pos)
        frame = self.camera.frame(stage, local).convert("RGBA")
        for tt, layer, cx, cy in self.texts:
            draw_text(frame, layer, cx, cy, local - tt)
        return frame


def render(shots, length, audio_wav, out_mp4, flash_at=()):
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-i", audio_wav,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4], stdin=subprocess.PIPE)
    black = Image.new("RGB", (OUT_W, OUT_H), "black")
    for f in range(int(length * FPS)):
        t = f / FPS
        shot = next((s for s in shots if s.start <= t < s.end), None)
        if shot is None:
            ff.stdin.write(black.tobytes())
            continue
        fr = shot.frame(t)
        # whoosh transition: a quick sideways smear in the first 4 frames of a new shot
        if shot.start > 0 and t - shot.start < 4 / FPS:
            k = 1 - (t - shot.start) * FPS / 4
            fr = fr.transform(fr.size, Image.AFFINE, (1, 0, -120 * k, 0, 1, 0)).filter(ImageFilter.BoxBlur(10 * k))
        for ft in flash_at:                           # white flash on big hits
            if 0 <= t - ft < 0.1:
                fr = Image.blend(fr.convert("RGB"), Image.new("RGB", fr.size, "white"),
                                 0.55 * (1 - (t - ft) / 0.1)).convert("RGBA")
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
