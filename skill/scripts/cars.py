# parking-site-3d: procedural passenger cars (Blender).
# Each car = a smooth body (lofted cross-sections + Subdivision Surface) and a detail mesh
# (tyres, alloy rims, lamps, grille, plates, mirrors, handles) that stays sharp.
# x = forward, y = left, z = up, origin = ground under the car centre.
import bpy, bmesh, math
from mathutils import Vector

# name: length, width, wheelbase, front overhang, tyre radius, clearance,
#       hood front z, belt z, roof z, windscreen base x, windscreen top x, rear-glass top x, rear-glass base x, rear deck z, weight
SPECS = {
    'sedan':  dict(L=4.70, W=1.80, wb=2.75, fo=.95, R=.32, cl=.16, hood=.72, belt=.98, roof=1.44, wsb=.80, wst=.02, rgt=-.95, rgb=-1.55, deck=.98, n=3),
    'hatch':  dict(L=4.10, W=1.76, wb=2.55, fo=.82, R=.31, cl=.15, hood=.74, belt=.98, roof=1.47, wsb=.78, wst=.0, rgt=-1.70, rgb=-1.98, deck=1.0, n=2),
    'suv':    dict(L=4.65, W=1.86, wb=2.72, fo=.92, R=.37, cl=.21, hood=.98, belt=1.13, roof=1.72, wsb=.95, wst=.12, rgt=-2.05, rgb=-2.25, deck=1.13, n=2),
    'pickup': dict(L=5.30, W=1.86, wb=3.10, fo=.92, R=.38, cl=.23, hood=1.0, belt=1.13, roof=1.80, wsb=1.30, wst=.62, rgt=-.62, rgb=-.78, deck=1.13, n=3, bed=-.88),
}
LOW, BODY0 = {}, {}      # web export: low-detail wheel/lamp meshes; one shared body per car kind
COLORS = [(.82, .82, .81), (.55, .56, .58), (.02, .02, .025), (.25, .26, .28), (.45, .04, .03), (.05, .13, .32)]


def _lerp(a, b, t):
    return a + (b - a) * max(0., min(1., t))


def _smooth(t):
    t = max(0., min(1., t)); return t * t * (3 - 2 * t)


