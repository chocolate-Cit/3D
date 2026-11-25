# Parking Site 3D Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `parking-site-3d` skill so any parking site is described in one JSON file and assembled in Blender from a stock library of hardware, buildings and roads. The result is a dashboard-sized schematic site GLB plus a demo viewer. RCA is the first site.

**Architecture:** The pure-Python core (schema + layout) turns a site JSON into a layout of placed items: road segments, checkpoints, lanes, devices, closures and buildings, all axis-aligned. Blender-side modules build stock items from the library and assemble the layout into one scene, then export a GLB. A standalone three.js demo page loads the GLB and drives it from a fixed status contract.

**Tech Stack:** Python 3 (pytest) for the core; Blender 5.3 bpy through the `blender` MCP server; glTF/GLB; three.js r128 UMD for the demo page.

**Spec:** `D:/Super_power/docs/superpowers/specs/2026-11-23-parking-site-3d-skill-design.md`

## Global Constraints
- Two skills (user clarification: "stock" = a reusable skill of Blender models kept for future sites):
  - **Stock skill** `C:/Users/TOON/.claude/skills/parking-stock-models/`: standalone, usable on its own ("build me a Kiosk Exit in Blender"). Holds `devices/` (one builder script per device type + `devices.json` registry), `roads/`, `buildings/`, `materials.py`, a `SKILL.md` that lists every model with dims and how to call it, and `library/*.blend` saved assets. Tasks 3 and 4 create files here, not in parking-site-3d.
  - **Site skill** `C:/Users/TOON/.claude/skills/parking-site-3d/`: site JSON, layout core, assembly, export, demo viewer. It loads builders from the stock skill path. Tasks 1, 2, 5, 6 paths below are relative to it.
- No vehicles of any kind in any scene or library.
- Thailand drives on the left. IN lanes flow +Y in checkpoint-local space, and the kiosk is on the driver's right.
- Lane key format: `CP{n}-IN{k}` / `CP{n}-OUT{k}`. Device root name: `<Type>_CP{n}-{IN|OUT}{k}_{NN}`; for standalone devices: `<Type>_CP{n}_{NN}`. Checkpoint root: `Checkpoint_CP{n}`. Closure: `Closure_CP{n}-{IN|OUT}{k}`.
- Device root extras: `device_type`, `device_id`, `lane_key` (absent for standalone), `checkpoint`, `status_part`, `core` (bool).
- Core devices, which close a lane: `barrier`, `kiosk_entrance`, `kiosk_exit`, `lpr`, `loop`. All other devices are non-core and get a ring only.
- Roads: constant width = `lanes_per_direction × 2 × lane_width`, plus equal sidewalks on both sides. Checkpoint heading is one of 0/90/180/270°.
- Web budget: site GLB under 8 MB, under 300k triangles. Textures are 1k JPEG. Draco is off for the demo page.
- Readable code: noun variable names, no `x`/`y`/`z` throwaways (user rule).
- Status contract: `{ devices: {device_id: "ok"|"down"}, barriers: {lane_key: "up"|"down"}, closedLanes?: lane_key[], focus?: number|"overview" }`.

## Review Focus
1. **A checkpoint with 0 IN or 0 OUT lanes (exit-only booth):** layout and closures must still build, with no empty island. Test: `test_exit_only_checkpoint` in Task 2.
2. **A cone row on a narrow lane (≤ 2.9 m):** every cone stays inside the lane rectangle, never on an island. Test: `test_cones_stay_inside_lane` in Task 2.
3. **An unknown device type in the site JSON:** fails with a clear message naming the lane and type, not a Blender traceback. Test: `test_unknown_device_type_rejected` in Task 1.
4. **Two checkpoints on the same side of one road:** they must not overlap after compression. Test: `test_checkpoints_do_not_overlap` in Task 2.
5. **Status for a device_id the GLB does not have:** the demo ignores it and logs it once, without throwing. Covered in Task 6, step 3.

---

### Task 1: Site schema and loader (pure Python)

**Files:**
- Create: `core/site_schema.py`, `core/__init__.py`
- Read: `C:/Users/TOON/.claude/skills/parking-stock-models/devices/devices.json` (the type registry, created in this task as a stub and completed in Task 3: key → `{core: bool, status_part: str, dims: [w, d, h]}` for barrier, lpr, loop, radar, intercom, display, kiosk_entrance, kiosk_exit, kiosk_payment, booth, cone)
- Test: `tests/test_site_schema.py`

