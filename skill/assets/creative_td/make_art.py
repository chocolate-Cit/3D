# Rebuild the CREATIVE slip-dispenser panel artwork from the company close-up photo.
#   py make_art.py            (reads source_panel_photo.png next to this file, writes the *.png the model uses)
# Corner points were measured on the photo; the photo is taken at a slight angle, so screen / logo / label
# are straightened with a four-corner transform. White-on-dark artwork gets a transparent background.
import os
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
photo = Image.open(os.path.join(HERE, 'source_panel_photo.png')).convert('RGB')
UPSCALE = 3

def straighten(corners, size):
    """corners = upper-left, lower-left, lower-right, upper-right (photo pixels); size = output size before upscaling."""
    flat = photo.transform(size, Image.QUAD, corners, Image.BICUBIC)
    big = flat.resize((size[0] * UPSCALE, size[1] * UPSCALE), Image.LANCZOS)
    return big.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=2))

def white_on_transparent(image, dark=85, light=165):
    """Keep only the white print: alpha ramps from 0 at `dark` grey to full at `light` grey (crisp edges)."""
    alpha = image.convert('L').point(lambda value: max(0, min(255, int((value - dark) * 255 / (light - dark)))))
    out = Image.new('RGB', image.size, (255, 255, 255)); out.putalpha(alpha); return out

def save(image, name): image.save(os.path.join(HERE, name)); print('saved', name, image.size)

# screen: lit display, straightened; stronger contrast so the text reads clearly
screen = straighten((160, 348, 160, 555, 461, 577, 461, 369), (320, 220))
save(ImageOps.autocontrast(screen, cutoff=1), 'screen.png')
save(white_on_transparent(straighten((530, 108, 530, 153, 732, 168, 732, 123), (200, 45))), 'logo.png')
save(white_on_transparent(straighten((578, 360, 578, 410, 705, 419, 705, 369), (127, 53))), 'help.png')

# (1)(2) graphics: the reader disc and slot bezel are real 3D parts, so clear them from the print
graphics = white_on_transparent(straighten((128, 675, 128, 1035, 520, 1035, 520, 675), (392, 360)))
alpha = graphics.getchannel('A'); draw = ImageDraw.Draw(alpha); s = UPSCALE / 2
draw.ellipse((345 * s, 0, 555 * s, 225 * s), fill=0); draw.rectangle((280 * s, 275 * s, 628 * s, 440 * s), fill=0)
graphics.putalpha(alpha); save(graphics, 'graphics.png')

# MEMBER plate: dark print on a white plate, keep it opaque, lift contrast
member = straighten((572, 652, 572, 1032, 713, 1032, 713, 652), (141, 380))
save(ImageOps.autocontrast(member, cutoff=1), 'member.png')
