"""Novation Launchkey Mini [MK3].
Источники: Launchkey Mini [MK3] User Guide 1.1 (пэды 2×8, режим Drum, порты); Launchkey MK3 Programmer's Reference
(официальный документ семейства MK3): Drum-режим — ноты на канале 10, верхний ряд 40-43, 48-51, нижний 36-39, 44-47;
кнопки «>» и «Stop/Solo/Mute» — CC 104/105 на канале 16 (прямо сказано про совместимость с Launchkey Mini MK3);
Play/Record — CC 115/117 на канале 16 (у большого Launchkey MK3). CC ручек 21-28 — из сообщества, «?» до калибровки."""
from devices._util import keyboard, cc, note, PITCH

PAD_CH = 9
TOP = [40, 41, 42, 43, 48, 49, 50, 51]
BOT = [36, 37, 38, 39, 44, 45, 46, 47]
C = []
C.append({"id": "pitch", "label": "Полоса Pitch", "kind": "strip", "short": "Pitch", "trig": dict(PITCH), "rect": (34, 70, 26, 150), "verify": "official"})
C.append({"id": "mod", "label": "Полоса Mod", "kind": "strip", "short": "Mod", "trig": cc(1), "rect": (72, 70, 26, 150), "verify": "community"})
for i in range(8):
    C.append({"id": f"knob{i+1}", "label": f"Ручка {i+1}", "kind": "knob", "trig": cc(21 + i), "rect": (150 + i * 74, 58, 46, 46), "verify": "community"})
for i in range(16):
    row, col = divmod(i, 8)   # пэды 1-8 — верхний ряд, 9-16 — нижний
    n = (TOP if row == 0 else BOT)[col]
    C.append({"id": f"pad{i+1}", "label": f"Пэд {i+1}", "kind": "pad", "pad": i, "trig": note(n, PAD_CH),
              "rect": (120 + col * 74, 140 + row * 66, 66, 58), "verify": "family"})
C.append({"id": "next", "label": "Кнопка ▶ (Scene)", "kind": "button", "short": "▶", "trig": cc(104, 15), "rect": (722, 150, 46, 38), "verify": "official"})
C.append({"id": "ssm", "label": "Кнопка Stop/Solo/Mute", "kind": "button", "short": "S/S/M", "trig": cc(105, 15), "rect": (722, 216, 46, 38), "verify": "official"})
C.append({"id": "play", "label": "Кнопка Play", "kind": "button", "short": "Play", "trig": cc(115, 15), "rect": (800, 216, 54, 38), "verify": "family"})
C.append({"id": "rec", "label": "Кнопка Record", "kind": "button", "short": "Rec", "trig": cc(117, 15), "rect": (862, 216, 54, 38), "verify": "family"})
C += keyboard(48, 25, 30, 292, 58.6, 56, 136, 36, 84, channel=0, verify="community")

DEVICE = {
    "id": "launchkey_mini3", "name": "Launchkey Mini MK3", "vendor": "Novation", "title": "NOVATION  Launchkey Mini MK3", "size": (940, 440),
    "ports": [r"launchkey\s*mini"],
    "listen": [r"lkmk3", r"launchkey"],
    "banks": None,
    "screen": None,
    "controls": C,
    "pads": [f"pad{i+1}" for i in range(16)],
    "calib": ([(f"knob{i}", f"Ручка {i}", "cc") for i in range(1, 9)] + [("mod", "Полоса Mod", "cc"), ("pitch", "Полоса Pitch", "pitch"),
              ("next", "Кнопка ▶ (нажмите)", "cc"), ("ssm", "Кнопка Stop/Solo/Mute (нажмите)", "cc"), ("play", "Кнопка Play (нажмите)", "cc"), ("rec", "Кнопка Record (нажмите)", "cc")]),
    "led": None,
    "manual": "https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Launchkey_MK3_Programmers_Reference.pdf",
    "starter": [
        ("knob1", "Ручка 1: громкость", "master_volume", {"step": 5}, {"mode": "absolute"}),
        ("knob2", "Ручка 2: микрофон", "mic_volume", {"step": 5}, {"mode": "absolute"}),
        ("knob3", "Ручка 3: Spotify", "app_volume", {"process": "Spotify.exe", "step": 5}, {"mode": "absolute"}),
        ("knob4", "Ручка 4: прокрутка", "scroll", {"lines": 3}, {"mode": "abs_to_rel"}),
        ("pad9", "Пэд 9: микрофон", "mic_mute", {"mode": "toggle"}, {"mode": "press"}),
        ("pad10", "Пэд 10: назад", "media", {"cmd": "prev"}, {"mode": "press"}),
        ("pad11", "Пэд 11: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "press"}),
        ("pad12", "Пэд 12: вперёд", "media", {"cmd": "next"}, {"mode": "press"}),
        ("play", "Play: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "button", "button_mode": "press"}),
        ("rec", "Record: скриншот", "screenshot", {"mode": "snip"}, {"mode": "button", "button_mode": "press"}),
        ("pitch", "Полоса Pitch: питч голоса", "voice_pitch", {"range": 12}, {"mode": "absolute"}),
    ],
}
