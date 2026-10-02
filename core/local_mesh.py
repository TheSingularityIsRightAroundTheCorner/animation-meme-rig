"""Localized inverse mesh sampling for flattened art; no invented pixels/poses."""
from io import BytesIO
import math
from PIL import Image, ImageCms


def smoothstep(value):
    u = min(1.0, max(0.0, value))
    return u * u * (3 - 2 * u)


def ellipse_weight(x, y, cx, cy, rx, ry):
    """Compact support: exactly zero outside the ellipse."""
    if rx <= 0 or ry <= 0:
        raise ValueError('ellipse radii must be positive')
    return max(0.0, 1 - ((x-cx)/rx)**2 - ((y-cy)/ry)**2)**2


def plateau_weight(x, y, box, feather):
    """One inside xyxy box; smooth decay outward. Shared hand/object contact."""
    x0, y0, x1, y1 = box
    if x1 < x0 or y1 < y0 or feather <= 0:
        raise ValueError('ordered box and positive feather required')
    dx = max(x0-x, 0, x-x1)
    dy = max(y0-y, 0, y-y1)
    return (1-smoothstep(dx/feather)) * (1-smoothstep(dy/feather))


def pulse(t, center, width):
    if width <= 0:
        raise ValueError('pulse width must be positive')
    return math.exp(-((t-center)/width)**2)


def camera_inverse(x, y, zoom=1, screen_anchor=(0, 0), world_anchor=(0, 0)):
    """Map output pixels to stage, before applying local inverse deformation."""
    if zoom <= 0:
        raise ValueError('zoom must be positive')
    return ((x-screen_anchor[0])/zoom+world_anchor[0],
            (y-screen_anchor[1])/zoom+world_anchor[1])


def warp_local(image, inverse_point, output_size=None, step=24):
    """inverse_point(output_x,output_y) -> source_xy. One resampling pass.

    Positive visible translation dx uses source_x = output_x - dx.
    Mesh interpolation spreads a boundary by up to one cell: include safety
    margins around occluders and test smaller steps around mouths/fingers.
    """
    if not isinstance(step, int) or step < 1:
        raise ValueError('step must be a positive integer')
    width, height = output_size or image.size
    if width <= 0 or height <= 0:
        raise ValueError('output size must be positive')
    mesh = []
    exact = []
    for y in range(0, height, step):
        for x in range(0, width, step):
            x1, y1 = min(x+step, width), min(y+step, height)
            quad = tuple(v for p in ((x,y),(x,y1),(x1,y1),(x1,y))
                         for v in inverse_point(*p))
            if not all(math.isfinite(v) for v in quad):
                raise ValueError('nonfinite source coordinate')
            mesh.append(((x,y,x1,y1), quad))
            qx,qy = quad[:2]
            if qx == int(qx) and qy == int(qy) and quad == (qx,qy,qx,qy+y1-y,qx+x1-x,qy+y1-y,qx+x1-x,qy):
                exact.append(((x,y,x1,y1),(int(qx),int(qy),int(qx+x1-x),int(qy+y1-y))))
    source = image.convert('RGBA')
    result = source.transform((width,height), Image.Transform.MESH,
             mesh, Image.Resampling.BICUBIC, fillcolor=(0,0,0,0))
    # Pillow premultiplies RGBA when interpolating, which rounds even untouched
    # translucent pixels. Exact unit translations need no interpolation.
    for dest, src in exact:
        result.paste(source.crop(src), dest)
    return result


def load_srgb(path):
    """Convert embedded RGB profile, preserving alpha; untagged assumed sRGB."""
    with Image.open(path) as source:
        profile = source.info.get('icc_profile')
        result = source.convert('RGBA')
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
    if profile:
        result = ImageCms.profileToProfile(result,
            ImageCms.ImageCmsProfile(BytesIO(profile)), srgb, outputMode='RGBA')
    result.info['icc_profile'] = srgb.tobytes()
    return result
