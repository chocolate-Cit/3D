# parking-site-3d: hardware library catalogue (pure Python, shared by site_layout.py, hardware.py and the showroom).
# type -> ordered list of (model, Thai name, short description). The first model is the default.
# Trimmed to the hardware the team actually installs (2026-11). Types not listed here (cctv, light_pole, sign, ...)
# still build for older sites but are not part of the library.

MODELS = {
    'barrier_gate': [
        ('straight', 'ไม้กั้น CREATIVE แขนตรง', 'Company unit: charcoal cabinet, silver panels with status LED / P badge / CREATIVE, white rectangular boom with red bars (default)'),
        ('folding', 'ไม้กั้น CREATIVE แขนพับ 90°', 'Same cabinet; two-section white boom with silver hinge plates and linkage rod, outer section stays level while opening (low ceilings)'),
        ('led', 'แขน LED', 'Rectangular boom, full-length LED light bar on both faces'),
    ],
    'ticket_dispenser': [
        ('creative', 'ตู้จ่ายสลิป CREATIVE (รุ่นที่ใช้จริง)', 'Company unit: white cabinet, black front panel, screen + camera, contactless (1), slip slot (2), member QR plate, intercom, side door (default)'),
        ('creative_exit', 'ตู้ Kiosk Exit CREATIVE (รุ่นที่ใช้จริง)', 'Exit lane kiosk: same cabinet; screen with plate / time / fee + PromptPay QR, white plate "(1) scan parking-ticket QR" with scanner, (2) receipt slot (auto on exit lanes)'),
        ('creative_dual', 'ตู้ CREATIVE 2 ชั้น (รุ่นที่ใช้จริง)', 'Company 2-tier kiosk: charcoal lower cabinet, grey tower; PL1000 card reader at car height, upper black head with 10-inch screen + scan-slip / slip-out / RFID plates; 7-inch screen on its own post'),
        ('standard', 'ตู้จ่ายสลิปมาตรฐาน', 'Pedestal + tilted head: screen, PRESS button, slip printer mouth with a slip, RFID, intercom, camera'),
        ('slim', 'ตู้จ่ายสลิปแบบเสาเพรียว', 'Slim column with slip printer, QR / card tap and small screen, for narrow islands'),
        ('dual', 'ตู้จ่ายสลิปสองระดับ (รถเก๋ง/รถบรรทุก)', 'One tall cabinet with two tilted service faces: car window height and truck-cab height'),
    ],
    'lpr_camera': [
        ('sign', 'กล้อง DHI-ITC413 ติดป้าย LED', 'DHI-ITC413-PW4D at the top of a round black pole; charcoal LED sign below it facing the driver: Welcome / plate / date / member lines, reader, white LEDs (default)'),
        ('short', 'กล้อง DHI-ITC413 เสาเตี้ย', 'DHI-ITC413-PW4D on a short round black pole (same as the sign unit), camera at about 1.05 m, no sign'),
        ('pole', 'เสาสั้นข้างเลน (รุ่นเก่า)', 'Older generic ANPR camera on a post; display=true adds the LED screen'),
    ],
    'card_reader': [
        ('gooseneck', 'แขนโค้งหัวเอียง', 'Pedestal with gooseneck head, display, RFID zone, LED bar (default)'),
        ('column', 'เสาตั้ง', 'Straight column reader at window height'),
        ('uhf', 'UHF ระยะไกล', 'Flat UHF antenna panel on a 2.4 m pole, reads windscreen tags without stopping'),
    ],
    'pay_station': [
        ('creative', 'ตู้ชำระเงิน CREATIVE CRT-AP-i23 (รุ่นที่ใช้จริง)', 'Company unit: black cabinet 750 x 550 x 1700, screen in trapezoid hood, intercom, QR scanner, banknote + coin, change tray, receipt (default)'),
        ('creative_slim', 'ตู้ชำระเงิน CREATIVE N-park (เสาเพรียว หัวเอียง)', 'Company unit: slim black column, head tilted back with camera, intercom, portrait screen, QR scanner, receipt'),
        ('kiosk', 'ตู้ใหญ่', 'Full kiosk: lit header, touch screen, ticket / QR / NFC / notes / coins / receipt'),
        ('compact', 'ตู้เล็ก', 'Column with screen, QR and card only (cashless)'),
        ('wall', 'ติดผนัง', 'Slim unit on a wall stub, cashless'),
    ],
    'guard_booth': [
        ('glass', 'ป้อมกระจกใส', 'Clear-glazed booth with thin frames, interior desk / chair / monitor, roof overhang, AC; size=[w, l] (default)'),
        ('container', 'ตู้คอนเทนเนอร์', 'Prefab steel cabin with ribbed walls and small windows'),
    ],
    'vacancy_sign': [
        ('gantry', 'ป้ายสองเสา', 'Two-post LED sign: P badge + free count (default)'),
        ('pole', 'ป้ายเสาเดี่ยว', 'Single pole, smaller LED panel'),
    ],
    'radar_sensor': [
        ('post', 'ตั้งบนเสาเตี้ย', 'Radar on a 0.5 m post (default)'),
        ('cabinet', 'ติดข้างตู้ไม้กั้น', 'Radar housing on a slim bracket at barrier-cabinet height'),
    ],
    'height_bar': [('gantry', 'คานจำกัดความสูง', 'Two posts + hanging yellow/black bar with height plate; width, height params (default)')],
    'stall_sensor': [('indicator', 'ไฟแสดงสถานะช่อง', 'Pole-top green/red bay indicator light (default)')],
}

