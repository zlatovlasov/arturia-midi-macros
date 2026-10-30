import copy, json, sys, time, threading
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QRectF, QSize, Property, QPropertyAnimation
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDialog, QFormLayout, QLineEdit, QSpinBox, QPlainTextEdit, QCheckBox, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu, QFileDialog, QMessageBox, QInputDialog, QFrame, QToolButton, QDialogButtonBox, QSizePolicy, QScrollArea)
import config as C
from engine import Engine, norm_msg, trigger_from, describe_trigger, CC_MODES, NOTE_MODES
from actions import ACTIONS, label, Runner, normalize_urls, MAX_LINKS, find_browsers
from presets import minilab3_profile, is_minilab3, maybe_minilab_port
from leds import LedOut, compute_pad_colors, PALETTE
from macro import SCENE_STEPS
from midi_io import MidiHub, Worker, list_inputs
from controller import MacroController, fl_is_running
from device import DeviceView
from picker import ActionPicker, ActionButton
from calib import Calibration, ORDER as CALIB_ORDER
import calib as CAL
import theme
from theme import col

QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 14px; color: #ece9e4; }
QMainWindow, QDialog, QWidget#root { background: #141312; }
QFrame#topbar { background: #1b1a18; border-bottom: 1px solid #2b2926; }
QFrame#card { background: #1c1b19; border: 1px solid #2c2a27; border-radius: 14px; }
QLabel#h1 { font-size: 20px; font-weight: 700; }
QLabel#h2 { font-size: 17px; font-weight: 600; }
QLabel#muted { color: #9a938a; }
QLabel#pill { border-radius: 12px; padding: 4px 12px; font-weight: 600; }
QPushButton, QToolButton { background: #2a2825; border: 1px solid #3a3733; border-radius: 9px; padding: 8px 14px; }
QPushButton:hover, QToolButton:hover { background: #34312d; }
QPushButton#primary { background: #ff8a2a; color: #141312; border: none; font-weight: 700; }
QPushButton#primary:hover { background: #ff9c48; }
QPushButton#learn[active="true"] { background: #ff8a2a; color: #141312; }
QPushButton#danger { color: #ff9a8a; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit { background: #111110; border: 1px solid #34312d; border-radius: 8px; padding: 6px 8px; }
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus { border-color: #ff8a2a; }
QComboBox QAbstractItemView { background: #1c1b19; selection-background-color: #3a352f; padding: 4px; }
QListWidget { background: #111110; border: 1px solid #2c2a27; border-radius: 10px; padding: 4px; }
QListWidget::item { padding: 6px; border-radius: 6px; }
QListWidget::item:selected { background: #3a332b; color: #ffd2aa; }
QCheckBox::indicator { width: 18px; height: 18px; }
QMenu { background: #1c1b19; border: 1px solid #34312d; padding: 6px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; } QMenu::item:selected { background: #3a332b; }
QScrollArea { border: none; background: transparent; }
QToolButton#tile { background: #1c1b19; border: 1px solid #34312d; border-radius: 16px; padding: 14px 8px; font-size: 15px; font-weight: 600; }
QToolButton#tile:hover { background: #2a2825; border-color: #ff8a2a; }
QToolButton#tile[current="true"] { border: 2px solid #ff8a2a; }
QPushButton#actbtn { text-align: left; padding: 9px 12px; background: #111110; border: 1px solid #34312d; font-weight: 600; }
QPushButton#actbtn:hover { border-color: #ff8a2a; }
QListWidget#actions::item { padding: 8px 10px; margin: 2px 0; }
QListWidget#actions::item:hover { background: #24221f; }
QFrame#monitor { background: #111110; border: 1px solid #2c2a27; border-radius: 10px; }
QLabel#mono { font-family: 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 12px; color: #d8d2c8; }
QLabel#calbig { font-size: 22px; font-weight: 700; color: #ff8a2a; }
QToolButton#mini { padding: 0; min-width: 26px; min-height: 26px; font-size: 13px; }
"""

MODE_RU = {"press": "Нажатие", "release": "Отпускание", "tap": "Короткое нажатие", "long": "Долгое нажатие",
           "hold": "Удержание (вкл/выкл)", "absolute": "Абсолютный", "relative_offset64": "Энкодер: 64 = центр",
           "relative_twos": "Энкодер: 1/127", "relative_signbit": "Энкодер: знак. бит", "abs_to_rel": "Ручка как энкодер",
           "button": "Как кнопка (≥64)"}
CAT_COL = {"Общее": "#77716a", "Запуск": "#ff8a2a", "Клавиатура": "#e8d6b0", "Медиа": "#d77a5a", "Звук": "#f2b84b",
           "Окна": "#b9a58c", "Система": "#c98d6e", "Сцены": "#e8a25a", "Голос": "#d9c27a", "Профили": "#e0e0d8"}


def tray_icon(on):
    pm = QPixmap(64, 64); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(col("#ff8a2a" if on else "#6b6660")); p.setPen(Qt.NoPen); p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setBrush(col("#141312"))
    for i, x in enumerate((14, 27, 40)):
        p.drawRoundedRect(x, 16 if i != 1 else 26, 10, 32 if i != 1 else 22, 3, 3)
    p.end(); return QIcon(pm)


def cat_icon(cat):
    pm = QPixmap(18, 18); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(col(CAT_COL.get(cat, "#999"))); p.setPen(Qt.NoPen); p.drawRoundedRect(2, 2, 14, 14, 4, 4)
    p.setPen(col("#141312")); f = QFont("Inter", 8, QFont.Bold); p.setFont(f); p.drawText(QRectF(2, 2, 14, 14), Qt.AlignCenter, cat[0])
    p.end(); return QIcon(pm)


class Switch(QWidget):
    toggled = Signal(bool)
    def __init__(self):
        super().__init__(); self.on = True; self.setFixedSize(236, 46); self.setCursor(Qt.PointingHandCursor)
    def setChecked(self, v): self.on = bool(v); self.update()
    def mousePressEvent(self, e): self.on = not self.on; self.update(); self.toggled.emit(self.on)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(col("#ff8a2a" if self.on else "#4a4640"), 1.5)); p.setBrush(col("#2a1d12" if self.on else "#1f1e1c"))
        p.drawRoundedRect(r, 23, 23)
        k = QRectF(self.width() - 44 if self.on else 4, 4, 38, 38)
        p.setPen(Qt.NoPen); p.setBrush(col("#ff8a2a" if self.on else "#77716a")); p.drawEllipse(k)
        p.setPen(col("#ffd2aa" if self.on else "#bdb6ad")); p.setFont(QFont("Inter", 13, QFont.Bold))
        p.drawText(QRectF(20 if self.on else 54, 0, 170, self.height()), Qt.AlignVCenter | Qt.AlignLeft, "МАКРОСЫ ВКЛ" if self.on else "ВЫКЛ")
        p.end()


class UrlList(QWidget):
    """Список ссылок: добавить / удалить / переставить, проверка и автодобавление https://."""
    def __init__(self, urls):
        super().__init__(); self.L = QVBoxLayout(self); self.L.setContentsMargins(0, 0, 0, 0); self.L.setSpacing(6)
        self.rows = []; self.box = QVBoxLayout(); self.box.setSpacing(6); self.L.addLayout(self.box)
        self.add = QPushButton("+ Добавить ссылку"); self.add.clicked.connect(lambda: self.add_row("", focus=True)); self.L.addWidget(self.add)
        self.info = QLabel(""); self.info.setObjectName("muted"); self.L.addWidget(self.info)
        for u in (urls or [""]): self.add_row(u)

    def add_row(self, text, focus=False):
        if len(self.rows) >= MAX_LINKS: return
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
        num = QLabel(); num.setObjectName("muted"); num.setFixedWidth(18); h.addWidget(num)
        e = QLineEdit(text); e.setCursorPosition(0); e.setPlaceholderText("spb-4.ru"); e.editingFinished.connect(lambda e=e: self.check(e)); h.addWidget(e, 1)
        for t, fn in (("↑", -1), ("↓", 1)):
            b = QToolButton(); b.setObjectName("mini"); b.setText(t); b.setFixedWidth(30); b.clicked.connect(lambda _=False, w=w, d=fn: self.move(w, d)); h.addWidget(b)
        x = QToolButton(); x.setObjectName("mini"); x.setText("✕"); x.setFixedWidth(30); x.clicked.connect(lambda _=False, w=w: self.remove(w)); h.addWidget(x)
        w.edit, w.num = e, num; self.rows.append(w); self.box.addWidget(w); self.renum()
        if focus: e.setFocus()

    def check(self, e):
        t = e.text().strip()
        if not t: e.setStyleSheet(""); return
        ok, bad = normalize_urls([t])
        if ok: e.setText(ok[0]); e.setStyleSheet("")
        else: e.setStyleSheet("border: 1px solid #e5484d;")
        self.renum()

    def move(self, w, d):
        i = self.rows.index(w); j = i + d
        if 0 <= j < len(self.rows):
            self.rows[i].edit.text(); a, b = self.rows[i].edit.text(), self.rows[j].edit.text()
            self.rows[i].edit.setText(b); self.rows[j].edit.setText(a)

    def remove(self, w):
        if len(self.rows) == 1: w.edit.clear(); return
        self.rows.remove(w); w.setParent(None); w.deleteLater(); self.renum()

    def renum(self):
        for i, w in enumerate(self.rows): w.num.setText(str(i + 1))
        self.add.setEnabled(len(self.rows) < MAX_LINKS)
        ok, bad = normalize_urls(self.value())
        self.info.setText(f"Откроется ссылок: {len(ok)} из {MAX_LINKS}" + (f" · ошибка: {', '.join(bad)}" if bad else ""))

    def value(self):
        return [w.edit.text().strip() for w in self.rows if w.edit.text().strip()]


class StepList(QWidget):
    """Шаги сцены: тип шага + значение, добавить/удалить/переставить."""
    def __init__(self, steps):
        super().__init__(); self.L = QVBoxLayout(self); self.L.setContentsMargins(0, 0, 0, 0); self.L.setSpacing(6)
        self.rows = []; self.box = QVBoxLayout(); self.box.setSpacing(6); self.L.addLayout(self.box)
        add = QPushButton("+ Добавить шаг"); add.clicked.connect(lambda: self.add_row({"do": "open", "arg": ""})); self.L.addWidget(add)
        for st in steps or []: self.add_row(st)

    def add_row(self, st):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
        num = QLabel(); num.setObjectName("muted"); num.setFixedWidth(18); h.addWidget(num)
        cb = QComboBox(); cb.setFixedWidth(190)
        for k, (ru, _) in SCENE_STEPS.items(): cb.addItem(ru, k)
        cb.setCurrentIndex(max(0, cb.findData(st.get("do")))); h.addWidget(cb)
        e = QLineEdit(str(st.get("arg", ""))); e.setCursorPosition(0); e.setPlaceholderText(SCENE_STEPS.get(st.get("do"), ("", ""))[1]); h.addWidget(e, 1)
        cb.currentIndexChanged.connect(lambda _=0, cb=cb, e=e: e.setPlaceholderText(SCENE_STEPS[cb.currentData()][1]))
        for t, d in (("↑", -1), ("↓", 1)):
            b = QToolButton(); b.setObjectName("mini"); b.setText(t); b.setFixedWidth(28); b.clicked.connect(lambda _=False, w=w, d=d: self.move(w, d)); h.addWidget(b)
        x = QToolButton(); x.setObjectName("mini"); x.setText("✕"); x.setFixedWidth(28); x.clicked.connect(lambda _=False, w=w: self.remove(w)); h.addWidget(x)
        w.cb, w.edit, w.num = cb, e, num; self.rows.append(w); self.box.addWidget(w); self.renum()

    def move(self, w, d):
        i = self.rows.index(w); j = i + d
        if 0 <= j < len(self.rows):
            a, b = self.rows[i], self.rows[j]
            va, vb = (a.cb.currentIndex(), a.edit.text()), (b.cb.currentIndex(), b.edit.text())
            a.cb.setCurrentIndex(vb[0]); a.edit.setText(vb[1]); b.cb.setCurrentIndex(va[0]); b.edit.setText(va[1])

    def remove(self, w):
        self.rows.remove(w); w.setParent(None); w.deleteLater(); self.renum()

    def renum(self):
        for i, w in enumerate(self.rows): w.num.setText(str(i + 1))

    def value(self):
        return [{"do": w.cb.currentData(), "arg": w.edit.text().strip()} for w in self.rows]


class Swatches(QWidget):
    picked = Signal(str)
    def __init__(self, current):
        super().__init__(); h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(5)
        self.cur = current or ""; self.btns = {}
        for name, hx in [("Авто", "")] + list(PALETTE.items()):
            b = QToolButton(); b.setObjectName("mini"); b.setToolTip(name); b.setFixedSize(26, 26); b.setCheckable(True)
            b.clicked.connect(lambda _=False, hx=hx: self.pick(hx)); self.btns[hx] = b; h.addWidget(b)
            b.setText("A" if not hx else "")
        h.addStretch(1); self.refresh()
    def pick(self, hx): self.cur = hx; self.refresh(); self.picked.emit(hx)
    def refresh(self):
        for hx, b in self.btns.items():
            sel = hx == self.cur
            b.setChecked(sel)
            bg = hx if hx else "transparent"
            b.setStyleSheet(f"QToolButton {{ background: {bg}; border-radius: 13px; padding: 0; border: {'3px solid ' + theme.hx('#ff8a2a') if sel else '1px solid ' + theme.hx('#4a4640')}; }}")


class Bus(QObject):
    midi = Signal(str, object)
    note = Signal(str)
    toggle = Signal()
    fl = Signal(bool)
    leds = Signal(dict)
    state = Signal(dict)
    vbcable = Signal()


class Editor(QFrame):
    """Правая панель: назначения выбранного контрола."""
    changed = Signal()

    def __init__(self, main):
        super().__init__(); self.setObjectName("card"); self.main = main
        self.control = None; self.trig = None; self.m = None; self.learning = False; self.param_w = {}
        L = QVBoxLayout(self); L.setContentsMargins(20, 18, 20, 18); L.setSpacing(10)
        self.title = QLabel("Выберите контрол"); self.title.setObjectName("h2"); L.addWidget(self.title)
        self.sub = QLabel("Кликните по пэду, ручке, фейдеру или клавише на схеме — или просто коснитесь его на клавиатуре.")
        self.sub.setObjectName("muted"); self.sub.setWordWrap(True); L.addWidget(self.sub)
        self.colrow = QWidget(); cr = QHBoxLayout(self.colrow); cr.setContentsMargins(0, 0, 0, 0)
        cl = QLabel("Цвет пэда"); cl.setFixedWidth(84); cr.addWidget(cl); self.sw_holder = QHBoxLayout(); cr.addLayout(self.sw_holder, 1)
        L.addWidget(self.colrow); self.colrow.hide(); self.swatches = None
        self.list = QListWidget(); self.list.setMaximumHeight(96); self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.list.setTextElideMode(Qt.ElideRight); self.list.currentRowChanged.connect(self.pick); L.addWidget(self.list)
        row = QHBoxLayout()
        self.addb = QPushButton("+ Ещё действие"); self.addb.clicked.connect(self.add_new); row.addWidget(self.addb)
        self.learn = QPushButton("Назначить заново"); self.learn.setObjectName("learn"); self.learn.clicked.connect(self.toggle_learn); row.addWidget(self.learn)
        L.addLayout(row)
        self.form_w = QWidget(); f = QFormLayout(self.form_w); f.setContentsMargins(0, 6, 0, 0); f.setVerticalSpacing(10); self.f = f
        self.name = QLineEdit(); f.addRow("Название", self.name)
        self.act = ActionButton(); self.act.changed.connect(lambda _: self._act_changed()); f.addRow("Действие", self.act)
        self.mode = QComboBox(); f.addRow("Режим", self.mode); self.mode.currentIndexChanged.connect(lambda _: self._upd_long())
        vel = QHBoxLayout(); self.vmin = QSpinBox(); self.vmax = QSpinBox()
        for s in (self.vmin, self.vmax): s.setRange(1, 127); vel.addWidget(s)
        self.vel_lbl = QLabel("Сила удара"); f.addRow(self.vel_lbl, vel)
        self.long = QSpinBox(); self.long.setRange(100, 5000); self.long.setSuffix(" мс"); self.long_lbl = QLabel("Долгое нажатие"); f.addRow(self.long_lbl, self.long)
        self.pf = QFormLayout(); self.pf.setVerticalSpacing(10); f.addRow(self.pf)
        L.addWidget(self.form_w)
        self.hint = QLabel(""); self.hint.setObjectName("muted"); self.hint.setWordWrap(True); L.addWidget(self.hint)
        L.addStretch(1)
        b = QHBoxLayout()
        self.test = QPushButton("▶  Проверить"); self.test.clicked.connect(self.do_test)
        self.dele = QPushButton("Удалить"); self.dele.setObjectName("danger"); self.dele.clicked.connect(self.do_delete)
        self.save = QPushButton("Сохранить"); self.save.setObjectName("primary"); self.save.clicked.connect(self.do_save)
        b.addWidget(self.test); b.addWidget(self.dele); b.addStretch(1); b.addWidget(self.save); L.addLayout(b)
        self.set_enabled(False)

    def set_enabled(self, on):
        for w in (self.form_w, self.test, self.dele, self.save, self.learn): w.setEnabled(on)
        self.addb.setEnabled(self.trig is not None)

    def mappings_for(self, trig):
        out = []
        for m in self.main.cur_list():
            t = m.get("trigger", {})
            if t.get("type") == trig["type"] and (trig["type"] == "pitch" or t.get("number") == trig["number"]) and (trig["channel"] is None or t.get("channel") in (None, trig["channel"])):
                out.append(m)
        return out

    def show_control(self, title, trig, sel_id=None):
        self.control_title, self.trig = title, trig
        self.title.setText(title); self.sub.setText(describe_trigger(trig))
        is_pad = trig["type"] == "note" and trig["channel"] == 9 and 36 <= trig["number"] <= 51
        self.colrow.setVisible(is_pad)
        if is_pad:
            if self.swatches: self.swatches.setParent(None)
            cur = self.main.cfg.setdefault("pad_colors", {}).get(self.main.cfg["active_profile"], {}).get(str(trig["number"]), "")
            self.swatches = Swatches(cur); self.swatches.picked.connect(lambda hx, n=trig["number"]: self.main.set_pad_color(n, hx))
            self.sw_holder.addWidget(self.swatches)
        self.items = self.mappings_for(trig)
        self.list.blockSignals(True); self.list.clear()
        for m in self.items:
            it = QListWidgetItem(cat_icon(ACTIONS.get(m["action"]["type"], ("", "", "Общее"))[2]), f"{label(m['action'])}   ·  {MODE_RU.get(m.get('mode'), '')}")
            self.list.addItem(it)
        if not self.items: self.list.addItem("Пока ничего не назначено — нажмите «+ Ещё действие»")
        self.list.blockSignals(False)
        idx = next((i for i, m in enumerate(self.items) if m["id"] == sel_id), 0)
        if self.items: self.list.setCurrentRow(idx); self.pick(idx)
        else: self.m = None; self.set_enabled(False)
        self.addb.setEnabled(True)

    def add_new(self):
        if not self.trig: return
        kind = "press" if self.trig["type"] == "note" else "absolute"
        m = {"id": C.new_id(), "name": self.control_title, "trigger": dict(self.trig), "mode": kind, "action": {"type": "none", "params": {}}}
        self.main.cur_list().append(m); self.main.persist(); self.show_control(self.control_title, self.trig, m["id"])

    def pick(self, i):
        if not (0 <= i < len(getattr(self, "items", []))): return
        self.m = self.items[i]; m = self.m; self.set_enabled(True)
        self.name.setText(m.get("name", ""))
        t = m["trigger"]["type"]; modes = NOTE_MODES if t == "note" else CC_MODES if t == "cc" else ["absolute"] if t == "pitch" else ["press"]
        self.mode.clear()
        for md in modes: self.mode.addItem(MODE_RU[md], md)
        self.mode.setCurrentIndex(max(0, self.mode.findData(m.get("mode", modes[0]))))
        self.vmin.setValue(m.get("velocity_min", 1)); self.vmax.setValue(m.get("velocity_max", 127)); self.long.setValue(m.get("long_ms", 500))
        note = t == "note"
        for w in (self.vmin, self.vmax, self.vel_lbl): w.setVisible(note)
        self._upd_long()
        self.act.set(m["action"].get("type", "none"))
        self.build_params()

    def _act_changed(self):
        if self.act.currentData() == "voice" and self.mode.findData("hold") >= 0:
            self.mode.setCurrentIndex(self.mode.findData("hold"))
        self.build_params()

    def _upd_long(self):
        v = self.mode.currentData() in ("tap", "long")
        self.long.setVisible(v); self.long_lbl.setVisible(v)

    def build_params(self):
        while self.pf.rowCount(): self.pf.removeRow(0)
        self.param_w = {}; k = self.act.currentData() or "none"
        cur = self.m["action"].get("params", {}) if self.m and self.m["action"].get("type") == k else {}
        for pname, ru, kind, default, choices in ACTIONS[k][1]:
            v = cur.get(pname, default)
            if kind == "int": w = QSpinBox(); w.setRange(-100, 1000); w.setValue(int(v))
            elif kind == "choice": w = QComboBox(); w.addItems(choices); w.setCurrentText(str(v))
            elif kind == "text": w = QPlainTextEdit(str(v)); w.setFixedHeight(96)
            elif kind == "urls": w = UrlList(list(v))
            elif kind == "steps": w = StepList(list(v))
            else: w = QLineEdit(str(v))
            if pname == "browser":
                found = find_browsers(); w.clear()
                for b in ["default"] + [b for b in ("chrome", "edge", "firefox", "yandex") if b in found or sys.platform != "win32"]:
                    w.addItem({"default": "По умолчанию", "chrome": "Chrome", "edge": "Edge", "firefox": "Firefox", "yandex": "Яндекс Браузер"}[b], b)
                w.setCurrentIndex(max(0, w.findData(v)))
            self.param_w[pname] = (kind, w)
            if kind in ("urls", "steps"): self.pf.addRow(QLabel(ru)); self.pf.addRow(w)
            else: self.pf.addRow(ru, w)
        hints = {"macro": "Шаги по строке: hotkey ctrl+c · text Привет · wait 300 · open notepad.exe · cmd … · ps … · media next · volume -5 · mic_mute · desktop next",
                 "hotkey": "Примеры: ctrl+shift+s, alt+f4, windows+e. Для OBS удобны F13–F24: задайте их в OBS → Горячие клавиши.",
                 "master_volume": "Фейдер — точное значение, энкодер — шагами, кнопка — шаг (минус = тише).",
                 "open_links": "Одно нажатие открывает все ссылки по очереди. https:// добавится сам. Пауза нужна, чтобы браузер не путал порядок вкладок.",
                 "scene": "Сцена выполняет шаги сверху вниз одним нажатием: открыть программы и ссылки, выставить громкость, микрофон, паузы.",
                 "voice": "Режим «Удержание»: держите пэд и говорите, отпустите — текст вставится в активное окно. windows — встроенный ввод Win+H (ничего ставить не нужно, нужен интернет); vosk — офлайн, при первом использовании скачается русская модель ~45 МБ.",
                 "voice_pitch": "Центр полосы — обычный голос, вверх — выше, вниз — ниже. Звук идёт в виртуальный микрофон VB-Cable: в Discord/OBS/Telegram выберите микрофон «CABLE Output». Включается в Настройках.",
                 "macros_off": "Закрывает MIDI-порт, чтобы клавиатуру мог взять FL Studio. Включить обратно — Ctrl+Alt+M или кнопкой в окне/трее."}
        self.hint.setText(hints.get(k, ""))

    def collect(self):
        m = self.m; m["name"] = self.name.text().strip() or self.control_title
        m["mode"] = self.mode.currentData(); m["velocity_min"], m["velocity_max"], m["long_ms"] = self.vmin.value(), self.vmax.value(), self.long.value()
        p = {}
        for n, (kind, w) in self.param_w.items():
            p[n] = (w.value() if kind in ("int", "urls", "steps") else (w.currentData() or w.currentText()) if kind == "choice"
                    else w.toPlainText() if kind == "text" else w.text())
        m["action"] = {"type": self.act.currentData() or "none", "params": p}

    def do_save(self):
        if not self.m: return
        self.collect(); self.main.persist(); self.show_control(self.control_title, self.trig, self.m["id"]); self.main.notify("Сохранено")

    def do_test(self):
        if self.m: self.collect(); self.main.runner(self.m["action"], {"kind": "trigger"})

    def do_delete(self):
        if self.m: self.main.cur_list().remove(self.m); self.main.persist(); self.show_control(self.control_title, self.trig)

    def toggle_learn(self):
        self.learning = not self.learning
        self.learn.setText("Жду контрол…" if self.learning else "Назначить заново")
        self.learn.setProperty("active", self.learning); self.learn.style().unpolish(self.learn); self.learn.style().polish(self.learn)

    def learned(self, ev):
        if not (self.learning and self.m): return False
        self.m["trigger"] = trigger_from(ev); self.toggle_learn(); self.main.persist()
        self.show_control(describe_trigger(self.m["trigger"]), self.m["trigger"], self.m["id"]); return True


class SettingsDialog(QDialog):
    def __init__(self, main):
        super().__init__(main); self.main = main; self.setWindowTitle("Настройки"); self.setMinimumWidth(520)
        cfg = main.cfg; L = QVBoxLayout(self); L.setSpacing(10)
        L.addWidget(QLabel("MIDI-входы (можно несколько):"))
        self.inputs = QListWidget(); self.inputs.setMaximumHeight(140); L.addWidget(self.inputs)
        names = list_inputs() or main.known_inputs
        for n in names:
            it = QListWidgetItem(n); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if n in cfg["inputs"] else Qt.Unchecked); self.inputs.addItem(it)
        if not names: self.inputs.addItem("Устройства не найдены — подключите клавиатуру")
        self.autostart = QCheckBox("Запускать вместе с Windows"); self.autostart.setChecked(cfg.get("autostart", True))
        self.start_off = QCheckBox("Стартовать в состоянии ВЫКЛ (порт свободен)"); self.start_off.setChecked(cfg.get("start_off", False))
        self.fl = QCheckBox("Автоматически выключать, пока открыт FL Studio"); self.fl.setChecked(cfg.get("auto_off_fl", False))
        self.allports = QCheckBox("Слушать все входы MiniLab (рекомендуется: ручки бывают на другом порту)"); self.allports.setChecked(cfg.get("all_minilab_ports", True))
        self.pitch = QCheckBox("Питч голоса на полосе Pitch (виртуальный микрофон VB-Cable)"); self.pitch.setChecked(cfg.get("voice_pitch_enabled", False))
        for w in (self.autostart, self.start_off, self.fl, self.allports, self.pitch): L.addWidget(w)
        f = QFormLayout(); self.hk = QLineEdit(cfg.get("hotkey", "ctrl+alt+m")); f.addRow("Горячая клавиша ВКЛ/ВЫКЛ", self.hk)
        self.theme = QComboBox(); self.theme.addItem("Тёмная (оранжевый акцент)", "dark"); self.theme.addItem("Светлая (фиолетовый акцент)", "light")
        self.theme.setCurrentIndex(max(0, self.theme.findData(cfg.get("theme", "dark")))); f.addRow("Тема", self.theme)
        self.led = QComboBox(); self.led.addItem("Авто (MiniLab 3 по USB)", "auto"); self.led.addItem("Не подсвечивать", "none")
        try:
            import mido; outs = mido.get_output_names()
        except Exception: outs = getattr(main, "fake_outputs", [])
        for o in outs: self.led.addItem(o, o)
        self.led.setCurrentIndex(max(0, self.led.findData(cfg.get("led_output", "auto")))); f.addRow("Подсветка пэдов (выход)", self.led)
        L.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Сохранить")
        bb.button(QDialogButtonBox.Ok).setObjectName("primary"); bb.button(QDialogButtonBox.Cancel).setText("Отмена")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); L.addWidget(bb)

    def apply(self):
        cfg = self.main.cfg
        sel = [self.inputs.item(i).text() for i in range(self.inputs.count()) if self.inputs.item(i).flags() & Qt.ItemIsUserCheckable and self.inputs.item(i).checkState() == Qt.Checked]
        cfg["inputs"] = sel; cfg["start_off"] = self.start_off.isChecked(); cfg["auto_off_fl"] = self.fl.isChecked()
        cfg["hotkey"] = self.hk.text().strip().lower() or "ctrl+alt+m"
        cfg["led_output"] = self.led.currentData()
        cfg["all_minilab_ports"] = self.allports.isChecked()
        if cfg.get("voice_pitch_enabled", False) != self.pitch.isChecked():
            cfg["voice_pitch_enabled"] = self.pitch.isChecked(); self.main.apply_pitch(check=True)
        if cfg.get("theme", "dark") != self.theme.currentData():
            cfg["theme"] = self.theme.currentData(); self.main.apply_theme()
        if cfg.get("autostart") != self.autostart.isChecked():
            cfg["autostart"] = self.autostart.isChecked()
            try: C.set_autostart(cfg["autostart"])
            except Exception as e: self.main.notify(f"Автозапуск: {e}")


class MidiMonitor(QFrame):
    """Полоска «что приходит с клавиатуры»: последние сырые сообщения (порт, тип, канал, номер, значение)."""
    def __init__(self, rows=4):
        super().__init__(); self.setObjectName("monitor"); self.rows = rows; self.lines = []
        h = QHBoxLayout(self); h.setContentsMargins(12, 6, 12, 6); h.setSpacing(12)
        t = QLabel("MIDI-монитор"); t.setObjectName("muted"); t.setFixedWidth(104); t.setAlignment(Qt.AlignTop); h.addWidget(t)
        self.txt = QLabel("Пока тихо — покрутите ручку или нажмите пэд"); self.txt.setObjectName("mono"); self.txt.setTextFormat(Qt.PlainText)
        self.txt.setMinimumHeight(rows * 17); h.addWidget(self.txt, 1)

    @staticmethod
    def fmt(port, msg):
        ev = norm_msg(msg)
        port = (port or "")[:26]
        if ev is None:
            return f"{port:<26}  {getattr(msg, 'type', '?')}"
        kind = {"note": "Note " + ("on " if ev.get("on") else "off"), "cc": "CC", "pitch": "Pitch", "program": "Prog"}[ev["type"]]
        num = "" if ev["type"] == "pitch" else f"#{ev['number']:<3}"
        return f"{port:<26}  {kind:<9} кан.{ev['channel'] + 1:<2}  {num:<5} = {ev['value']}"

    def add(self, port, msg):
        if getattr(msg, "type", "") in ("clock", "active_sensing"): return
        self.lines.insert(0, self.fmt(port, msg)); del self.lines[self.rows:]
        self.txt.setText("\n".join(self.lines))


class CalibrationDialog(QDialog):
    """Мастер «Калибровка ручек»: по очереди подсвечивает контрол на схеме, ждёт движения, запоминает CC/канал."""
    def __init__(self, main):
        super().__init__(main); self.main = main; self.cal = Calibration(CALIB_ORDER)
        self.setWindowTitle("Калибровка ручек"); self.setMinimumSize(520, 380); self.setModal(False)
        L = QVBoxLayout(self); L.setContentsMargins(22, 20, 22, 18); L.setSpacing(10)
        h = QLabel("Калибровка ручек"); h.setObjectName("h1"); L.addWidget(h)
        info = QLabel("Покрутите контрол, который подсвечен на схеме. Программа запомнит, что реально шлёт ваша MiniLab, "
                      "и перенесёт на него все назначения. Если какого-то контрола нет — «Пропустить».")
        info.setWordWrap(True); info.setObjectName("muted"); info.setMinimumHeight(64); L.addWidget(info)
        self.step = QLabel(""); self.step.setObjectName("muted"); L.addWidget(self.step)
        self.big = QLabel(""); self.big.setObjectName("calbig"); L.addWidget(self.big)
        self.got = QLabel(""); self.got.setObjectName("mono"); self.got.setWordWrap(True); L.addWidget(self.got)
        b = QHBoxLayout()
        self.backb = QPushButton("← Назад"); self.backb.clicked.connect(self.back); b.addWidget(self.backb)
        self.skipb = QPushButton("Пропустить"); self.skipb.clicked.connect(self.skip); b.addWidget(self.skipb)
        b.addStretch(1)
        self.cancelb = QPushButton("Отмена"); self.cancelb.clicked.connect(self.reject); b.addWidget(self.cancelb)
        self.okb = QPushButton("Сохранить"); self.okb.setObjectName("primary"); self.okb.clicked.connect(self.finish); b.addWidget(self.okb)
        L.addLayout(b); self.refresh()

    def refresh(self):
        cur = self.cal.current(); n = len(self.cal.order)
        self.step.setText(f"Шаг {min(self.cal.i + 1, n)} из {n}")
        self.big.setText(f"Двигайте: {cur[1]}" if cur else "Готово! Нажмите «Сохранить»")
        self.main.dev.calib_target = cur[0] if cur else None
        if cur: self.main.dev.select_id(cur[0])
        rows = []
        for cid, lbl, _ in self.cal.order:
            r = self.cal.result.get(cid)
            if r: rows.append(f"{lbl:<30} {'Pitch' if r['type'] == 'pitch' else 'CC ' + str(r['number'])} · кан. {r['channel'] + 1}")
        self.got.setText("\n".join(rows[-6:]))
        self.skipb.setEnabled(cur is not None); self.backb.setEnabled(self.cal.i > 0)
        self.main.dev.update()

    def feed(self, ev):
        if self.cal.feed(ev): self.refresh(); return True
        return False

    def skip(self): self.cal.skip(); self.refresh()
    def back(self): self.cal.back(); self.refresh()

    def finish(self):
        n = CAL.apply(self.main.cfg, self.cal.result, self.main.dev.defaults())
        self.main.dev.set_calib(self.main.cfg.get("calib", {})); self.main.persist()
        self.main.notify(f"Калибровка сохранена: контролов {len(self.cal.result)}, назначений перенесено {n}")
        self.accept()

    def done(self, r):
        self.main.dev.calib_target = None; self.main.calib = None; self.main.dev.update()
        super().done(r)


class Main(QMainWindow):
    def __init__(self, cfg, backend, hub=None, save=True, inputs_fn=None):
        super().__init__()
        self.cfg, self.do_save = cfg, save
        self.list_inputs = inputs_fn or list_inputs; self.known_inputs = []
        self.setWindowTitle("MIDI Макросы — MiniLab 3"); self.setWindowIcon(tray_icon(True)); self.resize(1480, 860)
        self.bus = Bus()
        self.runner = Runner(backend, on_profile=self.switch_profile_async, notify=self.bus.note.emit, on_off=self.bus.toggle.emit)
        self.engine = Engine(cfg, self.runner)
        self.hub = hub or MidiHub()
        self.hub.listeners.append(lambda port, msg: self.bus.midi.emit(port, msg))
        self.ctl = MacroController(self.hub, cfg, self._inputs, self.bus.state.emit)
        self.led = LedOut(); self.runner.on_state = self.bus.leds.emit
        self.bus.midi.connect(self.on_midi_ui); self.bus.note.connect(self.notify)
        self.bus.leds.connect(lambda _: self.update_leds()); self.bus.state.connect(self.show_state); self.bus.toggle.connect(self.toggle_from_hotkey); self.bus.fl.connect(self.ctl.set_fl_running)
        self._profile_req = None
        self.calib = None
        self.runner.on_need_vbcable = self.bus.vbcable.emit; self.bus.vbcable.connect(self.offer_vbcable)
        self.runner.pitch_enabled = bool(cfg.get("voice_pitch_enabled", False)); self.runner.pitch_output = cfg.get("voice_pitch_output", "CABLE Input")

        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        L = QVBoxLayout(root); L.setContentsMargins(0, 0, 0, 0); L.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); T = QHBoxLayout(top); T.setContentsMargins(22, 12, 22, 12); T.setSpacing(14)
        t = QLabel("MIDI Макросы"); t.setObjectName("h1"); T.addWidget(t)
        T.addSpacing(18); T.addWidget(QLabel("Профиль"))
        self.prof = QComboBox(); self.prof.setMinimumWidth(220); self.prof.currentTextChanged.connect(self.profile_selected); T.addWidget(self.prof)
        pm = QToolButton(); pm.setText("⋯"); pm.setPopupMode(QToolButton.InstantPopup); menu = QMenu(pm)
        for txt, fn in (("Новый профиль", self.new_profile), ("Копия профиля", self.dup_profile), ("Удалить профиль", self.del_profile),
                        (None, None), ("Загрузить готовый MiniLab 3", self.add_minilab), ("Импорт…", self.do_import), ("Экспорт…", self.do_export)):
            if txt is None: menu.addSeparator(); continue
            a = menu.addAction(txt); a.triggered.connect(fn)
        pcm = menu.addMenu("Цвет профиля (подсветка)")
        for nm, hx in PALETTE.items():
            a = pcm.addAction(nm); a.triggered.connect(lambda _=False, hx=hx: self.set_profile_color(hx))
        pm.setMenu(menu); T.addWidget(pm)
        T.addStretch(1)
        self.port = QLabel(""); self.port.setObjectName("pill"); T.addWidget(self.port)
        self.sw = Switch(); self.sw.toggled.connect(lambda on: self.ctl.set_enabled(on)); T.addWidget(self.sw)
        gear = QPushButton("Настройки"); gear.clicked.connect(self.open_settings); T.addWidget(gear)
        L.addWidget(top)

        body = QHBoxLayout(); body.setContentsMargins(18, 16, 18, 10); body.setSpacing(16); L.addLayout(body, 1)
        leftw = QFrame(); leftw.setObjectName("card"); LL = QVBoxLayout(leftw); LL.setContentsMargins(16, 14, 16, 14)
        hl = QHBoxLayout(); hh = QLabel("Ваша MiniLab 3"); hh.setObjectName("h2"); hl.addWidget(hh); hl.addStretch(1)
        self.live = QLabel("Нажимайте контролы — схема повторяет их вживую"); self.live.setObjectName("muted"); hl.addWidget(self.live)
        LL.addLayout(hl)
        cb = QPushButton("Калибровка ручек"); cb.clicked.connect(self.open_calibration); hl.addWidget(cb)
        self.dev = DeviceView(); self.dev.set_calib(cfg.get("calib", {})); self.dev.selected.connect(self.control_selected); self.dev.on_bank = lambda: (self.refresh_mapped(), self.update_leds()); LL.addWidget(self.dev, 1)
        self.offmask = QLabel(""); self.offmask.setObjectName("muted"); self.offmask.setAlignment(Qt.AlignCenter); LL.addWidget(self.offmask)
        self.monitor = MidiMonitor(); LL.addWidget(self.monitor)
        body.addWidget(leftw, 3)
        self.editor = Editor(self); self.editor.setMinimumWidth(470); self.editor.setMaximumWidth(560); body.addWidget(self.editor, 1)
        self.ledhint = QLabel(""); self.ledhint.setObjectName("muted"); self.ledhint.setAlignment(Qt.AlignCenter); LL.addWidget(self.ledhint)
        self.statusL = QLabel(""); self.statusL.setObjectName("muted"); self.statusL.setContentsMargins(22, 0, 22, 10); L.addWidget(self.statusL)

        self.tray = QSystemTrayIcon(tray_icon(True), self)
        tm = QMenu()
        a = QAction("Открыть", self); a.triggered.connect(self.show_normal); tm.addAction(a)
        self.tray_toggle = QAction("Выключить макросы", self); self.tray_toggle.triggered.connect(lambda: self.ctl.toggle()); tm.addAction(self.tray_toggle)
        self.tray_prof = tm.addMenu("Профиль")
        a = QAction("Выход", self); a.triggered.connect(self.quit); tm.addAction(a)
        self.tray.setContextMenu(tm); self.tray.activated.connect(lambda r: self.show_normal() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

        self.fill_profiles(); self.ctl.apply(); self.update_leds()
        self.worker = Worker(self.hub, self.engine); self.worker.start()
        self.pt = QTimer(self); self.pt.timeout.connect(self.poll_profile); self.pt.start(100)
        self.hk_handle = None; self.register_hotkey()
        self._fl_stop = False; threading.Thread(target=self._fl_loop, daemon=True).start()
        QTimer.singleShot(400, self.maybe_suggest_minilab)
        self.dev.select_id("pad1")

    # ---------- общее
    def _inputs(self):
        n = self.list_inputs(); self.known_inputs = n
        if not self.cfg.get("inputs"):
            self.cfg["inputs"] = [x for x in n if is_minilab3(x)] or [x for x in n if maybe_minilab_port(x)] or n[:1]
        return n

    def persist(self):
        if self.do_save: C.save(self.cfg)
        self.refresh_mapped()

    def notify(self, text):
        self.statusL.setText(text)
        if self.isHidden() and self.tray.supportsMessages(): self.tray.showMessage("MIDI Макросы", text, tray_icon(self.ctl.enabled), 1500)

    def show_normal(self): self.show(); self.raise_(); self.activateWindow()
    def closeEvent(self, e): e.ignore(); self.hide(); self.notify("Работаю в трее")

    def quit(self):
        self._fl_stop = True; self.worker.running = False; self.runner.stop_pitch(); self.led.close(colors_on_release=["#7f7f7f"] * 8); self.hub.close(); self.persist(); QApplication.quit()

    # ---------- ВКЛ/ВЫКЛ
    def show_state(self, st):
        on = st["mode"] in ("on", "error")
        self.sw.setChecked(self.ctl.enabled)
        self.dev.dimmed = st["mode"] in ("off", "fl"); self.dev.update()
        self.update_leds()
        self.tray.setIcon(tray_icon(st["mode"] == "on")); self.setWindowIcon(tray_icon(st["mode"] == "on"))
        self.tray_toggle.setText("Выключить макросы" if self.ctl.enabled else "Включить макросы")
        hk = self.cfg.get("hotkey", "ctrl+alt+m").upper()
        if st["mode"] == "on":
            txt, bg, fg = f"● Порт: {', '.join(st['open'])}", "#2a1d12", "#ffb070"
            self.offmask.setText("")
        elif st["mode"] == "error":
            txt, bg, fg = "● Порт недоступен", "#3a1a16", "#ff9a8a"
            self.offmask.setText(st["errors"][0] if st["errors"] else "")
        elif st["mode"] == "fl":
            txt, bg, fg = "○ Пауза: открыт FL Studio", "#24221f", "#d8d2c8"
            self.offmask.setText("FL Studio запущен — порт отдан ему. Макросы включатся сами, когда FL закроется.")
        else:
            txt, bg, fg = "○ Порт свободен", "#24221f", "#bdb6ad"
            self.offmask.setText(f"Макросы выключены — MiniLab 3 работает как обычная MIDI-клавиатура (FL Studio и др.). Включить: {hk}")
        self.port.setText(txt); self.port.setStyleSheet(f"background:{theme.hx(bg)}; color:{theme.hx(fg)};")
        self.tray.setToolTip(f"MIDI Макросы — {'ВКЛ' if st['mode'] == 'on' else 'ВЫКЛ'}")
        self.notify({"on": "Макросы включены", "off": "Макросы выключены, порт свободен", "fl": "FL Studio открыт — макросы на паузе", "error": "Не удалось открыть порт"}[st["mode"]])

    def led_port_name(self):
        want = self.cfg.get("led_output", "auto")
        if want == "none": return None
        try:
            import mido; outs = mido.get_output_names()
        except Exception:
            outs = getattr(self, "fake_outputs", [])
        if want != "auto": return want if want in outs else None
        return LedOut.find_output(outs)

    def update_leds(self):
        on = self.ctl.state.get("mode") == "on"
        colors = compute_pad_colors(self.cfg, self.dev.bank, self.runner.state, enabled=True)
        self.dev.pad_colors = {f"pad{i + 1}": c for i, c in enumerate(colors)}; self.dev.update()
        name = self.led_port_name() if on else None
        if on and name and self.led.open(name):
            try: self.led.send(colors)
            except Exception as e: self.notify(f"Подсветка: {e}")
            self.ledhint.setText(f"Подсветка пэдов: {name} (экспериментально)")
        else:
            if self.led.port: self.led.close(colors_on_release=["#7f7f7f"] * 8)
            if self.cfg.get("led_output", "auto") == "none": self.ledhint.setText("Подсветка пэдов выключена в настройках — цвета только на схеме")
            elif on: self.ledhint.setText("Для подсветки на самой клавиатуре подключите MiniLab 3 по USB — пока цвета только на схеме")
            else: self.ledhint.setText("")

    def set_pad_color(self, note, hx):
        d = self.cfg.setdefault("pad_colors", {}).setdefault(self.cfg["active_profile"], {})
        if hx: d[str(note)] = hx
        else: d.pop(str(note), None)
        self.persist(); self.update_leds()

    def set_profile_color(self, hx):
        self.cfg.setdefault("profile_colors", {})[self.cfg["active_profile"]] = hx; self.persist(); self.update_leds()

    def apply_theme(self):
        theme.set_theme(self.cfg.get("theme", "dark"))
        QApplication.instance().setStyleSheet(theme.qss(QSS))
        self.show_state(self.ctl.state); self.editor.build_params() if self.editor.m else None
        if self.dev.sel: self.control_selected(self.dev.sel)
        self.dev.update(); self.sw.update()

    def toggle_from_hotkey(self): self.ctl.toggle()

    def register_hotkey(self):
        try:
            import keyboard
            if self.hk_handle is not None: keyboard.remove_hotkey(self.hk_handle)
            self.hk_handle = keyboard.add_hotkey(self.cfg.get("hotkey", "ctrl+alt+m"), self.bus.toggle.emit)
        except Exception as e:
            self.hk_handle = None
            if sys.platform == "win32": self.notify(f"Горячая клавиша не задана: {e}")

    def _fl_loop(self):
        while not self._fl_stop:
            if self.cfg.get("auto_off_fl"): self.bus.fl.emit(fl_is_running())
            time.sleep(2)

    def open_settings(self):
        d = SettingsDialog(self)
        if d.exec():
            d.apply(); self.persist(); self.register_hotkey(); self.ctl.apply(); self.update_leds()

    def maybe_suggest_minilab(self):
        if self.cfg.get("asked_minilab") or not any(maybe_minilab_port(n) for n in self.known_inputs): return
        self.cfg["asked_minilab"] = True; self.persist()
        if "MiniLab 3" in self.cfg["profiles"]:
            if self.cfg["active_profile"] != "MiniLab 3" and QMessageBox.question(self, "MiniLab 3", "Найдена MiniLab 3. Включить готовый профиль для неё?") == QMessageBox.Yes:
                self.prof.setCurrentText("MiniLab 3")
        elif QMessageBox.question(self, "MiniLab 3", "Найдена MiniLab 3. Добавить готовый профиль?") == QMessageBox.Yes:
            self.add_minilab()

    # ---------- MIDI в интерфейсе
    def open_calibration(self):
        if self.calib: self.calib.raise_(); return
        if self.ctl.state.get("mode") != "on":
            self.notify("Включите макросы — калибровке нужен открытый MIDI-порт")
        self.calib = CalibrationDialog(self); self.calib.show()

    def apply_pitch(self, check=False):
        on = bool(self.cfg.get("voice_pitch_enabled", False)); self.runner.pitch_enabled = on
        if not on: self.runner.stop_pitch(); self.notify("Питч голоса выключен"); return
        try:
            from voice_fx import VoicePitch
            ok = VoicePitch(output=self.cfg.get("voice_pitch_output", "CABLE Input")).available()
        except Exception:
            ok = False
        if not ok and check: self.offer_vbcable()
        elif ok: self.notify("Питч голоса включён — двигайте полосу Pitch")

    def offer_vbcable(self):
        self.cfg["voice_pitch_enabled"] = False; self.runner.pitch_enabled = False; self.persist()
        mb = QMessageBox(self); mb.setWindowTitle("Нужен VB-Cable"); mb.setIcon(QMessageBox.Information)
        mb.setText("Для питча голоса нужен бесплатный виртуальный микрофон VB-Cable.")
        mb.setInformativeText("1. Откроется официальный сайт vb-audio.com — скачайте «VBCABLE_Driver_Pack».\n"
                              "2. Распакуйте и запустите VBCABLE_Setup_x64.exe от администратора, нажмите Install, перезагрузите ПК.\n"
                              "3. Включите питч в Настройках. В Discord/OBS/Telegram выберите микрофон «CABLE Output».")
        go = mb.addButton("Открыть vb-audio.com", QMessageBox.AcceptRole); mb.addButton("Позже", QMessageBox.RejectRole)
        mb.exec()
        if mb.clickedButton() is go:
            import webbrowser; from voice_fx import VB_URL; webbrowser.open(VB_URL)

    def on_midi_ui(self, port, msg):
        self.monitor.add(port, msg)
        ev = norm_msg(msg)
        if not ev: return
        if self.calib and ev["type"] in ("cc", "pitch"):
            self.calib.feed(ev); self.dev.on_event(ev); return
        if ev["type"] == "note" and not ev["on"]:
            self.dev.on_event(ev); return
        if self.editor.learned(ev): return
        c = self.dev.on_event(ev)
        self.live.setText(f"{describe_trigger(trigger_from(ev))}  =  {ev['value']}")
        if c and c is not self.dev.sel and not self.editor.learning:
            self.dev.sel = c; self.control_selected(c)

    def control_selected(self, c):
        self.editor.show_control(self.dev.label(c), self.dev.trig(c))

    def refresh_mapped(self):
        self.dev.mapped = {c["id"] for c in self.dev.controls
                           if any(m["action"].get("type") != "none" for m in self.editor.mappings_for(self.dev.trig(c)))}
        self.dev.update()

    # ---------- профили
    def cur_list(self): return self.cfg["profiles"][self.cfg["active_profile"]]

    def fill_profiles(self):
        self.prof.blockSignals(True); self.prof.clear(); self.prof.addItems(list(self.cfg["profiles"]))
        self.prof.setCurrentText(self.cfg["active_profile"]); self.prof.blockSignals(False)
        self.tray_prof.clear()
        for n in self.cfg["profiles"]:
            a = self.tray_prof.addAction(n); a.setCheckable(True); a.setChecked(n == self.cfg["active_profile"])
            a.triggered.connect(lambda _=False, n=n: self.prof.setCurrentText(n))
        self.refresh_mapped()
        if self.dev.sel: self.control_selected(self.dev.sel)

    def profile_selected(self, name):
        if name and name in self.cfg["profiles"]:
            self.engine.set_profile(name); self.persist(); self.fill_profiles(); self.update_leds(); self.notify(f"Профиль: {name}")

    def switch_profile_async(self, name, step): self._profile_req = (name, step)

    def poll_profile(self):
        if self._profile_req:
            name, step = self._profile_req; self._profile_req = None
            n = self.engine.set_profile(name, step); self.persist(); self.fill_profiles(); self.update_leds(); self.notify(f"Профиль: {n}")

    def new_profile(self):
        n, ok = QInputDialog.getText(self, "Новый профиль", "Название:")
        if ok and n and n not in self.cfg["profiles"]:
            self.cfg["profiles"][n] = []; self.fill_profiles(); self.prof.setCurrentText(n)

    def dup_profile(self):
        cur = self.cfg["active_profile"]; n = cur + " (копия)"
        self.cfg["profiles"][n] = copy.deepcopy(self.cfg["profiles"][cur])
        for m in self.cfg["profiles"][n]: m["id"] = C.new_id()
        self.fill_profiles(); self.prof.setCurrentText(n)

    def del_profile(self):
        if len(self.cfg["profiles"]) < 2: return
        cur = self.cfg["active_profile"]
        if QMessageBox.question(self, "Удалить", f"Удалить профиль «{cur}»?") == QMessageBox.Yes:
            del self.cfg["profiles"][cur]; self.cfg["active_profile"] = next(iter(self.cfg["profiles"])); self.persist(); self.fill_profiles()

    def add_minilab(self):
        n = "MiniLab 3" if "MiniLab 3" not in self.cfg["profiles"] else f"MiniLab 3 ({len(self.cfg['profiles'])})"
        self.cfg["profiles"][n] = minilab3_profile(); self.persist(); self.fill_profiles(); self.prof.setCurrentText(n)

    def do_import(self):
        p, _ = QFileDialog.getOpenFileName(self, "Импорт", "", "JSON (*.json)")
        if not p: return
        try: new = C.import_from(p)
        except Exception as e: return QMessageBox.warning(self, "Импорт", str(e))
        for k, v in new["profiles"].items():
            self.cfg["profiles"][k if k not in self.cfg["profiles"] else k + " (импорт)"] = v
        self.persist(); self.fill_profiles()

    def do_export(self):
        p, _ = QFileDialog.getSaveFileName(self, "Экспорт", "midi-macros.json", "JSON (*.json)")
        if p: C.export_to(self.cfg, p)


def run(argv):
    app = QApplication(argv); app.setQuitOnLastWindowClosed(False); theme.set_theme(C.load().get('theme', 'dark')); app.setStyleSheet(theme.qss(QSS))
    from actions import WinBackend
    cfg = C.load()
    w = Main(cfg, WinBackend())
    if "--tray" not in argv or not cfg.get("start_minimized", True): w.show()
    if cfg.get("autostart") and sys.platform == "win32":
        try: C.set_autostart(True)
        except Exception: pass
    return app.exec()
