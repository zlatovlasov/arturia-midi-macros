"""Любое MIDI-устройство (Generic MIDI, режим «пошевели — и появится»).
Контролов заранее нет: каждый новый CC / нота / pitch bend добавляется на схему, когда его шевелят."""

COLS, CELL_W, CELL_H, X0, Y0 = 8, 108, 92, 34, 62
MAX = 32


def rect(i, kind):
    """Место i-го контрола в сетке 8×4."""
    col, row = i % COLS, i // COLS
    x, y = X0 + col * CELL_W, Y0 + row * CELL_H
    if kind == "knob": return (x + 26, y + 6, 52, 52)
    if kind == "strip": return (x + 40, y + 2, 26, 70)
    return (x + 10, y + 6, 84, 60)


def make(ev, i):
    """Новый контрол по нормализованному сообщению (engine.norm_msg)."""
    t, ch, n = ev["type"], ev["channel"], ev["number"]
    if t == "cc": kind, label = "knob", f"CC {n} · кан. {ch + 1}"
    elif t == "note": kind, label = "pad", f"Нота {n} · кан. {ch + 1}"
    elif t == "pitch": kind, label = "strip", f"Pitch · кан. {ch + 1}"
    else: kind, label = "button", f"Program {n} · кан. {ch + 1}"
    return {"id": f"g_{t}_{ch}_{n}", "label": label, "short": label.split(" · ")[0], "kind": kind,
            "trig": {"type": t, "channel": ch, "number": 0 if t == "pitch" else n}, "rect": rect(i, kind), "verify": "official"}


DEVICE = {
    "id": "generic", "name": "Любое MIDI-устройство", "vendor": "", "title": "GENERIC  MIDI · пошевелите контрол — он появится",
    "size": (940, 440), "ports": [], "listen": [], "banks": None, "screen": None,
    "controls": [], "pads": [], "calib": [], "led": None, "dynamic": True, "starter": [],
}
