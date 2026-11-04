"""Encode motion-repair frames. Requires ffmpeg; no Python dependencies."""
from pathlib import Path
import subprocess
import zipfile
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'captures').resolve()
MEDIA = Path(sys.argv[2] if len(sys.argv) > 2 else 'exports').resolve()
MEDIA.mkdir(exist_ok=True)

def run(args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)

for shot in ['cross', 'run']:
    pattern = str(ROOT / (shot + '_frames') / 'frame_%04d.png')
    source = ['-framerate', '24', '-i', pattern]
    run([*source, '-c:v', 'qtrle', '-pix_fmt', 'argb', str(MEDIA / (shot + '_alpha_animation.mov'))])
    run([*source, '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-crf', '25', '-b:v', '0',
         '-deadline', 'good', '-cpu-used', '4', '-row-mt', '1', str(MEDIA / (shot + '_alpha.webm'))])
    run(['-f', 'lavfi', '-i', 'color=c=0x263244:s=1920x1080:r=24', *source,
         '-filter_complex', '[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p',
         '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-movflags', '+faststart',
         str(MEDIA / (shot + '_preview.mp4'))])
    print(shot + ': MOV, WebM, MP4 encoded', flush=True)

run(['-i', str(MEDIA / 'cross_preview.mp4'), '-i', str(MEDIA / 'run_preview.mp4'),
     '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[out]', '-map', '[out]',
     '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-movflags', '+faststart',
     str(MEDIA / 'hero_camera_preview.mp4')])
with zipfile.ZipFile(MEDIA / 'transparent_png_24fps.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for shot in ['cross','run']:
        for frame in sorted((ROOT / (shot + '_frames')).glob('frame_*.png')):
            archive.write(frame, Path(shot) / frame.name)
print('Preview and transparent PNG package ready', flush=True)
