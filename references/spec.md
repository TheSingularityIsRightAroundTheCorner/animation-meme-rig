# Scene format and CLI

Use Python 3.10+ with the packages in `requirements.txt`. `ffmpeg` is needed only for MP4. Run commands from the skill directory, or replace `scripts/render.py` with its absolute path.

```sh
python scripts/render.py shot.json --validate
python scripts/render.py shot.json --out previews/shot
python scripts/render.py shot.json --out previews/shot.gif
python scripts/render.py shot.json --out previews/shot.mp4
python scripts/render.py historical_spec.json --assets /path/to/original/art --out previews/review --probes previews/probes.json
```

`--validate` checks the scene structure, hierarchy, image readability, shared canvases where needed, and camera bounds. It does not render or create outputs. Missing artwork is an error with its path; the renderer never creates replacement art. `--probes` is available for rig mode only. The CLI refuses output filenames that would overwrite supplied input artwork, including numbered PNG sequence files.

An output path with **no suffix** is a PNG sequence directory containing `00000.png` onward and `timing.json`. `.png` accepts exactly one frame. `.gif` uses one global palette. `.mp4` uses H.264/YUV420p, requires even dimensions, and resamples authored holds onto the export `fps`. PNG timing is exact in `durations_ms`; GIF timing has the format's centisecond precision. Preview output files may be overwritten when they are not input artwork.

## Common fields and paths

A canonical document contains `"version": 1` and one `mode`: `rig`, `punch`, `mesh`, `globe`, `room`, `pant`, or `camera`. The [machine-readable schema](../schemas/animation.schema.json) is JSON Schema draft 2020-12. Apply it to the **expanded scene** returned by `core.spec.load_spec`, after optional profile merging and legacy adaptation. Runtime validation adds checks that JSON Schema cannot express, such as image dimensions, cycles, referenced part names, and crop bounds. Rendering does not require a `jsonschema` dependency.

Common optional fields:

| Field | Meaning |
|---|---|
| `profile` | One JSON profile path, relative to the scene JSON. Objects merge recursively; arrays and scalar values are replaced by scene values. Nested profile includes are rejected. |
| `base_dir` | Asset root relative to the scene file; default is its directory. Absolute paths are supported. |
| `output` | Output path relative to the scene file. `--out` overrides it; the command-line path is relative to the shell's current directory. |
| `fps` | Positive export frame rate, default 30. Punch and mesh also use it to generate their frame grid. Rig/pant/camera hold durations remain authored milliseconds. |
| `out_size` | Positive integer `[width,height]` for modes that expose an output resize: rig, room, pant, camera. |
| `canvas` | Output canvas for punch/mesh; actual source canvas for camera. |
| `bg` | RGB/RGBA background for rig, camera, legacy pant and globe. Mode-specific defaults are described below. |
| `preserve_alpha` | Supported by rig, camera and legacy pant. Default is true when their RGBA `bg` has alpha below 255. Explicit false requests RGB. |
| `preset`, `provenance`, `notes` | Descriptive metadata; they do not choose engine branches or execute instructions. |

Asset paths inherited from a profile still resolve relative to the **scene JSON**, not the profile file. `--assets DIR` replaces `base_dir`. Relative asset paths keep their subdirectories; historical absolute asset paths are explicitly remapped to `DIR/basename` under this override. Existing Unicode filenames are resolved without renaming them. The legacy `out` key is accepted as a fallback for `output`.

Globe, room, punch, mesh and modern pant currently render opaque frames. They reject requests for alpha output. Rig/camera/legacy pant PNG sequences preserve RGBA; GIF and MP4 flatten alpha against `bg` RGB. Set the desired background explicitly when exporting a transparent scene to those formats. No renderer assumes that an aligned joint can fill missing painted shoulder overlap.

## Rig

The rig uses a shared transparent source canvas. Pivots and anchors are measured in source pixels. Camera rectangles are **xyxy**: `[left,top,right,bottom]`.

```json
{
  "version": 1,
  "mode": "rig",
  "output": "preview",
  "out_size": [64,64],
  "bg": [0,0,0,0],
  "parts": {
    "body": {"file":"body.png", "pivot":[32,40], "z":0},
    "arm": {"file":"arm.png", "pivot":[40,24], "parent":"body", "z":1,
            "anchors":{"wrist":[52,32]}}
  },
  "frames": [
    {"ms":80, "camera":[0,0,64,64], "layers":{}},
    {"ms":80, "camera":[0,0,64,64], "layers":{"body":{"dx":3}, "arm":{"rot":-8}}}
  ]
}
```

