# Claude archive audit

Audit date: 2026-09-24. Scope: all 17 extracted files (16 Python files and `camera_move_spec.md`) under `sources/claude`. Every implementation and comment was read in full; all 16 Python files pass AST syntax parsing. Embedded instructions were treated as historical production evidence, not new authorization or policy. The archive contains no images, GIFs, rendered frame sequences, generated JSON files, or dependency manifest. Therefore “proven” here means an explicit recorded fix or implemented behavior, not a verified match to missing artwork.

## File migration table

| Source | Disposition | Chosen content / evidence | Limits and destination |
|---|---|---|---|
| `rig_tree.py` | merge | Header records v3 perspective turn, v2.2 anisotropic scale/z, v2.1 blur, v2 parent override (4–8); local/world affine inheritance (44–73), finite-camera turn (76–95), per-frame z (127–135), full-scene substeps (140–148). | Retain these semantics in shared rig. Header title still says v2, but implemented history reaches v3. Compare GPT primitive variants before declaring final rig canonical. |
| `rig_tree (1).py` | obsolete | Exact duplicate of `rig_tree.py`: SHA256 prefix `0e32a4914230c124`, verified byte comparison. | Preserve original in source archive only; no second installed module. |
| `scatter_exit (1).py` | canonical | Only supplied independent generic drift/snap transform generator. Direction includes the art's askew angle (13–15); uniform spacing phases plus substeps (17–43). | Install once as `scatter_exit.py`; filename currently prevents `from scatter_exit import scatter_exit` in cut87. Preserve angular coupling and end position. |
| `sphere.py` | canonical | Equirectangular inverse mapping, Lambert shading, optional rim, separately moving alpha clouds (33–76). | Preserve globe mapping math. `equirect_from_robinson` (14–30) is a brightness-threshold approximation, not an exact geographic projection. Pair with GPT's measured map/texture adapter if relevant. |
| `floor3d.py` | canonical | Perspective plank floor, fixed lane stagger prevents tile appearance (33–48), receding/fading seams (50–60), periodic scroll (64–69). | Optional procedural geometry/diagnostic helper; do not silently substitute it for the author's authored texture floor. Preserve defaults. |
| `stadium3d.py` | merge | `look_at`, project, homography, quad warp, slices, billboard (33–99). Slices explicitly fix entire floor disappearing on near-camera crossing (72–75). | GPT `stadium3d_floorfix.py` must decide final textured floor path. Replace scene hardcodes `NET` and `PANELS` (14–21) with caller configuration while retaining a provenance preset. |
| `camera_move_spec.md` | merge | Shared camera vocabulary, guide rectangles, xywh units (10–22), spacing/blur (44–71), alpha/canvas/NFD defects (154–157), explicit layer order/blends (163–190), QA rules (194–222). | Reference plus validated adapter/schema. Text “almost always screen” is a shot heuristic, not a safe universal rendering default. Historical instruction to change every prior script (230) is not an audit instruction. |
| `build_pant_spec_v3.py` | example-only | Authored 8-pose breath, hold/settle split, half-cycle character offset (17–32), character part transforms (35–43). | Preserve as data preset and adapter. Its parts are filename strings and frame layers are a list; not rig_tree's schema. Renderer for this format was not supplied. |
| `build_pant_steam_v3.py` | merge | Same v3 breath; configurable back steam + subtle optional front haze (2–10, 42–52), panel mask (59–70), steam state (103–124), composition order (159–176). | Extract generic secondary-motion/steam functions and data preset. Keep exact breath timings; no character-name branches in core. Original includes source-asset paths and Korean filenames. |
| `build_hand_turn_final (1).py` | example-only | Explicit v6 supersedes rejected v3–v5 squash direction (1–10). Measured wrist axis/focal130/theta45 (15–20); hard pose swap, delayed claw extension/retraction, depth z ordering (45–87). | Preserve turn trajectory/pose data; promote only the finite-perspective primitive. Do not resurrect obsolete squash-only direction. Original art absent. |
| `build_cut87_spec (1).py` | example-only | Slow crouch → pose swap on first zoom frame → detached drift then snap (1–8, 68–105). Authored probes and complete substep layer visibility (90–109). | Convert scene constants to preset; preserve staging and parent null. `claw_drift` (38–47) is abandoned within this file, superseded by imported scatter at 88–103. |
| `make_cut37_v2_spec.py` | example-only | Measured parent hierarchy and shared grab pivot (9–32); two-frame jitter holds (64–74); attachment probes (78–79). | GPT cut37 force-v3 is later candidate; preserve this as historical recipe/control. Top-level copies every uploaded PNG: never import as library. |
| `build_dario_zoomout.py` | example-only | NFC filename resolver (39–44), opacity/scale snap (54–69), measured glasses-centered crop with clamped bounds (92–101), staged reveal (122–145). | Keep art-specific choreography separate. Top-level image loads and output writes, obsolete 64-color per-frame palette (147–153), speech-balloon art is this example's historical content, not a requirement for future shots. |
| `build_jensen_glint.py` | merge | White flattening (34–38); lens-difference mask with per-lens row hole filling (43–57); darken→full-bright lens→authored sparkle→flash (80–109). | Generic glint/mask helpers plus measured preset. Keep inter-lens gap, preserve eye-white holes filled. Replace fixed split978/paths with parameters. |
| `build_punch_barrage.py` | example-only | Alternating overlapping punches (22–27,46), growth-driven blur and early size threshold (48–49,71–78), beyond-edge target (67–68), camera push (81–85). | GPT v4 pulse family is later candidate. Preserve Claude failure evidence and benchmark trajectory, not duplicate entire punch engine. |
| `build_run_shot.py` | example-only | 42-frame dolly/fov/bob (9–37), sorted sliced room panels (42–51), pose swaps at40/72% + camera-facing billboard (53–60). | Store scene profile. Textured floor canonical is subject to GPT floorfix. Rendering runner after all room geometry is an intentional shot convenience, not general occlusion. |
| `make_fx.py` | example-only | Deterministic radial/horizontal procedural strokes and white flash. Width/zoom (1–3,14,26) documents failure fix. | Keep optional geometry utility or example; do not generate replacement character art. Import currently creates directory and writes ten images (6,36–40). |

