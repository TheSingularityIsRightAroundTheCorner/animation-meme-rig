# Robots, Vehicles & Transformations

A standalone low-poly robot, vehicle transformation lab, and deterministic hero-shot rig. No build step, external models, or remote textures.

## Open

- `index.html`: fusion lab, vehicle modes, six mechanisms, palette-driven toon rendering.
- `showcase.html`: hero camera, face-front X charge, downward arm release, screen-filling spark burst, clean final pose, and knee-height Dutch-angle run.

Open either HTML file in a desktop browser. Keep the included folder layout. Three.js r149 UMD is bundled locally.

## Hero shot timing

| Time | Action |
| --- | --- |
| 0–1.10 s | Crossed fists in front of the face; high camera; continuous electric arcs and sparks. |
| 1.10–1.85 s | Arms spread down and outward; camera follows the descending hands. |
| 1.55–2.10 s | Camera pulls back and drops to the low-angle full-body composition. |
| 2.05–2.47 s | One large radial burst expands out of the frame and disappears. |
| 2.47–4.50 s | Clean full-body hero pose, no remaining sparks. |

The running camera sits at model height 9, near knee height, with an 18-degree Dutch angle. Both shots are sampled at 12 poses per second and exported as 24 fps two-frame holds. Spark geometry uses deterministic seeds and pooled meshes.

## Files and interfaces

- `antigravity_king.js`: original combining model; `window.AntigravityKing.build(palette)`.
- `motion_rig.js`: independent pose rig; `window.MechaMotionRig.build(robot)`; `cross(seconds)` and `run(seconds)`.
- `hero_effects.js`: pooled lightning and burst geometry; `window.HeroEffects.build(scene, palette)`.
- `showcase.html`: camera choreography and preview; `window.MotionLab.render(shot, seconds, width, height)`.
- `tools/capture.mjs`: PNG capture through a local Chrome debugging connection.
- `tools/encode.py`: FFmpeg encoding of captured transparent frames.
- `tests/verify.mjs`: browser-level motion, framing, and timing checks.

The shot rig resets all transforms before each pose, so seeking and out-of-order sampling do not accumulate joint rotations. Feet are solved from ankle targets. The X pose uses forward/inward shoulder travel and a telescoping upper-arm frame; it is an animation rig, not a collision-free physical mechanism.

## Capture

Start a local server from this directory:

```sh
python3 -m http.server 8766 --bind 127.0.0.1
```

Launch a separate temporary Chrome profile with remote debugging on port 9222. Install Deno and FFmpeg if using the optional capture tools. No dependencies are needed just to open the HTML previews.

```sh
deno run --allow-net=127.0.0.1:9222 --allow-read --allow-write tools/capture.mjs cross captures/cross_frames
deno run --allow-net=127.0.0.1:9222 --allow-read --allow-write tools/capture.mjs run captures/run_frames
python3 tools/encode.py captures exports
deno run --allow-net=127.0.0.1:9222 tests/verify.mjs
```

The MOV output uses the lossless QuickTime Animation codec, not ProRes. WebM carries VP9 alpha. PNG sequences are the source of truth. Editor support for alpha must be checked in the target application. Preview MP4 files have a solid background and do not carry alpha.

## Repository scope

This package contains only the robot code, local runtime, tools, and documentation. Rendered media are supplied separately and ignored by Git. No story-project documents, hand-drawn source files, account identifiers, personal home-directory paths, or existing Git history are included.

Keep code and shot settings in version control; store bulky exports separately. This makes it easier to identify which change caused a regression and restore a known working version.

## Third-party runtime

Three.js r149 is distributed under the MIT license. Its required notice is preserved in `vendor/THREE-LICENSE.txt`. The project-specific robot design and demo code are provided for viewing; no additional license is granted for them. The repository-root MIT license applies to the Python rigging tools, not this standalone demo. Three.js retains its own MIT license.
