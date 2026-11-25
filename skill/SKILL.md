---
name: parking-site-3d
description: Turn a parking-lot / site plan (PDF, image, or plain dimensions) into a realistic 3D parking site in headless Blender - asphalt, stall striping (90/60/45/30 deg, parallel, motorcycle, accessible, EV), aisles with arrows, curbs, islands, sidewalks, buildings, trees, parked cars - with every piece of parking equipment placed where the plan says (barrier gates, ticket dispensers, card readers, pay stations, LPR cameras, CCTV, vacancy signs, loop detectors, intercoms, guard booths, EV chargers, light poles, signs, speed bumps). Outputs renders (overview, top plan, per-gate close-ups with ID labels), a .blend, a .glb, an interactive single-file web viewer (click equipment to see what/where), and a Thai summary of entries, exits, stall counts and an equipment schedule (MD + CSV). Use for any parking lot, car park, site access road, gate/entrance layout, "ลานจอดรถ", "ที่จอดรถ", "ผังไซต์", "ทางเข้าออก", "ตำแหน่งอุปกรณ์", "ไม้กั้น", "กล้อง LPR", even if Blender is not named.
---

# Parking Site 3D

Plan in, 3D site + equipment schedule out. Everything is driven by one `site.json`; the scripts never guess positions, so the accuracy of the result = the accuracy of `site.json`.

## Pipeline
```
site.json --site_layout.py--> layout.json, plan.png, summary_th.md, summary.json, equipment.csv
          --build_blender.py--> site.blend, site.glb, render/*.png
          --make_viewer.py--> web/index.html (single file: model + data embedded; double-click to open)
```
One command: `powershell -ExecutionPolicy Bypass -File <skill>/scripts/run.ps1 <site.json> [out_dir] [-NoRender] [-Samples 64] [-Res 1600x900]`
Fast check without Blender: `py <skill>/scripts/site_layout.py <site.json> <out_dir>` and Read `plan.png`.
Needs: Blender 4.2+ (`$env:BLENDER_EXE`, else `scripts/find_blender.ps1` searches PATH, Program Files and Steam libraries on every drive), `py` with Pillow. **New computer:** the skill is also in the user's claude.ai account (synced, without the 14 MB textures/sky: run.ps1 downloads them once into `%LOCALAPPDATA%\parking-site-3d\assets`), or copy this folder to `%USERPROFILE%\.claude\skills\parking-site-3d`; then run `powershell -ExecutionPolicy Bypass -File scripts/setup_check.ps1 -Fix` (checks Python, Pillow, Blender, Tahoma, assets; installs Pillow and saves BLENDER_EXE). Worked real project (5 checkpoints, compact dashboard map): `examples/projects/campus_5_gates/` (source drawings, `site_compact.json`) built by `examples/campus_make_site_compact.py` — copy it for the next campus job. GPU (OptiX/CUDA/HIP) auto-detected. ~35 s for all renders at 32 samples, ~1-3 min at 64 (slower while another Blender holds the GPU).
Realism assets: CC0 Poly Haven textures (asphalt, grass, concrete, interlocking pavers) and a pure-sky HDRI live in `assets/` (see `assets/manifest.json`). If missing, run `py -I <skill>/scripts/fetch_assets.py` once (internet); without them the builder falls back to procedural materials and a Blender sky. The builder finds the HDRI's sun, rotates the sky so the sun matches the sun lamp, and adds render-only extras (oil stains, distant tree belt) in collections `Decals` / `Backdrop` that are not exported. The `.glb` keeps the albedo textures (scaled to 512 px, `--web-tex N` to change) on world-metre UVs.

