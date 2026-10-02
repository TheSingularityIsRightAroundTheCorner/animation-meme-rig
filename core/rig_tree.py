"""Derived from supplied Claude rig_tree v3; legacy affine/turn semantics retained."""
import copy
import math
from pathlib import Path
import numpy as np
from PIL import Image
from .assets import resolve_asset, validate_canvases
from .output import save_frames, temporal_average

def T(dx, dy):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)

def R(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

def S(kx, ky=None):
    ky = kx if ky is None else ky
    return np.array([[kx, 0, 0], [0, ky, 0], [0, 0, 1]], float)

def local_matrix(pivot, tr):
    if "matrix" in tr:
        matrix = np.asarray(tr["matrix"], float)
        if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-12:
            raise ValueError("matrix must be a finite invertible 3x3 transform")
        return matrix
    rot = tr.get("rot", 0.0)
    dx, dy = tr.get("dx", 0.0), tr.get("dy", 0.0)
    k = tr.get("scale", 1.0)
    kx, ky = tr.get("sx", k), tr.get("sy", k)     # sx/sy: squash toward the turn axis (2.5D)
    if not np.isfinite([rot, dx, dy, kx, ky, *pivot]).all() or kx == 0 or ky == 0:
        raise ValueError("transform values must be finite; scale must be nonzero")
    px, py = pivot
    return T(px + dx, py + dy) @ R(rot) @ S(kx, ky) @ T(-px, -py)

def world_matrices(parts, frame_tr):
    """Resolve tree. Detects cycles. Returns {name: 3x3}."""
    cache = {}

    def world(name, stack=()):
        if name in cache:
            return cache[name]
        if name in stack:
            raise ValueError(f"cycle: {' -> '.join(stack + (name,))}")
        if name not in parts:
            raise ValueError(f"unknown parent/part: {name}")
        p = parts[name]
        tr = frame_tr.get(name, {})
        L = local_matrix(p["pivot"], tr)
        # "parent" may be overridden per frame -> detach (None) or re-attach (name)
        par = tr["parent"] if "parent" in tr else p.get("parent")
        W = L if par is None else world(par, stack + (name,)) @ L
        cache[name] = W
        return W

    for n in parts:
        world(n)
    return cache

def turn_matrix(axis_x, axis_y, theta_deg, focal):
    """Rotate the part's plane about a vertical axis and project it with a finite camera.
    (u,v,1) -> (u*cos, v, 1 + u*sin/f).  Near side (u*sin<0) divides by <1: it GROWS and
    pushes outward. Far side shrinks and pulls in. That asymmetry is the direction cue an
    orthographic squash can never produce."""
    if not np.isfinite([axis_x, axis_y, theta_deg, focal]).all() or focal <= 0:
        raise ValueError("turn requires finite values and positive focal distance")
    th = math.radians(theta_deg)
    M = np.array([[math.cos(th), 0.0, 0.0],
                  [0.0,          1.0, 0.0],
                  [math.sin(th) / focal, 0.0, 1.0]], float)
    return T(axis_x, axis_y) @ M @ T(-axis_x, -axis_y)

def apply_homography(img, H):
    """PIL wants the output->input map, normalised so the bottom-right entry is 1."""
    inv = np.linalg.inv(H)
    inv = inv / inv[2, 2]
    c = (inv[0, 0], inv[0, 1], inv[0, 2],
         inv[1, 0], inv[1, 1], inv[1, 2],
         inv[2, 0], inv[2, 1])
    return img.transform(img.size, Image.PERSPECTIVE, c, resample=Image.BICUBIC)

def lerp(a, b, t):
    return a + (b - a) * t

def ease_out(t):
    return 1 - (1 - t) ** 3


def rendered_matrix(matrix, layer):
    turn = layer.get('turn')
    if turn:
        return turn_matrix(turn['axis_x'], turn['axis_y'], turn['theta'], turn.get('focal', 600)) @ matrix
    return matrix


def _point(matrix, point):
    p = matrix @ np.array([*point, 1.0])
    if abs(p[2]) < 1e-9:
        raise ValueError('point lies on the projection plane')
    return p[:2] / p[2]


def anchor_world(parts, layers, name, anchor, projected=False):
    point = parts[name]['anchors'][anchor] if isinstance(anchor, str) else anchor
    matrix = world_matrices(parts, layers)[name]
    if projected:
        matrix = rendered_matrix(matrix, layers.get(name, {}))
    return _point(matrix, point)


def reparent_layers(parts, layers, child, new_parent):
    """Return explicit layer state with an exact keep-world local matrix.

    Matrix storage preserves shear under nonuniformly scaled parents. Carry this
    state forward; ordinary per-frame parent overrides remain backward compatible.
    """
    before = world_matrices(parts, layers)
    result = copy.deepcopy(layers)
    result.setdefault(child, {})['parent'] = new_parent
    world_matrices(parts, result)  # validate the proposed hierarchy, including cycles
    parent_world = np.eye(3) if new_parent is None else before[new_parent]
    result[child]['matrix'] = (np.linalg.inv(parent_world) @ before[child]).tolist()
    return result


def align_anchor(parts, layers, child, child_anchor, target_world):
    """Translate a part in its parent's space to align an affine world anchor."""
    result = copy.deepcopy(layers)
    worlds = world_matrices(parts, layers)
    delta = np.asarray(target_world) - anchor_world(parts, layers, child, child_anchor)
    layer = result.setdefault(child, {})
    parent = layer.get('parent', parts[child].get('parent'))
    parent_world = np.eye(3) if parent is None else worlds[parent]
    layer['matrix'] = (np.linalg.inv(parent_world) @ T(*delta) @ worlds[child]).tolist()
    return result


def compose_frame(parts, images, layers, bg=(255, 255, 255, 255)):
    size = validate_canvases(images)
    matrices = world_matrices(parts, layers)
    canvas = Image.new('RGBA', size, tuple(bg))
    for name in sorted(parts, key=lambda n: layers.get(n, {}).get('z', parts[n].get('z', 0))):
        part, layer = parts[name], layers.get(name, {})
        if part.get('role') in ('guide', 'diagnostic') or not layer.get('visible', part.get('visible', True)):
            continue
        image = apply_homography(images[name], rendered_matrix(matrices[name], layer))
        opacity = float(layer.get('opacity', 1))
        if not 0 <= opacity <= 1:
            raise ValueError('opacity must lie in [0,1]')
        if opacity < 1:
            image.putalpha(image.getchannel('A').point(lambda v: int(v * opacity)))
        from .effects import composite_effect
        canvas = composite_effect(canvas, image, mode=layer.get('blend', part.get('blend', 'normal')))
    return canvas, matrices


def render(spec, out_gif=None, attach=True):
    """Return frames and legacy affine probe rows; optionally export.

    Extra `rendered_probes` in each row report projectively correct diagnostics.
    Source PNGs and the input spec are never modified.
    """
    from .camera_25d import crop_frame
    parts = copy.deepcopy(spec['parts'])
    if not parts or not spec.get('frames'):
        raise ValueError('rig requires parts and frames')
    if not attach:
        for name in spec.get('detach_for_control', []):
            parts[name]['parent'] = None
    images = {}
    for name, part in parts.items():
        with Image.open(resolve_asset(spec.get('base_dir', '.'), part['file'])) as image:
            images[name] = image.convert('RGBA')
    size = validate_canvases(images)
    out_size = tuple(spec.get('out_size', [980, 556]))
    bg = tuple(spec.get('bg', [255, 255, 255, 255]))
    preserve_alpha = spec.get('preserve_alpha', len(bg) == 4 and bg[3] < 255)
    mode = 'RGBA' if preserve_alpha else 'RGB'
    def average(samples):
        return temporal_average(samples, preserve_alpha=preserve_alpha)
    frames, logs, durations = [], [], []
    for index, frame in enumerate(spec['frames']):
        layers = frame.get('layers', {})
        substeps = frame.get('substeps') or [layers]
        cameras = frame.get('camera_substeps') or [frame.get('camera', [0, 0, *size])]
        samples = []
        count = max(len(substeps), len(cameras))
        for i in range(count):
            state = copy.deepcopy(layers)
            for name, values in substeps[min(i, len(substeps)-1)].items():
                state.setdefault(name, {}).update(values)
            canvas, _ = compose_frame(parts, images, state, bg)
            rect = cameras[min(i, len(cameras)-1)]
            # Original layer blur averages before the camera. For identical camera
            # samples averaging before crop preserves the historical byte output.
            samples.append(canvas)
        if len(cameras) == 1:
            if len(samples) > 1:
                canvas = average(samples).convert('RGBA')
            else:
                canvas = samples[0]
            result = crop_frame(canvas, cameras[0], out_size).convert(mode)
        else:
            cropped = [crop_frame(s, cameras[min(i, len(cameras)-1)], out_size).convert(mode) for i, s in enumerate(samples)]
            result = average(cropped)
        frames.append(result)
        durations.append(frame.get('ms', 80))
        matrices = world_matrices(parts, layers)
        row = {'frame': index}
        projected = {}
        for probe in spec.get('probes', []):
            for name in probe['parts']:
                key = f"{probe['name']}@{name}"
                row[key] = tuple(round(float(v), 1) for v in _point(matrices[name], probe['point']))
                projected[key] = tuple(round(float(v), 3) for v in _point(rendered_matrix(matrices[name], layers.get(name, {})), probe['point']))
        if projected:
            row['rendered_probes'] = projected
        logs.append(row)
    if out_gif is not None:
        save_frames(frames, out_gif, fps=spec.get('fps', 30), durations=durations)
    return frames, logs
