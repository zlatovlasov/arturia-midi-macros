"""Выбор действия в два шага: крупные плитки категорий -> короткий список с описаниями. Поиск сверху."""
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon, QPen
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QLabel, QToolButton,
                               QListWidget, QListWidgetItem, QStackedWidget, QWidget, QPushButton)
from actions import ACTIONS
from theme import col

# плитка: (название, значок, цвет, подсказка)
TILES = [("Запуск", "▶", "#ff8a2a", "программы, сайты"),
         ("Клавиатура", "⌨", "#e8d6b0", "клавиши, текст"),
         ("Медиа", "♫", "#d77a5a", "музыка, видео"),
         ("Звук", "◖", "#f2b84b", "громкость, микро"),
         ("Окна", "▣", "#b9a58c", "окна, столы"),
         ("Сцены", "✦", "#e8a25a", "много шагов"),
         ("Голос", "◉", "#d9c27a", "диктовка, питч"),
         ("Прочее", "⋯", "#c98d6e", "система, профили")]
OTHER = {"Система", "Профили", "Общее"}

DESC = {
    "none": "Ничего не делать — освободить контрол",
    "open": "Запустить программу, открыть файл, папку или сайт",
    "open_links": "Одно нажатие — до 10 вкладок в выбранном браузере",
    "hotkey": "Нажать сочетание клавиш, например ctrl+shift+s",
    "rel_hotkeys": "Крутите вправо/влево — жмутся две разные клавиши",
    "type_text": "Напечатать готовую фразу, реквизиты, ответ клиенту",
    "macro": "Цепочка: клавиши, текст, паузы, команды",
    "media": "Плей/пауза, следующий и предыдущий трек, стоп",
    "master_volume": "Общая громкость Windows: фейдер, ручка или шаг",
    "master_mute": "Выключить и включить весь звук",
    "app_volume": "Громкость одной программы: Chrome, Spotify, Discord…",
    "app_mute": "Заглушить одну программу",
    "mic_volume": "Чувствительность микрофона",
    "mic_mute": "Мьют микрофона: переключить или «держи и говори»",
    "mute_all": "Тишина: звук и микрофон разом",
    "audio_output": "Переключить колонки ↔ наушники",
    "window": "Свернуть, развернуть, закрыть, прилепить окно",
    "desktop": "Следующий/предыдущий виртуальный рабочий стол",
    "scene": "Открыть программы и сайты, выставить звук — всё сразу",
    "voice": "Держите пэд, говорите — текст вставится сам",
    "voice_pitch": "Полоса Pitch двигает высоту вашего голоса в реальном времени",
    "lock": "Заблокировать компьютер",
    "sleep": "Отправить ПК в сон",
    "screenshot": "Скрин области или всего экрана",
    "run": "Выполнить команду cmd или PowerShell",
    "brightness": "Яркость монитора",
    "scroll": "Крутилка как колесо мыши",
    "profile": "Переключить профиль назначений",
    "macros_off": "Отдать клавиатуру FL Studio (выключить макросы)",
}


def tile_of(key):
    cat = ACTIONS[key][2]
    return "Прочее" if cat in OTHER else cat


def by_tile():
    out = {t[0]: [] for t in TILES}
    for k in ACTIONS:
        out[tile_of(k)].append(k)
    return out


def search(q):
    q = q.strip().lower()
    if not q: return []
    return [k for k, v in ACTIONS.items() if q in v[0].lower() or q in DESC.get(k, "").lower() or q in tile_of(k).lower()]


def glyph_icon(sym, color, size=44):
    pm = QPixmap(size, size); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen); p.setBrush(col(color)); p.drawRoundedRect(QRectF(0, 0, size, size), size * .28, size * .28)
    p.setPen(col("#141312")); p.setFont(QFont("Segoe UI Symbol", int(size * .42), QFont.Bold))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, sym); p.end(); return QIcon(pm)


def tile_icon(name, size=22):
    t = next((t for t in TILES if t[0] == name), TILES[-1]); return glyph_icon(t[1], t[2], size)


