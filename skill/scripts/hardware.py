# parking-site-3d: hardware library (Blender). Extra models for the device types in hardware_catalog.py.
# build_blender.py calls install(globals()) so these builders can use its helpers (box, cyl, face_cyl, text_mesh,
# mat, M, plinth, vents, link, L ...), then dispatch(BUILDERS) routes each equipment by its 'model'.
# Local frame of every device: +X = heading (the side facing the lane / driver), origin = ground under it.
import math, os
from hardware_catalog import MODELS, default_model

def install(g):
    globals().update({k: v for k, v in g.items() if not k.startswith('__')})
    M.update(
        hw_yellow=mat('HWYellow', (.95, .7, .02), .4),
        hw_white_led=mat('WhiteLed', (.9, .9, .9), .2, emit=(1, 1, .95), estr=3.),
        hw_rib=mat('ContainerSteel', (.75, .77, .78), .45, .4),
        hw_alu=mat('AluProfile', (.86, .87, .88), .3, .6),
        hw_green=mat('SignalGreen', (.02, .3, .05), .3, emit=(.1, 1, .25), estr=4.),
        slip=mat('SlipPaper', (.95, .95, .93), .6),
        wood=mat('DeskTop', (.45, .33, .22), .5),
        chair=mat('ChairFabric', (.08, .08, .1), .8),
        kiosk_white=mat('KioskWhite', (.86, .87, .88), .35),
        panel_black=mat('PanelBlack', (.012, .012, .013), .7),        # near-black + matte: the web viewer's environment light otherwise greys it       # matches the dark grey of the printed artwork
        screen_white=mat('ScreenWhite', (.9, .9, .9), .25, emit=(1, 1, 1), estr=.7),
        label_white=mat('LabelWhite', (.95, .95, .95), .4),
    )
    g_ = mat('BoothClearGlass', (.93, .97, .97), .02)          # clear glazing: transmission, no refraction (thin panes)
    b_ = g_.node_tree.nodes.get('Principled BSDF')
    for k, v in (('Transmission Weight', 1.0), ('IOR', 1.05), ('Alpha', .35)):
        if k in b_.inputs: b_.inputs[k].default_value = v
    M['clear_glass'] = g_

# ------------------------------------------------------------------ barrier booms (cabinet, LEDs, rest post, cones stay in build_barrier)
def stripes_on(parent, x0, length, h, z, name, w=.052):
    """Red reflective chevron stickers on a rectangular boom (both faces)."""
    n = max(2, int(length / .45))
    for i in range(0, n, 2):
        box(f'{name}St{i}', (length / n * .9, w + .004, h * .8), (x0 + (i + .5) * length / n, 0, z), M['reflect'], parent, bevel=0)

BARRIER_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'creative_barrier')
BOOM_H, BOOM_W = .1, .04                      # CREATIVE boom: white rectangular profile 100 x 40 mm

def creative_barrier_cabinet(r, beacon, led):
    """CREATIVE barrier cabinet (company product renders): charcoal body ~1.0 m with chamfered vertical edges,
    slightly wider rounded charcoal top cap, silver panel on both traffic faces (+/-Y) with a status LED dot,
    white P badge and vertical CREATIVE; small vent slots on the side. Arm pivot sits just under the cap on +X."""
    charcoal = M['panel_black']                   # near-black matte (viewer damps its reflections, so it stays dark)
    body = box('Cabinet', (.34, .28, 1.07), (0, 0, .08), charcoal, r, bevel=0)
    soften(body, .03, 4)                                                    # one flush body, all edges rounded (no overhanging cap)
    cyl('ShaftBoss', .035, .06, (.165, 0, 1.01), charcoal, r, rot=(0, math.pi / 2, 0), seg=24)   # gearbox output to the arm hub
    # base: steel mounting plate bolted to the concrete pad, charcoal kick band where the cabinet meets it
    box('BasePlate', (.44, .38, .012), (0, 0, .08), M['steel'], r, bevel=.003)
    for corner_x in (-.19, .19):
        for corner_y in (-.16, .16):
            cyl('BaseBolt', .011, .022, (corner_x, corner_y, .092), M['steel'], r, seg=6)
            cyl('BaseWasher', .018, .004, (corner_x, corner_y, .092), M['steel'], r, seg=16)
    soften(box('Kick', (.352, .292, .045), (0, 0, .092), charcoal, r, bevel=0), .01, 1)
    for side in (-1, 1):                                                    # silver panel + art on both faces
        plate = box(f'Panel{side}', (.26, .004, .92), (-.005, side * .14, .13), M['hw_alu'], r, bevel=0)
        art = decal(f'PanelArt{side}', 'panel.png', .26, .92, (-.005, side * .1425, .59), r, folder=BARRIER_ART)
        art.rotation_euler = (0, 0, side * math.pi / 2)
        flat_disc(f'StatusDot{side}', .011, .003, (-.005, side * .1435, .96), beacon, r, axis='y', segments=20)
    for k in range(7):                                                      # vent slots on the -X side
        box(f'Vent{k}', (.004, .006, .022), (-.171, .1, .62 + k * .03), M['vent'], r, bevel=0)

def boom_clamp(piv):
    """Arm root: black clamp block around the boom where it leaves the cabinet, bolted, on a round drive-shaft hub
    (moves with the arm)."""
    soften(box('ArmClamp', (.17, BOOM_W + .03, BOOM_H + .03), (.075, 0, -BOOM_H - .015), M['panel_black'], piv, bevel=0), .01, 2)
    for side in (-1, 1):
        cyl(f'ShaftHub{side}', .045, .012, (.0, side * (BOOM_W / 2 + .021), -BOOM_H / 2), M['panel_black'], piv,
            rot=(-side * math.pi / 2, 0, 0), seg=28)
        cyl(f'ShaftNut{side}', .016, .008, (.0, side * (BOOM_W / 2 + .033), -BOOM_H / 2), M['steel'], piv,
            rot=(-side * math.pi / 2, 0, 0), seg=6)
        for bolt_x in (.09, .14):
            for bolt_z in (-.025, -.075):
                cyl(f'ClampBolt{side}{bolt_x}{bolt_z}', .006, .004, (bolt_x, side * (BOOM_W / 2 + .016), bolt_z), M['steel'], piv,
                    rot=(-side * math.pi / 2, 0, 0), seg=8)

def boom_stripes(parent, start, length, name):
    """Short red reflective bars on both faces of the white boom, about every 0.5 m (as on the product)."""
    count = max(2, int(length / .5))
    for k in range(count):
        centre = start + (k + .5) * length / count
        box(f'{name}Red{k}', (.2, BOOM_W + .002, .032), (centre, 0, -BOOM_H / 2 - .016), M['reflect'], parent, bevel=0)

def arm_creative(e, piv, L_, led):
    """Straight CREATIVE boom: white rectangular profile, red bars, black end cap."""
    boom_clamp(piv)
    box('Boom', (L_, BOOM_W, BOOM_H), (.03 + L_ / 2, 0, -BOOM_H), M['white'], piv, bevel=.006)
    boom_stripes(piv, .15, L_ - .2, 'Boom')
    box('EndCap', (.02, BOOM_W + .006, BOOM_H + .006), (.03 + L_ + .01, 0, -BOOM_H - .003), M['black'], piv, bevel=.004)

def arm_folding(e, piv, L_, led):
    """CREATIVE folding (articulated) 90° boom for low ceilings (product render): two white sections with red bars.
    Knuckle: a pointed silver gusset plate on each face, pinned at the top corner of the inner section and bolted
    (4 black bolts) onto the start of the outer section, which sits a little higher and starts beside the inner one;
    the inner section's end is rounded. A thin silver rod runs parallel to the inner section on its lower side (inside
    the fold) from the cabinet to a small bracket under the plate: the four-bar that keeps the outer section level.
    Inner section hangs off ARM_<id>; the outer off ARM2_<id> (viewer counter-rotates it). ARM2's origin = hinge pin."""
    boom_clamp(piv)
    L1 = round(L_ * .42, 2); L2 = L_ - L1
    knuckle = .03 + L1                                      # hinge pin: top corner of the inner section's far end
    box('BoomA', (knuckle - .03, BOOM_W, BOOM_H), ((.03 + knuckle) / 2, 0, -BOOM_H), M['white'], piv, bevel=.006)
    boom_stripes(piv, .15, L1 - .35, 'A')
    # parallelogram rod: pivots on a fixed point of the cabinet (main shaft + offset), top pinned to the gusset at the
    # same offset from the fold axis, so it stays attached at every angle. ROD_<id> turns with the arm in the viewer.
    offset_x, offset_z = .13, -.13                           # below the inner section when closed, beside it when open
    rod_pivot = bpy.data.objects.new(f"ROD_{e['id']}", None); link(rod_pivot, 'Equipment'); rod_pivot.parent = piv.parent
    rod_y = BOOM_W / 2 + .042                                # in front of the clamp and hubs
    rod_pivot.location = (piv.location.x + offset_x, rod_y, piv.location.z + offset_z)
    # fixed bracket on the cabinet that carries the rod's lower pivot
    bracket_length = math.hypot(offset_x + .05, offset_z); bracket_angle = math.atan2(-offset_z, offset_x + .05)
    box('RodMount', (bracket_length, .01, .04), (piv.location.x - .05 + (offset_x + .05) / 2, rod_y - .012, piv.location.z + offset_z / 2 - .02),
        M['panel_black'], piv.parent, rot=(0, bracket_angle, 0), bevel=.004)
    rod_length = math.hypot(knuckle, BOOM_H / 2); rod_angle = math.atan2(BOOM_H / 2, knuckle)
    cyl('LinkRod', .0065, rod_length, (0, 0, 0), M['hw_alu'], rod_pivot, rot=(0, math.pi / 2 + rod_angle, 0), seg=14)
    cyl('LinkFoot', .014, .03, (-.015, 0, 0), M['dark'], rod_pivot, rot=(0, math.pi / 2, 0), seg=16)
    j = bpy.data.objects.new(f"ARM2_{e['id']}", None); link(j, 'Equipment'); j.parent = piv; j.location = (knuckle, 0, -BOOM_H / 2)   # fold axis on the boom centreline: closed = straight
    # gusset plate outline in the ARM2 frame (x along the outer section, z up when open): pin nose -> top -> outer end
    pin_x, pin_z = -.03, -.025                               # pin drawn at the inner section's outer corner (as in the render)
    gusset = [(pin_x + gx, pin_z + gz) for gx, gz in
              ((-.024, -.006), (-.018, .016), (.06, .066), (.2, .066), (.212, .054), (.212, -.026), (.2, -.036),
               (.15, -.036), (.12, -.05), (.06, -.046), (.0, -.024), (-.016, -.022))]   # wedge: narrow nose at the pin
    for side in (-1, 1):
        near, far = side * (BOOM_W / 2 + .0015), side * (BOOM_W / 2 + .0075)
        side_prism(f'Gusset{side}', gusset, min(near, far), max(near, far), M['hw_alu'], j)
        face_y = side * (BOOM_W / 2 + .0085)
        cyl(f'PinRing{side}', .016, .003, (pin_x, face_y, pin_z), M['steel'], j, rot=(-side * math.pi / 2, 0, 0), seg=20)
        cyl(f'Pin{side}', .009, .005, (pin_x, face_y, pin_z), M['black'], j, rot=(-side * math.pi / 2, 0, 0), seg=16)
        for bolt_x, bolt_z in ((.12, .005), (.165, .005), (.12, -.045), (.165, -.045)):
            cyl(f'Bolt{side}{bolt_x}{bolt_z}', .006, .004, (bolt_x, face_y, bolt_z), M['black'], j, rot=(-side * math.pi / 2, 0, 0), seg=12)
    box('RodBracket', (.026, .032, .08), (offset_x, rod_y - .022, offset_z - .012), M['hw_alu'], j, bevel=.004)   # rod eye under the gusset
    cyl('RodEye', .01, .022, (offset_x, rod_y - .016, offset_z), M['steel'], j, rot=(-math.pi / 2, 0, 0), seg=14)
    outer_start = BOOM_H                                     # outer section begins just beside the inner one
    box('BoomB', (L2 - outer_start, BOOM_W, BOOM_H), ((outer_start + L2) / 2, 0, -BOOM_H / 2), M['white'], j, bevel=.004)
    boom_stripes_at(j, outer_start + .05, L2 - outer_start - .1, 0, 'B')
    box('EndCap', (.02, BOOM_W + .006, BOOM_H + .006), (L2 + .01, 0, -BOOM_H / 2 - .003), M['black'], j, bevel=.004)

