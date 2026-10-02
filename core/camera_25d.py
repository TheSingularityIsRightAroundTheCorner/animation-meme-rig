"""Measured camera guides and explicit adapters for the historical camera spec.

Guide coordinates are xywh in old authoring docs; rendered frames use xyxy.
Camera coordinates are independent of world/screen effect coordinate spaces.
"""
from copy import deepcopy
import math
import numpy as np
from PIL import Image


def _rect(rect):
    if len(rect) != 4 or not all(math.isfinite(float(v)) for v in rect):
        raise ValueError('camera rectangle must contain four finite values')
    x0,y0,x1,y1 = map(float, rect)
    if x1 <= x0 or y1 <= y0:
        raise ValueError('camera rectangle must have positive width and height')
    return x0,y0,x1,y1


def xywh_to_xyxy(rect):
    if len(rect) != 4:
        raise ValueError('xywh rectangle requires four values')
    x,y,w,h = rect
    return _rect((x,y,x+w,y+h))


def measure_frame(image, canvas_size, color='blue'):
    """Measure visible colored guide pixels; do not infer from transparent RGB."""
    if image.size != tuple(canvas_size):
        raise ValueError('guide canvas size differs from scene canvas')
    channels={'red':0,'green':1,'blue':2}
    if color not in channels:
        raise ValueError('guide color must be red, green, or blue')
    a=np.asarray(image.convert('RGBA')).astype(np.int16)
    channel=channels[color]
    other=[i for i in range(3) if i != channel]
    mask=(a[...,3]>0)&(a[...,channel]>=80)&(a[...,channel]>a[...,other[0]]+40)&(a[...,channel]>a[...,other[1]]+40)
    ys,xs=np.where(mask)
    if not len(xs):
        raise ValueError(f'no visible {color} guide pixels')
    return int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)


def _ease(progress, easing, power):
    t=float(progress)
    if not math.isfinite(t) or not 0 <= t <= 1 or power <= 0:
        raise ValueError('progress must be in 0..1 and easing power positive')
    if easing in ('smooth','ease_in_out'):
        return t*t*(3-2*t)
    if easing=='ease_out': return 1-(1-t)**power
    if easing=='ease_in': return t**power
    if easing in ('linear','snap'): return t
    raise ValueError(f'unsupported camera easing: {easing}')


def camera_at(start, end, progress, easing='smooth', power=3.0):
    """Interpolate an xyxy crop or {eye,target,fov} camera with exact endpoints."""
    t=_ease(progress,easing,power)
    if isinstance(start,dict) or isinstance(end,dict):
        if not isinstance(start,dict) or not isinstance(end,dict) or set(start)!=set(end):
            raise ValueError('camera endpoints must use matching fields')
        return {key:(np.asarray(start[key],float)+(np.asarray(end[key],float)-start[key])*t).tolist() for key in start}
    a,b=np.asarray(_rect(start)),np.asarray(_rect(end))
    return tuple(a+(b-a)*t)


def pose_at(schedule, progress):
    if not schedule or not 0 <= progress <= 1:
        raise ValueError('pose schedule and progress in 0..1 required')
    ordered=sorted(schedule,key=lambda item:item['at'])
    if any(not 0 <= item['at'] <= 1 for item in ordered):
        raise ValueError('pose swap times must be in 0..1')
    selected=None
    for item in ordered:
        if item['at'] <= progress: selected=item['part']
    return selected


def crop_frame(image, rect, out_size):
    x0,y0,x1,y1=_rect(rect)
    if x0<0 or y0<0 or x1>image.width or y1>image.height:
        raise ValueError('camera crop exceeds canvas bounds')
    if len(out_size)!=2 or min(out_size)<1:
        raise ValueError('positive output dimensions required')
    rounded=tuple(int(round(v)) for v in (x0,y0,x1,y1))
    _rect(rounded)
    return image.crop(rounded).resize(tuple(out_size),Image.LANCZOS)


def compile_shot(shot, canvas_size):
    """Compile old high-level xywh shot data without silently changing blend space.

    Returned camera_substeps are complete xyxy camera samples. A renderer must
    explicitly consume them; they are not rig_tree's layer-transform substeps.
    The authored aspect ratio is retained: no silent 16:9 stretching of guides.
    """
    count=int(shot.get('frames',14))
    if count<2: raise ValueError('camera move requires at least two frames')
    if min(canvas_size)<=0: raise ValueError('positive canvas dimensions required')
    start=xywh_to_xyxy(shot['frame_start'])
    end=xywh_to_xyxy(shot.get('frame_end',[0,0,*canvas_size]))
    easing=shot.get('easing','ease_out');power=float(shot.get('ease_power',2))
    hold_in=int(shot.get('hold_in',0));hold_out=int(shot.get('hold_out',0))
    ms=float(shot.get('frame_ms',50))
    if hold_in<0 or hold_out<0 or ms<=0: raise ValueError('invalid hold or duration')
    overshoot=float(shot.get('overshoot',0))
    if not 0 <= overshoot <= .08: raise ValueError('overshoot must be in 0..0.08')
    def rect_at(t):
        value=np.asarray(camera_at(start,end,t,easing,power))
        # A late, vanishing sinusoid adds a settle without moving either endpoint.
        if overshoot and 0<t<1:
            value += (np.asarray(end)-start)*overshoot*math.sin(math.pi*t)*t
        result=tuple(float(v) for v in value)
        x0,y0,x1,y1=_rect(result)
        if x0<0 or y0<0 or x1>canvas_size[0] or y1>canvas_size[1]:
            raise ValueError('camera trajectory exceeds canvas bounds; reduce overshoot or use overscan')
        return result
    frames=[]
    for i in range(-hold_in,count+hold_out):
        t=max(0,min(1,i/(count-1)))
        frame={'camera':list(rect_at(t)),'ms':ms}
        for space in ('screen_effects','world_effects'):
            if space in shot: frame[space]=deepcopy(shot[space])
        if shot.get('swap'): frame['pose']=pose_at(shot['swap'],t)
        if 'exposure' in shot:
            a,b=shot['exposure'];frame['exposure']=a+(b-a)*t
        if shot.get('motion_blur') and 0<i<count:
            samples=int(shot.get('blur_steps',6))
            if samples<2: raise ValueError('motion blur needs at least two samples')
            prior=(i-1)/(count-1)
            frame['camera_substeps']=[list(rect_at(prior+(t-prior)*(j+1)/samples)) for j in range(samples)]
        frames.append(frame)
    return frames
