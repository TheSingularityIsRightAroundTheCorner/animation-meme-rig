"""Version-1 scene dispatch, explicit legacy adapters, and runtime validation.

No JSON Schema package is required. The matching published schema describes
portable documents; asset existence, image dimensions and hierarchy checks run
here before rendering.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
from PIL import Image
from .assets import resolve_asset

MODES = ('rig', 'punch', 'mesh', 'globe', 'room', 'pant', 'camera')
BLENDS = ('normal', 'screen', 'multiply', 'overlay')


def _dict(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    return value


def _list(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f'{label} must be a {"nonempty " if nonempty else ""}list')
    return value


def _number(value, label, minimum=None, maximum=None, positive=False, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    if integer and int(value) != value:
        raise ValueError(f'{label} must be an integer')
    if positive and value <= 0 or minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(f'{label} is outside the supported range')
    return value


def _vector(value, length, label, positive=False, integer=False):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f'{label} must contain {length} numbers')
    for item in value:
        _number(item, label, positive=positive, integer=integer)
    return value


def _path(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f'{label} must be a nonempty path string')
    return value


def _rect(value, label, size=None, xywh=False):
    a, b, c, d = _vector(value, 4, label)
    if xywh:
        c, d = a + c, b + d
    if c <= a or d <= b:
        raise ValueError(f'{label} must have positive width and height')
    if size is not None and (a < 0 or b < 0 or c > size[0] or d > size[1]):
        raise ValueError(f'{label} exceeds the source canvas')


def _merge(base, overrides):
    result = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_json(path):
    try:
        return _dict(json.loads(Path(path).read_text(encoding='utf-8')), str(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Cannot read JSON {path}: {exc}') from exc


def load_spec(path, assets=None):
    """Load/merge relative to the scene file and make external asset paths explicit.

    A profile is data, not executable code. Paths contained in the merged profile
    resolve relative to the scene file. ``assets`` explicitly replaces base_dir;
    with that override historical absolute filenames are mapped by basename.
    """
    scene_path = Path(path).expanduser().resolve()
    data = _read_json(scene_path)
    if 'profile' in data:
        profile_path = scene_path.parent / _path(data['profile'], 'profile')
        profile = _read_json(profile_path)
        if 'profile' in profile:
            raise ValueError('Nested profile includes are unsupported; merge one explicit profile')
        data = _merge(profile, data)
    if 'mode' not in data:
        if 'parts' in data and isinstance(data.get('frames'), list) and data['frames']:
            data['mode'] = 'pant' if isinstance(data['frames'][0].get('layers'), list) else 'rig'
        else:
            raise ValueError('mode is required (legacy detection supports rig and pant list layers only)')
    data.setdefault('version', 1)
    if data['mode'] == 'pant' and 'parts' in data and 'actors' not in data:
        data['format'] = 'legacy_layers'
    declared_base = _path(data.get('base_dir', '.'), 'base_dir')
    base = Path(assets).expanduser().resolve() if assets is not None else (scene_path.parent / declared_base).resolve()
    data['base_dir'] = str(base)

    def asset(value):
        value = _path(value, 'asset')
        path_value = Path(value)
        if assets is not None and path_value.is_absolute():
            path_value = Path(path_value.name)
        # Unicode lookup is performed during validation, so missing paths remain
        # useful diagnostics rather than being silently substituted.
        return str(base / path_value)

    mode = data['mode']
    if mode in ('rig', 'camera') and isinstance(data.get('parts'), dict):
        for name, part in data['parts'].items():
            if isinstance(part, str):
                data['parts'][name] = asset(part)
            elif isinstance(part, dict) and 'file' in part:
                part['file'] = asset(part['file'])
    if mode in ('punch', 'mesh') and isinstance(data.get('assets'), dict):
        for key, value in data['assets'].items():
            data['assets'][key] = [asset(item) for item in value] if isinstance(value, list) else asset(value)
    if mode == 'globe':
        for key in ('land', 'cloud'):
            if data.get(key) is not None:
                data[key] = asset(data[key])
    if mode == 'room':
        if 'panel_sheet' in data: data['panel_sheet'] = asset(data['panel_sheet'])
        if isinstance(data.get('pose_files'), list): data['pose_files'] = [asset(p) for p in data['pose_files']]
    if mode == 'pant':
        if data.get('format') == 'legacy_layers' and isinstance(data.get('parts'), dict):
            data['parts'] = {name: asset(file) for name, file in data['parts'].items()}
        else:
            for key in ('background', 'divider', 'divider_background'):
                if data.get(key) is not None: data[key] = asset(data[key])
            if isinstance(data.get('actors'), list):
                for actor in data['actors']:
                    if isinstance(actor.get('files'), dict): actor['files'] = {name: asset(file) for name, file in actor['files'].items()}
                    for key in ('steam', 'mask'):
                        if actor.get(key) is not None: actor[key] = asset(actor[key])
    output = data.get('output', data.get('out'))
    if output is not None:
        data['output'] = str(scene_path.parent / _path(output, 'output'))
    return data


def asset_paths(spec):
    mode = spec['mode']
    if mode in ('rig', 'camera'):
        return [p if isinstance(p, str) else p['file'] for p in spec['parts'].values()]
    if mode == 'punch':
        a = spec['assets']; return [a['body'], *a['fists']] + ([a['speedline']] if spec.get('speedline', {}).get('enabled', True) else [])
    if mode == 'mesh': return spec['assets']['poses']
    if mode == 'globe': return [spec['land']] + ([spec['cloud']] if spec.get('cloud') is not None else [])
    if mode == 'room': return [spec['panel_sheet'], *spec['pose_files']]
    if mode == 'pant':
        if spec.get('format') == 'legacy_layers': return list(spec['parts'].values())
        result = [spec['background']]
        result += [spec[k] for k in ('divider', 'divider_background') if spec.get(k) is not None]
        for actor in spec['actors']:
            result += list(actor['files'].values())
            if actor.get('steam') is not None: result.append(actor['steam'])
            if actor.get('mask') is not None: result.append(actor['mask'])
        return result
    return []


def _parts(spec, require_objects=False):
    parts = _dict(spec.get('parts'), 'parts')
    if not parts: raise ValueError('parts must be nonempty')
    for name, part in parts.items():
        if not isinstance(name, str) or not name: raise ValueError('part names must be nonempty strings')
        if isinstance(part, str) and not require_objects:
            _path(part, f'parts.{name}')
        else:
            _dict(part, f'parts.{name}'); _path(part.get('file'), f'parts.{name}.file')
            if require_objects: _vector(part.get('pivot'), 2, f'parts.{name}.pivot')
            if part.get('parent') is not None and part['parent'] not in parts: raise ValueError(f'unknown parent {part["parent"]}')
            if 'blend' in part and part['blend'] not in BLENDS: raise ValueError('unsupported part blend')
            if 'z' in part: _number(part['z'], 'part.z')
            for point in part.get('anchors', {}).values(): _vector(point, 2, 'anchor')
    return parts


def _rig_layers(layers, parts):
    from .rig_tree import world_matrices, rendered_matrix
    _dict(layers, 'frame.layers')
    unknown = set(layers) - set(parts)
    if unknown: raise ValueError(f'unknown rig layers: {sorted(unknown)}')
    allowed = {'visible','rot','dx','dy','scale','sx','sy','parent','z','turn','matrix','opacity','blend'}
    for name, values in layers.items():
        _dict(values, f'layers.{name}')
        if set(values) - allowed: raise ValueError(f'unsupported rig layer fields: {sorted(set(values)-allowed)}')
        if 'visible' in values and not isinstance(values['visible'], bool): raise ValueError('visible must be boolean')
        if 'opacity' in values: _number(values['opacity'], 'opacity', minimum=0, maximum=1)
        if 'z' in values: _number(values['z'], 'z')
        if values.get('blend', 'normal') not in BLENDS: raise ValueError('unsupported layer blend')
        if 'turn' in values:
            turn = _dict(values['turn'], 'turn')
            for field in ('axis_x', 'axis_y', 'theta'): _number(turn.get(field), f'turn.{field}')
            _number(turn.get('focal', 600), 'turn.focal', positive=True)
    matrices = world_matrices(parts, layers)
    for name, matrix in matrices.items(): rendered_matrix(matrix, layers.get(name, {}))


def _rig(spec):
    parts = _parts(spec, True)
    for frame in _list(spec.get('frames'), 'frames'):
        _dict(frame, 'frame'); _number(frame.get('ms', 80), 'frame.ms', positive=True)
        unsupported = set(frame) - {'layers','camera','ms','substeps','camera_substeps'}
        if unsupported: raise ValueError(f'unsupported rig frame fields: {sorted(unsupported)}; use camera mode for camera effects')
        _rig_layers(frame.get('layers', {}), parts)
        if 'camera' in frame: _rect(frame['camera'], 'frame.camera')
        for state in frame.get('substeps', []):
            merged = _merge(frame.get('layers', {}), _dict(state, 'substep'))
            _rig_layers(merged, parts)
        for rect in frame.get('camera_substeps', []): _rect(rect, 'camera_substep')
    for probe in spec.get('probes', []):
        _path(probe.get('name'), 'probe.name'); _vector(probe.get('point'), 2, 'probe.point')
        for part in _list(probe.get('parts'), 'probe.parts'):
            if part not in parts: raise ValueError('probe references unknown part')


def _punch(spec):
    a = _dict(spec.get('assets'), 'assets')
    _path(a.get('body'), 'assets.body')
    images = _list(a.get('fists'), 'assets.fists')
    for file in images: _path(file, 'fist path')
    meta = _list(spec.get('fists'), 'fists')
    if len(meta) != len(images): raise ValueError('one fists metadata entry is required per asset')
    shoulders = _dict(spec.get('shoulders'), 'shoulders')
    for point in shoulders.values(): _vector(point, 2, 'shoulder')
    for item in meta:
        _dict(item, 'fist metadata'); _vector(item.get('centroid'), 2, 'fist.centroid')
        if item.get('side') not in shoulders: raise ValueError('fist side must reference a measured shoulder')
    punch = _dict(spec.get('punch'), 'punch')
    for key in ('step_frames','duration_frames','perspective_scale','end_overshoot','initial_scale','ease_power'):
        if key in punch: _number(punch[key], 'punch.'+key, positive=True)
    _number(punch.get('count', 10), 'punch.count', positive=True, integer=True)
    if punch.get('fade_start') is not None: _number(punch['fade_start'], 'fade_start', minimum=0, maximum=.999999)
    blur = _dict(spec.get('motion_blur', {}), 'motion_blur')
    if blur.get('type', 'temporal_substeps') != 'temporal_substeps': raise ValueError('motion_blur.type must be temporal_substeps')
    _number(blur.get('substeps', 4), 'substeps', positive=True, integer=True)
    _number(blur.get('shutter', .7), 'shutter', minimum=0)
    camera = _dict(spec.get('camera', {}), 'camera')
    _number(camera.get('zoom_end', .78), 'zoom_end', positive=True)
    if camera.get('ease', 'cubic_out') not in ('linear','cubic_out'): raise ValueError('unsupported punch camera ease')
    effect = _dict(spec.get('speedline', {}), 'speedline')
    if not isinstance(effect.get('enabled', True), bool): raise ValueError('speedline.enabled must be boolean')
    if effect.get('enabled', True): _path(a.get('speedline'), 'assets.speedline')
    if effect.get('z_order', 'topmost') not in ('topmost','background'): raise ValueError('unsupported speedline z_order')
    if effect.get('full_screen_flash', False): raise ValueError('line pulse cannot request full_screen_flash')
    _number(effect.get('pulse_interval_sec', .5), 'pulse_interval_sec', positive=True)
    for value in effect.get('visible_envelope_frames', [.25,.75,1,.55,.18]): _number(value, 'pulse strength', minimum=0, maximum=1)


def _mesh(spec):
    a = _dict(spec.get('assets'), 'assets')
    poses = _list(a.get('poses'), 'assets.poses')
    for file in poses: _path(file, 'pose path')
    for row in _list(spec.get('sequence'), 'sequence'):
        if not isinstance(row, list) or len(row) != 3: raise ValueError('sequence rows are [one-based pose, motion name, strength]')
        _number(row[0], 'pose index', positive=True, integer=True)
        if row[0] > len(poses): raise ValueError('sequence pose exceeds assets.poses')
        if row[1] not in ('none','shakeR','shakeL','clapR','clapL','cross','pulse','breathe','pop','leanR','leanL','reachR','reachL','final','waveR','waveL'): raise ValueError('unsupported mesh motion name')
        _number(row[2], 'motion strength', minimum=0)
    _number(spec.get('bpm', 189.9), 'bpm', positive=True)
    _number(spec.get('beats_per_pose', 2), 'beats_per_pose', positive=True)
    _number(spec.get('offset_ms', 0), 'offset_ms')
    for index in spec.get('preserve_baselines', []): _number(index, 'preserve_baselines', minimum=1, maximum=len(poses), integer=True)


def _globe(spec):
    unsupported = {'cloud_drift_turns', 'spin_turns', 'spin_start'} & set(spec)
    if unsupported: raise ValueError(f'unsupported globe controls: {sorted(unsupported)}; use cloud_relative_speed')
    _path(spec.get('land'), 'land')
    if spec.get('cloud') is not None: _path(spec['cloud'], 'cloud')
    _number(spec.get('size', 520), 'size', positive=True, integer=True)
    _number(spec.get('frames', 48), 'frames', positive=True, integer=True)
    light = _vector(spec.get('light', [-.6,.35,.72]), 3, 'light')
    if not any(light): raise ValueError('light direction must be nonzero')
    for key in ('ambient','cloud_opacity'):
        if key in spec: _number(spec[key], key, minimum=0, maximum=1)
    for key in ('rim','cloud_relative_speed'):
        if key in spec: _number(spec[key], key)


def _room(spec):
    _path(spec.get('panel_sheet'), 'panel_sheet')
    for file in _list(spec.get('pose_files'), 'pose_files'): _path(file, 'pose_file')
    panels = _dict(spec.get('panels'), 'panels')
    if not {'far','left','right','near','floor'} <= set(panels): raise ValueError('panels require far,left,right,near,floor')
    for name, panel in panels.items():
        _rect(panel.get('box') if isinstance(panel, dict) else panel, 'panels.'+name)
        if isinstance(panel, dict): _number(panel.get('rotation', 0), 'panel.rotation')
    _number(spec.get('frames', 42), 'frames', minimum=2, integer=True)
    _number(spec.get('slices', 14), 'slices', positive=True, integer=True)
    for key, value in _dict(spec.get('room', {}), 'room').items():
        if key not in ('width','depth','height'): raise ValueError('unsupported room dimension')
        _number(value, 'room.'+key, positive=True)
    for key in ('camera_start','camera_end'):
        if key not in spec: continue
        camera = _dict(spec[key], key)
        eye = _vector(camera.get('eye'), 3, key+'.eye'); target = _vector(camera.get('target'), 3, key+'.target')
        _number(camera.get('fov'), key+'.fov', positive=True, maximum=179)
        if eye[0] == target[0] and eye[2] == target[2]: raise ValueError('room view direction cannot be parallel to vertical up')
    for item in spec.get('pose_schedule', []):
        _number(item.get('at'), 'pose_schedule.at', minimum=0, maximum=1)
        _number(item.get('part'), 'pose_schedule.part', minimum=0, maximum=len(spec['pose_files'])-1, integer=True)
    if spec.get('pose_schedule') and min(item['at'] for item in spec['pose_schedule']) != 0: raise ValueError('pose_schedule must start at zero')


def _pant(spec):
    if spec.get('format') == 'legacy_layers':
        parts = _parts(spec)
        if any(not isinstance(v, str) for v in parts.values()): raise ValueError('legacy pant parts map names to filenames')
        if 'crop' in spec: _rect(spec['crop'], 'crop')
        if 'height' in spec: _number(spec['height'], 'height', positive=True, integer=True)
        allowed = {'part','dx','dy','rot','pivot','scale','opacity'}
        for frame in _list(spec.get('frames'), 'frames'):
            _number(frame.get('ms', 80), 'frame.ms', positive=True)
            for layer in _list(frame.get('layers'), 'legacy layers', nonempty=False):
                _dict(layer, 'legacy layer')
                if set(layer)-allowed: raise ValueError(f'unsupported legacy pant fields: {sorted(set(layer)-allowed)}')
                if layer.get('part') not in parts: raise ValueError('legacy pant layer references unknown part')
                for key in ('dx','dy','rot'):
                    if key in layer: _number(layer[key], key)
                if 'pivot' in layer: _vector(layer['pivot'], 2, 'pivot')
                if 'scale' in layer: _number(layer['scale'], 'scale', positive=True)
                if 'opacity' in layer: _number(layer['opacity'], 'opacity', minimum=0, maximum=1)
        return
    _path(spec.get('background'), 'background')
    _number(spec.get('breaths', 2), 'breaths', positive=True, integer=True)
    for actor in _list(spec.get('actors'), 'actors'):
        _dict(actor, 'actor'); profile = _dict(actor.get('profile'), 'actor.profile')
        _vector(profile.get('neck'), 2, 'neck'); _vector(profile.get('crown'), 2, 'crown')
        files = _dict(actor.get('files'), 'actor.files'); names = _dict(profile.get('parts'), 'profile.parts')
        for file in files.values(): _path(file, 'actor file')
        for key in ('body1','body2','head','hair'):
            if names.get(key) not in files: raise ValueError('profile.parts references unavailable actor art')
        for row in _list(profile.get('breath'), 'profile.breath'):
            _vector(row, 5, 'breath row'); _number(row[0], 'body pose', minimum=1, maximum=2, integer=True); _number(row[4], 'breath duration', positive=True)
        if actor.get('side', 'left') not in ('left','right'): raise ValueError('actor side must be left or right')
        if actor.get('steam') and not actor.get('mask') and 'side' not in actor:
            raise ValueError('steam requires a supplied mask or explicit actor side')
        if 'period' in actor.get('steam_parameters', {}):
            raise ValueError('steam period follows the authored breath cycle length')


def _camera(spec):
    from .camera_25d import compile_shot
    parts = _parts(spec)
    canvas = _vector(spec.get('canvas'), 2, 'canvas', positive=True, integer=True)
    for name in _list(spec.get('layers'), 'layers', nonempty=False):
        if name not in parts: raise ValueError('camera static layer references unknown part')
    allowed = {'name','frame_start','frame_end','easing','ease_power','frames','motion_blur','blur_steps','hold_in','hold_out','frame_ms','overshoot','exposure','swap','screen_effects','world_effects'}
    for shot in _list(spec.get('shots'), 'shots'):
        _dict(shot, 'shot')
        unsupported = set(shot) - allowed
        if unsupported: raise ValueError(f'unsupported camera shot fields: {sorted(unsupported)}')
        _rect(shot.get('frame_start'), 'frame_start', canvas, xywh=True)
        if 'frame_end' in shot: _rect(shot['frame_end'], 'frame_end', canvas, xywh=True)
        _number(shot.get('frames', 14), 'shot.frames', minimum=2, integer=True)
        _number(shot.get('frame_ms', 50), 'shot.frame_ms', positive=True)
        for key in ('hold_in','hold_out'): _number(shot.get(key, 0), key, minimum=0, integer=True)
        if 'exposure' in shot:
            _vector(shot['exposure'], 2, 'exposure')
            for value in shot['exposure']: _number(value, 'exposure', minimum=0)
        for item in shot.get('swap', []):
            _number(item.get('at'), 'swap.at', minimum=0, maximum=1)
            if item.get('part') not in parts: raise ValueError('swap references unknown part')
        if shot.get('swap') and min(item['at'] for item in shot['swap']) != 0: raise ValueError('swap must start at zero')
        for key in ('world_effects','screen_effects'):
            for effect in shot.get(key, []):
                _dict(effect, key)
                if set(effect)-{'part','blend','opacity','enabled','kind','pulse'}: raise ValueError(f'unsupported {key} fields')
                if effect.get('part') not in parts: raise ValueError('effect references unknown part')
                if effect.get('blend', 'normal') not in BLENDS: raise ValueError('unsupported effect blend')
                _number(effect.get('opacity', 1), 'effect opacity', minimum=0, maximum=1)
                if not isinstance(effect.get('enabled', True), bool): raise ValueError('effect enabled must be boolean')
                if effect.get('kind', 'image') not in ('image','speedline'): raise ValueError('effect kind must be image or speedline')
                if 'pulse' in effect:
                    pulse = _dict(effect['pulse'], 'effect.pulse')
                    if set(pulse)-{'enabled','pulse_interval_sec','visible_envelope_frames'}: raise ValueError('unsupported effect.pulse fields')
                    if not isinstance(pulse.get('enabled', True), bool): raise ValueError('pulse enabled must be boolean')
                    _number(pulse.get('pulse_interval_sec', .5), 'pulse interval', positive=True)
                    for value in _list(pulse.get('visible_envelope_frames', [.25,.75,1,.55,.18]), 'pulse envelope'):
                        _number(value, 'pulse strength', minimum=0, maximum=1)
        compile_shot(shot, canvas)  # Check the entire trajectory and all camera substeps.


def validate_spec(spec, check_assets=True):
    """Raise ValueError for malformed data before decoding/rendering any frames."""
    _dict(spec, 'spec')
    if spec.get('version') != 1: raise ValueError('version must be 1')
    mode = spec.get('mode')
    if mode not in MODES: raise ValueError(f'unknown mode {mode!r}; choose {", ".join(MODES)}')
    _number(spec.get('fps', 30), 'fps', positive=True)
    for key in ('canvas','out_size'):
        if key in spec: _vector(spec[key], 2, key, positive=True, integer=True)
    for key in ('frame_ms',):
        if key in spec: _number(spec[key], key, positive=True)
    if 'preserve_alpha' in spec and not isinstance(spec['preserve_alpha'], bool): raise ValueError('preserve_alpha must be boolean')
    alpha_supported = mode in ('rig','camera') or mode == 'pant' and spec.get('format') == 'legacy_layers'
    transparent_bg = isinstance(spec.get('bg'), list) and len(spec['bg']) == 4 and spec['bg'][3] < 255
    if not alpha_supported and (spec.get('preserve_alpha', False) or transparent_bg):
        raise ValueError(f'{mode} currently produces opaque frames; alpha output is supported by rig, camera, and legacy pant')
    if 'bg' in spec:
        if not isinstance(spec['bg'], list) or len(spec['bg']) not in (3,4): raise ValueError('bg must contain RGB or RGBA values')
        for value in spec['bg']: _number(value, 'bg', minimum=0, maximum=255, integer=True)
    {'rig':_rig,'punch':_punch,'mesh':_mesh,'globe':_globe,'room':_room,'pant':_pant,'camera':_camera}[mode](spec)
    if not check_assets: return spec
    sizes = {}
    for file in asset_paths(spec):
        _path(file, 'asset path')
        try:
            resolved = resolve_asset(spec.get('base_dir', '.'), file)
            with Image.open(resolved) as image:
                sizes[file] = image.size
                image.verify()
        except (OSError, ValueError) as exc:
            raise ValueError(f'Cannot read supplied asset {file}: {exc}') from exc
    if mode in ('rig','mesh','camera') or mode == 'pant' and spec.get('format') == 'legacy_layers':
        if len(set(sizes.values())) != 1: raise ValueError('this mode requires a shared source canvas')
        size = next(iter(sizes.values()))
        if mode == 'camera' and list(size) != spec['canvas']: raise ValueError('camera.canvas must match supplied art')
        if mode == 'rig':
            for frame in spec['frames']:
                if 'camera' in frame: _rect(frame['camera'], 'frame.camera', size)
                for rect in frame.get('camera_substeps', []): _rect(rect, 'camera_substep', size)
        if mode == 'pant' and 'crop' in spec: _rect(spec['crop'], 'crop', size)
    if mode == 'room':
        size = sizes[spec['panel_sheet']]
        for name, panel in spec['panels'].items(): _rect(panel.get('box') if isinstance(panel, dict) else panel, 'panels.'+name, size)
    return spec
