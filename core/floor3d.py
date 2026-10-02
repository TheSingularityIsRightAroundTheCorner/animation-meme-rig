"""floor3d.py — a perspective floor you can run on, drawn with lines only.

Same idea as the hand turn: divide by depth. A plank edge at ground distance d lands at
    screen_y = horizon + focal * eye_height / d
so evenly spaced planks bunch up toward the horizon on their own - no texture needed.
Moving the camera forward is just subtracting from d, which is why the boards appear to
rush past. scroll is in plank units, so 1.0 = exactly one plank travelled: the pattern
repeats seamlessly and the loop is frame-perfect.
"""
import math

# Optional procedural example; authored floor textures remain the production default.
from PIL import Image, ImageDraw


def draw_floor(w, h, scroll=0.0, horizon=0.36, focal=1.05, eye=1.0,
               plank=2.6, lanes=11, lane_w=0.52, near=0.55, far=26.0,
               bg=(250, 249, 246), line=(30, 30, 34), fade=True):
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    hy = h * horizon

    def y_of(dist):
        return hy + focal * eye * h / max(dist, 1e-4)

    def x_of(lateral, dist):
        return w / 2 + focal * lateral * h / max(dist, 1e-4)

    def shade(dist, base):
        if not fade:
            return base
        k = min(1.0, max(0.0, (dist - near) / (far - near)))
        return tuple(int(c + (bg[i] - c) * (k ** 0.55)) for i, c in enumerate(base))

    # plank END joints. Real flooring staggers them lane by lane, so they must NOT line up
    # across the whole width - aligned joints read as tiles, not as boards.
    n = int(far / plank) + 2
    for k in range(lanes):
        lat0 = (k - lanes / 2) * lane_w
        lat1 = lat0 + lane_w
        offset = ((k * 7) % 5) / 5.0            # fixed per-lane stagger, repeats every 5 lanes
        for i in range(n):
            dist = near + ((i + scroll + offset) % n) * plank
            if dist > far:
                continue
            y = y_of(dist)
            if y < hy + 0.5 or y > h:
                continue
            d.line([(x_of(lat0, dist), y), (x_of(lat1, dist), y)],
                   fill=shade(dist, line), width=2 if dist < 3 else 1)

    #长 seams between planks: straight lines in 3D, so they converge on the vanishing point
    for k in range(lanes + 1):
        lat = (k - lanes / 2) * lane_w
        pts = []
        steps = 40
        for s in range(steps + 1):
            dist = near + (far - near) * (s / steps) ** 1.6
            pts.append((x_of(lat, dist), y_of(dist)))
        for s in range(steps):
            mid = near + (far - near) * ((s + 0.5) / steps) ** 1.6
            d.line([pts[s], pts[s + 1]], fill=shade(mid, line), width=2 if mid < 3 else 1)
    return img


def floor_gif(path, frames=24, w=900, h=506, speed=1.0, ms=60, **kw):
    ims = [draw_floor(w, h, scroll=-speed * i / frames, **kw) for i in range(frames)]
    from .output import save_frames
    save_frames(ims, path, durations=[ms] * len(ims))
    return path
