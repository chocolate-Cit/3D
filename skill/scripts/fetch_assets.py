# parking-site-3d: download the CC0 Poly Haven textures + HDRI the builder uses (once; cached in ../assets).
#   py fetch_assets.py [--res 1k]
import json, os, sys, urllib.request

RES = sys.argv[sys.argv.index('--res') + 1] if '--res' in sys.argv else '1k'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
try:                                   # skill folder may be read-only (skill synced from the account): use the user cache
    os.makedirs(ROOT, exist_ok=True); open(os.path.join(ROOT, '.w'), 'w').close(); os.remove(os.path.join(ROOT, '.w'))
except OSError:
    ROOT = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'parking-site-3d', 'assets')
TEXTURES = {   # role: Poly Haven asset id
    'asphalt': 'asphalt_02',
    'grass': 'leafy_grass',
    'concrete': 'concrete_floor_02',
    'pavers': 'interlocking_concrete_pavers',
}
HDRI = 'kloofendal_48d_partly_cloudy_puresky'
MAPS = {'Diffuse': 'diff', 'nor_gl': 'nor', 'Rough': 'rough'}
UA = {'User-Agent': 'parking-site-3d/1.0'}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()

def save(url, path):
    if os.path.exists(path): return 'cached'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url); open(path, 'wb').write(data); return f'{len(data) // 1024} KB'

manifest = {'textures': {}, 'hdri': None, 'license': 'CC0 (polyhaven.com)'}
for role, aid in TEXTURES.items():
    files = json.loads(get(f'https://api.polyhaven.com/files/{aid}'))
    manifest['textures'][role] = {'asset': aid}
    for key, short in MAPS.items():
        f = files[key][RES]['jpg']
        p = os.path.join(ROOT, 'textures', aid, f'{short}.jpg')
        print(role, short, save(f['url'], p))
        manifest['textures'][role][short] = os.path.relpath(p, ROOT).replace('\\', '/')
files = json.loads(get(f'https://api.polyhaven.com/files/{HDRI}'))
p = os.path.join(ROOT, 'hdri', f'{HDRI}_2k.hdr')
print('hdri', save(files['hdri']['2k']['hdr']['url'], p))
manifest['hdri'] = os.path.relpath(p, ROOT).replace('\\', '/')
json.dump(manifest, open(os.path.join(ROOT, 'manifest.json'), 'w'), indent=1)
print('ASSETS_OK', ROOT)
