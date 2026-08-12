#!/usr/bin/env python3
"""파츠 PNG 사전 점검: 캔버스 일치, 알파 유무, bbox, 중복, 접합 후보 좌표."""
import sys, glob, os
from PIL import Image
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else '.'
files = sorted(glob.glob(os.path.join(d, '*.png')))
info, sizes, bboxes = [], {}, {}
for f in files:
    im = Image.open(f).convert('RGBA')
    a = np.array(im)
    opaque = a[..., 3].min() == 255
    bb = im.getbbox()
    if opaque:  # 흰 배경 flatten 의심 → 비흰색 영역으로 재측정
        nw = (a[..., :3] < 240).any(-1)
        ys, xs = np.where(nw)
        bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
    info.append((os.path.basename(f), im.size, opaque, bb))
    sizes.setdefault(im.size, []).append(os.path.basename(f))
    bboxes.setdefault(bb, []).append(os.path.basename(f))

print("=== 파츠 목록 ===")
for n, s, op, bb in info:
    flag = "  [!] 알파 없음 = 흰배경 flatten" if op else ""
    print(f"{n:40s} {s}  bbox={bb}{flag}")

if len(sizes) > 1:
    print("\n[!] 캔버스 크기 불일치 — 정렬 깨짐. 재출력 요청할 것:")
    for s, ns in sizes.items():
        print(f"   {s}: {', '.join(ns)}")
else:
    print(f"\n캔버스 통일 OK: {list(sizes)[0]}")

dups = {b: n for b, n in bboxes.items() if len(n) > 1 and b}
if dups:
    print("\n[i] bbox 동일 = 같은 파츠 중복 가능:")
    for b, ns in dups.items():
        print(f"   {b}: {', '.join(ns)}")

def rows(f, ys):
    a = np.array(Image.open(f).convert('RGBA'))[..., 3] > 10
    out = []
    for y in ys:
        if 0 <= y < a.shape[0]:
            xs = np.where(a[y])[0]
            out.append((y, (int(xs.min()), int(xs.max())) if len(xs) else None))
    return out

body = [f for f in files if '몸통' in f or 'body' in f.lower()]
legs = [f for f in files if '다리' in f or 'leg' in f.lower()]
if body and legs:
    bf = body[0]
    a = np.array(Image.open(bf).convert('RGBA'))[..., 3] > 10
    ys, xs = np.where(a)
    bot = int(ys.max())
    xr = np.where(a[bot - 5])[0]
    print(f"\n=== 접합 진단 ===\n몸통 하단 y={bot}, x={xr.min()}~{xr.max()}")
    for lf in legs:
        la = np.array(Image.open(lf).convert('RGBA'))[..., 3] > 10
        lys, lxs = np.where(la)
        top = int(lys.min())
        print(f"\n{os.path.basename(lf)}  상단 y={top}")
        for y, r in rows(lf, [top + 10, bot, bot + 20, bot + 50, bot + 80]):
            mark = ""
            if r:
                mark = " <-- 몸통과 겹침" if not (r[1] < xr.min() or r[0] > xr.max()) else " (몸통 밖)"
            print(f"   y={y}: {r}{mark}")
    print("\n※ '몸통 밖'만 나오면 다리를 옮기지 말고 몸통을 아래로 내릴 것.")
