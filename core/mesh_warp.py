"""Foot-anchored row warp and exact secondary-motion curves from GPT source.

No artwork loads or renders on import. Poses keep a common canvas; horizontal
composition and drawn relative sizes remain intact.
"""
from __future__ import annotations
import math
import statistics
import numpy as np
import cv2
from PIL import Image
from .beat_grid import frame_counts


def align_poses(images, size, *, preserve_baselines=()):
    """Return RGBA arrays, median foot and top y without per-pose scaling.

    All source images must share a canvas. ``preserve_baselines`` lists one-based
    pose numbers whose original y placement is retained, e.g. an authored jump.
    Other poses use the source prototype's median baseline translation.
    """
    if not images:
        raise ValueError("At least one supplied pose is required")
    if len({im.size for im in images}) != 1:
        raise ValueError("Pose assets must share one source canvas")
    if len(size) != 2 or min(size) <= 0:
        raise ValueError("Output size must contain two positive dimensions")
    poses, bottoms, tops = [], [], []
    for image in images:
        arr = np.array(image.convert("RGBA").resize(tuple(size), Image.Resampling.LANCZOS))
        ys, _ = np.where(arr[:, :, 3] > 10)
        if len(ys) == 0:
            raise ValueError("Pose asset is fully transparent")
        poses.append(arr)
        bottoms.append(int(ys.max()))
        tops.append(int(ys.min()))
    foot_y = int(round(statistics.median(bottoms)))
    top_y = int(round(statistics.median(tops)))
    preserve = set(preserve_baselines)
    aligned = []
    for number, (arr, bottom) in enumerate(zip(poses, bottoms), 1):
        dy = 0 if number in preserve else foot_y - bottom
        matrix = np.float32([[1, 0, 0], [0, 1, dy]])
        aligned.append(cv2.warpAffine(arr, matrix, tuple(size), flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)))
    return aligned, foot_y, top_y


def warp_rgba(arr, foot_y, top_y, sway=0.0, sy=1.0, bend=0.0):
    """Foot-anchored row warp. Upper rows move more; foot baseline stays stable."""
    yy, xx = np.indices(arr.shape[:2], dtype=np.float32)
    denom = max(1, foot_y - top_y)
    t = np.clip((foot_y - yy) / denom, 0, 1)

    smooth = t * t * (3 - 2 * t)
    curve = np.sin(np.pi * t)

    dx = sway * smooth + bend * curve
    map_x = xx - dx

    # Scale vertically around the foot baseline.
    map_y = foot_y + (yy - foot_y) / max(0.90, sy)

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

def rgba_on_white(arr):
    a = arr[:, :, 3:4].astype(np.float32) / 255.0
    return (
        arr[:, :, :3].astype(np.float32) * a
        + 255.0 * (1.0 - a)
    ).astype(np.uint8)

def render_sequence(images, sequence, *, size=(540, 960), bpm=189.9, fps=30,
                    beats_per_pose=2.0, preserve_baselines=(), offset_ms=0.0):
    """Hard-cut one-based poses on an absolute beat grid; return RGB frames.

    Sequence entries are ``[pose_number, motion_name, strength]``. The image's
    original horizontal composition is retained. There is no crossfade.
    ``offset_ms`` locates the first beat relative to output time zero. Positive
    offsets hold the initial pose; negative offsets crop already elapsed motion.
    """
    if isinstance(offset_ms, bool) or not isinstance(offset_ms, (int, float)) or not math.isfinite(offset_ms):
        raise ValueError("offset_ms must be a finite number")
    poses, foot_y, top_y = align_poses(images, size, preserve_baselines=preserve_baselines)
    offset_frames = offset_ms * fps / 1000.0
    counts = frame_counts(len(sequence), bpm, fps, beats_per_pose, offset_frames)
    if any(count < 1 for count in counts):
        raise ValueError("Beat intervals must last at least one output frame")
    position = round(offset_frames)
    if not counts or position + sum(counts) <= 0:
        raise ValueError("offset_ms leaves no output frames")
    frames = []
    for (pose_number, preset, strength), count in zip(sequence, counts):
        if not 1 <= pose_number <= len(poses):
            raise ValueError("Sequence references an unavailable pose")
        for j in range(max(0, -position), count):
            phase = j / max(1, count - 1)
            warped = warp_rgba(poses[pose_number - 1], foot_y, top_y,
                               **motion_params(preset, phase, strength))
            frames.append(Image.fromarray(rgba_on_white(warped), "RGB"))
        position += count
    return [frames[0].copy() for _ in range(max(0, round(offset_frames)))] + frames
