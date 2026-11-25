# parking-site-3d: layout engine (pure Python, no Blender).
#   py site_layout.py <site.json> <out_dir>
# Reads the site description, fills parking areas with stalls, resolves equipment,
# and writes: layout.json (everything the Blender builder + viewer need),
# summary.json, summary_th.md, equipment.csv, plan.png (2D check plan).
import json, math, os, random, sys, csv

# ---------------------------------------------------------------- catalogue
EQUIP = {  # type: (Thai name, plan colour, short code)
    'barrier_gate':     ('ไม้กั้นรถ', (230, 120, 20), 'BG'),
    'ticket_dispenser': ('ตู้จ่ายสลิป', (40, 120, 220), 'TD'),
    'card_reader':      ('เครื่องอ่านบัตร', (60, 160, 230), 'CR'),
    'pay_station':      ('ตู้ชำระเงินอัตโนมัติ', (20, 160, 90), 'PS'),
    'lpr_camera':       ('กล้องอ่านป้ายทะเบียน (LPR)', (200, 40, 160), 'LPR'),
    'cctv':             ('กล้องวงจรปิด', (120, 60, 200), 'CAM'),
    'vacancy_sign':     ('ป้ายแสดงช่องจอดว่าง', (240, 60, 60), 'VS'),
    'loop_detector':    ('ลูปตรวจจับรถ', (120, 120, 120), 'LD'),
    'intercom':         ('อินเตอร์คอม', (90, 140, 160), 'IC'),
    'guard_booth':      ('ป้อมยาม', (150, 110, 70), 'GB'),
    'ev_charger':       ('เครื่องชาร์จรถไฟฟ้า (EV)', (30, 190, 120), 'EV'),
    'light_pole':       ('เสาไฟส่องสว่าง', (200, 180, 40), 'LP'),
    'sign':             ('ป้ายจราจร', (220, 50, 50), 'SG'),
    'speed_bump':       ('ลูกระนาด', (230, 200, 30), 'SB'),
    'traffic_cone':     ('กรวยจราจร', (250, 110, 20), 'TC'),
    'radar_sensor':     ('เรดาร์ตรวจจับรถ', (0, 170, 200), 'RD'),
    'height_bar':       ('คานจำกัดความสูง', (240, 170, 0), 'HB'),
    'stall_sensor':     ('เซนเซอร์ช่องจอด', (40, 180, 120), 'SS'),
}
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware_catalog import MODELS as HW_MODELS, default_model, model_th
STATUS_TH = {'ok': 'ใช้งานได้', 'fault': 'เสีย', 'maintenance': 'ซ่อมบำรุง'}
GATE_TH = {'entry': 'ทางเข้า', 'exit': 'ทางออก', 'both': 'ทางเข้า-ออก'}
STALL_TH = {'normal': 'รถยนต์ทั่วไป', 'accessible': 'คนพิการ', 'ev': 'รถไฟฟ้า (EV)', 'motorcycle': 'รถจักรยานยนต์'}

# Thai building-control defaults (กฎกระทรวงฉบับที่ 7/41): stall 2.4 x 5.0 (parallel 2.4 x 6.0)
# aisle 90deg 6.0, 60deg 5.5, 45deg 3.5, 30deg 3.5, parallel 3.0. Always overridable.
AISLE = {90: 6.0, 60: 5.5, 45: 3.5, 30: 3.5, 0: 3.0}
MOTO = dict(stall_w=1.0, stall_l=2.0, aisle=2.0)


# ---------------------------------------------------------------- geometry helpers
def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)

def inside(pt, poly):
    x, y = pt; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

def poly_dist(p, poly):  # distance to polygon edges
    return min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))

def line_dist(p, pts):
    return min(seg_dist(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1))

def area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2

def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def sample_pts(q):  # corners, edge mids, centre of a quad
    pts = list(q)
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]; pts.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    pts.append(centroid(q))
    return pts

def road_band(pts, w):
    """Polygon outline of a polyline with width (mitred joints)."""
    h = w / 2; L, R = [], []
    for i, p in enumerate(pts):
        dirs = []
        if i > 0: dirs.append((p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]))
        if i < len(pts) - 1: dirs.append((pts[i + 1][0] - p[0], pts[i + 1][1] - p[1]))
        ns = []
        for d in dirs:
            l = math.hypot(*d) or 1; ns.append((-d[1] / l, d[0] / l))
        nx, ny = sum(n[0] for n in ns), sum(n[1] for n in ns); l = math.hypot(nx, ny) or 1
        nx, ny = nx / l, ny / l
        k = h / max(0.3, (nx * ns[0][0] + ny * ns[0][1]))
        L.append((p[0] + nx * k, p[1] + ny * k)); R.append((p[0] - nx * k, p[1] - ny * k))
    return L + R[::-1]


