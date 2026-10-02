"""One animation palette; explicit PNG/GIF/MP4 export."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image


def flatten(frame, bg=(255, 255, 255)):
    if frame.mode == 'RGB':
        return frame
    canvas = Image.new('RGBA', frame.size, (*bg[:3], 255))
    canvas.alpha_composite(frame.convert('RGBA'))
    return canvas.convert('RGB')


def temporal_average(samples, preserve_alpha=False):
    """Source-compatible RGB average, or premultiplied RGBA for alpha delivery."""
    if not samples:
        raise ValueError('temporal samples cannot be empty')
    if not preserve_alpha:
        return Image.fromarray(np.mean([np.asarray(s.convert('RGB'), dtype=np.float32) for s in samples], axis=0).astype(np.uint8))
    arrays = np.stack([np.asarray(s.convert('RGBA'), dtype=np.float32) for s in samples])
    alpha = arrays[..., 3:4] / 255
    mean_alpha = alpha.mean(axis=0)
    premult = (arrays[..., :3] * alpha).mean(axis=0)
    colors = np.divide(premult, mean_alpha, out=np.zeros_like(premult), where=mean_alpha > 0)
    return Image.fromarray(np.concatenate((colors, mean_alpha * 255), axis=2).clip(0,255).astype(np.uint8))


def global_palette(frames):
    if not frames:
        raise ValueError('no frames')
    # Every frame contributes, including a single-frame late impact. Downsample
    # only large frames, preserving small diagnostic gradients in full.
    samples = []
    for frame in frames:
        sample = flatten(frame).copy()
        sample.thumbnail((256, 256))
        samples.append(sample)
    atlas = Image.new('RGB', (max(f.width for f in samples), sum(f.height for f in samples)))
    y = 0
    for sample in samples:
        atlas.paste(sample, (0, y))
        y += sample.height
    return atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)


def quantize_frames(frames):
    palette = global_palette(frames)
    # Pillow's fixed-palette cache uses reduced RGB precision and can collapse
    # an exact 255-step grayscale into 64 levels. Preserve exact palette matches.
    colors = np.asarray(palette.getpalette(), dtype=np.uint32).reshape(-1, 3)
    keys = (colors[:, 0] << 16) | (colors[:, 1] << 8) | colors[:, 2]
    order = np.argsort(keys, kind='stable')
    sorted_keys = keys[order]
    result = []
    for frame in frames:
        rgb = flatten(frame)
        q = rgb.quantize(palette=palette, dither=Image.Dither.NONE)
        a = np.asarray(rgb, dtype=np.uint32)
        pixels = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
        where = np.searchsorted(sorted_keys, pixels).clip(0, len(keys)-1)
        exact = sorted_keys[where] == pixels
        indices = np.array(q)
        indices[exact] = order[where[exact]].astype(np.uint8)
        fixed = Image.fromarray(indices)
        fixed.putpalette(palette.getpalette())
        result.append(fixed)
    return result


def save_frames(frames, path, fps=30, durations=None, bg=(255, 255, 255)):
    if not frames or fps <= 0:
        raise ValueError('frames must be nonempty and fps positive')
    if len({f.size for f in frames}) != 1:
        raise ValueError('output frame dimensions must match')
    if durations is not None and (len(durations) != len(frames) or any(not np.isfinite(x) or x <= 0 for x in durations)):
        raise ValueError('one positive duration per frame is required')
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in ('', '.png', '.gif', '.mp4'):
        raise ValueError(f'unsupported output extension: {suffix}')
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == '':
        path.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(frames):
            frame.save(path / f'{index:05d}.png')
        (path / 'timing.json').write_text(json.dumps({'fps': fps, 'durations_ms': durations or [1000/fps]*len(frames)}, indent=2)+'\n')
    elif suffix == '.png':
        if len(frames) != 1:
            raise ValueError('multiple PNG frames need an output directory without a suffix')
        frames[0].save(path)
    elif suffix == '.gif':
        q = quantize_frames([flatten(f, bg) for f in frames])
        q[0].save(path, save_all=True, append_images=q[1:], duration=durations or round(1000/fps), loop=0, disposal=2, optimize=False)
    else:
        if not shutil.which('ffmpeg'):
            raise RuntimeError('MP4 export requires ffmpeg on PATH; PNG/GIF remain available')
        if frames[0].width % 2 or frames[0].height % 2:
            raise ValueError('yuv420p MP4 requires even output dimensions; use PNG or adjust out_size')
        indices = list(range(len(frames)))
        if durations is not None:
            ends = np.cumsum(durations) / 1000
            count = max(1, round(ends[-1] * fps))
            indices = np.searchsorted(ends, np.arange(count) / fps + 1e-9, side='right').clip(0, len(frames)-1).tolist()
        with tempfile.TemporaryDirectory() as directory:
            for index, source in enumerate(indices):
                flatten(frames[source], bg).save(Path(directory) / f'{index:06d}.png')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(fps),'-i',str(Path(directory)/'%06d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(path)], check=True)
    return path
