# Hardware catalogue (parking-site-3d)

Pick a model with `"model": "<model>"` on any equipment entry (or per gate kit: `"hardware": {"barrier_gate": {"model": "folding"}}`). The first model of each type is the default. Picture sheet: `examples/previews/hardware_catalog.png`.

## `barrier_gate` · ไม้กั้นรถ (ID prefix BG)

| model | ชื่อ | description |
|---|---|---|
| `straight` | แขนตรง | Round aluminium boom with red reflective bands + LED strip (default) |
| `folding` | แขนพับ 90° | Articulated rectangular boom: hinge plates + pin, linkage rod; outer section stays level while opening |
| `led` | แขน LED | Rectangular boom, full-length LED light bar on both faces |

## `ticket_dispenser` · ตู้จ่ายสลิป (ID prefix TD)

| model | ชื่อ | description |
|---|---|---|
| `standard` | ตู้จ่ายสลิปมาตรฐาน | Pedestal + tilted head: screen, PRESS button, slip printer mouth with a slip, RFID, intercom, camera (default) |
| `slim` | ตู้จ่ายสลิปแบบเสาเพรียว | Slim column with slip printer, QR / card tap and small screen, for narrow islands |
| `dual` | ตู้จ่ายสลิปสองระดับ (รถเก๋ง/รถบรรทุก) | One tall cabinet with two tilted service faces: car window height and truck-cab height |

## `lpr_camera` · กล้องอ่านป้ายทะเบียน (LPR) (ID prefix LPR)

| model | ชื่อ | description |
|---|---|---|
| `pole` | เสาสั้นข้างเลน | Square post, sun-shielded ANPR camera with IR ring; display=true adds a large LED screen showing the Thai plate (default) |

## `card_reader` · เครื่องอ่านบัตร (ID prefix CR)

| model | ชื่อ | description |
|---|---|---|
| `gooseneck` | แขนโค้งหัวเอียง | Pedestal with gooseneck head, display, RFID zone, LED bar (default) |
| `column` | เสาตั้ง | Straight column reader at window height |
| `uhf` | UHF ระยะไกล | Flat UHF antenna panel on a 2.4 m pole, reads windscreen tags without stopping |

## `pay_station` · ตู้ชำระเงินอัตโนมัติ (ID prefix PS)

| model | ชื่อ | description |
|---|---|---|
| `kiosk` | ตู้ใหญ่ | Full kiosk: lit header, touch screen, ticket / QR / NFC / notes / coins / receipt (default) |
| `compact` | ตู้เล็ก | Column with screen, QR and card only (cashless) |
| `wall` | ติดผนัง | Slim unit on a wall stub, cashless |

## `guard_booth` · ป้อมยาม (ID prefix GB)

| model | ชื่อ | description |
|---|---|---|
| `glass` | ป้อมกระจกใส | Clear-glazed booth with thin frames, interior desk / chair / monitor, roof overhang, AC; size=[w, l] (default) |
| `container` | ตู้คอนเทนเนอร์ | Prefab steel cabin with ribbed walls and small windows |

## `vacancy_sign` · ป้ายแสดงช่องจอดว่าง (ID prefix VS)

| model | ชื่อ | description |
|---|---|---|
| `gantry` | ป้ายสองเสา | Two-post LED sign: P badge + free count (default) |
| `pole` | ป้ายเสาเดี่ยว | Single pole, smaller LED panel |

## `radar_sensor` · เรดาร์ตรวจจับรถ (ID prefix RD)

| model | ชื่อ | description |
|---|---|---|
| `post` | ตั้งบนเสาเตี้ย | Radar on a 0.5 m post (default) |
| `cabinet` | ติดข้างตู้ไม้กั้น | Radar housing on a slim bracket at barrier-cabinet height |

## `height_bar` · คานจำกัดความสูง (ID prefix HB)

| model | ชื่อ | description |
|---|---|---|
| `gantry` | คานจำกัดความสูง | Two posts + hanging yellow/black bar with height plate; width, height params (default) |

## `stall_sensor` · เซนเซอร์ช่องจอด (ID prefix SS)

| model | ชื่อ | description |
|---|---|---|
| `indicator` | ไฟแสดงสถานะช่อง | Pole-top green/red bay indicator light (default) |

## Single-model types

`cctv` (กล้องวงจรปิด), `loop_detector` (ลูปตรวจจับรถ), `intercom` (อินเตอร์คอม), `ev_charger` (เครื่องชาร์จรถไฟฟ้า (EV)), `light_pole` (เสาไฟส่องสว่าง), `sign` (ป้ายจราจร), `speed_bump` (ลูกระนาด), `traffic_cone` (กรวยจราจร)

## Parameters

- `barrier_gate`: `arm` (m), `traffic` (lane direction, deg), `status`/`note`
- `guard_booth`: `size` [w, l]
- `lpr_camera`: `display` (true adds the LED screen; integrated always has one)
- `vacancy_sign`: `display` (number shown)
- `tyre_killer`, `road_blocker`, `speed_bump`: `length`
- `height_bar`: `width`, `height`
- `loop_detector`: `width`, `length`
- `pedestrian_gate`: `width` (passage)
- `sign`: `text` (ASCII)

## Adding a model

1. Add `(model, Thai name, description)` to `scripts/hardware_catalog.py`.
2. Write `def <type>_<model>(e, r)` in `scripts/hardware.py` (local +X faces the lane, origin on the ground, use box/cyl/face_cyl/text_mesh with M[...] materials) and register it in `VARIANTS` (or `ARM_STYLES` for a barrier boom; a folding-type boom puts its outer part under an `ARM2_<id>` empty so the viewer keeps it level).
3. New device type: also add it to `EQUIP` in `site_layout.py` and to `NEW_TYPES`.
4. Re-run the showroom (below) and check the sheet.

## Showroom / catalogue sheet

```powershell
py <skill>/scripts/hardware_showroom.py <dir>/site.json            # every model, one row per type (optional: type,type filter)
py <skill>/scripts/site_layout.py <dir>/site.json <dir>/out
& $env:BLENDER_EXE -b --factory-startup --python <skill>/scripts/build_blender.py -- <dir>/out/layout.json <dir>/out --samples 32 --res 840x630 --closeup-all
py <skill>/scripts/catalog_sheet.py <dir>/out                   # -> hardware_catalog.png
py <skill>/scripts/make_viewer.py <dir>/out                     # -> web/index.html (3D library)
```
