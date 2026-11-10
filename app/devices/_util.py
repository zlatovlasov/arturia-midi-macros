"""Помощники для модулей-профилей устройств (без Qt)."""

def keyboard(first_note, count, x0, y, step, ww, wh, bw, bh, channel=0, verify="official"):
    """Клавиши: сначала белые, потом чёрные (чёрные рисуются поверх). Как в исходной схеме MiniLab 3."""
    whites = [0, 2, 4, 5, 7, 9, 11]
    out = []; n = 0
    for k in range(count):
        note = first_note + k
        if (note % 12) in whites:
            out.append({"id": f"key{note}", "label": f"Клавиша {note}", "kind": "white", "trig": {"type": "note", "channel": channel, "number": note},
                        "rect": (x0 + n * step, y, ww, wh), "verify": verify}); n += 1
    n = 0
    for k in range(count):
        note = first_note + k
        if (note % 12) in whites:
            n += 1; continue
        out.append({"id": f"key{note}", "label": f"Клавиша {note}", "kind": "black", "trig": {"type": "note", "channel": channel, "number": note},
                    "rect": (x0 + n * step - bw / 2, y, bw, bh), "verify": verify})
    return out


def cc(n, ch=0):
    return {"type": "cc", "channel": ch, "number": n}


def note(n, ch=0):
    return {"type": "note", "channel": ch, "number": n}


PITCH = {"type": "pitch", "channel": 0, "number": 0}