Each part requires `file` and `pivot`. Optional part fields are `parent`, numeric `z`, `visible`, `blend`, named `anchors`, and `role`. `role: guide` or `diagnostic` excludes that image from production composition. Supported blends are `normal`, `screen`, `multiply`, and `overlay`.

Each frame contains a `layers` object keyed by part name. Missing layer values use identity/defaults for that frame, not the previous frame's values. Supported transforms: `dx`, `dy`, `rot` in degrees, `scale`, `sx`, `sy`, `visible`, `opacity`, `z`, `blend`, `parent` and an optional full invertible 3×3 `matrix`. A `turn` object contains `axis_x`, `axis_y`, `theta` and optional positive `focal` (default 600). Turn is applied after affine inheritance; it is not automatically inherited by children in the legacy contract.

`substeps` is a list of partial layer dictionaries merged over that frame's `layers`; rendered samples are temporally averaged. `camera_substeps` is a list of xyxy crop rectangles. `camera` defaults to the full source canvas. `ms` defaults to 80. All crop rectangles must fit the source canvas. `out_size` defaults to `[980,556]`; author it explicitly to preserve the intended aspect ratio.

For keep-world attachment, call `core.rig_tree.reparent_layers(parts,layers,child,new_parent)` before storing the returned frame layers. It writes an explicit local matrix and preserves shear. `parent:null` detaches. Carry the returned state into subsequent frames when needed. Use `align_anchor` only when the shot intentionally aligns an anchor to a target point. There is no implicit snap or inferred anatomy.

Optional `probes` entries use `{"name":"joint","point":[x,y],"parts":["body","arm"]}`. `--probes` saves legacy affine values and separate `rendered_probes` that include perspective division.

The authored [force contact](../examples/force_contact.json), [knuckle turn](../examples/knuckle_turn.json), and [depth turn](../examples/hand_turn_depth.json) examples require the original missing PNGs. Their numeric data is retained; they are not bundled rendered demonstrations.

## Punch

Choose either [heavy](../presets/punch_gpt_heavy.json) or [fast](../presets/punch_claude_machinegun.json) as a data profile. The fast profile retains historical fast timing and body jitter, with the documented topmost-line/temporal-blur corrections; it is labeled an adapted profile, not an original-art visual golden.

```json
{
  "version":1, "mode":"punch",
  "profile":"../presets/punch_gpt_heavy.json",
  "assets":{
    "body":"body.png",
    "fists":["fist_1.png","fist_3.png","fist_2.png","fist_4.png"],
    "speedline":"speed_line.png"
  }
}
```

`assets.fists` order must match the profile's `fists` metadata, whose entries contain `side` and source-canvas `centroid`. `side` names a measured point in `shoulders`. New artwork needs its own measured metadata; copying the supplied coordinates cannot calibrate a different drawing.

`punch` exposes `count`, `step_frames`, `duration_frames`, `perspective_scale`, `end_overshoot`, `initial_scale`, `ease_power`, and `fade_start` (null disables late fade). `body` exposes horizontal/vertical brace amplitudes, their frequencies, and `round_position`. `camera` exposes positive `zoom_end` and `ease: cubic_out|linear`. `motion_blur` uses `type: temporal_substeps`, positive `substeps`, and nonnegative `shutter` in frame units.

`speedline` supports `enabled`, `z_order: topmost|background`, positive `pulse_interval_sec`, and a per-frame `visible_envelope_frames` list in 0…1. The period is rounded onto the frame grid; omitted envelope frames are off. `full_screen_flash:true` is rejected. A disabled line layer does not require an image. Original heavy rendering keeps the line layer before the whole-scene camera transform and locks pulse strength over the temporal samples.

## Mesh and beat grid

Use [dance_half_time](../presets/dance_half_time.json) with `mode: mesh` and `assets: {"poses":[...]}`. Every pose must have the same source canvas. The profile supplies `canvas`, `fps`, `bpm`, `beats_per_pose`, and `sequence`. Sequence rows are `[one_based_pose_number,motion_name,strength]`.

