# parking-site-3d: building library (Blender). Realistic low/mid-rise blocks, 4-10 floors typical.
# Each building = ONE mesh with material slots (light for the web), built in a local frame on a rectangular
# footprint: X along the long side, Y across, front face = -Y (or the side facing 'front_heading').
# Styles (catalogue in hardware_catalog.BUILDING_MODELS): office_glass, office_concrete, condo, mixed_podium,
# government, parking.
import math
from mathutils import Vector, Matrix

SLOTS = ['wall', 'glass', 'frame', 'slab', 'roof', 'accent', 'dark', 'stone', 'rail', 'sign', 'clear', 'lit', 'blue']

def install(g):
    globals().update({k: v for k, v in g.items() if not k.startswith('__')})
    def m(name, col, rough, metal=0., **kw): return mat(name, col, rough, metal, **kw)
    global BM
    BM = dict(
        office_glass=dict(wall=m('BG_Core', (.25, .27, .3), .5), glass=m('BG_CurtainGlass', (.06, .14, .18), .04, .6),
                          frame=m('BG_Alu', (.72, .74, .76), .3, .7), slab=m('BG_SlabEdge', (.82, .83, .84), .4),
                          accent=m('BG_Accent', (.12, .3, .55), .35)),
        office_concrete=dict(wall=m('BG_PaintBeige', (.78, .74, .66), .75), glass=m('BG_WinGlass', (.08, .12, .15), .05, .4),
                             frame=m('BG_WinFrame', (.2, .21, .22), .4, .4), slab=m('BG_Band', (.62, .6, .55), .7),
                             accent=m('BG_Fin', (.9, .9, .88), .6)),
        condo=dict(wall=m('BG_CondoWhite', (.88, .87, .84), .7), glass=m('BG_CondoGlass', (.1, .16, .2), .05, .4),
                   frame=m('BG_CondoFrame', (.3, .3, .3), .4, .5), slab=m('BG_BalconySlab', (.8, .79, .76), .6),
                   accent=m('BG_CondoAccent', (.55, .42, .32), .6)),
        mixed_podium=dict(wall=m('BG_PodiumStone', (.68, .64, .58), .6), glass=m('BG_TowerGlass', (.1, .17, .2), .04, .55),
                          frame=m('BG_TowerFrame', (.18, .19, .2), .35, .5), slab=m('BG_TowerSlab', (.85, .85, .84), .5),
                          accent=m('BG_Awning', (.55, .1, .08), .5)),
        government=dict(wall=m('BG_GovWhite', (.86, .85, .8), .6), glass=m('BG_GovGlass', (.1, .15, .18), .05, .45),
                        frame=m('BG_GovFrame', (.55, .56, .58), .4, .5), slab=m('BG_GovBand', (.76, .74, .68), .6),
                        accent=m('BG_GovFin', (.9, .89, .85), .55)),
        parking=dict(wall=m('BG_ParkConcrete', (.7, .7, .68), .8), glass=m('BG_ParkDark', (.05, .05, .055), .7),
                     frame=m('BG_ParkRail', (.72, .73, .75), .35, .8), slab=m('BG_ParkSlab', (.6, .6, .58), .8),
                     accent=m('BG_ParkStripe', (.95, .65, .05), .5)),
    )
    common = dict(roof=m('BG_Roof', (.4, .41, .42), .85), dark=m('BG_Dark', (.06, .06, .07), .5, .3),
                  stone=m('BG_BaseStone', (.42, .4, .37), .7), rail=m('BG_RailGlass', (.6, .72, .75), .05, alpha=.4),
                  sign=m('BG_SignLit', (.9, .92, .95), .3, emit=(1, 1, 1), estr=1.5), clear=m('BG_LobbyGlass', (.5, .6, .62), .03, .2),
                  lit=m('BG_LobbyLight', (.95, .9, .8), .4, emit=(1, .92, .8), estr=1.2),
                  blue=m('BG_SignBlue', (.02, .18, .55), .4))
    for s in BM.values(): s.update(common)

