"""Authored pose holds, steam depth, and lens glints extracted from Claude v3.

All artwork and actor-specific pivots/poses belong to caller profiles. `place`
retains Pillow's positive rotation sign from the source steam renderer; it is
opposite to the shared rig's screen-coordinate matrix rotation.
"""
import math
import random
import numpy as np
from PIL import Image, ImageFilter


def breath_layers(profile, step):
    cycle=profile['breath']
    if not cycle: raise ValueError('breath cycle is empty')
    body,head_dy,hair_dy,tilt,_=cycle[(int(step)+int(profile.get('phase',0)))%len(cycle)]
    names=profile['parts']
    return [
        {'part':names[f'body{body}'],'dy':round(head_dy*profile.get('body_ratio',.70),1)},
        {'part':names['head'],'dy':head_dy,'rot':tilt,'pivot':profile['neck']},
        {'part':names['hair'],'dy':hair_dy,'rot':round(tilt*profile.get('hair_rotation_ratio',1.1),1),'pivot':profile['crown']},
    ]


def panel_mask(size, side, line_x0=59.0, slope=1.6886, half=46):
    if side not in ('left','right'): raise ValueError('side must be left or right')
    w,h=map(int,size)
    if w<1 or h<1 or half<0: raise ValueError('positive size and nonnegative divider half-width required')
    # int() in original truncates toward zero, including a negative projected edge.
    edge=line_x0+slope*np.arange(h)
    limit=np.clip(np.trunc(edge-half if side=='left' else edge+half),0,w)
    xx=np.arange(w)[None,:]
    visible=xx<limit[:,None] if side=='left' else xx>=limit[:,None]
    return Image.fromarray((visible*255).astype(np.uint8))


def line_only(with_line, plain, threshold=40):
    if with_line.size != plain.size: raise ValueError('divider source canvases must match')
    a=np.asarray(with_line.convert('RGBA'));b=np.asarray(plain.convert('RGBA'))
    mask=np.abs(a[...,:3].astype(int)-b[...,:3].astype(int)).sum(2)>threshold
    out=np.zeros_like(a);out[mask,:3]=a[mask,:3];out[mask,3]=255
    return Image.fromarray(out)


