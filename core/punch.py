"""Shared barrage renderer factored from the supplied final GPT prototype.

Timing, growth, late fade, backward shutter, camera crop and rasterization are
preserved. Character/artwork coordinates live in presets, never engine branches.
"""
from __future__ import annotations
import math
import numpy as np
from PIL import Image
from .effects import build_speedline_overlay, pulse_strength

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def ease_in(t: float, power: float = 1.65) -> float:
    return clamp01(t) ** power

def ease_out(t: float) -> float:
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def render_frames(body: Image.Image, fist_srcs: list[Image.Image],
                  speedline_src: Image.Image | None, cfg: dict) -> list[Image.Image]:
    """Render RGB frames without writing files or changing the supplied profile.

    ``fists`` entries specify source-canvas ``centroid`` and a ``side`` key in
    ``shoulders``. Artwork is cropped by alpha; coordinates are never inferred.
    """
    w, h = map(int, cfg.get("canvas", [768, 432]))
    fps = int(cfg.get("fps", 30))
    if min(w, h, fps) <= 0:
        raise ValueError("Canvas dimensions and fps must be positive")
    if not fist_srcs or len(fist_srcs) != len(cfg.get("fists", [])):
        raise ValueError("Each fist asset needs one profile metadata entry")
    for entry in cfg["fists"]:
        if entry.get("side") not in cfg.get("shoulders", {}):
            raise ValueError("Fist side must name a measured shoulder")
        if len(entry.get("centroid", [])) != 2:
            raise ValueError("Fist centroid must contain x and y")
    punch = cfg.get("punch", {})
    if int(punch.get("count", 10)) <= 0:
        raise ValueError("Punch count must be positive")
    if float(punch.get("step_frames", 3)) <= 0 or float(punch.get("duration_frames", 6.5)) <= 0:
        raise ValueError("Punch step and duration must be positive")
    blur = cfg.get("motion_blur", {})
    if blur.get("type", "temporal_substeps") != "temporal_substeps":
        raise ValueError("Punch motion blur uses temporal_substeps")
    if int(blur.get("substeps", 4)) < 1:
        raise ValueError("Motion blur needs at least one substep")
    shutter = float(blur.get("shutter", .70))
    if shutter < 0:
        raise ValueError("Shutter cannot be negative")
    if float(cfg.get("camera", {}).get("zoom_end", .78)) <= 0:
        raise ValueError("Camera crop scale must be positive")
    if cfg.get("camera", {}).get("ease", "cubic_out") not in ("cubic_out", "linear"):
        raise ValueError("Camera ease must be cubic_out or linear")
    effect = cfg.get("speedline", {})
    effect_order = effect.get("z_order", "topmost")
    if effect_order not in ("topmost", "background"):
        raise ValueError("Speedline z_order must be topmost or background")
    if effect.get("full_screen_flash", False):
        raise ValueError("A line pulse does not apply a full-screen flash")
    enabled = effect.get("enabled", True)
    if enabled and speedline_src is None:
        raise ValueError("Enabled speedlines require a supplied image")
    speedline_rgba = build_speedline_overlay(speedline_src, (w, h)) if enabled else None
    body = body.convert("RGBA")
    fist_srcs = [im.convert("RGBA") for im in fist_srcs]

    def add_lines(canvas, frame_idx):
        strength = pulse_strength(frame_idx, fps, effect) if enabled else 0.0
        if strength > 0.0:
            arr = speedline_rgba.copy()
            arr[:, :, 3] = np.clip(arr[:, :, 3].astype(np.float32) * strength, 0, 255).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(arr, "RGBA"))
        return canvas

    punch_cfg = cfg["punch"]
    n_punch = int(punch_cfg.get("count", 10))
    step = float(punch_cfg.get("step_frames", 3.0))
    duration = float(punch_cfg.get("duration_frames", 6.5))
    perspective_scale = float(punch_cfg.get("perspective_scale", 8.9))
    end_overshoot = float(punch_cfg.get("end_overshoot", 1.85))

    substeps = int(cfg.get("motion_blur", {}).get("substeps", 4))

    shoulder = cfg["shoulders"]
    shoulder = {k: tuple(v) for k, v in shoulder.items()}

    # Artwork-specific endpoints and alternating roles belong to the profile.
    fist_meta = [(item["side"], item["centroid"]) for item in cfg["fists"]]

    fists = []
    for im, (side, centroid) in zip(fist_srcs, fist_meta):
        bb = im.getbbox()
        if bb is None:
            raise ValueError("A fist asset is fully transparent")
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

        if effect_order == "background":
            canvas = add_lines(canvas, frame_idx)

        # Background/body first.
        bx = brace_x * math.sin(ft * float(body_cfg.get("horizontal_frequency", 2.4)))
        by = brace_y * math.cos(ft * float(body_cfg.get("vertical_frequency", 2.1)))
        quantize_position = round if body_cfg.get("round_position", True) else int
        canvas.alpha_composite(body, (int(quantize_position(bx)), int(quantize_position(by))))

        # Fists and normal overlays next.
        for k in range(n_punch):
            t0 = k * step
            t = (ft - t0) / duration
            if not (0.0 <= t <= 1.0):
                continue

            crop, side, end = fists[k % len(fists)]
            p = ease_in(t, float(punch_cfg.get("ease_power", 1.65)))

            sx, sy = shoulder[side]
            ex = w / 2 + (end[0] - w / 2) * end_overshoot
            ey = h / 2 + (end[1] - h / 2) * end_overshoot

            cx = lerp(sx, ex, p)
            cy = lerp(sy, ey, p)

            scale = float(punch_cfg.get("initial_scale", 0.48)) + perspective_scale * p
            fw = max(2, int(crop.width * scale))
            fh = max(2, int(crop.height * scale))
            fist = crop.resize((fw, fh), Image.Resampling.BICUBIC)

            # Fade only after the fist has passed the lens.
            fade_start = punch_cfg.get("fade_start", 0.88)
            if fade_start is not None and t > fade_start:
                alpha_scale = max(0.0, 1.0 - (t - fade_start) / (1.0 - fade_start))
                alpha = fist.getchannel("A").point(
                    lambda v: int(v * alpha_scale)
                )
                fist.putalpha(alpha)

            canvas.alpha_composite(
                fist,
                (int(cx - fw / 2), int(cy - fh / 2)),
            )

        # Preserve source ordering: the line pulse follows every action part.
        if effect_order == "topmost":
            canvas = add_lines(canvas, frame_idx)

        # Camera push-in happens after layer compositing, preserving z-order.
        camera_progress = ft / max(1, total - 1)
        camera_ease = clamp01 if camera_cfg.get("ease", "cubic_out") == "linear" else ease_out
        z = lerp(1.0, zoom_end, camera_ease(camera_progress))
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
                -shutter + (s / (substeps - 1)) * shutter
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

    return frames