class MB:
    """mesh accumulator: boxes / quads with a material slot, local coordinates."""
    def __init__(s): s.v, s.f, s.mi = [], [], []
    def box(s, x0, x1, y0, y1, z0, z1, slot):
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4: return
        b = len(s.v)
        s.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            s.f.append(tuple(b + i for i in q)); s.mi.append(SLOTS.index(slot))
    def cyl(s, x, y, z0, z1, r, slot, n=12):
        b = len(s.v)
        for z in (z0, z1):
            for k in range(n): s.v.append((x + r * math.cos(k / n * math.tau), y + r * math.sin(k / n * math.tau), z))
        for k in range(n):
            s.f.append((b + k, b + (k + 1) % n, b + n + (k + 1) % n, b + n + k)); s.mi.append(SLOTS.index(slot))
        s.f.append(tuple(b + n + k for k in range(n))); s.mi.append(SLOTS.index(slot))

# ------------------------------------------------------------------ facade helpers (a face = one side of the rectangle)
def faces(L_, D_):
    """four facades: (name, along-axis, fixed coordinate, outward sign, length). 'x' faces run along X at y = +-D/2."""
    return [('front', 'x', -D_ / 2, -1, L_), ('back', 'x', D_ / 2, 1, L_), ('left', 'y', -L_ / 2, -1, D_), ('right', 'y', L_ / 2, 1, D_)]

def fbox(mb, axis, fixed, out, a0, a1, d0, d1, z0, z1, slot):
    """box on a facade: a0..a1 along the face, d0..d1 outward from the face plane (negative = inside), z0..z1."""
    if axis == 'x':
        y0, y1 = sorted((fixed + out * d0, fixed + out * d1)); mb.box(a0, a1, y0, y1, z0, z1, slot)
    else:
        x0, x1 = sorted((fixed + out * d0, fixed + out * d1)); mb.box(x0, x1, a0, a1, z0, z1, slot)

def bays(length, target):
    n = max(1, round(length / target)); w = length / n
    return [(-length / 2 + i * w, -length / 2 + (i + 1) * w) for i in range(n)]

def rooftop(mb, L_, D_, H, rnd, style):
    """parapet, lift overrun, AC condensers, water tank, antenna."""
    p = .9 if style != 'parking' else 1.1
    for name, axis, fixed, out, ln in faces(L_, D_):
        fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.2, .05, H, H + p, 'slab' if style in ('office_glass', 'mixed_podium') else 'wall')
    mb.box(-L_ / 2 + .2, L_ / 2 - .2, -D_ / 2 + .2, D_ / 2 - .2, H - .02, H + .02, 'roof')
    if style == 'parking': return
    cx = rnd.uniform(-L_ * .2, L_ * .2)
    mb.box(cx - 2.5, cx + 2.5, -1.8, 1.8, H, H + 3.2, 'wall')                       # lift / stair overrun
    mb.box(cx - 2.6, cx + 2.6, -1.9, 1.9, H + 3.2, H + 3.4, 'slab')
    for i in range(int(min(L_ * .5, 14) / 1.4)):                                    # rows of AC condensers
        x = -L_ / 2 + 2 + i * 1.4
        if abs(x - cx) < 3.2: continue
        mb.box(x, x + 1.0, D_ / 2 - 4, D_ / 2 - 3.2, H, H + .9, 'frame')
        mb.box(x + .1, x + .9, D_ / 2 - 4.02, D_ / 2 - 3.98, H + .15, H + .8, 'dark')
    mb.cyl(L_ / 2 - 4, -D_ / 2 + 4, H, H + 2.2, 1.0, 'frame', 14)                 # water tank
    mb.cyl(cx + 1.8, 1.2, H + 3.4, H + 7.5, .05, 'frame', 6)                        # antenna mast

