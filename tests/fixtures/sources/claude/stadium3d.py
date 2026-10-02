"""stadium3d.py — fold a hand-drawn net into an open-top box and film inside it.

Every panel is one quad in 3D. Project its four corners, solve the homography from the
drawn crop to those four points, warp, composite back-to-front. Same divide-by-depth as
the hand turn and the floor, just applied to whole panels instead of one plane.
Billboards (the characters) are quads that always face the camera, so the drawing keeps
its own perspective while the room moves around it.
"""
import math
import numpy as np
from PIL import Image

# --- measured panel boxes on the 1200x1600 net -------------------------------
NET = "/mnt/user-data/uploads/stadium_parts.jpg"
PANELS = {                       # (x0, y0, x1, y1), rotation to bring the floor edge to the bottom
    "far":   ((315, 387, 893, 668), 0),
    "near":  ((340, 1002, 929, 1242), 180),
    "left":  ((83, 683, 304, 1008), 270),
    "right": ((883, 646, 1162, 932), 90),
    "floor": ((340, 700, 893, 960), 0),
}

def load_panels():
    net = Image.open(NET).convert("RGBA")
    out = {}
    for k, (box, rot) in PANELS.items():
        im = net.crop(box)
        if rot: im = im.rotate(rot, expand=True)
        out[k] = im
    return out

# --- camera -------------------------------------------------------------------
def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    s = np.cross(f, up); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    return np.stack([s, u, -f]), eye

def project(pts, R, eye, w, h, fov=52.0):
    cam = (np.asarray(pts, float) - eye) @ R.T
    z = -cam[:, 2]
    fpx = (h / 2) / math.tan(math.radians(fov) / 2)
    x = w / 2 + fpx * cam[:, 0] / np.maximum(z, 1e-3)
    y = h / 2 - fpx * cam[:, 1] / np.maximum(z, 1e-3)
    return np.stack([x, y], 1), z

def homography(src, dst):
    A, B = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]); B.append(dx)
        A.append([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]); B.append(dy)
    h = np.linalg.solve(np.array(A, float), np.array(B, float))
    return np.array([[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1.0]])

def draw_quad(canvas, tex, corners3d, R, eye, fov):
    w, h = canvas.size
    dst, z = project(corners3d, R, eye, w, h, fov)
    if (z < 0.05).any():
        return None
    tw, th = tex.size
    src = [(0, 0), (tw, 0), (tw, th), (0, th)]
    H = homography(src, [tuple(p) for p in dst])
    inv = np.linalg.inv(H); inv = inv / inv[2, 2]
    warped = tex.transform((w, h), Image.PERSPECTIVE,
                           (inv[0, 0], inv[0, 1], inv[0, 2],
                            inv[1, 0], inv[1, 1], inv[1, 2],
                            inv[2, 0], inv[2, 1]), resample=Image.BICUBIC)
    canvas.alpha_composite(warped)
    return float(z.mean())

def strips(quad, tex, n=10, axis=0):
    """Split a quad (and its crop) into n slices. A single huge quad is dropped whole the
    moment ONE corner falls behind the camera - which is what made the floor disappear.
    Sliced, only the slices actually behind the lens are skipped."""
    p0, p1, p2, p3 = [np.asarray(p, float) for p in quad]
    tw, th = tex.size
    out = []
    for i in range(n):
        a, b = i / n, (i + 1) / n
        if axis == 0:                       # slice along the p0->p1 edge
            q = [p0 + (p1 - p0) * a, p0 + (p1 - p0) * b,
                 p3 + (p2 - p3) * b, p3 + (p2 - p3) * a]
            crop = tex.crop((int(tw * a), 0, max(int(tw * b), int(tw * a) + 1), th))
        else:                               # slice along the p0->p3 edge
            q = [p0 + (p3 - p0) * a, p1 + (p2 - p1) * a,
                 p1 + (p2 - p1) * b, p0 + (p3 - p0) * b]
            crop = tex.crop((0, int(th * a), tw, max(int(th * b), int(th * a) + 1)))
        out.append((q, crop))
    return out


def billboard(center, height, aspect, R):
    """A quad that always faces the camera: built from the camera's own right/up axes."""
    right, up = R[0], R[1]
    c = np.array(center, float)
    hw, hh = height * aspect / 2, height / 2
    return [c - right * hw + up * hh, c + right * hw + up * hh,
            c + right * hw - up * hh, c - right * hw - up * hh]