class Car:
    def __init__(s, kind):
        s.k = kind; s.p = SPECS[kind]
        p = s.p; s.xf = p['L'] / 2 - p['fo']; s.xr = s.xf - p['wb']

    def halfw(s, x):
        p = s.p; e = p['L'] / 2 - abs(x)
        w = p['W'] / 2 * (.80 + .20 * _smooth(e / .45))
        if x > 0: w *= 1 - .03 * (x / (p['L'] / 2))          # plan-view taper to the nose
        return w

    def ztop(s, x):  # top of the lower body (hood / belt / deck)
        p = s.p; L2 = p['L'] / 2
        if x >= p['wsb']:
            t = (x - p['wsb']) / (L2 - p['wsb']); return _lerp(p['belt'] - .01, p['hood'], t ** 1.6)
        if p.get('bed') is not None and x < p['bed']:
            return p['deck']
        if x <= p['rgb']:
            t = (p['rgb'] - x) / max(.05, p['rgb'] + L2); return _lerp(p['belt'], p['deck'] - .06, t ** 2)
        return p['belt']

    def zbot(s, x):
        p = s.p; L2 = p['L'] / 2; R = p['R']; Ra = R + .075; z = p['cl']
        for wx in (s.xf, s.xr):
            d = abs(x - wx)
            if d < Ra: z = max(z, R + math.sqrt(Ra * Ra - d * d) * .92)
        e = L2 - abs(x)
        if e < .3: z = max(z, p['cl'] + (.3 - e) * .9)          # bumper approach angle
        return z

    def roof_h(s, x):
        p = s.p; b = s.ztop(x)
        if x > p['wst']:
            return _lerp(p['roof'], p['belt'], (x - p['wst']) / (p['wsb'] - p['wst']))
        if x < p['rgt']:
            return _lerp(p['roof'], p['belt'], (p['rgt'] - x) / (p['rgt'] - p['rgb']))
        return p['roof'] - .02 * ((x - (p['wst'] + p['rgt']) / 2) / (p['wst'] - p['rgt'])) ** 2

    # ---------------------------------------------------------------- body loft
    def body(s, bm):
        p = s.p; L2 = p['L'] / 2
        xs = []
        x = -L2
        while x < L2:
            xs.append(x); x += .09
        xs.append(L2)
        xs[0] += .015; xs[-1] -= .015
        rings = []
        for x in xs:
            w = s.halfw(x); zt = s.ztop(x); zb = s.zbot(x)
            e = L2 - abs(x); end = _smooth(e / .18)
            zt_e = zb + (zt - zb) * (.86 + .14 * end); w_e = w * (.9 + .1 * end)
            zs = zt_e - min(.07, (zt_e - zb) * .25)
            zm = zb + (zs - zb) * .45
            half = [(0, zb), (w_e * .84, zb), (w_e * .97, zb + .02), (w_e, zb + .08), (w_e, zm), (w_e, zs - .04), (w_e * .985, zs),
                    (w_e * .935, zt_e - .006), (w_e * .88, zt_e), (w_e * .45, zt_e + .012), (0, zt_e + .018)]   # support loops keep the shoulder and sill crisp
            ring = half + [(-y, z) for y, z in reversed(half[1:-1])]
            rings.append([bm.verts.new((x, y, z)) for y, z in ring])
        n = len(rings[0])
        for a, b in zip(rings, rings[1:]):
            for j in range(n):
                f = bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j])); f.material_index = 0
        for r_, flip in ((rings[0], True), (rings[-1], False)):
            f = bm.faces.new(r_ if not flip else list(reversed(r_))); f.material_index = 0

    def greenhouse(s, bm):
        p = s.p
        x0 = p['rgb'] + .03; x1 = p['wsb'] - .03
        xs = []; x = x0
        while x < x1:
            xs.append(x); x += .08
        xs.append(x1)
        bpil = (p['wst'] + p['rgt']) / 2 + (.25 if s.k != 'pickup' else -.1)
        rings, xs_used = [], []
        for x in xs:
            zb = s.ztop(x) - .015; h = max(zb + .02, s.roof_h(x)); gw = s.halfw(x) * .92
            half = [(gw, zb), (gw * .955, zb + (h - zb) * .5), (gw * .86, h - .05), (gw * .74, h - .012), (0, h)]
            ring = half + [(-y, z) for y, z in reversed(half[:-1])]
            rings.append([bm.verts.new((x, y, z)) for y, z in ring]); xs_used.append(x)
        n = len(rings[0])
        for i, (a, b) in enumerate(zip(rings, rings[1:])):
            xm = (xs_used[i] + xs_used[i + 1]) / 2
            flat = p['rgt'] + .05 < xm < p['wst'] - .05
            for j in range(n - 1):
                seg = j if j < 4 else (n - 2 - j)      # 0,1 side glass · 2 pillar/rail · 3 roof or screen
                f = bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
                if seg in (0, 1):
                    glass = abs(xm - bpil) > .07 and not (xm < p['rgt'] - .02 and s.k in ('sedan',)) and xm < p['wsb'] - .12
                    if s.k == 'pickup' and xm < p['rgt'] + .12: glass = False
                    f.material_index = 1 if glass else 0
                elif seg == 2:
                    f.material_index = 0
                else:
                    f.material_index = 0 if flat else 1
        for r_, flip in ((rings[0], False), (rings[-1], True)):
            f = bm.faces.new(r_ if not flip else list(reversed(r_))); f.material_index = 1 if s.k in ('hatch', 'suv') else 0

    # ---------------------------------------------------------------- details (sharp)
    def details(s, bm, lod=0):
        p = s.p; L2 = p['L'] / 2; R = p['R']; hi = lod == 0

        def cube(sx, sy, sz, c, mi, rot=0.):
            before = set(bm.faces); g = bmesh.ops.create_cube(bm, size=1)
            for v in g['verts']:
                co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
                if rot: co.rotate(__import__('mathutils').Euler((0, 0, rot)))
                v.co = co + Vector(c)
            if hi: bmesh.ops.bevel(bm, geom=list({e for f in set(bm.faces) - before for e in f.edges}), offset=min(sx, sy, sz) * .25, segments=2, affect='EDGES')
            for f in set(bm.faces) - before: f.material_index = mi

        def lathe(prof, centre, side, seg=24, mi=2):
            vs = []
            for k in range(seg):
                a = k / seg * math.tau; ring = []
                for r, y in prof:
                    ring.append(bm.verts.new((centre[0] + r * math.cos(a), centre[1] + side * y, centre[2] + r * math.sin(a))))
                vs.append(ring)
            for k in range(seg):
                A, B = vs[k], vs[(k + 1) % seg]
                for j in range(len(prof) - 1):
                    f = bm.faces.new((A[j], A[j + 1], B[j + 1], B[j]) if side > 0 else (A[j], B[j], B[j + 1], A[j + 1]))
                    f.material_index = mi
                    f.smooth = True
            return vs

        tyre = [(R * .64, -.115), (R * .93, -.12), (R, -.085), (R, .085), (R * .93, .12), (R * .64, .115)]
        rim = [(R * .64, .112), (R * .6, .105), (R * .22, .095), (R * .08, .115), (0.0, .118)]
        for wx in (s.xf, s.xr):
            for side in (1, -1):
                yc = side * (s.halfw(wx) - .125)
                lathe(tyre, (wx, yc, R), side, 28 if hi else 12, 2)
                lathe(rim, (wx, yc, R), side, 20 if hi else 10, 7)
                for k in range(5 if hi else 0):        # dark spoke gaps give the alloy depth
                    a = (k + .5) / 5 * math.tau
                    cube(.02, .012, R * .26, (wx + math.cos(a) * R * .4, yc + side * .101, R + math.sin(a) * R * .4), 6, 0)
        # lamps, grille, plates
        zf = s.ztop(L2 - .1); w = s.halfw(L2 - .12); zr = s.ztop(-L2 + .1); wr = s.halfw(-L2 + .1)
        for sd in (1, -1):
            cube(.14, .42, .1, (L2 - .05, sd * (w - .3), zf - .1), 3)                      # head lamps (proud of the nose)
            cube(.14, .46, .11, (-L2 + .05, sd * (wr - .3), zr - .11), 4)                   # tail lamps
            # mirrors at the base of the A-pillar
            xm = p['wsb'] - .12; cube(.18, .1, .11, (xm, sd * (s.halfw(xm) + .04), p['belt'] + .1), 6)
            cube(.03, .1, .07, (xm + .1, sd * (s.halfw(xm) + .07), p['belt'] + .1), 1)
            for xh in (p['wsb'] - .7, (p['wst'] + p['rgt']) / 2 - .35):
                cube(.13, .02, .025, (xh, sd * (s.halfw(xh) + .005), p['belt'] - .07), 7)
        cube(.12, .62, .12, (L2 - .05, 0, zf - .12), 6)                                   # upper grille
        zi = s.zbot(L2 - .05) + .12
        cube(.12, 1.0, .11, (L2 - .06, 0, zi), 6)                                          # lower intake
        cube(.1, .36, .11, (L2 - .02, 0, zi + .13), 5)                                     # front plate
        cube(.1, .36, .11, (-L2 + .02, 0, zr - .3), 5)                                     # rear plate
        cube(.1, 1.2, .06, (-L2 + .03, 0, s.zbot(-L2 + .05) + .06), 6)                    # rear diffuser strip
        if p.get('bed') is not None:            # pickup bed: dark floor + tailgate line
            cube(abs(-L2 + .12 - p['bed']), p['W'] - .2, .03, ((p['bed'] - L2 + .12) / 2, 0, p['deck'] + .005), 6)

    def build(s, name):
        bm = bmesh.new(); s.body(bm); s.greenhouse(bm)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.normal_update()
        body = bpy.data.meshes.new(name + '_body'); bm.to_mesh(body); bm.free()
        for f in body.polygons: f.use_smooth = True
        bm = bmesh.new(); s.details(bm)
        det = bpy.data.meshes.new(name + '_det'); bm.to_mesh(det); bm.free()
        bm = bmesh.new(); s.details(bm, 1)
        low = bpy.data.meshes.new(name + '_detlow'); bm.to_mesh(low); bm.free()
        LOW[det.name] = low
        return body, det