def entrance(mb, L_, D_, z_top, style):
    """front entrance: canopy, lit lobby glass, steps."""
    w = min(10, L_ * .3)
    mb.box(-w / 2, w / 2, -D_ / 2 - 3.2, -D_ / 2, z_top - .35, z_top - .1, 'slab' if style != 'government' else 'accent')
    for x in (-w / 2 + .3, w / 2 - .3): mb.box(x - .15, x + .15, -D_ / 2 - 3.0, -D_ / 2 - 2.7, 0, z_top - .35, 'frame')
    mb.box(-w / 2 + .5, w / 2 - .5, -D_ / 2 - .06, -D_ / 2 + .02, .15, z_top - .5, 'clear')
    mb.box(-w / 2 + .6, w / 2 - .6, -D_ / 2 + .1, -D_ / 2 + .2, z_top - 1.2, z_top - .9, 'lit')
    for k in range(3): mb.box(-w / 2, w / 2, -D_ / 2 - 3.2 + k * .35, -D_ / 2, 0, .15 * (3 - k) / 3 + .02, 'stone')

# ------------------------------------------------------------------ styles
def office_glass(mb, L_, D_, F, rnd):
    h0, h = 4.5, 3.6; H = h0 + (F - 1) * h
    mb.box(-L_ / 2 + .3, L_ / 2 - .3, -D_ / 2 + .3, D_ / 2 - .3, 0, H, 'glass')            # curtain-wall volume
    for name, axis, fixed, out, ln in faces(L_, D_):
        fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.35, .05, 0, .6, 'stone')             # plinth
        for k in range(F):                                                                 # slab-edge / spandrel bands
            z = h0 + (k - 1) * h if k else 0
            zt = z + (h0 if k == 0 else h)
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.3, .02, zt - .45, zt, 'slab')
        for a0, a1 in bays(ln, 1.5):                                                       # mullions
            fbox(mb, axis, fixed, out, a0 - .03, a0 + .03, -.3, .1, .6, H, 'frame')
        fbox(mb, axis, fixed, out, -ln / 2, -ln / 2 + .25, -.3, .12, 0, H, 'frame')
        fbox(mb, axis, fixed, out, ln / 2 - .25, ln / 2, -.3, .12, 0, H, 'frame')
    # vertical accent fin pair on the front corner + logo band
    fbox(mb, 'x', -D_ / 2, -1, L_ / 2 - 3.2, L_ / 2 - 2.6, 0, .6, 0, H + 1.5, 'accent')
    mb.box(-L_ / 4, L_ / 4, -D_ / 2 - .08, -D_ / 2 + .02, H - .3, H + .7, 'sign')
    return H

def office_concrete(mb, L_, D_, F, rnd):
    h0, h = 4.2, 3.5; H = h0 + (F - 1) * h
    mb.box(-L_ / 2, L_ / 2, -D_ / 2, D_ / 2, 0, H, 'wall')
    for name, axis, fixed, out, ln in faces(L_, D_):
        fbox(mb, axis, fixed, out, -ln / 2, ln / 2, 0, .06, 0, 1.0, 'stone')
        for k in range(F):
            z = 0 if k == 0 else h0 + (k - 1) * h; fh = h0 if k == 0 else h
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, 0, .08, z + fh - .3, z + fh, 'slab')      # floor band
            if k == 0 and name == 'front': continue
            for a0, a1 in bays(ln, 3.0):                                                        # punched windows
                c = (a0 + a1) / 2; ww, wh = 1.9, 1.7; zb = z + (1.1 if k else 1.4)
                fbox(mb, axis, fixed, out, c - ww / 2 - .08, c + ww / 2 + .08, -.01, .05, zb - .08, zb + wh + .08, 'frame')
                fbox(mb, axis, fixed, out, c - ww / 2, c + ww / 2, .0, .055, zb, zb + wh, 'glass')
                fbox(mb, axis, fixed, out, c - .025, c + .025, .0, .07, zb, zb + wh, 'frame')
                fbox(mb, axis, fixed, out, c - ww / 2 - .2, c + ww / 2 + .2, 0, .55, zb + wh + .15, zb + wh + .23, 'accent')  # sun shade
    # ground floor shop/lobby glazing on the front
    fbox(mb, 'x', -D_ / 2, -1, -L_ / 2 + 1, L_ / 2 - 1, .0, .05, .5, h0 - .5, 'clear')
    for a0, a1 in bays(L_ - 2, 2.5): fbox(mb, 'x', -D_ / 2, -1, a0 - .04, a0 + .04, 0, .09, .5, h0 - .5, 'frame')
    return H

