"""Fractional beat scheduling inherited from mesh_dance_test.py.

Round absolute boundaries only. Rounding each interval accumulates timing drift.
"""
from __future__ import annotations
import math


def boundaries(count: int, bpm: float, fps: float, beats_per_pose: float = 2.0,
               offset_frames: float = 0.0) -> list[int]:
    """Return count+1 absolute frame boundaries, including an optional offset."""
    if int(count) != count or count < 0:
        raise ValueError("Pose count must be a nonnegative integer")
    if any(not math.isfinite(value) or value <= 0 for value in (bpm, fps, beats_per_pose)):
        raise ValueError("bpm, fps and beats_per_pose must be finite and positive")
    if not math.isfinite(offset_frames):
        raise ValueError("Offset must be finite")
    step = 60.0 / bpm * beats_per_pose * fps
    return [round(offset_frames + k * step) for k in range(count + 1)]


def frame_counts(count: int, bpm: float, fps: float,
                 beats_per_pose: float = 2.0, offset_frames: float = 0.0) -> list[int]:
    """Return interval lengths while preserving fractional accumulated timing."""
    positions = boundaries(count, bpm, fps, beats_per_pose, offset_frames)
    return [b - a for a, b in zip(positions, positions[1:])]