def library(mat, M):
    """-> list of (kind, body_mesh, detail_mesh); kinds repeated by weight. mat(name, rgb, rough, metal)."""
    paints = []
    for i, c in enumerate(COLORS):
        m = mat(f'CarPaint_{i}', c, .22, .5 if i in (1, 3) else .05)
        b = m.node_tree.nodes.get('Principled BSDF')
        for k, v in (('Coat Weight', 1.0), ('Coat Roughness', .03)):
            if k in b.inputs: b.inputs[k].default_value = v
        paints.append(m)
    glass = mat('CarGlass', (.012, .015, .02), .03, 0.)
    alloy = mat('Alloy', (.62, .63, .65), .25, 1.)
    tyre = mat('Tyre', (.025, .025, .025), .85)
    head = mat('CarHeadlamp', (.75, .77, .8), .08, .6, emit=(1, .97, .9), estr=.4)
    tail = mat('CarTaillamp', (.35, .02, .02), .15, 0., emit=(1, .05, .03), estr=.6)
    out = []
    for kind, sp in SPECS.items():
        car = Car(kind)
        det = None
        for i, pm in enumerate(paints):
            body, det_i = car.build(f'Car_{kind}_{i}')
            if det is None:
                det = det_i
                for m in (pm, glass, tyre, head, tail, M['white'], M['dark'], alloy): det.materials.append(m)
            else:
                bpy.data.meshes.remove(det_i)

            for m in (pm, glass): body.materials.append(m)
            BODY0.setdefault(kind, body)
            out += [(kind, body, det)] * sp['n']
    return out


