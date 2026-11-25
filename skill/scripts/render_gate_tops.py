import bpy, json, sys, math, os
argv = sys.argv[sys.argv.index('--') + 1:]
L = json.load(open(argv[0], encoding='utf8')); out = argv[1]
sc = bpy.context.scene
for c in bpy.data.collections:
    if c.name in ('Labels',):
        for o in c.all_objects:
            if o: o.hide_render = True
sc.render.resolution_x, sc.render.resolution_y = 1200, 1200; sc.cycles.samples = 24
for g in L['gates']:
    if g['id'] not in ('G1', 'G2', 'G4'): continue
    cd = bpy.data.cameras.new('T'); cd.type = 'ORTHO'; cd.ortho_scale = 16
    cam = bpy.data.objects.new('TopGate', cd); sc.collection.objects.link(cam)
    cam.location = (g['pos'][0], g['pos'][1], 60); cam.rotation_euler = (0, 0, math.radians(g.get('heading', 90) - 90))
    sc.camera = cam; sc.render.filepath = os.path.join(out, f"top_{g['id']}.png"); bpy.ops.render.render(write_still=True)
print('TOP_OK')
