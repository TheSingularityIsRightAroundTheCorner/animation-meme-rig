#!/usr/bin/env python3
"""build_pant_steam_v3.py — steam BEHIND the characters, optional haze in front.

    gradient background
    steam_back    <- the drawn steam, full strength, masked to its panel
    characters
    steam_front   <- same art blurred + very low opacity (depth only)
    panel line

FRONT_HAZE = False renders the "behind only" version.
"""
import math
import random
import sys
from PIL import Image, ImageFilter

UP = "/mnt/user-data/uploads"
W, H = 1920, 1080
OUT_H = 470

FRONT_HAZE = "--haze" in sys.argv
OUT = ("/mnt/user-data/outputs/pant_steam_v3b_behind_plus_haze.gif" if FRONT_HAZE
       else "/mnt/user-data/outputs/pant_steam_v3a_behind_only.gif")

LINE_X0, LINE_SLOPE, LINE_HALF = 59.0, 1.6886, 46
NECK = {"claude": [1500, 640], "gpt": [350, 900]}
CROWN = {"claude": [1455, 60], "gpt": [400, 370]}

BREATH = [                      # (body_pose, head_dy, hair_dy, tilt, ms)
    (1,   0,  -5,  0.0, 110),
    (1,   0,   0,  0.0, 210),
    (1, -14,  -4, -1.2,  55),
    (2, -26, -14, -2.8,  55),
    (2, -23, -30, -2.5, 110),
    (2, -23, -23, -2.5, 210),
    (2, -10, -26, -1.2,  55),
    (1,   4,  -9,  0.4,  55),
]
HALF = len(BREATH) // 2
N_BREATHS = 2

STEAM_PHASE = 4
STEAM_RISE = 155
STEAM_GROW = 0.26
WOBBLE = 11
JITTER = 13
PEAK_OPACITY = 0.85

HAZE_BLUR = 9
HAZE_OPACITY = 0.20     # must stay low — if you can see its shape, it's too much
HAZE_SCALE = 1.14
HAZE_LEAD = 0.7         # front wisp runs slightly ahead of the back mass


def load(name):
    return Image.open(f"{UP}/{name}").convert("RGBA")


def panel_mask(side):
    m = Image.new("L", (W, H), 0)
    px = m.load()
    for y in range(H):
        edge = LINE_X0 + LINE_SLOPE * y
        if side == "left":
            x0, x1 = 0, max(0, min(W, int(edge - LINE_HALF)))
        else:
            x0, x1 = max(0, min(W, int(edge + LINE_HALF))), W
        for x in range(x0, x1):
            px[x, y] = 255
    return m


def line_only(with_line, plain):
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a, b, o = with_line.load(), plain.load(), out.load()
    for y in range(H):
        for x in range(W):
            r1, g1, b1, _ = a[x, y]
            r2, g2, b2, _ = b[x, y]
            if abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2) > 40:
                o[x, y] = (r1, g1, b1, 255)
    return out


def place(canvas, im, dx=0, dy=0, rot=0.0, pivot=None, scale=1.0, opacity=1.0):
    if opacity <= 0.01:
        return
    layer = im
    cx, cy = pivot if pivot else (W // 2, H // 2)
    if scale != 1.0:
        layer = layer.transform(
            (W, H), Image.AFFINE,
            (1 / scale, 0, cx - cx / scale, 0, 1 / scale, cy - cy / scale),
            resample=Image.BICUBIC)
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
    if opacity < 1.0:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * opacity)))
    canvas.alpha_composite(layer, (int(dx), int(dy)))


def steam_state(step, phase=0.0, lead=0.0):
    t = ((step + lead) % len(BREATH)) / len(BREATH)
    op = t / 0.15 if t < 0.15 else max(0.0, 1 - (t - 0.15) / 0.85) ** 1.7
    return dict(dx=WOBBLE * math.sin(t * math.pi * 3.0 + phase),
                dy=-STEAM_RISE * t,
                scale=1 + STEAM_GROW * t,
                opacity=op * PEAK_OPACITY)


def draw_steam(canvas, art, mask, st, rng, blur=0, opacity_mul=1.0, scale_mul=1.0):
    puff = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(puff, art,
          dx=st["dx"] + rng.randint(-JITTER, JITTER),
          dy=st["dy"] + rng.randint(-3, 3),
          scale=st["scale"] * scale_mul,
          pivot=(W // 2, H // 2),
          opacity=st["opacity"] * opacity_mul)
    if blur:
        puff = puff.filter(ImageFilter.GaussianBlur(blur))
    puff.putalpha(Image.composite(puff.getchannel("A"),
                                  Image.new("L", (W, H), 0), mask))
    canvas.alpha_composite(puff)


def character(canvas, tag, pose, parts):
    body, head_dy, hair_dy, tilt, _ = pose
    place(canvas, parts[f"{tag}_body{body}"], dy=head_dy * 0.70)
    place(canvas, parts[f"{tag}_head"], dy=head_dy, rot=tilt, pivot=NECK[tag])
    place(canvas, parts[f"{tag}_hair"], dy=hair_dy, rot=tilt * 1.1, pivot=CROWN[tag])


def main():
    parts = {
        "claude_body1": load("몸_1_-_claude.png"),
        "claude_body2": load("몸_2_-_claude.png"),
        "claude_head": load("클로드_지피티_헤드_-_claude.png"),
        "claude_hair": load("클로드_지피티_헤어_-_claude.png"),
        "gpt_body1": load("몸_1_-gpt.png"),
        "gpt_body2": load("몸_2_-_gpt.png"),
        "gpt_head": load("클로드_지피티_헤드_-_gpt.png"),
        "gpt_hair": load("클로드_지피티_헤어_-_gpt.png"),
    }
    steam = {"claude": load("지피티_김_클로드_김_-_claude.png"),
             "gpt": load("지피티_김_클로드_김_-_gpt.png")}
    bg_plain, bg_line = load("클로지피_배경.png"), load("배경.png")
    lines = line_only(bg_line, bg_plain)
    masks = {"claude": panel_mask("right"), "gpt": panel_mask("left")}
    phase = {"claude": 0.0, "gpt": 1.7}

    rng = random.Random(7)
    frames, durs = [], []
    for _ in range(N_BREATHS):
        for i in range(len(BREATH)):
            steps = {"claude": i - STEAM_PHASE, "gpt": i + HALF - STEAM_PHASE}
            poses = {"claude": BREATH[i], "gpt": BREATH[(i + HALF) % len(BREATH)]}

            canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            canvas.alpha_composite(bg_plain)

            for tag in ("gpt", "claude"):                       # steam BEHIND
                draw_steam(canvas, steam[tag], masks[tag],
                           steam_state(steps[tag], phase[tag]), rng)

            character(canvas, "gpt", poses["gpt"], parts)
            character(canvas, "claude", poses["claude"], parts)

            if FRONT_HAZE:                                     # depth only
                for tag in ("gpt", "claude"):
                    draw_steam(canvas, steam[tag], masks[tag],
                               steam_state(steps[tag], phase[tag], HAZE_LEAD),
                               rng, blur=HAZE_BLUR,
                               opacity_mul=HAZE_OPACITY, scale_mul=HAZE_SCALE)

            canvas.alpha_composite(lines)
            frames.append(canvas.convert("RGB").resize(
                (int(W * OUT_H / H), OUT_H), Image.LANCZOS))
            durs.append(BREATH[i][4])

    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=True)
    print(f"{OUT}  {frames[0].size}  {len(frames)}frames")


if __name__ == "__main__":
    main()