def boom_stripes_at(parent, start, length, centre_z, name):
    count = max(2, int(length / .5))
    for k in range(count):
        box(f'{name}Red{k}', (.2, BOOM_W + .002, .032), (start + (k + .5) * length / count, 0, centre_z - .016), M['reflect'], parent, bevel=0)

def arm_led(e, piv, L_, led):
    """Rectangular aluminium boom with a full-length LED light bar on both faces."""
    boom_clamp(piv)
    box('Boom', (L_, .045, .11), (.08 + L_ / 2, 0, -.055), M['white'], piv, bevel=.012)
    for s_ in (-1, 1):
        box(f'LightBar{s_}', (L_ - .08, .004, .05), (.1 + L_ / 2, s_ * .024, -.06), led, piv, bevel=0)
    box('EndCap', (.03, .05, .12), (.08 + L_ + .015, 0, -.06), M['black'], piv, bevel=.006)
    box('Rubber', (L_ - .1, .03, .025), (.1 + L_ / 2, 0, -.125), M['black'], piv, bevel=.004)

ARM_STYLES = dict(straight=arm_creative, folding=arm_folding, led=arm_led)

# ------------------------------------------------------------------ slip dispensers
def slip(parent, x, y, z, name='Slip'):
    """A printed slip sticking out of the printer mouth, curling down a little."""
    box(name + 'A', (.06, .055, .002), (x + .03, y, z), M['slip'], parent, bevel=0)
    box(name + 'B', (.05, .055, .002), (x + .075, y, z - .012), M['slip'], parent, rot=(0, math.radians(28), 0), bevel=0)
    box(name + 'Print', (.04, .03, .0005), (x + .03, y, z + .0012), M['vent'], parent, bevel=0)

def ticket_slim(e, r):
    plinth(r, .42, .42, .08)
    box('Column', (.26, .3, 1.42), (0, 0, .06), M['tdshell'], r, bevel=.03)
    box('Face', (.008, .22, .6), (.131, 0, .72), M['dark'], r, bevel=.004)
    box('Screen', (.004, .16, .1), (.136, 0, 1.17), M['screen'], r, bevel=0)
    box('QR', (.006, .1, .08), (.136, 0, 1.0), M['glass'], r, bevel=0)
    box('QRLed', (.004, .08, .008), (.139, 0, 1.05), M['led_r'], r, bevel=0)
    face_cyl('Tap', .04, .004, (.136, 0, .86), M['acryl'], r, 20)
    box('MouthBezel', (.012, .12, .03), (.137, 0, .77), M['steel'], r, bevel=.004)
    box('Mouth', (.006, .09, .008), (.142, 0, .77), M['black'], r, bevel=0)
    slip(r, .14, 0, .77)
    face_cyl('Btn', .03, .015, (.135, 0, .69), M['led_g'], r, 16)
    box('Cap', (.32, .36, .03), (.02, 0, 1.48), M['navy'], r, bevel=.008)

CREATIVE_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'creative_td')
DUAL_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'creative_dual')
CREATIVE_EXIT_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'creative_exit')
DECAL_MATS = {}
def decal_mat(file_name, glow, folder=None):
    """Material showing one artwork image (glow=True also lights it, for screens)."""
    folder = folder or CREATIVE_ART
    key = (folder, file_name, glow)
    if key in DECAL_MATS: return DECAL_MATS[key]
    m = bpy.data.materials.new('Art_' + os.path.splitext(file_name)[0]); m.use_nodes = True
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    image_node = nt.nodes.new('ShaderNodeTexImage')
    image_node.image = bpy.data.images.load(os.path.abspath(os.path.join(folder, file_name)), check_existing=True)
    nt.links.new(image_node.outputs['Color'], bsdf.inputs['Base Color'])
    if image_node.image.depth == 32 or image_node.image.channels == 4:      # white-on-transparent artwork: show the panel through
        nt.links.new(image_node.outputs['Alpha'], bsdf.inputs['Alpha'])
        if hasattr(m, 'surface_render_method'): m.surface_render_method = 'BLENDED'
        nt.links.new(image_node.outputs['Color'], bsdf.inputs['Emission Color'])     # white print stays bright white, not grey
        bsdf.inputs['Emission Strength'].default_value = .35
    bsdf.inputs['Roughness'].default_value = .3 if glow else .5
    if glow:
        nt.links.new(image_node.outputs['Color'], bsdf.inputs['Emission Color']); bsdf.inputs['Emission Strength'].default_value = .6
    DECAL_MATS[key] = m; return m

def decal(name, file_name, size_y, size_z, centre, parent, glow=False, folder=None, uv=(0, 0, 1, 1)):
    """Flat picture facing +X (the lane side), centred at `centre`; `uv` = (u0, v0, u1, v1) part of the image to show."""
    bm = bmesh.new()
    corners = [(-size_y / 2, -size_z / 2), (size_y / 2, -size_z / 2), (size_y / 2, size_z / 2), (-size_y / 2, size_z / 2)]
    verts = [bm.verts.new((0, cy_, cz_)) for cy_, cz_ in corners]
    face = bm.faces.new(verts); uv_layer = bm.loops.layers.uv.new()
    u0, v0, u1, v1 = uv
    for loop, corner in zip(face.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))): loop[uv_layer].uv = corner
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(decal_mat(file_name, glow, folder))
    o = link(bpy.data.objects.new(name, me), 'Equipment'); o.location = centre; o.parent = parent
    return o

def creative_cabinet(r, screen_file, screen_folder=None, screen_size=(.2, .137)):
    """Shared CREATIVE kiosk body (slip dispenser and Kiosk Exit): white cabinet ~1.45 m, black front panel,
    recessed screen with camera above, CREATIVE logo, intercom with 'ติดต่อเจ้าหน้าที่' label, vents, side door.
    Returns (face_x, at) so each model adds its own lower panel: face_x = front of the black panel, at(z) = height."""
    base = .08
    plinth(r, .6, .62, base)
    white, black = M['kiosk_white'], M['panel_black']
    depth, width = .4, .46
    box('Body', (depth, width - .03, .72), (0, 0, base), white, r, bevel=.01)                  # lower cabinet
    box('Upper', (depth, width, .68), (0, 0, base + .7), white, r, bevel=.01)                  # upper cabinet behind panel
    box('TopCap', (depth + .03, width + .01, .025), (.01, 0, base + 1.37), white, r, bevel=.006)
    face_x = depth / 2 + .03                                                                   # front of the black panel
    # Artwork is cropped from the company photo (assets/creative_td/*.png). Positions measured on that photo
    # at 0.6 mm per pixel; z values below are centres above the plinth top.
    def at(z): return base + z
    # black front panel (0.04 m thick) built as a frame around a tapered pocket for the screen and camera
    panel_x = depth / 2 + .01; half_w = (width + .01) / 2; thick = .04
    # measured on the flattened Kiosk Exit photo (800 x 1100 px = 0.47 x 0.66 m): opening x 92-560 px, y 140-615 px
    hole_y0, hole_y1, hole_z0, hole_z1 = -.181, .094, at(1.001), at(1.286)
    recess_depth = .028; back_x = face_x - recess_depth             # back plate must stay in front of the white cabinet (x = depth / 2)
    def panel_piece(name, y0, y1, z0, z1):
        box(name, (thick, y1 - y0, z1 - z0), (panel_x, (y0 + y1) / 2, z0), black, r, bevel=0)
    panel_piece('PanelBelow', -half_w, half_w, at(.71), hole_z0)
    panel_piece('PanelAbove', -half_w, half_w, hole_z1, at(1.37))
    panel_piece('PanelLeft', -half_w, hole_y0, hole_z0, hole_z1)
    panel_piece('PanelRight', hole_y1, half_w, hole_z0, hole_z1)
    # pocket = trapezoid in section: left wall and floor straight (screen sits flush there); the top (hood over the
    # camera) and the right wall slope inward, so the back plate is smaller than the front opening, as on the unit
    back_y1, back_z1 = .054, hole_z1 - .02
    pocket = bmesh.new()
    front = [pocket.verts.new((face_x, y_, z_)) for y_, z_ in ((hole_y0, hole_z0), (hole_y1, hole_z0), (hole_y1, hole_z1), (hole_y0, hole_z1))]
    back = [pocket.verts.new((back_x, y_, z_)) for y_, z_ in ((hole_y0, hole_z0), (back_y1, hole_z0), (back_y1, back_z1), (hole_y0, back_z1))]
    pocket.faces.new([back[0], back[1], back[2], back[3]])                       # back plate, facing the lane
    for i in range(4):                                                           # four walls, facing into the pocket
        j = (i + 1) % 4
        pocket.faces.new([front[i], back[i], back[j], front[j]])
    bmesh.ops.recalc_face_normals(pocket, faces=pocket.faces)
    for face in pocket.faces: face.normal_flip()                                  # normals point into the opening (toward the viewer)
    pocket_mesh = bpy.data.meshes.new('ScreenPocket'); pocket.to_mesh(pocket_mesh); pocket.free()
    pocket_mesh.materials.append(M['black'])
    pocket_object = link(bpy.data.objects.new('ScreenPocket', pocket_mesh), 'Equipment'); pocket_object.parent = r
    # camera on the recess back: flat round grey housing, rounded lens window, small black lens
    cam_y, cam_z = -.060, at(1.243)
    housing = face_cyl('CamHousing', .022, .003, (back_x - .001, cam_y, cam_z), mat('CamGrey', (.09, .09, .095), .5), r, 40)
    for polygon in housing.data.polygons: polygon.use_smooth = False
    box('CamWindow', (.002, .011, .02), (back_x + .002, cam_y, cam_z - .01), M['vent'], r, bevel=.003)
    face_cyl('CamLens', .0035, .002, (back_x + .003, cam_y, cam_z), M['black'], r, 16)
    # screen on the recess back, at the LEFT of the recess (left edges line up; open space on the right),
    # about 19 mm behind the panel face. Bezel x 95-470 px, lit area x 108-470 / y 327-555 px on the flat photo.
    box('ScreenBezel', (.006, .225, .18), (back_x, -.068, at(1.104) - .09), M['dark'], r, bevel=.003)
    decal('Screen', screen_file, screen_size[0], screen_size[1], (back_x + .0065, -.065, at(1.105)), r, glow=True, folder=screen_folder)
    decal('Logo', 'logo.png', .12, .027, (face_x + .001, width / 2 - .012 - .06, at(1.335)), r)    # top-right corner, straightened
    # intercom (right/top): label, mounting bracket, silver body, dome camera, 3 red LEDs, speaker, button, name plate
    decal('HelpLabel', 'help.png', .076, .032, (face_x + .001, .164, at(1.142)), r)                 # centred above the intercom
    box('Intercom', (.035, .087, .122), (face_x + .0175, .164, at(1.0)), M['hw_alu'], r, bevel=.006)
    ix = face_x + .035
    cyl('DomeBase', .024, .006, (ix, .164, at(1.085)), M['dark'], r, rot=(0, math.pi / 2, 0), seg=24)          # centred on the body
    cyl('Dome', .021, .016, (ix + .006, .164, at(1.085)), M['black'], r, rot=(0, math.pi / 2, 0), r2=.012, seg=24)
    for led_y in (.156, .164, .172):
        face_cyl(f'IcLed{led_y}', .0018, .003, (ix, led_y, at(1.052)), M['led_r'], r, 8)
    # speaker: a grid of small holes (dots), not lines
    for row in range(3):
        for column in range(10):                       # ends at y .175, leaving a clear gap before the button
            box(f'IcHole{row}_{column}', (.0008, .0012, .0012), (ix, .148 + column * .003, at(1.0285) + row * .0026), M['vent'], r, bevel=0)
    # call button: flush with the face, just a thin dark ring outline
    for part in (face_cyl('IcBtnRing', .006, .0006, (ix, .191, at(1.031)), M['dark'], r, 32),
                 face_cyl('IcBtn', .0052, .0008, (ix, .191, at(1.031)), M['hw_alu'], r, 32)):
        for polygon in part.data.polygons: polygon.use_smooth = False                                               # flat, not domed
    box('IcNamePlate', (.002, .031, .01), (ix, .161, at(1.016)), M['label_white'], r, bevel=0)
    # lower body: vents under the panel, side door with two hinge blocks (on the -Y side)
    for group_y in (-.08, .1):
        for i in range(4):
            box(f'Vent{group_y}{i}', (.004, .06, .006), (depth / 2 + .002, group_y, base + .6 + i * .016), M['vent'], r, bevel=0)
    box('DoorSeamTop', (.36, .004, .004), (0, -width / 2 + .013, base + 1.36), M['vent'], r, bevel=0)
    box('DoorSeamFront', (.004, .004, 1.3), (.17, -width / 2 + .013, base + .06), M['vent'], r, bevel=0)
    for hinge_z in (base + .25, base + 1.15):
        box(f'Hinge{hinge_z:.2f}', (.07, .03, .14), (.13, -width / 2 - .002, hinge_z), white, r, bevel=.006)
    return face_x, at

