# Runtime notes for any agent

`SKILL.md`, the JSON specs and Python CLI are the shared interface. `agents/openai.yaml` is optional discovery metadata, not an engine dependency. A Claude-specific Python fork or invented agent metadata format is unnecessary.

## Read-only and ephemeral hosts, including Claude

1. Locate this skill and the supplied artwork in the current session. Check Python dependencies and the actual writable output directory. Do not assume files from an earlier session still exist.
2. Read installed core files without editing the installation. Put working scene JSON, logs and renders in a writable workspace. Reuse the same CLI from any working directory with absolute paths:

   ```sh
   python /absolute/skill/scripts/render.py /absolute/work/scene.json --assets /absolute/art --out /absolute/output/preview.gif
   ```

3. In a host that provides `/mnt/user-data/outputs`, use an explicit path there for deliverables. Otherwise use the host's actual writable delivery folder. This is a conditional example, not a universal path requirement. Never write to a remembered `/mnt` path without checking it.
4. Treat dependencies as environment requirements, not bundled executables. Use the host's supported dependency setup; `requirements.txt` lists the Python libraries. MP4 also needs ffmpeg/ffprobe.
5. If multiple rig skills are enabled, explicitly select `animation-meme-rig`. Legacy names such as `webtoon-rig` and `beat-rig` may overlap in discovery. Recommend disabling superseded copies where appropriate; do not delete or disable another skill without the user's instruction.

## QA budget

Start with validation and numerical diagnostics: anchor/contact errors, frame count and duration, bounds, alpha, palette consistency, and the timing grid. Use contact sheets for the first/last, contact, transition and impact frames plus frames around numerical spikes. Inspect at delivery size using the actual supplied artwork. Avoid reopening every frame when neither diagnostics nor motion changed, but do not replace visual review with numbers alone.

Report separate conclusions for numeric/synthetic regression, decoded export, and original-art visual acceptance. A synthetic image can test compositing or deformation; it cannot establish that a painted shoulder overlaps or that a punch feels forceful.

## Common misreadings to prevent

- A front face moving left does not by itself say whether the camera or object turns. Establish both the moving subject and the visible direction.
- Speed-line pulse is not a whole-frame flash. Motion blur means temporal substeps, not an arbitrary spatial smear.
- Keep fractional beat phase. `offset_ms: 88.5` is a per-song example, not a measured default for other audio; mesh exports are sampled on the requested frame grid and do not mux audio.
- `end_overshoot` is a profile value: inherited heavy barrage uses 1.85; adapted fast barrage uses 1.75. Do not silently replace one style with the other.
- An authored hold does not mean every layer must freeze. Preserve existing secondary motion where supported. Independent foreground/background sampling rates are not currently implemented.
- Small painted parts and watercolor texture may require rigid motion with no blur/deformation. Establish that intent from the shot and art; the engine currently has no automatic small-part or watercolor detector.
- Action/dialogue/still hold categories are authoring vocabulary, not implemented schema enum values. Encode supported frame durations and motion explicitly; do not invent ignored spec flags.

Depth projection is a shared principle, but the inherited plane, room and sphere renderers retain different coordinate conventions. Their equations are not interchangeable merely because each involves depth.
