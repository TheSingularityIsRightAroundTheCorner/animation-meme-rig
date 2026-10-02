#!/usr/bin/env python3
"""Small portable mouth-acting preview; coordinates belong to a measured profile."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.local_mesh import ellipse_weight, load_srgb, warp_local
from core.output import save_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output', required=True, help='GIF/MP4 or extensionless PNG sequence directory')
    args = parser.parse_args()
    cfg = json.loads(Path(args.profile).read_text())
    source = load_srgb(args.source)
    if list(source.size) != cfg['source_size']:
        parser.error('source_size differs: remeasure the profile for this drawing')
    duration, fps = cfg['duration'], cfg['fps']
    if not 0 < duration <= 10 or not 1 <= fps <= 60:
        parser.error('preview supports duration (0,10] and fps [1,60]')
    if round(duration*fps) < 1:
        parser.error('duration must include at least one frame')
    frames = []
    for i in range(round(duration*fps)):
        t = i/fps
        acting_t = math.floor(t*fps/2)*2/fps if cfg.get('on_twos') else t
        amount = cfg['amplitude']*math.sin(cfg['angular_frequency']*acting_t)
        if any(a <= t < b for a,b in cfg.get('pauses', [])):
            amount = 0
        cx,cy,rx,ry = cfg['mouth']
        def inverse(x,y):
            w = ellipse_weight(x,y,cx,cy,rx,ry)
            return x, y-amount*(y-cy)*w
        frame = warp_local(source, inverse, step=cfg.get('mesh_step',24))
        if cfg.get('preview_width'):
            width = cfg['preview_width']
            frame = frame.resize((width, round(width*source.height/source.width)))
        frames.append(frame)
    # GIF centiseconds, rounded at absolute boundaries to avoid duration drift.
    durations = [(round((i+1)*100/fps)-round(i*100/fps))*10 for i in range(len(frames))]
    save_frames(frames, args.output, fps=fps,
                durations=durations if Path(args.output).suffix.lower()=='.gif' else None)

if __name__ == '__main__':
    main()