**Interfaces:**
- Produces: `load_site(path: str) -> Site`. The dataclasses are:
  - `Site(id, name, roads: list[Road], checkpoints: list[Checkpoint], standalone: list[Standalone], buildings: list[Building])`
  - `Road(id, lanes_per_direction: int, lane_width: float, sidewalk: float, order: list[str])`. `order` lists checkpoint ids and junction names along the road.
  - `Checkpoint(id: int, name, road, side: "on"|"north"|"south", in_lanes: list[Lane], out_lanes: list[Lane], lane_width, island_width, booth: bool, override: tuple[float, float]|None)`
  - `Lane(devices: list[str])`
  - `Standalone(type, checkpoint: int, index: int)`
  - `Building(id, kind, near: int, side, floors, footprint: tuple[float, float])`
- `SiteError(Exception)` is raised with a readable message.

- [ ] **Step 1: Write the failing tests**
  - `test_loads_rca` loads `sites/rca.json` (a minimal fixture written in this task: 5 checkpoints, lanes 2/2, 2/2, 1/1, 1/1, 1/1) and asserts 5 checkpoints and `sum(len(c.in_lanes) for c in checkpoints) == 7`.
  - `test_unknown_device_type_rejected` uses a fixture where one lane contains `"teleporter"`. Assert `SiteError` is raised and its message contains `"CP1-IN1"` and `"teleporter"`.
  - `test_checkpoint_on_missing_road_rejected`.
- [ ] **Step 2: Run** `python -m pytest tests/test_site_schema.py -v` and expect FAIL (module missing).
- [ ] **Step 3: Implement** `load_site` with dataclasses and `json`. Validate device types against `devices.json`.
- [ ] **Step 4: Run** the same command and expect PASS.
- [ ] **Step 5: Commit** in the skill folder: `git init` if needed, then `git add core tests devices.json sites` and `git commit -m "feat: site schema and loader"`.

### Task 2: Schematic layout (pure Python)