# building library: model -> (Thai name, description, typical footprint L x D m). floors 4-10 typical (any >= 1 works)
BUILDING_MODELS = {
    'office_glass':    ('อาคารสำนักงานกระจก', 'Curtain-wall office: slab-edge bands, 1.5 m mullions, stone plinth, accent fin, lit sign band, lobby canopy', (36, 18)),
    'office_concrete': ('อาคารสำนักงานคอนกรีต', 'Painted concrete office with punched windows, frames, sun shades, floor bands, glazed ground floor', (36, 18)),
    'condo':           ('คอนโดมิเนียม / ที่พักอาศัย', 'Residential block: balcony per unit with glass rail, sliding doors, AC condensers, side windows', (40, 16)),
    'mixed_podium':    ('อาคารมิกซ์ยูส (โพเดียม + ทาวเวอร์)', '2-storey retail podium with shopfronts, awnings and signs; set-back glass tower with vertical fins', (40, 24)),
    'government':      ('อาคารราชการ / สถาบัน', 'Stone base, vertical louvres, corner piers, columned portico with deep canopy', (44, 20)),
    'parking':         ('อาคารจอดรถ', 'Open-deck car park: slabs every 3 m, column grid, spandrel parapets with stripe, big P sign, vehicle entry', (40, 30)),
}

# Models kept for older sites but left out of the hardware library / catalogue (the team does not install them).
LIBRARY_HIDDEN = {
    'ticket_dispenser': {'standard', 'slim', 'dual'},
    'lpr_camera': {'pole'},
    'card_reader': {'gooseneck', 'column'},
    'pay_station': {'kiosk', 'compact', 'wall'},
    'guard_booth': {'container'},
    'vacancy_sign': {'gantry', 'pole'},
    'stall_sensor': {'indicator'},
}

def library_models(t):
    """Models of type t shown in the hardware library (MODELS minus LIBRARY_HIDDEN)."""
    return [m for m in MODELS.get(t, []) if m[0] not in LIBRARY_HIDDEN.get(t, set())]

def default_model(t):
    return MODELS[t][0][0] if t in MODELS else None

def model_th(t, m):
    for k, th, _ in MODELS.get(t, []):
        if k == m: return th
    return m
