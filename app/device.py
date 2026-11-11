"""Интерактивная схема устройства (QPainter). Раскладка и номера — из профиля в app/devices/."""
import time
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PySide6.QtWidgets import QWidget
from theme import col, overlay
import devices as D
from devices import generic as G

W, H = 940, 440   # холст MiniLab 3 (у других моделей — DEVICE["size"])

def build_controls(calib=None, device=D.DEFAULT, extra=None):
    """Контролы схемы из профиля устройства. calib: id -> триггер (калибровка); extra — контролы Generic MIDI."""
    prof = D.get(device)
    src = list(prof["controls"]) if not prof.get("dynamic") else list(extra or [])
    c = []
    for x in src:
        x = dict(x); r = x["rect"]; x["rect"] = QRectF(*r) if not isinstance(r, QRectF) else QRectF(r)
        if prof.get("dynamic"):
            x["trig"] = dict(x["trig"])   # Generic: канал как пришёл
        elif "bank_trigs" in x:
            x["bank_trigs"] = [D.default_trig(x, b) for b in range(len(x["bank_trigs"]))]
        elif x["kind"] in D.ANY_CHANNEL_KINDS:   # ручки/фейдеры/энкодер/полосы/кнопки: канал любой; калибровка подменяет CC
            x["default_trig"] = D.default_trig(x)
            got = (calib or {}).get(x["id"]) or x["default_trig"]
            x["trig"] = dict(got, channel=None) if got else None
        else:
            got = (calib or {}).get(x["id"])
            x["default_trig"] = dict(x["trig"]) if x.get("trig") else None
            x["trig"] = dict(got) if got else x["default_trig"]
        c.append(x)
    return c

CONTINUOUS = ("strip", "encoder", "knob", "fader")


