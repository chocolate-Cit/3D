# Parking Site 3D skill: design

Date: 2026-11-23 · Status: approved 2026-11-23 (scope: skill + stock library; no dashboard renovation now)

## Intent
A reusable skill (`parking-site-3d`) that turns a parking site's plan into a realistic 3D model for an executive web dashboard. The first site is RCA (Go Inno Parking, 5 checkpoints). The model shows **where every piece of hardware is installed** and its **live status**. The model must fit a dashboard panel: one overview that shows every checkpoint, and click-to-zoom per checkpoint.

## Goals (from the user)
1. Each site looks as close to the real site as possible.
2. Hardware sits where it is really installed, per checkpoint and per lane.
3. Device models match the real product models. Photos of the real models come later; until then, use realistic generic models.
4. A device library that also covers sites with other systems: Kiosk Entrance, Kiosk Exit, Kiosk Payment, LPR, Loop, Radar Sensor, Intercom, barrier gate, and similar general hardware.
5. Roads are balanced: constant width, no side visibly wider than the other.
6. Checkpoints are placed square, not tilted.
7. When a device is offline, the affected entry or exit lane gets a row of traffic cones across the lane, on the road surface only (never on sidewalk or islands), plus a blinking red ring that signals "offline".
8. The overview shows every checkpoint without zooming out too far. Clicking a checkpoint flies the camera to it.

## Non-goals
- Vehicles of any kind (user rule).
- Controlling hardware from the web (existing dashboard decision: view only).
- Keeping the code-drawn 3D scene. The user does not like 3D written in code; the dashboard should show the Blender model instead.
- Real-distance geography. The overview is a schematic layout (see Layout).
- Phones below 768px (existing dashboard rule: 3D not loaded).

## Anti-goals
- An overview where checkpoints are specks in a long strip.
- Tilted or uneven roads and booths that look sloppy.
- Device objects merged into scenery, which would break status binding.
- A file so heavy the dashboard panel loads slowly.

## Constraints
- Target panel: the dashboard `LotPanel`, 480px high (580px at lg), page max width 1440px, dark theme (see `D:\Web_Dashboard_RCA\docs\project\06-dashboard-ui.md`, `07-lot-3d.md`).
- Dashboard stack: three 0.170, @react-three/fiber 9, drei 10. Delivered models are glTF/GLB.
- Lane keys in the dashboard are `CP{n}-{IN|OUT}{k}`; device names and tags must map to them.
- Blender 5.3 via the `blender` MCP server; textures from Poly Haven at 1k.
- Thailand drives on the left.
- Web budget: target < 8 MB for one site GLB, < 300k triangles.

## Approaches considered
1. **Site description file + device library + auto layout (chosen).** Each site is one data file (roads, checkpoints, lanes, installed devices). Devices live in one shared library. The skill reads the file, lays out a schematic scene, places library devices, exports one site GLB. Cost: most setup work up front; the file format must be designed well; auto layout may need manual overrides.
2. Hand-built script per site (what RCA used so far). Fast to start, but every site starts from scratch, and device changes must be redone everywhere.
3. Blender for device models only, layout drawn in web code. Lightest file, but roads and buildings are less realistic.

The user chose 1 because the device library (goal 4) and later swap to real product models (goal 3) both need one shared place to change.

## Design

### Site description file (`sites/<site>.json` in the skill)
- `site`: id, display name.
- `roads`: list of named roads, each with an ordered list of checkpoint ids or junctions along it, a `lanes_per_direction` count, and an optional sidewalk flag. No real coordinates are required.
- `checkpoints`: id, name, which road it sits on, side (on the road, or a branch to the north / south), `in_lanes`, `out_lanes`, lane width, island width, booth (yes/no).
- `lanes`: per lane, the installed devices in order along the lane, with type keys from the library (e.g. `kiosk_entrance`, `lpr`, `loop`, `radar`, `intercom`, `barrier`), plus optional model variant.
- `standalone_devices`: e.g. Kiosk Payment, with the checkpoint it belongs near.
- `buildings`: optional named blocks with relative position (before / after a checkpoint, north / south side), floors.
- `overrides`: optional manual offsets per checkpoint or building when auto layout is not right.

### Device library (`library/devices.blend` + `library/devices.json`)
- One collection per device type, each with a generic realistic model now and room for named product variants later.
- Each device has a fixed pivot and forward axis (faces oncoming traffic), real dimensions, and named child parts for status: e.g. barrier `Arm` (hinge pivot), kiosk `Screen`, a `StatusLight` on powered devices.
- Types at launch: barrier gate, LPR camera on pole, loop (road cut outline), radar sensor, intercom, kiosk entrance, kiosk exit, kiosk payment, booth, traffic cone (for offline display).
- Realism: bevelled edges, real proportions, PBR materials (painted metal, glass, plastic), screens with emission.

### Stock library beyond devices (user priority)
- **Buildings:** parametric building kit in `library/buildings.blend`: shophouse row (4 m units, 3–5 floors, roll-up shutters, signage), office/mid-rise block (window grid, parapet), mall/plaza block, guard/booth house, parking structure. Each takes footprint and floors; facades use shared materials.
- **Roads:** road kit in `library/roads.blend`: straight segment (lanes × lane width, kerb, equal sidewalks both sides), T-junction and 4-way junction, branch stub, gate plaza (lane islands at gate width), lane markings (centre dash, lane line, stop line, zebra), median. All share one asphalt, one pavement and one paint material.
- The library is the stock to build any site from; site files only reference library items.

