"""stadium3d.py — fold a hand-drawn net into an open-top box and film inside it.

Every panel is one quad in 3D. Clip its visible polygon at the near plane, preserve the
texture homography, warp, and composite back-to-front. Same divide-by-depth as
the hand turn and the floor, just applied to whole panels instead of one plane.
Billboards (the characters) are quads that always face the camera, so the drawing keeps
its own perspective while the room moves around it.
"""
import math
import numpy as np
from PIL import Image, ImageChops

def load_panels(sheet_path, panels):
    """Crop a caller-provided sheet; regions are xyxy or {box, rotation}."""
    if not panels:
        raise ValueError("explicit panel mapping must not be empty")
    with Image.open(sheet_path) as source:
        net = source.convert("RGBA")
    out = {}
    for name, region in panels.items():
        box = region["box"] if isinstance(region, dict) else region
        rotation = region.get("rotation", 0) if isinstance(region, dict) else 0
        if len(box) != 4 or not (0 <= box[0] < box[2] <= net.width and 0 <= box[1] < box[3] <= net.height):
            raise ValueError(f"panel {name}: box lies outside sheet bounds")
        image = net.crop(box)
        out[name] = image.rotate(rotation, expand=True) if rotation else image
    return out

# --- camera -------------------------------------------------------------------
def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye
    if not np.isfinite([eye, target, up]).all() or np.linalg.norm(f) < 1e-12:
        raise ValueError("eye and target must be finite and distinct")
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    if np.linalg.norm(s) < 1e-12:
        raise ValueError("camera up must not be parallel to view direction")
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    return np.stack([s, u, -f]), eye

def project(pts, R, eye, w, h, fov=52.0):
    if w <= 0 or h <= 0 or not 0 < fov < 180:
        raise ValueError("positive output dimensions and fov in 0..180 required")
    cam = (np.asarray(pts, float) - eye) @ R.T
    z = -cam[:, 2]
    fpx = (h / 2) / math.tan(math.radians(fov) / 2)
    x = w / 2 + fpx * cam[:, 0] / np.maximum(z, 1e-3)
    y = h / 2 - fpx * cam[:, 1] / np.maximum(z, 1e-3)
    return np.stack([x, y], 1), z

def homography(src, dst):
    A, B = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]); B.append(dx)
        A.append([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]); B.append(dy)
    h = np.linalg.solve(np.array(A, float), np.array(B, float))
    return np.array([[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1.0]])

def clip_near(camera_polygon, near=0.05):
    """Clip a camera-space polygon to depth >= near before perspective division."""
    vertices = np.asarray(camera_polygon, float)
    if not np.isfinite(near) or near <= 0:
        raise ValueError("near must be finite and positive")
    if not len(vertices):
        return np.empty((0, 3))
    output = []
    previous = vertices[-1]
    for current in vertices:
        previous_inside, current_inside = -previous[2] >= near, -current[2] >= near
        if previous_inside != current_inside:
            t = (-near - previous[2]) / (current[2] - previous[2])
            output.append(previous + t * (current - previous))
        if current_inside:
            output.append(current)
        previous = current
    return np.asarray(output, float).reshape(-1, 3)


def _homogeneous_texture_map(camera_quad, texture_size, output_size, fov):
    """Map texture to screen without dividing original corners by their depth.

    Homogeneous correspondences also work for corners on/behind the eye plane.
    UV coordinates remain those of the original planar quad after clipping.
    """
    rows = []
    for uv, point in zip(((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)), camera_quad):
        x, y, z = point * (1, -1, -1)
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        rows.extend(np.kron(cross, uv))
    _, _, vectors = np.linalg.svd(rows, full_matrices=False)
    normalized = vectors[-1].reshape(3, 3)
    w, h = output_size
    focal = (h / 2) / math.tan(math.radians(fov) / 2)
    viewport = np.array([[focal, 0, w/2], [0, focal, h/2], [0, 0, 1]])
    return viewport @ normalized @ np.diag([1/texture_size[0], 1/texture_size[1], 1])