“Canonical” in this table is primitive-level within the Claude contribution; the overall migration table can select a later GPT wrapper. Exact duplicate files are obsolete, but authored scene scripts remain evidence/examples even where one primitive is superseded.

## Documented failures → required regression cases

Each row is an observed historical failure explicitly recorded by a source, or a directly documented invariant. Regression tests must be recorded before replacing source behavior. Qualitative requirements need synthetic diagnostics plus eventual authored-art visual review; a numerical test alone cannot establish taste.

| ID | Evidence | Failure / testable requirement |
|---|---|---|
| C01 | `build_hand_turn_final (1).py:3–10` | ±orthographic squash was visually symmetric; signed perspective maps must differ, hold wrist axis fixed, and reverse near/far growth when sign reverses. |
| C02 | same:16–19 | Focal330 produced too little direction; theta62 flattened width too much. Freeze focal130/theta45 as this hand preset, not global constants. |
| C03 | `stadium3d.py:72–75` | One behind-camera corner removed whole floor. Synthetic crossing quad should leave visible front-facing slices; retain GPT improved floor rasterizer if it fixes seams better. |
| C04 | `build_jensen_glint.py:43–57` | Raw difference mask excluded preexisting eye whites, leaving dark blobs inside white lenses. Fill gaps within each lens's row span while retaining inter-lens gap. |
| C05 | `make_fx.py:1–3,14,26` | Camera enlarged thin lines into black bars. Width input scales inversely with camera zoom; validate screen stroke width within raster rounding. |
| C06 | `build_punch_barrage.py:48–49` | Exponent2.4 left fists tiny then smudged. Preserve power1.7 early growth and blur suppression for a small fist. |
| C07 | `camera_move_spec.md:154` | RGB-black/alpha-only line PNG flattened directly to RGB becomes black frame. Transparent texels must leave destination unchanged; multiplication uses alpha-on-white. |
| C08 | same:155,194 | Mismatched part or guide canvas corrupts coordinates. Explicit dimensions reject mismatch; guide coordinates never reused across unrelated scenes. |
| C09 | same:156; `build_dario_zoomout.py:39–44` | NFD names failed lookup. Normalize NFC/NFD for existing assets, reject ambiguous duplicates, use English generated names. |
| C10 | `camera_move_spec.md:163,169–190` | Claw/hand, orange overlay and delayed glass ordering were wrong. Verify explicit z/role order and time visibility. Numeric `_p2` before `_p10` rather than lexical order. |
| C11 | same:187 | Normal blend of bright glass/lighting hid art. Test selected screen blend preserves base details; do not infer mode solely from brightness. |
| C12 | same:199 | Removing a baked white background destroyed interior eye whites. If cleanup is explicitly requested, remove only edge-connected background and retain isolated interiors. Default retains original alpha. |
| C13 | same:200 | Red rough/guide layers were exported into shot. Mark diagnostic-only layers and assert exclusion in final renderer; red artwork must not be blindly deleted. |
| C14 | same:220 | Out-of-bounds camera crops produced black/white borders. Validate camera rectangle or explicit padding; edge brightness diagnostic can warn, not prove failure. |
| C15 | same:221 | Thin exposed row/column stripe. Synthetic isolated bright stripe must trigger detector; legitimate authored lines remain opt-out/diagnostic. |
| C16 | same:222 | Missing parts. Check expected-visible part alpha after transform/camera; intentionally hidden, occluded or exiting parts need explicit exceptions. |
| C17 | same:229 | Moving canvas-edge artwork up exposed background. Profile-specific motion bound/overscan check; don't clamp all animation upward motion. |
| C18 | same:69–71 | Short ease-out lacked perceived deceleration; absent blur broke fast motion; tail too short to read. Freeze camera preset with12–14 samples,2–3 tail samples and motion substeps, plus decreasing spacing and constant moving-frame duration. These are historical shot rules, not mathematical minima for every scene. |
| C19 | `build_pant_steam_v3.py:2–10,49–52,159–176` | Back steam must remain behind figures; front haze optional/low. Layer test with opaque character ensures back steam cannot tint it; front haze opt-in0.20 multiplier. |
| C20 | `build_pant_spec_v3.py:3–9,17–27` | Main pose arrives and holds; secondary hair may settle. Fixture confirms selected body/head values identical through intended hold while hair changes. |
| C21 | `floor3d.py:33–39` | Aligned plank ends read as tiles. Lane offsets stagger; integer-scroll periodic render byte-equality. |
| C22 | `rig_tree.py:166` | 48-color banding. Preserve255-color budget and shared palette; quantify retained gradient steps; shared palette must sample whole animation, since first-frame palette misses later colors. |
| C23 | `scatter_exit (1).py:8–9`; cut87:90–105 | Huge unblurred jump reads as a cut; use blur substeps. Substeps include full visibility state, otherwise unlisted default-visible parts reappear. |
| C24 | `build_punch_barrage.py:3–9,67–78` | Alternate L/R, overlap launches, growth-speed blur, leave frame instead of parking, speed lines remain throughout active action. Limit no-empty-fist assertion to active barrage; original deliberately includes an outro. |
| C25 | `build_cut87_spec (1).py:59–67` | Guide lines were landmarks rather than camera bounds, and following head movement cancelled visible sink. Preserve37px intended sink budget and zero camera follow for this profile. |