def ticket_creative(e, r):
    """Company slip dispenser (CREATIVE): shared cabinet + (1) No Touch contactless reader, (2) slip slot,
    white MEMBER plate with QR scanner window."""
    face_x, at = creative_cabinet(r, 'screen.png')
    # (1) contactless reader, (2) slip slot, slip icon: printed artwork + raised 3D parts on top of it (left/bottom)
    decal('Graphics', 'graphics.png', .235, .216, (face_x + .001, -.036, at(.866)), r)
    # printed reader disc and slot bezel are cleared from graphics.png; these 3D parts sit exactly where they were
    reader_y, reader_z = -.0186, at(.941)
    for part in (face_cyl('ReaderRing', .025, .002, (face_x + .001, reader_y, reader_z), M['label_white'], r, 48),   # flat white disc
                 face_cyl('Reader', .0105, .007, (face_x + .001, reader_y, reader_z), M['black'], r, 40)):          # small black button
        for polygon in part.data.polygons: polygon.use_smooth = False                                               # flat faces, no donut shading
    slot_y, slot_z = -.018, at(.867)
    box('SlotBezel', (.012, .1, .044), (face_x, slot_y, slot_z - .022), M['hw_alu'], r, bevel=.003)
    box('SlotLip', (.01, .07, .006), (face_x + .008, slot_y, slot_z + .002), M['hw_alu'], r, bevel=.002)
    box('Slot', (.004, .066, .004), (face_x + .012, slot_y, slot_z - .002), M['black'], r, bevel=0)
    # MEMBER plate with QR scanner window (right/bottom)
    box('MemberPlate', (.004, .085, .228), (face_x, .155, at(.874) - .114), M['label_white'], r, bevel=.004)
    decal('MemberArt', 'member.png', .085, .228, (face_x + .0045, .155, at(.874)), r)

def ticket_creative_exit(e, r):
    """Company Kiosk Exit (CREATIVE): shared cabinet; screen shows plate / entry time / duration / fee + PromptPay QR;
    white L-shaped plate '(1) สแกนคิวอาร์โค้ดบัตรจอดรถ' with the ticket QR scanner; (2) receipt slot + receipt icon.
    Artwork: assets/creative_exit (make_art.py flattens the photo to 800 x 1100 px = 0.47 x 0.66 m panel)."""
    face_x, at = creative_cabinet(r, 'screen.png', CREATIVE_EXIT_ART, screen_size=(.2125, .137))
    art = CREATIVE_EXIT_ART
    decal('ExitPlate', 'plate.png', .4436, .2472, (face_x + .001, .0103, at(.8564)), r, folder=art)      # white L plate, printed
    box('ExitScanGlass', (.002, .0435, .052), (face_x + .0015, .1555, at(.911) - .026), M['hw_alu'], r, bevel=0)
    decal('ExitLower', 'lower.png', .2115, .15, (face_x + .001, -.0823, at(.809)), r, folder=art)        # (2) + receipt icon
    slot_y, slot_z = -.038, at(.852)
    box('SlotBezel', (.012, .116, .054), (face_x, slot_y, slot_z - .027), M['hw_alu'], r, bevel=.003)
    box('SlotLip', (.01, .08, .007), (face_x + .008, slot_y, slot_z + .003), M['hw_alu'], r, bevel=.002)
    box('Slot', (.004, .074, .004), (face_x + .012, slot_y, slot_z - .001), M['black'], r, bevel=0)

# ------------------------------------------------------------------ LPR camera DHI-ITC413-PW4D (company drawing 2569/2/13, mm)
LPR_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'lpr_itc413')

def side_prism(name, outline, y_min, y_max, material, parent):
    """Solid made by extruding a side-view outline (list of (x, z) points, in order) across y_min..y_max."""
    mesh_builder = bmesh.new()
    near = [mesh_builder.verts.new((x_, y_min, z_)) for x_, z_ in outline]
    far = [mesh_builder.verts.new((x_, y_max, z_)) for x_, z_ in outline]
    mesh_builder.faces.new(near); mesh_builder.faces.new(list(reversed(far)))
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        mesh_builder.faces.new([near[i], near[j], far[j], far[i]])
    bmesh.ops.recalc_face_normals(mesh_builder, faces=mesh_builder.faces)
    mesh = bpy.data.meshes.new(name); mesh_builder.to_mesh(mesh); mesh_builder.free(); mesh.materials.append(material)
    solid = link(bpy.data.objects.new(name, mesh), 'Equipment'); solid.parent = parent
    return solid

def soften(part, width, segments=4, clamp=True):
    """Rounded edges that also reach the web model (the plain box() bevel is render-only).
    clamp=False lets long edges round fully even where the outline has short segments."""
    bevel = part.modifiers.get('Bevel') or part.modifiers.new('Bevel', 'BEVEL')
    bevel.width = width; bevel.segments = segments; bevel.limit_method = 'ANGLE'; bevel.show_viewport = True
    bevel.use_clamp_overlap = clamp
    bevel.harden_normals = True
    for polygon in part.data.polygons: polygon.use_smooth = True
    return part

def flat_disc(name, radius, thickness, location, material, parent, axis='x', segments=32):
    """Thin flat disc (flush cap / LED), flat-shaded so it does not look domed."""
    disc = cyl(name, radius, thickness, location, material, parent,
               rot=(0, math.pi / 2, 0) if axis == 'x' else (math.pi / 2, 0, 0), seg=segments)
    for polygon in disc.data.polygons: polygon.use_smooth = False
    return disc

def camera_body(name, point, material, parent, half_width=.0505, bottom_radius=.024, top_radius=.006, corner_steps=8):
    """ITC413 black body lofted from rounded cross-sections (front-view outline), so the long bottom edges are as round
    as the drawing. point(back_mm, depth_mm) -> (x, z). Top steps down 29 -> 51 mm between 129 and 165 mm back;
    bottom at 104 mm; the front face leans back (41 -> 59 mm over the height); front/back edges get a small round-over."""
    def top_depth(back_mm):
        if back_mm <= 129: return 29
        if back_mm >= 165: return 51
        return 29 + (back_mm - 129) * 22 / 36
    def section(top_mm, bottom_mm, inset_mm):
        """Rounded rectangle in (y, depth_mm), clockwise from the top right; same vertex count for every ring."""
        width = half_width - inset_mm / 1000; bottom = bottom_mm - inset_mm
        outline = []
        for corner_y, corner_d, radius, start in ((width, top_mm, top_radius, 90), (width, bottom, bottom_radius, 0),
                                                  (-width, bottom, bottom_radius, -90), (-width, top_mm, top_radius, 180)):
            centre_y = corner_y - math.copysign(radius, corner_y)
            centre_d = corner_d + (radius * 1000 if corner_d == top_mm else -radius * 1000)
            for step in range(corner_steps + 1):
                angle = math.radians(start - 90 * step / corner_steps)
                outline.append((centre_y + radius * math.cos(angle), centre_d - radius * 1000 * math.sin(angle)))
        return outline
    def front_back(depth_mm): return 41 + (depth_mm - 29) * 18 / 75          # sloped front face
    rings = []                                                                 # each ring: list of (back_mm, y, depth_mm)
    for offset, inset in ((0, 3), (4, 0)):                                     # rounded front edge
        rings.append([(front_back(d) + offset, y_, d) for y_, d in section(29, 104, inset)])
    for back_mm in (129, 140, 152, 165, 258):
        rings.append([(back_mm, y_, d) for y_, d in section(top_depth(back_mm), 104, 0)])
    rings.append([(262, y_, d) for y_, d in section(51, 104, 3)])             # rounded back edge
    mesh_builder = bmesh.new()
    vertex_rings = []
    for ring in rings:
        vertex_rings.append([mesh_builder.verts.new((point(b, d)[0], y_, point(b, d)[1])) for b, y_, d in ring])
    count = len(vertex_rings[0])
    for near, far in zip(vertex_rings, vertex_rings[1:]):
        for i in range(count):
            j = (i + 1) % count
            mesh_builder.faces.new([near[i], near[j], far[j], far[i]])
    mesh_builder.faces.new(vertex_rings[0]); mesh_builder.faces.new(list(reversed(vertex_rings[-1])))
    bmesh.ops.recalc_face_normals(mesh_builder, faces=mesh_builder.faces)
    mesh = bpy.data.meshes.new(name); mesh_builder.to_mesh(mesh); mesh_builder.free(); mesh.materials.append(material)
    for polygon in mesh.polygons: polygon.use_smooth = True
    try: mesh.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    body = link(bpy.data.objects.new(name, mesh), 'Equipment'); body.parent = parent
    return body

