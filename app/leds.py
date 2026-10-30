"""Подсветка RGB-пэдов MiniLab 3 (ЭКСПЕРИМЕНТАЛЬНО: SysEx не из официальной документации,
а из реверс-инжиниринга сообщества: gist Janiczek «Arturia Minilab 3 Sysex codes», форум Arturia).
  F0 00 20 6B 7F 42 02 02 16 <id> <r> <g> <b> F7   id: пэды 1-8 = 0x04..0x0B, r/g/b 0..127"""
from presets import is_minilab3

HEADER = [0x00, 0x20, 0x6B, 0x7F, 0x42]
PALETTE = {"Выкл": "#000000", "Белый": "#ffffff", "Красный": "#ff2020", "Оранжевый": "#ff8a2a", "Жёлтый": "#ffd23a",
           "Зелёный": "#2ee66b", "Бирюза": "#22d3c5", "Синий": "#3b6cff", "Фиолетовый": "#8b5cf6", "Розовый": "#ff4fb4"}
MUTED, LIVE = "#ff2020", "#2ee66b"


def hex_rgb7(h):
    h = h.lstrip("#"); return [int(h[i:i + 2], 16) >> 1 for i in (0, 2, 4)]


def pad_sysex(pad_index0, hexcol):
    """Данные SysEx (без F0/F7, как ждёт mido) для пэда 0..7."""
    return HEADER + [0x02, 0x02, 0x16, 0x04 + pad_index0] + hex_rgb7(hexcol)


def dim(h, k=0.35):
    r, g, b = (int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def compute_pad_colors(cfg, bank, state, enabled=True):
    """-> список из 8 hex-цветов для пэдов текущего банка.
    Приоритет: состояние (микрофон/звук выключен -> красный, включён -> зелёный) > свой цвет пэда > цвет профиля (тускло) > выкл."""
    prof = cfg.get("active_profile")
    own = cfg.get("pad_colors", {}).get(prof, {})
    pcol = cfg.get("profile_colors", {}).get(prof, "#ffffff")
    maps = cfg["profiles"].get(prof, []) + cfg.get("global", [])
    out = []
    for i in range(8):
        note = 36 + bank * 8 + i
        acts = [m["action"]["type"] for m in maps if m.get("trigger", {}).get("type") == "note"
                and m["trigger"].get("number") == note and m["trigger"].get("channel") in (None, 9)]
        c = own.get(str(note))
        if not c:
            c = dim(pcol) if any(a != "none" for a in acts) else "#000000"
        if "mic_mute" in acts: c = MUTED if state.get("mic_muted") else LIVE
        elif "mute_all" in acts and state.get("all_muted"): c = MUTED
        elif "master_mute" in acts and state.get("master_muted"): c = MUTED
        if not enabled: c = "#000000"
        out.append(c)
    return out


class LedOut:
    """Выход на MiniLab 3. Если USB-выхода нет — цвета только на схеме в окне."""
    def __init__(self):
        self.port = None; self.name = None; self.last = None

    @staticmethod
    def find_output(names):
        for n in names:
            if is_minilab3(n) and "din" not in n.lower() and "mcu" not in n.lower():
                return n
        return None

    def open(self, name):
        if self.port and self.name == name: return True
        self.close()
        try:
            import mido
            self.port = mido.open_output(name); self.name = name; self.last = None; return True
        except Exception:
            self.port = None; return False

    def send(self, colors):
        if not self.port or colors == self.last: return
        import mido
        for i, c in enumerate(colors):
            if self.last is None or self.last[i] != c:
                self.port.send(mido.Message("sysex", data=pad_sysex(i, c)))
        self.last = list(colors)

    def close(self, colors_on_release=None):
        if self.port:
            try:
                if colors_on_release: self.last = None; self.send(colors_on_release)
                self.port.close()
            except Exception: pass
        self.port = None; self.name = None; self.last = None
