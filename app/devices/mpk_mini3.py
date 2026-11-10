"""Akai MPK mini mk3 (программа 1 «MPC», загружается при включении).
Официально (Akai): джойстик влево-вправо — pitch bend, вверх-вниз — модуляция (Quickstart Guide v1.3);
пэды — канал 10, клавиши — канал 1 (статья поддержки Akai). Номера нот пэдов (A: 36-43, B: 44-51) и CC ручек
(70-77) Akai публикует только внутри MPK mini Editor — взяты из считанной с устройства программы 1
(сообщество) и помечены «?» до калибровки."""
from devices._util import keyboard, cc, note, PITCH

PAD_CH = 9
C = []
C.append({"id": "pitch", "label": "Джойстик ←→ (Pitch)", "kind": "strip", "short": "Джой X", "trig": dict(PITCH), "rect": (34, 70, 26, 150), "verify": "official"})
C.append({"id": "mod", "label": "Джойстик ↑↓ (Mod)", "kind": "strip", "short": "Джой Y", "trig": cc(1), "rect": (72, 70, 26, 150), "verify": "community"})
for i in range(8):
    row, col = divmod(i, 4)   # пэды 1-4 — нижний ряд, 5-8 — верхний (как на корпусе)
    C.append({"id": f"pad{i+1}", "label": "Пэд {bank}" + str(i + 1), "kind": "pad", "pad": i,
              "bank_trigs": [note(36 + i, PAD_CH), note(44 + i, PAD_CH)], "rect": (310 + col * 86, 144 - row * 80, 76, 66), "verify": "community"})
for i in range(8):
    C.append({"id": f"knob{i+1}", "label": f"Ручка {i+1}", "kind": "knob", "trig": cc(70 + i),
              "rect": (684 + (i % 4) * 64, 62 + (i // 4) * 84, 46, 46), "verify": "community"})
C += keyboard(48, 25, 30, 262, 58.6, 56, 160, 36, 96, channel=0, verify="community")

DEVICE = {
    "id": "mpk_mini3", "name": "MPK mini mk3", "vendor": "Akai", "title": "AKAI  MPK mini mk3", "size": (940, 440),
    "ports": [r"mpk\s*mini\s*(3|mk\s*3|mkiii|iii)"],
    "listen": [],
    "banks": {"names": ["A", "B"], "label": "Пэды", "rect": (760, 10, 150, 28)},
    "screen": (120, 60, 160, 64),
    "controls": C,
    "pads": [f"pad{i+1}" for i in range(8)],
    "calib": [(f"knob{i}", f"Ручка {i}", "cc") for i in range(1, 9)] + [("mod", "Джойстик вверх-вниз", "cc"), ("pitch", "Джойстик влево-вправо", "pitch")],
    "led": None,
    "manual": "https://support.akaipro.com/en/support/solutions/articles/69000863197",
    "starter": [
        ("knob1", "Ручка 1: громкость", "master_volume", {"step": 5}, {"mode": "absolute"}),
        ("knob2", "Ручка 2: микрофон", "mic_volume", {"step": 5}, {"mode": "absolute"}),
        ("knob3", "Ручка 3: Spotify", "app_volume", {"process": "Spotify.exe", "step": 5}, {"mode": "absolute"}),
        ("knob4", "Ручка 4: прокрутка", "scroll", {"lines": 3}, {"mode": "abs_to_rel"}),
        ("knob5", "Ручка 5: яркость", "brightness", {"step": 10}, {"mode": "absolute"}),
        ("pad1", "Пэд A1: микрофон", "mic_mute", {"mode": "toggle"}, {"mode": "press"}),
        ("pad2", "Пэд A2: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "press"}),
        ("pad3", "Пэд A3: назад", "media", {"cmd": "prev"}, {"mode": "press"}),
        ("pad4", "Пэд A4: вперёд", "media", {"cmd": "next"}, {"mode": "press"}),
        ("pad5", "Пэд A5: выключить весь звук", "mute_all", {}, {"mode": "press"}),
        ("pad6", "Пэд A6: скриншот", "screenshot", {"mode": "snip"}, {"mode": "press"}),
        ("pad7", "Пэд A7: проводник", "open", {"target": "explorer.exe", "args": ""}, {"mode": "press"}),
        ("pad8", "Пэд A8: рабочий стол", "window", {"cmd": "show_desktop"}, {"mode": "press"}),
        ("pitch", "Джойстик X: питч голоса", "voice_pitch", {"range": 12}, {"mode": "absolute"}),
    ],
}
