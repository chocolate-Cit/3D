# parking-site-3d: Blender builder (headless).
#   blender -b --factory-startup --python build_blender.py -- <layout.json> <out_dir> [--no-render] [--samples 64] [--res 1600x900] [--cars 0.6]
# Builds a realistic 3D parking site from layout.json (made by site_layout.py):
# asphalt, paint, curbs, islands, sidewalks, buildings, trees, cars, and every piece of
# equipment as its own named node "EQ_<id>" (custom props -> glTF extras).
# Writes site.blend, site.glb and renders (overview, top, top_labels, gate_<id>, entrance).
import bpy, bmesh, json, math, os, random, sys, warnings
warnings.simplefilter('ignore', DeprecationWarning)
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
LAYOUT, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
def opt(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default
RENDER = '--no-render' not in argv
SAMPLES = opt('--samples', 64)
RES = [int(v) for v in opt('--res', '1600x900').split('x')]
CAR_FILL = opt('--cars', 0.0)     # parked cars/motorcycles off by default; e.g. --cars 0.6 to fill 60% of stalls
os.makedirs(OUT, exist_ok=True)
L = json.load(open(LAYOUT, encoding='utf8'))
random.seed(L.get('seed', 7))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
COL = {}
def coll(name):
    if name not in COL:
        c = bpy.data.collections.new(name); sc.collection.children.link(c); COL[name] = c
    return COL[name]

# ------------------------------------------------------------------ materials
MATS = {}
def mat(name, color, rough=.6, metal=0., emit=None, estr=0., noise=None, alpha=1.):
    """noise = (scale, contrast, color2) adds world-space variation (asphalt, concrete, grass)."""
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = estr
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    if noise:
        sc_, ct, c2 = noise
        g = nt.nodes.new('ShaderNodeNewGeometry')
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = sc_; n.inputs['Detail'].default_value = 8
        nt.links.new(g.outputs['Position'], n.inputs['Vector'])
        r = nt.nodes.new('ShaderNodeValToRGB')
        r.color_ramp.elements[0].position = .5 - ct; r.color_ramp.elements[1].position = .5 + ct
        r.color_ramp.elements[0].color = (*c2, 1); r.color_ramp.elements[1].color = (*color, 1)
        nt.links.new(n.outputs['Fac'], r.inputs['Fac']); nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
        bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .15
        n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = sc_ * 12
        nt.links.new(g.outputs['Position'], n2.inputs['Vector'])
        nt.links.new(n2.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    m.diffuse_color = (*color, 1)
    MATS[name] = m; return m

# ---- Poly Haven PBR textures (CC0), fetched once by fetch_assets.py into ../assets
def _assets_dir():          # skill/assets, else the per-user cache (account-synced skills ship without the big files)
    for d in (os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets'),
              os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'parking-site-3d', 'assets')):
        mf = os.path.join(d, 'manifest.json')
        if os.path.exists(mf):
            m = json.load(open(mf))
            if m.get('hdri') and os.path.exists(os.path.join(d, m['hdri'])): return d, m
    return None, None
ASSETS, MANIFEST = _assets_dir()
IMGS = {}
def img(rel, noncolor=False):
    p = os.path.join(ASSETS, rel)
    if p not in IMGS:
        im = bpy.data.images.load(p, check_existing=True)
        if noncolor: im.colorspace_settings.name = 'Non-Color'
        IMGS[p] = im
    return IMGS[p]

def tmat(name, role, tile, color, rough=.8, tint=None, normal=1.0, fallback_noise=None):
    """Textured PBR material on the mesh's world-metre UVs (tile = metres per texture repeat).
    tint (rgb, factor) multiplies the albedo (render only; the glTF gets the plain texture)."""
    if not MANIFEST or role not in MANIFEST['textures']:
        return mat(name, color, rough, noise=fallback_noise)
    if name in MATS: return MATS[name]
    T = MANIFEST['textures'][role]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    uv = nt.nodes.new('ShaderNodeUVMap'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1 / tile)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector'])
    def tex(rel, nc):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(rel, nc); nt.links.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    d = tex(T['diff'], False); d.label = 'DIFF'
    if tint:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = tint[1]; mx.inputs[7].default_value = (*tint[0], 1)
        nt.links.new(d.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    else:
        nt.links.new(d.outputs['Color'], b.inputs['Base Color'])
    r = tex(T['rough'], True); r.label = 'ROUGH'
    rm = nt.nodes.new('ShaderNodeMath'); rm.operation = 'MULTIPLY'; rm.inputs[1].default_value = rough / .8
    nt.links.new(r.outputs['Color'], rm.inputs[0]); nt.links.new(rm.outputs[0], b.inputs['Roughness'])
    n = tex(T['nor'], True); n.label = 'NOR'
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    m.diffuse_color = (*color, 1); m['textured'] = True
    MATS[name] = m; return m

def stripe_mat(name, c1, c2, period=.5):
    """Painted curb stripes (Thai equipment islands): alternating colours along world X+Y."""
    if name in MATS: return MATS[name]
    m = mat(name + '_base', c1, .55); m.name = name; MATS[name] = m
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    g = nt.nodes.new('ShaderNodeNewGeometry'); ch = nt.nodes.new('ShaderNodeTexChecker')
    ch.inputs['Scale'].default_value = 1 / period
    ch.inputs['Color1'].default_value = (*c1, 1); ch.inputs['Color2'].default_value = (*c2, 1)
    off = nt.nodes.new('ShaderNodeVectorMath'); off.inputs[1].default_value = (0, 0, .013)
    nt.links.new(g.outputs['Position'], off.inputs[0]); nt.links.new(off.outputs[0], ch.inputs['Vector'])
    nt.links.new(ch.outputs['Color'], b.inputs['Base Color'])
    return m

M = dict(
    grass=tmat('Grass', 'grass', 3.0, (.11, .21, .055), .9, tint=((.34, .62, .2), 1.), fallback_noise=(.35, .18, (.07, .14, .035))),
    asphalt=tmat('Asphalt', 'asphalt', 4.0, (.05, .05, .05), .85, tint=((.62, .62, .64), 1.), fallback_noise=(1.5, .12, (.032, .032, .033))),
    street=tmat('StreetAsphalt', 'asphalt', 3.3, (.042, .042, .043), .8, tint=((.48, .48, .5), 1.), fallback_noise=(1.2, .12, (.028, .028, .029))),
    paint=mat('PaintWhite', (.8, .8, .77), .55),
    yellow=mat('PaintYellow', (.82, .58, .05), .55),
    blue=mat('PaintBlue', (.04, .2, .58), .6),
    green=mat('PaintGreen', (.05, .42, .2), .6),
    concrete=tmat('Concrete', 'concrete', 2.0, (.55, .54, .51), .8, fallback_noise=(2.0, .1, (.45, .44, .41))),
    curb=tmat('Curb', 'concrete', 1.5, (.62, .61, .58), .75, tint=((1.1, 1.1, 1.08), 1.)),
    sidewalk=tmat('Pavers', 'pavers', 1.6, (.58, .52, .46), .8, fallback_noise=(3.0, .12, (.48, .43, .38))),
    curb_stripe=stripe_mat('CurbStripe', (.85, .65, .05), (.03, .03, .03)),
    stain=mat('OilStain', (.0, .0, .0), .35),
    wall=mat('BuildingWall', (.78, .76, .72), .7),
    glass=mat('Glass', (.05, .09, .12), .08, .3),
    roof=mat('Roof', (.35, .35, .36), .8),
    metal=mat('Galvanised', (.55, .56, .58), .35, .9),
    dark=mat('DarkMetal', (.06, .06, .07), .4, .5),
    black=mat('Rubber', (.02, .02, .02), .8),
    orange=mat('SafetyOrange', (.9, .38, .03), .45),
    red=mat('Red', (.7, .04, .03), .45),
    white=mat('WhitePlastic', (.85, .85, .85), .4),
    navy=mat('Navy', (.04, .07, .18), .4),
    trunk=mat('Bark', (.18, .11, .06), .9),
    leaf=mat('Foliage', (.06, .22, .05), .8, noise=(1.2, .2, (.03, .14, .03))),
    leaf2=mat('Foliage2', (.12, .30, .06), .8, noise=(1.2, .2, (.06, .18, .04))),
    screen=mat('ScreenBlue', (.02, .1, .25), .15, emit=(.12, .4, .95), estr=1.1),
    led_g=mat('LedGreen', (.02, .2, .05), .3, emit=(.1, 1., .25), estr=6.),
    led_r=mat('LedRed', (.25, .02, .02), .3, emit=(1., .08, .05), estr=5.),
    lamp=mat('LampLens', (.9, .9, .85), .2, emit=(1., .95, .85), estr=4.),
    loop=mat('LoopGroove', (.004, .004, .004), .45),
    loop_seal=mat('LoopTar', (.018, .018, .02), .16),
    plate=mat('LabelPlate', (.02, .02, .03), .5),
    labeltext=mat('LabelText', (1, 1, 1), .5, emit=(1, 1, 1), estr=1.5),
)
CAR_COLORS = [(.85, .85, .84), (.6, .61, .63), (.03, .03, .035), (.3, .31, .33), (.55, .05, .04), (.06, .16, .4), (.85, .85, .84), (.6, .61, .63)]

# ------------------------------------------------------------------ mesh helpers
def link(obj, c='Site'):
    coll(c).objects.link(obj); return obj

def signed_area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2

def ccw(p):
    p = [tuple(x) for x in p]
    return p if signed_area(p) > 0 else p[::-1]

def offset_poly(p, d):
    """Offset a CCW polygon outward by d (mitred)."""
    p = ccw(p); n = len(p); out = []
    for i in range(n):
        a, b, c = Vector(p[i - 1]), Vector(p[i]), Vector(p[(i + 1) % n])
        e1 = (b - a).normalized(); e2 = (c - b).normalized()
        n1 = Vector((e1.y, -e1.x)); n2 = Vector((e2.y, -e2.x))
        m = (n1 + n2).normalized(); k = d / max(.3, m.dot(n1))
        out.append(tuple(b + m * k))
    return out

def world_uv(me):
    """UVs in world metres: tops use (x, y), sides use (along-wall, z). Objects sit at the origin."""
    uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        side = abs(p.normal.z) < .5
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = ((co.x * abs(p.normal.y) + co.y * abs(p.normal.x)), co.z) if side else (co.x, co.y)

def poly_obj(name, pts, z, material, height=0., inset=None, c='Site'):
    """Flat polygon at z, or a prism z..z+height. inset=(width, material2) puts material2 on an inset top."""
    bm = bmesh.new(); pts = ccw(pts)
    vs = [bm.verts.new((x, y, z)) for x, y in pts]
    f = bm.faces.new(vs)
    if height > 0:
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        top = [v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)]
        for v in top: v.co.z += height
        f.normal_flip()
        tops = [g for g in r['geom'] if isinstance(g, bmesh.types.BMFace)]
        if inset:
            res = bmesh.ops.inset_region(bm, faces=tops, thickness=inset[0], use_even_offset=True)
            for t in tops: t.material_index = 1
    bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); world_uv(me)
    me.materials.append(material)
    if inset: me.materials.append(inset[1])
    return link(bpy.data.objects.new(name, me), c)

def quads_obj(name, quads, z, material, c='Site'):
    verts, faces = [], []
    for q in quads:
        i = len(verts); verts += [(x, y, z) for x, y in ccw(q)]; faces.append((i, i + 1, i + 2, i + 3))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); world_uv(me)
    me.materials.append(material)
    return link(bpy.data.objects.new(name, me), c)

def seg_quad(a, b, w):
    a, b = Vector(a), Vector(b); d = (b - a);
    if d.length < 1e-6: return None
    n = Vector((-d.y, d.x)).normalized() * w / 2
    return [tuple(a + n), tuple(b + n), tuple(b - n), tuple(a - n)]

