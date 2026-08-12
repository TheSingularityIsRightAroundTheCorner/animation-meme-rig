#!/usr/bin/env python3
"""spec.json -> 루프 GIF.
프레임은 레이어 목록. 각 레이어에 이동/회전/스케일/불투명도를 줄 수 있다.
humanoid 축약형(body_dy/legs_dy/head_dy)도 계속 지원."""
import sys, json, math, os
from PIL import Image

def load(p): return Image.open(p).convert('RGBA')

def fit(p, px):
    im = load(p); im = im.crop(im.getbbox())
    w, h = im.size; s = px / max(w, h)
    return im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)

def fade(im, a):
    if a >= 1: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im

def place(canvas, part, W, H, dx=0, dy=0, rot=0, pivot=None, scale=1.0, opacity=1.0):
    """pivot(원본 좌표) 기준 회전/확대 후 dx,dy 이동해서 합성. pivot 없으면 파츠 중심."""
    im = part
    if rot or scale != 1.0:
        bb = im.getbbox()
        if not bb: return
        crop = im.crop(bb)
        px, py = pivot if pivot else ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
        if scale != 1.0:
            crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))), Image.LANCZOS)
        ox, oy = (px - bb[0]) * scale, (py - bb[1]) * scale   # crop 내 피벗
        if rot:
            rc = crop.rotate(rot, resample=Image.BICUBIC, expand=True,
                             center=(ox, oy), translate=(0, 0))
            # expand 보정: 회전 후 피벗의 새 위치
            ox += (rc.width - crop.width) / 2
            oy += (rc.height - crop.height) / 2
            crop = rc
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        layer.alpha_composite(fade(crop, opacity), (int(px - ox + dx), int(py - oy + dy)))
        canvas.alpha_composite(layer)
    else:
        canvas.alpha_composite(fade(im, opacity), (int(dx), int(dy)))

spec = json.load(open(sys.argv[1]))
base = spec.get('base_dir', '.')
P = {k: load(os.path.join(base, v)) for k, v in spec['parts'].items()}
W, H = next(iter(P.values())).size
crop = spec.get('crop', [0, 0, W, H])
FW, FH = crop[2] - crop[0], crop[3] - crop[1]

cells, bgsp = [], {}
bgc = spec.get('background')
if bgc:
    for k, v in bgc['sprites'].items():
        bgsp[k] = fit(os.path.join(base, v), bgc.get('size', 150))
    keys = list(bgsp); cols, rows = bgc.get('cols', 5), bgc.get('rows', 6)
    for r in range(rows):
        for c in range(cols):
            cells.append((int((c + .5 + (.5 if r % 2 else 0)) * FW / cols), int((r + .5) * FH / rows),
                          keys[(r + c) % len(keys)], (r * cols + c) % 2, (r * 3 + c * 5) % 12))

def bg(f, n):
    layer = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    for x, y, k, mode, ph in cells:
        t = ((f + ph) % n) / n
        ang = 360 * t if mode else bgc.get('wobble', 22) * math.sin(2 * math.pi * t)
        rot = fade(bgsp[k].rotate(ang, resample=Image.BICUBIC, expand=True), bgc.get('opacity', .30))
        layer.alpha_composite(rot, (x - rot.width // 2, y - rot.height // 2))
    return layer

def humanoid_layers(fr):
    """축약형 -> 레이어 목록 변환. 레이어 순서 규칙 내장."""
    dyb, dyl, hd = fr.get('body_dy', 0), fr.get('legs_dy', 0), fr.get('head_dy', 0)
    L = [{"part": p, "dy": dyl} for p in fr.get('legs', [])]
    arms = [{"part": p, "dy": dyb} for p in fr.get('arms', [])]
    if fr.get('arms_behind'): L += arms
    L += [{"part": spec['body'], "dy": dyb}, {"part": spec['head'], "dy": dyb + hd}]
    if not fr.get('arms_behind'): L += arms
    return L

seq = spec['frames']; N = len(seq); out, durs = [], []
for f, fr in enumerate(seq):
    cv = Image.new('RGBA', (FW, FH), tuple(spec.get('bg_color', [255, 255, 255, 255])))
    if cells: cv.alpha_composite(bg(f, N))
    ch = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for lay in (fr['layers'] if 'layers' in fr else humanoid_layers(fr)):
        place(ch, P[lay['part']], W, H, lay.get('dx', 0), lay.get('dy', 0),
              lay.get('rot', 0), lay.get('pivot'), lay.get('scale', 1.0), lay.get('opacity', 1.0))
    cv.alpha_composite(ch.crop(tuple(crop)))
    for m in spec.get('mascots', []):
        sp = fit(os.path.join(base, m['file']), m.get('size', 400))
        hop = int(m.get('hop', 14) * abs(math.sin(math.pi * f / 3)))
        sp = sp.rotate(m.get('wobble', 8) * math.sin(2 * math.pi * f / N), resample=Image.BICUBIC, expand=True)
        cv.alpha_composite(sp, (FW - sp.width - m.get('right', 40), FH - sp.height - m.get('bottom', 30) - hop))
    t = spec.get('height', 620)
    out.append(cv.resize((int(FW * t / FH), t), Image.LANCZOS).convert('RGB'))
    durs.append(fr.get('ms', 110))

dst = spec.get('out', 'out.gif')
out[0].save(dst, save_all=True, append_images=out[1:], duration=durs, loop=0, optimize=True)
print(f"{dst}  {out[0].size}  {len(out)}frames  {os.path.getsize(dst)//1024}KB")