def condo(mb, L_, D_, F, rnd):
    h0, h = 4.0, 3.0; H = h0 + (F - 1) * h
    mb.box(-L_ / 2, L_ / 2, -D_ / 2, D_ / 2, 0, H, 'wall')
    for name, axis, fixed, out, ln in faces(L_, D_):
        fbox(mb, axis, fixed, out, -ln / 2, ln / 2, 0, .05, 0, h0, 'stone')
        long_side = name in ('front', 'back')
        for k in range(1, F):
            z = h0 + (k - 1) * h
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, 0, .05, z - .12, z + .05, 'slab')
            for i, (a0, a1) in enumerate(bays(ln, 4.2 if long_side else 3.0)):
                c = (a0 + a1) / 2
                if long_side:                                                               # balcony unit
                    fbox(mb, axis, fixed, out, a0 + .25, a1 - .25, .0, 1.4, z, z + .14, 'slab')
                    fbox(mb, axis, fixed, out, a0 + .25, a1 - .25, 1.36, 1.42, z + .14, z + 1.15, 'rail')
                    fbox(mb, axis, fixed, out, a0 + .25, a1 - .25, 1.36, 1.44, z + 1.1, z + 1.16, 'frame')
                    fbox(mb, axis, fixed, out, c - 1.3, c + 1.3, .0, .04, z + .14, z + 2.5, 'glass')   # sliding door
                    fbox(mb, axis, fixed, out, c - .03, c + .03, .0, .06, z + .14, z + 2.5, 'frame')
                    fbox(mb, axis, fixed, out, a1 - .95, a1 - .4, .3, .62, z + .14, z + .7, 'frame')  # AC condenser
                    if i % 2: fbox(mb, axis, fixed, out, a1 - .22, a1 - .05, 0, 1.4, z, z + h, 'accent')  # party-wall fin
                else:
                    fbox(mb, axis, fixed, out, c - .6, c + .6, .0, .05, z + .9, z + 2.2, 'glass')
                    fbox(mb, axis, fixed, out, c - .66, c + .66, .0, .07, z + .85, z + .9, 'frame')
    fbox(mb, 'x', -D_ / 2, -1, -L_ / 2 + 1.5, L_ / 2 - 1.5, 0, .05, .4, h0 - .6, 'clear')
    return H

