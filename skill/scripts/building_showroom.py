# parking-site-3d: showroom of every building style at 4, 7 and 10 floors (one row per style).
#   py building_showroom.py <out_site.json> [floors e.g. 4,7,10]
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware_catalog import BUILDING_MODELS

out = sys.argv[1]
FLOORS = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [4, 7, 10]
DX, DY = 75.0, 60.0
blds, pads = [], []
for row, (m, (th, _, (Lf, Df))) in enumerate(BUILDING_MODELS.items()):
    for col, F in enumerate(FLOORS):
        x, y = col * DX, -row * DY
        poly = [[x - Lf / 2, y - Df / 2], [x + Lf / 2, y - Df / 2], [x + Lf / 2, y + Df / 2], [x - Lf / 2, y + Df / 2]]
        blds.append(dict(id=f'{m}_{F}', label=f'{th} {F} ชั้น', model=m, model_th=th, floors=F, polygon=poly))
        pads.append([[x - Lf / 2 - 8, y - Df / 2 - 10], [x + Lf / 2 + 8, y - Df / 2 - 10], [x + Lf / 2 + 8, y + Df / 2 + 6], [x - Lf / 2 - 8, y + Df / 2 + 6]])
site = dict(name='คลังอาคาร (Building Library)', buildings=blds, equipment=[], gates=[], roads=[], trees=[],
            parking_areas=[dict(id=f'PAD{i}', polygon=p, no_stalls=True) for i, p in enumerate(pads)])
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
json.dump(site, open(out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('BUILDING_SHOWROOM_OK', len(blds), 'buildings ->', out)
