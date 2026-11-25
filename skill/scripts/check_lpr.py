# parking-site-3d: LPR sight-line + clearance check (Blender, headless).
#   blender -b <out>/site.blend --python check_lpr.py -- <out>/layout.json [report.json]
# For every lpr_camera: casts a fan of rays from the lens along its view direction and reports the first thing
# each ray hits (should be the road surface a few metres out, never the booth / ticket machine / barrier),
# and checks that its parts do not intersect any other device's bounding box.
import bpy, json, math, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
L = json.load(open(argv[0], encoding='utf8'))
for c in bpy.data.collections:
    if c.name in ('Labels', 'Decals', 'Backdrop', 'Cameras', 'Lights'):
        for o in c.all_objects:
            if o: o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene

def root_of(o):
    while o and not o.name.startswith('EQ_'): o = o.parent
    return o
def parts(r): return [o for o in [r] + list(r.children_recursive) if o.type == 'MESH' and not o.hide_render]
def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])
def overlap(a, b, m=.01):
    return all(a[0][i] < b[1][i] - m and b[0][i] < a[1][i] - m for i in range(3))
SURFACES = ('Lot_', 'Road_', 'Street', 'Ground', 'StallLines', 'Arrows', 'Lines', 'StopLines', 'Stop_', 'IslandHatch', 'Loop', 'Island_', 'Curbs')

report, bad = [], 0
roots = {o.name[3:]: o for o in bpy.data.objects if o.name.startswith('EQ_')}
boxes = {k: bbox(parts(r)) for k, r in roots.items() if parts(r)}
for e in [x for x in L['equipment'] if x['type'] == 'lpr_camera']:
    r = roots[e['id']]
    lens = next((o for o in r.children_recursive if o.name.startswith('Lens')), None)
    cam = lens.parent if lens else r
    origin = lens.matrix_world.translation if lens else r.matrix_world.translation + Vector((0, 0, 1.45))
    fwd = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
    hits = []
    for yaw in (-10, -5, 0, 5, 10):
        for pitch in (-4, 0, 4):
            d = fwd.copy(); d.rotate(__import__('mathutils').Euler((0, 0, math.radians(yaw))))
            side = d.cross(Vector((0, 0, 1))).normalized(); d.rotate(__import__('mathutils').Quaternion(side, math.radians(pitch)))
            o_ = origin + d * .06; ok = False
            for _ in range(20):                       # skip render-hidden helpers (fault cones, label plates)
                ok, loc, nrm, idx, obj, mtx = sc.ray_cast(dg, o_, d, distance=40)
                if not ok or not (obj.hide_render or obj.name.startswith('Label')): break   # render-only labels are not in the real scene
                o_ = loc + d * .002
            if not ok: hits.append(('sky', 40)); continue
            rt = root_of(obj); dist = (loc - origin).length
            p_ = obj
            while p_ and not p_.name.startswith(('FAULT_', 'EQ_')): p_ = p_.parent
            if p_ and p_.name.startswith('FAULT_'): hits.append(('cones (lane closed)', round(dist, 2))); continue   # fine: the lane is coned off
            name = f"EQ:{rt.name[3:]}" if rt and rt != r else obj.name
            hits.append((name, round(dist, 2)))
    # blocked = something solid inside the 3.5 m plate-reading zone, or the centre ray hitting a device at any range
    centre = hits[7]
    blocked = [(n, d) for n, d in hits if d < 3.5 and not (n.startswith(SURFACES) or n in ('sky', 'cones (lane closed)'))]
    if centre[0].startswith('EQ:'): blocked.append(centre)
    near_ground = [d for n, d in hits if n.startswith(SURFACES) and d < 2.0]
    def above_ground(o): return bbox([o])[1].z > .3         # footings / base plates sit on the ground: pads may share space
    mine = [bbox([o]) for o in parts(r) if above_ground(o)]                  # part-level overlap (a device-level box is too coarse: booth roofs, arms)
    clash = sorted({k for k, rr in roots.items() if k != e['id'] and overlap(boxes[e['id']], boxes.get(k, boxes[e['id']]))
                    for o in parts(rr) if above_ground(o) for b in [bbox([o])] for m_ in mine if overlap(m_, b)})
    status = 'OK' if not blocked and not clash and not near_ground else 'CHECK'
    bad += status != 'OK'
    report.append(dict(id=e['id'], gate=e.get('gate'), lane=e.get('lane'), heading=e.get('heading'), status=status,
                       blocked=blocked[:6], clash=clash, ground_hits=sorted(d for n, d in hits if n.startswith(SURFACES))[:3]))
for row in report: print('LPR', json.dumps(row, ensure_ascii=False))
if len(argv) > 1: json.dump(report, open(argv[1], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('LPR_CHECK', 'all OK' if not bad else f'{bad} to fix', len(report), 'cameras')
