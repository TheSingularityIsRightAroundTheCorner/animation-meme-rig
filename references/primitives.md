# Primitive notes

## Rig and contact

Source coordinates use a shared PNG canvas, with x right and y down. A part's pivot and named anchors are measured in this canvas. Local transforms compose as `T(pivot + delta) @ R(rot) @ S(sx,sy) @ T(-pivot)`; positive matrix rotation moves clockwise on the screen. World matrices inherit recursively. Layers explicitly override their parent for one frame; a missing override returns to the part's declared parent. A keep-world helper returns a full local matrix so rotated/nonuniformly scaled parents do not lose shear during decomposition. Carry its returned layer state into subsequent frames when an attachment persists. An explicit `matrix` overrides `rot/dx/dy/scale/sx/sy`; multiply the matrix to animate that local pose, or remove it when intentionally returning to scalar controls.

The legacy `turn` is a canvas-space projection applied after affine inheritance. It does not automatically propagate from a parent: supplied hand specs explicitly repeat it on each claw. Keep this compatibility to avoid double turns. `anchor_world(..., projected=True)` and rendered probe diagnostics apply and divide the homography; old probe logs are affine only.

Contact needs an anchor and sufficient drawn overlap. Align corresponding anchors before an intentional pose swap. Preserving a world pose avoids teleportation but does not imply that two unrelated contact points coincide. Use anchor alignment only when the shot calls for snapping them together. Check descendants after either operation.

## Perspective turn

The inherited homography is `T(axis) @ [[cos(theta),0,0],[0,1,0],[sin(theta)/focal,0,1]] @ T(-axis)`. Near and far offsets scale differently. The authored Claude hand uses focal130 and45degrees; the later GPT knuckle spec uses focal420 and up to-78degrees. These are distinct measured shot setups, not an instruction to average parameters.

Sort crossing parts with explicit per-frame z values. Grow a claw with sy around its knuckle anchor, then stagger the growth values. At a drawn side-pose transition, align measured anchors and inspect silhouette/width. A point-perfect alignment cannot manufacture a missing side drawing or guarantee a pop-free outline.

## Secondary motion

The row warp is taken from the GPT dance prototype: smoothstep sway plus a sinusoidal bend, with y scaling around the foot baseline. Preserve the common canvas and horizontal composition. Baseline correction must be opt-in for poses depicting jumps. Pose changes remain hard cuts; the warp supplies motion during each hold. Absolute beat boundaries prevent cumulative rounding drift.

Panting preserves the eight authored poses and nonuniform hold durations. Body/head holds and delayed hair settle are different channels. Steam is composited behind the character; optional front haze uses a low opacity multiplier. Secondary helpers preserve Pillow's counterclockwise positive rotation convention; a rig adapter must invert the sign.

## Camera and room

Rig camera rectangles are xyxy. Historical camera-shot documents use xywh and need an explicit conversion. A colored guide image must have the same canvas size as the artwork. Crop bounds should fail clearly rather than pad with accidental black. Do not force every project into16:9.

Room panel records contain explicit crops and rotations. The original 1200x1600 net supplied on 2026-09-25 confirms `stadium_run` as the suitable wall crop set. `stadium_floorfix` remains historical data, with excessive outside white margins for this sheet. Some white borders are painted inside even the narrower crops; clipping cannot remove them.

The shared room implementation retains Claude's negative-camera-Z convention. It clips polygons to depth >= 0.05 before perspective division, retains texture coordinates via a homogeneous mapping, and samples the polygon mask at pixel centres to avoid cracks. Already-front-facing quads retain the original pixel path. `slices: 1` is sufficient for these nonintersecting box panels. This is near-plane clipping, not a depth buffer: actors are still composited over the room, multiple independent room actors are unsupported, and a camera can still see above an open wall or outside the box.

## Compositing and output

Transparent black line PNGs carry their shape in alpha; dropping alpha turns them into black rectangles. White-keyed speed lines use darkness multiplied by source alpha. Blend modes are explicit. Screen blend is appropriate for the supplied light/glass example but not a universal property of bright art. Optional filename roles provide an ordering suggestion only.

Motion blur averages temporal render samples. Gaussian blur remains available for haze or soft glow, not as a substitute for displacement blur. Screen-space overlays are applied after the camera when stroke thickness must stay fixed. The historical punch keeps its overlay before the camera to preserve that successful source behavior.

Use a single255-color representative palette for a GIF, including late effects. Alpha delivery uses PNG; RGB preview/MP4 flattens against an explicit background. ffmpeg is an optional system executable required only for MP4. Source output timings in milliseconds are preserved when frames have authored holds.