def mixed_podium(mb, L_, D_, F, rnd):
    hp, h = 4.5, 3.4; P = 2; H = P * hp + (F - P) * h; sb = 2.5
    mb.box(-L_ / 2, L_ / 2, -D_ / 2, D_ / 2, 0, P * hp, 'wall')                               # podium
    for name, axis, fixed, out, ln in faces(L_, D_):
        for k in range(P):
            z = k * hp
            for a0, a1 in bays(ln, 6.0):                                                       # shopfronts / podium glazing
                fbox(mb, axis, fixed, out, a0 + .3, a1 - .3, .0, .05, z + .3, z + hp - .9, 'clear' if k == 0 else 'glass')
                if k == 0 and name == 'front':
                    fbox(mb, axis, fixed, out, a0 + .4, a1 - .4, 0, 1.2, z + hp - .85, z + hp - .7, 'accent')   # awnings
                    fbox(mb, axis, fixed, out, a0 + .8, a1 - .8, .0, .08, z + hp - .65, z + hp - .3, 'sign')
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, 0, .1, z + hp - .25, z + hp, 'slab')
    Lt, Dt = L_ - 2 * sb, D_ - 2 * sb                                                          # set-back tower
    z0 = P * hp
    mb.box(-Lt / 2 + .25, Lt / 2 - .25, -Dt / 2 + .25, Dt / 2 - .25, z0, H, 'glass')
    for name, axis, fixed, out, ln in faces(Lt, Dt):
        for k in range(F - P):
            zt = z0 + (k + 1) * h
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.25, .05, zt - .4, zt, 'slab')
        for j, (a0, a1) in enumerate(bays(ln, 1.2)):
            fbox(mb, axis, fixed, out, a0 - .04, a0 + .04, -.25, .35 if j % 3 == 0 else .08, z0, H, 'frame')   # vertical fins
    mb.box(-L_ / 2 + .3, L_ / 2 - .3, -D_ / 2 + .3, D_ / 2 - .3, z0 - .02, z0 + .05, 'roof')            # podium roof deck
    return H, Lt, Dt

def government(mb, L_, D_, F, rnd):
    h0, h = 4.5, 3.6; H = h0 + (F - 1) * h
    mb.box(-L_ / 2 + .4, L_ / 2 - .4, -D_ / 2 + .4, D_ / 2 - .4, 0, H, 'glass')
    for name, axis, fixed, out, ln in faces(L_, D_):
        fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.4, .1, 0, 1.2, 'stone')                     # stone base
        for k in range(F):
            z = 0 if k == 0 else h0 + (k - 1) * h; fh = h0 if k == 0 else h
            fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.4, .15, z + fh - .5, z + fh, 'slab')
        for j, (a0, a1) in enumerate(bays(ln, .9)):                                              # vertical louvres
            fbox(mb, axis, fixed, out, a0 - .06, a0 + .06, -.4, .45, 1.2, H, 'accent')
        fbox(mb, axis, fixed, out, -ln / 2, -ln / 2 + .8, -.4, .3, 0, H + .9, 'wall')              # corner piers
        fbox(mb, axis, fixed, out, ln / 2 - .8, ln / 2, -.4, .3, 0, H + .9, 'wall')
    # portico: columns + deep canopy on the front
    w = min(16, L_ * .5)
    mb.box(-w / 2, w / 2, -D_ / 2 - 5, -D_ / 2 + .2, h0 + .3, h0 + .9, 'wall')
    for x in [(-w / 2 + .5) + i * (w - 1) / 4 for i in range(5)]:
        mb.cyl(x, -D_ / 2 - 4.5, 0, h0 + .3, .35, 'wall', 16)
    mb.box(-w / 2 + 1, w / 2 - 1, -D_ / 2 - .1, -D_ / 2 + .5, .2, h0, 'clear')
    return H

