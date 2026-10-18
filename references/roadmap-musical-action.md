# Musical × action roadmap

**Status: design proposal (2026-10-18). Nothing in this file is implemented unless a section says so. Do not author scene fields from it; the current contract is [spec.md](spec.md).** It records decisions from a design session so later sessions extend the engine instead of rebuilding rigs.

Goal: hand-drawn actors are drawn once and reused across shots (musical numbers, fights, prop handling, turns). Code assembles, times, films and adds effects. New drawings are requested only where the rig cannot produce the pose.

## Order of work

| Step | Builds | Accept when |
|---|---|---|
| P0 | Screen-space renderer | Existing rig renders match within a stated tolerance; per-frame time at 1080p is logged |
| P1 | Hierarchical depth, clip/cut masks, ordering-cycle report | A hand–sword sandwich composites correctly while the arm passes behind the body |
| P2 | Sockets, attach state machine, contact QA | Gemini v2's tie tug is reproduced as a pin constraint and compared with its accepted render |
| P3 | Line-weight compensation | Comparison sheet from scale 0.06 to 0.5 on supplied art |
| P4 | Multi-view turn rig | 180° look-back: shared-anchor error at the swap below 1 px, tie motion continuous |
| P5 | Two-bone IK | After arms are drawn as upper arm / forearm / hand |

## P0. Screen-space rendering

Current: `rig_tree.compose_frame` warps every part image over the full shared canvas (up to 10871×5000 for the supplied characters), then `crop_frame` crops and resizes. Cost grows with canvas area times part count. This is the out-of-memory path that tempts an agent to rebuild a rig instead of reusing it.

Proposed:

- Store parts as bbox crops with an offset. The character archives' `assets.json` already records `bbox`.
- Concatenate camera, world and offset into one matrix `M = C · W · T(bbox)` and sample each part directly into the output frame.
- Keep a per-part pyramid (1, ½, ¼, ⅛) and sample the level that matches the local scale.
- Expose the per-part screen scale `s = sqrt(|det J|)`, where `J` is the linear part of `M` (or the homography Jacobian at the part centre). Line weight, detail culling and view selection all read this one number.
- Keep each frame a pure function of time, so frames render in parallel and resume after interruption. Simulated secondary motion is computed once per shot, cached and sampled.

## P1. Occlusion

**Hierarchical depth.** Replace the flat `z` with a group path. The sort key is the tuple of z values from the root group down to the part.

```
body              z 0
arm_R group       z +1
  arm             0
  hand_back       1
  sword           2   (joins the group while held)
  fingers_front   3
```

Moving the arm behind the body changes only the group's z, so the hand–prop sandwich moves as one unit. This is the idea behind Harmony composites, Spine draw order and Unity Sorting Groups.

**Ordering cycles.** Collect "A over B" pairs for each pose and sort them topologically. A cycle (A over B and B over A) cannot be solved with depth. Report the part pair and request a split drawing (palm side / fingers) or a mask.

**Masks.** Two layer options. The mask is transformed by its owner's matrix.

- `clip_to: part`: visible only inside that part's alpha (pupils, cloth pattern, painted shadow). `α' = α · M`.
- `cut_by: part`: hidden where that part is opaque. `α' = α · (1 − M)`.

These correspond to Harmony's Cutter and inverted Cutter, Spine clipping attachments and Unity Sprite Mask.

**Swap timing.** A depth swap always pops. Given an allowed window, pick the frame where the two parts' alpha overlap is smallest, or place the swap on a smear or motion-blur frame.

## P2. Holding props

