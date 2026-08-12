#!/usr/bin/env python3
"""GIF 프레임을 격자 이미지로 합쳐 육안 검수용으로 저장."""
import sys, os
from PIL import Image
p = sys.argv[1]
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 4
im = Image.open(p); frames = []; i = 0
try:
    while True:
        im.seek(i); frames.append(im.convert('RGB')); i += 1
except EOFError:
    pass
w, h = frames[0].size
rows = (len(frames) + cols - 1) // cols
sheet = Image.new('RGB', (w * cols, h * rows), 'white')
for i, f in enumerate(frames):
    sheet.paste(f, (w * (i % cols), h * (i // cols)))
scale = min(1.0, 1600 / sheet.width)
sheet = sheet.resize((int(sheet.width * scale), int(sheet.height * scale)))
out = os.path.splitext(p)[0] + '_sheet.png'
sheet.save(out)
print(f"{len(frames)} frames -> {out}")
