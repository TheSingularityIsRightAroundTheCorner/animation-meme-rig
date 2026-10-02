# Verification report

The original archive files were preserved byte-for-byte. Each file has a SHA256 and a canonical/merge/example-only/obsolete disposition in the [migration table](audit/migration_table.json). The initial 111-test release is recorded in `audit/final_verification.json`; the 119-test beat-offset release is in [review verification](audit/review_verification.json). The latest 126-test room-clipping release is in [room verification](audit/room_verification.json).

## Test-first sequence

1. Audit every supplied Python, JSON, specification and numeric output. Record absent PNG/GIF/MP4 assets explicitly.
2. Write91 behavioral contracts before any canonical core module exists, run them, and capture the test hashes and expected missing-core errors in `audit/regression_baseline.json`. This records ordering; it is not a claim that missing modules reproduce the old visual failures.
3. Extract inherited implementations and make narrow fixes. Consolidate4 duplicate tests and add an original-render golden test. Add regressions before fixing new discoveries, including alpha export and the shared CLI. The CLI has a separate initial snapshot.
4. Compare legacy numeric results, source-rendered synthetic frames, and real exported files. Forward-test the skill with an independent agent using a fresh small animation request.

## Verified behaviors

| Area | Evidence |
|---|---|
| Rig compatibility | Full RGBA fixture render matches the original Claude renderer after RGB flattening, including parent motion, crop and temporal substeps. |
| Recorded outputs | All80 supplied GPT probe frames reproduce exactly at their recorded one-decimal precision. These are affine probes. |
| Punch compatibility | All21 diagnostic frames match the original final GPT punch renderer pixel-for-pixel; body brace, growth, fade, camera and shutter retained. |
| Mesh, globe, floor, scatter | Reference function comparisons preserve remap pixels, all supplied motion curves, cloud/rim shader, staggered planks and drift/snap transforms. |
| Attachment | Translation, rotation, nested inheritance, detach/reattach, cycle detection, keep-world matrix and anchor thresholds tested. |
| Effects | Alpha-only lines, topmost order, independent disable,0.5s pulse, absence of accidental whole-frame flashing, explicit screen/multiply, lens holes and stroke compensation. |
| Camera/room | Explicit semantic crops, exact endpoints, pose schedule, guide dimensions, bounds, actual near-plane clipping, texture alpha/UV, legacy front-quad pixel equality and facing billboards. |
| Output | PNG alpha and frame sequence, GIF shared palette/late colors/holds, MP4 actual encode/decode/frame count/duration. |
| Independent forward use |41-frame diagnostic clip with parent inheritance, detach/reattach, camera push and screen-space line pulse. Detach matrix error0; reattach error2.22e-16; contact-anchor error2.84e-14px. Alpha delivery was independently rechecked after its fix. |
| Independent CLI use | Validation and rendering from an unrelated working directory; screen/world effect-space distinction; pulse with camera blur; alpha preservation. Both direct-file and numbered-sequence input collisions are rejected with original asset bytes unchanged. |

The standalone package includes the source fixtures needed by its test suite. No test requires a historical `/mnt` directory or original character drawing. Python/NumPy/Pillow/OpenCV are prerequisites; MP4 tests additionally use ffmpeg/ffprobe.

The failure register contains 47 groups: 39 historical documented groups, 6 reproducible audit/forward-use defects, 1 post-review beat-offset defect and 1 reproduced wall-disappearance defect. The fresh CLI tests were captured before the CLI implementation; later discoveries received targeted regressions before their fixes. GIF timing has the format's 10ms precision, while MP4 duration is quantized to the selected frame rate; `timing.json` retains the requested millisecond values.

## Post-review correction

The externally reported beat-offset omission was reproduced: the delivered CLI ignored `offset_ms` and produced 19 frames for a two-pose diagnostic that requires 22 frames at +88.5ms or 16 at -88.5ms. Eight added tests cover the actual CLI, pose-cut pixels, leading hold, negative clipping without phase reset, fractional boundary drift, invalid values, empty output and the published schema. The initial failing run and a corrected-validator-test rerun against the unmodified previous release are preserved in `audit/beat_offset_regression_baseline.json`.

That release had 119 tests. The default offset remains zero. Korean discovery terms and conditional runtime guidance were added without a second engine. An external Claude/Linux report was supplied by the user; it is additional reported evidence, not a Linux run performed here, and it predates that patch.

## Original-art stadium correction, 2026-09-25

Newly supplied stadium artwork and GIFs exposed a gap in the synthetic slicing tests: side walls were subdivided vertically, so each strip still spanned both sides of the camera plane and was rejected wholesale. Seven new tests were run before the clipping change (five failed, two passed). They verify actual visible-polygon coverage, a corner on the eye plane, a single visible corner against independent ray/plane intersections, texture direction/alpha, fully hidden geometry, exact original pixels for fully visible quads, and both room sides without slicing.

One old slicing test explicitly expected an unsliced quad to be rejected. Its assertion remains against the archived renderer; the corrected renderer must now draw that quad. This is an intentional defect correction, not a replaced visual golden. Pixel-centre mask sampling also prevents one-pixel cracks between clipped panels.

The original 48-frame, 960x540, 2.88s shot was rerendered with unchanged art, camera, actor, room dimensions, crops and timing. Clipping plus `slices: 1` restores the side walls and missing foreground floor. Source JPEG pixels re-encoded as PNG produce identical corrected first/last frames. The sheet confirms `stadium_run` as the suitable wall crop set; `floorfix` has 29-34% near-white pixels in its far/left/right crops, including outside margins. Near-white counts also include legitimate white artwork and are not an automatic crop rule. Local original-art renders are kept outside the distributable skill.

See [stadium diagnosis](stadium_diagnosis.md), `audit/clipping_regression_baseline.json`, and `audit/stadium_render_verification.json`. The latest full suite has 126 tests.

## Remaining manual-art limitations

- The initial archives contained no original PNG parts, GIF or MP4. Stadium art and three outputs were supplied later and checked for this room correction; unrelated character shots still need original-art review.
- Correct joint coordinates do not guarantee sufficient painted shoulder overlap or a convincing sense of force.
- Side-pose anchor alignment does not guarantee silhouette continuity. The original GPT hand swap remains an unchanged example with its source misalignment documented.
- Room-panel measurements, seam quality, glint placement, steam opacity and calibrated pivots must be checked on the actual artwork.
- Room near-plane clipping is now implemented. There is still no general depth buffer, independent second room actor or ceiling; views outside the room and painted white margins are not clipping failures.
- Border/stripe/missing-part diagnostics are heuristics. Intended offscreen movement, occlusion, art borders and effect lines require interpretation. Guide layers must be explicitly marked; red pixels cannot reliably identify a rough sketch.

## Folder layout

```text
animation-meme-rig/
  SKILL.md
  agents/openai.yaml          optional discovery metadata
  requirements.txt
  core/                      shared inherited primitives and adapters
  scripts/render.py          one CLI
  schemas/animation.schema.json
  presets/                   measured motion and environment data
  examples/                  preserved authored rig/turn sequences
  references/                usage, migration, verification and audit records
  tests/                     regressions and isolated original-code fixtures
```

`agents/openai.yaml` is optional UI metadata. The skill, JSON, Python and tests require no assistant-specific service.
