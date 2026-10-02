#!/usr/bin/env python3
"""Render an authored animation scene with the shared version-1 skill core."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))

from PIL import Image
import numpy as np
from core.assets import resolve_asset
from core.output import save_frames, temporal_average
from core.spec import asset_paths, load_spec, validate_spec


def read_image(path, base_dir='.'):
    with Image.open(resolve_asset(base_dir, path)) as image:
        return image.convert('RGBA')


def render_legacy_pant(spec):
    """Preserve ordered list layers, authored holds, and Pillow rotation sign."""
    from core.secondary import place
    from core.camera_25d import crop_frame
    images = {name: read_image(file, spec['base_dir']) for name, file in spec['parts'].items()}
    size = next(iter(images.values())).size
    crop = spec.get('crop', [0, 0, *size])
    background = tuple(spec.get('bg', [255, 255, 255, 255]))
    preserve_alpha = spec.get('preserve_alpha', len(background) == 4 and background[3] < 255)
    out_size = spec.get('out_size')
    if out_size is None:
        height = int(spec.get('height', crop[3] - crop[1]))
        out_size = [max(1, round((crop[2]-crop[0]) * height / (crop[3]-crop[1]))), height]
    frames, durations = [], []
    for frame in spec['frames']:
        canvas = Image.new('RGBA', size, background)
        for layer in frame['layers']:
            place(canvas, images[layer['part']], **{key:value for key,value in layer.items() if key != 'part'})
        frames.append(crop_frame(canvas, crop, out_size).convert('RGBA' if preserve_alpha else 'RGB'))
        durations.append(frame.get('ms', 80))
    return frames, durations


def render_camera(spec):
    """Consume camera substeps, pose swaps, exposure and explicit effect spaces."""
    from core.camera_25d import compile_shot, crop_frame
    from core.effects import composite_effect, build_speedline_overlay, pulse_strength
    images = {name: read_image(part if isinstance(part, str) else part['file'], spec['base_dir'])
              for name, part in spec['parts'].items()}
    size = tuple(spec['canvas'])
    output = tuple(spec.get('out_size', size))
    background = tuple(spec.get('bg', [255, 255, 255, 255]))
    preserve_alpha = spec.get('preserve_alpha', len(background) == 4 and background[3] < 255)
    frames, durations = [], []
    effect_images = {}

    def add_part(canvas, name):
        part = spec['parts'][name]
        mode = part.get('blend', 'normal') if isinstance(part, dict) else 'normal'
        return composite_effect(canvas, images[name], mode=mode)

    def effect(canvas, entry, frame_index, frame_ms, screen=False):
        key = (entry['part'], entry.get('kind', 'image'), screen)
        if key not in effect_images:
            image = images[entry['part']]
            effect_size = output if screen else size
            if entry.get('kind') == 'speedline':
                image = Image.fromarray(build_speedline_overlay(image, effect_size))
            elif screen and image.size != output:
                image = image.resize(output, Image.Resampling.LANCZOS)
            effect_images[key] = image
        strength = entry.get('opacity', 1)
        if 'pulse' in entry:
            # Camera duration belongs to the authored shot, not MP4 export fps.
            strength *= pulse_strength(frame_index, 1000/frame_ms, entry['pulse'])
        image = effect_images[key]
        return composite_effect(canvas, image, mode=entry.get('blend', 'normal'),
                                strength=strength, enabled=entry.get('enabled', True))

    for shot in spec['shots']:
        for shot_index, state in enumerate(compile_shot(shot, size)):
            world = Image.new('RGBA', size, background)
            for name in spec['layers']:
                world = add_part(world, name)
            if state.get('pose') is not None:
                world = add_part(world, state['pose'])
            for entry in state.get('world_effects', []):
                world = effect(world, entry, shot_index, state['ms'])
            crops = state.get('camera_substeps') or [state['camera']]
            samples = [crop_frame(world, crop, output).convert('RGBA' if preserve_alpha else 'RGB') for crop in crops]
            if len(samples) == 1:
                frame = samples[0]
            else:
                frame = temporal_average(samples, preserve_alpha=preserve_alpha)
            exposure = state.get('exposure', 1)
            if exposure != 1:
                values = np.asarray(frame, np.float32).copy()
                values[..., :3] = np.clip(values[..., :3]*exposure, 0, 255)
                frame = Image.fromarray(values.astype(np.uint8))
            canvas = frame.convert('RGBA')
            for entry in state.get('screen_effects', []):
                canvas = effect(canvas, entry, shot_index, state['ms'], screen=True)
            frames.append(canvas.convert('RGBA' if preserve_alpha else 'RGB'))
            durations.append(state['ms'])
    return frames, durations


def render_scene(spec):
    """Return frames, per-frame durations and optional numerical diagnostics."""
    mode = spec['mode']
    fps = spec.get('fps', 30)
    logs = None
    if mode == 'rig':
        from core.rig_tree import render
        frames, logs = render(spec)
        durations = [frame.get('ms', 80) for frame in spec['frames']]
    elif mode == 'punch':
        from core.punch import render_frames
        a = spec['assets']; enabled = spec.get('speedline', {}).get('enabled', True)
        frames = render_frames(read_image(a['body']), [read_image(file) for file in a['fists']],
                               read_image(a['speedline']) if enabled else None, spec)
        durations = [1000/fps]*len(frames)
    elif mode == 'mesh':
        from core.mesh_warp import render_sequence
        frames = render_sequence([read_image(file) for file in spec['assets']['poses']], spec['sequence'],
                                 size=spec.get('canvas', [540,960]), bpm=spec.get('bpm',189.9), fps=fps,
                                 beats_per_pose=spec.get('beats_per_pose',2), preserve_baselines=spec.get('preserve_baselines',[]),
                                 offset_ms=spec.get('offset_ms',0))
        durations = [1000/fps]*len(frames)
    elif mode == 'globe':
        from core.sphere import render_frames
        frames = render_frames(spec, spec['base_dir'])
        durations = [spec.get('frame_ms', 1000/fps)]*len(frames)
    elif mode == 'room':
        from core.stadium3d import render_frames
        frames = render_frames(spec, spec['base_dir'])
        durations = [spec.get('frame_ms', 70)]*len(frames)
    elif mode == 'pant':
        if spec.get('format') == 'legacy_layers':
            frames, durations = render_legacy_pant(spec)
        else:
            from core.secondary import render_frames
            frames, durations = render_frames(spec, spec['base_dir'])
    elif mode == 'camera':
        frames, durations = render_camera(spec)
    else:
        raise ValueError(f'Unsupported mode {mode}')
    return frames, durations, logs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path, help='Version-1 JSON scene or supported legacy rig/pant JSON')
    parser.add_argument('--out', type=Path, help='PNG sequence directory, single PNG, GIF or MP4 (overrides scene output)')
    parser.add_argument('--assets', type=Path, help='Replace asset base_dir; remap historical absolute filenames by basename')
    parser.add_argument('--validate', action='store_true', help='Validate data, image paths/dimensions and cameras without rendering')
    parser.add_argument('--probes', type=Path, help='Write rig affine/projected probe diagnostics as JSON')
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec, assets=args.assets)
        validate_spec(spec)
        output = args.out or (Path(spec['output']) if spec.get('output') else None)
        inputs = {resolve_asset(spec['base_dir'], file).resolve() for file in asset_paths(spec)}
        if output is not None and output.expanduser().resolve() in inputs:
            raise ValueError('Output would overwrite a supplied input asset; choose another path')
        if args.probes is not None and args.probes.expanduser().resolve() in inputs:
            raise ValueError('Probe output would overwrite a supplied input asset')
        if args.validate:
            print(f'valid: mode={spec["mode"]}, assets={len(inputs)}')
            return 0
        if output is None:
            raise ValueError('Specify --out or an output path in the scene')
        if args.probes is not None and spec['mode'] != 'rig':
            raise ValueError('--probes is available for rig mode only')
        frames, durations, logs = render_scene(spec)
        destinations = {output.expanduser().resolve()}
        if not output.suffix:
            destinations = {(output / f'{index:05d}.png').expanduser().resolve() for index in range(len(frames))}
            destinations.add((output / 'timing.json').expanduser().resolve())
        if args.probes is not None:
            destinations.add(args.probes.expanduser().resolve())
        if destinations & inputs:
            raise ValueError('Planned output would overwrite a supplied input asset; choose another directory')
        save_frames(frames, output, fps=spec.get('fps', 30), durations=durations, bg=spec.get('bg', [255,255,255]))
        if args.probes is not None:
            args.probes.parent.mkdir(parents=True, exist_ok=True)
            args.probes.write_text(json.dumps(logs, indent=2)+'\n')
        print(f'wrote {output} | mode={spec["mode"]} | frames={len(frames)} | duration_ms={sum(durations):.3f}')
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        parser.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
