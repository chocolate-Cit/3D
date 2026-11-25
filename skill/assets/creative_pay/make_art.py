# Front artwork for the CREATIVE pay stations, cut from the company drawings (PDF rendered to *_source.png),
# darkened so the cabinet grey prints near-black like the real units.
import os
import numpy as np
from PIL import Image
here = os.path.dirname(os.path.abspath(__file__))
def darken(image):
    pixels = np.array(image.convert('RGB')).astype(float)
    dark = pixels.max(axis=2) < 100                       # cabinet fill / outlines; icons, labels and the intercom stay
    pixels[dark] *= .38
    return Image.fromarray(pixels.clip(0, 255).astype('uint8'))
# box cabinet CRT-AP-i23: cabinet outline at x 66-1842, y 88-4109 px (0.75 x 1.70 m)
box = Image.open(os.path.join(here, 'box_front_source.png')).crop((66, 88, 1843, 4110))
darken(box).resize((888, 2011), Image.LANCZOS).save(os.path.join(here, 'box_front.png'))
# slim N-park PLY2024N52: head + column face at x 128-1121, y 95-4323 px
slim = Image.open(os.path.join(here, 'slim_front_source.png')).crop((128, 95, 1122, 4324))
slim = np.array(darken(slim).resize((596, 2537), Image.LANCZOS))
for rows, edge in ((slice(0, 80), 80), (slice(1370, 1510), 70)):           # paper white outside the rounded corners -> body black
    block = slim[rows]; outside = block.min(axis=2) > 40
    outside[:, edge:596 - edge] = False; block[outside] = (18, 18, 19)
Image.fromarray(slim).save(os.path.join(here, 'slim_front.png'))
print('ART_OK')
