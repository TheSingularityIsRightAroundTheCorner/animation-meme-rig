---
name: animation-meme-rig
description: >-
  Rig and animate supplied hand-drawn PNG parts with Python: reusable parent-child motion, anchored and localized mesh deformation for flattened PNG mouth/hand acting, comic reaction timing, punch timing, layered effects, finite-camera turns, globes, and folded-room camera shots. Use for code-driven animation from existing artwork, including requests such as 리깅해줘, 파츠 애니메이션, 애니밈 만들어줘, and 움티. Not for generating or redesigning artwork.
---

# Animation Meme Rig

Use one shared Python engine with shot data and motion profiles. This skill works from a filesystem and Python with any agent; it does not depend on a particular assistant, API, or cloud workspace.

## Start from the supplied art

Inspect the PNG alpha, shared canvas sizes, pivots, anchors, and requested framing before rendering. Preserve source files. Resolve existing Unicode filenames without renaming them; use English names for new outputs. Missing artwork is a missing input: do not generate replacement characters, storyboard sheets, or invented poses. Synthetic test fixtures are geometry, not replacement art.

Use the closest existing primitive and edit JSON data before changing core code. Keep character identity, measured coordinates, and motion style in profiles. A heavy barrage and a fast barrage share an engine but keep distinct timing. Project-specific dialogue, captions, music, and publishing rules stay with the project.

## Choose the entry point

- Run `python scripts/render.py --help` for the common renderer and validation commands. Paths inside a spec resolve relative to that spec, never a previous assistant's `/mnt` directory.
- Read [the spec reference](references/spec.md) for inputs, coordinate systems, legacy adapters, and runnable examples.
- For unseparated mouth/hand acting, typing, nodding, trembling, angry/excited stretch, comic zooms, horizontal reveals, and safe ending framing, read [comic acting](references/comic-acting.md). Reuse `core/local_mesh.py`; keep measured regions and timing in shot profiles. `scripts/render_comic_preview.py --help` runs a small mouth preview, not an automatic full-scene rig.
- Read [primitives](references/primitives.md) when authoring anchors, camera motion, turns, or effects.
- Read [migration](references/migration.md) when changing an inherited implementation or choosing between historical variants. Detailed audit evidence and regression coverage ship in `references/audit/`.
- Read [runtime notes](references/runtime.md) for Claude or another read-only/ephemeral host, explicit output paths, and efficient numeric-first QA. Agent UI metadata is optional; use this same engine on every host.
- `examples/force_contact.json`, `knuckle_turn.json`, and `hand_turn_depth.json` preserve the authored attachment/turn sequences. Supply the original PNGs via the CLI asset-directory override. They are measured shot examples, not generic calibrations for new drawings.

## Preserve these behaviors

1. **Attachment:** parent motion propagates through descendants. Use explicit named anchors and keep-world reparenting for contact changes; retain overlap in the drawing. Joint coincidence alone cannot fill missing shoulder artwork.
2. **Turning:** establish whether the camera, object, or background plane moves. Describe which way the front face travels. A finite-camera turn makes the near side grow and the far side shrink. A silhouette squash cannot establish direction. Projected anchor diagnostics and affine legacy probes have different meanings.
3. **Effects:** speed lines default to the topmost layer and pulse independently. A line pulse must not become a white flash. Preserve source alpha. Choose normal/screen/multiply explicitly; filenames may suggest a role but do not override an explicit spec. World-space effects move with the camera; screen-space effects keep their stroke width.
4. **Timing:** use temporal substeps for motion blur, keeping the effect pulse locked to the final frame. Camera ease uses spacing with constant frame durations. Panting may deliberately use authored holds. Beat boundaries are rounded from absolute fractional positions, including the song's `offset_ms`, not repeated rounded intervals. Measure the first downbeat; the default offset is zero and no song-specific value is universal. Pose swaps are hard cuts unless a transition is explicitly authored.
5. **Environment:** provide semantic panel crops explicitly. Do not infer which rectangle is the floor. Keep panel rotations, camera endpoints, pose swaps, and billboard facing in the shot data.
6. **Delivery:** inspect RGB PNG frames before accepting compressed output. GIFs use one palette sampled across the entire shot. Use PNG sequences for alpha and MP4 for ordinary playback. QA warnings are review prompts; intentional effect lines and borders are not automatic failures.

## Validate changes

Run `python -m unittest discover -s tests -v` from this skill folder after an engine change. Add a behavioral regression before fixing a newly observed failure. Compare unchanged behavior against reference implementations and numeric fixtures; do not replace goldens just to make a test pass. For art-dependent changes, render contact, transition, first/last, and impact frames and inspect them at delivery size.

The supplied archives contain numeric probe outputs but no original PNG, GIF, or MP4. The migration proves synthetic and numeric behavior; it does not certify missing artwork. Use original parts and accepted renders for the final visual comparison. A large 2.5D body/face turn can require an artist-drawn pose, and aligned anchors do not guarantee matching silhouettes.