class ActionPicker(QDialog):
    def __init__(self, parent=None, current="none"):
        super().__init__(parent); self.setWindowTitle("Выберите действие"); self.setMinimumSize(720, 560)
        self.choice = None; self.groups = by_tile()
        L = QVBoxLayout(self); L.setContentsMargins(22, 20, 22, 20); L.setSpacing(14)
        h = QLabel("Что сделать?"); h.setObjectName("h1"); L.addWidget(h)
        self.q = QLineEdit(); self.q.setPlaceholderText("🔍  Поиск: громкость, ссылки, микрофон…"); self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self.on_search); L.addWidget(self.q)
        self.stack = QStackedWidget(); L.addWidget(self.stack, 1)
        # шаг 1: плитки
        grid_w = QWidget(); g = QGridLayout(grid_w); g.setSpacing(12); g.setContentsMargins(0, 0, 0, 0)
        for i, (name, sym, c, sub) in enumerate(TILES):
            b = QToolButton(); b.setObjectName("tile"); b.setIcon(glyph_icon(sym, c)); b.setIconSize(QSize(44, 44))
            b.setText(f"{name}\n{sub}"); b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setMinimumSize(140, 120); b.setCursor(Qt.PointingHandCursor)
            if any(k == current for k in self.groups[name]): b.setProperty("current", True)
            b.clicked.connect(lambda _=False, n=name: self.open_tile(n)); g.addWidget(b, i // 4, i % 4)
        self.stack.addWidget(grid_w)
        # шаг 2: список
        lw = QWidget(); LL = QVBoxLayout(lw); LL.setContentsMargins(0, 0, 0, 0); LL.setSpacing(8)
        top = QHBoxLayout(); self.backb = QPushButton("←  Все категории"); self.backb.clicked.connect(self.go_back); top.addWidget(self.backb)
        self.cat_lbl = QLabel(""); self.cat_lbl.setObjectName("h2"); top.addWidget(self.cat_lbl); top.addStretch(1); LL.addLayout(top)
        self.list = QListWidget(); self.list.setObjectName("actions"); self.list.setIconSize(QSize(22, 22))
        self.list.itemActivated.connect(self.pick); self.list.itemClicked.connect(self.pick); LL.addWidget(self.list, 1)
        self.stack.addWidget(lw)
        self.current = current
        cancel = QPushButton("Отмена"); cancel.clicked.connect(self.reject); r = QHBoxLayout(); r.addStretch(1); r.addWidget(cancel); L.addLayout(r)

    def fill(self, keys, title):
        self.list.clear(); self.cat_lbl.setText(title)
        for k in keys:
            it = QListWidgetItem(tile_icon(tile_of(k)), f"{ACTIONS[k][0]}\n{DESC.get(k, '')}")
            it.setData(Qt.UserRole, k); it.setSizeHint(QSize(0, 58)); self.list.addItem(it)
            if k == self.current: self.list.setCurrentItem(it)
        if not keys: self.list.addItem("Ничего не нашлось — попробуйте другое слово")
        self.stack.setCurrentIndex(1)

    def open_tile(self, name):
        self.fill(self.groups[name], name)

    def on_search(self, text):
        if text.strip(): self.fill(search(text), f"Поиск: «{text.strip()}»")
        else: self.go_back()

    def go_back(self):
        self.stack.setCurrentIndex(0)
        if self.q.text(): self.q.blockSignals(True); self.q.clear(); self.q.blockSignals(False)

    def pick(self, it):
        k = it.data(Qt.UserRole)
        if k: self.choice = k; self.accept()


class ActionButton(QPushButton):
    """Кнопка-поле «Действие»: показывает выбранное, по клику открывает ActionPicker."""
    changed = Signal(str)

    def __init__(self):
        super().__init__(); self.key = "none"; self.setObjectName("actbtn"); self.setIconSize(QSize(22, 22))
        self.setCursor(Qt.PointingHandCursor); self.clicked.connect(self.open); self.set("none")

    def currentData(self): return self.key

    def set(self, k):
        self.key = k if k in ACTIONS else "none"
        self.setIcon(tile_icon(tile_of(self.key))); self.setText(f"  {ACTIONS[self.key][0]}   ▾")

    def open(self):
        d = ActionPicker(self.window(), self.key)
        if d.exec() and d.choice:
            self.set(d.choice); self.changed.emit(d.choice)
