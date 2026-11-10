"""Arturia MiniLab 3 — исходная схема программы (координаты и номера не менялись).
Источник: Arturia MiniLab 3 User Manual v1.0.5, гл. 4.5 (пэды, канал 10), 4.x (полоса Mod = CC 1),
5.4.1–5.4.3 (ручки 74,71,76,77,93,18,19,16; фейдеры 82,83,85,17). Энкодер CC 28 и его нажатие CC 118 в
руководстве не указаны — исторические значения программы, уточняются калибровкой."""
from devices._util import keyboard, cc, note, PITCH
from presets import KNOBS, FADERS, PAD_CH, CH1, is_minilab3, maybe_minilab_port
from calib import ORDER

C = []
C.append({"id": "pitch", "label": "Полоса Pitch", "kind": "strip", "short": "Pitch", "trig": dict(PITCH, channel=CH1), "rect": (34, 70, 26, 170), "verify": "official"})
C.append({"id": "mod", "label": "Полоса Mod", "kind": "strip", "short": "Mod", "trig": cc(1, CH1), "rect": (72, 70, 26, 170), "verify": "official"})
C.append({"id": "enc", "label": "Главный энкодер", "kind": "encoder", "trig": cc(28, CH1), "rect": (150, 140, 76, 76), "verify": "community"})
C.append({"id": "encclick", "label": "Главный энкодер: нажатие", "kind": "button", "short": "Клик", "trig": cc(118, CH1), "rect": (236, 186, 40, 22), "verify": "unknown"})
for i, n in enumerate(KNOBS):
    C.append({"id": f"knob{i+1}", "label": f"Ручка {i+1}", "kind": "knob", "trig": cc(n, CH1),
              "rect": (318 + (i % 4) * 74, 62 + (i // 4) * 84, 52, 52), "verify": "official"})
for i, n in enumerate(FADERS):
    C.append({"id": f"fader{i+1}", "label": f"Фейдер {i+1}", "kind": "fader", "trig": cc(n, CH1), "rect": (640 + i * 66, 50, 34, 176), "verify": "official"})
for i in range(8):
    C.append({"id": f"pad{i+1}", "label": "Пэд {bank}" + str(i + 1), "kind": "pad", "pad": i,
              "bank_trigs": [note(36 + i, PAD_CH), note(44 + i, PAD_CH)], "rect": (120 + i * 92, 244, 80, 64), "verify": "official"})
C += keyboard(48, 25, 30, 326, 58.6, 56, 104, 36, 64, channel=CH1, verify="official")

DEVICE = {
    "id": "minilab3", "name": "MiniLab 3", "vendor": "Arturia", "title": "ARTURIA  MiniLab 3", "size": (940, 440),
    "ports": [r"mini\s*_*lab\s*_*3"], "port_match": is_minilab3, "listen_match": maybe_minilab_port,
    "banks": {"names": ["A", "B"], "label": "Пэды", "rect": (760, 10, 150, 28)},
    "screen": (118, 60, 170, 64),
    "controls": C,
    "pads": [f"pad{i+1}" for i in range(8)],
    "calib": list(ORDER),
    "led": "minilab3",
    "manual": "https://dl.arturia.net/products/minilab-3/manual/minilab-3_Manual_1_0_5_EN.pdf",
}