def place(lib_entry, name, loc, yaw, coll):
    kind, body, det = lib_entry
    o = bpy.data.objects.new(name, body); coll.objects.link(o)
    o['car_kind'] = kind; o['paint'] = [round(v, 3) for v in body.materials[0].diffuse_color[:3]]
    o.location = loc; o.rotation_euler = (0, 0, yaw)
    sub = o.modifiers.new('Smooth', 'SUBSURF'); sub.levels = 0; sub.render_levels = 2   # viewport level 0 = what the .glb gets (light web file)
    d = bpy.data.objects.new(name + '_det', det); coll.objects.link(d); d.parent = o
    return o


def web_swap(coll):
    """Before glTF export: every car of a kind shares one body mesh (colour travels in the node's 'paint' extra and is
    re-applied by the viewer) and wheels/lamps switch to the low-detail mesh."""
    for o in coll.objects:
        if o.get('car_kind') and o.type == 'MESH' and not o.name.endswith('_det'):
            o.data = BODY0[o['car_kind']]
            for m in list(o.modifiers): o.modifiers.remove(m)      # modifiers would force one mesh copy per car in the .glb
        if o.name.endswith('_det') and o.data.name in LOW:
            low = LOW[o.data.name]
            if not low.materials:
                for m in o.data.materials: low.materials.append(m)
            o.data = low