def lpr_itc413(parent, tilt_degrees=7, name='ITC'):
    """Dahua DHI-ITC413-PW4D ANPR camera, shaped from the CREATIVE drawing (2569/2/13, mm), all four views.
    Local frame: origin = back (mounting) face of the junction box at its centre, +X = viewing direction.
    Overall 395 mm: junction box 56 deep x 123 wide x 111 high (screwed flat to the post, never tilted),
    arm 74 mm, camera 266 long x 105 high. The camera tilts down at the plate from the ball joint, not the box.
    Side view: black body taller at the front, stepping down along a diagonal toward the rear; front face leans back
    at the bottom; silver sun hood over the top, overhanging the front, side panels following the step.
    Edges are rounded (body, hood, box). Black-and-white CIT logo on the hood's right side, toward the rear."""
    hood = mat('ITCHood', (.52, .55, .70), .35)
    box_grey = mat('ITCBoxGrey', (.42, .43, .45), .45)
    body_black = mat('ITCBody', (.025, .025, .028), .45)
    # junction box: rounded grey box flat against the post, flush screw caps, top/bottom mounting tabs
    soften(box(name + 'JBox', (.056, .123, .111), (.028, 0, -.0555), box_grey, parent), .012)
    for side in (-1, 1):
        flat_disc(name + f'Cap{side}', .014, .0015, (.03, side * .0615, -.002), M['hw_alu'], parent, axis='y')
        box(name + f'Slot{side}', (.003, .0012, .016), (.03, side * .0625, -.01), M['dark'], parent, bevel=0)
    for z_ in (.0555, -.0635):
        soften(box(name + f'Tab{z_}', (.02, .03, .008), (.028, 0, z_), box_grey, parent), .003, 2)
    # arm: round neck from the box, ball joint (the tilt pivot), nearly flush side plug
    cyl(name + 'Neck', .022, .05, (.056, 0, 0), M['hw_alu'], parent, rot=(0, math.pi / 2, 0), seg=32)
    flat_disc(name + 'Plug', .007, .0015, (.09, -.0215, 0), M['dark'], parent, axis='y', segments=20)
    pivot_x = .104
    cyl(name + 'Ball', .017, .02, (pivot_x - .01, 0, 0), M['hw_alu'], parent, rot=(0, math.pi / 2, 0), seg=32)
    aim = bpy.data.objects.new(name + 'Aim', None); link(aim, 'Equipment'); aim.parent = parent
    aim.location = (pivot_x, 0, 0); aim.rotation_euler = (0, math.radians(tilt_degrees), 0)
    cyl(name + 'Nut', .012, .02, (0, 0, 0), M['steel'], aim, rot=(0, math.pi / 2, 0), seg=6)
    # side-view outlines in mm: (distance back from the hood front, depth below the hood top), in the aim frame
    front_x, top_z = .395 - pivot_x, .043
    def point(back_mm, depth_mm): return (front_x - back_mm / 1000, top_z - depth_mm / 1000)
    body_outline = [point(41, 29), point(129, 29), point(165, 51), point(258, 51), point(262, 56), point(262, 92),
                    point(255, 101), point(245, 104), point(62, 104), point(59, 101)]
    camera_body(name + 'Body', point, body_black, aim)
    hood_outline = [point(0, 4), point(2, 0), point(266, 0), point(266, 51), point(165, 51), point(129, 29),
                    point(41, 29), point(10, 29), point(3, 24), point(0, 15)]
    soften(side_prism(name + 'Hood', list(reversed(hood_outline)), -.0575, .0575, hood, aim), .006)
    soften(box(name + 'Badge', (.04, .02, .003), (front_x - .11, 0, top_z), M['dark'], aim), .006, 3)
    soften(box(name + 'Lug', (.015, .02, .01), (front_x - .092, 0, top_z - .114), M['hw_alu'], aim), .003, 2)
    # black-and-white CIT logo on the hood's right side (camera's right = -Y), toward the rear
    logo = decal(name + 'CitLogo', 'cit_logo_mono.png', .1, .0193, (front_x - .2, -.0579, top_z - .024), aim, folder=LPR_ART)
    logo.rotation_euler = (0, 0, -math.pi / 2)
    # front face leans back at the bottom (41 -> 59 mm over 75 mm): window, lens, flush IR LEDs on that slope
    face = bpy.data.objects.new(name + 'Front', None); link(face, 'Equipment'); face.parent = aim
    slope = math.atan2(18, 75)
    face.location = (front_x - .05, 0, top_z - .0665); face.rotation_euler = (0, slope, 0)
    soften(box(name + 'WindowFrame', (.002, .075, .052), (.0005, 0, -.0183), M['vent'], face), .008, 3)
    soften(box(name + 'Window', (.003, .066, .044), (.001, 0, -.0143), M['dark'], face), .006, 3)
    flat_disc(name + 'LensBarrel', .013, .004, (.002, 0, .0077), M['black'], face)
    flat_disc(name + 'LensGlass', .008, .002, (.005, 0, .0077), M['glass'], face)
    for k in range(4):                                               # IR LEDs: flush white discs, not domes
        flat_disc(name + f'IR{k}', .0045, .0008, (.0005, -.027 + k * .018, -.027), M['hw_white_led'], face, segments=24)
    # 'Lens' marker for check_lpr.py: at the lens, in the aim frame (so its +X is the camera's line of sight)
    lens_marker = bpy.data.objects.new('Lens' + name, None); link(lens_marker, 'Equipment'); lens_marker.parent = aim
    lens_marker.location = (face.location.x + .006 * math.cos(slope) + .0077 * math.sin(slope), 0,
                            face.location.z - .006 * math.sin(slope) + .0077 * math.cos(slope))

def lpr_post(r, height):
    """Lane-side post: footing pad, base plate with 4 bolts, 80 mm square post, cap."""
    plinth(r, .36, .36, .08)
    box('BasePlate', (.22, .22, .015), (0, 0, .06), M['steel'], r, bevel=.004)
    for xx in (-.08, .08):
        for yy in (-.08, .08): cyl('Bolt', .01, .03, (xx, yy, .075), M['steel'], r, seg=8)
    box('Post', (.08, .08, height), (0, 0, .075), M['tdshell'], r, bevel=.01)
    box('PostCap', (.1, .1, .02), (0, 0, .075 + height), M['navy'], r, bevel=.005)

def lpr_mount(e, r, z):
    """ITC413 junction box screwed flat to the post face that looks along the camera heading; the camera itself
    tilts down at the plate from its ball joint."""
    head = bpy.data.objects.new('LPR_Head', None); link(head, 'Equipment'); head.parent = r
    head.location = (.04, 0, z)
    lpr_itc413(head, e.get('tilt', 7))

def lpr_round_post(r, height, radius=.045):
    """Round black pole on a flared foot and round base plate (company LED-sign unit), domed top cap."""
    pole_black = M['panel_black']
    plinth(r, .36, .36, .08)                                   # concrete pad (same as the old post), top at 0.06
    cyl('BasePlate', .165, .012, (0, 0, .06), pole_black, r, seg=40)
    cyl('Foot', .1, .1, (0, 0, .072), pole_black, r, r2=radius + .006, seg=40)
    cyl('Pole', radius, height - .08, (0, 0, .17), pole_black, r, seg=32)
    cyl('PoleCap', radius + .004, .03, (0, 0, .09 + height), pole_black, r, seg=32)
    for angle in range(4):
        corner = math.radians(45 + angle * 90)
        cyl('BaseBolt', .01, .014, (.13 * math.cos(corner), .13 * math.sin(corner), .072), M['steel'], r, seg=6)

def lpr_sign(e, r):
    """LPR with LED sign (lane default), from the company render: DHI-ITC413-PW4D at the top of a round black pole,
    charcoal LED sign on the pole below it facing the driver: black screen with four lines (red message, green plate,
    date, member type), round reader below the screen and three white LEDs at the bottom."""
    lpr_round_post(r, 1.5)
    lpr_mount(e, r, 1.52)
    sign = bpy.data.objects.new('LPR_Display', None); link(sign, 'Equipment'); sign.parent = r
    sign.rotation_euler = (0, 0, math.radians(e.get('display_yaw', 0))); shift = e.get('display_shift', 0)
    width, height, depth, bottom = .42, .56, .09, .8
    charcoal = mat('SignCharcoal', (.07, .07, .075), .5)
    red = mat('SignRed', (1, 0, 0), .4, emit=(1, 0, 0), estr=1.6)
    green = mat('SignGreen', (0, 1, 0), .4, emit=(.05, 1, .05), estr=1.4)
    bold = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', 'tahomabd.ttf')   # bold, has Thai glyphs
    front = .045 + depth
    box('DispBracket', (.05, .1, .3), (.07, shift * .5, bottom + .12), charcoal, sign, bevel=0)
    soften(box('DispBox', (depth, width, height), (.045 + depth / 2, shift, bottom), charcoal, sign, bevel=0), .018, 3)
    screen_width, screen_height = .34, .37
    screen_bottom = bottom + height - .04 - screen_height
    box('DispBezel', (.003, screen_width + .03, screen_height + .03), (front, shift, screen_bottom - .015), M['black'], sign, bevel=.002)
    box('DispFace', (.004, screen_width, screen_height), (front + .001, shift, screen_bottom), M['screen_black'] if 'screen_black' in M else M['black'], sign, bevel=0)
    face_cyl('DispTopDot', .005, .003, (front, shift, bottom + height - .02), M['black'], sign, 12)
    lines = ((e.get('message', 'Welcome'), red, False), (e.get('plate', 'กข1234'), green, True),
             (e.get('date', '2024-01-01'), green, False), (e.get('member', 'GUEST'), green, False))
    line_step = screen_height / 4.3
    for index, (text, material, thai) in enumerate(lines):
        line = text_mesh(f'DispLine{index}', text, .088, material, sign,
                         (front + .005, shift, screen_bottom + screen_height - line_step * (index + .6)), (math.pi / 2, 0, math.pi / 2), font=bold)
        left_edge = min(vertex.co.x for vertex in line.data.vertices)
        text_width = max(vertex.co.x for vertex in line.data.vertices) - left_edge
        scale = min(1, (screen_width - .03) / text_width)
        line.scale = (scale, scale, 1)
        line.location.y = shift - screen_width / 2 + .015 - left_edge * scale       # left-aligned like the real sign
    face_cyl('DispReader', .034, .003, (front, shift, bottom + .095), mat('SignReader', (.09, .09, .1), .4), sign, 32)
    box('DispLedBar', (.006, .08, .03), (front, shift, bottom + .014), M['kiosk_white'], sign, bevel=.006)
    for k in (-1, 0, 1):
        face_cyl(f'DispLed{k}', .009, .006, (front + .003, shift + k * .022, bottom + .029), M['hw_white_led'], sign, 14)

def lpr_short(e, r):
    """LPR on a short round black pole (same pole as the LED-sign unit, no sign): DHI-ITC413-PW4D at about 1.05 m."""
    lpr_round_post(r, 1.05)
    lpr_mount(e, r, 1.05)

def service_face(parent, name):
    """Tilted service panel used by the dual-height unit: screen, PRESS button, slip mouth + slip, RFID, speaker."""
    box(name + 'Panel', (.012, .4, .46), (0, 0, 0), M['dark'], parent, bevel=.006)
    box(name + 'Screen', (.004, .22, .13), (.008, 0, .13), M['screen'], parent, bevel=0)
    face_cyl(name + 'Ring', .05, .01, (.008, -.1, -.04), M['steel'], parent, 22)
    face_cyl(name + 'Btn', .04, .018, (.008, -.1, -.04), M['led_g'], parent, 22)
    box(name + 'MouthBz', (.014, .14, .035), (.009, .08, -.1), M['steel'], parent, bevel=.004)
    box(name + 'Mouth', (.004, .1, .008), (.016, .08, -.1), M['black'], parent, bevel=0)
    slip(parent, .016, .08, -.1, name + 'Slip')
    face_cyl(name + 'Tap', .035, .004, (.009, .1, .02), M['acryl'], parent, 20)
    for i in range(3):
        for k in range(3): face_cyl(f'{name}Spk{i}{k}', .004, .004, (.008, .13 + i * .018, -.17 + k * .018), M['vent'], parent, 8)

