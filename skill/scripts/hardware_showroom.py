# parking-site-3d: build a "showroom" site with every hardware model side by side (one row per type).
#   py hardware_showroom.py <out_site.json> [type,type,...]
# Then: run.ps1 <out_site.json> <out_dir> + build_blender.py --closeup-all, and catalog_sheet.py for the picture sheet.
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware_catalog import MODELS, library_models
from site_layout import EQUIP

out = sys.argv[1]
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
ON_ROAD = {'tyre_killer', 'road_blocker', 'loop_detector', 'speed_bump', 'stall_sensor'}
EXTRA = {'barrier_gate': dict(arm=3.5), 'tyre_killer': dict(length=3.0), 'road_blocker': dict(length=3.0),
         'height_bar': dict(width=6.0, height=2.1), 'guard_booth': dict(size=[1.6, 2.2]), 'lpr_camera': dict(display=True), 'vacancy_sign': dict(display=128)}
DX, DY = 9.0, 11.0
eq, pads, lots = [], [], []
types = [t for t in MODELS if (not only or t in only) and library_models(t)]
for row, t in enumerate(types):
    for col, (m, th, _) in enumerate(library_models(t)):
        x, y = col * DX, -row * DY
        e = dict(type=t, model=m, pos=[x, y], heading=270, label=f'{EQUIP[t][0]} · {th}')
        e.update(EXTRA.get(t, {}))
        if t == 'barrier_gate':
            e['heading'] = 0; e['pos'] = [x - 2, y]; e['traffic'] = 90   # arm points east across a 3.5 m "lane"
        if t == 'height_bar': e['heading'] = 270
        eq.append(e)
        poly = [[x - 3.6, y - 4.2], [x + 3.6, y - 4.2], [x + 3.6, y + 4.2], [x - 3.6, y + 4.2]]
        (lots if t in ON_ROAD or t in ('height_bar', 'barrier_gate') else pads).append(poly)
site = dict(name='คลังอุปกรณ์ (Hardware Library)', notes='Every model of every device type, one row per type.',
            equipment=eq,
            islands=[dict(id=f'PAD{i}', polygon=p, kind='equipment', no_hatch=True) for i, p in enumerate(pads)],
            parking_areas=[dict(id=f'LOT{i}', polygon=p, no_stalls=True) for i, p in enumerate(lots)],
            gates=[], roads=[], trees=[])
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
json.dump(site, open(out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('SHOWROOM_OK', len(eq), 'models in', len(types), 'types ->', out)