- Sockets belong to each drawing: `hand_grip` and `hand_open` have different palm points. Props carry their own sockets (`hilt`, `pommel`, `tip`; a microphone's `handle`).
- Held transform: `T_prop = T_hand · S_hand_drawing · S_prop⁻¹`.
- States: free (world) → held (hand) → thrown or dropped (world). Enter a state with `reparent_layers` (keep-world), then interpolate to the grip socket over k frames in decomposed form (translation, angle, log scale), so nothing teleports.
- When the hand drawing swaps, the prop moves to the new drawing's socket on the same frame.
- Two-handed sword: the main hand is the parent; the `pommel` socket is the off hand's IK target.
- Contact QA: measure the hand–prop socket distance in screen pixels on every frame; fail above 0.5 px.
- Pin constraint: Gemini v2's `contact_motion` is a character-specific ramp warp. The general form pins the tie knot to the hand socket during the contact window, follows it with `local_mesh`, and keeps the free end's secondary swing.

**IK.** Analytic two-bone solve (law of cosines) with joint limits. A target out of reach or past a limit is reported as "new drawing needed" for that frame range. This needs arms drawn as upper arm / forearm / hand with elbow overlap. The three supplied characters have one-piece arms, so they use pose swaps and local mesh until redrawn.

## P3. Line weight

Raster parts bake their stroke width: screen width = source width × `s`. Harmony avoids this because pencil lines are centreline-plus-thickness vectors whose thickness is recomputed at render time (its Scale Independent, Zoom Independent Thickness and Proportional options).

**Policy.** `w(s) = w_ref · (s / s_ref)^α`, clamped to `[w_min, w_max]` screen pixels.

- α = 1 is the current behaviour; α = 0 matches Harmony's scale-independent mode; 0.3–0.5 is the proposed default.
- Keep separate α values for object scale and camera zoom. Cel practice uses the same pencil at any drawing size, while a camera truck-in enlarges the lines.
- Code effects (slashes, speed lines) specify width in the same units, so they match the actor's line.
- PDoomVideo, a procedural vector video, uses the same shape of rule: `sw = clamp(size / k, min, max)`, plus small details drawn only above a size threshold.

**Experiment** (`scripts/line_weight_probe.py`; GPT head part, 990×1304; target 1.8 px):

- Dark masses (hair, large black shadow) separate cleanly with an opening of radius 14 px and are left uncompensated.
- The median ridge stroke width is about 6 px, fine hatching included.
- Plain dilation restores the contours but fills the eyes at s ≤ 0.10, where they read as sunglasses.
- Gap-protected dilation gives gaps that a closing with the growth radius would fill only 25% of the growth. It keeps the iris readable at s = 0.10 while thickening the contour, nose and ears.
- At s = 0.06 (head about 60 px wide) no compensation preserves the eye detail.

**Tiers by the actor's screen size.**

1. Above roughly s = 0.10: gap-protected thickening. Font rasterizers' stem darkening addresses the same problem for small text.
2. Smaller: fade interior detail strokes and keep silhouette strokes; replace eyes with dot or line glyphs at eye anchors. At a few pixels the style difference is invisible.
3. A hero moment at tiny size: request a simplified far-shot drawing.

**Two paths.**

- Flattened PNG (the supplied characters): thicken only. Thinning needs the colour beneath the line, which flattening destroyed.
- Separated line layer (future drawings): precompute a signed distance field of the line art and a local stroke-radius field. Per frame, warp both and threshold: constant mode `d < δ`, proportional mode `d < R · (k − 1)`. This thickens and thins, antialiases, and can normalise anisotropic squash with the warped field's gradient. It requires flats painted under the lines.

## P4. Turns (needs testing)

- Yaw θ is actor state. A view is a complete small rig at a drawn angle (0°, 45°, 90°, 180°) with its own parts, pivots, sockets, depth groups and masks. 270° may mirror 90° with asymmetric patches (ID card side, hair part).
- Between views, apply the residual `Δ = θ − θ_view` with the existing `turn` homography plus per-part depth parallax: `x' = x_axis + (x − x_axis) · cos Δ + d · sin Δ`, with d > 0 for the nose and near arm and d < 0 for the ears and far arm. The usable range without new drawings is estimated at ±20° and has not been tested.
- Swap to the nearest view with hysteresis. Align a shared anchor (neck or pelvis) at the swap with `align_anchor`. Above roughly 30° per frame, skip intermediate views and smear.
- Secondary motion state (tie angle and velocity) belongs to the actor, not the drawing, so it survives view swaps; mirrored views flip its sign.
- Required drawings follow from θ(t): views held on screen for two or more frames need art; views passed faster can be smears.
- A camera orbit uses `θ_eff = θ_actor − θ_camera`.

## Drawing preparation for new artwork

1. Export a PSD group per part with `line`, `flat` and `shadow` layers; flats extend under the lines.
2. Draw hands separately from arms. Draw a gripping hand as two layers: the palm side behind the prop and the fingers in front.
3. Minimum hand set: open, fist, point, cylinder grip (sword and microphone), pinch (tie).
4. Mark sockets with coloured dots on a guide layer and extend the colour-guide measurement in `camera_25d.measure_frame` to read them.
5. Split arms meant for IK into upper arm and forearm, with elbow overlap.
6. Views in priority order: side, back (one piece is fine), three-quarter.
7. Record the pen width in source pixels as `w_ref`.

## Borrowed from PDoomVideo

[JohnHeibel/PDoomVideo](https://github.com/JohnHeibel/PDoomVideo) is a fully procedural p5.brush music video with no supplied artwork, so its characters and look do not transfer. Its production structure does:

- Every frame is a pure function of song time, which makes rendering parallel and resumable.
- Expressions never snap. `mood()` squints shut, plays a squash-stretch take, pops an emote and then opens the new eyes. The same transition fits head-drawing swaps.
- A beat-locked motion library (`move(style, t)`: bounce, hop, sway, spin, stomp, shimmy and more) is built on one beat function with an offset; it maps onto `beat_grid`.
- Line boil: hand-drawn jitter reseeded 12 times per second. For raster parts, a small smooth displacement reseeded on twos or threes may make cutout motion read as hand-drawn. Not yet tested.
- Stroke weight is clamped by size, and details are drawn only above a size threshold.
- Workflow: a storyboard document, a style guide for parallel subagents, one file per shot, shared code read-only (bugs are reported, not edited), and contact sheets that print milliseconds per frame.

## Prior-art map

| Need | Harmony | Spine / Unity 2D | Cel animation | Here |
|---|---|---|---|---|
| Depth groups | composites | draw order / Sorting Group | cel levels, BOOK, overlay | P1 hierarchical depth |
| Masks | Cutter | clipping attachment / Sprite Mask | mattes | P1 `clip_to`, `cut_by` |
| Drawing swap | drawing substitution | skins and attachments / Sprite Resolver | replacement drawings | existing swaps plus per-drawing sockets |
| IK | IK tool | IK constraint / 2D IK limb solver | none | P5 |
| Line weight | pencil-line thickness modes | none; raster at a mostly fixed scale | same pencil at any size | P3 |
| Limited timing | exposures | not applicable | on ones, twos and threes | per-layer stepping; not implemented (see [runtime notes](runtime.md)) |