def box(bm_or_name, size, loc=(0, 0, 0), material=None, parent=None, rot=(0, 0, 0), bevel=None, c='Equipment'):
    """Box object (size x,y,z), loc = centre of the bottom face in parent space."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z = (v.co.z + .5) * size[2]
    if bevel is None: bevel = min(.008, min(size) * .2)   # soft edges catch highlights
    me = bpy.data.meshes.new(bm_or_name); bm.to_mesh(me); bm.free()
    if material: me.materials.append(material)
    o = link(bpy.data.objects.new(bm_or_name, me), c)
    if bevel > 1e-4:     # render-only bevel: renders get soft edges, the .glb keeps plain 12-triangle boxes
        bv = o.modifiers.new('Bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.show_viewport = False
    o.location = loc; o.rotation_euler = rot
    if parent: o.parent = parent
    return o

def cyl(name, r, h, loc=(0, 0, 0), material=None, parent=None, rot=(0, 0, 0), r2=None, seg=16, c='Equipment'):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    for v in bm.verts: v.co.z += h / 2
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if material: me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(name, me), c)
    o.location = loc; o.rotation_euler = rot
    if parent: o.parent = parent
    return o

THAI_FONT = next((p for p in (os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', f) for f in ('tahomabd.ttf', 'tahoma.ttf', 'leelawdb.ttf')) if os.path.exists(p)), None)
def text_mesh(name, body, size, material, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), extrude=0., c='Equipment', thai=False, font=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size
    if thai and THAI_FONT: cu.font = bpy.data.fonts.load(THAI_FONT, check_existing=True)     # Blender's built-in font has no Thai glyphs
    if font and os.path.exists(font): cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = extrude
    tmp = bpy.data.objects.new(name + '_tmp', cu); sc.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    me.materials.clear(); me.materials.append(material)
    o = link(bpy.data.objects.new(name, me), c); o.location = loc; o.rotation_euler = rot
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ ground surfaces
def poly_dist2(pt, poly):
    best = 1e9; P = Vector(pt)
    for i in range(len(poly)):
        A_, B_ = Vector(poly[i]), Vector(poly[(i + 1) % len(poly)]); d = B_ - A_; L2 = d.length_squared
        t_ = 0 if L2 == 0 else max(0, min(1, (P - A_).dot(d) / L2)); best = min(best, (A_ + d * t_ - P).length)
    return best

def inside(pt, poly):
    x, y = pt; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c

allpts = list(L['site'] or [])
for k in ('buildings', 'islands', 'sidewalks', 'parking_areas', 'streets'):
    for b in L[k]: allpts += b['polygon']
for r in L['roads']: allpts += r['band']
for w_ in L.get('water', []): allpts += w_['polygon']
X0, X1 = min(p[0] for p in allpts), max(p[0] for p in allpts)
Y0, Y1 = min(p[1] for p in allpts), max(p[1] for p in allpts)
CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2
pad = 1500
poly_obj('Ground', [(X0 - pad, Y0 - pad), (X1 + pad, Y0 - pad), (X1 + pad, Y1 + pad), (X0 - pad, Y1 + pad)], 0, M['grass'])

Z_ASP, Z_PAINT, Z_FILL, CURB = .02, .026, .023, .15
for s in L['streets']:
    poly_obj(f"Street_{s.get('id', '')}", s['polygon'], .012, M['street'])
    cl = s.get('centerline')
    if cl:
        dashes = []
        for a, b in zip(cl, cl[1:]):
            A, B = Vector(a), Vector(b); n = int((B - A).length // 6)
            for i in range(n):
                q = seg_quad(A + (B - A) * (i / n), A + (B - A) * ((i + .5) / n), .12)
                if q: dashes.append(q)
        quads_obj('StreetCentreLine', dashes, .018, M['paint'])
for A in L['parking_areas']:
    poly_obj(f"Lot_{A.get('id', '')}", A['polygon'], Z_ASP, M['asphalt'])
for r in L['roads']:
    poly_obj(f"Road_{r.get('id', '')}", r['band'], Z_ASP - .001, M['asphalt'])
for s in L['sidewalks']:
    poly_obj(f"Sidewalk_{s.get('id', '')}", s['polygon'], 0, M['curb'], CURB, inset=(.15, M['sidewalk']))
for s in L['islands']:
    poly_obj(f"Island_{s.get('id', '')}", s['polygon'], 0, M['curb'], CURB, inset=(.15, M['concrete'] if s.get('kind') == 'equipment' else M['grass']))
    if s.get('kind') == 'equipment': o_ = bpy.data.objects[f"Island_{s.get('id', '')}"]; o_.data.materials[0] = M['curb_stripe']
for s in L['no_parking']:
    q = s['polygon']; xs = [p[0] for p in q]; ys = [p[1] for p in q]
    hatch = []
    for t in range(int(min(xs) - max(ys)), int(max(xs) - min(ys)), 1):
        pass
    poly_obj(f"NoParking_{s.get('id', '')}", q, Z_FILL, M['yellow'])

# ------------------------------------------------------------------ paint: stalls, arrows
stripes, seen = [], set()
def stripe(a, b, w=.1, bucket=None):
    key = tuple(sorted([(round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))]))
    if key in seen: return
    seen.add(key); q = seg_quad(a, b, w)
    if q: (bucket if bucket is not None else stripes).append(q)
fills = {'accessible': [], 'ev': []}
hatch = []
moto_stripes = []
for s in L['stalls']:
    q = s['quad']; t = s['type']
    bucket = moto_stripes if t == 'motorcycle' else stripes
    stripe(q[0], q[3], .1, bucket); stripe(q[1], q[2], .1, bucket)
    if s.get('front') and abs(Vector(q[1]).x - Vector(q[0]).x) > 0 and s.get('axis') and abs(s['axis'][0]) > 0 and abs(s['axis'][1]) < 1e-6:
        stripe(q[3], q[2], .1, bucket)   # parallel stalls get a kerb-side line
    if t in fills:
        c = Vector(q[0]) * .25 + Vector(q[1]) * .25 + Vector(q[2]) * .25 + Vector(q[3]) * .25
        fills[t].append([tuple(c + (Vector(p) - c) * .93) for p in q])
    if t == 'access_aisle':   # diagonal hatching inside the access aisle
        A_, B_, C_, D_ = map(Vector, q)
        for i in range(1, 7):
            f = i / 7; stripe(A_.lerp(D_, f), B_.lerp(C_, max(0, f - .15)), .08)
quads_obj('StallLines', stripes, Z_PAINT, M['paint'])
if moto_stripes: quads_obj('MotoStallLines', moto_stripes, Z_PAINT, M['yellow'])
if fills['accessible']: quads_obj('AccessibleFill', fills['accessible'], Z_FILL, M['blue'])
if fills['ev']: quads_obj('EVFill', fills['ev'], Z_FILL, M['green'])

# oil stains / tyre wear under parked positions (render only: collection 'Decals', not exported)
def stain_material():
    m = M['stain']; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    uv = nt.nodes.new('ShaderNodeUVMap'); sub = nt.nodes.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (.5, .5, 0); nt.links.new(uv.outputs['UV'], sub.inputs[0])
    ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; nt.links.new(sub.outputs[0], ln.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = .5; mr.inputs['From Max'].default_value = .05
    nt.links.new(ln.outputs['Value'], mr.inputs['Value'])
    g = nt.nodes.new('ShaderNodeNewGeometry'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 6
    nt.links.new(g.outputs['Position'], nz.inputs['Vector'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; nt.links.new(mr.outputs['Result'], mul.inputs[0]); nt.links.new(nz.outputs['Fac'], mul.inputs[1])
    mul2 = nt.nodes.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = .75
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(mul2.outputs[0], b.inputs['Alpha'])
    b.inputs['Base Color'].default_value = (.008, .008, .008, 1)
stain_material()
sv, sf, suv = [], [], []
rs = random.Random(11)
for s in L['stalls']:
    if s['type'] not in ('normal', 'ev') or rs.random() > .55: continue
    q = [Vector(p) for p in s['quad']]; c = sum(q, Vector((0, 0))) / 4
    ax = (q[3] - q[0]); ax = ax.normalized() if ax.length > 1e-6 else Vector((0, 1)); sd = Vector((-ax.y, ax.x))
    c = c + ax * rs.uniform(-.3, .6); w, l = rs.uniform(.9, 1.6), rs.uniform(1.4, 2.6)
    i = len(sv)
    for (u, v) in ((0, 0), (1, 0), (1, 1), (0, 1)):
        p = c + sd * (u - .5) * w + ax * (v - .5) * l; sv.append((p.x, p.y, Z_FILL - .001)); suv.append((u, v))
    sf.append((i, i + 1, i + 2, i + 3))
if sf:
    me = bpy.data.meshes.new('Stains'); me.from_pydata(sv, [], sf); uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices: uvl.data[li].uv = suv[me.loops[li].vertex_index]
    me.materials.append(M['stain']); link(bpy.data.objects.new('Stains', me), 'Decals')

# wheelchair-ish symbol: white circle + seat block on each accessible stall
sym = []
for s in L['stalls']:
    if s['type'] != 'accessible': continue
    q = [Vector(p) for p in s['quad']]; c = sum(q, Vector((0, 0))) / 4
    ax = (q[3] - q[0]).normalized(); sd = (q[1] - q[0]).normalized()
    for k in range(16):
        a0, a1 = k / 16 * math.tau, (k + 1) / 16 * math.tau
        r0, r1 = .55, .7
        P = lambda r, a: c + sd * (math.cos(a) * r) + ax * (math.sin(a) * r)
        sym.append([tuple(P(r0, a0)), tuple(P(r1, a0)), tuple(P(r1, a1)), tuple(P(r0, a1))])
    sym.append([tuple(c - sd * .12 - ax * .25), tuple(c + sd * .12 - ax * .25), tuple(c + sd * .12 + ax * .45), tuple(c - sd * .12 + ax * .45)])
    sym.append([tuple(c - sd * .12 + ax * .3), tuple(c + sd * .45 + ax * .3), tuple(c + sd * .45 + ax * .45), tuple(c - sd * .12 + ax * .45)])
if sym: quads_obj('AccessibleSymbol', sym, Z_PAINT + .001, M['paint'])

def arrow_quads(pos, heading, length=3.2, w=.22, head=.95, hl=1.1):
    h = math.radians(heading); d = Vector((math.cos(h), math.sin(h))); n = Vector((-d.y, d.x))
    p = Vector(pos) - d * length / 2
    shaft = [p - n * w / 2, p + d * (length - hl) - n * w / 2, p + d * (length - hl) + n * w / 2, p + n * w / 2]
    tip = p + d * length; hb = p + d * (length - hl)
    headq = [hb - n * head / 2, tip, tip, hb + n * head / 2]
    return [[tuple(v) for v in shaft], [tuple(v) for v in headq]]
arrows = []
for a in L['aisles']:
    A_, B_ = Vector(a['a']), Vector(a['b']); d = B_ - A_; Ln = d.length
    if Ln < 8: continue
    hd = math.degrees(math.atan2(d.y, d.x)); n = Vector((-d.y, d.x)).normalized()
    k = max(1, int(Ln // 20))
    for i in range(k):
        p = A_ + d * ((i + .5) / k)
        if a.get('one_way'):
            arrows += arrow_quads(p, hd)
        else:
            arrows += arrow_quads(p + n * a['width'] / 4, hd + 180)   # drive on the left
            arrows += arrow_quads(p - n * a['width'] / 4, hd)
for a in L['arrows']:
    arrows += arrow_quads(a['pos'], a['heading'])
if arrows: quads_obj('Arrows', arrows, Z_PAINT, M['paint'])

# extra painted lines (lane dividers / edge lines from gate kits or the plan)
wl, yl = [], []
for ln in L.get('lines', []):
    P = [Vector(p) for p in ln['points']]; w = ln.get('width', .12)
    for a_, b_ in zip(P, P[1:]):
        segs = [(a_, b_)]
        if ln.get('dashed'):
            d = (b_ - a_); n_ = max(1, int(d.length / 4)); segs = [(a_ + d * (k / n_), a_ + d * ((k + .5) / n_)) for k in range(n_)]
        for s0, s1 in segs:
            q = seg_quad(tuple(s0), tuple(s1), w)
            if q: (yl if ln.get('color') == 'yellow' else wl).append(q)
for r in L['roads']:               # every ordinary road: dashed centre line + solid edge lines
    if r.get('kit') or not r.get('markings', True) or r.get('width', 6) < 5.5: continue
    P = [Vector(p) for p in r['points']]; hw = r.get('width', 6) / 2 - .35
    for a_, b_ in zip(P, P[1:]):
        dv = b_ - a_; Ln = dv.length
        if Ln < 1: continue
        t_ = dv / Ln; n_ = Vector((-t_.y, t_.x)); tr = r.get('trim', 0); t0, t1 = (tr, tr) if not isinstance(tr, list) else tr
        A2, B2 = a_ + t_ * min(t0, Ln / 3), b_ - t_ * min(t1, Ln / 3)       # trim = keep junction mouths free of edge lines
        for s_ in (1, -1):
            q = seg_quad(tuple(A2 + n_ * hw * s_), tuple(B2 + n_ * hw * s_), .12)
            if q: wl.append(q)
        nd = max(1, int((B2 - A2).length / 6))
        for k_ in range(nd):
            q = seg_quad(tuple(A2 + (B2 - A2) * (k_ / nd)), tuple(A2 + (B2 - A2) * ((k_ + .5) / nd)), .12)
            if q: (yl if r.get('centre') == 'yellow' else wl).append(q)
if wl: quads_obj('LinesWhite', wl, Z_PAINT + .0005, M['paint'])
if yl: quads_obj('LinesYellow', yl, Z_PAINT + .0005, M['yellow'])
# water (canals, ponds)
M['water'] = mat('Water', (.05, .16, .2), .05, .0)
for k, wtr in enumerate(L.get('water', [])):
    poly_obj(f'Water_{k}', wtr['polygon'], -.3, M['water'])
# cable routes (uplink fibre / power) from the control room, drawn as coloured bands just above ground
for k, cb in enumerate(L.get('cables', [])):
    col = tuple(cb.get('color', [.1, .3, .9])); cm = mat(f"Cable_{cb.get('id', k)}", col, .4, emit=col, estr=1.5)
    qs = [seg_quad(tuple(a_), tuple(b_), cb.get('width', .8)) for a_, b_ in zip(cb['points'], cb['points'][1:])]
    o = quads_obj(f"Cable_{cb.get('id', k)}", [q for q in qs if q], .06, cm, 'Cables')
    o['cable'] = json.dumps({k_: cb[k_] for k_ in ('id', 'label', 'length_m', 'to') if k_ in cb}, ensure_ascii=False)
# ------------------------------------------------------------------ road realism: curbs, stop lines, island noses, drains
PAVED = [a['polygon'] for a in L['parking_areas']] + [r['band'] for r in L['roads']] + [s['polygon'] for s in L['streets']] \
      + [s['polygon'] for s in L['sidewalks']] + [s['polygon'] for s in L['islands']]
def paved(pt): return any(inside(pt, p) for p in PAVED)
def centroid_(p): return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))
cv, cf, curb_pieces = [], [], []
for poly in [a['polygon'] for a in L['parking_areas']] + [r['band'] for r in L['roads']]:
    P = ccw(poly)
    for i in range(len(P)):
        A_, B_ = Vector(P[i]), Vector(P[(i + 1) % len(P)]); d = B_ - A_
        if d.length < .2: continue
        n_ = Vector((d.y, -d.x)).normalized(); k = max(1, int(d.length / .9))
        keep = []
        for j in range(k):
            a_, b_ = A_.lerp(B_, j / k), A_.lerp(B_, (j + 1) / k); m_ = (a_ + b_) / 2
            ok_ = not (paved(m_ + n_ * .3) or paved(m_ + n_ * .3 + d.normalized() * .2))
            keep.append(ok_)
            if ok_: curb_pieces.append((m_, n_))
        j = 0
        while j < k:             # one prism per continuous run (keeps the .glb small on long roads)
            if not keep[j]: j += 1; continue
            j0 = j
            while j < k and keep[j]: j += 1
            a_, b_ = A_.lerp(B_, j0 / k), A_.lerp(B_, j / k)
            q = [a_, b_, b_ + n_ * .15, a_ + n_ * .15]; base = len(cv)
            cv += [(p.x, p.y, 0) for p in q] + [(p.x, p.y, CURB) for p in q]
            cf += [(base, base + 3, base + 2, base + 1), (base + 4, base + 5, base + 6, base + 7),
                   (base, base + 1, base + 5, base + 4), (base + 1, base + 2, base + 6, base + 5),
                   (base + 2, base + 3, base + 7, base + 6), (base + 3, base, base + 4, base + 7)]
if cf:
    me = bpy.data.meshes.new('Curbs'); me.from_pydata(cv, [], cf); me.update(); world_uv(me); me.materials.append(M['curb'])
    link(bpy.data.objects.new('Curbs', me))
# drain grates every ~18 m along the curbs + a few manholes in the aisles
M['grate'] = mat('Grate', (.05, .05, .055), .55, .8)
FOCUS = [Vector(g['pos']) for g in L['gates']] + [Vector(centroid_(a['polygon'])) for a in L['parking_areas']]
for i, (m_, n_) in enumerate(curb_pieces):
    if i % 20 == 7 and (not FOCUS or min((m_ - f_).length for f_ in FOCUS) < 70):      # drains only around gates / lots
        p = m_ - n_ * .3; ang = math.atan2(n_.y, n_.x)
        box(f'Drain{i}', (.36, .6, .02), (p.x, p.y, Z_ASP - .012), M['grate'], rot=(0, 0, ang), bevel=.01, c='Site')
for k, a in enumerate(L['aisles'][:4]):
    p = Vector(a['a']).lerp(Vector(a['b']), .35)
    cyl(f'Manhole{k}', .36, .012, (p.x, p.y, Z_ASP - .004), M['grate'], seg=24, c='Site')
# stop lines + STOP text in front of every barrier, chevron hatching in front of equipment islands
stops, hatch_q = [], []
for e in L['equipment']:
    if e['type'] != 'barrier_gate': continue
    g = next((x for x in L['gates'] if x['id'] == e.get('gate')), None)
    h = math.radians(e.get('heading', 0)); a = Vector((math.cos(h), math.sin(h)))
    th = math.radians(e.get('traffic', (g or {}).get('heading', e.get('heading', 0) + 90))); t = Vector((math.cos(th), math.sin(th)))
    p0 = Vector(e['pos']); arm = e.get('arm', 3.5)
    pre = 2.0 if any(x['type'] == 'loop_detector' and x.get('role') == 'before' and x.get('lane') == e.get('lane') and x.get('gate') == e.get('gate') for x in L['equipment']) else 1.0
    q = seg_quad(tuple(p0 + a * .35 - t * pre), tuple(p0 + a * (arm + .2) - t * pre), .3)      # stop line in front of the presence loop
    if q: stops.append(q)
    c_ = p0 + a * (.26 + arm / 2) - t * (pre + 2.2)
    so = text_mesh(f"Stop_{e['id']}", 'STOP', 1.1, M['paint'], loc=(c_.x, c_.y, Z_PAINT), rot=(0, 0, math.atan2(t.y, t.x) - math.pi / 2), c='Site')
    bpy.context.view_layer.update(); fit = (arm - .9) / max(.1, so.dimensions.x)      # STOP must fit inside the lane, clear of islands
    if fit < .45: bpy.data.objects.remove(so)
    elif fit < 1: so.scale = (fit, fit, 1)
if stops: quads_obj('StopLines', stops, Z_PAINT, M['paint'])
for s in L['islands']:
    if s.get('kind') != 'equipment' or not L['gates'] or s.get('no_hatch'): continue
    cen = Vector((sum(p[0] for p in s['polygon']) / len(s['polygon']), sum(p[1] for p in s['polygon']) / len(s['polygon'])))
    g = min(L['gates'], key=lambda x: (Vector(x['pos']) - cen).length)
    th = math.radians(g.get('heading', 90)); t = Vector((math.cos(th), math.sin(th))); n_ = Vector((-t.y, t.x))
    pr = [Vector(p).dot(t) for p in s['polygon']]; pn = [Vector(p).dot(n_) for p in s['polygon']]
    end = min(pr); lo, hi = min(pn), max(pn); mid = (lo + hi) / 2
    P = lambda u, v: tuple(t * u + n_ * v)
    apex = P(end - 3.0, mid); bl, br = P(end - .05, lo), P(end - .05, hi)
    for a_, b_ in ((apex, bl), (apex, br), (bl, br)):
        q = seg_quad(a_, b_, .12); hatch_q.append(q)
    for k in range(1, 4):
        f_ = k / 4; u = end - 3.0 * (1 - f_)
        hw = (hi - lo) / 2 * f_
        q = seg_quad(P(u - .35, mid - hw), P(u + .1, mid + hw), .1); hatch_q.append(q)
if hatch_q: quads_obj('IslandHatch', hatch_q, Z_PAINT, M['yellow'])

# ------------------------------------------------------------------ buildings (library styles in buildings.py; non-rectangular footprints fall back to a glazed prism)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buildings as BLDG
BLDG.install(globals())
for b in L['buildings']:
    if BLDG.build(b, random.Random(sum(map(ord, str(b.get('id', 'x')))))) is not None: continue
    H = b.get('height', 8.0); poly = b['polygon']
    poly_obj(f"Building_{b.get('id', '')}", poly, 0, M['wall'], H)
    poly_obj(f"BuildingRoof_{b.get('id', '')}", offset_poly(poly, -.3), H, M['roof'], .05)
    # glass bands per floor (outer skin, slightly proud of the wall)
    ring = offset_poly(poly, .04); floors = max(1, int(H // 3.5))
    verts, faces = [], []
    for fl in range(floors):
        z0 = fl * 3.5 + (.3 if fl == 0 else 1.0); z1 = fl * 3.5 + 3.0
        for i in range(len(ring)):
            a, c_ = ring[i], ring[(i + 1) % len(ring)]; j = len(verts)
            verts += [(a[0], a[1], z0), (c_[0], c_[1], z0), (c_[0], c_[1], z1), (a[0], a[1], z1)]
            faces.append((j, j + 1, j + 2, j + 3))
    me = bpy.data.meshes.new('Glazing'); me.from_pydata(verts, [], faces); me.materials.append(M['glass'])
    link(bpy.data.objects.new(f"BuildingGlass_{b.get('id', '')}", me))
    # mullions
    mull = []
    for i in range(len(ring)):
        a, c_ = Vector(ring[i]), Vector(ring[(i + 1) % len(ring)]); n_ = int((c_ - a).length // 2.5)
        for k in range(1, n_):
            p = a.lerp(c_, k / n_); mull.append(p)
    mv, mf = [], []
    for p in mull:                 # all mullions of a building in one mesh
        base = len(mv)
        for zz in (0, H - .3):
            mv += [(p.x - .04, p.y - .04, zz), (p.x + .04, p.y - .04, zz), (p.x + .04, p.y + .04, zz), (p.x - .04, p.y + .04, zz)]
        mf += [(base, base + 1, base + 5, base + 4), (base + 1, base + 2, base + 6, base + 5), (base + 2, base + 3, base + 7, base + 6), (base + 3, base, base + 4, base + 7)]
    if mf:
        me_m = bpy.data.meshes.new('Mullions'); me_m.from_pydata(mv, [], mf); me_m.materials.append(M['dark'])
        link(bpy.data.objects.new(f"Mullions_{b.get('id', '')}", me_m))

# ------------------------------------------------------------------ trees + shrubs
def blob(bm, centre, r, rnd, squash=.8, subdiv=2, mi=0):
    before = set(bm.faces)
    g = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    for v in g['verts']:
        n = v.co.normalized()
        v.co = v.co * (1 + rnd.uniform(-.18, .18)); v.co.z *= squash; v.co += centre
    for f in set(bm.faces) - before: f.material_index = mi

def tree(pos, i):
    rnd = random.Random(i * 31 + 5)
    z = CURB if any(inside(pos, s['polygon']) for s in L['islands'] + L['sidewalks']) else 0
    h = rnd.uniform(5.0, 7.0); r = rnd.uniform(2.0, 2.8)
    bm = bmesh.new()
    def limb(a, b, r0, r1):
        a, b = Vector(a), Vector(b); d = b - a
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=r0, radius2=r1, depth=d.length)
        q = d.to_track_quat('Z', 'Y')
        for v in g['verts']:
            v.co.z += d.length / 2; v.co.rotate(q); v.co += a
    top = Vector((rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), h * .55))
    limb((0, 0, 0), top, .2, .12)
    ends = []
    for k in range(4):
        a = k / 4 * math.tau + rnd.uniform(-.4, .4)
        e = top + Vector((math.cos(a) * r * .55, math.sin(a) * r * .55, rnd.uniform(.6, 1.4)))
        limb(top - Vector((0, 0, .4)), e, .09, .04); ends.append(e)
    me_t = bpy.data.meshes.new('Trunk'); bm.to_mesh(me_t); bm.free(); me_t.materials.append(M['trunk'])
    for p_ in me_t.polygons: p_.use_smooth = True
    t = link(bpy.data.objects.new(f'TreeTrunk_{i}', me_t), 'Trees'); t.location = (pos[0], pos[1], z)
    bm = bmesh.new()
    centres = ends + [top + Vector((0, 0, 1.6))]
    for k in range(22):
        base = centres[k % len(centres)]
        off = base + Vector((rnd.uniform(-.8, .8), rnd.uniform(-.8, .8), rnd.uniform(-.3, .8)))
        blob(bm, off, r * rnd.uniform(.3, .45), rnd, .8, 3, k % 2)
    me = bpy.data.meshes.new('Canopy'); bm.to_mesh(me); bm.free()
    me.materials.append(M['leaf']); me.materials.append(M['leaf2'])
    for p_ in me.polygons: p_.use_smooth = True
    o = link(bpy.data.objects.new(f'TreeCanopy_{i}', me), 'Trees'); o.location = (pos[0], pos[1], z)
for i, p in enumerate(L['trees']): tree(p, i)

# distant tree belt so the horizon is not an empty field (render only, collection 'Backdrop')
def backdrop():
    protos = [o for o in coll('Trees').objects if o.name.startswith(('TreeTrunk_', 'TreeCanopy_'))]
    if not protos: return
    pairs = [(t, bpy.data.objects.get(t.name.replace('Trunk', 'Canopy'))) for t in protos if t.name.startswith('TreeTrunk_')]
    rnd = random.Random(3); n = 0; tries = 0
    streets = [s['polygon'] for s in L['streets']]
    while n < 140 and tries < 2000:
        tries += 1
        x = rnd.uniform(X0 - 90, X1 + 90); y = rnd.uniform(Y0 - 90, Y1 + 90)
        if X0 - 14 < x < X1 + 14 and Y0 - 14 < y < Y1 + 14: continue
        if any(inside((x, y), sp) for sp in streets) or any(inside((x, y + 4), sp) or inside((x, y - 4), sp) for sp in streets): continue
        t, cn = pairs[rnd.randrange(len(pairs))]; s_ = rnd.uniform(.8, 1.35); rz = rnd.uniform(0, math.tau)
        for src in (t, cn):
            if not src: continue
            o = bpy.data.objects.new(src.name + f'_bg{n}', src.data); link(o, 'Backdrop')
            o.location = (x, y, 0); o.scale = (s_, s_, s_ * rnd.uniform(.9, 1.2)); o.rotation_euler = (0, 0, rz)
        n += 1
backdrop()

# low shrubs around the edge of every green island
for k, s in enumerate(L['islands']):
    if s.get('kind') == 'equipment' or s.get('no_trees'): continue
    ring = offset_poly(s['polygon'], -.55); rnd = random.Random(100 + k); bm = bmesh.new()
    for a, b_ in zip(ring, ring[1:] + ring[:1]):
        A_, B_ = Vector(a), Vector(b_); n = max(1, int((B_ - A_).length / .9))
        for j in range(n):
            p = A_.lerp(B_, j / n)
            blob(bm, Vector((p.x, p.y, CURB + .25)), rnd.uniform(.32, .46), rnd, .75, 1, j % 2)
    me = bpy.data.meshes.new(f'Shrubs_{k}'); bm.to_mesh(me); bm.free()
    me.materials.append(M['leaf2']); me.materials.append(M['leaf'])
    for p_ in me.polygons: p_.use_smooth = True
    link(bpy.data.objects.new(f"Shrubs_{s.get('id', k)}", me), 'Trees')

# ------------------------------------------------------------------ cars (smooth lofted bodies, see cars.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cars as CARLIB
CARS = CARLIB.library(mat, M) if CAR_FILL > 0 else []

def moto_mesh(ci):
    """Scooter: 2 wheels, low body, seat, front shield, handlebar (x = forward)."""
    bm = bmesh.new()
    def part(sx, sy, sz, cx, cz, mi):
        before = set(bm.faces); r = bmesh.ops.create_cube(bm, size=1)
        for v in r['verts']: v.co.x = v.co.x * sx + cx; v.co.y *= sy; v.co.z = v.co.z * sz + cz
        bmesh.ops.bevel(bm, geom=list({e for f in set(bm.faces) - before for e in f.edges}), offset=.03, segments=2, affect='EDGES')
        for f in set(bm.faces) - before: f.material_index = mi
    for x in (-.62, .62):
        before = set(bm.faces)
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=.26, radius2=.26, depth=.11)
        for v in g['verts']:
            y, z = v.co.y, v.co.z; v.co.y, v.co.z = z, y; v.co += Vector((x, 0, .26))
        for f in set(bm.faces) - before: f.material_index = 1
    part(1.0, .32, .22, -.05, .45, 0)      # floor / body
    part(.62, .3, .22, -.28, .68, 0)       # rear body
    part(.6, .26, .08, -.25, .83, 1)       # seat
    part(.14, .36, .6, .5, .68, 0)         # front shield
    part(.05, .62, .04, .5, 1.02, 1)       # handlebar
    me = bpy.data.meshes.new(f'Moto_{ci}'); bm.to_mesh(me); bm.free()
    me.materials.append(mat(f'MotoBody_{ci}', [(.75, .75, .76), (.03, .03, .03), (.5, .05, .05), (.08, .2, .45)][ci], .3, .3))
    me.materials.append(M['black'])
    for p in me.polygons: p.use_smooth = True
    return me
MOTOS = [moto_mesh(i) for i in range(4)] if CAR_FILL > 0 else []

ncar = 0
for s in (L['stalls'] if CAR_FILL > 0 else []):
    t = s['type']
    if t in ('access_aisle',): continue
    fill = CAR_FILL * (.5 if t in ('accessible', 'ev') else 1)
    if random.random() > fill: continue
    q = [Vector(p) for p in s['quad']]
    front = (q[0] + q[1]) / 2; back = (q[2] + q[3]) / 2
    if t == 'motorcycle':
        o = link(bpy.data.objects.new(f"Moto_{s['id']}", MOTOS[random.randrange(4)]), 'Cars')
        c = (front + back) / 2; d = back - front
        o.location = (c.x, c.y, Z_ASP); o.rotation_euler = (0, 0, math.atan2(d.y, d.x)); continue
    d = back - front
    if d.length < 1: continue
    along = d.normalized()
    if abs(along.dot((q[1] - q[0]).normalized())) > .9:   # parallel stall: car along the kerb
        along = (q[1] - q[0]).normalized()
        c = (q[0] + q[1] + q[2] + q[3]) / 4
    else:
        c = front + along * (d.length / 2 + .15)
    CARLIB.place(CARS[random.randrange(len(CARS))], f"Car_{s['id']}", (c.x, c.y, Z_ASP),
                 math.atan2(along.y, along.x) + random.uniform(-.03, .03), coll('Cars')); ncar += 1

# ------------------------------------------------------------------ equipment
def ground_z(pos):
    if any(inside(pos, s['polygon']) for s in L['islands'] + L['sidewalks']): return CURB
    if any(inside(pos, a['polygon']) for a in L['parking_areas']) or any(inside(pos, r['band']) for r in L['roads']): return Z_ASP
    return 0.

def equip_root(e):
    o = bpy.data.objects.new(f"EQ_{e['id']}", None); link(o, 'Equipment')
    o.empty_display_size = .5
    o.location = (e['pos'][0], e['pos'][1], ground_z(e['pos']))
    o.rotation_euler = (0, 0, math.radians(e.get('heading', 0)))
    for k in ('id', 'type', 'label', 'name_th', 'gate', 'stall', 'note'):
        if e.get(k) is not None: o[k] = str(e[k])
    return o

# local frame: +X = heading (front of the device / arm direction), origin = ground under the device
M.update(
    powder=mat('PowderCoatGrey', (.32, .34, .36), .38, .2),
    yellowcab=mat('CabinetYellow', (.95, .62, .04), .35),
    steel=mat('BrushedSteel', (.62, .63, .65), .28, 1.0),
    vent=mat('VentSlot', (.01, .01, .01), .6),
    sticker=mat('StickerWhite', (.92, .92, .9), .5),
    reflect=mat('ReflectiveRed', (.75, .03, .02), .3),
    acryl=mat('Acrylic', (.85, .9, .95), .05),
    cone=mat('ConeOrange', (.95, .3, .02), .45),
    tdshell=mat('KioskShell', (.78, .8, .82), .3, .35),
    signlit=mat('SignLit', (.9, .92, .95), .3, emit=(1, 1, 1), estr=1.2),
    ui_btn=mat('UIButton', (.1, .45, .95), .3, emit=(.1, .45, 1), estr=1.4),
    white_refl=mat('ReflectiveWhite', (.9, .9, .9), .25, emit=(1, 1, 1), estr=.15),
)
def plinth(r, sx, sy, h=.1):
    box('Plinth', (sx, sy, h), (0, 0, -.02), M['concrete'], r, bevel=.02)
    for xx in (-sx / 2 + .06, sx / 2 - .06):
        for yy in (-sy / 2 + .06, sy / 2 - .06):
            cyl('Anchor', .012, .03, (xx, yy, h - .02), M['steel'], r, seg=8)

def vents(r, x, z0, n, w, face=1):
    for i in range(n):
        box('Vent', (.012, w, .012), (x * face, 0, z0 + i * .035), M['vent'], r, bevel=0)

def cone(name, loc, parent, h=.7):
    """Traffic cone: black square base, orange body, two white reflective collars."""
    x, y = loc
    box(f'{name}_Base', (.38, .38, .035), (x, y, 0), M['black'], parent, bevel=.01)
    cyl(f'{name}_Body', .15, h, (x, y, .03), M['cone'], parent, r2=.025, seg=18)
    for z0, z1 in ((.3, .4), (.5, .56)):
        r0 = .15 - (.125 * z0 / h) + .004; r1 = .15 - (.125 * z1 / h) + .004
        cyl(f'{name}_Band{z0}', r0, z1 - z0, (x, y, .03 + z0), M['white_refl'], parent, r2=r1, seg=18)

def build_barrier(e, r):
    eid = e['id']; fault = e.get('status', 'ok') != 'ok'
    plinth(r, .62, .62)
    # status materials are unique per barrier so the web viewer can switch them (LED_<id>, BEACON_<id>)
    led = mat(f'LED_{eid}', (.25, .02, .02), .3, emit=(1., .05, .03), estr=4.)
    beacon = mat(f'BEACON_{eid}', (.25, .02, .02) if fault else (.02, .2, .05), .3,
                 emit=(1., .05, .03) if fault else (.1, 1., .25), estr=6.)
    # hinged boom: everything on the arm hangs off ARM_<id> (pivot at the hub; rotate about local Y to open)
    piv = bpy.data.objects.new(f'ARM_{eid}', None); link(piv, 'Equipment'); piv.parent = r
    piv.location = (.22, 0, 1.06); piv.empty_display_size = .2                         # boom leaves the cabinet just under the cap
    HW.creative_barrier_cabinet(r, beacon, led)                                         # CREATIVE cabinet (hardware.py)
    L_ = e.get('arm', 3.5); n = max(4, int(L_ / .5))
    style = e.get('model', 'straight')
    if style in ARM_STYLES:          # other boom types live in hardware.py
        ARM_STYLES[style](e, piv, L_, led)
    else:
      for i in range(n):   # rounded aluminium boom with red reflective bands
        cyl(f'Arm{i}', .045, L_ / n, (.08 + i * L_ / n, 0, 0), M['reflect'] if i % 2 else M['white'], piv, rot=(0, math.pi / 2, 0), seg=12)
      cyl('ArmTip', .05, .05, (.08 + L_, 0, 0), M['black'], piv, rot=(0, math.pi / 2, 0), seg=12)
      box('ArmLED', (L_ - .1, .025, .018), (.1 + L_ / 2, 0, -.058), led, piv, bevel=0)
      box('ArmRubber', (L_ - .1, .03, .03), (.1 + L_ / 2, 0, -.09), M['black'], piv, bevel=.005)
    # boom rest post at the far end
    # boom rest: post under the arm with a U-fork the arm drops into (fork stays below the rubber)
    xr = .22 + .03 + L_ - .3
    cyl('RestPost', .04, .9, (xr, 0, 0), M['steel'], r, seg=10)
    box('RestFork', (.12, .18, .03), (xr, 0, .9), M['powder'], r)
    for yy in (-.075, .075):
        box(f'RestProng{yy}', (.05, .02, .12), (xr, yy, .93), M['powder'], r)
    box('RestPad', (.1, .11, .02), (xr, 0, .93), M['black'], r)
    if True:   # cone row is built for every barrier: visible only when faulty (viewer can toggle FAULT_<id> live)
        g = next((x for x in L['gates'] if x['id'] == e.get('gate')), None)
        hd = math.radians(e.get('traffic', (g or {}).get('heading', e.get('heading', 0) + 90)) - e.get('heading', 0))
        t = Vector((math.cos(hd), math.sin(hd)))                     # traffic direction in barrier-local space
        grp = bpy.data.objects.new(f'FAULT_{eid}', None); link(grp, 'Equipment'); grp.parent = r; grp['fault_props'] = 1
        # one straight row of cones across the lane, a few metres ahead of the stop line
        hb = math.radians(e.get('heading', 0)); base = Vector(e['pos'])
        def to_world(v): return base + Vector((v.x * math.cos(hb) - v.y * math.sin(hb), v.x * math.sin(hb) + v.y * math.cos(hb)))
        blockers = [s['polygon'] for s in L['islands'] + L['sidewalks']]
        def clear(w):     # cone base (r .19) + margin must be on open road, off islands and curbs
            if any(inside(w, p) for p in blockers): return False
            if any(poly_dist2(w, p) < .38 for p in blockers): return False
            return any(inside(w, a['polygon']) for a in L['parking_areas']) or any(inside(w, rb['band']) for rb in L['roads'])
        ok = [x / 20 for x in range(0, int((L_ + .8) * 20)) if clear(to_world(Vector((x / 20, 0)) - t * 3.2))]
        grp.location.z = Z_ASP - ground_z(e['pos'])          # cones stand on the asphalt, not at island height
        if ok:
            x0, x1 = min(ok), max(ok); nC = max(2, int(round((x1 - x0) / .75)) + 1)
            for k in range(nC):
                x = x0 + (x1 - x0) * k / (nC - 1)
                p = Vector((x, 0)) - t * 3.2
                cone(f'Cone{k}', (p.x, p.y), grp)
        if not fault:
            for ch in grp.children: ch.hide_render = True

def build_cone(e, r):
    cone('Cone', (0, 0), r)
def face_cyl(name, r_, depth, loc, material, parent, seg=20):
    """Round part sticking out of a +X-facing panel (buttons, lenses, LEDs)."""
    return cyl(name, r_, depth, loc, material, parent, rot=(0, math.pi / 2, 0), seg=seg)

def build_ticket(e, r, kind='ticket'):
    """Entry ticket dispenser: plinth, two-tone cabinet, driver-height head tilted toward the car window,
    rain hood, colour screen, big PRESS button, lit ticket mouth, RFID tap zone, speaker + intercom, snapshot camera."""
    plinth(r, .64, .78)
    shell = M['tdshell']; trim = M['navy']
    box('Pedestal', (.4, .5, .62), (-.02, 0, .08), shell, r, bevel=.03)
    box('KickPlate', (.012, .42, .14), (.181, 0, .1), M['steel'], r, bevel=0)
    box('DoorSeamL', (.004, .004, .5), (.182, -.205, .16), M['vent'], r, bevel=0)
    box('DoorSeamR', (.004, .004, .5), (.182, .205, .16), M['vent'], r, bevel=0)
    box('Lock', (.012, .035, .035), (.186, .17, .55), M['steel'], r)
    for i in range(7): box(f'VentL{i}', (.16, .004, .012), (-.02, -.252, .25 + i * .03), M['vent'], r, bevel=0)
    # head: tilted 18 degrees so the face looks up at the driver's window (local +X = lane)
    hd = bpy.data.objects.new('TD_Head', None); link(hd, 'Equipment'); hd.parent = r
    hd.location = (0, 0, .7); hd.rotation_euler = (0, math.radians(-9), 0)
    box('Collar', (.42, .52, .06), (-.02, 0, .66), M['navy'], r, bevel=.01)
    box('HeadShell', (.42, .54, .62), (0, 0, 0), shell, hd, bevel=.04)
    box('Band', (.425, .545, .07), (0, 0, .5), trim, hd, bevel=.01)
    box('FacePanel', (.012, .44, .5), (.212, 0, .04), M['dark'], hd, bevel=.006)
    box('Screen', (.006, .22, .14), (.219, 0, .4), M['screen'], hd, bevel=0)
    box('ScreenBezel', (.004, .25, .17), (.216, 0, .385), M['black'], hd, bevel=0)
    face_cyl('PressRing', .055, .012, (.218, -.1, .24), M['steel'], hd, 24)
    face_cyl('PressBtn', .045, .022, (.218, -.1, .24), M['led_g'] if kind == 'ticket' else M['led_r'], hd, 24)
    face_cyl('IntercomBtn', .018, .02, (.218, .13, .26), M['steel'], hd, 16)
    for i in range(4):          # speaker grille
        for j in range(4):
            face_cyl(f'Spk{i}{j}', .005, .006, (.218, .1 + i * .02, .2 - j * .02), M['vent'], hd, 8)
    box('TapZone', (.006, .12, .1), (.219, .11, .11), M['acryl'], hd, bevel=.004)
    face_cyl('TapIcon', .025, .004, (.223, .11, .11), M['screen'], hd, 16)
    box('MouthBezel', (.02, .18, .05), (.222, -.07, .09), M['steel'], hd, bevel=.008)
    box('Mouth', (.006, .13, .012), (.232, -.07, .09), M['led_g'], hd, bevel=0)
    box('SlipA', (.06, .055, .002), (.262, -.07, .09), M['sticker'], hd, bevel=0)                 # printed parking slip
    box('SlipB', (.05, .055, .002), (.305, -.07, .078), M['sticker'], hd, rot=(0, math.radians(28), 0), bevel=0)
    box('SlipPrint', (.04, .03, .0005), (.262, -.07, .0912), M['vent'], hd, bevel=0)
    face_cyl('SnapCam', .016, .015, (.218, 0, .5), M['glass'], hd, 16)
    box('Sticker', (.004, .16, .05), (.219, -.12, .4), M['sticker'], hd, bevel=0)
    box('Hood', (.56, .64, .035), (.06, 0, .62), trim, hd, bevel=.012)
    box('HoodLip', (.03, .64, .07), (.33, 0, .56), trim, hd, bevel=.008)

def build_card_reader(e, r):
    """Member card reader on a gooseneck pedestal: tilted reader head with RFID zone, status LED bar and display."""
    plinth(r, .4, .4, .08)
    box('BasePlate', (.24, .24, .015), (0, 0, .06), M['steel'], r, bevel=.004)
    box('Post', (.09, .09, .9), (0, 0, .075), M['tdshell'], r, bevel=.012)
    box('Neck', (.2, .07, .07), (.07, 0, .94), M['tdshell'], r, bevel=.015)
    hd = bpy.data.objects.new('CR_Head', None); link(hd, 'Equipment'); hd.parent = r
    hd.location = (.17, 0, .9); hd.rotation_euler = (0, math.radians(-20), 0)
    box('Head', (.12, .28, .34), (0, 0, 0), M['tdshell'], hd, bevel=.03)
    box('Face', (.008, .22, .28), (.062, 0, .03), M['dark'], hd, bevel=.005)
    box('Display', (.004, .14, .05), (.067, 0, .25), M['screen'], hd, bevel=0)
    face_cyl('Rfid', .05, .004, (.067, 0, .13), M['acryl'], hd, 24)
    face_cyl('RfidIcon', .02, .003, (.07, 0, .13), M['screen'], hd, 16)
    box('LedBar', (.004, .18, .012), (.067, 0, .05), M['led_g'], hd, bevel=0)
    box('Hood', (.16, .32, .02), (.02, 0, .34), M['navy'], hd, bevel=.006)
def build_pay(e, r):
    """Auto pay station: tall two-tone kiosk, lit header, slanted touch screen, ticket / QR / contactless / banknote /
    coin / receipt points, recessed change tray, help + intercom, camera, side vents, kick plate."""
    plinth(r, .84, 1.0, .08)
    shell = M['tdshell']; trim = M['navy']
    box('Body', (.56, .82, 1.5), (-.02, 0, .06), shell, r, bevel=.04)
    box('Kick', (.012, .7, .14), (.262, 0, .08), M['steel'], r, bevel=0)
    for s_ in (-1, 1):
        for i in range(8): box(f'Vent{s_}{i}', (.22, .004, .012), (-.04, s_ * .412, .3 + i * .032), M['vent'], r, bevel=0)
        box(f'SideStripe{s_}', (.5, .004, .04), (-.02, s_ * .412, 1.3), trim, r, bevel=0)
    box('DoorSeam', (.004, .004, 1.1), (.262, -.37, .2), M['vent'], r, bevel=0)
    box('Lock', (.012, .035, .035), (.266, -.33, .9), M['steel'], r)
    # header with lit sign
    box('Header', (.6, .86, .26), (-.02, 0, 1.56), trim, r, bevel=.03)
    box('Sign', (.006, .7, .14), (.283, 0, 1.62), M['signlit'], r, bevel=0)
    text_mesh('PayText', 'PAY STATION', .085, M['navy'], r, (.29, 0, 1.69), (math.pi / 2, 0, math.pi / 2))
    face_cyl('Cam', .014, .015, (.283, .32, 1.62), M['glass'], r, 14)
    # slanted upper face (screen) and vertical lower face (payment points), local +X = customer side
    up = bpy.data.objects.new('PS_Upper', None); link(up, 'Equipment'); up.parent = r
    up.location = (.262, 0, 1.13); up.rotation_euler = (0, 0, 0)                 # screen sits above the payment fascia
    box('ScreenFrame', (.03, .64, .38), (0, 0, 0), M['dark'], up, bevel=.01)
    box('ScreenHood', (.08, .68, .025), (.03, 0, .38), M['navy'], up, bevel=.006)
    box('Screen', (.006, .52, .3), (.022, 0, .03), M['screen'], up, bevel=0)
    for k in range(3): box(f'UI{k}', (.004, .13, .045), (.026, -.16 + k * .16, .07), M['ui_btn'], up, bevel=0)
    box('UIHead', (.004, .4, .035), (.026, 0, .25), M['sticker'], up, bevel=0)
    box('Fascia', (.012, .66, .74), (.266, 0, .36), M['dark'], r, bevel=.006)
    def bezel(name, w, h, z, y, inner_mat, iw=None, ih=None):
        box(name + 'Bz', (.02, w, h), (.276, y, z), M['steel'], r, bevel=.006)
        box(name, (.006, iw or w * .75, ih or h * .3), (.286, y, z + h * .35), inner_mat, r, bevel=0)
    bezel('Ticket', .2, .07, 1.0, -.18, M['led_g'])                 # insert parking ticket
    box('QRWin', (.008, .12, .1), (.276, .17, 1.0), M['glass'], r, bevel=.004)
    box('QRLed', (.004, .1, .01), (.282, .17, 1.06), M['led_r'], r, bevel=0)
    box('NFC', (.01, .14, .12), (.276, .17, .86), M['acryl'], r, bevel=.006)
    face_cyl('NFCIcon', .028, .004, (.282, .17, .92), M['screen'], r, 16)
    bezel('Note', .2, .09, .84, -.18, M['led_g'])                   # banknote acceptor
    face_cyl('CoinSlot', .03, .015, (.276, -.18, .74), M['steel'], r, 18)
    box('CoinSlit', (.006, .006, .035), (.285, -.18, .74), M['black'], r, bevel=0)
    bezel('Receipt', .16, .05, .72, .17, M['vent'])
    box('TrayFrame', (.06, .3, .16), (.27, 0, .38), M['steel'], r, bevel=.01)
    box('TrayCavity', (.03, .24, .1), (.29, 0, .41), M['black'], r, bevel=0)
    face_cyl('Help', .028, .02, (.276, .3, .62), M['led_r'], r, 18)
    for i in range(3):
        for j in range(3): face_cyl(f'Spk{i}{j}', .005, .006, (.276, -.32 + i * .02, .64 - j * .02), M['vent'], r, 8)
    box('Instr', (.004, .2, .12), (.274, .02, .6), M['sticker'], r, bevel=0)
def build_lpr(e, r):
    """ANPR camera on a short lane-side pole: base plate with anchor bolts, square post with cap, swivel bracket,
    long weatherproof housing with a curved sun shield, front glass, lens, IR illuminator array, cable gland."""
    plinth(r, .36, .36, .08)
    box('BasePlate', (.22, .22, .015), (0, 0, .06), M['steel'], r, bevel=.004)
    for xx in (-.08, .08):
        for yy in (-.08, .08): cyl('Bolt', .01, .03, (xx, yy, .075), M['steel'], r, seg=8)
    box('Post', (.08, .08, 1.3), (0, 0, .075), M['tdshell'], r, bevel=.01)
    box('PostCap', (.1, .1, .02), (0, 0, 1.375), M['navy'], r, bevel=.005)
    cyl('Swivel', .03, .08, (0, 0, 1.395), M['steel'], r, seg=12)
    hd = bpy.data.objects.new('LPR_Head', None); link(hd, 'Equipment'); hd.parent = r
    hd.location = (0, 0, 1.5); hd.rotation_euler = (0, math.radians(e.get('tilt', 7)), 0)   # aimed down at the approaching plate
    box('Bracket', (.08, .05, .06), (-.02, 0, -.06), M['steel'], hd, bevel=.008)
    box('Housing', (.44, .13, .12), (.08, 0, -.02), M['white'], hd, bevel=.03)
    box('RearCap', (.03, .14, .13), (-.15, 0, -.025), M['powder'], hd, bevel=.01)
    cyl('Gland', .012, .04, (-.18, 0, .04), M['black'], hd, rot=(0, math.pi / 2, 0), seg=10)
    # sun shield: top plate + short side skirts, overhanging the glass
    box('ShieldTop', (.52, .17, .008), (.11, 0, .11), M['white'], hd, bevel=.003)
    for yy in (-.082, .082):
        box(f'ShieldSide{yy}', (.4, .006, .05), (.14, yy, .065), M['white'], hd, bevel=0)
    box('FrontBezel', (.012, .12, .11), (.305, 0, -.015), M['black'], hd, bevel=.008)
    box('Glass', (.004, .1, .09), (.312, 0, -.01), M['glass'], hd, bevel=0)
    face_cyl('Lens', .026, .01, (.312, 0, .0), M['dark'], hd, 20)
    face_cyl('LensGlass', .016, .004, (.318, 0, .0), M['glass'], hd, 16)
    for k in range(10):            # IR LED ring around the lens
        a = k / 10 * math.tau
        face_cyl(f'IR{k}', .0055, .004, (.314, math.cos(a) * .038, math.sin(a) * .032 - .002), M['led_r'], hd, 8)
    box('Label', (.12, .002, .03), (.06, -.066, -.02), M['sticker'], hd, bevel=0)
    if e.get('display'):     # LED display under the camera: shows the plate / welcome text to the driver
        dp = bpy.data.objects.new('LPR_Display', None); link(dp, 'Equipment'); dp.parent = r      # faces the driver, shifted over the island
        dp.rotation_euler = (0, 0, math.radians(e.get('display_yaw', 0))); ys = e.get('display_shift', 0)
        box('DispBracket', (.06, .12, .5), (.06, ys * .5, .62), M['steel'], dp, bevel=0)
        box('DispBox', (.1, .62, .48), (.11, ys, .6), M['powder'], dp, bevel=.02)                   # large LED screen for the driver
        box('DispFace', (.006, .56, .42), (.163, ys, .63), M['dark'], dp, bevel=0)
        text_mesh('DispPlate', e.get('plate', 'กข 1234'), .14, M['led_g'], dp, (.168, ys, .91), (math.pi / 2, 0, math.pi / 2), thai=True)
        text_mesh('DispText', e.get('message', 'WELCOME'), .075, M['led_r'], dp, (.168, ys, .73), (math.pi / 2, 0, math.pi / 2))

def build_radar(e, r):
    """Vehicle presence radar for barrier safety: small housing on a short post, aimed across the lane."""
    box('BasePlate', (.16, .16, .012), (0, 0, 0), M['steel'], r, bevel=.003)
    box('Post', (.06, .06, .5), (0, 0, .012), M['powder'], r, bevel=.008)
    box('Housing', (.07, .14, .12), (.03, 0, .5), M['white'], r, bevel=.02)
    box('Radome', (.006, .11, .09), (.067, 0, .515), M['dark'], r, bevel=0)
    box('Led', (.004, .02, .01), (.071, .045, .6), M['led_g'], r, bevel=0)

def build_cctv(e, r):
    """CCTV pole: concrete footing, flanged base with bolts, tapered galvanised pole, mid-height junction box with
    conduit, pole-top bracket. model 'bullet' (default) = bullet camera with sun shield on a wall mount;
    'ptz' = pendant PTZ dome on a goose-neck arm."""
    box('Footing', (.5, .5, .3), (0, 0, -.12), M['concrete'], r, bevel=.03)
    box('Flange', (.32, .32, .02), (0, 0, .18), M['steel'], r, bevel=.004)
    for xx in (-.12, .12):
        for yy in (-.12, .12):
            cyl('Bolt', .014, .05, (xx, yy, .2), M['steel'], r, seg=8)
    cyl('Gusset', .11, .12, (0, 0, .2), M['steel'], r, r2=.08, seg=16)
    cyl('Pole', .08, 4.3, (0, 0, .2), M['steel'], r, r2=.055, seg=16)
    cyl('PoleCap', .06, .04, (0, 0, 4.5), M['powder'], r, seg=16)
    box('JBox', (.16, .3, .4), (-.12, 0, 2.4), M['white'], r, bevel=.015)
    box('JBoxDoorSeam', (.004, .26, .004), (-.039, 0, 2.6), M['vent'], r, bevel=0)
    box('JBoxLock', (.01, .03, .03), (-.036, .1, 2.6), M['steel'], r)
    cyl('Conduit', .016, 2.2, (-.07, .12, .2), M['powder'], r, seg=8)
    for z_ in (.8, 1.6): box('Strap', (.18, .2, .025), (-.02, .04, z_), M['steel'], r, bevel=0)
    if e.get('model') == 'ptz':
        box('ArmMount', (.12, .12, .14), (.07, 0, 4.22), M['white'], r, bevel=.02)
        box('Neck', (.55, .06, .06), (.38, 0, 4.27), M['white'], r, bevel=.02)                  # arm out to the pendant
        p = Vector((.62, 0, 4.13))
        cyl('PtzCap', .1, .14, tuple(p), M['white'], r, r2=.09, seg=20)
        g = bpy.data.objects.new('PTZ_Dome', None); link(g, 'Equipment'); g.parent = r; g.location = tuple(p)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=.11)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > .002], context='VERTS')
        me = bpy.data.meshes.new('Dome'); bm.to_mesh(me); bm.free(); me.materials.append(M['glass'])
        for pl in me.polygons: pl.use_smooth = True
        d = link(bpy.data.objects.new('Dome', me), 'Equipment'); d.parent = g
        cyl('DomeRing', .112, .02, (0, 0, -.01), M['white'], g, seg=24)
        return
    box('ArmMount', (.1, .14, .16), (.07, 0, 4.3), M['white'], r, bevel=.02)
    box('Arm', (.45, .06, .06), (.32, 0, 4.4), M['white'], r, bevel=.01)
    hd = bpy.data.objects.new('CCTV_Head', None); link(hd, 'Equipment'); hd.parent = r
    hd.location = (.58, 0, 4.38); hd.rotation_euler = (0, math.radians(24), 0)
    cyl('Ball', .035, .06, (0, 0, -.03), M['white'], hd, seg=12)
    box('Body', (.34, .12, .12), (.12, 0, -.13), M['white'], hd, bevel=.03)
    box('RearCap', (.03, .125, .125), (-.06, 0, -.132), M['powder'], hd, bevel=.01)
    box('Shield', (.42, .16, .008), (.15, 0, .0), M['white'], hd, bevel=.003)
    for yy in (-.075, .075): box(f'ShieldSide{yy}', (.3, .005, .04), (.17, yy, -.035), M['white'], hd, bevel=0)
    box('Bezel', (.012, .11, .11), (.293, 0, -.13), M['black'], hd, bevel=.008)
    face_cyl('Lens', .025, .01, (.3, 0, -.075), M['dark'], hd, 18)
    face_cyl('LensGlass', .016, .004, (.306, 0, -.075), M['glass'], hd, 16)
    for k in range(8):
        a = k / 8 * math.tau
        face_cyl(f'IR{k}', .005, .004, (.302, math.cos(a) * .035, -.075 + math.sin(a) * .033), M['led_r'], hd, 8)
def build_vacancy(e, r):
    for y in (-.75, .75):
        box(f'Footing{y}', (.4, .4, .2), (0, y, 0), M['concrete'], r, bevel=.02)
        box(f'Post{y}', (.1, .1, 2.6), (0, y, .2), M['powder'], r, bevel=.01)
    box('Panel', (.16, 1.9, 1.3), (0, 0, 1.75), M['powder'], r, bevel=.02)
    box('Face', (.01, 1.76, 1.16), (.081, 0, 1.82), M['dark'], r, bevel=0)
    box('PBadge', (.012, .55, .55), (.088, -.55, 2.38), M['blue'], r, bevel=0)
    text_mesh('P', 'P', .5, M['labeltext'], r, (.096, -.55, 2.65), (math.pi / 2, 0, math.pi / 2))
    text_mesh('Digits', str(e.get('display', L['summary']['stalls_car'])), .42, M['led_g'], r, (.096, .35, 2.65), (math.pi / 2, 0, math.pi / 2))
    text_mesh('Free', 'FREE', .2, M['led_g'], r, (.096, .35, 2.15), (math.pi / 2, 0, math.pi / 2))
    box('Arrow', (.012, .5, .08), (.088, -.55, 1.98), M['led_g'], r, bevel=0)

def build_loop(e, r):
    """Inductive loop: thin saw-cut groove filled with black sealant + a glossy tar overband,
    45-degree corner cuts and a lead-in cut running to the nearest equipment island."""
    w, l = e.get('width', 2.0), e.get('length', 1.0)
    pts = [(-l / 2, -w / 2), (l / 2, -w / 2), (l / 2, w / 2), (-l / 2, w / 2)]
    segs = []
    for i in range(4):
        a, b_ = Vector(pts[i]), Vector(pts[(i + 1) % 4]); d = (b_ - a).normalized()
        segs.append((a + d * .12, b_ - d * .12))
        nxt = Vector(pts[(i + 2) % 4]) - b_
        segs.append((b_ - d * .12, b_ + nxt.normalized() * .12))          # chamfered corner
    # lead-in toward the barrier / equipment of the same gate
    tgt = next((x for x in L['equipment'] if x.get('gate') == e.get('gate') and x.get('lane') == e.get('lane') and x['type'] in ('barrier_gate', 'ticket_dispenser', 'card_reader')), None)
    if tgt:
        h = math.radians(e.get('heading', 0)); dv = Vector(tgt['pos']) - Vector(e['pos'])
        loc = Vector((dv.x * math.cos(-h) - dv.y * math.sin(-h), dv.x * math.sin(-h) + dv.y * math.cos(-h)))
        side = 1 if loc.y > 0 else -1
        start = Vector((-l / 2 + .12, side * w / 2))
        end = Vector((start.x, loc.y - side * .75))
        if (end - start).length > .1: segs.append((start, end))
    over = [seg_quad(tuple(a), tuple(b_), .045) for a, b_ in segs]
    groove = [seg_quad(tuple(a), tuple(b_), .012) for a, b_ in segs]
    o = quads_obj('LoopSealant', [q for q in over if q], .0035, M['loop_seal'], 'Equipment'); o.parent = r
    o = quads_obj('LoopGroove', [q for q in groove if q], .0045, M['loop'], 'Equipment'); o.parent = r
def build_intercom(e, r):
    box('BasePlate', (.18, .18, .02), (0, 0, 0), M['steel'], r)
    box('Post', (.09, .09, 1.02), (0, 0, .02), M['powder'], r, bevel=.01)
    box('Box', (.11, .22, .3), (.03, 0, 1.0), M['steel'], r, bevel=.015)
    box('Grille', (.006, .14, .1), (.087, 0, 1.17), M['vent'], r, bevel=0)
    box('Button', (.02, .06, .06), (.09, 0, 1.06), M['led_g'], r, bevel=.008)
    box('Camera', (.01, .03, .03), (.087, 0, 1.25), M['glass'], r, bevel=0)

def build_booth(e, r):
    sx, sy = e.get('size', [1.6, 1.6]); hx, hy = sx / 2, sy / 2
    box('Floor', (sx + .2, sy + .2, .12), (0, 0, 0), M['concrete'], r, bevel=.02)
    box('Body', (sx, sy, .95), (0, 0, .12), M['white'], r, bevel=.02)
    box('Window', (sx - .02, sy - .02, 1.15), (0, 0, 1.07), M['glass'], r, bevel=0)
    for xx in (-hx + .03, hx - .03):
        for yy in (-hy + .03, hy - .03):
            box('Mullion', (.06, .06, 1.15), (xx, yy, 1.07), M['powder'], r, bevel=0)
    for yy in [(-hy + k * sy / max(1, round(sy / 1.1))) for k in range(1, max(1, round(sy / 1.1)))]:
        for xx in (-hx + .03, hx - .03):
            box('MullionMid', (.05, .05, 1.15), (xx, yy, 1.07), M['powder'], r, bevel=0)
    box('Header', (sx + .02, sy + .02, .1), (0, 0, 2.22), M['white'], r)
    box('Roof', (sx + .5, sy + .5, .16), (0, 0, 2.32), M['navy'], r, bevel=.02)
    box('Door', (sx - .5, .02, 1.95), (0, -hy - .005, .12), M['powder'], r, bevel=0)
    box('AC', (.6, .25, .4), (0, hy + .13, 1.5), M['white'], r, bevel=.02)
    for xx in (-hx - .005, hx + .005):
        box('Counter', (.04, sy * .7, .04), (xx, 0, 1.05), M['steel'], r)
    box('Lamp', (.3, .3, .03), (0, 0, 2.31), M['lamp'], r)

def build_ev(e, r):
    box('Base', (.5, .42, .1), (0, 0, 0), M['concrete'], r, bevel=.02)
    box('Body', (.22, .34, 1.42), (0, 0, .1), M['white'], r, bevel=.04)
    box('Face', (.01, .26, .5), (.112, 0, .85), M['dark'], r, bevel=0)
    box('Screen', (.006, .14, .1), (.118, 0, 1.18), M['screen'], r, bevel=0)
    box('Strip', (.008, .04, .7), (.112, -.12, .35), M['led_g'], r, bevel=0)
    box('Holster', (.1, .1, .16), (.14, .08, .95), M['powder'], r, bevel=.02)
    cyl('Cable', .02, .7, (.2, .08, .3), M['black'], r, seg=8)
    box('Bollard', (.14, .14, .7), (.5, -.25, 0), M['yellowcab'], r, bevel=.03)

def build_light(e, r):
    box('Base', (.5, .5, .55), (0, 0, 0), M['concrete'], r, bevel=.03)
    box('BasePlate', (.32, .32, .02), (0, 0, .55), M['steel'], r)
    cyl('Pole', .09, 8.0, (0, 0, .57), M['steel'], r, r2=.055)
    for s_ in (1, -1):
        box(f'Arm{s_}', (1.1, .05, .05), (s_ * .55, 0, 8.45), M['steel'], r, rot=(0, -s_ * math.radians(8), 0))
        box(f'Head{s_}', (.7, .3, .1), (s_ * 1.15, 0, 8.5), M['powder'], r, bevel=.03)
        box(f'Lens{s_}', (.58, .22, .01), (s_ * 1.15, 0, 8.495), M['lamp'], r, bevel=0)

def build_sign(e, r):
    cyl('Post', .035, 2.45, (0, 0, 0), M['steel'], r, seg=10)
    box('Panel', (.03, .8, .55), (.04, 0, 1.82), M['red'], r, bevel=.01)
    box('Border', (.01, .74, .49), (.056, 0, 1.85), M['white'], r, bevel=0)
    box('Inner', (.01, .68, .43), (.061, 0, 1.88), M['red'], r, bevel=0)
    for z_ in (1.9, 2.25):
        box('Clamp', (.06, .09, .04), (.02, 0, z_), M['steel'], r)
    text_mesh('SignText', e.get('text', 'STOP'), .2, M['labeltext'], r, (.068, 0, 2.095), (math.pi / 2, 0, math.pi / 2))

def build_bump(e, r):
    Lb = e.get('length', 6.0); n = max(2, int(Lb / .5))
    for i in range(n):
        box(f'Seg{i}', (.35, Lb / n - .01, .055), (0, -Lb / 2 + (i + .5) * Lb / n, 0), M['yellowcab'] if i % 2 else M['black'], r, bevel=.02)
        for xx in (-.12, .12):
            box(f'Cat{i}{xx}', (.04, .06, .015), (xx, -Lb / 2 + (i + .5) * Lb / n, .055), M['reflect'] if i % 2 == 0 else M['white'], r, bevel=0)
BUILDERS = dict(barrier_gate=build_barrier, ticket_dispenser=build_ticket, card_reader=build_card_reader,
                pay_station=build_pay, lpr_camera=build_lpr, cctv=build_cctv, vacancy_sign=build_vacancy,
                loop_detector=build_loop, intercom=build_intercom, guard_booth=build_booth, ev_charger=build_ev,
                light_pole=build_light, sign=build_sign, speed_bump=build_bump, traffic_cone=build_cone, radar_sensor=build_radar)
# hardware library: extra models per type + new device types (hardware.py); 'model' on an equipment picks the variant
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hardware as HW
HW.install(globals())
ARM_STYLES = HW.ARM_STYLES
BUILDERS = HW.dispatch(BUILDERS)
ROOTS = {}
for e in L['equipment']:
    r = equip_root(e); BUILDERS[e['type']](e, r); ROOTS[e['id']] = r
    if e.get('model'): r['model'] = str(e['model'])

# ------------------------------------------------------------------ labels (render only, not exported)
LABELS = []   # (root, meta)
def label(text, pos, z, color_mat, meta=None):
    root = bpy.data.objects.new(f'Label_{text}', None); link(root, 'Labels')
    root.location = (pos[0], pos[1], z); root['meta'] = json.dumps(meta or {})
    t = text_mesh(f'LabelText_{text}', text, .8, M['labeltext'], root, (0, 0, .02), c='Labels')
    bpy.context.view_layer.update()
    w = t.dimensions.x + .5; h = t.dimensions.y + .35
    p = box(f'LabelPlate_{text}', (w, h, .02), (0, 0, -.01), color_mat, root, c='Labels')
    con = root.constraints.new('TRACK_TO'); con.track_axis = 'TRACK_Z'; con.up_axis = 'UP_Y'
    LABELS.append(root); return root
EQCOL = {k: mat(f'Tag_{k}', tuple(c / 255 for c in v['color']), .5) for k, v in L['equip_catalogue'].items()}
TOP_H = dict(cctv=5.2, light_pole=9.0, vacancy_sign=3.3, guard_booth=3.0, pay_station=2.5, barrier_gate=1.6,
             ticket_dispenser=2.0, card_reader=1.7, lpr_camera=2.1, intercom=1.6, loop_detector=.7, speed_bump=.7,
             sign=2.9, ev_charger=2.0)
MINOR = {'loop_detector', 'intercom', 'light_pole', 'speed_bump', 'ev_charger'}
stack = {}
for e in L['equipment']:
    if e.get('auto'): continue
    k = e.get('gate', '-'); n = stack[k] = stack.get(k, -1) + 1
    z = ground_z(e['pos']) + TOP_H.get(e['type'], 2.2) + (n % 3) * .85 * (1 if e.get('gate') else 0)
    bad = e.get('status', 'ok') != 'ok'
    label(e['id'] + (' FAULT' if bad else ''), e['pos'], z + (.4 if bad else 0), mat('Tag_fault', (.85, .05, .03), .5, emit=(1, .05, .03), estr=.6) if bad else EQCOL[e['type']],
          dict(gate=e.get('gate'), type=e['type'], minor=e['type'] in MINOR and not bad))
for g in L['gates']:
    gm = mat(f"Gate_{g['type']}", (.05, .5, .15) if g['type'] == 'entry' else (.7, .1, .05) if g['type'] == 'exit' else (.8, .45, .05), .5)
    label(f"{g['id']} {'IN' if g['type'] == 'entry' else 'OUT' if g['type'] == 'exit' else 'IN/OUT'}", g['pos'], 4.2, gm,
          dict(gate=g['id'], is_gate=True))

# ------------------------------------------------------------------ world, sun, render setup
sc.world = bpy.data.worlds.new('Sky'); sc.world.use_nodes = True
nt = sc.world.node_tree
bg = nt.nodes.get('Background') or nt.nodes.new('ShaderNodeBackground')
out = next((n for n in nt.nodes if n.type == 'OUTPUT_WORLD'), None) or nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
SUN_EL, SUN_AZ = math.radians(52), math.radians(215)
HDR = os.path.join(ASSETS, MANIFEST['hdri']) if MANIFEST and MANIFEST.get('hdri') else None
if HDR and os.path.exists(HDR):
    # HDRI sky: find its sun, rotate the map so the sun sits at SUN_AZ, and match the sun lamp to it
    import numpy as np
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDR, check_existing=True)
    im = env.image; w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    lum = px[..., 0] * .3 + px[..., 1] * .59 + px[..., 2] * .11
    row, col = np.unravel_index(int(np.argmax(lum)), lum.shape)
    phi = (col / w - .5) * math.tau; el = (row / h - .5) * math.pi        # Blender equirect: u = atan2(dy,-dx)/2pi + .5
    dx, dy = -math.cos(el) * math.cos(phi), math.cos(el) * math.sin(phi)
    az0 = math.atan2(dy, dx)
    SUN_EL = max(math.radians(25), el)
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, az0 - SUN_AZ)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = .9
    print('HDRI', os.path.basename(HDR), 'sun el', round(math.degrees(el), 1), 'az', round(math.degrees(az0), 1))
else:
    sky = nt.nodes.new('ShaderNodeTexSky')
    types = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for pref in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE', 'PREETHAM'):
        if pref in types: sky.sky_type = pref; break
    for attr, val in (('sun_elevation', SUN_EL), ('sun_rotation', SUN_AZ), ('altitude', 0.), ('air_density', 1.), ('dust_density', 1.5), ('sun_disc', False)):
        if hasattr(sky, attr):
            try: setattr(sky, attr, val)
            except Exception: pass
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = .25 if sky.sky_type in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING') else 1.0
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); link(sun, 'Lights')
sun.data.energy = 3.0; sun.data.angle = math.radians(1.5); sun.data.color = (1, .97, .92)
sun.rotation_euler = (math.pi / 2 - SUN_EL, 0, SUN_AZ - math.pi / 2)

sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
prefs = bpy.context.preferences.addons['cycles'].preferences
for dt in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'METAL'):
    try:
        prefs.compute_device_type = dt; prefs.get_devices()
        if [d for d in prefs.devices if d.type == dt]:
            for d in prefs.devices: d.use = d.type == dt
            break
    except Exception: pass
sc.cycles.device = 'GPU'
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.image_settings.file_format = 'PNG'
try: sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass

# ------------------------------------------------------------------ cameras
def camera(name, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 2000
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    c = bpy.data.objects.new(name, cd); link(c, 'Cameras'); c.location = loc
    d = Vector(target) - Vector(loc)
    c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return c
W_, H_ = X1 - X0, Y1 - Y0; diag = math.hypot(W_, H_)
cams = {}
cams['overview'] = camera('CamOverview', (CX + diag * .42, CY - diag * .62, diag * .46), (CX, CY + H_ * .04, 0), 32)
cams['top'] = camera('CamTop', (CX, CY, 300), (CX, CY, 0), ortho=max(W_, H_ * RES[0] / RES[1]) * 1.04)
cams['top'].rotation_euler = (0, 0, 0)
for g in L['gates']:
    h = math.radians(g.get('heading', 90)); d = Vector((math.cos(h), math.sin(h), 0))
    side = Vector((-d.y, d.x, 0))
    p = Vector((g['pos'][0], g['pos'][1], 0))
    cams[f"gate_{g['id']}"] = camera(f"CamGate_{g['id']}", tuple(p - d * 13 - side * 7 + Vector((0, 0, 7))), tuple(p + d * 1.5), 30)
# close-ups of the first device of each key type (shows the hardware detail)
for typ in ('ticket_dispenser', 'lpr_camera', 'barrier_gate', 'card_reader', 'pay_station'):
    e = next((x for x in L['equipment'] if x['type'] == typ.replace('_ptz', '') and x.get('status', 'ok') == 'ok' and (x.get('model') == 'ptz') == typ.endswith('_ptz')), None)
    if not e: continue
    h = math.radians(e.get('heading', 0)); f_ = Vector((math.cos(h), math.sin(h), 0)); s_ = Vector((-f_.y, f_.x, 0))
    p = Vector((e['pos'][0], e['pos'][1], ground_z(e['pos'])))
    dist = {'barrier_gate': 4.2, 'pay_station': 2.4}.get(typ, 2.0)
    look = p + Vector((0, 0, {'barrier_gate': .8, 'pay_station': 1.05}.get(typ, 1.0))) + (f_ * 1.2 if typ == 'barrier_gate' else Vector())
    cpos = p + f_ * dist + s_ * dist * .55 + Vector((0, 0, 1.55))
    if typ.startswith('cctv'):
        look = p + Vector((0, 0, 4.2)) + f_ * .4; cpos = p + f_ * 2.2 + s_ * 1.6 + Vector((0, 0, 3.9))
    cams[f"closeup_{e['id']}"] = camera(f"CamClose_{e['id']}", tuple(cpos), tuple(look), 35)
CLOSE_IDS = set(argv[argv.index('--closeup') + 1].split(',')) if '--closeup' in argv else None
if '--closeup-all' in argv or CLOSE_IDS:          # framed close-ups (all devices, or --closeup ID,ID)
    bpy.context.view_layer.update()
    for e in L['equipment']:
        r = ROOTS.get(e['id'])
        if r is None or e.get('auto') or (CLOSE_IDS and e['id'] not in CLOSE_IDS): continue
        pts = [o.matrix_world @ Vector(cn) for o in [r] + list(r.children_recursive) if o.type == 'MESH' and not o.hide_render for cn in o.bound_box]
        if e['type'] == 'cctv': pts = [p for p in pts if p.z > 3.6] or pts          # frame the camera head, not the whole pole
        if not pts: continue
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
        cen = (lo + hi) / 2; size = max((hi - lo).length, .8)
        h = math.radians(e.get('heading', 0)); f_ = Vector((math.cos(h), math.sin(h), 0)); s_ = Vector((-f_.y, f_.x, 0))
        if e['type'] == 'barrier_gate':
            th_ = math.radians(e.get('traffic', e.get('heading', 0) + 90)); f_ = -Vector((math.cos(th_), math.sin(th_), 0)); s_ = Vector((-f_.y, f_.x, 0))
        d_ = size * 1.05 + 1.0
        if e['type'] == 'lpr_camera':      # close 3/4 view from the lane side so the whole unit fills the frame
            base = Vector((e['pos'][0], e['pos'][1], 0))
            top = hi.z                                          # camera / sign height of this model
            distance = 1.2 + top * 1.1
            cams[f"closeup_{e['id']}"] = camera(f"CamClose_{e['id']}", tuple(base + f_ * distance + s_ * distance * .45 + Vector((0, 0, top * .85))), tuple(base + Vector((0, 0, top * .55))), 35)
            continue
        cams[f"closeup_{e['id']}"] = camera(f"CamClose_{e['id']}", tuple(cen + f_ * d_ + s_ * d_ * .45 + Vector((0, 0, size * .35 + .4))), tuple(cen), 35)
if '--closeup-all' in argv:          # buildings: 3/4 view from the front-left
    bpy.context.view_layer.update()
    for b in L['buildings']:
        o = bpy.data.objects.get(f"BLD_{b.get('id', '')}")
        if not o: continue
        pts = [o.matrix_world @ Vector(cn) for cn in o.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
        cen = (lo + hi) / 2; size = (hi - lo).length
        fwd = o.matrix_world.to_3x3() @ Vector((0, -1, 0)); side = o.matrix_world.to_3x3() @ Vector((-1, 0, 0))
        cams[f"closeup_{b['id']}"] = camera(f"CamB_{b['id']}", tuple(cen + fwd * size * .9 + side * size * .55 + Vector((0, 0, size * .12))), tuple(cen - Vector((0, 0, (hi.z - lo.z) * .08))), 35)
ent = next((g for g in L['gates'] if g['type'] in ('entry', 'both')), None)
if ent:
    h = math.radians(ent.get('heading', 90)); d = Vector((math.cos(h), math.sin(h), 0)); side = Vector((-d.y, d.x, 0))
    p = Vector((ent['pos'][0], ent['pos'][1], 0))
    cams['entrance'] = camera('CamEntrance', tuple(p - d * 22 - side * 3 + Vector((0, 0, 1.6))), tuple(p + d * 10 + Vector((0, 0, 1.2))), 26)

# ------------------------------------------------------------------ save + export
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'site.blend'))
# ------------------------------------------------------------------ renders
if RENDER:
    rd = os.path.join(OUT, 'render'); os.makedirs(rd, exist_ok=True)
    def shot(key, fname, labels):
        cam = cams[key]; sc.camera = cam
        solo = f"BLD_{key[8:]}" if key.startswith('closeup_') and bpy.data.objects.get(f"BLD_{key[8:]}") else None
        for o_ in bpy.data.objects:          # building close-ups show only that building (no neighbours in frame)
            if o_.name.startswith('BLD_'): o_.hide_render = bool(solo) and o_.name != solo
        for lab in LABELS:
            m = json.loads(lab['meta']); show = labels; s = 1.0
            if key.startswith('gate_'):
                show = labels and m.get('gate') == key[5:]; s = 1.0 if m.get('is_gate') else .5
            elif key == 'top':
                s = 2.4 if m.get('is_gate') else 1.5
            else:
                show = labels and not m.get('minor'); s = 2.4 if m.get('is_gate') else 1.5
            lab.scale = (s, s, s)
            lab.hide_render = not show
            for ch in lab.children: ch.hide_render = not show
            con = lab.constraints[0]
            if key == 'top':
                con.mute = True; lab.rotation_euler = (0, 0, 0)
            else:
                con.mute = False; con.target = cam
        sc.render.filepath = os.path.join(rd, fname)
        bpy.ops.render.render(write_still=True); print('RENDERED', fname, flush=True)
    shot('overview', 'overview.png', False)
    shot('overview', 'overview_labels.png', True)
    shot('top', 'top.png', False)
    shot('top', 'top_labels.png', True)
    for k in cams:
        if k.startswith('gate_'): shot(k, f'{k}.png', True)
    if 'entrance' in cams: shot('entrance', 'entrance.png', False)
    for k in cams:
        if k.startswith('closeup_'): shot(k, f'{k}.png', False)
# glTF cannot carry procedural noise: drop those links so the exporter uses each material's flat colour
for m_ in list(bpy.data.materials):
    if not m_.node_tree: continue
    if m_.name.startswith('Art_'): continue          # printed artwork (hardware.decal): image texture + alpha must reach the .glb
    nt_ = m_.node_tree; b_ = nt_.nodes.get('Principled BSDF')
    if not b_: continue
    for inp in ('Base Color', 'Normal', 'Roughness', 'Alpha'):
        for l_ in list(b_.inputs[inp].links): nt_.links.remove(l_)
    diff = next((n for n in nt_.nodes if n.type == 'TEX_IMAGE' and n.label == 'DIFF'), None)
    if diff: nt_.links.new(diff.outputs['Color'], b_.inputs['Base Color'])   # keep the albedo texture (UV + Mapping -> KHR_texture_transform)
WEB_TEX = opt('--web-tex', 512)
for im in IMGS.values():
    if im.size[0] > WEB_TEX: im.scale(WEB_TEX, WEB_TEX)
# lighter foliage in the .glb only: Decimate shows in the viewport evaluation (used by the exporter), not in renders
for o in coll('Trees').objects:
    if o.type == 'MESH' and o.name.startswith(('TreeCanopy_', 'Shrubs_')):
        dm = o.modifiers.new('WebDecimate', 'DECIMATE'); dm.ratio = .18 if o.name.startswith('TreeCanopy_') else .3; dm.show_render = False
CARLIB.web_swap(coll('Cars'))
bpy.ops.object.select_all(action='DESELECT')
for cname in ('Site', 'Trees', 'Cars', 'Equipment', 'Cables'):
    if cname in COL:
        for o in COL[cname].all_objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'site.glb'), export_format='GLB', use_selection=True,
                          export_extras=True, export_apply=True, export_yup=True, export_cameras=False, export_lights=False,
                          export_image_format='AUTO')     # AUTO: JPEG textures stay JPEG, transparent PNG artwork stays PNG
print('EXPORT_OK', os.path.getsize(os.path.join(OUT, 'site.glb')), 'bytes,', len(L['equipment']), 'equipment,', ncar, 'cars')

print('BUILD_OK')
