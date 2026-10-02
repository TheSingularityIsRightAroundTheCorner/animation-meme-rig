#!/usr/bin/env python3
"""rig_tree.py v2 — parent/child transform inheritance for hand-drawn part PNGs.

v3:   "turn" on a layer = real perspective rotation about a vertical axis (direction-bearing)
v2.2: "sx"/"sy" non-uniform scale and per-frame "z" override (2.5D turns)
v2.1: "substeps" on a frame = list of layer dicts rendered and averaged (motion blur for snap moves)
v2: a frame's layer entry may carry "parent" to override the tree mid-shot
    ("parent": null detaches; "parent": "hand" re-attaches).

All parts must share one canvas (same size, alpha). Each part has:
  file   : PNG path
  pivot  : [x, y] in canvas coords — the joint this part rotates about
  parent : name of parent part (or null). Child inherits parent's WORLD transform.
  z      : draw order (low = back)

Per frame, each part may get a LOCAL transform {rot, dx, dy, scale, visible}.
World(part) = World(parent) @ Local(part)
Local = T(pivot+d) @ R(rot) @ S(scale) @ T(-pivot)

Camera: {rect: [x0,y0,x1,y1]} per frame, cropped then resized to out_size.
Verification: prints per-frame world position of named "probe" points so
attachment can be checked numerically (no eyeballing).
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image


def T(dx, dy):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)


def R(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def S(kx, ky=None):
    ky = kx if ky is None else ky
    return np.array([[kx, 0, 0], [0, ky, 0], [0, 0, 1]], float)


def local_matrix(pivot, tr):
    rot = tr.get("rot", 0.0)
    dx, dy = tr.get("dx", 0.0), tr.get("dy", 0.0)
    k = tr.get("scale", 1.0)
    kx, ky = tr.get("sx", k), tr.get("sy", k)     # sx/sy: squash toward the turn axis (2.5D)
    px, py = pivot
    return T(px + dx, py + dy) @ R(rot) @ S(kx, ky) @ T(-px, -py)


def world_matrices(parts, frame_tr):
    """Resolve tree. Detects cycles. Returns {name: 3x3}."""
    cache = {}

    def world(name, stack=()):
        if name in cache:
            return cache[name]
        if name in stack:
            raise ValueError(f"cycle: {' -> '.join(stack + (name,))}")
        p = parts[name]
        tr = frame_tr.get(name, {})
        L = local_matrix(p["pivot"], tr)
        # "parent" may be overridden per frame -> detach (None) or re-attach (name)
        par = tr["parent"] if "parent" in tr else p.get("parent")
        W = L if par is None else world(par, stack + (name,)) @ L
        cache[name] = W
        return W

    for n in parts:
        world(n)
    return cache


def turn_matrix(axis_x, axis_y, theta_deg, focal):
    """Rotate the part's plane about a vertical axis and project it with a finite camera.
    (u,v,1) -> (u*cos, v, 1 + u*sin/f).  Near side (u*sin<0) divides by <1: it GROWS and
    pushes outward. Far side shrinks and pulls in. That asymmetry is the direction cue an
    orthographic squash can never produce."""
    th = math.radians(theta_deg)
    M = np.array([[math.cos(th), 0.0, 0.0],
                  [0.0,          1.0, 0.0],
                  [math.sin(th) / focal, 0.0, 1.0]], float)
    return T(axis_x, axis_y) @ M @ T(-axis_x, -axis_y)


def apply_homography(img, H):
    """PIL wants the output->input map, normalised so the bottom-right entry is 1."""
    inv = np.linalg.inv(H)
    inv = inv / inv[2, 2]
    c = (inv[0, 0], inv[0, 1], inv[0, 2],
         inv[1, 0], inv[1, 1], inv[1, 2],
         inv[2, 0], inv[2, 1])
    return img.transform(img.size, Image.PERSPECTIVE, c, resample=Image.BICUBIC)


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    return 1 - (1 - t) ** 3


def render(spec, out_gif, attach=True):
    base = Path(spec["base_dir"])
    parts = spec["parts"]
    imgs = {n: Image.open(base / p["file"]).convert("RGBA") for n, p in parts.items()}
    W0, H0 = next(iter(imgs.values())).size
    for n, im in imgs.items():
        assert im.size == (W0, H0), f"canvas mismatch: {n} {im.size} vs {(W0,H0)}"
    out_w, out_h = spec.get("out_size", [980, 556])
    bg = tuple(spec.get("bg", [255, 255, 255, 255]))

    # optional: break attachment for control render (children become roots)
    parts_eff = json.loads(json.dumps(parts))
    if not attach:
        for n in spec.get("detach_for_control", []):
            parts_eff[n]["parent"] = None

    frames, durations = [], []
    probe_log = []
    def compose(tr):
        Wm = world_matrices(parts_eff, tr)
        canvas = Image.new("RGBA", (W0, H0), bg)
        # z may be overridden per frame: a part that swings behind the axis must draw behind
        for n in sorted(parts_eff, key=lambda n: tr.get(n, {}).get("z", parts_eff[n]["z"])):
            if not tr.get(n, {}).get("visible", parts_eff[n].get("visible", True)):
                continue
            H = Wm[n]
            t = tr.get(n, {}).get("turn")
            if t:                                  # plane rotation applied in canvas space
                H = turn_matrix(t["axis_x"], t["axis_y"], t["theta"], t.get("focal", 600.0)) @ H
            canvas.alpha_composite(apply_homography(imgs[n], H))
        return canvas, Wm

    for fi, fr in enumerate(spec["frames"]):
        tr = fr.get("layers", {})
        subs = fr.get("substeps")            # motion blur: average several in-between renders
        if subs:
            acc = None
            for st in subs:
                c, _ = compose(st)
                a = np.asarray(c.convert("RGB"), dtype=np.float32)
                acc = a if acc is None else acc + a
            canvas = Image.fromarray((acc / len(subs)).astype(np.uint8)).convert("RGBA")
            Wm = world_matrices(parts_eff, tr)
        else:
            canvas, Wm = compose(tr)
        # camera
        x0, y0, x1, y1 = fr["camera"]
        crop = canvas.crop((int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))))
        crop = crop.resize((out_w, out_h), Image.LANCZOS).convert("RGB")
        frames.append(crop)
        durations.append(fr.get("ms", 80))
        # probes: world position of a canvas point under a part's matrix
        row = {"frame": fi}
        for pr in spec.get("probes", []):
            px, py = pr["point"]
            for n in pr["parts"]:
                v = Wm[n] @ np.array([px, py, 1.0])
                row[f"{pr['name']}@{n}"] = (round(float(v[0]), 1), round(float(v[1]), 1))
        probe_log.append(row)

    # global 255-color palette (avoid 48-color banding)
    pal = frames[0].quantize(colors=255, method=Image.MEDIANCUT)
    q = [f.quantize(colors=255, palette=pal, dither=Image.NONE) for f in frames]
    q[0].save(out_gif, save_all=True, append_images=q[1:], duration=durations, loop=0, disposal=2, optimize=False)
    return frames, probe_log


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    attach = "--detach" not in sys.argv
    out = spec["out"] if attach else spec["out"].replace(".gif", "_DETACHED.gif")
    frames, log = render(spec, out, attach=attach)
    print("wrote", out, len(frames), "frames")
    for row in log:
        print(row)