def draw_quad(canvas, tex, corners3d, R, eye, fov):
    w, h = canvas.size
    if w <= 0 or h <= 0 or not 0 < fov < 180:
        raise ValueError("positive output dimensions and fov in 0..180 required")
    camera = (np.asarray(corners3d, float) - eye) @ R.T
    z = -camera[:, 2]
    clipped = None
    if (z < 0.05).any():
        clipped = clip_near(camera)
        if len(clipped) < 3:
            return None
        focal = (h / 2) / math.tan(math.radians(fov) / 2)
        depth = -clipped[:, 2]
        dst = np.column_stack((w/2 + focal*clipped[:, 0]/depth,
                               h/2 - focal*clipped[:, 1]/depth))
        area = np.sum(dst[:, 0]*np.roll(dst[:, 1], -1) - dst[:, 1]*np.roll(dst[:, 0], -1))
        if abs(area) < 1e-8:
            return None
        H = _homogeneous_texture_map(camera, tex.size, canvas.size, fov)
    else:
        # Preserve the inherited resampling exactly for already-visible quads.
        dst, z = project(corners3d, R, eye, w, h, fov)
        tw, th = tex.size
        src = [(0, 0), (tw, 0), (tw, th), (0, th)]
        H = homography(src, [tuple(p) for p in dst])
    inv = np.linalg.inv(H); inv = inv / inv[2, 2]
    warped = tex.transform((w, h), Image.PERSPECTIVE,
                           (inv[0, 0], inv[0, 1], inv[0, 2],
                            inv[1, 0], inv[1, 1], inv[1, 2],
                            inv[2, 0], inv[2, 1]), resample=Image.BICUBIC)
    if clipped is not None:
        # Sample the mask at the same pixel centres as the perspective sampler.
        # Integer polygon rasterisation otherwise leaves cracks between panels.
        yy, xx = np.ogrid[:h, :w]
        inside = np.ones((h, w), dtype=bool)
        for start, end in zip(dst, np.roll(dst, -1, axis=0)):
            cross = ((end[0]-start[0])*(yy+.5-start[1])
                     - (end[1]-start[1])*(xx+.5-start[0]))
            inside &= cross * np.sign(area) >= -1e-8
        mask = Image.fromarray(inside.astype(np.uint8)*255)
        warped.putalpha(ImageChops.multiply(warped.getchannel('A'), mask))
    canvas.alpha_composite(warped)
    return float((-clipped[:, 2]).mean() if clipped is not None else z.mean())

def strips(quad, tex, n=10, axis=0):
    """Split a quad and its texture into slices for compatibility or painter ordering.

    Near-plane visibility no longer depends on subdivision: draw_quad clips each
    polygon. One slice is sufficient for the nonintersecting room panels.
    """
    if not isinstance(n, int) or n < 1 or axis not in (0, 1):
        raise ValueError("slices require positive integer n and axis 0 or 1")
    p0, p1, p2, p3 = [np.asarray(p, float) for p in quad]
    tw, th = tex.size
    out = []
    for i in range(n):
        a, b = i / n, (i + 1) / n
        if axis == 0:                       # slice along the p0->p1 edge
            q = [p0 + (p1 - p0) * a, p0 + (p1 - p0) * b,
                 p3 + (p2 - p3) * b, p3 + (p2 - p3) * a]
            crop = tex.crop((int(tw * a), 0, max(int(tw * b), int(tw * a) + 1), th))
        else:                               # slice along the p0->p3 edge
            q = [p0 + (p3 - p0) * a, p1 + (p2 - p1) * a,
                 p1 + (p2 - p1) * b, p0 + (p3 - p0) * b]
            crop = tex.crop((0, int(th * a), tw, max(int(th * b), int(th * a) + 1)))
        out.append((q, crop))
    return out


def billboard(center, height, aspect, R):
    """A quad that always faces the camera: built from the camera's own right/up axes."""
    right, up = R[0], R[1]
    c = np.array(center, float)
    hw, hh = height * aspect / 2, height / 2
    return [c - right * hw + up * hh, c + right * hw + up * hh,
            c + right * hw - up * hh, c - right * hw - up * hh]


