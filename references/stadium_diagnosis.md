# Stadium wall diagnosis — 2026-09-25

The wall disappearance is a geometric rejection defect, not a JPEG transparency problem. In the inherited renderer, `if (z < 0.05).any(): return None` rejects an entire panel as soon as one corner crosses the near plane. The side-wall subdivision cuts along wall height, so all 14 pieces can fail together. In frame 17 of the supplied restaged shot, both left and right walls have visible positive-depth corners but all 14 slices of each are rejected. The floor loses visible foreground regions for the same reason.

The GPT variant has the related defect: it requires at least three positive-depth corners and clamps negative depth before fitting its warp. It does not perform polygon clipping. This is separate from its wider crop rectangles, which include large exterior white margins and have different rotations.

## Verified against supplied art

- Sheet: 1200x1600 RGB JPEG. Matching original RGBA pose files were available locally as `angle 1.png`, `angle 2.png`, `angle 3.png`.
- Supplied shots: 42 frames / 900x506 / 2.94s, 42 frames / 900x506 / 2.94s, and restaged 48 frames / 960x540 / 2.88s.
- Reproducing the pre-fix restaged render differs from the supplied GIF by only 0.30-0.48 mean RGB levels on sampled first/middle/last frames; it reproduces the missing walls. This is not a byte-identical GIF claim.
- Re-encoding the decoded JPEG pixels as PNG gives pixel-identical corrected first and last frames. Changing the file extension cannot fix the geometry.
- The `stadium_run` wall crops match this sheet substantially better. Near-white pixel percentages (all RGB channels > 240) in `floorfix` are 28.77% far, 31.15% left, 34.01% right; these include both outside margins and legitimate white art. `stadium_run` retains some painted white edges and is not an automatic border-removal solution.
- GPT is drawn inside pose 3. It has no independent world position in the current single-billboard room mode. Two-actor staging is a separate feature and was not added for this fix.

## Narrow correction

Clip the camera-space polygon at depth 0.05 before dividing by depth. Retain original UV placement using a homogeneous texture mapping; mask at output pixel centres. Preserve the exact old warp for polygons already fully in front. The box works with `slices: 1`, while historical subdivision remains supported. Actual artwork, camera path, actor path, room dimensions, timing and crop coordinates were unchanged in the comparison.

Fully behind-camera geometry should remain invisible. An open-top box can expose the background above its walls. Painting/trim margins persist in the textures. Painter ordering and a final overlaid actor are not a z-buffer, so clipping does not guarantee correct arbitrary intersecting geometry or multiple-actor occlusion.

Seven new regressions were recorded before refactoring. The full 126-test result and source hashes are in [room verification](audit/room_verification.json); original-art rendering evidence is in [render verification](audit/stadium_render_verification.json). Original art and generated shot media are intentionally outside the skill archive.
