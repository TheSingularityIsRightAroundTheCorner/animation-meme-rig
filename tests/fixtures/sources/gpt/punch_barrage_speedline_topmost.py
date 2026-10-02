#!/usr/bin/env python3
"""
Punch barrage prototype — portable Astra/Codex handoff version.

Key production rules
--------------------
1. Use the supplied body PNG + four fist PNGs as-is. Do not redraw assets.
2. GPT body/shoulders stay almost fixed and feel heavy/rooted.
3. Punches overlap so there is no empty beat.
4. Motion blur uses temporal substeps, not GaussianBlur.
5. Camera pushes in through the barrage.
6. IMPORTANT: speed-line layer is composited LAST / TOPMOST.
   It must sit above body, fists, glow, and other overlays.
7. Speed lines pulse on a 0.5 s interval.

Run example:
    python punch_barrage_speedline_topmost.py \
      --body "18 punch gpt body.png" \
      --fists "18 punch gpt fist 1.png" "18 punch gpt fist 3.png" \
              "18 punch gpt fist 2.png" "18 punch gpt fist 4.png" \
      --speedline "speed line.png" \
      --params punch_barrage_params.json \
      --out punch_barrage_topmost.mp4

Requires:
    pillow, numpy, ffmpeg
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def ease_in(t: float, power: float = 1.65) -> float:
    return clamp01(t) ** power


def ease_out(t: float) -> float:
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def load_params(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_speedline_overlay(src: Image.Image, size: tuple[int, int]) -> np.ndarray:
    """Return a reusable RGBA array whose black lines keep transparency."""
    w, h = size
    im = src.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
    rgba = np.asarray(im)

    rgb = rgba[:, :, :3].astype(np.float32)
    src_alpha = rgba[:, :, 3].astype(np.float32) / 255.0

    # White -> transparent, black line -> opaque.
    darkness = 255.0 - rgb.mean(axis=2)
    alpha = np.clip(darkness * src_alpha * 1.35, 0, 255).astype(np.uint8)

    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, :3] = 0
    out[:, :, 3] = alpha
    return out


def pulse_strength(frame_idx: int, fps: int, speedline_cfg: dict) -> float:
    interval_sec = float(speedline_cfg.get("pulse_interval_sec", 0.5))
    period = max(1, round(interval_sec * fps))

    envelope = speedline_cfg.get(
        "visible_envelope_frames",
        [0.25, 0.75, 1.0, 0.55, 0.18],
    )

    phase = frame_idx % period
    if phase >= len(envelope):
        return 0.0
    return float(envelope[phase])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True, type=Path)
    ap.add_argument("--fists", required=True, type=Path, nargs=4)
    ap.add_argument("--speedline", required=True, type=Path)
    ap.add_argument("--params", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    cfg = load_params(args.params)

    w, h = map(int, cfg.get("canvas", [768, 432]))
    fps = int(cfg.get("fps", 30))

    body = Image.open(args.body).convert("RGBA")
    fist_srcs = [Image.open(p).convert("RGBA") for p in args.fists]
    speedline_src = Image.open(args.speedline).convert("RGBA")
    speedline_rgba = build_speedline_overlay(speedline_src, (w, h))

    punch_cfg = cfg["punch"]
    n_punch = int(punch_cfg.get("count", 10))
    step = float(punch_cfg.get("step_frames", 3.0))
    duration = float(punch_cfg.get("duration_frames", 6.5))
    perspective_scale = float(punch_cfg.get("perspective_scale", 8.9))
    end_overshoot = float(punch_cfg.get("end_overshoot", 1.85))

    substeps = int(cfg.get("motion_blur", {}).get("substeps", 4))

    shoulder = cfg.get("shoulders", {"L": [300, 190], "R": [455, 190]})
    shoulder = {k: tuple(v) for k, v in shoulder.items()}

    # Order matches the earlier production prototype:
    # fist 1, fist 3, fist 2, fist 4.
    fist_meta = [
        ("L", (42, 48)),
        ("R", (250, 149)),
        ("L", (37, 141)),
        ("R", (268, 38)),
    ]

    fists = []
    for im, (side, centroid) in zip(fist_srcs, fist_meta):
        bb = im.getbbox()
        crop = im.crop(bb)
        end = (
            centroid[0] / im.width * w,
            centroid[1] / im.height * h,
        )
        fists.append((crop, side, end))

    total = int(step * (n_punch - 1) + duration) + 6

    body_cfg = cfg.get("body", {})
    brace_x = float(body_cfg.get("max_horizontal_brace_px", 0.7))
    brace_y = float(body_cfg.get("max_vertical_brace_px", 1.4))

    camera_cfg = cfg.get("camera", {})
    zoom_end = float(camera_cfg.get("zoom_end", 0.78))

    speedline_cfg = cfg.get("speedline", {})

    def render_fractional(ft: float, frame_idx: int) -> Image.Image:
        canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))

        # Background/body first.
        bx = brace_x * math.sin(ft * 2.4)
        by = brace_y * math.cos(ft * 2.1)
        canvas.alpha_composite(body, (int(round(bx)), int(round(by))))

        # Fists and normal overlays next.
        for k in range(n_punch):
            t0 = k * step
            t = (ft - t0) / duration
            if not (0.0 <= t <= 1.0):
                continue

            crop, side, end = fists[k % len(fists)]
            p = ease_in(t)

            sx, sy = shoulder[side]
            ex = w / 2 + (end[0] - w / 2) * end_overshoot
            ey = h / 2 + (end[1] - h / 2) * end_overshoot

            cx = lerp(sx, ex, p)
            cy = lerp(sy, ey, p)

            scale = 0.48 + perspective_scale * p
            fw = max(2, int(crop.width * scale))
            fh = max(2, int(crop.height * scale))
            fist = crop.resize((fw, fh), Image.Resampling.BICUBIC)

            # Fade only after the fist has passed the lens.
            if t > 0.88:
                alpha_scale = max(0.0, 1.0 - (t - 0.88) / 0.12)
                alpha = fist.getchannel("A").point(
                    lambda v: int(v * alpha_scale)
                )
                fist.putalpha(alpha)

            canvas.alpha_composite(
                fist,
                (int(cx - fw / 2), int(cy - fh / 2)),
            )

        # Other optional glow/flash overlays would go HERE.
        # --------------------------------------------------
        # IMPORTANT:
        # SPEED LINES ARE COMPOSITED LAST / TOPMOST.
        # Nothing should be alpha_composited after this block
        # unless a shot explicitly overrides the canonical rule.
        # --------------------------------------------------
        strength = pulse_strength(frame_idx, fps, speedline_cfg)
        if strength > 0.0:
            arr = speedline_rgba.copy()
            arr[:, :, 3] = np.clip(
                arr[:, :, 3].astype(np.float32) * strength,
                0,
                255,
            ).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(arr, "RGBA"))

        # Camera push-in happens after layer compositing, preserving z-order.
        z = lerp(1.0, zoom_end, ease_out(ft / max(1, total - 1)))
        cw, ch = int(w * z), int(h * z)
        x0, y0 = (w - cw) // 2, (h - ch) // 2

        return (
            canvas
            .crop((x0, y0, x0 + cw, y0 + ch))
            .resize((w, h), Image.Resampling.LANCZOS)
            .convert("RGB")
        )

    frames: list[Image.Image] = []

    for fi in range(total):
        samples = []

        for s in range(substeps):
            frac = (
                -0.70 + (s / (substeps - 1)) * 0.70
                if substeps > 1
                else 0.0
            )

            # Pulse timing is locked to final frame index so the line layer
            # itself stays crisp instead of smearing within substeps.
            samples.append(
                np.asarray(
                    render_fractional(fi + frac, fi),
                    dtype=np.float32,
                )
            )

        avg = np.mean(samples, axis=0).clip(0, 255).astype(np.uint8)
        frames.append(Image.fromarray(avg, "RGB"))

    suffix = args.out.suffix.lower()

    if suffix == ".gif":
        sample_idxs = np.linspace(
            0,
            len(frames) - 1,
            min(8, len(frames)),
            dtype=int,
        )

        strip = Image.new("RGB", (w, h * len(sample_idxs)), "white")
        for j, idx in enumerate(sample_idxs):
            strip.paste(frames[idx], (0, j * h))

        palette = strip.quantize(
            colors=255,
            method=Image.Quantize.MEDIANCUT,
        )

        q = [
            f.quantize(
                colors=255,
                palette=palette,
                dither=Image.Dither.NONE,
            )
            for f in frames
        ]

        q[0].save(
            args.out,
            save_all=True,
            append_images=q[1:],
            duration=round(1000 / fps),
            loop=0,
            disposal=2,
            optimize=False,
        )

    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            for i, frame in enumerate(frames):
                frame.save(tmp / f"{i:04d}.png")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-framerate",
                    str(fps),
                    "-i",
                    str(tmp / "%04d.png"),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "18",
                    "-movflags",
                    "+faststart",
                    str(args.out),
                ],
                check=True,
            )

    print(
        f"wrote {args.out} | "
        f"{len(frames)} frames | "
        f"{len(frames) / fps:.2f}s"
    )


if __name__ == "__main__":
    main()