Available motions: `none`, `shakeR`, `shakeL`, `clapR`, `clapL`, `cross`, `pulse`, `breathe`, `pop`, `leanR`, `leanL`, `reachR`, `reachL`, `final`, `waveR`, and `waveL`. Their inherited curves remain in `core.mesh_warp.motion_params`. Pose swaps are hard cuts. Absolute boundaries use `round(offset_ms * fps / 1000 + k * 60/bpm * beats_per_pose * fps)`.

`offset_ms` is a finite signed number, default `0`, locating the first sequence beat relative to exported time zero. Positive values hold the initial pose before motion starts; negative values crop already elapsed motion without restarting its phase. A sequence entirely before time zero is rejected. Add the offset **before** rounding each absolute boundary, so fractional intervals remain accurate. Output is still quantized to whole frames (at 30fps, 88.5ms is 2.655 frames and the first boundary is frame 3). For a song whose first beat was measured at 88.5ms, set `"offset_ms": 88.5` in that scene; do not change the neutral default. The renderer does not mux audio.

All source canvases are resized together to the chosen output canvas. There is no per-pose bbox size normalization or horizontal recentering. By default, median baseline translation corrects vertical differences. Set `preserve_baselines` to one-based pose numbers whose original vertical placement should stay, such as an intentional jump. Foot-anchored sway, bend, and breathing are secondary motion within each hold.

## Globe

[globe.json](../presets/globe.json) is a complete parameter template after its `land` and optional `cloud` filenames are replaced or resolved with `--assets`. Land must be an authored equirectangular texture; clouds are a separate RGBA texture. Optional fields: `size`, `frames`, `fps`/`frame_ms`, `light` (nonzero 3-vector), `ambient`, `rim`, `bg`, `cloud_opacity`, and `cloud_relative_speed`.

One sequence covers one land revolution with the endpoint excluded for looping. Clouds at 1.12 advance 12% faster than land; the wrapper passes only the relative difference to the lower-level sampler. Other rotation trajectories can use `core.sphere.render_globe` directly; the scene CLI does not implement `spin_start`, `spin_turns`, or the superseded `cloud_drift_turns` field.

## Folded room

[stadium_run](../presets/stadium_run.json) is the selected panel set for the supplied 1200x1600 stadium sheet, visually checked on 2026-09-25. [stadium_floorfix](../presets/stadium_floorfix.json) is retained as historical data and is obsolete for this sheet because it includes large outside white margins. Required fields: `panel_sheet`, `panels` with explicit `far`, `left`, `right`, `near`, `floor`, and `pose_files`. Each panel is an xyxy rectangle or `{"box":[...],"rotation":degrees}`. Panel crops must fit the supplied sheet.

Optional `room` dimensions are `width`, `depth`, `height`. `camera_start` and `camera_end` contain `eye`, `target`, and vertical `fov`. `out_size`, `frames`, `frame_ms`, `slices`, RGBA `background`, and `camera_bob` control delivery and rendering. `pose_schedule` entries are `{at:0…1,part:zero_based_pose_index}` and must start at zero. The billboard always faces the camera.

`actor` may set `strides`, `height_start`, `height_growth`, `pose_phase`, `x`, `sway`, `bob`, `z_start`, and `travel`. The shared renderer uses the inherited Claude camera convention and smooth camera interpolation. Actual near-plane clipping retains visible portions of walls/floors even when other corners are behind the eye. Use `slices: 1` for the box; larger historical slice counts remain supported but are unnecessary for clipping. There is no general depth buffer, ceiling, or independent second room actor. Painted white margins and views outside/above the box remain visible as authored.

## Panting

[pant_steam_v3](../presets/pant_steam_v3.json) supplies the authored breath/secondary-motion data. Modern pant scenes require a `background` image and `actors`. Each actor has:

- `files`: part-name → supplied image filename.
- `profile`: `parts` mapping `body1`, `body2`, `head`, `hair` to those names; measured `neck`, `crown`; optional phase, body_ratio, hair_rotation_ratio; and `breath` rows `[body_pose,head_dy,hair_dy,tilt,ms]`.
- Optional `steam` artwork and either a supplied `mask` image whose alpha is used, or explicit `side: left|right` for the authored diagonal panel mask.
- Optional `steam_phase`, `steam_delay`, and `steam_parameters` containing `rise`, `grow`, `wobble`, `peak_opacity`. Steam period follows breath-cycle length.

