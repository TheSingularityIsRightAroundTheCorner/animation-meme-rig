# GPT archive audit

Audit date: 2026-09-24. Scope: every file under `sources/gpt`, including the three files inside the nested ZIP. Source documents are historical evidence, not new task instructions. Source files were not modified.

## Findings and evidence strength

- The latest executable punch implementation supplied is `punch_barrage_speedline_topmost.py`. Its topmost line pulse, heavy body amplitudes, punch timing, temporal shutter samples, push-in and representative GIF palette are concrete code, not just narrative claims. The exact original rendered GIF/MP4 and PNG assets are absent; original-art visual equivalence cannot be certified from this archive.
- `punch_barrage_rig_v2.py` and `build_tera_globe.py` contain comments only. They are not working renderers despite their filenames.
- `stadium3d_floorfix.py` provides a concrete corrected floor mapping. Preserve it when combining with Claude's complete room shot renderer.
- Parent/child specs and numerical probes are supplied, but `rig_tree(2).py` and all referenced prepared PNG work directories are absent. Probe coordinates establish some hierarchy behavior, not the visual quality of missing rendered output.
- Knuckle-turn spec uses finite-camera turn parameters, but contains no animated z values. It hard-swaps front to side at frame 27. Its probes ignore perspective projection: at frame 26 a front anchor remains `[241.5,117]` even with theta -78 degrees. Do not count these probes as proof of projected side alignment or depth crossings.
- The nested ZIP contains byte-identical copies of the outer punch Python, params JSON and handoff. It is packaging, not a later implementation.
- All seven top-level Python files parse successfully. All eleven JSON files parse successfully. Syntax success does not resolve missing assets or engine imports.

## File-level migration table

Paths below are relative to `sources/gpt`. `canonical` means chosen supplied implementation or preset basis; `merge` means selected unique logic or evidence to integrate; `example-only` means shot data/documentation that must not become another engine; `obsolete` means retained only in the source archive/failure history.

| Supplied file | Disposition | Destination / preserved behavior | Evidence / limits |
|---|---|---|---|
| `punch_barrage_speedline_topmost.py` | canonical | Shared punch renderer; extract configuration and remove CLI duplication | 63-94 line extraction/pulse; 116-154 timing/brace; 158-228 rendering; 230-252 temporal samples; 256-290 palette. Not asset-neutral yet: hardcoded fist side/centroid 130-135. |
| `punch_barrage_params.json` | canonical | Heavy punch preset | 8-14 timing/perspective; 25-34 brace/substeps/camera; 36-49 topmost 0.5s pulse. `enabled` and `z_order` currently not read by Python. |
| `punch_barrage_speedline_pulse_v4_params.json` | merge | Proven pulse envelope and no-flash regression evidence | 12-24 duplicates final preset; absolute effect path absent; no matching v4 executable supplied. |
| `punch_barrage_rig_v2_params.json` | merge | Exact fist order into heavy preset, then archive duplicate schema | 21-25 order 1,3,2,4; timing matches final. |
| `punch_barrage_rig_v2.py` | obsolete | Historical note only | All 12 lines are comments; executable said to exist only in prior conversation. |
| `punch_barrage_flash_v3_params.json` | obsolete | Failure fixture/documentation, never production default | 9,12 explicitly request full-screen flashing; superseded by line-only pulse. |
| `mesh_dance_test.py` | merge | Row warp, exact secondary-motion presets, fractional beat boundaries and example sequence | 87-108 warp; 119-244 presets; 247-273 sequence/timing. Import-time rendering and fixed paths must be removed; first-frame palette 328-331 must be replaced. |
| `stadium3d_floorfix.py` | merge | Correct panel crops plus shared projection/quad/billboard functions | 23-30 center wood floor vs near crowd; 34-81 camera/project/quad; 83-130 strips/billboard. Hardcoded crops remain a shot preset, not automatic panel inference. |
| `run25d_camera_box_params.json` | example-only | Explicit camera endpoints and pose schedule | 5-29 start/end; 31-34 schedule .4/.72; source basis `build_run_shot(1).py` absent under that name. |
| `tera_globe_params.json` | merge | Globe preset used with supplied Claude sphere engine | 8-16 lighting, cloud opacity and 1.12 relative speed; source textures absent. |
| `build_tera_globe.py` | obsolete | Historical intent only | Eight comments, no implementation. |
| `claw_catch_parenting_test_spec.json` | example-only | Early catch sequence and hierarchy fixture | 24 frames, 12 parts; attack arm changes parent at zero-based frame 16 (line 909). No rendered output/probe file. |
| `run_claw_catch_test.py` | obsolete | Replace with shared CLI against preserved example spec | 3-4 hardcoded missing `/mnt/data/rig_tree(2).py` and spec path. |
| `cut37_parent_child_force_v3_spec.json` | example-only | Most complete supplied catch-force shot spec | 28 frames,13 parts; reparent at frame17 (1074); arm local dx/dy/rot become zero; caught body may move independently. |
| `cut37_parent_child_force_v3_probe.json` | example-only | Numerical output fixture | 28 records; contact error exactly zero from frame17 onward; arm/claw chain error zero all frames. Values rounded to one decimal, so use appropriate comparison tolerance. |
| `claw_turn_knuckle_rig_spec.json` | example-only | Staggered anchored extension, finite turn and authored side pose | 52 frames,8 parts; wrist `[111,56]`, focal420, theta0→-78; front-to-side swap at frame27. No dynamic z field, no transition alignment correction. |
| `claw_turn_knuckle_rig_probe.json` | example-only | Affine anchor-coincidence output fixture | 52 records; front and side anchor pair errors zero. Does not include projective effects. |
| `run_claw_turn_knuckle_rig.py` | obsolete | Replace with shared CLI against preserved example spec | 4-5 missing hardcoded engine/spec paths. |
| `ASTRA_HANDOFF.md` | example-only | Provenance and rule evidence | 3-10 reports working punch behavior; 14-25 records behind-fist speed-line error and correction. |
| `ASTRA_MASTER_HANDOFF.md` | example-only | Failure register, desired architecture and unresolved limitations | Contains requested improvements as well as claims of past success. Do not represent all proposed capabilities as already implemented. |
| `astra_punch_barrage_handoff.zip` | obsolete | Immutable source archive only | Three members; all equal outer counterparts byte-for-byte; timestamps 2026-09-23 18:15:16. |
| `astra_punch_barrage_handoff/punch_barrage_speedline_topmost.py` | obsolete | Duplicate of canonical candidate | Exact byte duplicate verified. |
| `astra_punch_barrage_handoff/punch_barrage_params.json` | obsolete | Duplicate preset | Exact byte duplicate verified. |
| `astra_punch_barrage_handoff/ASTRA_HANDOFF.md` | obsolete | Duplicate documentation | Exact byte duplicate verified. |