## Workflow
1. **Get the plan.** PDF: Read it directly (the Read tool renders PDF pages). For pixel-accurate tracing save the page as PNG (Read of an image, or `py -m pip install pymupdf` then rasterise - ask before installing). Plain dimensions ("40x60 m, 50 cars, 1 in 1 out") are fine too: lay it out yourself.
2. **Find the scale.** Use a dimension line, a stall (2.4 m wide x 5.0 m long is the Thai default), or a known road width. Write down px-per-metre and the pixel of your chosen origin (bottom-left of the site).
3. **Write `site.json`** (schema below; copy `examples/sample_site.json`). Coordinates in metres, X east/right, Y north/up (flip image Y). Prefer `parking_areas` (auto-fill) when the plan shows a regular grid; trace exact `stalls` quads only when the plan's stalls are irregular.
4. **Check in 2D first.** Run `site_layout.py`; Read `plan.png`. Add `"underlay": {"image": "plan.png", "px_per_m": 12.5, "origin_px": [x, y]}` to draw the source plan beneath and compare. Fix until stall counts and gate/equipment positions match the plan. Report any count that differs from the plan's own table.
5. **Build 3D.** `run.ps1`. Read `render/overview.png`, `top_labels.png`, `gate_<id>.png`. Check: equipment on islands (not in lanes), barrier arms cross their lane, cars inside stalls, labels readable.
6. **Deliver.** Send renders + `summary_th.md` (SendUserFile), and the viewer: publish `web/index.html` as an Artifact (it is self-contained; declare `capabilities: {downloads: true}` for its screenshot button) or tell the user to double-click it. Answer the user's actual questions from `summary.json`: how many entries/exits/lanes, stalls by type, which equipment sits where.

## site.json
```jsonc
{
  "name": "โครงการ ...",
  "site": [[x,y], ...],                       // property line (optional but used for bounds/area)
  "streets":  [{"id","label","polygon":[...],"centerline":[[x,y],...]}],   // public road, dashed centre line
  "buildings":[{"id","label","polygon":[...],"height":8}],
  "sidewalks":[{"id","polygon":[...]}],       // raised 0.15 m, pavers, blocks stalls
  "islands":  [{"id","polygon":[...],"kind":"equipment"|"green"}],          // curbed; equipment islands get concrete top
  "no_parking":[{"id","polygon":[...]}],      // yellow fill, blocks stalls
  "roads":    [{"id","label","points":[[x,y],...],"width":6, "block_stalls":true}],  // driveways/connectors (asphalt band)
  "parking_areas":[{
     "id","label","polygon":[...],
     "angle_deg": 0,          // aisle direction (0 = east-west aisles)
     "stall_angle": 90,       // 90 | 60 | 45 | 30 | 0 (parallel)
     "stall_w": 2.4, "stall_l": 5.0, "aisle_width": 6.0,   // defaults by angle (Thai rules): 90->6.0, 60->5.5, 45/30->3.5, parallel 2.4x6.0 aisle 3.0
     "vehicle": "motorcycle", // optional: 1.0 x 2.0 stalls, 2.0 aisle
     "rows": "double",        // double = row|aisle|row modules, single = row|aisle
     "offset_u": 0, "offset_v": 0, "margin": 0.3, "lean": "forward"|"back", "one_way": true,
     "accessible": 2, "ev": 4, "special_near": [x,y]   // nearest stalls become accessible (2 stalls -> stall + hatched access aisle) / EV (+ auto charger)
  }],
  "stalls":  [{"quad":[[x,y]x4],"type":"normal|accessible|ev|motorcycle","axis":[dx,dy]}],   // exact traced stalls (front edge = quad[0]->quad[1])
  "gates":   [{"id":"G1","type":"entry|exit|both","label":"ทางเข้าหลัก","pos":[x,y],"heading":90,"lanes":2}],
  "arrows":  [{"pos":[x,y],"heading":90}],    // extra painted arrows (aisles get arrows automatically)
  "trees":   [[x,y], ...],
  "equipment":[{"type":"barrier_gate","gate":"G1","pos":[x,y],"heading":180,"label":"ไม้กั้นขาเข้า ช่อง 1","arm":3.6,"id":"BG-01","note":"..."}],
  "auto_ev_chargers": true, "seed": 7
}
```
Headings are degrees, 0 = east, 90 = north: the way the device faces, the way traffic flows (gates, arrows, loops), or the way a barrier arm points. IDs are generated per type (BG-01, LPR-02, ...) unless given.

