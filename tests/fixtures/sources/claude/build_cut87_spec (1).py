"""Cut 87 - 'dropping your tools'.
Three beats, one shared 3072x1264 canvas:
  A  crouch      : head sinks on a slow ease, tight camera, no cut
  B  release     : hard swap f1->f2 on the FIRST zoom frame + fast zoom out + speed-line flash
  C  let go      : claws detach (parent -> None) and drift out, slow first then whipped away
Action grammar: the slow beat pays for the fast one. A is long and quiet so B reads as a release,
and C is slow again so the claws feel weightless rather than thrown.
"""
import json, math

STAGE = "/home/claude/stage87"
CAM_TIGHT = [1232, 392, 1805, 715]      # 573 wide
CAM_WIDE  = [502, 182, 2422, 1262]      # 1920 wide
# name: (pivot, exit_angle_deg, askew_deg)
# exit angle = the blade's own long axis, measured from the art (PCA), pointing away from the body.
# Each blade already sits at a slightly different tilt, so the scatter fan is the drawing's, not invented.
CLAWS = {
    "claw_L1": ((1028, 952), 137.5, -3.5), "claw_L2": ((1101, 1047), 122.9, +2.5),
    "claw_L3": ((1185, 1092), 112.6, -1.5), "claw_R1": ((1807, 1078), 68.1, +3.0),
    "claw_R2": ((1881, 1045), 60.8, -2.0), "claw_R3": ((1923, 1011), 58.0, +4.0),
}
P = lambda f, pv, par, z: {"file": f, "pivot": pv, "parent": par, "z": z}
parts = {
    "fx_speed": P("fx_speed.png", [1462, 722], None, -9),   # pivot = wide-camera centre
    "f1_body":  P("f1_body.png", [1490, 880], None, 1),
    "f1_head":  P("f1_head.png", [1492, 575], "f1_body", 2),   # head is a child of the torso
    "f2_body":  P("f2_body.png", [1494, 1260], None, 1),
}
for n, (pv, _a, _k) in CLAWS.items():
    parts[n] = P(n + ".png", list(pv), "f2_body", 3)           # start attached to the body

lerp     = lambda a, b, t: a + (b - a) * t
ease_out = lambda t: 1 - (1 - t) ** 3          # fast start, soft landing  -> camera
ease_in  = lambda t: t ** 2.6                  # slow start, runs away     -> claws
smooth   = lambda t: t * t * (3 - 2 * t)       # soft both ends            -> crouch

EXIT = 2400          # px travelled by the time it clears frame
def claw_drift(name, t):
    """One blade after it is let go. Straight line along its own tilt - no wobble, no arc.
    The whole read is in the speed curve: it creeps for the first half, then is gone."""
    _pv, ang, askew = CLAWS[name]
    a = math.radians(ang + askew)                 # askew is baked into the travel direction too
    d = EXIT * t ** 3                             # cubic: barely moves, then leaves
    spin = askew * 9 * t ** 3                     # turns the way it was already leaning
    return {"dx": math.cos(a) * d, "dy": math.sin(a) * d, "rot": askew + spin}

frames = []
def F(cam, ms, layers):
    base = {n: {"visible": False} for n in parts}
    base.update(layers)
    frames.append({"layers": base, "camera": list(cam), "ms": ms})

def speed(scale_cam_w, cam, vis):
    """Frame-locked FX: counter-scale against the camera so the burst never appears to zoom."""
    if not vis: return {"visible": False}
    cx, cy = (cam[0] + cam[2]) / 2, (cam[1] + cam[3]) / 2
    k = scale_cam_w / 1920
    return {"visible": True, "scale": k, "dx": cx - 1462, "dy": cy - 722}

# --- A. crouch: 12 frames, slow -------------------------------------------------
# Read off the guide PNG: blue rule = crown, red rule = chin (landmarks, NOT start/end).
# The grey caliper between them is the measurement that matters - 37px of chin travel.
HEAD_TOTAL = 37                       # grey caliper on the guide: y 537 -> 575
BODY_DY    = 24                       # the torso carries most of the sink
HEAD_DY    = HEAD_TOTAL - BODY_DY     # the head's own share stays smaller than the torso's
CAM_FOLLOW = 0.0                      # 37px does not need a follow - a follow would cancel it
for i in range(12):
    p = i / 11
    t_body = smooth(p)                      # torso: slow, settles across the whole beat
    t_head = ease_out(min(1, p / 0.55))     # head: arrives by 55% and waits - leads the torso
    dy_cam = CAM_FOLLOW * BODY_DY * t_body
    cam = [CAM_TIGHT[0], CAM_TIGHT[1] + dy_cam, CAM_TIGHT[2], CAM_TIGHT[3] + dy_cam]
    F(cam, 100, {
        "f1_body": {"visible": True, "dy": BODY_DY * t_body, "scale": 1 - 0.008 * t_body},
        "f1_head": {"visible": True, "dy": HEAD_DY * t_head, "rot": 1.6 * t_head},
    })

# --- B. release: 5 frames, fast zoom out, swap on frame 0 --------------------
for i in range(5):
    t = ease_out(i / 4)
    cam_from = [CAM_TIGHT[0], CAM_TIGHT[1] + CAM_FOLLOW * BODY_DY, CAM_TIGHT[2], CAM_TIGHT[3] + CAM_FOLLOW * BODY_DY]
    cam = [lerp(a, b, t) for a, b in zip(cam_from, CAM_WIDE)]
    L = {"f2_body": {"visible": True}}
    for n in CLAWS: L[n] = {"visible": True}                       # still attached here
    L["fx_speed"] = speed(cam[2] - cam[0], cam, i % 2 == 0)        # flash on twos
    F(cam, 60, L)

# --- C. let go: 2.0 s creep (25f x 80ms), then gone in 3 frames with blur, then 8f hold on empty hands
from scatter_exit import scatter_exit
items = {n: (ang, k) for n, (_pv, ang, k) in CLAWS.items()}
def wrap(layers_c, flash):
    L = {n: {"visible": False} for n in parts}      # every part off unless named - substeps need this too
    L["f2_body"] = {"visible": True}
    for n, tr in layers_c.items():
        L[n] = {"visible": True, "parent": None, **tr}
    L["fx_speed"] = speed(1920, CAM_WIDE, flash)
    return L
for i, lay, subs in scatter_exit(items, drift_frames=25, drift_px=70, snap_frames=3, exit_px=2600):
    is_snap = i >= 25
    fr_layers = wrap(lay, is_snap)                       # flash across the whole discard
    F(CAM_WIDE, 80 if not is_snap else 60, fr_layers)
    if subs:
        frames[-1]["substeps"] = [wrap(st, is_snap and (k % 2 == 0)) for k, st in enumerate(subs)]
for i in range(8):
    F(CAM_WIDE, 80, {"f2_body": {"visible": True}})      # gone: no lines, empty hands

json.dump({"base_dir": STAGE, "out": "/mnt/user-data/outputs/cut87_claw_drop.gif",
           "out_size": [980, 551], "parts": parts, "frames": frames,
           "probes": [{"name": "clawL1", "point": [1028, 952], "parts": ["f2_body", "claw_L1"]},
                      {"name": "chin", "point": [1492, 579], "parts": ["f1_head"]}]},
          open("cut87_spec.json", "w"), indent=1)
print("frames:", len(frames))
