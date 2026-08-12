#!/usr/bin/env python3
"""자동 타이트 크롭 + '전역 공통 팔레트' 투명 GIF.
프레임마다 각자 다른 로컬 팔레트를 쓰면 디코더(특히 macOS Preview 계열)가
프레임 전환 시 disposal=2와 맞물려서 이상하게 그리는 경우가 있어,
전체 프레임을 합쳐 팔레트 하나를 만들고 전 프레임에 동일하게 적용한다."""
import sys, json, math, os
from PIL import Image
import numpy as np

def load(p): return Image.open(p).convert('RGBA')
def fade(im, a):
    if a >= 1: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im
def place(canvas, part, W, H, dx=0, dy=0, rot=0, pivot=None, scale=1.0, opacity=1.0):
    im = part
    if rot or scale != 1.0:
        bb = im.getbbox()
        if not bb: return
        crop = im.crop(bb)
        px, py = pivot if pivot else ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
        if scale != 1.0:
            crop = crop.resize((max(1,int(crop.width*scale)), max(1,int(crop.height*scale))), Image.LANCZOS)
        ox, oy = (px-bb[0])*scale, (py-bb[1])*scale
        if rot:
            rc = crop.rotate(rot, resample=Image.BICUBIC, expand=True, center=(ox,oy), translate=(0,0))
            ox += (rc.width-crop.width)/2; oy += (rc.height-crop.height)/2
            crop = rc
        layer = Image.new('RGBA',(W,H),(0,0,0,0))
        layer.alpha_composite(fade(crop,opacity),(int(px-ox+dx), int(py-oy+dy)))
        canvas.alpha_composite(layer)
    else:
        canvas.alpha_composite(fade(im,opacity),(int(dx),int(dy)))

MARGIN = int(sys.argv[2]) if len(sys.argv) > 2 else 50
spec = json.load(open(sys.argv[1]))
base_dir = spec['base_dir']
P = {k: load(os.path.join(base_dir, v)) for k, v in spec['parts'].items()}
W, H = next(iter(P.values())).size

raw = []
for fr in spec['frames']:
    ch = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for lay in fr['layers']:
        place(ch, P[lay['part']], W, H, lay.get('dx',0), lay.get('dy',0),
              lay.get('rot',0), lay.get('pivot'), lay.get('scale',1.0), lay.get('opacity',1.0))
    raw.append(ch)

union = np.zeros((H, W), dtype=bool)
for fr in raw:
    union |= (np.array(fr)[..., 3] > 10)
ys, xs = np.where(union)
x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
x0 = max(0, x0-MARGIN); y0 = max(0, y0-MARGIN); x1 = min(W, x1+MARGIN); y1 = min(H, y1+MARGIN)
FW, FH = x1-x0, y1-y0
t = spec.get('height', 620)
out_w = int(FW * t / FH)
print(f"자동 크롭: x{x0}-{x1} y{y0}-{y1}  출력 {out_w}x{t}")

cropped_rgba = [im.crop((x0,y0,x1,y1)).resize((out_w,t), Image.LANCZOS) for im in raw]

# ---- 전역 팔레트 생성: 모든 프레임을 가로로 이어붙여 한번에 quantize ----
strip = Image.new('RGB', (out_w, t*len(cropped_rgba)), (255,255,255))
for i, im in enumerate(cropped_rgba):
    strip.paste(im.convert('RGB'), (0, i*t))
master_pal_img = strip.convert('P', palette=Image.ADAPTIVE, colors=255)
master_palette = master_pal_img.getpalette()

pal_frames, durs = [], []
for fr, im in zip(spec['frames'], cropped_rgba):
    alpha = im.split()[3]
    rgb = im.convert('RGB')
    quant = rgb.quantize(palette=master_pal_img, dither=Image.NONE)
    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
    quant.paste(255, mask)
    pal_frames.append(quant)
    durs.append(fr.get('ms', 42))

dst = spec.get('out', 'out.gif')
pal_frames[0].save(dst, save_all=True, append_images=pal_frames[1:],
                    duration=durs, loop=0, disposal=2, transparency=255, optimize=False)
print(f"{dst}  {(out_w,t)}  {len(pal_frames)}frames  {os.path.getsize(dst)//1024}KB (전역 팔레트, transparent)")
