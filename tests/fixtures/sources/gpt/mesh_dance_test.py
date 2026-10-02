#!/usr/bin/env python3
"""
mesh_dance_test.py — pose-swap + foot-anchored mesh-warp prototype.

Expected inputs in the same directory:
    p01.png ... p13.png

Outputs:
    mesh_dance_test.mp4
    mesh_dance_test.gif

Production rules exercised:
- BPM 189.9 measured timing, half-time grid.
- Accumulate fractional frame positions; round only absolute boundaries.
- Never per-pose scale to "normalize" character size.
- Never align horizontally by bbox center.
- Pose swaps are hard cuts.
- Mesh deformation is secondary motion within/between holds.
- Feet stay anchored unless the source drawing itself clearly depicts a jump.
- Breathing is intentionally subtle.
"""
from PIL import Image
import numpy as np
import cv2
import math
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSE_PATHS = [ROOT / f"p{i:02d}.png" for i in range(1, 14)]
MP4_PATH = ROOT / "mesh_dance_test.mp4"
GIF_PATH = ROOT / "mesh_dance_test.gif"

W, H = 540, 960
FPS = 30
BPM = 189.9
HALF_SEC = 60.0 / BPM * 2.0
HALF_FRAMES = HALF_SEC * FPS


def load_poses():
    poses = {}
    bottoms = {}
    tops = {}

    for i, path in enumerate(POSE_PATHS, start=1):
        if not path.exists():
            raise FileNotFoundError(path)

        image = Image.open(path).convert("RGBA").resize(
            (W, H), Image.Resampling.LANCZOS
        )
        arr = np.array(image)
        poses[i] = arr

        alpha = arr[:, :, 3]
        ys, _ = np.where(alpha > 10)
        bottoms[i] = int(ys.max())
        tops[i] = int(ys.min())

    # Correct only small baseline differences.
    # Do not per-pose scale and do not bbox-center horizontally.
    foot_y = int(round(statistics.median(bottoms.values())))
    top_y = int(round(statistics.median(tops.values())))

    aligned = {}
    for i, arr in poses.items():
        dy = foot_y - bottoms[i]
        matrix = np.float32([[1, 0, 0], [0, 1, dy]])
        aligned[i] = cv2.warpAffine(
            arr,
            matrix,
            (W, H),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

    return aligned, foot_y, top_y


POSES, FOOT_Y, TOP_Y = load_poses()
YY, XX = np.indices((H, W), dtype=np.float32)


def warp_rgba(arr, sway=0.0, sy=1.0, bend=0.0):
    """Foot-anchored row warp. Upper rows move more; foot baseline stays stable."""
    denom = max(1, FOOT_Y - TOP_Y)
    t = np.clip((FOOT_Y - YY) / denom, 0, 1)

    smooth = t * t * (3 - 2 * t)
    curve = np.sin(np.pi * t)

    dx = sway * smooth + bend * curve
    map_x = XX - dx

    # Scale vertically around the foot baseline.
    map_y = FOOT_Y + (YY - FOOT_Y) / max(0.90, sy)

    return cv2.remap(
        arr,
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )


def bump(p):
    return math.sin(math.pi * max(0.0, min(1.0, p)))


def gauss(p, center, width):
    return math.exp(-0.5 * ((p - center) / width) ** 2)


def motion_params(preset, p, strength=1.0):
    # Moderate / v1-ish amplitudes.
    if preset == "shakeR":
        decay = 1 - 0.45 * p
        s = math.sin(4 * math.pi * p)
        return dict(
            sway=8 * strength * s * decay,
            sy=1.0,
            bend=2 * strength * s,
        )

    if preset == "shakeL":
        decay = 1 - 0.45 * p
        s = math.sin(4 * math.pi * p)
        return dict(
            sway=-8 * strength * s * decay,
            sy=1.0,
            bend=-2 * strength * s,
        )

    if preset == "clapR":
        hit = gauss(p, 0.22, 0.16)
        rebound = gauss(p, 0.48, 0.13)
        return dict(
            sway=2.5 * strength * (hit - rebound),
            sy=1 - 0.024 * strength * hit + 0.012 * strength * rebound,
            bend=1.5 * strength * hit,
        )

    if preset == "clapL":
        hit = gauss(p, 0.22, 0.16)
        rebound = gauss(p, 0.48, 0.13)
        return dict(
            sway=-2.5 * strength * (hit - rebound),
            sy=1 - 0.024 * strength * hit + 0.012 * strength * rebound,
            bend=-1.5 * strength * hit,
        )

    if preset == "cross":
        return dict(
            sway=-5 * strength * math.sin(2 * math.pi * p),
            sy=1 + 0.008 * math.sin(2 * math.pi * p),
            bend=-4 * strength * bump(p),
        )

    if preset == "pulse":
        return dict(
            sway=0,
            sy=1 + 0.015 * strength * math.sin(2 * math.pi * p),
            bend=0,
        )

    if preset == "breathe":
        # If this is obvious to the eye, it is too strong.
        return dict(
            sway=1.0 * math.sin(2 * math.pi * p),
            sy=1 + 0.009 * math.sin(2 * math.pi * p),
            bend=0,
        )

    if preset == "pop":
        hit = gauss(p, 0.25, 0.18)
        rebound = gauss(p, 0.55, 0.16)
        return dict(
            sway=0,
            sy=1 - 0.015 * strength * hit + 0.010 * strength * rebound,
            bend=0,
        )

    if preset == "leanR":
        q = bump(p)
        return dict(
            sway=8 * strength * q,
            sy=1 + 0.004 * math.sin(2 * math.pi * p),
            bend=5 * strength * q,
        )

    if preset == "leanL":
        q = bump(p)
        return dict(
            sway=-8 * strength * q,
            sy=1 + 0.004 * math.sin(2 * math.pi * p),
            bend=-5 * strength * q,
        )

    if preset == "reachR":
        s = math.sin(2 * math.pi * p)
        return dict(
            sway=10 * strength * s,
            sy=1 + 0.006 * s,
            bend=5 * strength * s,
        )

    if preset == "reachL":
        s = math.sin(2 * math.pi * p)
        return dict(
            sway=-10 * strength * s,
            sy=1 + 0.006 * s,
            bend=-5 * strength * s,
        )

    if preset == "final":
        s = math.sin(2 * math.pi * p)
        return dict(
            sway=3 * strength * s,
            sy=1 + 0.010 * s,
            bend=2 * strength * s,
        )

    if preset == "waveR":
        s = math.sin(2 * math.pi * p)
        return dict(
            sway=12 * strength * s,
            sy=1 + 0.006 * s,
            bend=7 * strength * s,
        )

    if preset == "waveL":
        s = math.sin(2 * math.pi * p)
        return dict(
            sway=-12 * strength * s,
            sy=1 + 0.006 * s,
            bend=-7 * strength * s,
        )

    return dict(sway=0, sy=1.0, bend=0)


# 13 supplied poses followed by ~2.5 s alternating raised-arm finish.
SEQUENCE = [
    (1,  "shakeR", 1.0),
    (2,  "clapR",  1.0),
    (3,  "shakeL", 1.0),
    (4,  "clapL",  1.0),
    (5,  "cross",   1.0),
    (6,  "pulse",   1.0),
    (12, "breathe", 1.0),
    (13, "pop",     1.0),
    (8,  "leanR",   1.0),
    (9,  "reachR",  1.0),
    (10, "leanL",   1.0),
    (11, "reachL",  1.0),
    (7,  "final",   1.0),
    (9,  "waveR",   1.0),
    (11, "waveL",   1.0),
    (9,  "waveR",   1.0),
    (11, "waveL",   1.0),
]

# Accumulated timing: do not round the per-beat step itself.
boundaries = [round(k * HALF_FRAMES) for k in range(len(SEQUENCE) + 1)]
counts = [
    boundaries[i + 1] - boundaries[i]
    for i in range(len(SEQUENCE))
]


def rgba_on_white(arr):
    a = arr[:, :, 3:4].astype(np.float32) / 255.0
    return (
        arr[:, :, :3].astype(np.float32) * a
        + 255.0 * (1.0 - a)
    ).astype(np.uint8)


frames = []
for (pose_idx, preset, strength), frame_count in zip(SEQUENCE, counts):
    for j in range(frame_count):
        phase = j / max(1, frame_count - 1)
        warped = warp_rgba(
            POSES[pose_idx],
            **motion_params(preset, phase, strength),
        )
        frames.append(rgba_on_white(warped))


tmp = ROOT / "_mesh_dance_frames"
tmp.mkdir(exist_ok=True)

try:
    for i, frame in enumerate(frames):
        cv2.imwrite(
            str(tmp / f"{i:04d}.png"),
            cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
        )

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(tmp / "%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-movflags", "+faststart",
        str(MP4_PATH),
    ], check=True)

finally:
    for path in tmp.glob("*.png"):
        path.unlink()
    if tmp.exists():
        tmp.rmdir()


# Lightweight 15 fps GIF review copy.
gif_frames = [
    Image.fromarray(frame).resize((360, 640), Image.Resampling.LANCZOS)
    for frame in frames[::2]
]
palette = gif_frames[0].quantize(
    colors=255,
    method=Image.Quantize.MEDIANCUT,
)
quantized = [
    frame.quantize(
        colors=255,
        palette=palette,
        dither=Image.Dither.NONE,
    )
    for frame in gif_frames
]
quantized[0].save(
    GIF_PATH,
    save_all=True,
    append_images=quantized[1:],
    duration=round(1000 / 15),
    loop=0,
    disposal=2,
    optimize=False,
)

print(
    f"{len(frames)} frames / {len(frames) / FPS:.2f}s / "
    f"half-beat {HALF_SEC:.3f}s"
)
print(MP4_PATH)
print(GIF_PATH)
