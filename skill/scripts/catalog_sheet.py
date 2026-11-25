# parking-site-3d: compose the hardware catalogue sheet from close-up renders.
#   py catalog_sheet.py <out_dir>      (reads out_dir/layout.json + out_dir/render/closeup_<id>.png -> out_dir/hardware_catalog.png)
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware_catalog import MODELS

outd = sys.argv[1]
L = json.load(open(os.path.join(outd, 'layout.json'), encoding='utf8'))
def font(sz, bold=False):
    for f in (('tahomabd.ttf' if bold else 'tahoma.ttf'), 'arial.ttf'):
        try: return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', f), sz)
        except Exception: pass
    return ImageFont.load_default()
F1, F2, F3 = font(30, True), font(20, True), font(15)
TW, TH_ = 420, 315; PAD = 16; COLS = max(len(v) for v in MODELS.values())
rows = []
if '--buildings' in sys.argv:          # building library sheet: one row per style, one column per floor count
    from hardware_catalog import BUILDING_MODELS
    for m, (th, _, _) in BUILDING_MODELS.items():
        bs = [dict(b, name_th=th, id=b['id'], model_th=f"{b['floors']} ชั้น", model=m) for b in L['buildings'] if b.get('model') == m]
        if bs: rows.append((m, bs))
    COLS = max(len(r[1]) for r in rows)
else:
  for t in MODELS:
    es = [e for e in L['equipment'] if e['type'] == t]
    if es: rows.append((t, es))
  COLS = max(len(r[1]) for r in rows)
W = PAD + COLS * (TW + PAD) + 260; H = 90 + len(rows) * (TH_ + 86 + PAD)
im = Image.new('RGB', (W, H), (246, 247, 249)); d = ImageDraw.Draw(im)
d.text((PAD, 24), L['name'], fill=(20, 28, 36), font=F1)
y = 90
for t, es in rows:
    lines, cur = [], ''                     # wrap the row label into the 205 px label column
    for ch in es[0]['name_th']:
        if d.textlength(cur + ch, font=F2) > 205 and cur:
            cut = max(cur.rfind(' '), cur.rfind('('))
            if cut > 0: lines.append(cur[:cut].strip()); cur = cur[cut:].lstrip()
            else: lines.append(cur); cur = ''
        cur += ch
    lines.append(cur.strip())
    for i, ln in enumerate(lines):
        d.text((PAD, y + TH_ / 2 - 14 * len(lines) + i * 28), ln, fill=(20, 28, 36), font=F2)
    for i, e in enumerate(es):
        x = 230 + i * (TW + PAD)
        p = os.path.join(outd, 'render', f"closeup_{e['id']}.png")
        if os.path.exists(p):
            th = ImageOps.fit(Image.open(p).convert('RGB'), (TW, TH_), Image.LANCZOS); im.paste(th, (x, y))   # fill the slot (any render aspect)
        d.rectangle([x, y, x + TW, y + TH_], outline=(200, 205, 212))
        title, name_lines = e.get('model_th', e.get('model', '')), []   # wrap long model names inside the slot width
        while d.textlength(title, font=F2) > TW:
            cut = max(title.rfind(' ', 0, len(title) - 1), title.rfind('('))
            if cut <= 0: break
            name_lines.insert(0, title[cut:].strip()); title = title[:cut].strip()
        name_lines.insert(0, title)
        for k, line in enumerate(name_lines[:2] if len(name_lines) <= 2 else [name_lines[0], ' '.join(name_lines[1:])]):
            d.text((x, y + TH_ + 6 + k * 26), line, fill=(20, 28, 36), font=F2)
        d.text((x, y + TH_ + 6 + min(len(name_lines), 2) * 26), f"model: {e.get('model')}   ({e['id']})", fill=(90, 100, 110), font=F3)
    y += TH_ + 86 + PAD
p = os.path.join(outd, 'building_catalog.png' if '--buildings' in sys.argv else 'hardware_catalog.png'); im.save(p)
print('SHEET_OK', p, im.size)
