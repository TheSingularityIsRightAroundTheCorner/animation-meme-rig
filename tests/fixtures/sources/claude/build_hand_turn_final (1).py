"""hand_turn_25d v6 - the turn is a real perspective rotation, so it has a direction.

v3-v5 squashed the silhouette toward a chosen edge. That never encoded direction: an
orthographic plane rotation is left/right symmetric, so both ways looked identical and I
kept "reversing" something that had no sign to begin with. v6 rotates the plane about the
wrist axis and projects it through a finite camera. The near edge grows and swings outward,
the far edge shrinks and pulls in - that asymmetry is what the eye reads as direction.

THETA > 0 : thumb edge (screen left) comes forward -> the front face sweeps to the RIGHT.
THETA < 0 : the little-finger edge comes forward instead.
"""
import json, math

STAGE = "/home/claude/stage25b"
AXIS_X, AXIS_Y = 108.8, 6.0          # measured wrist centre = the real turn axis
FOCAL = 130.0                        # the hand is only ~94px wide, so the camera has to be close;
                                     # at 330 the near/far difference was 13% and still read as symmetric
THETA_END = 45.0                     # 62도까지 돌리면 cos 0.47이라 폭이 절반이 됨. 45도면 71%라
                                     # 덜 납작하고, 원근 비대칭은 25%로 남아 방향은 그대로 읽힘
SIGN = +1                            # +1 sweeps the front face right (thumb comes to camera)
SWAP_AT = 1.0                        # the swap happens at the end of the turn

BACK = {"bc1": (91.0, 153.0), "bc2": (111.0, 194.0), "bc3": (132.0, 187.0)}   # x, fingertip y
SIDE = {"sc1": (276.0, 139.0), "sc2": (267.0, 199.0), "sc3": (248.0, 190.0)}
SIDE_WRIST_X = 275.3

P = lambda f, pv, z: {"file": f, "pivot": pv, "parent": None, "z": z}
parts = {"hand_back": P("hand_back.png", [AXIS_X, AXIS_Y], 5),
         "hand_side": P("hand_side.png", [AXIS_X, AXIS_Y], 5)}
for n, pv in BACK.items(): parts[n] = P(n + ".png", list(pv), 10)
for n, pv in SIDE.items(): parts[n] = P(n + ".png", list(pv), 10)

smooth = lambda t: t * t * (3 - 2 * t)
snap   = lambda t: 1 - (1 - t) ** 4

frames = []
def F(layers, ms=60):
    base = {n: {"visible": False} for n in parts}
    base.update(layers)
    frames.append({"layers": base, "camera": [40, 0, 200, 312], "ms": ms})

def turn(theta):
    return {"axis_x": AXIS_X, "axis_y": AXIS_Y, "theta": theta, "focal": FOCAL}

def pose_back(theta, out):
    L = {"hand_back": {"visible": True, "turn": turn(theta), "z": 5}}
    th = math.radians(theta)
    depths = {n: (rx - AXIS_X) * math.sin(th) for n, (rx, _) in BACK.items()}
    order = sorted(depths, key=lambda n: -depths[n])          # far (larger depth) draws first
    for i, (n, (rx, ry)) in enumerate(BACK.items()):
        e = out.get(i, 0.0)
        if e <= 0.001:
            L[n] = {"visible": False}; continue
        L[n] = {"visible": True, "sy": max(0.02, e),          # grows from the fingertip
                "turn": turn(theta), "z": 10 + order.index(n)}
    return L

def pose_side(settle, out):
    dx = AXIS_X - SIDE_WRIST_X
    L = {"hand_side": {"visible": True, "dx": dx, "dy": 3.0, "sx": 1 + 0.16 * settle, "z": 5}}
    for i, (n, (rx, ry)) in enumerate(SIDE.items()):
        e = out.get(i, 0.0)
        if e <= 0.001:
            L[n] = {"visible": False}; continue
        L[n] = {"visible": True, "dx": dx, "dy": 3.0,
                "sx": 1 + 0.16 * settle, "sy": max(0.02, e), "z": 12 - i}
    return L

ramp = lambda i, s, ln: max(0.0, min(1.0, (i - s + 1) / ln))
N, ALL = 18, {0: 1, 1: 1, 2: 1}

for _ in range(4):                                            # bare hand
    F(pose_back(0.0, {}), 90)
for i in range(N):                                            # turn + blades out
    th = SIGN * THETA_END * smooth((i + 1) / N)
    F(pose_back(th, {2: snap(ramp(i, 1, 3)), 1: snap(ramp(i, 5, 3)), 0: snap(ramp(i, 9, 3))}), 60)
for i in range(4):                                            # hard cut to the drawn side pose
    F(pose_side(1 - (i + 1) / 4, ALL), 60)
for _ in range(6):
    F(pose_side(0.0, ALL), 80)
for i in range(4):                                            # frontmost blade goes in first
    F(pose_side(0.0, {0: 1 - snap((i + 1) / 4), 1: 1, 2: 1}), 60)
for i in range(N):                                            # turn home, remaining blades slide in
    th = SIGN * THETA_END * smooth(1 - (i + 1) / N)
    F(pose_back(th, {0: 0.0, 1: 1 - snap(ramp(i, 1, 3)), 2: 1 - snap(ramp(i, 6, 3))}), 60)
for _ in range(4):
    F(pose_back(0.0, {}), 90)

json.dump({"base_dir": STAGE, "out": "/mnt/user-data/outputs/hand_turn_25d_final_A.gif",
           "out_size": [480, 936], "parts": parts, "frames": frames},
          open("hand_turn_v6_spec.json", "w"), indent=1)
print("frames:", len(frames))