# ---------------------------------------------------------------- stall generation
def fill_area(A, blockers, roads):
    """Fill one parking area polygon with stalls. Returns (stalls, aisles)."""
    poly = [tuple(p) for p in A['polygon']]
    moto = A.get('vehicle') == 'motorcycle'
    th = int(A.get('stall_angle', 90))
    W = A.get('stall_w', MOTO['stall_w'] if moto else 2.4)
    Ld = A.get('stall_l', MOTO['stall_l'] if moto else (6.0 if th == 0 else 5.0))
    aisle = A.get('aisle_width', MOTO['aisle'] if moto else AISLE.get(th, 6.0))
    ang = math.radians(A.get('angle_deg', 0))        # aisle direction
    margin = A.get('margin', 0.3)
    flip = -1 if A.get('lean', 'forward') == 'back' else 1
    rows_mode = A.get('rows', 'double')                # 'double' = row|aisle|row modules, 'single' = row|aisle
    # local frame: u along aisle, v across
    loc = [rot(p, -ang) for p in poly]
    umin, umax = min(p[0] for p in loc), max(p[0] for p in loc)
    vmin, vmax = min(p[1] for p in loc), max(p[1] for p in loc)
    u0 = umin + A.get('offset_u', 0.0); v0 = vmin + A.get('offset_v', 0.0)
    if th == 0:
        fw, depth = Ld, W
    else:
        s = math.sin(math.radians(th)); c = math.cos(math.radians(th))
        fw, depth = W / s, Ld * s
    rows = []   # (edge_v, side) side=-1: stalls below the aisle edge, +1: above
    v = v0
    while v < vmax:
        if rows_mode == 'single':
            rows.append((v + depth, -1)); v += depth + aisle
        else:
            rows.append((v + depth, -1)); rows.append((v + depth + aisle, +1)); v += 2 * depth + aisle
    stalls, aisles = [], []
    for ri, (e, side) in enumerate(rows):
        if th == 0:
            sv = (0.0, side * W)
        else:
            sv = (flip * Ld * math.cos(math.radians(th)), side * Ld * math.sin(math.radians(th)))
        # stagger the row start so angled rows begin inside
        u = u0 + (max(0, -sv[0]) if sv[0] < 0 else 0)
        run = []
        while u + fw <= umax + 1e-6:
            q = [(u, e), (u + fw, e), (u + fw + sv[0], e + sv[1]), (u + sv[0], e + sv[1])]
            acc = (u + fw / 2, e - side * aisle / 2)          # aisle centre in front of the stall
            wq = [rot(p, ang) for p in q]; wacc = rot(acc, ang)
            ok = all(inside(p, poly) and poly_dist(p, poly) >= margin - 1e-6 for p in wq[:4]) \
                and all(inside(p, poly) for p in sample_pts(wq)) and inside(wacc, poly)
            if ok:
                for b in blockers:
                    if any(inside(p, b) for p in sample_pts(wq)) or any(inside(p, wq) for p in b) \
                            or min(poly_dist(p, b) for p in wq) < 0.3 or inside(wacc, b):
                        ok = False; break
            if ok:
                for (rp, rw) in roads:
                    if min(line_dist(p, rp) for p in sample_pts(wq)) < rw / 2 + 0.2:
                        ok = False; break
            if ok:
                run.append(dict(quad=[list(map(lambda x: round(x, 3), p)) for p in wq], row=ri,
                                axis=[round(x, 4) for x in rot(sv, ang)], front=round(fw, 3),
                                type='motorcycle' if moto else 'normal'))
            u += fw
        stalls += run
        if run and (side == -1 or rows_mode == 'single'):
            us = [rot(s_['quad'][0], -ang)[0] for s_ in run]
            mid_v = e + aisle / 2 if side == -1 else e - aisle / 2
            a0, a1 = rot((min(us), mid_v), ang), rot((max(us) + fw, mid_v), ang)
            aisles.append(dict(a=[round(a0[0], 3), round(a0[1], 3)], b=[round(a1[0], 3), round(a1[1], 3)],
                               width=aisle, one_way=bool(A.get('one_way', th not in (90,))), area=A.get('id')))
    return stalls, aisles


def assign_special(stalls, A):
    """Mark accessible stalls (merge 2 neighbours: stall + access aisle) and EV stalls."""
    n_acc, n_ev = A.get('accessible', 0), A.get('ev', 0)
    near = A.get('special_near') or centroid(A['polygon'])
    def d(s): return math.dist(centroid(s['quad']), near)
    mine = [s for s in stalls if s.get('area') == A.get('id') and s['type'] == 'normal']
    # accessible: pairs of adjacent stalls in the same row, closest first
    pairs = []
    by_row = {}
    for s in mine: by_row.setdefault(s['row'], []).append(s)
    for row in by_row.values():
        for a, b in zip(row, row[1:]):
            if math.dist(a['quad'][1], b['quad'][0]) < 0.05:
                pairs.append((d(a) + d(b), a, b))
    pairs.sort(key=lambda t: t[0]); used = set()
    for _, a, b in pairs:
        if n_acc <= 0: break
        if id(a) in used or id(b) in used: continue
        a['type'] = 'accessible'; b['type'] = 'access_aisle'; a['pair'] = True
        used |= {id(a), id(b)}; n_acc -= 1
    for s in sorted([s for s in mine if s['type'] == 'normal'], key=d)[:n_ev]:
        s['type'] = 'ev'