class DeviceView(QWidget):
    selected = Signal(dict)

    def __init__(self, device=D.DEFAULT):
        super().__init__()
        self.bank = 0; self.sel = None
        self.seen = set(); self.calib_target = None   # что уже шевелили; что подсвечивает мастер калибровки
        self.lit, self.values, self.mapped, self.held, self.pad_colors = {}, {}, set(), set(), {}
        self.screen_text = ""
        self.on_new_control = None   # Generic MIDI: вызывается с новым контролом, чтобы GUI сохранил его
        self.set_device(device)
        self.setMinimumSize(620, 300); self.setMouseTracking(True); self.hover = None
        self.t = QTimer(self); self.t.timeout.connect(self._fade); self.t.start(40)

    # --- устройство
    def set_device(self, device, calib=None, extra=None):
        """Сменить модель на схеме: профиль, калибровка, контролы Generic MIDI."""
        self.prof = D.get(device); self.device = self.prof["id"]
        self.W, self.H = self.prof.get("size", (W, H))
        self.calib = dict(calib or {}); self.extra = [dict(x) for x in (extra or [])]
        self.bank = 0; self.sel = None; self.hover = None
        self.seen, self.lit, self.values, self.held, self.pad_colors = set(), {}, {}, set(), {}
        self.screen_text = ""
        self.controls = build_controls(self.calib, self.device, self.extra)
        self.update()

    @property
    def nbanks(self):
        b = self.prof.get("banks")
        return len(b["names"]) if b else 1

    def bank_name(self, b=None):
        b = self.bank if b is None else b
        bk = self.prof.get("banks")
        return bk["names"][b] if bk else ""

    def trig(self, c, bank=None):
        """Триггер контрола (для банковых — текущего банка). None — номер ещё не известен (нужна калибровка)."""
        if "bank_trigs" in c:
            return c["bank_trigs"][self.bank if bank is None else bank]
        return c.get("trig")

    def pads(self):
        """Пэды устройства по порядку (для цветов/подсветки)."""
        ids = self.prof.get("pads", [])
        by = {c["id"]: c for c in self.controls}
        return [by[i] for i in ids if i in by]

    def pad_trigs(self):
        return [self.trig(c) for c in self.pads()]

    def is_pad_trig(self, t):
        """Это триггер пэда устройства (любой банк)? — для выбора цвета пэда в редакторе."""
        if not t: return False
        for c in self.pads():
            for b in range(self.nbanks if "bank_trigs" in c else 1):
                pt = self.trig(c, b if "bank_trigs" in c else None)
                if pt and pt["type"] == t.get("type") and pt["number"] == t.get("number") and pt.get("channel") in (None, t.get("channel")):
                    return True
        return False

    def set_calib(self, calib):
        sel = self.sel["id"] if self.sel else None
        self.calib = dict(calib or {})
        self.controls = build_controls(self.calib, self.device, self.extra)
        self.sel = next((c for c in self.controls if c["id"] == sel), None); self.update()

    def set_extra(self, extra):
        """Generic MIDI: заменить набор появившихся контролов (например, «Очистить схему»)."""
        self.extra = [dict(x) for x in (extra or [])]; self.set_calib(self.calib)

    def defaults(self):
        return {c["id"]: c["default_trig"] for c in self.controls if "default_trig" in c}

    def label(self, c):
        if "{bank}" in c["label"]:
            return c["label"].format(bank=self.bank_name())
        return c["label"]

    def set_bank(self, b):
        self.bank = b % self.nbanks; self.update()
        if getattr(self, 'on_bank', None): self.on_bank()
        if self.sel and "bank_trigs" in self.sel: self.selected.emit(self.sel)

    @staticmethod
    def _match(t, ev):
        return bool(t) and t["type"] == ev["type"] and (t["type"] == "pitch" or t["number"] == ev["number"]) and t["channel"] in (None, ev["channel"])

    def find(self, ev):
        for c in self.controls:
            if self._match(self.trig(c), ev):
                return c
        for b in range(self.nbanks):   # контрол другого банка/слоя — переключаем банк на схеме
            if b == self.bank: continue
            for c in self.controls:
                if "bank_trigs" in c and self._match(self.trig(c, b), ev):
                    self.set_bank(b); return c
        return None

    def learn_new(self, ev):
        """Generic MIDI: незнакомое сообщение -> новый контрол на схеме. Возвращает контрол или None."""
        if not self.prof.get("dynamic") or ev["type"] not in ("cc", "note", "pitch", "program"): return None
        if ev["type"] == "note" and not ev.get("on"): return None
        if len(self.extra) >= G.MAX: return None
        x = G.make(ev, len(self.extra))
        if any(e["id"] == x["id"] for e in self.extra): return None
        self.extra.append(x); self.set_calib(self.calib)
        if self.on_new_control: self.on_new_control(x)
        return next((c for c in self.controls if c["id"] == x["id"]), None)

    def on_event(self, ev):
        c = self.find(ev) or self.learn_new(ev)
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
        s = min(self.width() / self.W, self.height() / self.H)
        return s, (self.width() - self.W * s) / 2, (self.height() - self.H * s) / 2

    def _bank_rect(self):
        b = self.prof.get("banks")
        if not b: return None
        x, y, w, h = b["rect"]; return QRectF(x, y - 2, w, h + 2)

    def _hit(self, pos):
        s, ox, oy = self._xf(); p = QPointF((pos.x() - ox) / s, (pos.y() - oy) / s)
        for c in [c for c in self.controls if c["kind"] == "black"] + [c for c in self.controls if c["kind"] != "black"]:
            if c["rect"].contains(p): return c
        br = self._bank_rect()
        if br and br.contains(p): return "bank"
        return None

    def mousePressEvent(self, e):
        h = self._hit(e.position())
        if h == "bank": self.set_bank(self.bank + 1)
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
        W, H = self.W, self.H
        g = QLinearGradient(0, 0, 0, H); g.setColorAt(0, col("#2a2826")); g.setColorAt(1, col("#1f1e1c"))
        p.setPen(QPen(col("#3a3733"), 1.5)); p.setBrush(g); p.drawRoundedRect(QRectF(4, 4, W - 8, H - 8), 22, 22)
        p.setFont(QFont("Inter", 11, QFont.DemiBold)); p.setPen(col("#d8d3cc")); p.drawText(QRectF(30, 18, 600, 30), Qt.AlignVCenter, self.prof["title"])
        # банк / слой
        bk = self.prof.get("banks")
        if bk:
            x, y, w, h = bk["rect"]; n = len(bk["names"]); step = (w - 2) / n
            br = QRectF(x, y, w, h); p.setPen(QPen(col("#4a4640"))); p.setBrush(col("#171615")); p.drawRoundedRect(br, 14, 14)
            for i, t in enumerate(bk["names"]):
                r = QRectF(x + 2 + i * step, y + 2, step - 2, h - 4)
                if i == self.bank: p.setPen(Qt.NoPen); p.setBrush(col("#ff8a2a")); p.drawRoundedRect(r, 12, 12)
                p.setPen(col("#111" if i == self.bank else "#bdb6ad")); p.setFont(QFont("Inter", 10, QFont.DemiBold))
                p.drawText(r, Qt.AlignCenter, f"{bk['label']} {t}")
        # экран
        sc = self.prof.get("screen")
        if sc:
            x, y, w, h = sc
            p.setPen(QPen(col("#3c3934"))); p.setBrush(col("#0e0e0d")); p.drawRoundedRect(QRectF(x, y, w, h), 8, 8)
            p.setPen(col("#ffb071")); p.setFont(QFont("Inter", 10)); p.drawText(QRectF(x + 8, y + 6, w - 10, h - 12), Qt.AlignCenter, self.screen_text if hasattr(self, "screen_text") else "")
        if self.prof.get("dynamic") and not self.controls:
            p.setPen(col("#8d867c")); p.setFont(QFont("Inter", 13))
            p.drawText(QRectF(0, 0, W, H), Qt.AlignCenter, "Пошевелите любую ручку, нажмите кнопку или клавишу —\nконтрол появится на схеме, и ему можно назначить действие")
        for c in self.controls: self._draw(p, c)
        if getattr(self, "dimmed", False):
            p.setPen(Qt.NoPen); p.setBrush(overlay()); p.drawRoundedRect(QRectF(4, 4, W - 8, H - 8), 22, 22)
            what = "клавиатура свободна" if any(c["kind"] == "white" for c in self.controls) else "устройство свободно"
            p.setPen(col("#d8d3cc")); p.setFont(QFont("Inter", 20, QFont.Bold)); p.drawText(QRectF(0, 0, W, H), Qt.AlignCenter, f"МАКРОСЫ ВЫКЛЮЧЕНЫ\n{what} для FL Studio")
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
        self._badge(p, c)
        if self.calib_target == c["id"]:
            ph = (time.monotonic() * 2) % 1.0
            p.setBrush(Qt.NoBrush); p.setPen(QPen(col("#ff8a2a"), 3 + 2 * ph))
            p.drawRoundedRect(c["rect"].adjusted(-8 - 4 * ph, -8 - 4 * ph, 8 + 4 * ph, 8 + 4 * ph), 12, 12)

    def _badge(self, p, c):
        """«?» — номер не подтверждён документацией (или неизвестен): пропадает после движения контрола или калибровки."""
        if c["kind"] in ("white", "black") or c.get("verify", "official") in D.VERIFIED: return
        if c["id"] in self.seen or c["id"] in self.calib: return
        r = c["rect"]; unknown = self.trig(c) is None
        d = QRectF(r.x() - 6, r.y() - 6, 14, 14)
        p.setPen(Qt.NoPen); p.setBrush(col("#ff5a4a") if unknown else col("#6b655d")); p.drawEllipse(d)
        p.setPen(col("#111")); p.setFont(QFont("Inter", 7, QFont.Bold)); p.drawText(d, Qt.AlignCenter, "?")

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
            p.drawText(r, Qt.AlignCenter, c["short"] if "short" in c else self.label(c).replace("Пэд ", ""))
        elif k in ("knob", "encoder"):
            p.setBrush(blend(col("#2f2c29"), col("#ff8a2a"), gl * .5)); p.drawEllipse(r)
            p.setPen(Qt.NoPen); p.setBrush(col("#1a1918")); p.drawEllipse(r.adjusted(7, 7, -7, -7))
            v = self.values.get(c["id"], 0.5 if k == "encoder" else 0.0)
            import math
            ang = math.radians(225 - 270 * v); cx, cy, rad = r.center().x(), r.center().y(), r.width() / 2 - 10
            p.setPen(QPen(col("#ff8a2a") if (gl or k == "knob") else col("#cfc8be"), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
            p.setPen(col("#a39b90")); p.setFont(QFont("Inter", 8))
            p.drawText(QRectF(r.x() - 20, r.bottom() + 1, r.width() + 40, 16), Qt.AlignCenter, (c.get("short") or c["label"].replace("Ручка ", "")) if k == "knob" else c.get("short", ""))
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
            p.setPen(col("#8d867c")); p.setFont(QFont("Inter", 7)); p.drawText(QRectF(r.x() - 10, r.bottom() + 2, r.width() + 20, 14), Qt.AlignCenter, c.get("short") or ("Pitch" if c["id"] == "pitch" else "Mod"))
        elif k == "button":
            p.setBrush(blend(col("#34312d"), col("#ff8a2a"), gl)); p.drawRoundedRect(r, 6, 6)
            p.setPen(col("#cfc8be")); p.setFont(QFont("Inter", 7 if r.height() < 28 else 9)); p.drawText(r, Qt.AlignCenter, c.get("short", "Клик"))
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
