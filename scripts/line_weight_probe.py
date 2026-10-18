#!/usr/bin/env python3
"""Line-weight probe: naive downscale vs. stroke-width compensation on one flattened part.

Experiment behind references/roadmap-musical-action.md (P3). Renders one RGBA part at
several screen scales in three columns (naive, plain dilation, gap-protected dilation)
and writes a magnified comparison sheet. It is not a scene mode.
"""
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
COLUMNS = ('naive', 'plain dilate', 'gap-protected')


def disk(radius):
    r = max(0, int(np.ceil(radius)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def split_ink(rgba, dark_luma=70, mass_radius=14):
    """Split dark painted pixels into strokes and masses (hair, large black shadow).

    A mass survives an opening of radius mass_radius; a stroke does not.
    Returns uint8 masks (line, mass, inside)."""
    inside = (rgba[..., 3] > 127).astype(np.uint8)
    luma = rgba[..., :3].astype(np.float32) @ LUMA
    dark = ((luma < dark_luma) & (inside > 0)).astype(np.uint8)
    mass = cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, disk(mass_radius)), disk(2))
    return dark & (1 - mass), mass, inside


def stroke_width(line):
    """Median stroke width in source px, read from ridge values of the stroke distance field."""
    dist = cv2.distanceTransform(line, cv2.DIST_L2, 5)
    ridge = (dist == cv2.dilate(dist, np.ones((3, 3), np.uint8))) & (line > 0) & (dist > 1)
    if not ridge.any():
        raise ValueError('no strokes found; adjust --dark-luma')
    return 2 * float(np.median(dist[ridge]))


def thicken(line, inside, grow, kappa=None):
    """Grow strokes by `grow` source px per side without leaving the silhouette.

    With kappa, gaps that a closing of radius `grow` would fill receive only
    kappa * grow, so close strokes such as lashes and eyelids stay apart."""
    if grow <= 0:
        return line.copy()
    to_line = cv2.distanceTransform((1 - line).astype(np.uint8), cv2.DIST_L2, 5)
    limit = np.full(line.shape, grow, np.float32)
    if kappa is not None:
        clog = cv2.morphologyEx(line, cv2.MORPH_CLOSE, disk(grow)) & (1 - line)
        limit[clog > 0] = kappa * grow
    return ((line > 0) | ((inside > 0) & (to_line <= limit))).astype(np.uint8)


def at_scale(rgba, strokes, ink, scale, background):
    """Paint `strokes` in ink over the part, downscale with Lanczos and flatten."""
    img = rgba.astype(np.float32)
    if strokes is not None:
        cover = strokes.astype(np.float32)[..., None]
        img[..., :3] = img[..., :3] * (1 - cover) + ink * cover
    size = (max(1, round(img.shape[1] * scale)), max(1, round(img.shape[0] * scale)))
    small = Image.fromarray(np.round(img).clip(0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    flat = Image.new('RGBA', size, background)
    flat.alpha_composite(small)
    return flat.convert('RGB')


def compare(rgba, scales, target_px=1.8, kappa=0.25, dark_luma=70, mass_radius=14,
            background=(230, 236, 243, 255)):
    """Return [(scale, [naive, plain, protected])] and measurement stats."""
    line, mass, inside = split_ink(rgba, dark_luma, mass_radius)
    width = stroke_width(line)
    ink = rgba[..., :3][line > 0].astype(np.float32).mean(axis=0)
    rows = []
    for scale in scales:
        grow = max(0.0, (target_px / scale - width) / 2)
        plain = thicken(line, inside, grow) if grow > 0 else None
        protected = thicken(line, inside, grow, kappa) if grow > 0 else None
        rows.append((scale, [at_scale(rgba, strokes, ink, scale, background)
                             for strokes in (None, plain, protected)]))
    return rows, {'stroke_width_px': width, 'line_px': int(line.sum()), 'mass_px': int(mass.sum())}


def sheet(rows, zoom):
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:  # Pillow < 10.1 has only the fixed bitmap font
        font = ImageFont.load_default()
    cell = max(im.width for _, images in rows for im in images) * zoom
    label, header, gap = 110, 48, 10
    height = header + sum(images[0].height * zoom + gap for _, images in rows)
    out = Image.new('RGB', (label + len(COLUMNS) * (cell + gap), height), 'white')
    draw = ImageDraw.Draw(out)
    for i, name in enumerate(COLUMNS):
        draw.text((label + i * (cell + gap) + 8, 10), name, fill='black', font=font)
    y = header
    for scale, images in rows:
        draw.text((8, y + 8), f's={scale:g}', fill='black', font=font)
        for i, im in enumerate(images):
            out.paste(im.resize((im.width * zoom, im.height * zoom), Image.NEAREST), (label + i * (cell + gap), y))
        y += images[0].height * zoom + gap
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part', help='flattened RGBA part PNG (line and colour merged)')
    parser.add_argument('--out', required=True, help='comparison sheet PNG')
    parser.add_argument('--scales', default='0.06,0.10,0.16', help='comma-separated screen scales')
    parser.add_argument('--target-px', type=float, default=1.8, help='on-screen stroke width to restore')
    parser.add_argument('--kappa', type=float, default=0.25, help='share of the growth allowed in closing gaps')
    parser.add_argument('--dark-luma', type=float, default=70, help='luma below which a pixel counts as ink')
    parser.add_argument('--mass-radius', type=float, default=14, help='source px half-width above which ink is a mass')
    parser.add_argument('--zoom', type=int, default=4, help='nearest-neighbour magnification of each cell')
    args = parser.parse_args()
    source, out = Path(args.part), Path(args.out)
    if out.resolve() == source.resolve():
        parser.error('--out would overwrite the supplied part')
    scales = [float(v) for v in args.scales.split(',')]
    if min(scales) <= 0 or args.target_px <= 0 or not 0 <= args.kappa <= 1 or args.zoom < 1:
        parser.error('scales and --target-px must be positive, --kappa in [0,1], --zoom at least 1')
    with Image.open(source) as image:
        rgba = np.asarray(image.convert('RGBA'))
    rows, stats = compare(rgba, scales, args.target_px, args.kappa, args.dark_luma, args.mass_radius)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet(rows, args.zoom).save(out)
    print(f"stroke width ~{stats['stroke_width_px']:.1f}px, line px {stats['line_px']}, "
          f"mass px {stats['mass_px']} -> {out}")


if __name__ == '__main__':
    main()
