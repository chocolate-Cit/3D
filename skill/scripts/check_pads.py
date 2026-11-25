import bpy, json, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
L = json.load(open(argv[0], encoding='utf8'))
def inside(pt, poly):
    x, y = pt; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
isl = [s['polygon'] for s in L['islands'] + L['sidewalks']]
bad = 0
for e in L['equipment']:
    host = next((p for p in isl if inside(e['pos'], p)), None)
    if not host: continue
    r = bpy.data.objects.get('EQ_' + e['id'])
    for o in [r] + list(r.children_recursive):
        if o.type != 'MESH' or o.hide_render or not o.name.startswith(('Plinth', 'Base', 'Footing', 'Floor')): continue
        for c_ in o.bound_box:
            w = o.matrix_world @ Vector(c_)
            if w.z < .2 and not inside((w.x, w.y), host):
                print('OVERHANG', e['id'], e['type'], o.name); bad += 1; break
print('PAD_CHECK', 'all on their islands' if not bad else f'{bad} pads overhang')
