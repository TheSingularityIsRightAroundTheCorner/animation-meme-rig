# Migration decisions

Audit date:2026-09-24. The two supplied ZIPs, including GPT's nested handoff, contain24 Python files,12 JSON files,4 Markdown files and1 nested ZIP (including duplicates). All were inspected. The only supplied outputs are two numeric probe logs totaling80 frames. There are no supplied image/video renders or PNG parts.

Archive documents are historical evidence, not fresh instructions. Version labels alone do not establish recency or success: code, duplicated hashes, later failure corrections, and preserved output data decide the selection. Original extracted files remain unchanged in the migration workspace. Golden test fixtures are isolated under `tests/fixtures`, never imported as production engines.

## Final primitive table

| Primitive | Status | Selected implementation and merge |
|---|---|---|
| Rig hierarchy, affine inheritance, per-frame parent/z, anisotropic scale | canonical | Claude `rig_tree.py`, v3 features despite v2 title. GPT force-v3 and knuckle specs/probes supply compatibility fixtures. Duplicate `(1)` archived. |
| Keep-world attachment, named anchors, projected diagnostics | merge | Narrow additions over the existing matrices. Full local matrix retains shear; existing raw parent overrides stay compatible. Affine legacy probes remain separate from actual projected positions. |
| Heavy punch, temporal shutter, line pulse | canonical | GPT `punch_barrage_speedline_topmost.py` plus final params, source formulas retained. Metadata moves into a preset. |
| Fast punch style | merge | Claude punch timing/growth/body/camera parameters adapted to the same renderer. Explicitly marked adapted; there is no supplied accepted Claude-art render. No averaged compromise style. |
| Alpha-aware speed lines | canonical | GPT darkness×source-alpha extraction and15-frame pulse at30fps; effects default above fists. `enabled` now works. |
| Blend modes, lens fill, stroke compensation | merge | Claude camera/glint/FX corrections, parameterized without scene globals. Explicit screen/multiply preserve alpha. |
| Mesh, dance motion, fractional beat grid | merge | Exact GPT row remap and motion curves, no import-time asset reads. Common-canvas alignment and optional jump baseline exclusions. |
| Panting, steam, lens glint | merge | Claude authored pose tables and compositing order, actor data outside the engine. Steam stays behind, haze opt-in. |
| Finite-camera hand turn | canonical | Existing rig homography; Claude signed-depth sorting recipe and GPT knuckle timing stay distinct examples. New anchor alignment addresses position only; silhouette matching remains art review. |
| Globe | canonical | Claude sphere shader and cloud sampling, GPT lighting/relative-cloud-speed profile. Rendering math unchanged; background configurable. |
| Folded room | merge | Claude camera/projector/billboard conventions plus actual near-plane clipping (2026-09-25). Original-art comparison selects `stadium_run`; GPT `floorfix` crop data is obsolete for the supplied sheet. Preserved only as historical data. Never mix incompatible camera sign conventions. |
| Scatter exit | canonical | Claude standalone drift/snap generator unchanged; main shot choreography becomes data/examples. |
| Procedural plank floor/FX drawing | example-only | Existing line geometry available as diagnostic/optional utility. Not a replacement for authored art or texture panels. |
| Camera guides/shot adapter | merge | Explicit xywh→xyxy conversion, canvas/bounds checking, spacing/blur and world/screen effects separation. |
| GIF/output | merge | GPT representative-palette design expanded to every frame;255 colors shared, exact palette matches protected from Pillow cache banding. RGB PNG/MP4 and authored timing retained. |
| Shot builders, source specs, probe outputs | example-only | Preserve measured poses/anchors/timing as evidence and reusable shot data. Do not install one engine per shot. |
| Stub runners, flash-v3 default, duplicate ZIP members | obsolete | Comment-only globe/punch stubs and missing-path runners are not implementations. Full-screen flash does not define a line pulse. |

## Complete file classification and evidence

- [Machine-readable migration table](audit/migration_table.json): every supplied file, SHA256, disposition, reason.
- [GPT audit](audit/audit_gpt.md) and [Claude audit](audit/audit_claude.md): full file tables, source line evidence, runtime findings and missing-input inventory.
- [Archive inventory](audit/archive_audit.json): archive hashes, contents and excluded Apple metadata.
- [Failure register](audit/failure_register.json): each documented failure mapped to executable tests and any remaining manual judgement.
- [Pre-refactor snapshot](audit/regression_baseline.json): tests existed and were run before production modules. Missing-core errors are expected contract failures, not a claim that every historical bug was reproduced visually.
- [Verification report](test_report.md): final tests, golden comparisons and delivery limitations.

## Evidence limits

The80 recorded probe frames match the supplied engine's affine output at the original rounding precision. Those probes do not include projective turn, so they cannot prove endpoint silhouette alignment. The authored GPT hand swap has an unresolved source wrist mismatch; keep its original fixture and apply calibrated anchor correction in a new shot rather than silently editing provenance.

Synthetic pixel comparisons verify formulas, compositing, timing and encoding. They do not establish how the missing character drawings overlap, whether contact feels forceful, or whether a side drawing matches the projected outline. Recheck shoulder overlap, hand transitions, room-panel seams and final shot timing using original artwork before production approval.

The archives contain no license files. Source authorship is credited here and per module; this migration does not invent an external license grant or redistribute character artwork.