def render_frames(spec, base_dir='.'):
    """Render the configurable folded-room/billboard shot from build_run_shot.

    Uses the Claude camera convention (Y up, forward negative camera Z). The
    Historical GPT floorfix profile supplies alternative panel crops to this renderer;
    its alternate matrix sign convention is not imported. Required: panel_sheet,
    panels, pose_files. Art is supplied
    by the caller; source sheet measurements live in presets/stadium_run.json.
    """
    from pathlib import Path
    from .camera_25d import camera_at, pose_at
    from .assets import resolve_asset
    base=Path(base_dir)
    dimensions=spec.get('room',{})
    width=float(dimensions.get('width',14));depth=float(dimensions.get('depth',22));height=float(dimensions.get('height',6))
    if min(width,depth,height)<=0:raise ValueError('room dimensions must be positive')
    output=tuple(spec.get('out_size',[900,506]));count=int(spec.get('frames',42))
    if count<2:raise ValueError('room shot requires at least two frames')
    panels=load_panels(resolve_asset(base,spec['panel_sheet']),spec['panels'])
    required={'far','left','right','near','floor'}
    if not required<=panels.keys():raise ValueError('room requires far, left, right, near, and floor panels')
    poses=[]
    for file in spec['pose_files']:
        with Image.open(resolve_asset(base,file)) as image:poses.append(image.convert('RGBA'))
    if not poses:raise ValueError('at least one actor pose is required')
    a=(-width/2,0,-depth/2);b=(width/2,0,-depth/2);c=(width/2,0,depth/2);d=(-width/2,0,depth/2)
    up=np.array([0,height,0])
    quads={'floor':[a,b,c,d],'far':[a+up,b+up,b,a],
           'left':[d+up,a+up,a,d],'right':[b+up,c+up,c,b],'near':[c+up,d+up,d,c]}
    quads={key:[np.asarray(point,float) for point in value] for key,value in quads.items()}
    start=spec.get('camera_start',{'eye':[5,2.3,8],'target':[0,1.8,1],'fov':54})
    end=spec.get('camera_end',{'eye':[.9,2.6,3.4],'target':[-.5,2.1,-depth/2],'fov':44})
    schedule=spec.get('pose_schedule',[{'at':0,'part':0},{'at':.4,'part':min(1,len(poses)-1)},{'at':.72,'part':min(2,len(poses)-1)}])
    actor=spec.get('actor',{});stride_count=float(actor.get('strides',3))
    frames=[]
    for i in range(count):
        p=i/(count-1);t=p*p*(3-2*p)
        camera=camera_at(start,end,p)
        eye=camera['eye'];bob=math.sin(p*math.pi*2*stride_count)
        eye=(eye[0],eye[1]+float(spec.get('camera_bob',.045))*bob,eye[2])
        rotation,position=look_at(eye,camera['target'])
        canvas=Image.new('RGBA',output,tuple(spec.get('background',[255,255,255,255])))
        pieces=[]
        for key in ('far','left','right','near','floor'):
            slices=1 if key=='far' else int(spec.get('slices',14))
            for quad,texture in strips(quads[key],panels[key],n=slices,axis=0 if key=='far' else 1):
                distance=np.mean([np.linalg.norm(np.asarray(point)-position) for point in quad])
                pieces.append((distance,quad,texture))
        for _,quad,texture in sorted(pieces,key=lambda item:-item[0]):
            draw_quad(canvas,texture,quad,rotation,position,camera['fov'])
        index=pose_at(schedule,p)
        if not isinstance(index,int) or not 0<=index<len(poses):raise ValueError('pose schedule index outside pose_files')
        texture=poses[index]
        actor_height=float(actor.get('height_start',4))+float(actor.get('height_growth',1.2))*t
        stride=math.sin(p*math.pi*2*stride_count+index*float(actor.get('pose_phase',1.1)))
        centre=(float(actor.get('x',-.35))+float(actor.get('sway',.15))*stride,
                actor_height/2+float(actor.get('bob',.10))*abs(stride),
                float(actor.get('z_start',3))-float(actor.get('travel',2.2))*t)
        quad=billboard(centre,actor_height,texture.width/texture.height,rotation)
        draw_quad(canvas,texture,quad,rotation,position,camera['fov'])
        frames.append(canvas.convert('RGB'))
    return frames
