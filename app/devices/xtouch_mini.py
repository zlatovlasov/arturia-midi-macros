"""Behringer X-TOUCH MINI (стандартный режим, не MC).
Источник: X-TOUCH MINI Quick Start Guide (Behringer/Music Tribe), «X-TOUCH MINI MIDI MAP»: всё на канале 11.
Слой A: энкодеры CC 1-8, нажатие энкодеров ноты 0-7, верхний ряд кнопок ноты 8-15, нижний 16-23, фейдер CC 9.
Слой B: энкодеры CC 11-18, нажатие 24-31, кнопки 32-39 и 40-47, фейдер CC 10.
(Нотация Behringer: C-2 = нота 0.) Подсветка кнопок/колец документирована, но на «глобальном» канале,
заводское значение которого не указано — поэтому подсветку не включаем."""
from devices._util import cc, note

CH = 10   # канал 11
C = []
for i in range(8):
    x = 40 + i * 90
    C.append({"id": f"enc{i+1}", "label": "Энкодер " + str(i + 1) + " · слой {bank}", "short": str(i + 1), "kind": "encoder",
              "bank_trigs": [cc(1 + i, CH), cc(11 + i, CH)], "rect": (x, 58, 60, 60), "verify": "official"})
    C.append({"id": f"push{i+1}", "label": "Нажатие энкодера " + str(i + 1) + " · слой {bank}", "short": "Нажать", "kind": "button",
              "bank_trigs": [note(i, CH), note(24 + i, CH)], "rect": (x + 8, 138, 44, 18), "verify": "official"})
    C.append({"id": f"btn{i+1}", "label": "Кнопка " + str(i + 1) + " · слой {bank}", "short": str(i + 1), "kind": "button",
              "bank_trigs": [note(8 + i, CH), note(32 + i, CH)], "rect": (x, 168, 60, 42), "verify": "official"})
    C.append({"id": f"btn{i+9}", "label": "Кнопка " + str(i + 9) + " · слой {bank}", "short": str(i + 9), "kind": "button",
              "bank_trigs": [note(16 + i, CH), note(40 + i, CH)], "rect": (x, 222, 60, 42), "verify": "official"})
C.append({"id": "fader", "label": "Фейдер · слой {bank}", "kind": "fader", "bank_trigs": [cc(9, CH), cc(10, CH)], "rect": (830, 60, 40, 200), "verify": "official"})

DEVICE = {
    "id": "xtouch_mini", "name": "X-TOUCH MINI", "vendor": "Behringer", "title": "BEHRINGER  X-TOUCH MINI", "size": (940, 300),
    "ports": [r"x-?\s*touch\s*mini"],
    "listen": [],
    "banks": {"names": ["A", "B"], "label": "Слой", "rect": (760, 10, 150, 28)},
    "screen": None,
    "controls": C,
    "pads": [],
    "calib": [],   # все контролы зависят от слоя — номера фиксированы картой Behringer
    "led": None,
    "manual": "https://cdn-media.empowertribe.com/a2d3dedbd371482db5c9906c06d301f4/QSG_BE_0808-AAF_X-TOUCH-MINI_WW.pdf",
    "starter": [
        ("fader", "Фейдер: громкость", "master_volume", {"step": 5}, {"mode": "absolute"}),
        ("enc1", "Энкодер 1: прокрутка", "scroll", {"lines": 3}, {"mode": "abs_to_rel"}),
        ("enc2", "Энкодер 2: микрофон", "mic_volume", {"step": 5}, {"mode": "absolute"}),
        ("enc3", "Энкодер 3: Spotify", "app_volume", {"process": "Spotify.exe", "step": 5}, {"mode": "absolute"}),
        ("btn1", "Кнопка 1: микрофон", "mic_mute", {"mode": "toggle"}, {"mode": "press"}),
        ("btn2", "Кнопка 2: назад", "media", {"cmd": "prev"}, {"mode": "press"}),
        ("btn3", "Кнопка 3: пауза/плей", "media", {"cmd": "play_pause"}, {"mode": "press"}),
        ("btn4", "Кнопка 4: вперёд", "media", {"cmd": "next"}, {"mode": "press"}),
        ("btn5", "Кнопка 5: скриншот", "screenshot", {"mode": "snip"}, {"mode": "press"}),
        ("push1", "Нажатие 1: звук компьютера", "master_mute", {}, {"mode": "press"}),
    ],
}
