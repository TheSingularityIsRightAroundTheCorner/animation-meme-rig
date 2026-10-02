"""Inherited line extraction and pulse; explicit alpha-aware layer composition."""
import re
import numpy as np
from PIL import Image

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
    if not speedline_cfg.get('enabled', True):
        return 0.0
    if fps <= 0 or speedline_cfg.get('pulse_interval_sec', .5) <= 0:
        raise ValueError('pulse interval and fps must be positive')
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


def composite_effect(canvas, src, strength=1, enabled=True, mode='normal'):
    if canvas.size != src.size:
        raise ValueError('effect canvas dimensions must match')
    if not 0 <= strength <= 1:
        raise ValueError('effect strength must lie in [0,1]')
    result = canvas.convert('RGBA').copy()
    if not enabled or strength == 0:
        return result
    source = src.convert('RGBA').copy()
    source.putalpha(source.getchannel('A').point(lambda v: int(v * strength)))
    if mode == 'normal':
        result.alpha_composite(source)
        return result
    if mode not in ('screen', 'multiply', 'overlay'):
        raise ValueError(f'unsupported blend: {mode}')
    # W3C-style source-over blend on straight-alpha color, preserving transparent
    # input semantics rather than flattening alpha-only line art to black.
    base = np.asarray(result, dtype=np.float64) / 255
    top = np.asarray(source, dtype=np.float64) / 255
    cb, cs = base[..., :3], top[..., :3]
    ab, a = base[..., 3:4], top[..., 3:4]
    if mode == 'screen':
        blend = 1 - (1-cb)*(1-cs)
    elif mode == 'multiply':
        blend = cb * cs
    else:
        blend = np.where(cb <= .5, 2*cb*cs, 1-2*(1-cb)*(1-cs))
    alpha = a + ab*(1-a)
    premultiplied = a*(1-ab)*cs + a*ab*blend + (1-a)*ab*cb
    color = np.divide(premultiplied, alpha, out=np.zeros_like(premultiplied), where=alpha > 0)
    return Image.fromarray(np.round(np.concatenate((color, alpha), axis=2)*255).clip(0,255).astype(np.uint8))


def fill_lens_mask(mask, split_x):
    a = np.asarray(mask.convert('L'))
    if not 0 < split_x < a.shape[1]:
        raise ValueError('split_x must lie between the two lens regions')
    filled = np.zeros_like(a)
    for x0, x1 in ((0, split_x), (split_x, a.shape[1])):
        for y in range(a.shape[0]):
            columns = np.flatnonzero(a[y, x0:x1] > 0)
            if len(columns):
                filled[y, x0+columns.min():x0+columns.max()+1] = 255
    return Image.fromarray(filled)


def scaled_line_width(width, zoom):
    if width <= 0 or zoom <= 0:
        raise ValueError('line width and zoom must be positive')
    return width / zoom


def layer_order(names):
    """Optional filename role ordering; explicit scene z always takes priority."""
    def key(name):
        stem = name.rsplit('.', 1)[0]
        stem = re.sub(r'_(scr|ov|mul)$', '', stem)
        numbered = re.search(r'_p(\d+)$', stem)
        if stem.endswith('_base'): rank, number = 0, 0
        elif numbered: rank, number = 1, int(numbered[1])
        elif stem.endswith('_fx'): rank, number = 2, 0
        elif stem.endswith(('_in','_out')): rank, number = 3, 0
        elif stem.endswith('_over'): rank, number = 4, 0
        else: rank, number = 1, 0
        return rank, number, name
    return sorted(names, key=key)


def effect_pulse(time, interval=.5, attack=.03, hold=.03, release=.1, strength=1):
    """Optional continuous envelope; archived punch keeps its exact frame table."""
    if interval <= 0 or min(attack, hold, release, strength) < 0:
        raise ValueError('invalid pulse envelope')
    phase = time % interval
    if phase < attack:
        return strength * phase / attack
    phase -= attack
    if phase < hold:
        return strength
    phase -= hold
    return strength * max(0, 1-phase/release) if release else 0
