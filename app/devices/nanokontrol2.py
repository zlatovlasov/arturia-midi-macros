"""Korg nanoKONTROL2.
Источник: Korg nanoKONTROL2 MIDI Implementation (официальный TXT), таблица «Native KORG Mode»: фейдеры CC 0-7,
ручки CC 16-23, Solo CC 32-39, Mute CC 48-55, Rec CC 64-71, Play 41, Stop 42, REW 43, FF 44, REC 45, Cycle 46,
Track ◀▶ 58/59, Marker Set 60, Marker ◀▶ 61/62. Заводская сцена CC-режима использует те же номера на канале 1
(по данным сообщества; в Parameter Guide номера по умолчанию не напечатаны) — поэтому канал «любой»."""
from devices._util import cc

C = []
T = [("track_prev", "Track ◀", "Trk◀", 58, (30, 70)), ("track_next", "Track ▶", "Trk▶", 59, (82, 70)),
     ("cycle", "Cycle", "Cycle", 46, (30, 124)), ("marker_set", "Marker Set", "Set", 60, (134, 124)),
     ("marker_prev", "Marker ◀", "Mrk◀", 61, (186, 124)), ("marker_next", "Marker ▶", "Mrk▶", 62, (238, 124)),
     ("rew", "Перемотка назад", "◀◀", 43, (30, 196)), ("ff", "Перемотка вперёд", "▶▶", 44, (82, 196)),
     ("stop", "Стоп", "■", 42, (134, 196)), ("play", "Play", "▶", 41, (186, 196)), ("rec", "Запись", "●", 45, (238, 196))]
for cid, label, short, n, (x, y) in T:
    C.append({"id": cid, "label": label, "kind": "button", "short": short, "trig": cc(n), "rect": (x, y, 46, 30), "verify": "family"})
for g in range(8):
    x = 320 + g * 76
    C.append({"id": f"knob{g+1}", "label": f"Ручка {g+1}", "kind": "knob", "trig": cc(16 + g), "rect": (x + 26, 48, 38, 38), "verify": "family"})
    for j, (k, base) in enumerate((("S", 32), ("M", 48), ("R", 64))):
        C.append({"id": f"{k.lower()}{g+1}", "label": f"Кнопка {k}{g+1}", "kind": "button", "short": k, "trig": cc(base + g),
                  "rect": (x, 116 + j * 46, 28, 30), "verify": "family"})
    C.append({"id": f"fader{g+1}", "label": f"Фейдер {g+1}", "kind": "fader", "trig": cc(g), "rect": (x + 34, 104, 26, 160), "verify": "family"})

DEVICE = {
    "id": "nanokontrol2", "name": "nanoKONTROL2", "vendor": "Korg", "title": "KORG  nanoKONTROL2", "size": (940, 300),
    "ports": [r"nanokontrol\s*2"],
    "listen": [],
    "banks": None, "screen": None,
    "controls": C,
    "pads": [],
    "calib": [(f"knob{i}", f"Ручка {i}", "cc") for i in range(1, 9)] + [(f"fader{i}", f"Фейдер {i}", "cc") for i in range(1, 9)],
    "led": None,
    "manual": "https://www.korg.com/us/support/download/manual/0/159/2710/",
    "starter": [
        ("fader1", "Фейдер 1: громкость", "master_volume", {"step": 5}, {"mode": "absolute"}),
        ("fader2", "Фейдер 2: микрофон", "mic_volume", {"step": 5}, {"mode": "absolute"}),
        ("fader3", "Фейдер 3: Chrome", "app_volume", {"process": "chrome.exe", "step": 5}, {"mode": "absolute"}),
        ("fader4", "Фейдер 4: Telegram", "app_volume", {"process": "Telegram.exe", "step": 5}, {"mode": "absolute"}),
        ("knob1", "Ручка 1: яркость", "brightness", {"step": 10}, {"mode": "absolute"}),
        ("knob2", "Ручка 2: прокрутка", "scroll", {"lines": 3}, {"mode": "abs_to_rel"}),
        ("play", "Play: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "button", "button_mode": "press"}),
        ("stop", "Стоп", "media", {"cmd": "stop"}, {"mode": "button", "button_mode": "press"}),
        ("rew", "Назад", "media", {"cmd": "prev"}, {"mode": "button", "button_mode": "press"}),
        ("ff", "Вперёд", "media", {"cmd": "next"}, {"mode": "button", "button_mode": "press"}),
        ("rec", "Запись: микрофон", "mic_mute", {"mode": "toggle"}, {"mode": "button", "button_mode": "press"}),
        ("m1", "M1: звук компьютера", "master_mute", {}, {"mode": "button", "button_mode": "press"}),
    ],
}
