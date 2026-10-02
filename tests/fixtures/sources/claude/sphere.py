"""sphere.py — wrap an equirectangular strip onto a rotating globe.

A flat strip is sampled as (longitude, latitude). For every screen pixel inside the disc:
    Z = sqrt(1 - X^2 - Y^2)          how far toward the viewer that point sits
    lat = asin(Y)                    vertical position maps straight to latitude
    lon = atan2(X, Z) + spin         the horizontal squeeze at the limb comes free from atan2
Spin is just an offset added to lon, so ONE strip rotates forever with no second drawing.
Shading is a lambert term against a light direction, so the terminator moves if you move the light.
"""
import numpy as np
from PIL import Image


def equirect_from_robinson(img):
    """Undo a Robinson-style projection well enough to test: every parallel is a straight line
    that has simply been shortened toward the poles, so stretch each row back to full width."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = a.shape
    body = a.sum(2) < 720
    out = np.zeros_like(a)
    for y in range(h):
        cols = np.nonzero(body[y])[0]
        if len(cols) < 4:
            out[y] = a[y]
            continue
        x0, x1 = cols.min(), cols.max()
        src = np.linspace(x0, x1, w)
        for c in range(3):
            out[y, :, c] = np.interp(src, np.arange(w), a[y, :, c])
    return Image.fromarray(out.astype(np.uint8))


def _sample(tex_rgba, lon, lat):
    """Sample an equirectangular strip at (lon, lat). Longitude wraps, so one strip spins forever."""
    t = tex_rgba
    th, tw = t.shape[:2]
    u = ((lon / (2 * np.pi)) % 1.0) * (tw - 1)
    v = np.clip((0.5 - lat / np.pi) * (th - 1), 0, th - 1)
    return t[v.astype(np.int32), u.astype(np.int32)]


def render_globe(tex, size=480, spin=0.0, light=(-0.6, 0.35, 0.72),
                 ambient=0.22, bg=(10, 12, 20), rim=0.0,
                 clouds=None, cloud_spin=0.0, cloud_opacity=1.0):
    t = np.asarray(tex.convert("RGB")).astype(np.float32)
    th, tw, _ = t.shape
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    X = (xx - size / 2) / (size / 2 * 0.94)
    Y = -(yy - size / 2) / (size / 2 * 0.94)
    r2 = X * X + Y * Y
    disc = r2 <= 1.0
    Z = np.sqrt(np.clip(1 - r2, 0, 1))

    lat = np.arcsin(np.clip(Y, -1, 1))
    lon = np.arctan2(X, np.where(Z == 0, 1e-6, Z)) + spin
    u = ((lon / (2 * np.pi)) % 1.0) * (tw - 1)
    v = (0.5 - lat / np.pi) * (th - 1)
    ui, vi = u.astype(np.int32), np.clip(v, 0, th - 1).astype(np.int32)
    col = t[vi, ui]

    if clouds is not None:
        c = np.asarray(clouds.convert("RGBA")).astype(np.float32)
        # clouds ride on their own longitude offset - a slightly faster drift is what sells depth
        cs = _sample(c, np.arctan2(X, np.where(Z == 0, 1e-6, Z)) + spin + cloud_spin, lat)
        ca = (cs[..., 3:4] / 255.0) * cloud_opacity
        col = col * (1 - ca) + cs[..., :3] * ca

    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    lam = np.clip(X * L[0] + Y * L[1] + Z * L[2], 0, 1)
    shade = (ambient + (1 - ambient) * lam)[..., None]
    out = col * shade
    if rim > 0:                                    # thin atmosphere at the limb
        edge = np.clip((r2 - 0.86) / 0.14, 0, 1)[..., None]
        out = out + edge * rim * np.array([90, 150, 255], np.float32)
    out = np.where(disc[..., None], out, np.array(bg, np.float32))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def spin_gif(tex, path, frames=48, size=420, ms=70, **kw):
    ims = [render_globe(tex, size=size, spin=2 * np.pi * i / frames, **kw) for i in range(frames)]
    pal = ims[0].quantize(colors=255)
    q = [im.quantize(colors=255, palette=pal, dither=Image.NONE) for im in ims]
    q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, disposal=2)
    return path
