# Rebuild the CREATIVE Kiosk Exit panel artwork from the company close-up photo.
#   py make_art.py      (reads source_panel_photo.webp next to this file, writes the *.png the model uses)
# Step 1 flattens the whole black front panel (photo taken at an angle) to 800 x 1100 px:
#   800 px = panel width 0.47 m, 1100 px = panel height 0.66 m. All crops below are in that flat image.
import os
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
photo = Image.open(os.path.join(HERE, 'source_panel_photo.webp')).convert('RGB')
flat = photo.transform((800, 1100), Image.QUAD, (262, 97, 262, 1186, 988, 1182, 988, 142), Image.BICUBIC)
UPSCALE = 3

def crop(box_, corners=None, size=None):
    """Crop from the flat panel (optionally straightening a quad), upscale and sharpen."""
    if corners:
        piece = flat.transform(size, Image.QUAD, corners, Image.BICUBIC)
    else:
        piece = flat.crop(box_)
    piece = piece.filter(ImageFilter.MedianFilter(3))              # remove the photo's render grain
    big = piece.resize((piece.width * UPSCALE, piece.height * UPSCALE), Image.LANCZOS)
    return big.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=2))

def white_on_transparent(image, dark=85, light=165):
    alpha = image.convert('L').point(lambda value: max(0, min(255, int((value - dark) * 255 / (light - dark)))))
    out = Image.new('RGB', image.size, (255, 255, 255)); out.putalpha(alpha); return out

def save(image, name): image.save(os.path.join(HERE, name)); print('saved', name, image.size)

# screen (plate number, entry time, duration, fee, PromptPay QR): lit display area, straightened
save(ImageOps.autocontrast(crop(None, (109, 327, 109, 549, 469, 557, 469, 338), (360, 226)), cutoff=1), 'screen.png')

# white L-shaped plate: band across the panel + column on the right with rounded bottom corners
PLATE = (40, 650, 795, 1062)                      # crop box in the flat panel (the plate drops 13 px left->right: straighten)
plate = crop(None, (40, 650, 40, 1062, 795, 1075, 795, 663), (755, 412))
mask = Image.new('L', plate.size, 0); d = ImageDraw.Draw(mask); s = UPSCALE
ox, oy = PLATE[0], PLATE[1]
d.rectangle(((46 - ox) * s, (657 - oy) * s, (790 - ox) * s, (797 - oy) * s), fill=255)                 # band
d.rounded_rectangle(((568 - ox) * s, (657 - oy) * s, (766 - ox) * s, (1057 - oy) * s), radius=22 * s, fill=255)  # column
plate = ImageOps.autocontrast(plate, cutoff=1); plate.putalpha(mask); save(plate, 'plate.png')

# (2) number + pointer line and the receipt icon: white print, slot bezel cleared (it is a 3D part)
LOWER = (80, 810, 440, 1060)
lower = white_on_transparent(crop(LOWER))
alpha = lower.getchannel('A'); ImageDraw.Draw(alpha).rectangle(((234 - 80) * s, (816 - 810) * s, (436 - 80) * s, (910 - 810) * s), fill=0)
lower.putalpha(alpha); save(lower, 'lower.png')
