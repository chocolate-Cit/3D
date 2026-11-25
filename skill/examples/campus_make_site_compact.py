# Compact dashboard version of the 5-checkpoint campus (v2: tighter).
# Keeps the order/topology of the overview drawing (6.jpg) but the checkpoints sit close together so the
# whole project fits a dashboard panel. Every road has ONE width (= the widest gate, 13.3 m); narrower gates
# sit inside it with kerbed islands at their sides. Hardware layouts are the exact drawings (T1323/T1060/T794/T884).
#   py make_site_compact.py  -> site_compact.json
import json, os

RW = 13.3                      # one road width everywhere (fits the 13.23 m 2-in/2-out checkpoints)
H = RW / 2
REAL = {'G1': 148, 'G2': 871, 'G3': 1049, 'G4': 444, 'G5': 594}   # uplink lengths measured on the overview drawing (m)
def rect(x0, x1, y0, y1): return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

AP = 16                                    # gate apron half-length (booth area + island noses)
X_G1, X_G4, X_G5, X_G2, X_G3 = 0, 48, 78, 108, 150
Y_BR = H + 4                               # branch gates start this far off the main road edge

site = dict(name='โครงการด่านตรวจ 5 จุด (ผังย่อสำหรับ Dashboard)',
            notes='Distances between checkpoints shortened for the dashboard; gate layouts and hardware are to scale.')
site['streets'] = [dict(id='CHT', label='ถนนจตุรทิศ', polygon=rect(-36, -24, -22, 22), centerline=[[-30, -22], [-30, 22]]),
                   dict(id='KP7', label='ถนนกำแพงเพชร 7', polygon=rect(X_G2 - 24, X_G2 + 24, -Y_BR - 2 * AP - 16, -Y_BR - 2 * AP - 6),
                        centerline=[[X_G2 - 24, -Y_BR - 2 * AP - 11], [X_G2 + 24, -Y_BR - 2 * AP - 11]])]
site['roads'] = [
    dict(id='W', label='ทางเชื่อมถนนจตุรทิศ', points=[[-24, 0], [X_G1 - AP, 0]], width=RW, markings=False),
    dict(id='M1', label='ถนนภายใน', points=[[X_G1 + AP, 0], [X_G4, 0]], width=RW, trim=[0, H + .5]),
    dict(id='M2', label='ถนนภายใน', points=[[X_G4, 0], [X_G5, 0]], width=RW, trim=[H + .5, H + .5]),
    dict(id='M3', label='ถนนภายใน', points=[[X_G5, 0], [X_G2, 0]], width=RW, trim=[H + .5, H + .5]),
    dict(id='M4', label='ถนนภายใน', points=[[X_G2, 0], [X_G3 - AP, 0]], width=RW, trim=[H + .5, 0]),
    dict(id='E', label='ทางออกศูนย์วิจัย', points=[[X_G3 + AP, 0], [X_G3 + AP + 10, 0]], width=RW, markings=False),
    dict(id='B4', label='ทางเข้า I-HOUSE (A,B,C)', points=[[X_G4, H], [X_G4, Y_BR]], width=RW, markings=False),
    dict(id='B5', label='ทางเข้า I-HOUSE (C,D)', points=[[X_G5, H], [X_G5, Y_BR]], width=RW, markings=False),
    dict(id='B2', label='ทางเชื่อมจุดที่ 2', points=[[X_G2, -H], [X_G2, -Y_BR]], width=RW, markings=False),
    dict(id='B2S', label='ออกถนนกำแพงเพชร 7', points=[[X_G2, -Y_BR - 2 * AP], [X_G2, -Y_BR - 2 * AP - 6]], width=RW, markings=False),
]
site['gate_kits'] = [
    dict(id='G1', label='จุดที่ 1 ป้อมจตุรทิศ', template='T1323', pos=[X_G1, 0], heading=0, apron=AP, road_width=RW),
    dict(id='G2', label='จุดที่ 2 ป้อมเพชรบุรี', template='T1323', pos=[X_G2, -Y_BR - AP], heading=90, apron=AP, road_width=RW,
         faults={'ขาเข้า ช่อง 2': 'fault'}),
    dict(id='G3', label='จุดที่ 3 ป้อมทางออกศูนย์วิจัย', template='T1060', pos=[X_G3, 0], heading=180, apron=AP, road_width=RW),
    dict(id='G4', label='จุดที่ 4 ป้อม I-HOUSE (A,B,C)', template='T794', pos=[X_G4, Y_BR + AP], heading=90, apron=AP, road_width=RW),
    dict(id='G5', label='จุดที่ 5 ป้อม I-HOUSE (C,D)', template='T884', pos=[X_G5, Y_BR + AP], heading=90, apron=AP, road_width=RW),
]
top = Y_BR + 2 * AP

# only the control room is modelled as a building (dashboard: hardware first)
site['buildings'] = [dict(id='BB', label='Control Room (Bldg B)', polygon=rect(X_G1 + AP + 2, X_G4 - H - 2, H + 3, H + 15), height=8)]
cr = [(X_G1 + AP + X_G4 - H) / 2, H + 3]
site['control_room'] = dict(pos=cr, label='Control Room (ชั่วคราว)')
yk = H + 1.2                                   # cables run on the verge just outside the north kerb
cab = [
    dict(id='UL_G1', to='G1', points=[cr, [cr[0], yk], [X_G1 + AP - 3, yk]], color=[.1, .3, .95]),
    dict(id='UL_G4', to='G4', points=[cr, [cr[0] + 1, yk + .5], [X_G4 - H - 1, yk + .5], [X_G4 - H - 1, Y_BR + AP]], color=[.9, .1, .1]),
    dict(id='UL_G5', to='G5', points=[cr, [cr[0] + 2, yk + 1], [X_G5 - H - 1, yk + 1], [X_G5 - H - 1, Y_BR + AP]], color=[.1, .1, .6]),
    dict(id='UL_G3', to='G3', points=[cr, [cr[0] + 3, yk + 1.5], [X_G3 - AP + 3, yk + 1.5]], color=[.85, .1, .85]),
    dict(id='UL_G2', to='G2', points=[cr, [cr[0] + 4, yk + 2], [X_G5 + H + 1, yk + 2], [X_G5 + H + 1, -H - 1], [X_G2 + H + 1, -H - 1],
                                      [X_G2 + H + 1, -Y_BR - AP]], color=[.1, .7, .2]),
]
for c in cab:
    c.update(label=f"UPLink → {c['to']} ≈ {REAL[c['to']]:,} ม.", length_m=REAL[c['to']], width=.3)
site['cables'] = []          # uplink routes not shown on the dashboard map (lengths kept in REAL for reference)
site['trees'] = []
json.dump(site, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_compact.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('SITE_OK compact v2')
