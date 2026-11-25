# parking-site-3d: build a single-file web viewer (open by double-click, or publish as an artifact).
#   py make_viewer.py <out_dir>        (reads out_dir/layout.json + out_dir/site.glb -> out_dir/web/index.html)
import base64, json, os, sys

outd = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(outd, 'layout.json'), encoding='utf8'))
keep = {k: L[k] for k in ('name', 'site', 'summary', 'equipment', 'gates', 'equip_catalogue')}
keep['stalls'] = [dict(quad=s['quad']) for s in L['stalls']]
def along(pts, f):          # point at fraction f of the polyline length (cable label spot near the gate end)
    import math
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; goal = sum(seg) * f
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if goal <= s and s > 0: return [a[0] + (b[0] - a[0]) * goal / s, a[1] + (b[1] - a[1]) * goal / s]
        goal -= s
    return pts[-1]
keep['cables'] = [dict(id=c['id'], label=c.get('label', c['id']), to=c.get('to'), length_m=c.get('length_m'), mid=along(c['points'], .72)) for c in L.get('cables', [])]
keep['control_room'] = L.get('control_room')
keep['streets'] = [dict(label=s_.get('label', ''), pos=[sum(p[0] for p in s_['polygon']) / len(s_['polygon']), sum(p[1] for p in s_['polygon']) / len(s_['polygon'])]) for s_ in L.get('streets', []) if s_.get('label')]
if not keep['site']:
    pts = [p for r in L['roads'] for p in r['band']] + [p for k in ('parking_areas', 'islands', 'buildings') for a in L.get(k, []) for p in a['polygon']] + [e['pos'] for e in L['equipment']]
    keep['site'] = [[min(p[0] for p in pts), min(p[1] for p in pts)], [max(p[0] for p in pts), max(p[1] for p in pts)]]
glb = base64.b64encode(open(os.path.join(outd, 'site.glb'), 'rb').read()).decode()
html = open(os.path.join(here, '..', 'viewer', 'template.html'), encoding='utf8').read()
html = html.replace('__TITLE__', L['name']).replace('__DATA__', json.dumps(keep, ensure_ascii=False)).replace('__GLB_B64__', glb)
os.makedirs(os.path.join(outd, 'web'), exist_ok=True)
p = os.path.join(outd, 'web', 'index.html')
open(p, 'w', encoding='utf8').write(html)
import shutil
shutil.copy(os.path.join(here, '..', 'viewer', 'dashboard_example.html'), os.path.join(outd, 'web', 'dashboard_example.html'))
print('VIEWER_OK', p, round(os.path.getsize(p) / 1e6, 2), 'MB')