def parking(mb, L_, D_, F, rnd):
    h = 3.0; H = F * h
    for k in range(F + 1):
        mb.box(-L_ / 2, L_ / 2, -D_ / 2, D_ / 2, k * h - .25, k * h + .02 if k else .02, 'slab')     # floor slabs
    for x in [(-L_ / 2 + .3) + i * (L_ - .6) / max(1, round(L_ / 8)) for i in range(round(L_ / 8) + 1)]:
        for y in (-D_ / 2 + .3, 0, D_ / 2 - .3):
            mb.box(x - .3, x + .3, y - .3, y + .3, 0, H, 'wall')                                     # column grid
    for name, axis, fixed, out, ln in faces(L_, D_):
        for k in range(1, F + 1):
            z = (k - 1) * h
            if k > 1 or name != 'front':
                fbox(mb, axis, fixed, out, -ln / 2, ln / 2, -.15, .05, z + .02, z + 1.1, 'wall')        # spandrel parapet
                fbox(mb, axis, fixed, out, -ln / 2, ln / 2, .05, .07, z + .45, z + .6, 'accent')       # painted stripe
                fbox(mb, axis, fixed, out, -ln / 2, ln / 2, .0, .1, z + 1.1, z + 1.16, 'frame')        # top rail
    y0 = -D_ / 2 - .3                                                                               # big blue P sign
    mb.box(-1.6, 1.6, y0, y0 + .2, H - .6, H + 2.0, 'blue')
    for x0, x1, z0, z1 in ((-.9, -.45, H - .25, H + 1.65), (-.9, .75, H + 1.25, H + 1.65), (-.9, .75, H + .45, H + .85), (.35, .75, H + .45, H + 1.65)):
        mb.box(x0, x1, y0 - .04, y0, z0, z1, 'sign')
    mb.box(-.1, .1, y0 + .2, y0 + .4, H - .6, H + 1.5, 'frame')                                     # bracket to the parapet
    mb.box(-6, 6, -D_ / 2 - .1, -D_ / 2, 0, 2.6, 'dark')                                           # vehicle entry
    return H

STYLES = dict(office_glass=office_glass, office_concrete=office_concrete, condo=condo, mixed_podium=mixed_podium,
              government=government, parking=parking)

def rect_frame(poly):
    """centre, angle, length, depth of a (near-)rectangular footprint; None if it is not a rectangle."""
    if len(poly) != 4: return None
    P = [Vector(p) for p in poly]
    e = [(P[(i + 1) % 4] - P[i]) for i in range(4)]
    if any(abs(e[i].normalized().dot(e[(i + 1) % 4].normalized())) > .05 for i in range(4)): return None
    i0 = 0 if e[0].length >= e[1].length else 1
    ang = math.atan2(e[i0].y, e[i0].x)
    c = sum(P, Vector((0, 0))) / 4
    return c, ang, e[i0].length, e[(i0 + 1) % 4].length

def build(b, rnd):
    """returns the building object (named BLD_<id>) or None when the footprint is not rectangular or no library
    model is named (then the original plain building is built, so sites made before the library look unchanged)."""
    if b.get('model') not in STYLES: return None
    fr = rect_frame(b['polygon'])
    if not fr: return None
    c, ang, L_, D_ = fr
    style = b.get('model', 'office_concrete'); F = int(b.get('floors') or max(1, round(b.get('height', 14) / 3.5)))
    if b.get('front_heading') is not None:                    # turn so the front (-Y) faces the requested direction
        fh = math.radians(b['front_heading'])
        best = min(range(4), key=lambda q: abs(((ang + q * math.pi / 2 - math.pi / 2) - fh + math.pi) % math.tau - math.pi))
        ang += best * math.pi / 2
        if best % 2: L_, D_ = D_, L_
    mb = MB()
    res = STYLES[style](mb, L_, D_, F, rnd)
    if isinstance(res, tuple): H, Lr, Dr = res
    else: H, Lr, Dr = res, L_, D_
    rooftop(mb, Lr, Dr, H, rnd, style)
    if style in ('office_glass', 'office_concrete', 'condo', 'government'):
        entrance(mb, L_, D_, 4.0 if style != 'condo' else 3.6, style)
    me = bpy.data.meshes.new(f"BLD_{b.get('id', '')}")
    me.from_pydata(mb.v, [], mb.f); me.update()
    for s in SLOTS: me.materials.append(BM[style][s])
    me.polygons.foreach_set('material_index', mb.mi)
    o = bpy.data.objects.new(f"BLD_{b.get('id', '')}", me); link(o, 'Site')
    o.location = (c.x, c.y, 0); o.rotation_euler = (0, 0, ang)
    for k, v in (('label', b.get('label', '')), ('model', style), ('floors', F), ('height_m', round(H, 1))):
        o[k] = v
    return o
