"""Advisory pixel diagnostics. Authored borders and lines may be intentional."""
import numpy as np


def inspect_frame(image, threshold=18):
    a = np.asarray(image.convert('RGB'), dtype=float).mean(axis=2)
    if min(a.shape) < 12:
        return []
    warnings = []
    bands = [(a[:3],a[3:9]),(a[-3:],a[-9:-3]),(a[:,:3],a[:,3:9]),(a[:,-3:],a[:,-9:-3])]
    if any(abs(float(edge.mean()-inside.mean())) > threshold for edge,inside in bands):
        warnings.append({'code':'border','detail':'edge brightness differs from adjacent interior; inspect crop/overscan'})
    for axis in (0,1):
        average = a.mean(axis=axis)
        for i in range(3,len(average)-3):
            neighbors = np.concatenate((average[i-3:i],average[i+1:i+4]))
            if abs(average[i]-neighbors.mean()) > threshold:
                warnings.append({'code':'stripe','axis':axis,'position':i,'detail':'isolated row/column; may be intentional art'})
                break
    return warnings


def inspect_parts(images, layers):
    result = []
    for name,image in images.items():
        if layers.get(name,{}).get('visible',True) and image.convert('RGBA').getchannel('A').getbbox() is None:
            result.append({'code':'missing_part','part':name})
    return result