Equipment types (`type` -> Thai name, extra params):
`barrier_gate` ไม้กั้นรถ (`arm` m) · `ticket_dispenser` ตู้จ่ายบัตร · `card_reader` เครื่องอ่านบัตร · `pay_station` ตู้ชำระเงินอัตโนมัติ · `lpr_camera` กล้องอ่านป้ายทะเบียน · `cctv` กล้องวงจรปิด (`model`: `bullet` default, or `ptz` pendant dome) · `vacancy_sign` ป้ายแสดงช่องจอดว่าง (`display` number, default = car stalls) · `loop_detector` ลูปตรวจจับรถ (`width`, `length`) · `intercom` อินเตอร์คอม · `guard_booth` ป้อมยาม · `ev_charger` เครื่องชาร์จ EV · `light_pole` เสาไฟ · `sign` ป้ายจราจร (`text`, ASCII) · `speed_bump` ลูกระนาด (`length`).
New type: add it to `EQUIP` in `site_layout.py` and a `build_<type>` function + `BUILDERS` entry in `build_blender.py` (local +X = heading, origin = ground under the device).

## Layout rules of thumb (Thailand, left-hand traffic)
- Drivers sit on the right: ticket dispensers / card readers / LPR posts go on the island to the **right of the lane in the direction of travel**; the barrier arm points across the lane from that island.
- Entry lane order: LPR (reads the approaching car) -> loop + ticket/card -> barrier -> second loop just past the arm. Exit mirrors it.
- Equipment islands 1.0-1.5 m wide, 6-8 m long; lanes 3.5-3.7 m.
- Two-way 90 deg aisles 6.0 m; angled stalls run one-way (arrows follow the lean).
- Accessible stalls next to the building entrance; EV stalls grouped.
These are defaults for laying out a site from dimensions; when a plan shows otherwise, follow the plan.

## Outputs (out_dir)
`plan.png` 2D check plan + legend · `summary_th.md` entries/exits/lanes, stalls by type, equipment counts and positions · `summary.json` · `equipment.csv` (UTF-8 BOM, opens in Excel) · `site.blend` (collections Site, Trees, Cars, Equipment, Labels, Cameras) · `site.glb` (each device = node `EQ_<id>` with extras id/type/label/gate) · `render/overview.png`, `overview_labels.png`, `top.png`, `top_labels.png`, `gate_<id>.png`, `entrance.png` · `web/index.html`.

## Hardware library (every model, ready to reuse)
Each device type has several models; pick one per device with `"model"`, or per gate kit with `"hardware": {"barrier_gate": {"model": "folding"}, "lpr_camera": {"model": "integrated"}}`. Default = first model. Full list, parameters and how to add a model: `references/hardware_catalog.md`; picture sheet: `examples/previews/hardware_catalog.png` (Read it to show the client the options).
The library holds only the hardware the team installs (trimmed 2026-11 by the user — do not re-add removed models unless asked):
- ไม้กั้น `barrier_gate`: straight · folding (แขนพับ 90°: rectangular sections, hinge plates + caps, linkage rod; outer section stays level when animated) · led
- ตู้จ่ายสลิป `ticket_dispenser` (prints a parking slip, not a card): standard · slim · dual (one tall cabinet, tilted faces at car and truck height)
- กล้อง LPR `lpr_camera`: pole only; `display: true` adds the large LED screen showing the Thai plate (`plate`, default "กข 1234") and `message`
- เครื่องอ่านบัตร `card_reader`: gooseneck · column · uhf
- ตู้ชำระเงิน `pay_station`: kiosk · compact · wall
- ป้อม `guard_booth`: glass (clear panes, slim frames, desk / monitor / chair inside) · container
- ป้ายช่องว่าง `vacancy_sign`: gantry · pole
- เรดาร์ `radar_sensor`: post · cabinet
- `height_bar` (คานจำกัดความสูง), `stall_sensor` (indicator light only)
Removed on request: CCTV (still builds for old sites but is not offered), fence boom, gooseneck / integrated LPR, mini booth, zone sign, traffic lights, bollards, tyre killer, road blocker, ground stall sensor, pedestrian gate. Thai text on 3D signs uses the Windows Tahoma font (`text_mesh(..., thai=True)`); avoid Thai strings with stacked vowel/tone marks in 3D text (Blender does not shape them) — plates like "กข 1234" are fine.
Unknown models stop site_layout.py with the list of valid ones. The viewer shows the model (รุ่น) in the info card. When the client names a product that is not in the library, add a model (see the reference) instead of approximating with a wrong one.