# ---------------------------------------------------------------- gate kits (toll-booth style checkpoints)
# Lane layouts measured from the client's drawings: (direction, lane width incl. outer strip, outer strip width)
# listed left -> right when facing the IN direction; the booth sits between the last IN and the first OUT lane.
GATE_TEMPLATES = {
    'T794':  dict(lanes=[('in', 3.35, 1.0), ('out', 3.35, 1.0)], booth=(1.24, 2.47)),
    'T884':  dict(lanes=[('in', 3.80, 1.0), ('out', 3.80, 1.0)], booth=(1.24, 2.50)),
    'T1060': dict(lanes=[('in', 3.50, 1.0), ('out', 3.50, 1.0)], booth=(1.60, 3.95)),
    'T1323': dict(lanes=[('in', 2.90, .9), ('in', 2.90, 0), ('out', 2.90, 0), ('out', 2.90, .9)], booth=(1.63, 3.90)),
}

def expand_gate_kits(site):
    """Turn each gate_kits entry into lanes, islands, booth and per-lane equipment
    (ticket machine at the entry end, LPR camera + display, safety loop + radar under the barrier arm)."""
    kits = site.get('gate_kits', [])
    for k in kits:
        T = dict(GATE_TEMPLATES[k['template']]) if k.get('template') else {}
        T.update({x: k[x] for x in ('lanes', 'booth') if x in k})
        bw, bl = T['booth']; lanes = T['lanes']
        h = math.radians(k['heading']); t = (math.cos(h), math.sin(h)); n = (math.sin(h), -math.cos(h))   # n = right of IN
        P0 = k['pos']
        def W(u, v): return [round(P0[0] + n[0] * u + t[0] * v, 3), round(P0[1] + n[1] * u + t[1] * v, 3)]
        nin = sum(1 for d, _, _ in lanes if d == 'in')
        RW0 = k.get('road_width')
        tot0 = sum(w for _, w, _ in lanes) + bw
        if RW0 and abs(tot0 - RW0) < .6:
            # gate fills the road: share each half of the road equally between that direction's lanes, so lane lines,
            # arrows and loops sit on a regular grid (the drawing's 0.9-1.0 m gutter strip becomes part of the lane)
            nout = len(lanes) - nin
            lanes = [(d, (RW0 / 2 - bw / 2) / (nin if d == 'in' else nout), 0) for d, _, _ in lanes]
        # u positions: booth centred on u = 0
        edges, u = [], -bw / 2 - sum(w for d, w, _ in lanes[:nin])
        for i, (d, w, s) in enumerate(lanes):
            if i == nin: u += bw
            edges.append((u, u + w)); u += w
        total = edges[-1][1] - edges[0][0]
        span = bl / 2 + 2.3; AP = k.get('apron', 22)
        gid = k['id']; label = k.get('label', gid)
        uL, uR = edges[0][0], edges[-1][1]
        RW = k.get('road_width')
        S1 = span + 3 if RW else AP                         # straight section; beyond it the apron tapers to the road width
        if RW and total <= RW + .05:
            # road keeps one width: the gate sits inside it, kerbed islands fill the gap at each side (tapered noses)
            rL, rR = -RW / 2, RW / 2
            site.setdefault('parking_areas', []).append(dict(id=f'{gid}_apron', label=label, polygon=[W(rL, -AP), W(rR, -AP), W(rR, AP), W(rL, AP)],
                                                             no_stalls=True, kit=gid))
            T_ = min(6.0, AP - S1 - .5)
            for (ge, re_) in ((uL, rL), (uR, rR)):
                if abs(ge - re_) < .25: continue
                site['islands'].append(dict(id=f'{gid}_side{int(ge > 0)}', kind='green', no_hatch=True, no_trees=True,
                                            polygon=[W(re_, -S1 - T_), W(ge, -S1), W(ge, S1), W(re_, S1 + T_)] if ge > re_ else
                                                    [W(re_, S1 + T_), W(ge, S1), W(ge, -S1), W(re_, -S1 - T_)]))
            for sr in (rL + .3, rR - .3):
                site.setdefault('lines', []).append(dict(points=[W(sr, -AP), W(sr, AP)], width=.12))
        elif RW:
            rL, rR = -RW / 2, RW / 2
            poly = [W(rL, -AP), W(rR, -AP), W(uR, -S1), W(uR, S1), W(rR, AP), W(rL, AP), W(uL, S1), W(uL, -S1)]
            site.setdefault('parking_areas', []).append(dict(id=f'{gid}_apron', label=label, polygon=poly, no_stalls=True, kit=gid))
            for su, sr in ((uL + .3, rL + .3), (uR - .3, rR - .3)):      # edge lines follow the flare
                site.setdefault('lines', []).append(dict(points=[W(sr, -AP), W(su, -S1), W(su, S1), W(sr, AP)], width=.12))
        else:
            site.setdefault('roads', []).append(dict(id=f'{gid}_pave', label=label, points=[W((uL + uR) / 2, -AP), W((uL + uR) / 2, AP)],
                                                     width=total + .02, block_stalls=False, kit=gid, markings=False))
        site.setdefault('islands', []).append(dict(id=f'{gid}_booth', kind='equipment', no_hatch=True,
                                                   polygon=[W(-bw / 2, -span), W(bw / 2, -span), W(bw / 2, span), W(-bw / 2, span)]))
        eq = site.setdefault('equipment', []); n_eq0 = len(eq)
        eq.append(dict(type='guard_booth', gate=gid, pos=W(0, 0), heading=k['heading'] + 90, size=[bw - .14, bl], label=f'ป้อม {label}'))
        lines = site.setdefault('lines', []); arrows = site.setdefault('arrows', [])
        nlane = {'in': 0, 'out': 0}
        # islands across the gate (u intervals): the booth and a 0.72 m divider at every lane edge whose equipment is not on the booth
        ISL = [(-bw / 2, bw / 2)]
        for (d_, w_, s_), (ua_, ub_) in zip(lanes, edges):
            se = ub_ if d_ == 'in' else ua_
            if abs(abs(se) - bw / 2) >= .05: ISL.append((se - .36, se + .36))
        def clear_of(ua_, ub_):
            """drivable width of a lane between islands (the 0.9-1.0 m outer strip is a flush gutter, part of the lane)"""
            a_ = max([ua_] + [hi for lo, hi in ISL if lo < ua_ + .5 and hi > ua_])
            b_ = min([ub_] + [lo for lo, hi in ISL if hi > ub_ - .5 and lo < ub_])
            outer = [edges[0][0], edges[-1][1]]
            if abs(a_ - outer[0]) < 1e-6: a_ += .35      # keep clear of the road edge line / kerb
            if abs(b_ - outer[1]) < 1e-6: b_ -= .35
            return a_, b_
        for i, ((d, w, s), (ua, ub)) in enumerate(zip(lanes, edges)):
            nlane[d] += 1; tag = f"{'ขาเข้า' if d == 'in' else 'ขาออก'} ช่อง {nlane[d]}"
            sg = 1 if d == 'in' else -1                     # travel direction along v
            side_u = ub if d == 'in' else ua                # driver's (right) side edge
            strip_u = ua if d == 'in' else ub               # outer strip on the far side
            inner = -1 if d == 'in' else 1                  # from the equipment edge into the lane (u direction)
            drive_a, drive_b = clear_of(ua, ub)                 # loops / arm / STOP fit this clear width
            uc = (drive_a + drive_b) / 2
            on_booth = abs(abs(side_u) - bw / 2) < .05
            host = side_u + (-inner * .34 if on_booth else 0)  # equipment sits on the booth island or on a divider (0.62 m pads stay inside)
            if not on_booth:
                site['islands'].append(dict(id=f'{gid}_div{i}', kind='equipment', no_hatch=True,
                                            polygon=[W(side_u - .36, -span), W(side_u + .36, -span), W(side_u + .36, span), W(side_u - .36, span)]))
            hdg_in = k['heading'] if d == 'in' else k['heading'] + 180
            face_lane = math.degrees(math.atan2(n[1] * inner, n[0] * inner))
            ex = bl / 2                                     # exit end of the booth along travel
            if d == 'in':
                eq.append(dict(type='ticket_dispenser', gate=gid, lane=tag, pos=W(host, -sg * (ex + .5)), heading=face_lane,
                               label=f'ตู้จ่ายสลิป {tag} ({label})'))
            else:                                       # exit lanes: CREATIVE Kiosk Exit (kit 'hardware' can still override)
                eq.append(dict(type='ticket_dispenser', model='creative_exit', gate=gid, lane=tag, pos=W(host, -sg * (ex + .5)),
                               heading=face_lane, label=f'ตู้ Kiosk Exit {tag} ({label})'))
            # LPR at the booth/divider corner, at the island edge, yawed into the lane so it reads approaching plates
            # past the booth (straight back would look into the booth / ticket machine); the LED display keeps facing the driver
            # LPR + display pole: stands clear of the booth end (0.75 m past it, beside the loop), at the island edge,
            # and the whole unit (camera AND screen) is turned >= 30 deg from straight-back toward the lane, so the camera
            # looks at cars on the road and the screen faces the approaching driver - never at the booth.
            s_l = ex + 1.2                                     # clear of the booth and of the other lane's slip dispenser
            host_l = side_u - inner * .28 if on_booth else side_u   # 0.36 m base pad (turned with the unit) fully on the island
            P_l = W(host_l, sg * s_l); T_l = W(uc, sg * (s_l - 4.5))
            back = (-t[0] * sg, -t[1] * sg); lane_dir = (n[0] * inner, n[1] * inner)
            yaw = max(30.0, math.degrees(math.atan2(abs(uc - host_l), 4.5)))
            v_ = (back[0] * math.cos(math.radians(yaw)) + lane_dir[0] * math.sin(math.radians(yaw)),
                  back[1] * math.cos(math.radians(yaw)) + lane_dir[1] * math.sin(math.radians(yaw)))
            hd_cam = math.degrees(math.atan2(v_[1], v_[0]))
            reach = abs(uc - host_l) / max(.2, math.sin(math.radians(yaw)))          # where the centre ray crosses the lane centre
            tilt = math.degrees(math.atan2(1.45, max(2.5, reach)))
            ydir = (-v_[1], v_[0]); isl = (-lane_dir[0], -lane_dir[1])
            eq.append(dict(type='lpr_camera', gate=gid, lane=tag, pos=P_l, heading=round(hd_cam, 1), tilt=round(tilt, 1), display=True,
                           display_yaw=0, display_shift=.16 if ydir[0] * isl[0] + ydir[1] * isl[1] > 0 else -.16,
                           label=f'กล้อง LPR + จอแสดงผล {tag}'))
            # two loops per lane: presence loop just before the barrier (car waiting at the boom) and an exit/safety loop
            # just after it (confirms the car has driven through, then the boom may close)
            lw = round(min(1.8, drive_b - drive_a - .6), 2)      # 0.3 m clear of islands / lines each side
            eq.append(dict(type='loop_detector', gate=gid, lane=tag, role='before', pos=W(uc, sg * (ex + 1.8 - 1.15)), heading=hdg_in,
                           width=lw, length=1.0, label=f'ลูปก่อนไม้กั้น {tag}'))
            eq.append(dict(type='loop_detector', gate=gid, lane=tag, role='after', pos=W(uc, sg * (ex + 1.8 + 1.25)), heading=hdg_in,
                           width=lw, length=1.0, label=f'ลูปหลังไม้กั้น (ตรวจรถผ่าน) {tag}'))
            eq.append(dict(type='barrier_gate', gate=gid, lane=tag, pos=W(host, sg * (ex + 1.8)), heading=face_lane,
                           arm=round(abs(strip_u + (s * inner * -1 if False else 0) - host) - .3 - (s if s else 0) * 0, 2),
                           traffic=hdg_in, label=f'ไม้กั้น {tag}', **({'status': k['faults'][tag]} if tag in k.get('faults', {}) else {})))
            far = drive_a if d == 'in' else drive_b             # arm reaches the far side of the clear lane
            eq[-1]['arm'] = round(abs(far - host) - .45, 2)
            eq.append(dict(type='radar_sensor', gate=gid, lane=tag, pos=W(host, sg * (ex + 1.55)), heading=face_lane,
                           label=f'เรดาร์ {tag}'))
            # paint: strip edge line, lane arrows
            # (no line at the gutter strip: it is part of the drivable lane; the road edge line marks the edge)
            um = (ua + ub) / 2                                   # arrows on the lane centre line
            arrows.append(dict(pos=W(um, -sg * (ex + 4.5)), heading=hdg_in))
            arrows.append(dict(pos=W(um, sg * (ex + 6.5)), heading=hdg_in))
        for e_ in eq[n_eq0:]:                      # per-kit hardware choice, e.g. {'barrier_gate': {'model': 'folding'}}
            e_.update(k.get('hardware', {}).get(e_['type'], {}))
        # lane dividers where lanes meet without an island beyond the island ends
        for (d1, _, _), (d2, _, _), (a1, b1), (a2, b2) in zip(lanes, lanes[1:], edges, edges[1:]):
            if abs(b1 - a2) < 1e-6:
                for v0, v1 in ((-S1, -span - .2), (span + .2, S1)):
                    lines.append(dict(points=[W(b1, v0), W(b1, v1)], width=.12, color='yellow' if d1 != d2 else 'white', dashed=d1 == d2))
        # opposing-direction separation: yellow centre line on the road axis, running into each booth-island nose
        lines.append(dict(points=[W(0, -AP), W(0, -span - .2)], width=.12, color='yellow'))
        lines.append(dict(points=[W(0, span + .2), W(0, AP)], width=.12, color='yellow'))
        site.setdefault('gates', []).append(dict(id=gid, type='both', label=label, pos=k['pos'], heading=k['heading'],
                                                 lanes=len(lanes), lanes_in=nin, lanes_out=len(lanes) - nin, width=round(total, 2)))
    return site

