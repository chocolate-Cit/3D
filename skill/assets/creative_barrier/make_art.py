# CREATIVE barrier cabinet front/back panel: silver-grey panel, white P badge, vertical white CREATIVE (reads bottom-up).
import os
from PIL import Image, ImageDraw, ImageFont
here = os.path.dirname(os.path.abspath(__file__))
fonts = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts')
width, height = 520, 1840                       # 0.26 x 0.92 m at 2000 px/m
panel = Image.new('RGBA', (width, height))
draw = ImageDraw.Draw(panel)
for column in range(width):                     # brushed silver, a little lighter toward the middle
    shade = int(158 + 14 * (1 - abs(column / width - .45) * 2))
    draw.line([(column, 0), (column, height)], fill=(shade, shade + 2, shade + 4, 255))
centre_x, badge_y, badge_r = width // 2, 470, 82
draw.ellipse([centre_x - badge_r, badge_y - badge_r, centre_x + badge_r, badge_y + badge_r], fill=(250, 250, 250, 255))
p_font = ImageFont.truetype(os.path.join(fonts, 'arialbd.ttf'), 128)
draw.text((centre_x + 3, badge_y + 4), 'P', font=p_font, fill=(150, 152, 155, 255), anchor='mm')
word_font = ImageFont.truetype(os.path.join(fonts, 'arialbi.ttf'), 74)
word = Image.new('RGBA', (520, 110)); ImageDraw.Draw(word).text((260, 55), 'CREATIVE', font=word_font, fill=(255, 255, 255, 255), anchor='mm')
word = word.rotate(-90, expand=True)            # reads top-to-bottom, as on the real unit
panel.alpha_composite(word, (40, height - 520 - 70))
panel.save(os.path.join(here, 'panel.png'))
print('ART_OK')
