# Artwork for the CREATIVE 2-tier kiosk (from the company drawing): three white head plates + PL1000 reader face.
import os
from PIL import Image, ImageDraw, ImageFont
here = os.path.dirname(os.path.abspath(__file__))
fonts = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts')
bold = os.path.join(fonts, 'tahomabd.ttf')
W, H = 520, 680                                  # one plate = 0.13 x 0.17 m
def font(size): return ImageFont.truetype(bold, size)
def ctext(d, y, s, size, fill='black', w=W, x0=0):
    f = font(size); tw = d.textlength(s, font=f); d.text((x0 + (w - tw) / 2, y), s, font=f, fill=fill)
def arrow(d, y, size=26): d.polygon([(W / 2 - size, y + size), (W / 2 + size, y + size), (W / 2, y)], fill='black')
def bracket_qr(d, x0, y0, s):
    k = s * .3; t = 12
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x0 + s, y0, -1, 1), (x0, y0 + s, 1, -1), (x0 + s, y0 + s, -1, -1)):
        d.line([(cx, cy + sy * k), (cx, cy), (cx + sx * k, cy)], fill='black', width=t)
    m = s * .18; b = s * .26
    for bx, by in ((x0 + m, y0 + m), (x0 + s - m - b, y0 + m), (x0 + m, y0 + s - m - b)):
        d.rectangle([bx, by, bx + b, by + b], outline='black', width=10)
    for i in range(3):
        for j in range(3):
            if (i + j) % 2 == 0: d.rectangle([x0 + s * .56 + i * 22, y0 + s * .56 + j * 22, x0 + s * .56 + i * 22 + 18, y0 + s * .56 + j * 22 + 18], fill='black')
def waves_icon(d, cx, cy, r, fill):
    for rad in (r * .45, r * .7, r * .95):
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], 200, 340, fill=fill, width=max(6, int(r * .09)))
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], 20, 160, fill=fill, width=max(6, int(r * .09)))
    d.ellipse([cx - r * .14, cy - r * .14, cx + r * .14, cy + r * .14], fill=fill)
def card_hand(d, x, y, s, fill, back):
    d.polygon([(x, y), (x + s * .55, y - s * .3), (x + s * .85, y + s * .25), (x + s * .3, y + s * .55)], fill=back, outline=fill, width=7)
    d.ellipse([x + s * .55, y + s * .35, x + s * 1.05, y + s * .85], fill=fill)
def new(): im = Image.new('RGB', (W, H), 'white'); return im, ImageDraw.Draw(im)
# head plates: cut straight from the company artwork (plates_source.png: three white plates on the dark panel)
source = Image.open(os.path.join(here, 'plates_source.png')).convert('RGB')
for name, (x0, x1) in (('scan', (47, 311)), ('idcard', (332, 596)), ('rfid', (614, 878))):
    source.crop((x0, 32, x1 + 1, 429)).resize((530, 794), Image.LANCZOS).save(os.path.join(here, f'{name}.png'))
# PL1000 reader face: cut from the company drawing (reader_source.png), dashed dimension line painted out
import numpy as np
pixels = np.array(Image.open(os.path.join(here, 'reader_source.png')).convert('RGB'))
band = pixels[336:364]; grey = band.mean(axis=2)
band[(grey > 5) & (grey < 70)] = (3, 3, 3)                  # the dashes are dark grey over the black panel
Image.fromarray(pixels).crop((291, 148, 561, 570)).resize((540, 844), Image.LANCZOS).save(os.path.join(here, 'reader.png'))
print('ART_OK')