# ---------------------------------------------------------------- main
def build(site):
    expand_gate_kits(site)
    out = dict(name=site.get('name', 'Parking Site'), units='m', north_deg=site.get('north_deg', 90))
    out['site'] = site.get('site')
    out['buildings'] = site.get('buildings', [])
    out['islands'] = site.get('islands', [])
    out['sidewalks'] = site.get('sidewalks', [])
    out['no_parking'] = site.get('no_parking', [])
    out['trees'] = site.get('trees', [])
    out['streets'] = site.get('streets', [])
    out['crosswalks'] = site.get('crosswalks', [])
    out['water'] = site.get('water', [])
    out['lines'] = site.get('lines', [])
    out['cables'] = site.get('cables', [])
    out['control_room'] = site.get('control_room')
    roads = site.get('roads', [])
    out['roads'] = [dict(r, band=[list(map(lambda x: round(x, 3), p)) for p in road_band(r['points'], r.get('width', 6.0))]) for r in roads]
    blockers = [b['polygon'] for k in ('buildings', 'islands', 'sidewalks', 'no_parking') for b in site.get(k, [])]
    road_lines = [(r['points'], r.get('width', 6.0)) for r in roads if r.get('block_stalls', True)]
    stalls, aisles = [], []
    for A in site.get('parking_areas', []):
        if A.get('no_stalls'): continue      # plain paved area (plaza / driveway apron)
        st, ai = fill_area(A, blockers, road_lines)
        for s in st: s['area'] = A.get('id')
        stalls += st; aisles += ai
        assign_special(stalls, A)
    # manual stalls (exact quads traced from a plan)
    for s in site.get('stalls', []):
        stalls.append(dict(quad=s['quad'], type=s.get('type', 'normal'), area=s.get('area', 'manual'),
                           axis=s.get('axis'), row=-1, front=None))
    for i, s in enumerate(stalls, 1):
        s['id'] = f"P{i:03d}"
    out['parking_areas'] = site.get('parking_areas', [])
    out['stalls'] = stalls; out['aisles'] = aisles + site.get('aisles', [])
    out['arrows'] = site.get('arrows', [])
    out['gates'] = site.get('gates', [])
    # equipment: explicit list + EV chargers at the head of each EV stall
    eq = [dict(e) for e in site.get('equipment', [])]
    for s in stalls:
        if s['type'] == 'ev' and site.get('auto_ev_chargers', True):
            q = s['quad']; back = ((q[2][0] + q[3][0]) / 2, (q[2][1] + q[3][1]) / 2)
            ax = s['axis'] or (0, -1); l = math.hypot(*ax) or 1
            pos = (back[0] + ax[0] / l * 0.4, back[1] + ax[1] / l * 0.4)
            eq.append(dict(type='ev_charger', pos=[round(pos[0], 3), round(pos[1], 3)],
                           heading=round(math.degrees(math.atan2(-ax[1], -ax[0])), 1), stall=s['id'], auto=True))
    counters = {}
    for e in eq:
        t = e['type']
        if t not in EQUIP: raise SystemExit(f"unknown equipment type: {t} (known: {', '.join(EQUIP)})")
        counters[t] = counters.get(t, 0) + 1
        e.setdefault('id', f"{EQUIP[t][2]}-{counters[t]:02d}")
        e.setdefault('label', EQUIP[t][0])
        e.setdefault('heading', 0)
        e.setdefault('status', 'ok')
        e['name_th'] = EQUIP[t][0]
        if t in HW_MODELS:
            e.setdefault('model', default_model(t))
            if e['model'] not in [m[0] for m in HW_MODELS[t]]:
                raise SystemExit(f"unknown model '{e['model']}' for {t} (known: {', '.join(m[0] for m in HW_MODELS[t])})")
            e['model_th'] = model_th(t, e['model'])
        e['status_th'] = STATUS_TH.get(e['status'], e['status'])
    out['equipment'] = eq
    out['equip_catalogue'] = {k: dict(name_th=v[0], color=v[1], code=v[2]) for k, v in EQUIP.items()}
    out['summary'] = summarize(out)
    return out