## Primitive selection

| Primitive | Selected supplied basis | Preserve / reconcile |
|---|---|---|
| Punch barrage | final topmost GPT Python + final params | Duration6.5, step3, count10, scale `0.48 + 8.9*p`, power1.65, overshoot1.85, late fade t>.88, body .7/1.4px, camera end .78. Keep machine-gun style separately when porting Claude values. |
| Temporal blur | GPT punch samples | Four backward-looking samples over shutter .70 frame; pulse frame index fixed across substeps. Camera still moves across substeps. |
| Speed-line pulse | GPT `build_speedline_overlay`, `pulse_strength` | Darkness alpha×source alpha×1.35; black RGB. 15-frame period at30fps; envelope [.25,.75,1,.55,.18], remaining frames0. |
| Global GIF palette | GPT punch exporter | Representative sample of up to8 evenly spaced frames;255 colors; same palette all frames; no dither. Do not reuse mesh's first-frame-only palette. |
| Foot-anchored mesh | GPT mesh row warp | t clamped from bottom to top; smoothstep sway + sin(pi*t) bend; y scaling around foot. Preserve exact preset amplitudes. |
| Beat grid | GPT mesh boundary formula | BPM189.9, half-time `60/BPM*2`; absolute boundary `round(k*frames_per_interval)`. |
| Parent hierarchy/contact | GPT v3 spec/probe + Claude rig engine candidate | Inheritance and chain tested numerically; generic pose-preserving reparent/anchors are requested fixes rather than demonstrated implementation. |
| Hand turn | Claude finite-camera implementation (cross-audit) + GPT authored timing | GPT spec alone lacks depth-sort crossing and alignment, so do not promote it as a fully solved endpoint. |
| Folded room | GPT corrected floor crop + Claude complete builder | Never infer floor from position/memory; explicit semantic JSON roles. |
| Globe | Claude sphere + GPT globe preset | Equirectangular map, light, separate clouds advancing1.12×, configurable dark background. |

## Documented failures → regression expectations

Each row must have a test before changing the relevant implementation. Asset-dependent appearance checks need supplied hand-drawn assets; numerical/synthetic fixtures can test the invariant now.