def ticket_creative_dual(e, r):
    """Company 2-tier kiosk (CREATIVE drawing): charcoal lower cabinet 750 x 400 x 1000 on four feet, grey tower to 2.4 m;
    lower tier = PL1000 card reader on a grey frame (car height, ~1.3 m), upper tier = black head with 10-inch screen and
    three white plates (left: scan slip QR, middle: slip out, right: tap RFID card); separate 75 mm post with a
    7-inch screen box at 1.5 m facing the approaching car (-Y)."""
    base = .06                                            # plinth top
    plinth(r, .8, 1.35, .08)
    charcoal = mat('DualCharcoal', (.055, .055, .06), .5)
    grey = mat('DualGrey', (.32, .33, .34), .5)
    black, white = M['panel_black'], M['label_white']
    # four angle feet with base plates, then the lower cabinet (front face at x = .2)
    for fx in (-.17, .17):
        for fy in (-.36, .36):
            box('FootPlate', (.14, .1, .012), (fx, fy + (.03 if fy > 0 else -.03), base), charcoal, r, bevel=0)
            box('FootLeg', (.05, .05, .1), (fx, fy, base), charcoal, r, bevel=.004)
            for bx in (-.045, .045):
                cyl('FootBolt', .008, .012, (fx + bx, fy + (.05 if fy > 0 else -.05), base + .012), M['steel'], r, seg=6)
    box('Cabinet', (.4, .75, .9), (0, 0, base + .1), charcoal, r, bevel=.008)
    for sy in (-1, 1):                                   # corner posts / bolt rows on the front, as on the drawing
        box(f'CabSeam{sy}', (.004, .004, .86), (.201, sy * .2, base + .12), M['vent'], r, bevel=0)
        for bz in (.18, .55, .92):
            face_cyl(f'CabBolt{sy}{bz}', .006, .003, (.201, sy * .34, base + bz), M['steel'], r, 8)
    # grey tower rising out of the cabinet
    box('Tower', (.3, .44, 1.4), (-.02, 0, base + 1.0), grey, r, bevel=.01)
    for sy in (-1, 1):
        box(f'TowerTab{sy}', (.14, .03, .16), (.04, sy * .235, base + 2.0), grey, r, bevel=.008)
        box(f'TowerTabLow{sy}', (.12, .025, .1), (.04, sy * .232, base + 1.42), grey, r, bevel=.008)
    for vy in (-.08, .08):
        for i in range(3):
            box(f'TowerVent{vy}{i}', (.004, .07, .007), (.131, vy, base + 1.75 + i * .018), M['vent'], r, bevel=0)
    # upper tier: black head panel with screen, camera, logo and three white plates
    head_x = .21
    # head panel = frame around a recessed pocket (same depth / sloped camera hood as the Kiosk Entrance)
    hole_y, hole_z0, hole_z1 = .155, base + 2.08, base + 2.35
    def head_piece(name, y0, y1, z0, z1):
        box(name, (.1, y1 - y0, z1 - z0), (.16, (y0 + y1) / 2, z0), black, r, bevel=0)
    head_piece('HeadBelow', -.275, .275, base + 1.82, hole_z0)
    head_piece('HeadAbove', -.275, .275, hole_z1, base + 2.4)
    head_piece('HeadLeft', -.275, -hole_y, hole_z0, hole_z1)
    head_piece('HeadRight', hole_y, .275, hole_z0, hole_z1)
    back_x = head_x - .028; back_z1 = hole_z1 - .02
    pocket = bmesh.new()
    front = [pocket.verts.new((head_x, y_, z_)) for y_, z_ in ((-hole_y, hole_z0), (hole_y, hole_z0), (hole_y, hole_z1), (-hole_y, hole_z1))]
    inset = .02                                                   # back plate smaller on every side: trapezoid in both sections
    back = [pocket.verts.new((back_x, y_, z_)) for y_, z_ in ((-hole_y + inset, hole_z0 + inset), (hole_y - inset, hole_z0 + inset), (hole_y - inset, back_z1), (-hole_y + inset, back_z1))]
    pocket.faces.new(back)
    for k in range(4): pocket.faces.new([front[k], back[k], back[(k + 1) % 4], front[(k + 1) % 4]])
    bmesh.ops.recalc_face_normals(pocket, faces=pocket.faces)
    for face in pocket.faces: face.normal_flip()
    pocket_mesh = bpy.data.meshes.new('HeadPocket'); pocket.to_mesh(pocket_mesh); pocket.free(); pocket_mesh.materials.append(M['black'])
    link(bpy.data.objects.new('HeadPocket', pocket_mesh), 'Equipment').parent = r
    # camera as on the drawing: flat thin ring, small upright rounded body with the lens (no dome)
    head_camera = [face_cyl('HeadCamRing', .013, .002, (back_x, 0, base + 2.3), M['black'], r, 32),
                   face_cyl('HeadCamFace', .0115, .0025, (back_x, 0, base + 2.3), M['dark'], r, 32)]
    box('HeadCamBody', (.0012, .011, .017), (back_x + .003, 0, base + 2.2915), M['black'], r, bevel=.002)
    head_camera.append(face_cyl('HeadCamLens', .0035, .001, (back_x + .0037, 0, base + 2.3), M['dark'], r, 16))
    for part in head_camera:
        for polygon in part.data.polygons: polygon.use_smooth = False
    box('ScreenBezel', (.006, .26, .18), (back_x, 0, base + 2.102), M['dark'], r, bevel=.003)
    decal('Screen', 'screen.png', .24, .164, (back_x + .0065, 0, base + 2.185), r, glow=True)                 # same screen picture as the Kiosk Entrance
    decal('Logo', 'logo.png', .11, .025, (head_x + .001, .19, base + 2.365), r)
    plate_z = base + 1.86; plate_h = .195; plate_w = .13          # 265 x 397 px plate art = 0.13 x 0.195 m
    for name, py in (('Scan', -.16), ('IdCard', 0), ('Rfid', .16)):            # white plates, print from assets/creative_dual
        box(f'{name}Plate', (.004, plate_w, plate_h), (head_x, py, plate_z), white, r, bevel=.004)
        decal(f'{name}Art', f'{name.lower()}.png', plate_w - .004, plate_h - .004, (head_x + .0045, py, plate_z + plate_h / 2), r, folder=DUAL_ART)
    box('IdSlot', (.008, .054, .007), (head_x + .004, 0, plate_z + .126), M['black'], r, bevel=.002)           # middle: ID card slot
    # lower tier: grey frame on the cabinet front holding the PL1000 card reader (265 x 258 x 107)
    box('ReaderFrame', (.06, .4, .42), (.23, 0, base + .96), grey, r, bevel=.006)
    box('Reader', (.107, .265, .258), (.2935, 0, base + 1.04), mat('ReaderGrey', (.155, .157, .163), .45), r, bevel=.008)
    decal('ReaderFace', 'reader.png', .142, .222, (.348, 0, base + 1.04 + .129), r, folder=DUAL_ART)          # black face: CARD READER / waves / ทาบบัตร
    # separate 75 mm post with the 7-inch screen box (330 x 250 x 90) on its lane side, facing out (+X) like the kiosk
    post_x, post_y = .3, .58
    box('PostPlate', (.15, .15, .012), (post_x, post_y, base), charcoal, r, bevel=0)
    box('Post', (.075, .075, 1.5), (post_x, post_y, base), charcoal, r, bevel=.004)
    for gx, gy in ((.05, 0), (-.05, 0), (0, .05), (0, -.05)):
        box('PostGusset', (.012 if gx else .04, .04 if gx else .012, .06), (post_x + gx, post_y + gy, base + .012), charcoal, r, bevel=0)
    screen_x = post_x + .0375 + .045
    box('SmallScreenBox', (.09, .33, .25), (screen_x, post_y, base + 1.25), M['dark'], r, bevel=.008)
    box('SmallBezel', (.004, .2, .13), (screen_x + .045, post_y, base + 1.31), M['black'], r, bevel=.003)
    box('SmallScreen', (.003, .17, .1), (screen_x + .047, post_y, base + 1.325), M['screen'], r, bevel=0)

def ticket_dual(e, r):
    """Dual-height slip dispenser: one tall cabinet, two tilted service faces at car (~1.05 m) and truck (~1.95 m) height."""
    plinth(r, .66, .8)
    shell = M['tdshell']
    box('Body', (.46, .58, 2.25), (-.02, 0, .08), shell, r, bevel=.04)
    box('Kick', (.012, .5, .14), (.212, 0, .1), M['steel'], r, bevel=0)
    box('DoorSeam', (.004, .004, .7), (.213, -.24, .2), M['vent'], r, bevel=0)
    box('Lock', (.012, .035, .035), (.218, .2, .6), M['steel'], r)
    for s_ in (-1, 1):
        for i in range(7): box(f'Vent{s_}{i}', (.18, .004, .012), (-.04, s_ * .292, .3 + i * .03), M['vent'], r, bevel=0)
        box(f'Stripe{s_}', (.44, .004, .05), (-.02, s_ * .292, 1.48), M['navy'], r, bevel=0)
    for name, z in (('Car', 1.05), ('Truck', 1.95)):
        f_ = bpy.data.objects.new(f'TD_{name}Face', None); link(f_, 'Equipment'); f_.parent = r
        f_.location = (.26, 0, z); f_.rotation_euler = (0, math.radians(-15), 0)
        box(f'{name}Housing', (.14, .5, .58), (-.06, 0, -.29), shell, f_, bevel=.03)       # tilted housing, panel on its front
        box(f'{name}Visor', (.2, .54, .025), (-.02, 0, .29), M['navy'], f_, bevel=.006)
        p_ = bpy.data.objects.new(f'TD_{name}Panel', None); link(p_, 'Equipment'); p_.parent = f_; p_.location = (.016, 0, 0)
        service_face(p_, name)
    box('Hood', (.62, .7, .04), (.04, 0, 2.33), M['navy'], r, bevel=.012)
    box('HoodLip', (.03, .7, .08), (.34, 0, 2.27), M['navy'], r, bevel=.006)
    face_cyl('Cam', .016, .015, (.24, 0, 2.2), M['glass'], r, 16)

# ------------------------------------------------------------------ pay stations (CREATIVE)
PAY_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'creative_pay')