def summarize(L):
    g = L['gates']
    st = {}
    for s in L['stalls']:
        if s['type'] == 'access_aisle': continue
        st[s['type']] = st.get(s['type'], 0) + 1
    eq = {}
    for e in L['equipment']:
        eq.setdefault(e['type'], []).append(e['id'])
    faults = [dict(id=e['id'], type=e['type'], name_th=e['name_th'], label=e.get('label'), gate=e.get('gate'), status=e['status'], note=e.get('note', ''))
              for e in L['equipment'] if e.get('status', 'ok') != 'ok']
    def lanes_open(x):
        bad = sum(1 for e in L['equipment'] if e.get('gate') == x['id'] and e['type'] == 'barrier_gate' and e.get('status', 'ok') != 'ok')
        return max(0, x.get('lanes', 1) - bad)
    return dict(
        entries=sum(1 for x in g if x.get('type') in ('entry', 'both')),
        exits=sum(1 for x in g if x.get('type') in ('exit', 'both')),
        gate_count=len(g),
        gates=[dict(id=x['id'], type=x['type'], name_th=x.get('label', GATE_TH.get(x['type'], '')),
                    lanes=x.get('lanes', 1), lanes_in=x.get('lanes_in'), lanes_out=x.get('lanes_out'), lanes_open=lanes_open(x)) for x in g],
        faults=faults,
        entry_lanes=sum(x.get('lanes_in', x.get('lanes', 1) if x.get('type') == 'entry' else 0) for x in g),
        exit_lanes=sum(x.get('lanes_out', x.get('lanes', 1) if x.get('type') == 'exit' else 0) for x in g),
        stalls=st, stalls_car=sum(v for k, v in st.items() if k != 'motorcycle'),
        stalls_total=sum(st.values()),
        equipment={k: dict(count=len(v), ids=v, name_th=EQUIP[k][0]) for k, v in eq.items()},
        site_area_m2=round(area(L['site']), 1) if L.get('site') else None,
    )