| Failure ID | Source evidence | Concrete regression expectation |
|---|---|---|
| GPT-F01 shoulder/arm gaps | Master97-128 | Named joint world positions within ≤0.5px after transform/reparent; differing source pivots use explicit anchors; world transform unchanged at keep-world parent switch. Requires artist overlap check on original PNGs. |
| GPT-F02 teleport on reparent | Master103-126 | Moving/rotated/scaled new parent: child world matrix unchanged at switch; subsequent parent delta inherited; nested descendant also continuous; detach/reattach and cycle rejection included. |
| GPT-F03 contact reads soft/equal shaking | Master130-141 | Fixed or tiny-amplitude aggressor root, shared locked contact point, restrained caught-body shake does not move captured arm independently; v3 zero local arm commands after frame17 preserved. Forcefulness still needs visual review. |
| GPT-F04 speed lines behind fists | Handoff14-25,Master229-232 | On an overlapping test pixel the opaque line color wins over the fist; default effect composited last; explicit alternate order only if requested. |
| GPT-F05 full-screen flash substituted for pulse | Master254-256,508-509;flash_v3 JSON9-12 | Line-only pulse leaves non-line pixels unchanged; outside five visible envelope frames effect absent; repeats at .5s; `enabled=false` must disable line effect independently. |
| GPT-F06 flat-card hand turn | Master283-302 | At finite focal distance equal near/far offsets show asymmetric projected magnification; sprite rotate/width squash is insufficient; depth crossing reverses stable draw order. |
| GPT-F07 claws emerge at wrong origin | Master304-315 | sy growth leaves knuckle pivot fixed; first/middle/outer appear sequentially; source sequence first visible front claws at7,12,17, side retractions end37,42,47. |
| GPT-F08 side-view endpoint pop | Master317-324 | Authored projected endpoint and side anchors align within pixel threshold when explicit side alignment supplied; transition continuous. Existing spec does not solve this; mark manual-art calibration limitation. |
| GPT-F09 crowd used as floor | Master375-404;floorfix20-30 | Explicit floor crop is(320,680,870,960), near crop(285,930,860,1245); color-coded semantic fixtures prove wall/floor assignments cannot be silently exchanged. |
| GPT-F10 GIF48-color banding/frame0 palette | Master486-497;mesh328-331 | Palette draws representative samples across shot with255 colors; later unique colors represented; every frame quantizes through same palette. RGB/MP4 validation path retained. |
| GPT-F11 generated storyboard/replacement art | Master501-515 | Renderer uses only provided asset paths and deterministic transforms/effects; source hand-drawn asset hashes unchanged; no image-generation dependency or automatic substitute fallback. |
| GPT-F12 timing drift from step rounding | mesh12-14,268-273 | boundaries equal round(k*HALF_FRAMES); endpoint error≤.5frame for long sequence; do not accumulate rounded per-interval step. |
| GPT-F13 pose size/x alignment changes | mesh15-16,62-80 | Common canvas resize only; no per-pose bbox-width normalization or bbox-x-centering; source horizontal composition preserved. |
| GPT-F14 unwanted blends/foot drift/over-breathing | mesh17-20,87-108,171-177 | Hard pose cuts; warp field at foot y has zero x/y displacement; breathing amplitudes remain sway1px and vertical .009. Intentional jumps require explicit authoring; current baseline normalization has no jump override. |

Additional observed implementation defects: punch ignores `speedline.enabled`; unknown z-order/type fields silently ignored; input validators missing for blank fists, zero substeps, bad sizes and zero-duration punches. These are code findings, distinct from historical documented failures. They should get targeted tests if fixed.

## Outputs and missing inputs

The only supplied GPT outputs are two JSON probe files. No PNG, JPG, GIF or MP4 is included. File comments and handoff success statements are secondhand visual evidence. Review cannot certify original-art fidelity without the missing art/outputs.

- Punch: one body + four fist PNGs and speed-line PNG absent. Final script accepts paths but centroids still depend on the original source canvases.
- Mesh dance: `p01.png`…`p13.png` absent. Script loads and renders on import, so source must be inspected without importing.
- Catch: `claw_catch_rig_work/`12 PNGs and `cut37_rig_v3_work/`13 PNGs absent; later engine`rig_tree(2).py` absent.
- Hand turn: `claw_turn_rig_work/`8 PNGs absent; later engine absent.
- Globe: `tera land.png`, `tera cloud.png` absent; `sphere.py` exists in the Claude archive, not GPT.
- Folded room: `stadium parts.jpg` and run poses absent; full builder exists in Claude archive with a different filename than source_basis.
- Dependencies: Pillow,NumPy,OpenCV for mesh/room; ffmpeg for MP4. No dependency lock or version information was supplied.

## Numerical output audit

`cut37_parent_child_force_v3_probe.json`:28 records,zero-based frame0…27. Before contact, pair error varies as expected during approach (maximum42.190px at9); at16 error0.5px; from17…27 error0.0px. Nested arm→claw3 point error0.0px for every frame. This supports locked inheritance after contact, not shoulder appearance.

`claw_turn_knuckle_rig_probe.json`:52 records,zero-based frame0…51. Both hand/claw anchor pairs match exactly throughout. Projective `turn` has not been included in probe coordinates; original rendered alignment remains unproven. At26 front wrist is[261,56], next frame's side wrist[273,58], which documents a12px/2px authoring mismatch before any new alignment logic.

Cross-audit verification by root: supplied Claude `rig_tree.world_matrices` reproduces all80 supplied GPT probe records with exactly0.0 error after matching the output rounding. This establishes that the available Claude engine is sufficient for those affine output fixtures even though the named `rig_tree(2).py` is missing.