## Building library (อาคาร 4–10 ชั้น, ready to reuse)
A building with a rectangular 4-point `polygon` AND a library `"model"` is built by `scripts/buildings.py` (one mesh `BLD_<id>`, per-style materials); without `model` (or with another footprint) it stays the original plain building, so approved older sites rebuild unchanged. Fields: `"model"`, `"floors"` (any >= 1; library shows 4/7/10; default = height / 3.5), `"front_heading"` (deg, the direction the entrance faces, snapped to a side; default = a long side), `label`. Styles (`hardware_catalog.BUILDING_MODELS`, typical footprint L x D):
- `office_glass` อาคารสำนักงานกระจก (36x18): curtain wall, slab bands, mullions every 1.5 m, stone plinth, blue accent fin, lit sign band, lobby canopy
- `office_concrete` อาคารสำนักงานคอนกรีต (36x18): punched windows with frames + sun shades, floor bands, glazed ground floor
- `condo` คอนโดมิเนียม (40x16): balconies with glass rails, sliding doors, AC condensers, side windows
- `mixed_podium` มิกซ์ยูส (40x24): 2-storey retail podium (shopfronts, awnings, signs) + set-back glass tower with fins
- `government` อาคารราชการ (44x20): stone base, vertical louvres, corner piers, columned portico
- `parking` อาคารจอดรถ (40x30): open decks every 3 m, column grid, parapets with yellow stripe, blue P sign, vehicle entry
Every style gets a rooftop (parapet, lift overrun, AC rows, water tank, antenna). Picture sheet: `examples/previews/building_catalog.png`; rebuild it with `py scripts/building_showroom.py <dir>/site.json` -> site_layout -> `build_blender.py ... --closeup-all` (building close-ups hide the neighbours) -> `py scripts/catalog_sheet.py <out> --buildings`. On a compact dashboard map keep buildings few (only the ones the client names, e.g. the control room); a 10-storey glass building adds ~0.3 MB to the glb.

