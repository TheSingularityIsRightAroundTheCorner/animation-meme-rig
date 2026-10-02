"""scatter_exit.py — reusable 'hang there, then everyone is gone' move.

Anime-meme grammar: several parts sit scattered in their own tilts, creep for a long
beat, then snap out of frame in 2-4 frames along the direction each was already leaning.
Works for dropped blades, a crowd bailing, petals, whatever — feed it a dict of
{name: (exit_angle_deg, askew_deg)} and it hands back per-frame local transforms.

Timing lives in spacing, not duration (frame_ms stays uniform). The snap frames get
sub-step transforms for motion blur; without blur a 700px jump reads as a cut.
"""
import math

def _pose(ang_deg, askew, d):
    a = math.radians(ang_deg + askew)
    return {"dx": math.cos(a) * d, "dy": math.sin(a) * d, "rot": askew + askew * 0.6 * (d / 400)}

def scatter_exit(items, drift_frames, drift_px, snap_frames, exit_px, blur_steps=6, snap_power=2.0):
    """Yields (frame_index, layers, substeps) for drift_frames + snap_frames frames.
    items: {name: (exit_angle_deg, askew_deg)}"""
    total = drift_frames + snap_frames
    prev_d = {n: 0.0 for n in items}
    for i in range(total):
        layers, subs = {}, None
        if i < drift_frames:                       # creep: linear, tiny, all frames uniform
            t = (i + 1) / drift_frames
            for n, (ang, k) in items.items():
                d = drift_px * t
                layers[n] = _pose(ang, k, d); prev_d[n] = d
        else:                                      # snap: ease_in, sub-stepped for blur
            t1 = (i - drift_frames + 1) / snap_frames
            subs = []
            for s in range(blur_steps):
                st = {}
                for n, (ang, k) in items.items():
                    t0 = (i - drift_frames) / snap_frames
                    tt = t0 + (t1 - t0) * (s + 1) / blur_steps
                    d = drift_px + (exit_px - drift_px) * tt ** snap_power
                    st[n] = _pose(ang, k, d)
                subs.append(st)
            for n, (ang, k) in items.items():
                d = drift_px + (exit_px - drift_px) * t1 ** snap_power
                layers[n] = _pose(ang, k, d)
        yield i, layers, subs
