"""Motion engine for AI character sprites (cut-out PNGs) on AI backgrounds.

The sprites never bend: life comes from pose switches on the beat, body motion (breathing, pop-ins,
bounces, jumps, trembling) and MrBeast-style camera work (push-ins, punch-zooms, shakes, pans).

Usage (demo):  python -m maker.motion demo SPRITE_DIR BACKGROUND.png out.mp4
"""
from __future__ import annotations

import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT_W, OUT_H, FPS = 1920, 1080, 30
STAGE_W, STAGE_H = 2560, 1440          # drawn bigger than the output, so the camera can zoom without blur
FLOOR_Y = 1330                          # where the feet stand on the stage


# ---------- sprites ----------

class Sprite:
    """A cut-out pose. Anchored at the feet, so switching poses never makes the character jump sideways."""

    def __init__(self, path: str, height: int):
        im = Image.open(path).convert("RGBA")
        im = im.crop(im.getbbox())
        s = height / im.height
        self.img = im.resize((max(1, int(im.width * s)), height), Image.LANCZOS)
        a = np.asarray(self.img)[:, :, 3]
        feet = a[int(a.shape[0] * 0.9):]
        cols = np.where(feet.sum(axis=0) > 0)[0]
        self.foot_x = int(cols.mean()) if len(cols) else self.img.width // 2

    def scaled(self, sx: float, sy: float) -> tuple[Image.Image, int]:
        w, h = max(1, int(self.img.width * sx)), max(1, int(self.img.height * sy))
        return self.img.resize((w, h), Image.BILINEAR), int(self.foot_x * sx)


def load_cast(sprite_dir: str, name: str, height: int, suffix="_1_cut.png") -> dict[str, Sprite]:
    out = {}
    prefix = name.lower() + "_"
    for f in sorted(os.listdir(sprite_dir)):
        if f.startswith(prefix) and f.endswith(suffix):
            out[f[len(prefix):-len(suffix)]] = Sprite(os.path.join(sprite_dir, f), height)
    return out


# ---------- easing ----------

def ease_out_back(t: float, k: float = 1.7) -> float:
    t -= 1
    return t * t * ((k + 1) * t + k) + 1


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


# ---------- body motion ----------

def body_motion(kind: str, t: float, since: float) -> tuple[float, float, float, float]:
    """(offset_x, offset_y, scale_x, scale_y) for the body at time t; `since` = seconds since this pose started."""
    breath = 1 + 0.012 * math.sin(t * 2 * math.pi / 3.2)          # slow breathing, always on
    sx, sy, dx, dy = 1.0, breath, 0.0, 0.0
    if since < 0.18:                                                # pop-in on every pose change (squash & stretch)
        p = since / 0.18
        sy *= 1 + 0.06 * math.sin(p * math.pi)
        sx *= 1 - 0.035 * math.sin(p * math.pi)
    if kind == "laughing":                                          # belly-laugh bounce
        dy -= abs(math.sin(t * 2 * math.pi * 2.6)) * 14
    elif kind == "scared":                                          # trembling
        dx += math.sin(t * 2 * math.pi * 13) * 4
        dy += math.cos(t * 2 * math.pi * 11) * 2
    elif kind == "excited":                                         # a happy jump at the start
        if since < 0.55:
            p = since / 0.55
            dy -= math.sin(p * math.pi) * 150
            if p > 0.9:
                sy *= 0.94; sx *= 1.04                              # landing squash
    elif kind.startswith("talk"):                                   # small nods while talking
        dy += math.sin(t * 2 * math.pi * 1.7) * 4
    return dx, dy, sx, sy


# ---------- camera ----------

class Camera:
    """Keys: (time, zoom, centre_x, centre_y, ease_seconds). Plus shakes: (time, seconds, strength)."""

    def __init__(self):
        self.keys = [(0.0, 1.0, STAGE_W / 2, STAGE_H / 2, 0.0)]
        self.shakes = []

    def key(self, t, zoom, cx, cy, ease=0.35):
        self.keys.append((t, zoom, cx, cy, ease))
        self.keys.sort()

    def shake(self, t, seconds=0.35, strength=22):
        self.shakes.append((t, seconds, strength))

    def at(self, t):
        prev = self.keys[0]
        for k in self.keys:
            if k[0] <= t:
                prev, cur = k, k
        # find the key before the current one to ease from
        idx = self.keys.index(prev)
        before = self.keys[idx - 1] if idx > 0 else prev
        p = ease_in_out((t - prev[0]) / prev[4]) if prev[4] > 0 else 1.0
        z = before[1] + (prev[1] - before[1]) * p
        cx = before[2] + (prev[2] - before[2]) * p
        cy = before[3] + (prev[3] - before[3]) * p
        for st, sec, s in self.shakes:
            if st <= t < st + sec:
                fall = 1 - (t - st) / sec
                cx += math.sin(t * 97) * s * fall
                cy += math.cos(t * 83) * s * fall
        return z, cx, cy

    def frame(self, stage: Image.Image, t: float) -> Image.Image:
        z, cx, cy = self.at(t)
        vw = STAGE_W / z
        vh = vw * OUT_H / OUT_W
        cx = min(max(cx, vw / 2), STAGE_W - vw / 2)
        cy = min(max(cy, vh / 2), STAGE_H - vh / 2)
        box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
        return stage.resize((OUT_W, OUT_H), Image.BILINEAR, box=box)


