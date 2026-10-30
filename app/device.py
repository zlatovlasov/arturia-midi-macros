"""Интерактивная схема MiniLab 3 (QPainter)."""
import time
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PySide6.QtWidgets import QWidget
from theme import col, overlay
from presets import KNOBS, FADERS, PAD_CH, CH1

W, H = 940, 440

def build_controls(calib=None):
    c = _build()
    for x in c:   # ручки/фейдеры/энкодер/полосы: канал любой; калибровка подменяет CC
        if x["kind"] in ("strip", "encoder", "button", "knob", "fader"):
            x["default_trig"] = dict(x["trig"], channel=None)
            x["trig"] = dict((calib or {}).get(x["id"]) or x["default_trig"], channel=None)
    return c

CONTINUOUS = ("strip", "encoder", "knob", "fader")

def _build():
    c = []
    c.append({"id": "pitch", "label": "Полоса Pitch", "kind": "strip", "trig": {"type": "pitch", "channel": CH1, "number": 0}, "rect": QRectF(34, 70, 26, 170)})
    c.append({"id": "mod", "label": "Полоса Mod", "kind": "strip", "trig": {"type": "cc", "channel": CH1, "number": 1}, "rect": QRectF(72, 70, 26, 170)})
    c.append({"id": "enc", "label": "Главный энкодер", "kind": "encoder", "trig": {"type": "cc", "channel": CH1, "number": 28}, "rect": QRectF(150, 140, 76, 76)})
    c.append({"id": "encclick", "label": "Главный энкодер: нажатие", "kind": "button", "trig": {"type": "cc", "channel": CH1, "number": 118}, "rect": QRectF(236, 186, 40, 22)})
    for i, cc in enumerate(KNOBS):
        x = 318 + (i % 4) * 74; y = 62 + (i // 4) * 84
        c.append({"id": f"knob{i+1}", "label": f"Ручка {i+1}", "kind": "knob", "trig": {"type": "cc", "channel": CH1, "number": cc}, "rect": QRectF(x, y, 52, 52)})
    for i, cc in enumerate(FADERS):
        x = 640 + i * 66
        c.append({"id": f"fader{i+1}", "label": f"Фейдер {i+1}", "kind": "fader", "trig": {"type": "cc", "channel": CH1, "number": cc}, "rect": QRectF(x, 50, 34, 176)})
    for i in range(8):
        x = 120 + i * 92
        c.append({"id": f"pad{i+1}", "label": f"Пэд {i+1}", "kind": "pad", "pad": i, "rect": QRectF(x, 244, 80, 64)})
    whites = [0, 2, 4, 5, 7, 9, 11]
    n = 0
    for k in range(25):
        note = 48 + k
        if (k % 12) in whites or k == 24:
            c.append({"id": f"key{note}", "label": f"Клавиша {note}", "kind": "white", "trig": {"type": "note", "channel": CH1, "number": note}, "rect": QRectF(30 + n * 58.6, 326, 56, 104)}); n += 1
    n = 0
    for k in range(25):
        note = 48 + k
        if (k % 12) in whites or k == 24:
            n += 1; continue
        c.append({"id": f"key{note}", "label": f"Клавиша {note}", "kind": "black", "trig": {"type": "note", "channel": CH1, "number": note}, "rect": QRectF(30 + n * 58.6 - 18, 326, 36, 64)})
    return c


class DeviceView(QWidget):
    selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self.controls = build_controls(); self.bank = 0; self.sel = None
        self.seen = set(); self.calib_target = None   # что уже шевелили; что подсвечивает мастер калибровки
        self.lit, self.values, self.mapped, self.held, self.pad_colors = {}, {}, set(), set(), {}
        self.screen_text = ""
        self.setMinimumSize(620, 300); self.setMouseTracking(True); self.hover = None
        self.t = QTimer(self); self.t.timeout.connect(self._fade); self.t.start(40)

    def trig(self, c):
        if c["kind"] == "pad":
            return {"type": "note", "channel": PAD_CH, "number": 36 + self.bank * 8 + c["pad"]}
        return c["trig"]

    def set_calib(self, calib):
        sel = self.sel["id"] if self.sel else None
        self.controls = build_controls(calib)
        self.sel = next((c for c in self.controls if c["id"] == sel), None); self.update()

    def defaults(self):
        return {c["id"]: c["default_trig"] for c in self.controls if "default_trig" in c}

    def label(self, c):
        return f"Пэд {'AB'[self.bank]}{c['pad']+1}" if c["kind"] == "pad" else c["label"]

    def set_bank(self, b):
        self.bank = b; self.update()
        if getattr(self, 'on_bank', None): self.on_bank()
        if self.sel and self.sel["kind"] == "pad": self.selected.emit(self.sel)

    def find(self, ev):
        for c in self.controls:
            t = self.trig(c)
            if t["type"] == ev["type"] and (t["type"] == "pitch" or t["number"] == ev["number"]) and t["channel"] in (None, ev["channel"]):
                return c
        if ev["type"] == "note" and ev["channel"] == PAD_CH and 36 <= ev["number"] <= 51:
            b = (ev["number"] - 36) // 8
            if b != self.bank: self.set_bank(b)
            return self.find(ev)
        return None

    def on_event(self, ev):
        c = self.find(ev)
        if not c: return None
        self.lit[c["id"]] = time.monotonic(); self.seen.add(c["id"])
        if ev["type"] == "note":
            (self.held.add if ev["on"] else self.held.discard)(c["id"])
            self.screen_text = f"{self.label(c)}\nvel {ev['value']}" if ev["on"] else self.screen_text
        elif ev["type"] in ("cc", "pitch"):
            self.screen_text = f"{self.label(c)}\n{ev['value']}"
        if ev["type"] == "cc": self.values[c["id"]] = ev["value"] / 127
        if ev["type"] == "pitch": self.values[c["id"]] = ev["value"] / 16383
        self.update(); return c

    def _fade(self):
        if self.lit or self.calib_target: self.update()
        now = time.monotonic()
        for k in [k for k, t in self.lit.items() if now - t > 0.6]: del self.lit[k]

    def select_id(self, cid):
        for c in self.controls:
            if c["id"] == cid: self.sel = c; self.update(); self.selected.emit(c); return

    # --- геометрия
    def _xf(self):
        s = min(self.width() / W, self.height() / H)
        return s, (self.width() - W * s) / 2, (self.height() - H * s) / 2

    def _hit(self, pos):
        s, ox, oy = self._xf(); p = QPointF((pos.x() - ox) / s, (pos.y() - oy) / s)
        for c in [c for c in self.controls if c["kind"] == "black"] + [c for c in self.controls if c["kind"] != "black"]:
            if c["rect"].contains(p): return c
        if QRectF(760, 8, 150, 30).contains(p): return "bank"
        return None

    def mousePressEvent(self, e):
        h = self._hit(e.position())
        if h == "bank": self.set_bank(1 - self.bank)
        elif h: self.sel = h; self.update(); self.selected.emit(h)

    def mouseMoveEvent(self, e):
        h = self._hit(e.position()); h = h["id"] if isinstance(h, dict) else h
        if h != self.hover: self.hover = h; self.update()
        self.setCursor(Qt.PointingHandCursor if h else Qt.ArrowCursor)

    def _glow(self, c):
        if c["id"] in self.held: return 1.0
        t = self.lit.get(c["id"])
        return max(0.0, 1 - (time.monotonic() - t) / 0.6) if t else 0.0

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s, ox, oy = self._xf(); p.translate(ox, oy); p.scale(s, s)
        g = QLinearGradient(0, 0, 0, H); g.setColorAt(0, col("#2a2826")); g.setColorAt(1, col("#1f1e1c"))
        p.setPen(QPen(col("#3a3733"), 1.5)); p.setBrush(g); p.drawRoundedRect(QRectF(4, 4, W - 8, H - 8), 22, 22)
        p.setFont(QFont("Inter", 11, QFont.DemiBold)); p.setPen(col("#d8d3cc")); p.drawText(QRectF(30, 18, 300, 30), Qt.AlignVCenter, "ARTURIA  MiniLab 3")
        # банк
        br = QRectF(760, 10, 150, 28); p.setPen(QPen(col("#4a4640"))); p.setBrush(col("#171615")); p.drawRoundedRect(br, 14, 14)
        for i, t in enumerate("AB"):
            r = QRectF(762 + i * 74, 12, 72, 24)
            if i == self.bank: p.setPen(Qt.NoPen); p.setBrush(col("#ff8a2a")); p.drawRoundedRect(r, 12, 12)
            p.setPen(col("#111" if i == self.bank else "#bdb6ad")); p.setFont(QFont("Inter", 10, QFont.DemiBold))
            p.drawText(r, Qt.AlignCenter, f"Пэды {t}")
        # экран
        p.setPen(QPen(col("#3c3934"))); p.setBrush(col("#0e0e0d")); p.drawRoundedRect(QRectF(118, 60, 170, 64), 8, 8)
        p.setPen(col("#ffb071")); p.setFont(QFont("Inter", 10)); p.drawText(QRectF(126, 66, 160, 52), Qt.AlignCenter, self.screen_text if hasattr(self, "screen_text") else "")
        for c in self.controls: self._draw(p, c)
        if getattr(self, "dimmed", False):
            p.setPen(Qt.NoPen); p.setBrush(overlay()); p.drawRoundedRect(QRectF(4, 4, W - 8, H - 8), 22, 22)
            p.setPen(col("#d8d3cc")); p.setFont(QFont("Inter", 20, QFont.Bold)); p.drawText(QRectF(0, 0, W, H), Qt.AlignCenter, "МАКРОСЫ ВЫКЛЮЧЕНЫ\nклавиатура свободна для FL Studio")
        p.end()

    def _frame(self, p, c, r, radius):
        sel = self.sel is c; hov = self.hover == c["id"]
        mapped = c["id"] in self.mapped
        pen = QPen(col("#ff8a2a") if sel else col("#7a746c") if hov else col("#3e3a35"), 2.4 if sel else 1.2)
        p.setPen(pen); return mapped

    def _draw(self, p, c):
        grey = c["kind"] in CONTINUOUS and c["id"] not in self.seen and getattr(self, "grey_untouched", True)
        if grey: p.setOpacity(0.38)
        self._draw1(p, c)
        p.setOpacity(1.0)
        if self.calib_target == c["id"]:
            ph = (time.monotonic() * 2) % 1.0
            p.setBrush(Qt.NoBrush); p.setPen(QPen(col("#ff8a2a"), 3 + 2 * ph))
            p.drawRoundedRect(c["rect"].adjusted(-8 - 4 * ph, -8 - 4 * ph, 8 + 4 * ph, 8 + 4 * ph), 12, 12)

    def _draw1(self, p, c):
        r = c["rect"]; k = c["kind"]
        if c["id"] in self.held:
            r = r.adjusted(2, 3, -2, 1) if k in ("pad", "white", "black") else r
        gl = self._glow(c); mapped = c["id"] in self.mapped
        sel = self.sel is c; hov = self.hover == c["id"]
        edge = col("#ff8a2a") if sel else col("#8a837a") if hov else col("#45413b")
        p.setPen(QPen(edge, 2.6 if sel else 1.3))
        if k == "pad":
            base = col("#34312d"); own = self.pad_colors.get(c["id"])
            if own and own != "#000000":
                base = blend(base, QColor(own), 0.6)
                p.save(); p.setPen(Qt.NoPen); g2 = QColor(own); g2.setAlpha(70); p.setBrush(g2); p.drawRoundedRect(r.adjusted(-4, -4, 4, 4), 12, 12); p.restore()
            base = blend(base, col("#ff8a2a"), gl * 0.9)
            p.setBrush(base); p.drawRoundedRect(r, 9, 9)
            p.setPen(col("#111" if gl > .5 else "#cfc8be")); p.setFont(QFont("Inter", 10, QFont.DemiBold))
            p.drawText(r, Qt.AlignCenter, self.label(c).replace("Пэд ", ""))
        elif k in ("knob", "encoder"):
            p.setBrush(blend(col("#2f2c29"), col("#ff8a2a"), gl * .5)); p.drawEllipse(r)
            p.setPen(Qt.NoPen); p.setBrush(col("#1a1918")); p.drawEllipse(r.adjusted(7, 7, -7, -7))
            v = self.values.get(c["id"], 0.5 if k == "encoder" else 0.0)
            import math
            ang = math.radians(225 - 270 * v); cx, cy, rad = r.center().x(), r.center().y(), r.width() / 2 - 10
            p.setPen(QPen(col("#ff8a2a") if (gl or k == "knob") else col("#cfc8be"), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
            p.setPen(col("#a39b90")); p.setFont(QFont("Inter", 8))
            p.drawText(QRectF(r.x() - 20, r.bottom() + 1, r.width() + 40, 16), Qt.AlignCenter, c["label"].replace("Ручка ", "") if k == "knob" else "")
        elif k == "fader":
            p.setBrush(col("#151413")); p.drawRoundedRect(QRectF(r.center().x() - 4, r.y(), 8, r.height()), 4, 4)
            v = self.values.get(c["id"], 0.0); y = r.bottom() - 14 - v * (r.height() - 28)
            p.setPen(QPen(edge, 1.3)); p.setBrush(blend(col("#d8d2c8"), col("#ff8a2a"), max(gl, .0)))
            p.drawRoundedRect(QRectF(r.x(), y, r.width(), 22), 5, 5)
            if sel: p.setPen(QPen(col("#ff8a2a"), 2)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r.adjusted(-4, -4, 4, 4), 6, 6)
        elif k == "strip":
            p.setBrush(blend(col("#2b2926"), col("#ff8a2a"), gl * .7)); p.drawRoundedRect(r, 8, 8)
            if c["id"] in self.values:
                v = self.values[c["id"]]; y = r.bottom() - 6 - v * (r.height() - 12)
                p.setPen(Qt.NoPen); p.setBrush(col("#ff8a2a")); p.drawRoundedRect(QRectF(r.x() + 4, y - 3, r.width() - 8, 6), 3, 3)
            p.setPen(col("#8d867c")); p.setFont(QFont("Inter", 7)); p.drawText(QRectF(r.x() - 10, r.bottom() + 2, r.width() + 20, 14), Qt.AlignCenter, "Pitch" if c["id"] == "pitch" else "Mod")
        elif k == "button":
            p.setBrush(blend(col("#34312d"), col("#ff8a2a"), gl)); p.drawRoundedRect(r, 6, 6)
            p.setPen(col("#cfc8be")); p.setFont(QFont("Inter", 7)); p.drawText(r, Qt.AlignCenter, "Клик")
        elif k == "white":
            p.setBrush(blend(col("#ece8e1"), col("#ffb36b"), gl)); p.drawRoundedRect(r, 4, 4)
        elif k == "black":
            p.setBrush(blend(QColor("#161518"), col("#ff8a2a"), gl)); p.drawRoundedRect(r, 3, 3)
        if mapped:
            p.setPen(Qt.NoPen); p.setBrush(col("#ff8a2a"))
            d = QPointF(r.right() - 5, r.top() + 5) if k not in ("white", "black") else QPointF(r.center().x(), r.bottom() - 12)
            p.drawEllipse(d, 3.5, 3.5)


def blend(a, b, t):
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t), int(a.blue() + (b.blue() - a.blue()) * t))