def place(canvas, im, dx=0, dy=0, rot=0.0, pivot=None, scale=1.0, opacity=1.0):
    if not math.isfinite(scale) or scale<=0: raise ValueError('positive finite scale required')
    if not 0<=opacity<=1: raise ValueError('opacity must be in 0..1')
    if opacity<=.01:return
    layer=im.convert('RGBA')
    w,h=canvas.size
    cx,cy=pivot if pivot is not None else (w//2,h//2)
    if scale != 1:
        layer=layer.transform((w,h),Image.AFFINE,(1/scale,0,cx-cx/scale,0,1/scale,cy-cy/scale),resample=Image.BICUBIC)
    if rot:layer=layer.rotate(rot,resample=Image.BICUBIC,center=(cx,cy))
    if opacity<1:
        layer=layer.copy();layer.putalpha(layer.getchannel('A').point(lambda v:int(v*opacity)))
    canvas.alpha_composite(layer,(int(dx),int(dy)))


def steam_state(step, phase=0.0, lead=0.0, period=8, rise=155, grow=.26, wobble=11, peak_opacity=.85):
    if period<=0 or not 0<=peak_opacity<=1:raise ValueError('invalid steam period or opacity')
    t=((step+lead)%period)/period
    op=t/.15 if t<.15 else max(0.,1-(t-.15)/.85)**1.7
    return dict(dx=wobble*math.sin(t*math.pi*3.+phase),dy=-rise*t,scale=1+grow*t,opacity=op*peak_opacity)


def draw_steam(canvas, art, mask, st, rng, blur=0, opacity_mul=1.0, scale_mul=1.0, jitter=13, jitter_y=3):
    if art.size!=canvas.size or mask.size!=canvas.size:
        raise ValueError('steam art, mask and canvas dimensions must match')
    puff=Image.new('RGBA',canvas.size,(0,0,0,0))
    place(puff,art,dx=st['dx']+rng.randint(-jitter,jitter),dy=st['dy']+rng.randint(-jitter_y,jitter_y),
          scale=st['scale']*scale_mul,pivot=(canvas.width//2,canvas.height//2),opacity=st['opacity']*opacity_mul)
    if blur:puff=puff.filter(ImageFilter.GaussianBlur(blur))
    puff.putalpha(Image.composite(puff.getchannel('A'),Image.new('L',canvas.size,0),mask))
    canvas.alpha_composite(puff)


def render_breath_frame(background, actors, step, divider=None, front_haze=False, rng=None):
    """Render back steam → actors → optional subtle haze → divider.

    Each actor has profile, images {part: RGBA}, and optional steam RGBA/mask L.
    Caller may pass one seeded RNG across frames to reproduce the source clip.
    """
    rng=rng if rng is not None else random.Random(7)
    canvas=Image.new('RGBA',background.size,'white');canvas.alpha_composite(background.convert('RGBA'))
    def steam(actor,front):
        if actor.get('steam') is None:return
        profile=actor['profile'];period=len(profile['breath'])
        st=steam_state(step+profile.get('phase',0)-actor.get('steam_delay',4),
                       phase=actor.get('steam_phase',0),lead=.7 if front else 0,
                       period=period,**actor.get('steam_parameters',{}))
        draw_steam(canvas,actor['steam'],actor['mask'],st,rng,
                   blur=9 if front else 0,opacity_mul=.20 if front else 1,scale_mul=1.14 if front else 1)
    for actor in actors:steam(actor,False)
    for actor in actors:
        profile=actor['profile'];cycle=profile['breath'];body,dy,hair_dy,tilt,_=cycle[(int(step)+int(profile.get('phase',0)))%len(cycle)]
        names=profile['parts'];images=actor['images']
        place(canvas,images[names[f'body{body}']],dy=dy*profile.get('body_ratio',.70))
        place(canvas,images[names['head']],dy=dy,rot=tilt,pivot=profile['neck'])
        # The steam v3 renderer did not round the hair angle (the JSON builder did).
        place(canvas,images[names['hair']],dy=hair_dy,rot=tilt*profile.get('hair_rotation_ratio',1.1),pivot=profile['crown'])
    if front_haze:
        for actor in actors:steam(actor,True)
    if divider is not None:canvas.alpha_composite(divider.convert('RGBA'))
    return canvas


def _on_white(image):
    out=Image.new('RGBA',image.size,'white');out.alpha_composite(image.convert('RGBA'));return out.convert('RGB')


def render_glint(base, lens, lens_mask, spark, config, t_dark, t_lens, spark_scale=0., spark_alpha=0., flash=0.):
    """Darken authored art but replace filled lens mask at original brightness.

    `spark` is the tightly cropped authored sprite; no generated sparkle. Lens
    mask hole filling lives in effects.fill_lens_mask and is explicitly chosen.
    """
    if base.size!=lens.size or lens_mask.size!=base.size:raise ValueError('glint source canvases must match')
    if any(not 0<=v<=1 for v in (t_dark,t_lens,spark_alpha,flash)):raise ValueError('glint opacity controls must be in 0..1')
    base_rgb,lens_rgb=_on_white(base),_on_white(lens)
    k=1-(1-config.get('dark_floor',.46))*t_dark
    image=base_rgb.point(lambda v:int(v*k))
    image.paste(lens_rgb,(0,0),lens_mask.convert('L').point(lambda v:int(v*t_lens)))
    if spark_scale>0 and spark_alpha>0:
        target_h=max(1,int(config['lens_height']*1.55*spark_scale))
        target_w=max(1,int(spark.width*target_h/spark.height))
        sprite=spark.convert('RGBA').resize((target_w,target_h),Image.LANCZOS)
        if spark_alpha<1:sprite.putalpha(sprite.getchannel('A').point(lambda v:int(v*spark_alpha)))
        x,y=config['spark_at'];image.paste(sprite,(int(x)-target_w//2,int(y)-target_h//2),sprite)
    if flash>0:image=image.point(lambda v:min(255,int(v+(255-v)*flash)))
    if 'out_size' in config:image=image.resize(tuple(config['out_size']),Image.LANCZOS)
    return image


def render_frames(spec, base_dir='.'):
    """Portable adapter for authored breath/steam scene profiles; returns frames, ms."""
    from .assets import resolve_asset, validate_canvases
    def load(file):
        with Image.open(resolve_asset(base_dir,file)) as image:return image.convert('RGBA')
    background=load(spec['background']);actors=[]
    panel=spec.get('panel',{})
    for configured in spec['actors']:
        actor={key:value for key,value in configured.items() if key not in ('files','steam','mask','side')}
        actor['images']={name:load(file) for name,file in configured['files'].items()}
        images={'background':background,**actor['images']}
        if configured.get('steam'):
            actor['steam']=load(configured['steam']);images['steam']=actor['steam']
            actor['mask']=load(configured['mask']).getchannel('A') if configured.get('mask') else panel_mask(background.size,configured['side'],**panel)
        validate_canvases(images);actors.append(actor)
    if not actors:raise ValueError('at least one actor is required')
    cycle=actors[0]['profile']['breath']
    if not cycle or any(len(actor['profile']['breath'])!=len(cycle) for actor in actors):raise ValueError('actors must use equal nonempty breath cycle lengths')
    divider=load(spec['divider']) if spec.get('divider') else None
    if spec.get('divider_background'):divider=line_only(load(spec['divider_background']),background)
    if divider is not None and divider.size!=background.size:raise ValueError('divider canvas mismatch')
    output=tuple(spec.get('out_size',background.size));breaths=int(spec.get('breaths',2))
    if min(output)<1 or breaths<1:raise ValueError('output dimensions and breath count must be positive')
    rng=random.Random(spec.get('seed',7));frames=[];durations=[]
    for _ in range(breaths):
        for step in range(len(cycle)):
            frame=render_breath_frame(background,actors,step,divider,spec.get('front_haze',False),rng)
            frames.append(frame.convert('RGB').resize(output,Image.LANCZOS));durations.append(cycle[step][4])
    return frames,durations