# ---------- scene ----------

def background(path: str) -> Image.Image:
    bg = Image.open(path).convert("RGB")
    s = max(STAGE_W / bg.width, STAGE_H / bg.height)
    bg = bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS)
    x, y = (bg.width - STAGE_W) // 2, (bg.height - STAGE_H) // 2
    return bg.crop((x, y, x + STAGE_W, y + STAGE_H))


def shadow(width: int) -> Image.Image:
    sh = Image.new("RGBA", (width, width // 5), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, width - 1, width // 5 - 1), fill=(0, 0, 0, 90))
    return sh.filter(ImageFilter.GaussianBlur(width // 25))


def draw_character(stage: Image.Image, sprite: Sprite, x: int, kind: str, t: float, since: float):
    dx, dy, sx, sy = body_motion(kind, t, since)
    img, foot = sprite.scaled(sx, sy)
    sh = shadow(int(sprite.img.width * 0.55))
    lift = max(0.0, -dy) / 150                                     # shadow shrinks when jumping
    sh = sh.resize((max(1, int(sh.width * (1 - 0.4 * lift))), max(1, int(sh.height * (1 - 0.4 * lift)))))
    stage.alpha_composite(sh, (int(x - sh.width / 2 + dx), int(FLOOR_Y - sh.height / 2)))
    stage.alpha_composite(img, (int(x - foot + dx), int(FLOOR_Y - img.height + dy)))


def render(timeline, cast, bg_path, out, seconds, camera, x=None, talk_rate=0.13):
    """timeline: list of (start_time, pose). A pose 'talk' alternates talk_closed/talk_open like syllables."""
    bg = background(bg_path).convert("RGBA")
    x = x or STAGE_W // 2
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(int(seconds * FPS)):
        t = f / FPS
        start, pose = max((k for k in timeline if k[0] <= t), key=lambda k: k[0])
        since = t - start
        if pose == "talk":
            syll = int(since / talk_rate)
            pose_img = "talk_open" if (syll % 3) != 2 else "talk_closed"
            kind, since_pose = "talk", since if since < 0.18 else 1.0
        else:
            pose_img, kind, since_pose = pose, pose, since
        stage = bg.copy()
        draw_character(stage, cast[pose_img], x, kind, t, since_pose)
        ff.stdin.write(camera.frame(stage, t).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()


def demo(sprite_dir, bg_path, out):
    cast = load_cast(sprite_dir, "kai", height=1000)
    x = int(STAGE_W * 0.27)                                          # beside the fire, not in it
    head_y = FLOOR_Y - 1000 + 160
    timeline = [(0.0, "neutral"), (1.6, "talk"), (3.6, "shocked"), (5.0, "laughing"), (6.8, "scared"),
                (8.2, "pointing"), (9.8, "excited"), (11.4, "thinking")]
    cam = Camera()
    cam.key(0.0, 1.0, STAGE_W / 2, STAGE_H / 2, 0)
    cam.key(1.6, 1.25, x, STAGE_H / 2 + 60, 1.8)                    # slow push-in while he talks
    cam.key(3.6, 2.1, x, head_y + 120, 0.12)                         # punch-zoom into the shocked face
    cam.shake(3.6, 0.45, 26)
    cam.key(5.0, 1.15, x, STAGE_H / 2 + 80, 0.25)                    # back out for the laugh
    cam.key(6.8, 1.45, x, STAGE_H / 2, 0.3)                          # tighter on the fear
    cam.shake(6.8, 0.3, 10)
    cam.key(8.2, 1.2, x - 200, STAGE_H / 2, 0.5)                     # pan towards where he points
    cam.key(9.8, 1.0, STAGE_W / 2, STAGE_H / 2, 0.3)                 # wide for the jump
    cam.key(11.4, 1.35, x, STAGE_H / 2 + 40, 1.2)
    render(timeline, cast, bg_path, out, 13.0, cam, x=x)


if __name__ == "__main__":
    if sys.argv[1] == "demo":
        demo(sys.argv[2], sys.argv[3], sys.argv[4])