### Layout (schematic, "metro map")
- Checkpoints keep their real order along each road and their real side, but the distance between them is compressed to a fixed spacing so the overview fits the panel.
- Roads are straight segments with constant width, built from `lanes_per_direction` × lane width, plus equal sidewalks on both sides.
- Checkpoints are axis-aligned to their road segment (no tilt). Branch checkpoints sit on short perpendicular stubs.
- Devices inside a checkpoint use real dimensions and real spacing.
- Buildings are placed by relative position, simplified to blocks with facades.

### Offline display
- Rule: only core devices (barrier, kiosk entrance/exit, LPR, loop) close a lane. Others get a small blinking ring on the device itself. Standalone kiosks: ring only.
- For an offline core device, the whole affected lane (IN or OUT) is closed: 3–4 cones in a straight row across the lane width, centred on the lane, placed on the road surface, clipped so none land on island or sidewalk.
- A red ring on the ground around the lane's device group, pulsing (opacity and scale) about once per second.
- Cones and ring are part of the export (hidden by default, one set per lane) so the web only toggles visibility. Named `Closure_CP{n}-{IN|OUT}{k}`.

### Naming and tags
- Device root name: `<Type>_CP{n}-{IN|OUT}{k}_{NN}` (standalone: `<Type>_CP{n}_{NN}`).
- Extras on each device root: `device_type`, `device_id`, `lane_key` (`CP{n}-IN{k}`), `checkpoint`, `status_part`.
- Checkpoint roots `Checkpoint_CP{n}` carry `name`, `in_lanes`, `out_lanes` for labels and camera focus.

### Web viewer (reference implementation in the skill)
- Loads one site GLB. Overview camera framed to all checkpoints with modest margin; clicking a checkpoint label or tab flies to it; "back to overview" button.
- Status per device and per lane: barrier arm up/down, offline closure (cones + blinking ring), tint for broken.
- Built so the dashboard team can port it into `LotPanel` (same lane keys, same panel size).

### Web 3D component and status contract (reference demo only for now)
- The backend API will change, and the user is open to renovating the dashboard. So the 3D work does not bind to today's API.
- Deliverable: one reusable web 3D component (React Three Fiber, same stack as the dashboard) that loads a site GLB and takes a status object in a fixed contract:
  - `devices: { [device_id]: "ok" | "down" }`
  - `barriers: { [lane_key]: "up" | "down" }`
  - `closedLanes?: lane_key[]` (e.g. repair in progress)
  - `focus?: checkpoint id | "overview"`, plus `onPick(checkpoint)`
- It owns: overview camera framed to all checkpoints in a 480–580px panel, fly-to per checkpoint, HTML labels anchored to empties, cone row + blinking ring, barrier animation.
- When the new backend API exists, an adapter maps it to this contract. The model and the component do not change.
- For now this ships only as a standalone demo page (mock status) to review each site; it is not mounted in the dashboard.

### Follow-up project (not in this design)
- Renovate the dashboard for the new backend API and mount the 3D component in place of the code-drawn `LotPanel` scene. Day/night and the mock-mode blueprint ground are decided there.

### Skill outputs per site
- `<site>.glb`, `<site>.blend`, a device table (name, type, lane key, checkpoint), list of assumptions, overview and close-up renders.

## Answers from the project
- **Status source:** the dashboard already uses lane keys `CP{n}-{IN|OUT}{k}` and two states, ok / down (see `07-lot-3d.md`, `11-pending-and-decisions.md`). The GLB is keyed by `lane_key` plus `device_id`; the viewer takes a map `{ device_id → ok|offline|broken }` and `{ lane_key → barrier up/down }`. The component's status contract (below) is that map; an adapter fills it from whichever backend API exists.
- **RCA lane contents:** per the fieldbook page, every lane has kiosk, LPR + display, loop, radar sensor and barrier; Kiosk Payment ×3 are standalone. Topology comes from the RCA master plan image the user sent (point 1 and 3 on the RCA road, 2 on the Phetchaburi link, 4 and 5 on branches to I-HOUSE).

## Builder calls (marked as mine, correctable)
- This version replaces the current skill's per-gate scripts (`build_gate.py`, `build_site.py`); the existing RCA test artifact is rebuilt from the new pipeline.
- Checkpoint labels and click targets are HTML overlays anchored to `Checkpoint_CP{n}`, styled by the web, not geometry in the GLB.
- Layout v1 supports straight roads meeting at 90° and perpendicular branch stubs; the schema keeps an optional `angle` field for later sites.
- Real product models are swapped in the library, then each site GLB is rebuilt (baked, one file per site). No runtime per-device loading.
- Intercom is in the library but not placed at RCA until the user confirms it is installed there.

## Decided by the user
- Approach 1, schematic overview that shows every checkpoint, click-to-zoom per checkpoint.
- The Blender model replaces the code-drawn 3D in the dashboard. Because the backend API will change, this design delivers the model, a reusable 3D component with a fixed status contract and a demo page; the dashboard renovation is a follow-up project.
- Offline rule (option ข): only core devices close a lane (barrier, kiosk entrance/exit, LPR, loop) with the cone row + blinking red ring. Other devices (radar, intercom, display) get a small blinking red ring on the device only. Standalone Kiosk Payment: ring only, no cones. Broken and offline look the same (dashboard has two states).
- Goals 1–8 above, including the cone row and blinking red ring for offline lanes.
- Real product models will replace generic ones when photos arrive.

## Left to the builder
- Exact JSON schema field names and validation.
- Spacing constants for the schematic layout per panel size.
- Polygon detail per device within the web budget.
- Whether the device library is linked or appended into site files.
- RCA site file contents from the master plan and fieldbook page.
