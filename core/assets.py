"""Input handling. Existing artwork is never replaced or rewritten."""
from collections import deque
from pathlib import Path
import unicodedata
import numpy as np
from PIL import Image


def resolve_asset(root, name):
    path = Path(name)
    if not path.is_absolute():
        path = Path(root) / path
    parent = path.parent
    normalized = unicodedata.normalize('NFC', path.name)
    matches = [p for p in parent.iterdir() if p.is_file() and unicodedata.normalize('NFC', p.name) == normalized] if parent.is_dir() else []
    if len(matches) > 1:
        raise ValueError(f'ambiguous Unicode asset: {name}')
    if not matches:
        raise FileNotFoundError(f'missing supplied artwork: {path}')
    return matches[0]


def validate_canvases(images):
    if not images:
        raise ValueError('no image parts')
    size = next(iter(images.values())).size
    for name, image in images.items():
        if image.size != size:
            raise ValueError(f'canvas mismatch: {name}: {image.size}, expected {size}')
    return size


def remove_edge_white(image, threshold=250):
    """Opt-in cleanup of edge-connected white only; interior whites survive."""
    a = np.array(image.convert('RGBA'))
    h, w = a.shape[:2]
    white = np.all(a[..., :3] >= threshold, axis=2)
    visited = np.zeros((h, w), bool)
    queue = deque([(x, y) for x in range(w) for y in (0, h-1)] + [(x, y) for y in range(h) for x in (0, w-1)])
    while queue:
        x, y = queue.popleft()
        if not (0 <= x < w and 0 <= y < h) or visited[y, x] or not white[y, x]:
            continue
        visited[y, x] = True
        queue.extend(((x-1,y), (x+1,y), (x,y-1), (x,y+1)))
    a[visited, 3] = 0
    return Image.fromarray(a)