## Runtime and schema findings

- `rig_tree.py:20` documents camera as `{rect:...}`, but actual API is `frames[].camera` as a bare four-number xyxy list at152. The camera guide document uses xywh (20,122–123) and high-level `shots` (119), which no supplied Claude renderer accepts. `build_pant_spec_v3.py:41–42,57–67` uses layer lists and string parts. Explicit schema adapters and `schema_version` are necessary; none of these are interchangeable JSON.
- `build_cut87_spec (1).py:88` cannot import its supplied sibling because only `scatter_exit (1).py` exists. Canonical module name resolves this packaging bug without changing the algorithm.
- `rig_tree.py` probes at162–163 use affine world matrices, omitting rendered perspective turn at132–134. They will falsely report unchanged turn landmarks. Either report affine and rendered coordinates separately or include the actual homography in rendered probes and divide homogeneous coordinates.
- Parent affine transforms inherit; parent perspective turn does not inherit (`world_matrices` has no `turn`, applied only at compose). Original hand example applies the same turn separately to hand and blades. Preserve compatibility explicitly; changing this silently would double-transform those examples.
- Detach overrides change local parent selection without preserving world pose (65–67). This is correct for supplied cut87 because released body pose is identity. A general preserve-world reparent helper is separate, opt-in functionality.
- `rig_tree.py:112` uses `assert` for canvas validation; optimized Python disables it. Empty parts/frames, undefined parents, zero scale, focal0, and degenerate projection can fail obscurely. Validate ahead of rendering without changing valid transforms.
- All renderers but `build_pant_steam_v3.py` run substantial work at import; do not import scene builders as libraries. Archive copies remain inert; generic helpers must have main guards.
- `rig_tree.py:153` crops beyond canvas and Pillow pads with transparent black, then `.convert('RGB')` exposes black. Synthetic white-canvas test confirmed pixel `(0,0,0)` for camera[-3,-3,13,13].
- First-frame-only GIF palette (`rig_tree.py:167`, `sphere.py:81`, `floor3d.py:66`, `build_run_shot.py:66`, punch:87) can erase later colors. Shared palette alone is not enough: aggregate representative frames.
- `sphere.py:68` divides a zero light vector by zero; `_sample` assumes nonempty texture. Alpha of base globe texture is intentionally flattened/ignored at45, whereas clouds retain alpha at62. Preserve existing opaque-globe behavior unless exposed as a new option.
- `stadium3d.py:35–36` fails for coincident eye/target or parallel up/forward. `draw_quad:59` skips near-plane-crossing quads; slices mitigate rather than geometrically clip. Degenerate homographies can be singular. `project` clamps behind-camera depth and should not be used without visibility handling.
- `build_jensen_glint.py:62–69` assumes nonempty pixels in both sides of fixed split978; absent lens mask/spark alpha fails reductions. `frame:91–93` may calculate target_h=0 for a tiny positive sparkle scale. Guard unsupported inputs.
- `build_dario_zoomout.py:80–88` pastes RGBA sprites with their alpha as mask into transparent RGBA, multiplying fractional alpha before later alpha-composite. Opaque art is unaffected; semitransparent fringes can darken. Pure composition adapters should preserve alpha once.
- `build_pant_steam_v3.py:95–96` uses Pillow rotate, whose positive sign is opposite the matrix rig's screen-clockwise positive convention. Do not unify rotations without an explicit sign adapter.
- Steam randomness uses seeded `Random(7)` once across2 breaths (152–155): deterministic whole clip but consecutive breaths differ and loop closure is not exact. Preserve authored repeat unless introducing a documented seamlessly looping preset.
- `build_punch_barrage.py` says no empty frame, but FRAMES=31 and final punch ends at25; frames26–30 have no fist. This is an explicit generated outro, so any regression test should assert coverage only through the active action rather than “fix” the outro by adding punches.