All actors use the same nonempty cycle length and source canvas. The first actor's authored durations determine the timeline. Global options: positive `breaths`, `out_size`, `front_haze`, deterministic `seed`, and `panel` values `line_x0`, `slope`, `half`. `divider` adds a supplied topmost layer; `divider_background` extracts its line against the clean background. Back steam precedes actors, optional low-opacity haze follows them, then the divider.

Legacy pant JSON is detected when `parts` maps names to strings and `frames[*].layers` is an ordered list. It receives `mode: pant`, `format: legacy_layers`. Only the named layers render in their list order. Layer keys: `part`, `dx`, `dy`, `rot`, `pivot`, `scale`, `opacity`. Rotation preserves the original Pillow sign, which differs from rig matrix rotation. `crop` is xyxy; `height` preserves its aspect ratio unless `out_size` is explicit. Original `ms` holds are retained. This adapter does not silently reinterpret list layers as a rig hierarchy.

## Camera shot

[camera_reveal](../presets/camera_reveal.json) is a one-scene camera template. Required fields are `canvas`, `parts` (name → filename or `{file,blend}`), static `layers` in draw order, and `shots`. All supplied camera parts use the declared source canvas. Optional `out_size` controls the output; default is the source canvas.

A shot's `frame_start` and optional `frame_end` are **xywh**, unlike the rig's xyxy camera. Supported controls are `frames` (at least 2), `frame_ms`, `easing: smooth|ease_in|ease_out|ease_in_out|linear|snap`, `ease_power`, `hold_in`, `hold_out`, `overshoot` in 0…0.08, `motion_blur`, and `blur_steps`. `snap` is linear spacing over the authored short frame count. Frame duration stays constant within a shot. The entire camera trajectory, including temporal samples, must stay inside the canvas.

`swap: [{"at":0,"part":"head_down"},{"at":0.7,"part":"head_up"}]` adds the selected pose after static layers; start at zero. `exposure: [start,end]` multiplies world RGB after camera sampling, leaving alpha unchanged.

Effects are explicit arrays in each shot:

```json
{
  "world_effects":[{"part":"smoke","blend":"screen","opacity":0.4}],
  "screen_effects":[{
    "part":"lines", "kind":"speedline", "blend":"normal",
    "pulse":{"pulse_interval_sec":0.5,"visible_envelope_frames":[0.25,0.75,1,0.55,0.18]}
  }]
}
```

Each effect supports `part`, `blend`, `opacity`, `enabled`, `kind: image|speedline`, and optional `pulse`. Speedline kind keys white to transparent while preserving source alpha. World effects compose before crop/exposure. Screen effects resize once to final output size and compose after exposure, so stroke width does not change during the camera move. List order is draw order; place speed lines last. Pulse restarts per shot, uses the shot's actual `frame_ms`, and stays fixed across camera blur samples. `pulse.enabled:false` turns the pulsing effect off.

Historical `punch`, `flash`, `lines`, `pulses`, `frame_via`, `move`, and `layer_order` are not automatic production controls in this scene API. Unsupported shot keys are rejected instead of silently ignored. Author impact effects with explicit effect entries/timing or call lower-level primitives. A guide can be measured with `core.camera_25d.measure_frame`; it is not automatically inferred from arbitrary image colors.

## Helper-only profiles and limitations

`presets/glint.json` is **helper data**, not a CLI scene. `core.secondary.render_glint` additionally needs supplied base/lens/spark artwork, a measured lens mask, and authored darkening/glint timing. Its mask filling and blend primitives are preserved and tested; no `mode: glint` dispatcher is claimed. `floor3d`, `scatter_exit`, and the low-level effect/rig helpers are likewise available through Python without inventing an unsupported scene mode.

The supplied archives contain no original PNG/GIF/MP4 artwork. Template filenames are explicit missing inputs, not bundled assets. Synthetic regression fixtures verify coordinates, color/alpha, timing and composition. Original-art appearance, shoulder overlap and large-turn silhouettes still require the artist's supplied parts and accepted reference renders.