## Toll-booth checkpoints (gate kits) and whole-campus projects
For booth-style checkpoints (booth island between IN and OUT lanes, ticket machine at the entry end, LPR camera + display, loop + radar under the barrier) use `gate_kits` instead of placing each device by hand:
```jsonc
"gate_kits": [{"id": "G1", "label": "จุดที่ 1 ป้อม...", "template": "T1323", "pos": [x, y], "heading": 12.5,   // heading = IN direction
               "apron": 24, "faults": {"ขาเข้า ช่อง 2": "fault"}}]
```
Templates (measured from client drawings, lanes listed left -> right facing IN; lane width includes the outer gutter strip, which is flush and drivable — loops, barrier arms and STOP are sized to each lane's clear width between islands, loops keeping 0.3 m from islands/lines; check with `render_gate_tops.py` (top-down render per gate)). When a kit's template width is within 0.6 m of `road_width` the lanes are re-spaced equally over each half of the road (regular lane lines, arrows on lane centres, outermost loops 0.35 m clear of the edge line); the yellow centre line runs on the road axis into each booth-island nose:
`T794` 1 in / 1 out, lanes 3.35, booth 1.24 x 2.47 · `T884` lanes 3.80, booth 1.24 x 2.50 · `T1060` lanes 3.50, booth 1.60 x 3.95 · `T1323` 2 in / 2 out, lanes 2.90, booth 1.63 x 3.90 (outer lanes get a 0.6 m divider island for their equipment). Custom: give `lanes: [[dir, width, strip], ...]` and `booth: [w, l]`.
Per lane the kit places (Thai left-hand traffic, equipment on the driver's right): slip dispenser 0.5 m before the booth; LPR camera + LED display pole 1.2 m past the booth (0.28 m in from the island edge on booth islands, centred on dividers so its 0.36 m pad stays on the island), the whole unit turned >= 30 deg from straight-back toward the lane (camera sees cars on the road, screen faces the driver, never the booth; >= 0.5 m clear of the booth); two loops 1.8 x 1.0 m (`role`: `before` = presence loop 1.15 m before the boom where the car waits, `after` = exit/safety loop 1.25 m past the boom that confirms the car has driven through before the boom closes), stop line + STOP in front of the presence loop; barrier 1.8 m past (arm spans the lane, `traffic` = lane direction); radar beside the cabinet at 1.55 m. (Barrier/loop sit ~0.45 m further out than the client drawing so the LPR pole fits between booth and barrier.) After every build run.ps1 runs `check_lpr.py`: it ray-casts each LPR's view and flags anything solid within 3.5 m or a centre ray hitting a device, plus part-level clashes; fix any `CHECK` before delivering; `check_pads.py` then confirms every base pad / booth floor sits inside the island it stands on (no `OVERHANG`); plus apron paving, edge/divider lines, lane arrows, and a gate record with `lanes_in`/`lanes_out`. `plan_<gate>.png` is a close-up check plan per gate — compare it with the client drawing.
For a web dashboard prefer a compact schematic (see `examples/campus_make_site_compact.py`): keep the order and topology of the overview but shorten the distances so all gates fit one view, use straight roads meeting at right angles, give every road the same width, and set `road_width` on each kit so its apron tapers from the gate width to that road width. Roads get a dashed centre line and edge lines automatically (`trim: [start, end]` keeps junction mouths clear; `markings: false` turns them off). Put real cable lengths in the cable labels instead of drawing them to scale. When every road should be one width, set `road_width` >= the widest gate: narrower gates then sit inside the road with plain grass kerb islands at their sides (tapered noses) instead of flaring the road. Dashboard checklist: one road width, straight roads, no decorative buildings except the control room, no plazas or streets that are not on the drawing, external streets only as short labelled stubs, STOP text sized to the lane (dropped if it cannot fit), device chips appear only when zoomed in (viewer `LABEL_NEAR`, 55 m).
Large projects: add `water` polygons (canals), `parking_areas` with `"no_stalls": true` (plain forecourts), a `control_room` `{pos, label}` and `cables` `[{id, to, label, length_m, points, color}]` (uplink routes drawn on the ground; the viewer toggles them with แนวสาย and totals them in สรุป). Generate such a site.json with a small script that converts the overview drawing's pixels to metres (scale from a known length, e.g. a labelled cable run) — see `examples/campus_make_site.py`.

## Equipment status, faults, barrier animation
- Any equipment can carry `"status": "ok" | "fault" | "maintenance"` and a `"note"`. Faults are listed in `summary_th.md` / `summary.json` (`faults`, and `lanes_open` per gate = lanes minus faulty barriers), drawn with a red ring in `plan.png`, labelled `<id> FAULT` (red) in renders, and shown red + pulsing in the viewer.
- A faulty `barrier_gate` gets its lane closed automatically: one straight row of traffic cones across the lane ~3 m ahead of the stop line (no extra signs), arm left down, beacon and arm LED strip red. The viewer draws a wide pulsing red ring around it.
- Loop detectors look like real saw-cuts: 12 mm sealed groove + glossy tar overband, chamfered corners and a lead-in cut to the equipment island. Loose cones can also be placed by hand with `"type": "traffic_cone"`.
- Barrier arms are hinged (`ARM_<id>` node at the drive shaft, clear of the cabinet cap; LED material `LED_<id>`, beacon `BEACON_<id>`); the boom drops into a U-fork rest post below its rubber strip, so nothing intersects. The viewer animates them like a real barrier: S-curve travel (open 1.8 s, close 2.4 s), a damped wobble at the top and a small rebound on the rest. Select a barrier -> เปิด/ปิดไม้กั้น buttons; dock button สาธิตรถผ่านไม้กั้น sends a car up to every working barrier: it brakes before the stop line, the boom opens, the car pulls away at parking speed and the boom closes once the car has cleared the loop. LED red when closed, amber while moving, green when open. Faulty barriers never move and blink red.
- Fault cones are placed only where the lane is open road: positions on islands, sidewalks or within 0.38 m of a curb are dropped, and the cones stand on the asphalt even though the barrier sits on its island.
- Road details added automatically: concrete curbs wherever paving meets grass, drain grates along curbs, manholes in aisles, a stop line + painted STOP before every barrier, and yellow chevron hatching in front of equipment islands.

## Using the viewer in a web dashboard
`web/index.html` is self-contained (model + data inside). Embed it with `<iframe src="index.html?ui=min">` (`ui=min` hides the side panel, header and dock; labels, selection card and barrier buttons stay). Control it:
- Same page: `window.ParkingSite.openBarrier(id)`, `.closeBarrier(id)`, `.toggleBarrier(id)`, `.setStatus(id, 'ok'|'fault'|'maintenance', note)`, `.select(id)`, `.getState()`, `.on('ready'|'barrier'|'status'|'select', fn)` (returns an unsubscribe function).
- From a parent page: `iframe.contentWindow.postMessage({type:'parking', action:'open'|'close'|'toggle'|'status'|'select'|'state', id, status, note, requestId}, '*')`. Replies come back as `{type:'parking-reply', ...}`; live events as `{type:'parking-event', event, id, state|status}`. In production, check `event.source`/`event.origin` on both sides.
- `setStatus(id,'fault')` works live: the boom drops, cones appear (`FAULT_<id>`, built for every barrier), labels/rings turn red, lane counts update.
- `web/dashboard_example.html` is a working parent page (barrier list with open/close/fault buttons + event log) to copy from. Serve the folder over http (iframes and `postMessage` need it; `py -m http.server`).
- The side panel's ควบคุม tab offers the same controls by hand (open/close each barrier, open/close all, report fault / repaired).

## Web file size (renders keep full detail)
The `.glb` is made lighter than the render scene, so `web/index.html` stays ~3-4 MB for a site like the sample:
- cars of one kind share a single body mesh (colour travels as the node extra `paint` and the viewer re-applies it); wheels/lamps switch to a low-detail mesh (`cars.web_swap`) and the Subdivision modifier is dropped;
- equipment bevels are render-only Bevel modifiers, so the web gets plain boxes;
- tree canopies/shrubs get a viewport-only Decimate; textures are scaled to 512 px (`--web-tex`); render-only extras (stains, backdrop trees, labels) are not exported.
The viewer adds a RoomEnvironment map so metallic parts (steel plates, bolts, brackets) are not rendered black. Do not use Draco or meshopt compression: the claude.ai artifact sandbox blocks their decoders.

## Realism notes
- Equipment islands get painted yellow/black curbs (Thai practice); green islands get edge shrubs; trees are branched with clustered canopies.
- Parked cars (`scripts/cars.py`): sedan / hatchback / SUV / pickup built from lofted cross-sections + Subdivision Surface (wheel arches, sloped glasshouse with A/B/C pillars, tumblehome), plus sharp details (tyres, 5-spoke alloys, head/tail lamps, grille, intake, plates, mirrors, handles); 6 clear-coated colours. Off by default (`--cars 0`); pass `--cars 0.6` to build_blender.py to park cars/motorcycles in ~60% of stalls. Tune shapes in `SPECS`. The `.glb` is Draco-compressed (the viewer loads the Draco decoder from jsDelivr).
- Equipment is generic but detailed (anchored plinths, seams, vents, hoods, screens, LEDs, reflective boom bands). To match the client's real brand/model: get photos (front, side, 3/4) + overall dimensions, a spec sheet, or a manufacturer CAD/STEP file, then rewrite that type's `build_<type>` function to those dimensions and colours. Once done, every site uses it.

## Known limits
Flat sites only (no ramps or multi-storey decks). Buildings are simple glazed boxes. Parked cars are generic. Blender labels are ASCII IDs; Thai names live in the viewer and the summary. Text inside signs is ASCII.
