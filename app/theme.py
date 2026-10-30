"""Темы. Палитра задаётся в «тёмных» hex-кодах; светлая тема — карта замен.
Акцент: тёмная тема — оранжевый, светлая — фиолетовый."""
import re
from PySide6.QtGui import QColor

current = "dark"

LIGHT = {
    "#ff8a2a": "#8b5cf6", "#ff9c48": "#7c4ddb", "#ffb070": "#6d3fd6", "#ffd2aa": "#5b2fc4", "#ffb36b": "#c4b5fd",
    "#ffb071": "#c4b5fd", "#2a1d12": "#ede7fe", "#3a332b": "#ebe5fb", "#3a352f": "#e6e0f5",
    "#141312": "#f4f3f1", "#1b1a18": "#ffffff", "#1c1b19": "#ffffff", "#111110": "#faf9f7", "#2a2825": "#f1efec",
    "#34312d": "#e4e1dc", "#3a3733": "#d9d5cf", "#2c2a27": "#e4e1dc", "#2b2926": "#dcd8d2", "#24221f": "#eeece8",
    "#1f1e1c": "#e3e0da", "#2a2826": "#f7f6f4", "#ece9e4": "#1f1d24", "#ece8e1": "#ffffff", "#d8d3cc": "#2b2930",
    "#d8d2c8": "#4a4652", "#cfc8be": "#3a3740", "#bdb6ad": "#5a5660", "#9a938a": "#77737c", "#a39b90": "#77737c",
    "#8d867c": "#8a8690", "#8a837a": "#a8a3ad", "#7a746c": "#a8a3ad", "#77716a": "#b8b3bd", "#6b6660": "#b8b3bd",
    "#4a4640": "#cfcac4", "#45413b": "#c9c4be", "#3e3a35": "#d3cec8", "#3c3934": "#3a3644", "#2f2c29": "#d6d2cc",
    "#1a1918": "#fbfaf8", "#171615": "#efede9", "#151413": "#cfcbc5", "#0e0e0d": "#1e1b26", "#111": "#fff",
    "#3a1a16": "#fde8e6", "#ff9a8a": "#c0392b", "#f2b84b": "#a78bfa", "#e8d6b0": "#c4b5fd", "#d77a5a": "#7c3aed",
    "#c98d6e": "#9f7aea", "#b9a58c": "#b9a8d9", "#e0e0d8": "#6b6375", "#d8d2c9": "#f4f3f1", "#e8a25a": "#7c3aed", "#d9c27a": "#a78bfa",
}

ACCENT = "#ff8a2a"

def set_theme(name):
    global current
    current = "light" if name == "light" else "dark"

def hx(h):
    return LIGHT.get(h.lower(), h) if current == "light" else h

def col(h):
    return QColor(hx(h))

def qss(s):
    if current != "light":
        return s
    return re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", lambda m: hx(m.group(0)), s)

def overlay():
    return QColor(244, 243, 241, 200) if current == "light" else QColor(20, 19, 18, 170)