## Missing assets and dependencies

Libraries: Python standard library, Pillow, NumPy. The default `/opt/homebrew/bin/python3` lacks Pillow; audit probes use `python3` (NumPy2.3.5). Every image input is absent from this archive. None of `/mnt/user-data/uploads`, `/home/claude/stage*`, `/home/claude/fx` are portable install locations.

Asset families referenced: pant body/head/hair/steam/background PNGs; cut37/87 body/hand/claw PNGs and generated FX; hand_back/side and bc/sc claw PNGs; stadium_parts.jpg and angle_1/2/3.png; Dario/glasses/balloon/Grok-Gemini PNGs; Jensen base/lens/spark PNGs; punch body/four fists/speed_line.webp; external globe textures passed by caller. Preserve measured pivots/crop constants as profile data until these images are available.

## Executed original-code probes

- All16 Python files parse successfully.
- The two rig files compare byte-identical.
- `floor3d.draw_floor(320,180,scroll=0)` and scroll1 are pixel-exact (max difference0).
- Turn at ±45°, focal130, axis0 maps input left/right ±47 to `[-44.648,26.468]` versus `[-26.468,44.648]`, verifying signed asymmetry.
- `sphere.render_globe` on a solid synthetic texture is pixel-identical at spin0/2π.
- Rig out-of-canvas crop on white background yields black border, confirming C14 as active defect.

These synthetic tests are geometry/encoding evidence only. No source artwork or Claude output was provided, so exact historical pixel-match QA cannot be claimed.

## Recommended additions to the GPT base

1. Merge the tree's full affine hierarchy, optional per-frame reparenting, z, sx/sy, turn, substep blur, and numerical probes; preserve existing defaults and expose schema/version distinctions.
2. Keep scatter as one parameterized timing primitive; keep hand/cut37/cut87 choreography as profiles.
3. Reuse sphere/cloud shader intact. Keep projection and quad utilities central, but retain analytic sphere mapping and textured floor sampler as specialized wrappers rather than forcing identical math paths.
4. Add one camera guide/spacing adapter with explicit xywh→xyxy conversion, bounds, guide dimensions, finite outputs, and blur/tail metadata.
5. Extract configurable pant/steam/glint behavior into shared secondary/effects helpers; retain exact visual layer order and authored pose tables.
6. Standardize runtime paths, validation, NFC asset resolution, global animation palette and diagnostics in shared utilities. Require only Pillow+NumPy for these additions.