def write_reports(L, outd):
    S = L['summary']
    with open(os.path.join(outd, 'summary.json'), 'w', encoding='utf8') as f:
        json.dump(S, f, ensure_ascii=False, indent=1)
    lines = [f"# สรุปลานจอดรถ: {L['name']}", '']
    lines += ['## ทางเข้า-ออก', '', f"- ทางเข้า **{S['entries']}** จุด ({S['entry_lanes']} ช่องทาง)",
              f"- ทางออก **{S['exits']}** จุด ({S['exit_lanes']} ช่องทาง)", '']
    lines += ['| รหัส | ประเภท | ชื่อ | ช่องทาง | ใช้งานได้ |', '|---|---|---|---|---|']
    for g in S['gates']:
        lines.append(f"| {g['id']} | {GATE_TH.get(g['type'], g['type'])} | {g['name_th']} | {g['lanes']} | {g['lanes_open']} |")
    if S['faults']:
        lines += ['', '## อุปกรณ์ที่เสีย / ปิดซ่อม', '', '| รหัส | อุปกรณ์ | จุด | สถานะ | หมายเหตุ |', '|---|---|---|---|---|']
        for x in S['faults']:
            lines.append(f"| {x['id']} | {x['label'] or x['name_th']} | {x['gate'] or '-'} | {STATUS_TH.get(x['status'], x['status'])} | {x['note']} |")
    lines += ['', '## ช่องจอด', '', '| ประเภท | จำนวน |', '|---|---|']
    for k, v in S['stalls'].items():
        lines.append(f"| {STALL_TH.get(k, k)} | {v} |")
    lines.append(f"| **รวมรถยนต์** | **{S['stalls_car']}** |")
    lines += ['', '## อุปกรณ์', '', '| อุปกรณ์ | จำนวน | รหัส |', '|---|---|---|']
    for k, v in S['equipment'].items():
        lines.append(f"| {v['name_th']} | {v['count']} | {', '.join(v['ids'])} |")
    lines += ['', '## ตำแหน่งอุปกรณ์', '', '| รหัส | อุปกรณ์ | ตำแหน่ง X, Y (ม.) | ประจำจุด | สถานะ | หมายเหตุ |', '|---|---|---|---|---|---|']
    for e in L['equipment']:
        lines.append(f"| {e['id']} | {e['name_th']} | {e['pos'][0]:.1f}, {e['pos'][1]:.1f} | {e.get('gate', e.get('stall', '-'))} | {e['status_th']} | {e.get('note', '') if e.get('label') == e['name_th'] else e.get('label', '')} |")
    with open(os.path.join(outd, 'summary_th.md'), 'w', encoding='utf8') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.join(outd, 'equipment.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['id', 'type', 'name_th', 'label', 'x_m', 'y_m', 'heading_deg', 'gate', 'stall', 'status', 'note'])
        for e in L['equipment']:
            w.writerow([e['id'], e['type'], e['name_th'], e.get('label', ''), e['pos'][0], e['pos'][1], e.get('heading', 0),
                        e.get('gate', ''), e.get('stall', ''), e['status'], e.get('note', '')])


def plan_png(L, path, underlay=None, px_per_m=None, bbox=None, title=None):
    """2D check plan. underlay = dict(image, px_per_m, origin_px=[x,y]) draws the source plan beneath."""
    from PIL import Image, ImageDraw, ImageFont
    pts = [p for p in (L['site'] or [])] + [p for s in L['stalls'] for p in s['quad']]
    for k in ('buildings', 'islands', 'sidewalks'):
        pts += [p for b in L[k] for p in b['polygon']]
    for r in L['roads']: pts += r['band']
    for s in L['streets']: pts += s['polygon']
    for w_ in L.get('water', []): pts += w_['polygon']
    x0, x1 = min(p[0] for p in pts) - 6, max(p[0] for p in pts) + 6
    y0, y1 = min(p[1] for p in pts) - 6, max(p[1] for p in pts) + 6
    if bbox: x0, x1, y0, y1 = bbox
    k = px_per_m or max(.6, min(10, 2400 / max(x1 - x0, y1 - y0))); Wp, Hp = int((x1 - x0) * k), int((y1 - y0) * k)
    legend_w = 360
    im = Image.new('RGB', (Wp + legend_w, max(Hp, 700)), (245, 245, 240))
    def P(p): return ((p[0] - x0) * k, (y1 - p[1]) * k)
    if underlay:
        try:
            ui = Image.open(underlay['image']).convert('RGB'); s = k / underlay['px_per_m']
            ui = ui.resize((int(ui.width * s), int(ui.height * s)))
            ox, oy = underlay.get('origin_px', [0, 0])          # pixel of world (0,0) in the source image
            im.paste(Image.blend(Image.new('RGB', ui.size, (255, 255, 255)), ui, .45),
                     (int(P((0, 0))[0] - ox * s), int(P((0, 0))[1] - oy * s)))
        except Exception as ex:
            print('underlay failed:', ex)
    d = ImageDraw.Draw(im, 'RGBA')
    def font(sz, bold=False):
        for f in (('tahomabd.ttf' if bold else 'tahoma.ttf'), 'arial.ttf'):
            try: return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', f), sz)
            except Exception: pass
        return ImageFont.load_default()
    f10, f12, f14, f18 = font(10), font(12), font(14, True), font(18, True)
    def poly(pp, fill, outline=None, w=1):
        d.polygon([P(p) for p in pp], fill=fill, outline=outline);
        if outline and w > 1: d.line([P(p) for p in pp] + [P(pp[0])], fill=outline, width=w)
    if L['site']: poly(L['site'], (225, 235, 215, 255), (60, 60, 60), 2)
    for s in L['streets']: poly(s['polygon'], (90, 90, 95, 255))
    for w_ in L.get('water', []): poly(w_['polygon'], (110, 170, 210, 255))
    for A in L['parking_areas']: poly(A['polygon'], (120, 120, 125, 255))
    for r in L['roads']: poly(r['band'], (110, 110, 115, 255))
    for s in L['sidewalks']: poly(s['polygon'], (205, 200, 190, 255), (150, 150, 150))
    for s in L['islands']: poly(s['polygon'], (120, 170, 90, 255), (200, 200, 200))
    for s in L['no_parking']: poly(s['polygon'], (230, 200, 40, 120), (230, 200, 40))
    for b in L['buildings']:
        poly(b['polygon'], (180, 175, 170, 255), (70, 70, 70), 2)
        c = P(centroid(b['polygon'])); t = b.get('label', b.get('id', ''))
        d.text(c, t, fill=(30, 30, 30), font=f14, anchor='mm')
    col = {'normal': (255, 255, 255, 40), 'accessible': (40, 110, 230, 200), 'access_aisle': (255, 255, 255, 60),
           'ev': (30, 190, 120, 200), 'motorcycle': (240, 200, 60, 80)}
    for s in L['stalls']:
        d.polygon([P(p) for p in s['quad']], fill=col.get(s['type'], (255, 255, 255, 40)), outline=(255, 255, 255))
    for ln in L.get('lines', []):
        d.line([P(p) for p in ln['points']], fill=(240, 200, 0) if ln.get('color') == 'yellow' else (255, 255, 255), width=2)
    for a in L['aisles']:
        A_, B_ = P(a['a']), P(a['b'])
        d.line([A_, B_], fill=(255, 255, 255, 90), width=1)
    for cb in L.get('cables', []):
        d.line([P(p) for p in cb['points']], fill=tuple(int(v * 255) for v in cb.get('color', [.1, .3, .9])), width=2)
    for g in L['gates']:
        c = P(g['pos']); col_g = (20, 160, 60) if g['type'] == 'entry' else (220, 50, 40) if g['type'] == 'exit' else (230, 150, 20)
        h = math.radians(g.get('heading', 90)); dx, dy = math.cos(h) * 22, -math.sin(h) * 22
        d.line([(c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy)], fill=col_g, width=4)
        d.polygon([(c[0] + dx * 1.3, c[1] + dy * 1.3), (c[0] + dx * .7 - dy * .4, c[1] + dy * .7 + dx * .4),
                   (c[0] + dx * .7 + dy * .4, c[1] + dy * .7 - dx * .4)], fill=col_g)
        d.rounded_rectangle([c[0] + 10, c[1] - 26, c[0] + 10 + 16 + 8 * len(g['id']), c[1] - 8], 4, fill=col_g)
        d.text((c[0] + 14, c[1] - 25), g['id'], fill='white', font=f12)
    for e in L['equipment']:
        c = P(e['pos']); cc = EQUIP[e['type']][1]
        d.ellipse([c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5], fill=cc, outline='white')
        if e.get('status', 'ok') != 'ok':
            d.ellipse([c[0] - 10, c[1] - 10, c[0] + 10, c[1] + 10], outline=(230, 30, 30), width=3)
        if not e.get('auto'):
            d.text((c[0] + 7, c[1] + 2), e['id'], fill=(20, 20, 20), font=f10)
    # scale bar + north
    sx, sy = 20, Hp - 25
    d.rectangle([sx, sy, sx + 10 * k, sy + 6], fill='black'); d.text((sx, sy - 16), '10 m', fill='black', font=f12)
    nx, ny = 40, 40
    d.polygon([(nx, ny - 22), (nx - 9, ny + 8), (nx, ny + 2), (nx + 9, ny + 8)], fill='black'); d.text((nx, ny + 18), 'N', fill='black', font=f14, anchor='mm')
    # legend
    S = L['summary']; lx = Wp + 16; y = 16
    d.rectangle([Wp, 0, Wp + legend_w, im.height], fill=(255, 255, 255))
    d.text((lx, y), title or L['name'], fill='black', font=f18); y += 34
    d.text((lx, y), f"ทางเข้า {S['entries']}  ทางออก {S['exits']}", fill='black', font=f14); y += 24
    for k_, v in S['stalls'].items():
        d.rectangle([lx, y + 3, lx + 14, y + 15], fill=col.get(k_, (255, 255, 255))[:3], outline='black')
        d.text((lx + 22, y), f"{STALL_TH.get(k_, k_)}: {v}", fill='black', font=f12); y += 20
    d.text((lx, y), f"รวมช่องจอดรถยนต์ {S['stalls_car']}", fill='black', font=f14); y += 30
    for k_, v in S['equipment'].items():
        cc = EQUIP[k_][1]
        d.ellipse([lx, y + 3, lx + 12, y + 15], fill=cc)
        d.text((lx + 22, y), f"{v['name_th']} × {v['count']}", fill='black', font=f12); y += 20
    im.save(path)


def main():
    site_path, outd = sys.argv[1], sys.argv[2]
    os.makedirs(outd, exist_ok=True)
    site = json.load(open(site_path, encoding='utf8'))
    L = build(site)
    L['source'] = os.path.abspath(site_path)
    with open(os.path.join(outd, 'layout.json'), 'w', encoding='utf8') as f:
        json.dump(L, f, ensure_ascii=False)
    write_reports(L, outd)
    ul = site.get('underlay')
    if ul and not os.path.isabs(ul['image']):
        ul = dict(ul, image=os.path.join(os.path.dirname(os.path.abspath(site_path)), ul['image']))
    plan_png(L, os.path.join(outd, 'plan.png'), ul)
    for g in L['gates']:      # close-up check plan per gate (compare with the gate drawing)
        gx, gy = g['pos']; r_ = max(16, g.get('width', 10) * 1.4)
        plan_png(L, os.path.join(outd, f"plan_{g['id']}.png"), None, 900 / (2 * r_), (gx - r_, gx + r_, gy - r_, gy + r_), f"{g['id']} {g.get('label', '')}")
    S = L['summary']
    print('LAYOUT_OK', 'stalls', S['stalls'], 'entries', S['entries'], 'exits', S['exits'],
          'equipment', {k: v['count'] for k, v in S['equipment'].items()})


if __name__ == '__main__':
    main()