def recess_pocket(name, parent, x_front, depth, opening, back, material):
    """Screen recess cut into a panel: walls slope from the front `opening` (at x_front) back to the smaller `back`
    plate `depth` behind it, so the recess is a trapezoid in every section. Rectangles are (y0, y1, z0, z1)."""
    bm = bmesh.new()
    def ring(x, rect):
        y0, y1, z0, z1 = rect
        return [bm.verts.new((x, y_, z_)) for y_, z_ in ((y0, z0), (y1, z0), (y1, z1), (y0, z1))]
    front, rear = ring(x_front, opening), ring(x_front - depth, back)
    bm.faces.new(rear)
    for k in range(4):
        n = (k + 1) % 4
        bm.faces.new([front[k], rear[k], rear[n], front[n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces: face.normal_flip()                                   # normals point out of the recess, at the viewer
    mesh = bpy.data.meshes.new(name); bm.to_mesh(mesh); bm.free(); mesh.materials.append(material)
    o = link(bpy.data.objects.new(name, mesh), 'Equipment'); o.parent = parent
    return o

def art_parts(parent, file_name, image_size, origin, x_face, parts, body):
    """Raised parts cut from a front drawing: each (name, (x0, y0, x1, y1) px, depth, material or None = body) becomes
    a box standing `depth` proud of the face at x_face, with the same drawing region printed on its front.
    origin(px_x, px_y) -> (y, z) of that drawing pixel on the face."""
    width, height = image_size
    for name, (x0, y0, x1, y1), depth, material in parts:
        (y_a, z_top), (y_b, z_bottom) = origin(x0, y0), origin(x1, y1)
        size_y, size_z = y_b - y_a, z_top - z_bottom
        box(name, (depth, size_y, size_z), (x_face + depth / 2, (y_a + y_b) / 2, z_bottom), material or body, parent, bevel=min(.004, depth / 3))
        decal(name + 'Art', file_name, size_y, size_z, (x_face + depth + .0007, (y_a + y_b) / 2, (z_top + z_bottom) / 2), parent,
              folder=PAY_ART, uv=(x0 / width, 1 - y1 / height, x1 / width, 1 - y0 / height))

def coin_acceptor(parent, origin, x_face):
    """Coin acceptor modelled in 3D from the drawing (px 640-708 x 721-849): grey bezel plate with 4 screws, a slanted
    coin entry slot sunk into a black rim, a ribbed coin-return button, and a slanted return chute ending in a lever."""
    grey = mat('CoinGrey', (.32, .32, .33), .35, .6)
    void = mat('CoinVoid', (.002, .002, .002), .9)
    def at(x_px, y_px): return origin(x_px, y_px)
    (ya, zt), (yb, zb) = at(640, 721), at(708, 849)
    plate_d = .002; front = x_face + plate_d
    box('CoinPlate', (plate_d, yb - ya, zt - zb), (x_face + plate_d / 2, (ya + yb) / 2, zb), grey, parent, bevel=.003)
    for sx, sz in ((645, 725), (703, 725), (645, 845), (703, 845)):
        sy, szz = at(sx, sz)
        cyl('CoinScrew', .0025, .0006, (front, sy, szz), M['black'], parent, rot=(0, math.pi / 2, 0), seg=12)
    def slanted(name, p0, p1, width_px, rim_depth, sink):
        (y0, z0), (y1, z1) = at(*p0), at(*p1)
        length = math.hypot(y1 - y0, z1 - z0); width = width_px * (z0 - at(p0[0], p0[1] + 1)[1])
        pivot = bpy.data.objects.new(name, None); link(pivot, 'Equipment'); pivot.parent = parent
        pivot.location = (front, (y0 + y1) / 2, (z0 + z1) / 2)
        pivot.rotation_euler = (math.atan2(y1 - y0, z0 - z1), 0, 0)
        box(name + 'Rim', (rim_depth, width + .006, length + .006), (rim_depth / 2, 0, -(length + .006) / 2), M['black'], pivot, bevel=.0015)
        box(name + 'Hole', (.002, width * .7, length - .004), (rim_depth - .0007, 0, -(length - .004) / 2), void, pivot, bevel=0)   # dark opening in the rim face
        return pivot
    slanted('CoinEntry', (658, 727), (668, 764), 4, .0015, .001)
    slanted('CoinReturn', (674, 797), (680, 828), 4, .0015, .001)
    (ly0, lz0), (ly1, lz1) = at(673, 828), at(687, 845)
    box('CoinLever', (.003, ly1 - ly0, lz0 - lz1), (front + .0015, (ly0 + ly1) / 2, lz1), M['black'], parent, bevel=.002)
    (by0, bz1), (by1, bz0) = at(647, 767), at(684, 792)
    box('CoinButton', (.003, by1 - by0, bz1 - bz0), (front + .0015, (by0 + by1) / 2, bz0), M['black'], parent, bevel=.002)
    for k in range(3):
        rib_y = by0 + (by1 - by0) * (k + 1) / 4
        box('CoinButtonRib', (.001, .003, (bz1 - bz0) * .72), (front + .0033, rib_y, bz0 + (bz1 - bz0) * .14), grey, parent, bevel=0)

def pay_creative(e, r):
    """CREATIVE pay station CRT-AP-i23 (company drawing): black cabinet 750 x 550 x 1700 on 52 mm levelling feet.
    Upper panel: screen deep in a trapezoid recess, camera, grey intercom 'ติดต่อเจ้าหน้าที่', (1) QR scanner plate,
    (2) banknote acceptor 20/50/100 B and coin slot 5/10; lower door (raised): (3) change tray, (3) receipt slot;
    side vents. Front print is the drawing itself (assets/creative_pay/box_front.png, 888 x 2011 px)."""
    body = mat('PayBlack', (.012, .012, .013), .45)
    width, depth, height, foot = .75, .55, 1.70, .052
    for fx in (-.22, .22):
        for fy in (-.31, .31):
            cyl('Foot', .028, .012, (fx, fy, 0), M['steel'], r, seg=16)
            cyl('FootStem', .008, foot - .012, (fx, fy, .012), M['steel'], r, seg=8)
    for wy in (-.12, .12):                                                    # two castors seen under the front
        cyl('Castor', .035, .025, (.18, wy - .0125, .036), M['black'], r, rot=(math.pi / 2, 0, 0), seg=20)
    face = depth / 2
    recess = .07                                                              # front plate thickness = screen recess depth
    box('Cabinet', (depth - recess, width, height), (-recess / 2, 0, foot), body, r, bevel=.006)
    px = width / 888
    image = (888, 2011)
    def origin(x_px, y_px): return (x_px * px - width / 2, foot + height - y_px * px)
    def print_region(name, x0, y0, x1, y1, x_at):
        (ya, zt), (yb, zb) = origin(x0, y0), origin(x1, y1)
        decal(name, 'box_front.png', yb - ya, zt - zb, (x_at, (ya + yb) / 2, (zt + zb) / 2), r, folder=PAY_ART,
              uv=(x0 / image[0], 1 - y1 / image[1], x1 / image[0], 1 - y0 / image[1]))
    # front plate in four pieces around the screen opening (drawing px 77-467 x 156-456), each with its print
    opening = (77, 156, 467, 456)
    for name, (x0, y0, x1, y1) in (('PlateTop', (0, 0, 888, opening[1])), ('PlateBottom', (0, opening[3], 888, 2011)),
                                   ('PlateLeft', (0, opening[1], opening[0], opening[3])), ('PlateRight', (opening[2], opening[1], 888, opening[3]))):
        (ya, zt), (yb, zb) = origin(x0, y0), origin(x1, y1)
        box(name, (recess, yb - ya, zt - zb), (face - recess / 2, (ya + yb) / 2, zb), body, r, bevel=0)
        print_region(name + 'Print', x0, y0, x1, y1, face + .0006)
    # lower door stands 15 mm proud; its print sits on its front
    door = (37, 1016, 847, 1726); door_depth = .015
    (ya, zt), (yb, zb) = origin(door[0], door[1]), origin(door[2], door[3])
    box('LowerDoor', (door_depth, yb - ya, zt - zb), (face + door_depth / 2, (ya + yb) / 2, zb), body, r, bevel=.003)
    print_region('DoorPrint', *door, face + door_depth + .0006)
    # screen recess: sloped walls (deep sloped sill under the screen) back to the screen, 60 mm in
    (oy0, oz1), (oy1, oz0) = origin(opening[0], opening[1]), origin(opening[2], opening[3])
    (by0, bz1), (by1, bz0) = origin(125, 184), origin(421, 346)
    recess_pocket('ScreenRecess', r, face, .06, (oy0, oy1, oz0, oz1), (by0, by1, bz0, bz1), body)
    box('ScreenBezel', (.004, by1 - by0 + .02, bz1 - bz0 + .02), (face - .06 + .002, (by0 + by1) / 2, bz0 - .01), M['dark'], r, bevel=.003)
    decal('Screen', 'screen.png', by1 - by0, bz1 - bz0, (face - .06 + .0045, (by0 + by1) / 2, (bz0 + bz1) / 2), r, glow=True, folder=CREATIVE_EXIT_ART)
    grey = mat('IntercomGrey', (.3, .3, .31), .4)
    on_panel = [('Intercom', (627, 146, 711, 316), .03, grey),
                ('QrPlate', (114, 783, 390, 901), .004, M['label_white']),
                ('QrScanner', (263, 806, 341, 884), .014, M['black']),
                ('NoteAcceptor', (642, 506, 777, 568), .03, None)]
    art_parts(r, 'box_front.png', image, origin, face, on_panel, body)
    coin_acceptor(r, origin, face)
    # change tray and receipt slot sit flush in the door: the door print shows them straight on, nothing sticks out
    for side in (-1, 1):                                                      # side vents, top and bottom
        for group_z in (foot + 1.38, foot + .32):
            for column_x in (-.13, .03):
                for i in range(6):
                    box('SideVent', (.08, .003, .007), (column_x + .05, side * (width / 2 + .0005), group_z + i * .016), M['vent'], r, bevel=0)

def pay_creative_slim(e, r):
    """CREATIVE N-park pay station PLY2024N52 (company drawing): slim black column 380 wide, 500 deep, 1.47 m, on a base
    with levelling feet; head tilted back ~19 deg with round camera, intercom box (help / call / arrow), portrait
    touch screen, QR scanner and receipt slot; vents on the back of the head. Print = the drawing (slim_front.png)."""
    body = mat('PayBlack', (.012, .012, .013), .45)
    width = .38
    for fx in (-.2, .2):
        for fy in (-.155, .155):
            cyl('Foot', .025, .01, (fx, fy, 0), M['steel'], r, seg=16)
            cyl('FootStem', .007, .02, (fx, fy, .01), M['steel'], r, seg=8)
    box('Base', (.5, .396, .057), (0, 0, .026), body, r, bevel=.008)
    # column: side profile from the drawing (front at x .151, back at -.151, back top sloping into the head)
    profile = [(.151, .083), (-.151, .083), (-.151, .916), (-.0755, 1.057), (.067, .647), (.151, .676)]
    bm = bmesh.new()
    left = [bm.verts.new((x_, -width / 2 + .005, z_)) for x_, z_ in profile]
    right = [bm.verts.new((x_, width / 2 - .005, z_)) for x_, z_ in profile]
    bm.faces.new(left); bm.faces.new(right[::-1])
    for k in range(len(profile)):
        n = (k + 1) % len(profile)
        bm.faces.new([left[k], left[n], right[n], right[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    column_mesh = bpy.data.meshes.new('Column'); bm.to_mesh(column_mesh); bm.free(); column_mesh.materials.append(body)
    link(bpy.data.objects.new('Column', column_mesh), 'Equipment').parent = r
    # head: pivot at its front-bottom edge, tilted back 19.2 deg; local +X = face normal, +Z = up the face
    head = bpy.data.objects.new('PayHead', None); link(head, 'Equipment'); head.parent = r
    head.location = (.227, 0, .703); head.rotation_euler = (0, math.radians(-19.2), 0)
    face_length, thick = .8, .17
    box('Head', (thick, width, face_length), (-thick / 2, 0, 0), body, head, bevel=.025)
    # print: rows 0-1475 of the 596 x 2537 drawing on the head face, rows 1505-2537 on the column front
    px = width / 596
    head_rows = 1475                                                          # face + bottom lip; the column starts at row 1505
    def head_origin(x_px, y_px): return (x_px * px - width / 2, face_length - y_px * face_length / head_rows)
    decal('HeadPrint', 'slim_front.png', width, face_length, (.0008, 0, face_length / 2), head, folder=PAY_ART, uv=(0, 1 - head_rows / 2537, 1, 1))
    parts = [('Intercom', (305, 62, 498, 345), .008, None),                 # almost flush, as on the drawing
             ('ScreenFrame', (42, 403, 553, 1022), .006, None),
             ('ReceiptBezel', (280, 1163, 502, 1222), .004, None)]             # QR scanner is flush: print only
    for name, (x0, y0, x1, y1), depth, material in parts:
        (ya, zt), (yb, zb) = head_origin(x0, y0), head_origin(x1, y1)
        box(name, (depth, yb - ya, zt - zb), (depth / 2, (ya + yb) / 2, zb), material or body, head, bevel=min(.004, depth / 3))
        decal(name + 'Art', 'slim_front.png', yb - ya, zt - zb, (depth + .0007, (ya + yb) / 2, (zt + zb) / 2), head, folder=PAY_ART,
              uv=(x0 / 596, 1 - y1 / 2537, x1 / 596, 1 - y0 / 2537))
    (cy_, cz_), _ = head_origin(184, 224), None                                          # round camera: ring, dark disc, camera icon
    ring_radius = 66 * px
    # flush camera with real relief: chamfered black ring (3 mm), dark face sunk inside it, rounded camera body
    # standing off the face, glossy lens; edges catch the light so it reads as a part, not a print
    camera_face = mat('CamFace', (.05, .05, .053), .55)
    ring_mat = mat('CamRingBlack', (.006, .006, .007), .25)
    camera_parts = []
    camera_parts.append(cyl('CamRing', ring_radius, .003, (0, cy_, cz_), ring_mat, head, rot=(0, math.pi / 2, 0), r2=ring_radius * .9, seg=48))   # chamfered rim
    camera_parts.append(face_cyl('CamDisc', ring_radius * .74, .0018, (0, cy_, cz_), camera_face, head, 48))               # sunk below the rim
    box('CamBody', (.005, .05, .03), (.0035, cy_, cz_ - .015), ring_mat, head, bevel=.0024)                                   # rounded body
    box('CamBodyFace', (.001, .04, .021), (.006, cy_, cz_ - .0105), camera_face, head, bevel=.0012)
    cyl('CamLensRim', .0095, .0015, (.0062, cy_, cz_), ring_mat, head, rot=(0, math.pi / 2, 0), seg=32)
    cyl('CamLens', .0075, .002, (.0074, cy_, cz_), M['glass'], head, rot=(0, math.pi / 2, 0), r2=.004, seg=32)              # domed glass
    for part in camera_parts:
        for polygon in part.data.polygons: polygon.use_smooth = False                                              # flat, not domed
    (sy0, sz1), (sy1, sz0) = head_origin(78, 438), head_origin(517, 985)                  # lit portrait touch screen
    box('Screen', (.002, sy1 - sy0, sz1 - sz0), (.0075, (sy0 + sy1) / 2, sz0), M['black'], head, bevel=0)
    picture_w = sy1 - sy0; picture_h = picture_w * .137 / .2125                            # Kiosk Exit picture, full width, centred
    decal('Screen', 'screen.png', picture_w, picture_h, (.0087, (sy0 + sy1) / 2, (sz0 + sz1) / 2), head, glow=True, folder=CREATIVE_EXIT_ART)
    column_top = .676
    decal('ColumnPrint', 'slim_front.png', width - .01, column_top - .083, (.1518, 0, (column_top + .083) / 2), r, folder=PAY_ART,
          uv=(0, 0, 1, 1 - 1505 / 2537))
    for column_y in (-.07, .07):                                              # vents on the back of the head
        for i in range(12):
            box('BackVent', (.003, .1, .008), (-thick - .001, column_y, .2 + i * .03), M['vent'], head, bevel=0)

# ------------------------------------------------------------------ card readers
def reader_column(e, r):
    plinth(r, .36, .36, .08)
    box('Column', (.18, .22, 1.15), (0, 0, .06), M['tdshell'], r, bevel=.025)
    box('Face', (.008, .16, .3), (.091, 0, .82), M['dark'], r, bevel=.004)
    face_cyl('Rfid', .05, .004, (.096, 0, .9), M['acryl'], r, 24)
    box('Disp', (.004, .12, .04), (.096, 0, 1.05), M['screen'], r, bevel=0)
    box('LedBar', (.004, .12, .01), (.096, 0, .78), M['led_g'], r, bevel=0)
    box('Cap', (.22, .26, .025), (0, 0, 1.21), M['navy'], r, bevel=.006)

def reader_uhf(e, r):
    plinth(r, .36, .36, .08)
    cyl('Pole', .045, 2.3, (0, 0, .06), M['steel'], r, seg=14)
    box('Bracket', (.12, .06, .06), (.05, 0, 2.25), M['steel'], r)
    hd = bpy.data.objects.new('UHF', None); link(hd, 'Equipment'); hd.parent = r
    hd.location = (.12, 0, 2.25); hd.rotation_euler = (0, math.radians(25), 0)
    box('Panel', (.05, .32, .32), (0, 0, -.16), M['white'], hd, bevel=.02)
    box('Radome', (.004, .26, .26), (.027, 0, -.13), M['tdshell'], hd, bevel=0)
    box('Led', (.004, .03, .01), (.028, .1, -.02), M['led_g'], hd, bevel=0)

# ------------------------------------------------------------------ pay stations
def pay_compact(e, r):
    plinth(r, .5, .56, .08)
    box('Body', (.38, .46, 1.55), (0, 0, .06), M['tdshell'], r, bevel=.04)
    box('Band', (.385, .465, .12), (0, 0, 1.45), M['navy'], r, bevel=.01)
    box('Screen', (.006, .32, .24), (.193, 0, 1.12), M['screen'], r, bevel=0)
    box('QR', (.006, .12, .1), (.193, -.08, .88), M['glass'], r, bevel=0)
    face_cyl('NFC', .035, .004, (.195, .1, .88), M['acryl'], r, 20)
    box('Receipt', (.008, .12, .015), (.194, 0, .74), M['vent'], r, bevel=0)
    face_cyl('Help', .022, .015, (.193, .15, .62), M['led_r'], r, 16)
    text_mesh('PayTxt', 'PAY', .07, M['labeltext'], r, (.196, 0, 1.5), (math.pi / 2, 0, math.pi / 2))

def pay_wall(e, r):
    box('WallStub', (.12, 1.0, 2.2), (-.18, 0, 0), M['concrete'], r, bevel=.01)
    box('Body', (.18, .5, .8), (-.03, 0, .85), M['tdshell'], r, bevel=.03)
    box('Screen', (.006, .34, .22), (.063, 0, 1.38), M['screen'], r, bevel=0)
    box('QR', (.006, .1, .08), (.063, -.12, 1.08), M['glass'], r, bevel=0)
    face_cyl('NFC', .035, .004, (.064, .1, 1.1), M['acryl'], r, 20)
    box('Receipt', (.008, .12, .015), (.063, 0, .95), M['vent'], r, bevel=0)
    box('Hood', (.26, .58, .03), (.0, 0, 1.66), M['navy'], r, bevel=.008)

# ------------------------------------------------------------------ guard booths
def booth_glass(e, r):
    """Guard booth as built at Thai car parks: concrete plinth with stainless kick band, white ACP lower walls with a
    navy stripe, dark-anodised aluminium frames, tinted glass with a transom, sliding service windows on both lane sides
    (with counters), glazed door with handle, ACP fascia with SECURITY lettering, flat roof with drip edge, split-type
    AC (indoor unit inside, condenser on the roof), wall lamp, CCTV dome, downpipe; desk, monitor, chair inside."""
    width, length = e.get('size', [1.6, 1.6]); half_w, half_l = width / 2, length / 2
    wall, floor_top, sill_z, transom_z, header_z = .06, .12, .95, 1.95, 2.2
    alu = mat('BoothAlu', (.09, .095, .1), .35, .6)
    tint = M['clear_glass']
    acp = M['white']; accent = M['navy']; steel = M['steel']
    box('Floor', (width + .1, length + .2, floor_top), (0, 0, 0), M['concrete'], r, bevel=.02)
    for name, size, loc in (('KickN', (width + .002, .004, .15), (0, half_l + .001, floor_top)), ('KickS', (width + .002, .004, .15), (0, -half_l - .001, floor_top)),
                            ('KickE', (.004, length + .002, .15), (half_w + .001, 0, floor_top)), ('KickW', (.004, length + .002, .15), (-half_w - .001, 0, floor_top))):
        box(name, size, loc, steel, r, bevel=0)                                         # stainless kick band
    # lower walls (ACP) with a navy stripe just under the sill
    for name, size, loc in (('WallN', (width, wall, sill_z - floor_top), (0, half_l - wall / 2, floor_top)),
                            ('WallE', (wall, length, sill_z - floor_top), (half_w - wall / 2, 0, floor_top)),
                            ('WallW', (wall, length, sill_z - floor_top), (-half_w + wall / 2, 0, floor_top)),
                            ('WallS', (width - .62, wall, sill_z - floor_top), (half_w - (width - .62) / 2, -half_l + wall / 2, floor_top))):
        box(name, size, loc, acp, r, bevel=.004)
    for name, size, loc in (('StripeN', (width + .004, wall + .004, .05), (0, half_l - wall / 2, sill_z - .12)),
                            ('StripeE', (wall + .004, length + .004, .05), (half_w - wall / 2, 0, sill_z - .12)),
                            ('StripeW', (wall + .004, length + .004, .05), (-half_w + wall / 2, 0, sill_z - .12)),
                            ('StripeS', (width - .62, wall + .004, .05), (half_w - (width - .62) / 2, -half_l + wall / 2, sill_z - .12))):
        box(name, size, loc, accent, r, bevel=0)
    for name, size, loc in (('SillN', (width + .04, .09, .035), (0, half_l - .025, sill_z)), ('SillE', (.09, length + .04, .035), (half_w - .025, 0, sill_z)),
                            ('SillW', (.09, length + .04, .035), (-half_w + .025, 0, sill_z)), ('SillS', (width - .58, .09, .035), (half_w - (width - .58) / 2 + .02, -half_l + .025, sill_z))):
        box(name, size, loc, alu, r, bevel=.004)
    # corner posts and transom ring
    for post_x in (-half_w + .03, half_w - .03):
        for post_y in (-half_l + .03, half_l - .03):
            box('Post', (.06, .06, header_z - floor_top), (post_x, post_y, floor_top), alu, r, bevel=.008)
    for name, size, loc in (('TransomN', (width - .06, .045, .045), (0, half_l - .03, transom_z)), ('TransomS', (width - .06, .045, .045), (0, -half_l + .03, transom_z)),
                            ('TransomE', (.045, length - .06, .045), (half_w - .03, 0, transom_z)), ('TransomW', (.045, length - .06, .045), (-half_w + .03, 0, transom_z))):
        box(name, size, loc, alu, r, bevel=.003)
    glass_low, glass_high = sill_z + .035, transom_z
    # back (north) wall: fixed tinted panes, mullion in the middle
    box('PaneN', (width - .1, .01, glass_high - glass_low), (0, half_l - .03, glass_low), tint, r, bevel=0)
    box('PaneNTop', (width - .1, .01, header_z - transom_z - .045), (0, half_l - .03, transom_z + .045), tint, r, bevel=0)
    box('MullionN', (.035, .04, glass_high - glass_low), (0, half_l - .03, glass_low), alu, r, bevel=0)
    # lane sides (east / west): fixed panes at the ends, a two-sash sliding service window in the middle
    sash_w = min(.55, (length - .2) / 3)
    for side in (-1, 1):
        x = side * (half_w - .03)
        box(f'PaneTop{side}', (.01, length - .1, header_z - transom_z - .045), (x, 0, transom_z + .045), tint, r, bevel=0)
        end_w = (length - .1 - 2 * sash_w) / 2
        for end in (-1, 1):
            y = end * (sash_w + end_w / 2)
            box(f'PaneEnd{side}{end}', (.01, end_w, glass_high - glass_low), (x, y, glass_low), tint, r, bevel=0)
            box(f'Mullion{side}{end}', (.04, .035, glass_high - glass_low), (x, end * sash_w, glass_low), alu, r, bevel=0)
        for k, (offset_y, offset_x) in enumerate(((-sash_w / 2 + .03, 0), (sash_w / 2 - .03, -side * .025))):   # second sash slid behind the first
            sash = bpy.data.objects.new(f'Sash{side}{k}', None); link(sash, 'Equipment'); sash.parent = r
            sash.location = (x + offset_x, offset_y, glass_low)
            sash_h = glass_high - glass_low
            box('SashGlass', (.008, sash_w - .05, sash_h - .05), (0, 0, .025), tint, sash, bevel=0)
            for name, size, loc in (('SashTop', (.03, sash_w, .025), (0, 0, sash_h - .025)), ('SashBottom', (.03, sash_w, .025), (0, 0, 0)),
                                    ('SashL', (.03, .025, sash_h), (0, -sash_w / 2 + .0125, 0)), ('SashR', (.03, .025, sash_h), (0, sash_w / 2 - .0125, 0))):
                box(name, size, loc, alu, sash, bevel=0)
            box('SashHandle', (.015, .012, .1), (side * .02, (sash_w / 2 - .04) * (1 if k == 0 else -1), sash_h / 2 - .05), steel, sash, bevel=.003)
        box(f'Counter{side}', (.22, sash_w * 2 + .1, .03), (side * (half_w + .08), 0, sill_z - .005), steel, r, bevel=.004)   # service shelf
        for bracket_y in (-sash_w, sash_w):
            box(f'CounterBracket{side}', (.18, .02, .12), (side * (half_w + .07), bracket_y, sill_z - .125), steel, r, bevel=0)
    # front (south): glazed door on the west end, fixed pane beside it
    door_x0 = -half_w + .06; door_w = .56
    box('PaneS', (width - .72, .01, glass_high - glass_low), (half_w - (width - .72) / 2 - .04, -half_l + .03, glass_low), tint, r, bevel=0)
    box('PaneSTop', (width - .1, .01, header_z - transom_z - .045), (0, -half_l + .03, transom_z + .045), tint, r, bevel=0)
    box('DoorJamb', (.05, .06, transom_z - floor_top), (door_x0 + door_w + .025, -half_l + .03, floor_top), alu, r, bevel=0)
    door = bpy.data.objects.new('BoothDoor', None); link(door, 'Equipment'); door.parent = r
    door.location = (door_x0 + door_w / 2, -half_l + .03, floor_top)
    door_h = transom_z - floor_top - .01
    box('DoorGlass', (door_w - .08, .008, door_h - .55), (0, 0, .5), tint, door, bevel=0)
    box('DoorPanel', (door_w - .02, .03, .45), (0, 0, .03), acp, door, bevel=.003)            # solid kick panel
    for name, size, loc in (('DoorStileL', (.04, .045, door_h), (-door_w / 2 + .02, 0, 0)), ('DoorStileR', (.04, .045, door_h), (door_w / 2 - .02, 0, 0)),
                            ('DoorRailTop', (door_w, .045, .05), (0, 0, door_h - .05)), ('DoorRailMid', (door_w, .045, .05), (0, 0, .48))):
        box(name, size, loc, alu, door, bevel=0)
    box('DoorHandle', (.025, .04, .25), (door_w / 2 - .07, -.035, .9), steel, door, bevel=.006)
    # fascia band with lettering, flat roof with drip edge
    box('Fascia', (width + .3, length + .3, .26), (0, 0, header_z), acp, r, bevel=.01)
    box('FasciaStripe', (width + .31, length + .31, .04), (0, 0, header_z + .04), accent, r, bevel=0)
    box('Roof', (width + .36, length + .36, .05), (0, 0, header_z + .26), M['powder'], r, bevel=.01)
    box('Soffit', (width + .29, length + .29, .01), (0, 0, header_z - .005), acp, r, bevel=0)
    for side in (-1, 1):
        text_mesh(f'BoothSign{side}', 'SECURITY', .11, accent, r, (side * (half_w + .152), 0, header_z + .1),
                  (math.pi / 2, 0, side * math.pi / 2), extrude=.004)
    box('CeilLight', (.5, .2, .02), (0, 0, header_z - .03), M['lamp'], r, bevel=0)
    # split AC: indoor unit high on the back wall, condenser on the roof with a fan grille
    box('AcIndoor', (min(.8, width - .3), .2, .26), (0, half_l - .17, header_z - .32), acp, r, bevel=.03)
    box('AcVent', (min(.7, width - .4), .01, .03), (0, half_l - .275, header_z - .31), M['vent'], r, bevel=0)
    box('Condenser', (.7, .3, .5), (0, half_l - .1, header_z + .31), acp, r, bevel=.02)
    grille = cyl('CondenserFan', .19, .01, (0, half_l - .25, header_z + .56), M['dark'], r, rot=(math.pi / 2, 0, 0), seg=32)
    for polygon in grille.data.polygons: polygon.use_smooth = False
    for k in range(5):
        box(f'FanBar{k}', (.36, .006, .006), (0, half_l - .262, header_z + .44 + k * .06), alu, r, bevel=0)
    # wall lamp over the door, CCTV dome under the fascia, downpipe on the back corner
    box('LampBack', (.12, .04, .14), (door_x0 + door_w / 2, -half_l - .02, transom_z + .03), alu, r, bevel=.01)
    box('LampLens', (.1, .02, .06), (door_x0 + door_w / 2, -half_l - .045, transom_z + .05), M['lamp'], r, bevel=.008)
    cyl('CctvBase', .05, .02, (half_w + .08, -half_l + .1, header_z - .025), acp, r, seg=24)
    cyl('CctvDome', .045, .045, (half_w + .08, -half_l + .1, header_z - .07), M['dark'], r, r2=.02, seg=24)
    cyl('DownPipe', .028, header_z - floor_top, (half_w + .035, half_l + .035, floor_top), M['powder'], r, seg=12)       # hugs the back corner post
    # interior: desk along the north wall, monitor, keyboard, chair
    box('Desk', (width - .3, .45, .04), (0, half_l - .3, .9), M['wood'], r, bevel=.006)
    for leg_x in (-half_w + .22, half_w - .22): box('DeskLeg', (.04, .4, .78), (leg_x, half_l - .3, .12), M['powder'], r, bevel=0)
    box('Monitor', (.04, .45, .28), (0, half_l - .18, .94), M['dark'], r, rot=(0, 0, math.pi / 2), bevel=.006)
    box('MonScreen', (.004, .41, .24), (0, half_l - .2, .96), M['screen'], r, rot=(0, 0, math.pi / 2), bevel=0)
    box('Keyboard', (.38, .13, .02), (0, half_l - .42, .94), M['dark'], r, bevel=.003)
    box('Seat', (.42, .42, .06), (0, half_l - .85, .62), M['chair'], r, bevel=.02)
    box('Back', (.42, .05, .45), (0, half_l - 1.04, .68), M['chair'], r, bevel=.02)
    cyl('ChairPost', .025, .5, (0, half_l - .85, .12), M['steel'], r, seg=10)

def booth_container(e, r):
    sx, sy = e.get('size', [2.4, 3.0]); hx, hy = sx / 2, sy / 2
    box('Base', (sx + .1, sy + .1, .12), (0, 0, 0), M['concrete'], r, bevel=.02)
    box('Shell', (sx, sy, 2.4), (0, 0, .12), M['hw_rib'], r, bevel=.02)
    nr = int(sy / .25)
    for s_ in (-1, 1):
        for i in range(nr):
            box(f'Rib{s_}{i}', (.03, .08, 2.2), (s_ * (hx + .01), -hy + .15 + i * .25, .22), M['hw_rib'], r, bevel=0)
        box(f'Win{s_}', (.03, sy * .55, .8), (s_ * (hx + .02), 0, 1.25), M['glass'], r, bevel=0)
    box('Door', (sx * .45, .03, 2.0), (0, -hy - .015, .15), M['powder'], r, bevel=0)
    box('Roof', (sx + .2, sy + .2, .1), (0, 0, 2.52), M['hw_rib'], r, bevel=.01)
    box('AC', (.6, .25, .4), (0, hy + .13, 1.7), M['white'], r, bevel=.02)

# ------------------------------------------------------------------ vacancy sign, radar, height bar, stall indicator
def vacancy_pole(e, r):
    box('Footing', (.4, .4, .2), (0, 0, 0), M['concrete'], r, bevel=.02)
    cyl('Pole', .06, 2.3, (0, 0, .2), M['powder'], r, seg=14)
    box('Panel', (.14, 1.0, .7), (.04, 0, 2.3), M['powder'], r, bevel=.02)
    box('Face', (.006, .9, .6), (.113, 0, 2.35), M['dark'], r, bevel=0)
    box('P', (.006, .32, .32), (.118, -.25, 2.5), M['blue'], r, bevel=0)
    text_mesh('Pt', 'P', .28, M['labeltext'], r, (.122, -.25, 2.66), (math.pi / 2, 0, math.pi / 2))
    text_mesh('Num', str(e.get('display', L['summary'].get('stalls_car', 0) or 0)), .26, M['led_g'], r, (.122, .18, 2.66), (math.pi / 2, 0, math.pi / 2))

def radar_cabinet(e, r):
    box('MountBar', (.04, .06, .86), (-.05, 0, 0), M['steel'], r, bevel=.004)
    box('Bracket', (.04, .1, .1), (-.02, 0, .8), M['steel'], r, bevel=.004)
    box('Housing', (.07, .14, .12), (.03, 0, .78), M['white'], r, bevel=.02)
    box('Radome', (.006, .11, .09), (.067, 0, .795), M['dark'], r, bevel=0)

def height_bar(e, r):
    W = e.get('width', 7.0); H = e.get('height', 2.1)
    for s_ in (-1, 1):
        box(f'Footing{s_}', (.4, .4, .2), (0, s_ * W / 2, 0), M['concrete'], r, bevel=.02)
        box(f'Post{s_}', (.15, .15, H + .6), (0, s_ * W / 2, .2), M['hw_yellow'], r, bevel=.01)
    box('Beam', (.12, W, .12), (0, 0, H + .6), M['hw_yellow'], r, bevel=.01)
    n = int(W / .5)
    for i in range(n):
        box(f'Bar{i}', (.1, W / n - .01, .22), (0, -W / 2 + (i + .5) * W / n, H), M['hw_yellow'] if i % 2 else M['black'], r, bevel=.01)
        if i % 2: box(f'Chain{i}', (.01, .01, .4), (0, -W / 2 + (i + .5) * W / n, H + .22), M['steel'], r, bevel=0)
    face_cyl('Plate', .2, .02, (.07, 0, H + .66), M['white'], r, 24)
    face_cyl('PlateRing', .21, .015, (.065, 0, H + .66), M['red'], r, 24)
    text_mesh('HText', f"{H:.1f}m", .12, M['black'], r, (.09, 0, H + .66), (math.pi / 2, 0, math.pi / 2))

def stall_sensor(e, r):
    cyl('Pole', .025, 2.4, (0, 0, 0), M['steel'], r, seg=10)
    cyl('Lamp', .07, .1, (0, 0, 2.4), M['hw_green'], r, seg=18)

NEW_TYPES = dict(height_bar=height_bar, stall_sensor=stall_sensor)
VARIANTS = {
    'ticket_dispenser': dict(creative=ticket_creative, creative_exit=ticket_creative_exit, creative_dual=ticket_creative_dual, slim=ticket_slim, dual=ticket_dual),
    'lpr_camera': dict(sign=lpr_sign, short=lpr_short),
    'card_reader': dict(column=reader_column, uhf=reader_uhf),
    'pay_station': dict(creative=pay_creative, creative_slim=pay_creative_slim, compact=pay_compact, wall=pay_wall),
    'guard_booth': dict(glass=booth_glass, container=booth_container),
    'vacancy_sign': dict(pole=vacancy_pole),
    'radar_sensor': dict(cabinet=radar_cabinet),
}

def dispatch(base):
    """type -> builder that honours e['model'] (missing/unknown model -> the library default, else the base builder)."""
    out = dict(base); out.update(NEW_TYPES)
    for t, var in VARIANTS.items():
        b0 = base[t]
        out[t] = (lambda t, b0, var: lambda e, r: var.get(e.get('model') or default_model(t), b0)(e, r))(t, b0, var)
    return out
