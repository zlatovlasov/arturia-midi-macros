"""Arturia KeyLab Essential mk3 (49 клавиш).
Источник: Arturia KeyLab Essential mk3 User Manual v1.1.6 — гл. 4.1 (колесо модуляции = CC 1, pitch bend),
4.3/4.5 (пэды на канале 10: банк A 40-43 / 36-39, банк B 48-51 / 44-47; в таблице опечатка «48 (C#2)» — это 49).
Номера CC девяти энкодеров, девяти фейдеров и главного энкодера в руководствах Arturia НЕ опубликованы
(шаблоны Arturia/DAW только для чтения в MIDI Control Center) — поэтому trig=None: включите калибровку или
выделите контрол на схеме и пошевелите его."""
from devices._util import keyboard, cc, note, PITCH

PAD_CH = 9
TOP_A, BOT_A = [40, 41, 42, 43], [36, 37, 38, 39]
TOP_B, BOT_B = [48, 49, 50, 51], [44, 45, 46, 47]

C = []
C.append({"id": "pitch", "label": "Колесо Pitch", "kind": "strip", "short": "Pitch", "trig": dict(PITCH), "rect": (34, 80, 26, 150), "verify": "official"})
C.append({"id": "mod", "label": "Колесо Mod", "kind": "strip", "short": "Mod", "trig": cc(1), "rect": (72, 80, 26, 150), "verify": "official"})
C.append({"id": "enc", "label": "Главный энкодер", "kind": "encoder", "trig": None, "rect": (150, 150, 70, 70), "verify": "unknown"})
C.append({"id": "encclick", "label": "Главный энкодер: нажатие", "kind": "button", "short": "Клик", "trig": None, "rect": (232, 196, 44, 22), "verify": "unknown"})
for i in range(8):
    row, col = divmod(i, 4)   # пэды 1-4 — верхний ряд, 5-8 — нижний
    a = (TOP_A if row == 0 else BOT_A)[col]; b = (TOP_B if row == 0 else BOT_B)[col]
    C.append({"id": f"pad{i+1}", "label": "Пэд {bank}" + str(i + 1), "kind": "pad", "pad": i,
              "bank_trigs": [note(a, PAD_CH), note(b, PAD_CH)], "rect": (330 + col * 86, 70 + row * 82, 76, 66), "verify": "official"})
for i in range(9):
    C.append({"id": f"knob{i+1}", "label": f"Ручка {i+1}", "kind": "knob", "trig": None, "rect": (690 + i * 52, 60, 40, 40), "verify": "unknown"})
for i in range(9):
    C.append({"id": f"fader{i+1}", "label": f"Фейдер {i+1}", "kind": "fader", "trig": None, "rect": (696 + i * 52, 124, 28, 150), "verify": "unknown"})
# 49 клавиш; нижняя нота 36 при нулевом сдвиге октавы — в руководстве не указана (типично для 49-клавишных)
C += keyboard(36, 49, 30, 300, 38.6, 36.6, 160, 24, 98, channel=0, verify="community")

DEVICE = {
    "id": "keylab_essential3", "name": "KeyLab Essential mk3", "vendor": "Arturia", "title": "ARTURIA  KeyLab Essential 49 mk3", "size": (1180, 470),
    "ports": [r"keylab\s*essential", r"kl\s*essential", r"keylab.*mk\s*3"],
    "listen": [r"keylab"],
    "banks": {"names": ["A", "B"], "label": "Пэды", "rect": (1010, 10, 150, 28)},
    "screen": (120, 64, 190, 64),
    "controls": C,
    "pads": [f"pad{i+1}" for i in range(8)],
    "calib": ([(f"knob{i}", f"Ручка {i}", "cc") for i in range(1, 10)] + [(f"fader{i}", f"Фейдер {i}", "cc") for i in range(1, 10)]
              + [("enc", "Главный энкодер (покрутите)", "cc"), ("mod", "Колесо Mod", "cc"), ("pitch", "Колесо Pitch", "pitch")]),
    "led": None,
    "manual": "https://dl.arturia.net/products/keylab-essential-49-mk3/manual/keylab-essential-mk3_Manual_1_1_6_EN.pdf",
    "starter": [
        ("pad5", "Пэд A5: микрофон", "mic_mute", {"mode": "toggle"}, {"mode": "press"}),
        ("pad6", "Пэд A6: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "press"}),
        ("pad7", "Пэд A7: назад", "media", {"cmd": "prev"}, {"mode": "press"}),
        ("pad8", "Пэд A8: вперёд", "media", {"cmd": "next"}, {"mode": "press"}),
        ("pad1", "Пэд A1: выключить весь звук", "mute_all", {}, {"mode": "press"}),
        ("pad2", "Пэд A2: скриншот", "screenshot", {"mode": "snip"}, {"mode": "press"}),
        ("pad3", "Пэд A3: проводник", "open", {"target": "explorer.exe", "args": ""}, {"mode": "press"}),
        ("pad4", "Пэд A4: рабочий стол", "window", {"cmd": "show_desktop"}, {"mode": "press"}),
        ("mod", "Колесо Mod: громкость", "master_volume", {"step": 5}, {"mode": "absolute"}),
        ("pitch", "Колесо Pitch: питч голоса", "voice_pitch", {"range": 12}, {"mode": "absolute"}),
    ],
}