**Files:**
- Create: `core/layout.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: `Site` from Task 1.
- Produces: `compute_layout(site: Site, spacing: float = 45.0) -> Layout`. The dataclasses are:
  - `Layout(roads: list[RoadSegment], checkpoints: list[PlacedCheckpoint], devices: list[PlacedDevice], closures: list[Closure], buildings: list[PlacedBuilding], bounds: tuple[float, float, float, float])`
  - `RoadSegment(id, start: (x, y), end: (x, y), width, sidewalk)`
  - `PlacedCheckpoint(id, name, position: (x, y), heading: int, width, length, islands: list[Rect], lanes: list[PlacedLane])`
  - `PlacedLane(key, direction: "IN"|"OUT", rect: Rect)`
  - `PlacedDevice(name, type, lane_key|None, checkpoint, position: (x, y, z), heading: int, core: bool)`
  - `Closure(lane_key, cones: list[(x, y)], ring_center: (x, y), ring_radius)`
  - `PlacedBuilding(id, kind, position, heading, footprint, floors)`
  - `Rect(center: (x, y), size: (w, d), heading: int)`
- Rules from the spec:
  - Checkpoints are placed along their road in `order`, with gaps of `spacing` m between them.
  - Roads run along +X and junction branches along ±Y. Every angle is a multiple of 90°.
  - Device order along the lane uses the existing RCA offsets: kiosk 0, LPR 4.3, loop 5.4, barrier 6.4 m (mirrored for OUT).
  - A closure has 4 cones evenly spaced across the lane, inset 0.35 m from each edge, 1.5 m before the first device.

- [ ] **Step 1: Write the failing tests**
  - `test_headings_are_square`: every checkpoint heading and building heading is in {0, 90, 180, 270}.
  - `test_road_width_constant`: each segment's width equals `lanes_per_direction*2*lane_width`.
  - `test_checkpoints_do_not_overlap`: no two checkpoint footprints intersect.
  - `test_cones_stay_inside_lane`: for every closure, every cone lies inside its lane rect shrunk by 0.2 m. Use lane widths 2.9 and 3.8.
  - `test_exit_only_checkpoint`: a checkpoint with `in_lanes=[]` and one OUT lane has exactly 2 islands and 1 closure.
  - `test_overview_aspect`: for RCA, `bounds` width/height is ≤ 3.2, so the layout fits a 1440×580 panel without zooming out too far.
- [ ] **Step 2: Run** `python -m pytest tests/test_layout.py -v` and expect FAIL.
- [ ] **Step 3: Implement** `compute_layout`. Keep geometry helpers (rect intersection, rotate point by a 90° multiple) in the same file.
- [ ] **Step 4: Run** the tests and expect PASS. Also run `python -m pytest -v` (all tests).
- [ ] **Step 5: Commit** with `git commit -m "feat: schematic layout"`.

### Task 3: Stock hardware library (Blender)

**Files:**
- Create (stock skill): `devices/<type>.py` one file per type exposing `build(name, variant='generic')`, `devices/__init__.py` with `build_device` dispatching by type, `devices/devices.json` (moved here from Task 1; Task 1 reads it from the stock skill path)
- Create (stock skill): `SKILL.md` with frontmatter (name `parking-stock-models`, a pushy description covering Kiosk Entrance/Exit/Payment, LPR, Loop, Radar Sensor, Intercom, barrier, display, cone, roads, buildings), a table per model (type, dims, pivot, forward axis, status part) and the one-line `exec` loader
- Delete: `scripts/build_gate.py`, `scripts/build_site.py`

**Interfaces:**
- Produces: `build_device(type: str, name: str, variant: str = "generic") -> bpy.types.Object` returns an Empty root at the origin, facing +Y, with named children. Requirements per device:
  - `barrier`: `<name>_Arm` has its pivot at the hinge and rotates on local Y. Add a `<name>_StatusLight`.
  - `kiosk_*`: has `<name>_Screen` with emission.
  - `lpr`: has `<name>_Head`.
  - `loop`: has `<name>_Outline`.
  - `radar` and `intercom`: each has `<name>_StatusLight`.
  - `cone`: a single cone mesh.
- Also produces `tag_device(root, type, device_id, lane_key, checkpoint)`, which sets the Global Constraints extras from `devices.json`.
- Realism bar: bevels on every hard edge, real dims from `devices.json`, and multi-part forms. For example, the barrier is a cabinet with a door seam, top cap and arm-mount boss; the LPR has a pole base plate, arm and housing with a sunshield; the kiosk has a plinth, body, screen bezel, ticket/QR slot and canopy. Materials are painted metal, black plastic and glass. Each device stays under 3k triangles.

- [ ] **Step 1: Build every type in the open Blender** by `exec`-ing `blender/devices.py` and calling `build_device` for each type in a row at x = 0, 2, 4…
- [ ] **Step 2: Verify** with `get_scene_info(query="_Arm")` that the arm exists. Rotate the arm −85° and confirm with `look` that it lifts upward. Read each root's custom props in `execute_blender_code` and assert every key in Global Constraints is present.
- [ ] **Step 3: Render** a `look` row of all devices (three_quarter, max_size 900) and compare against the realism bar. Fix any item that is still a plain box.
- [ ] **Step 4: Save** stock `library/devices.blend` (one collection per type, marked as assets) and commit with `git commit -m "feat: stock hardware library"`.

### Task 4: Stock road and building kit (Blender)

**Files:**
- Create (stock skill): `roads/roads.py`, `buildings/buildings.py`, `materials.py` (holds the shared materials `asphalt_web`, `pavement_web`, `paint_white`, `paint_yellow`, `plaster_web`, `glass`, plus the world-UV helper from the current skill)

**Interfaces:**
- Consumes: `RoadSegment`, `PlacedCheckpoint`, `PlacedBuilding` from Task 2. In Blender these arrive as plain dicts, because the layout is exported to JSON.
- Produces:
  - `build_road(segment: dict) -> Object`: asphalt slab, 0.15 m kerbs, sidewalks of equal width on both sides, centre dashes, lane lines and a zebra at each checkpoint. Markings sit 8 mm above the road.
  - `build_junction(center, arms: list[int], width) -> Object`.
  - `build_gate_plaza(checkpoint: dict) -> list[Object]`: islands, stop lines and the booth when `booth`.
  - `build_building(spec: dict) -> Object` with kinds `shophouse_row` (4 m units, roll-up shutters, signs), `office`, `plaza`, `parking_structure`, `guard_house`.
  - Each builder reuses the shared materials and adds no new image textures.

- [ ] **Step 1: Build a test strip** from a hand-made 2-segment layout dict with one junction and one plaza, plus one building of each kind.
- [ ] **Step 2: Verify** with `look` from the top that the road edges are parallel and both sidewalks have the same width, by measuring object bounds with `get_scene_info`. Markings must be visible in rendered shading.
- [ ] **Step 3: Save** stock `library/kit.blend` and commit with `git commit -m "feat: road and building kit"`.

### Task 5: Site assembly, RCA site file and export

**Files:**
- Create: `blender/assemble.py`, `cli/layout_to_json.py` (runs the core to produce `out/<site>.layout.json`)
- Modify: `sites/rca.json` (full content, see below)
- Modify: `SKILL.md` (new workflow: describe site → run layout → assemble → export → demo), `references/hardware-specs.md` (add radar, intercom and display dims)

**Interfaces:**
- Consumes: `compute_layout` (Task 2), `build_device`/`tag_device` (Task 3), and the kit builders (Task 4).
- Produces:
  - `assemble_site(layout_json_path: str) -> dict` builds the scene. It returns `{device_count, closure_count, checkpoints}`.
  - Closures are built from cones plus a ring torus named `Closure_<lane_key>_Ring` and are hidden by default. Each device gets a hidden `<name>_Ring` (for non-core devices) placed at the device.
  - `export_site(path: str) -> dict` writes a GLB (Draco off, JPEG 1k) and returns `{size_mb, triangles}`.
- RCA content comes from the master plan and the fieldbook:
  - CP1 จตุรทิศ on the RCA road, 2 IN / 2 OUT, lane width 2.90, island 1.63.
  - CP3 ทางออกศูนย์วิจัย on the RCA road east, 1/1, 3.50 / 1.60.
  - CP2 เพชรบุรี on the link road south to Phetchaburi, 2/2, 2.90 / 1.63.
  - CP4 I-HOUSE A–C on a north branch, 1/1, 3.80 / 1.24.
  - CP5 I-HOUSE D–E on a north branch, 1/1, 3.35 / 1.24.
  - Every lane has `[kiosk_*, display, lpr, loop, radar, barrier]`.
  - Three `kiosk_payment` units: assumed at CP1, CP2 and CP3, listed as an assumption.
  - Buildings: Bldg A–H, I-HOUSE, Office and RCA Plaza as kinds from Task 4, and shophouse rows on the south side.

- [ ] **Step 1: Run** `python cli/layout_to_json.py sites/rca.json out/rca.layout.json`. Expect it to print 5 checkpoints and 14 lanes.
- [ ] **Step 2: Assemble** in Blender with `assemble_site`. Expect `device_count == 14*6 + 3 = 87` and `closure_count == 14`.
- [ ] **Step 3: Verify** with an overview `look` and one close-up per checkpoint. No headings may be tilted, and the cones of one unhidden closure must sit inside the lane.
- [ ] **Step 4: Export** to `out/rca.glb`. Expect `size_mb < 8` and `triangles < 300000`.
- [ ] **Step 5: Commit** with `git commit -m "feat: assemble and export RCA site"`.

### Task 6: Demo viewer with the status contract

**Files:**
- Create: `viewer/index.html`, `viewer/site-view.js` (the module that owns the scene), `viewer/mock-status.js`
- Build step: `cli/pack_for_artifact.py out/rca.glb viewer/rca_site.js`. This wraps the GLB in a JS file, which is needed because the claude.ai artifact frame refuses `.glb` and `fetch` of data URIs. Use the in-memory GLB rebuild and the `createImageBitmap = undefined` workaround from the current artifact.

**Interfaces:**
- Consumes: the GLB names and extras from Task 5.
- Produces: `createSiteView(container: HTMLElement, modelScript: string) -> { setStatus(status: StatusContract), focus(target: number|"overview"), onPick(callback) }`.

- [ ] **Step 1: Implement** the view.
  - **Overview camera:** perspective fov 35, framed to `Checkpoint_CP*` bounds with 10% margin, at a height that makes RCA fill a 1440×580 panel.
  - **Fly-to:** 1 s ease-out to 45 m from the checkpoint.
  - **Labels:** HTML labels over each `Checkpoint_CP{n}`.
  - **Barrier animation:** arm rotates on local Z toward +85° in glTF space, damped.
  - **Lane closure:** a lane closes when any core device on it is `down` or it is listed in `closedLanes`. Its closure becomes visible and the ring opacity pulses at 1 Hz.
  - **Non-core down:** shows that device's `_Ring` only.
- [ ] **Step 2: Mock status page.** Buttons for "สุ่มสถานะ" and "รีเซ็ต", plus tabs for ภาพรวม and CP1–CP5. A status entry for an unknown device_id is ignored and logged once with `console.warn`.
- [ ] **Step 3: Verify in Chrome** after publishing to the existing artifact URL `https://claude.ai/artifact/3vf5JFBDi1Miaa5kTYvhop`:
  - The overview shows all 5 labels without scrolling.
  - Clicking CP2 flies there.
  - Randomizing so that an LPR goes down closes the lane with a cone row on the road and a blinking ring.
  - A radar going down shows the ring only.
  - A barrier set to up lifts upward.
- [ ] **Step 4: Commit** with `git commit -m "feat: demo viewer with status contract"`, and update the `parking-site-3d-model.md` memory with the new workflow.
