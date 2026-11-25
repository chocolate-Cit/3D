# parking-site-3d: stable fingerprint of a build, to prove another computer makes the SAME model.
#   py fingerprint.py <out_dir>            -> prints a JSON summary + one hash per part
#   py fingerprint.py <out_dir> <ref.json> -> compares with a saved reference, prints MATCH or the differences
# Byte hashes of site.glb differ run to run (the glTF exporter shuffles primitive order), so this compares content:
# layout.json exactly, and per glb mesh: name, vertex count, rounded bounding box, material names; per node: name + rounded transform.
import hashlib, json, os, struct, sys

def h(o): return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode('utf8')).hexdigest()[:16]

def glb_parts(p):
    b = open(p, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    acc = j.get('accessors', []); mats = j.get('materials', [])
    meshes = []
    for m in j.get('meshes', []):
        vc, lo, hi, mn = 0, [1e9] * 3, [-1e9] * 3, []
        for pr in m['primitives']:
            a = acc[pr['attributes']['POSITION']]; vc += a['count']
            lo = [min(x, y) for x, y in zip(lo, a['min'])]; hi = [max(x, y) for x, y in zip(hi, a['max'])]
            if 'material' in pr: mn.append(mats[pr['material']].get('name', ''))
        meshes.append((m.get('name', ''), vc, [round(x, 2) for x in lo], [round(x, 2) for x in hi], sorted(mn)))
    nodes = sorted((nd.get('name', ''), [round(x, 2) for x in nd.get('translation', [0, 0, 0])],
                    [round(x, 3) for x in nd.get('rotation', [0, 0, 0, 1])], [round(x, 3) for x in nd.get('scale', [1, 1, 1])])
                   for nd in j.get('nodes', []))
    return sorted(meshes), nodes, len(j.get('images', []))

def fingerprint(d):
    lay = json.load(open(os.path.join(d, 'layout.json'), encoding='utf8')); lay.pop('source', None)   # input path differs per computer
    meshes, nodes, nimg = glb_parts(os.path.join(d, 'site.glb'))
    return dict(layout=h(lay), meshes=h(meshes), nodes=h(nodes), n_meshes=len(meshes), n_nodes=len(nodes), n_images=nimg,
                n_equipment=len(lay.get('equipment', [])), n_buildings=len(lay.get('buildings', [])))

if __name__ == '__main__':
    fp = fingerprint(sys.argv[1])
    if len(sys.argv) > 2:
        ref = json.load(open(sys.argv[2], encoding='utf8'))
        bad = {k: (ref.get(k), v) for k, v in fp.items() if ref.get(k) != v}
        print('MATCH' if not bad else 'DIFFERENT ' + json.dumps(bad, ensure_ascii=False))
        sys.exit(1 if bad else 0)
    print(json.dumps(fp, indent=1))
