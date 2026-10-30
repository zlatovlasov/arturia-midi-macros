"""Движок маппинга: MIDI-сообщение -> действие. Без зависимостей от Windows (тестируется на любой ОС)."""
import time, threading

CC_MODES = ["absolute", "relative_offset64", "relative_twos", "relative_signbit", "abs_to_rel", "button"]
NOTE_MODES = ["press", "release", "tap", "long", "hold"]  # hold: press -> on, release -> off


def norm_msg(msg):
    """Приводит mido.Message (или dict) к dict: type, channel, number, value, raw_max."""
    if not isinstance(msg, dict):
        d = {"type": msg.type, "channel": getattr(msg, "channel", 0)}
        for k in ("note", "velocity", "control", "value", "pitch", "program"):
            if hasattr(msg, k):
                d[k] = getattr(msg, k)
        msg = d
    t = msg["type"]
    if t == "note_on" and msg.get("velocity", 0) == 0:
        t = "note_off"
    if t in ("note_on", "note_off"):
        return {"type": "note", "on": t == "note_on", "channel": msg["channel"], "number": msg["note"], "value": msg.get("velocity", 0)}
    if t == "control_change":
        return {"type": "cc", "channel": msg["channel"], "number": msg["control"], "value": msg["value"]}
    if t == "pitchwheel":
        return {"type": "pitch", "channel": msg["channel"], "number": 0, "value": msg["pitch"] + 8192}
    if t == "program_change":
        return {"type": "program", "channel": msg["channel"], "number": msg["program"], "value": 127}
    return None


def trigger_from(ev):
    return {"type": ev["type"], "channel": ev["channel"], "number": ev["number"]}


def matches(trig, ev):
    if trig.get("type") != ev["type"]:
        return False
    ch = trig.get("channel")
    if ch is not None and ch != ev["channel"]:
        return False
    if ev["type"] == "pitch":
        return True
    return trig.get("number") == ev["number"]


def describe_trigger(t):
    ch = "любой" if t.get("channel") is None else str(t["channel"] + 1)
    names = {"note": "Нота", "cc": "CC", "pitch": "Pitch bend", "program": "Program"}
    s = names.get(t.get("type"), "?")
    if t.get("type") != "pitch":
        s += f" {t.get('number')}"
    return f"{s} · кан. {ch}"


def rel_delta(mode, v):
    if mode == "relative_offset64":
        return v - 64
    if mode == "relative_twos":
        return v if v < 64 else v - 128
    if mode == "relative_signbit":
        return -(v - 64) if v >= 64 else v
    return 0


class Engine:
    """dispatch(action: dict, ctx: dict) вызывается для каждого сработавшего действия.
    ctx: {"kind": "trigger"} | {"kind": "abs", "value": 0..1} | {"kind": "rel", "delta": int} | {"kind": "on"/"off"}"""

    def __init__(self, config, dispatch, clock=time.monotonic):
        self.config = config
        self.dispatch = dispatch
        self.clock = clock
        self.pressed = {}   # key -> (t0, mapping, long_fired)
        self.last_abs = {}  # key -> last value for abs_to_rel
        self.lock = threading.RLock()

    # --- профили
    def active_mappings(self):
        c = self.config
        prof = c["profiles"].get(c.get("active_profile"), [])
        return list(c.get("global", [])) + list(prof)

    def set_profile(self, name=None, step=0):
        names = list(self.config["profiles"].keys())
        if not names:
            return None
        if name in names:
            self.config["active_profile"] = name
        elif step:
            cur = self.config.get("active_profile")
            i = names.index(cur) if cur in names else 0
            self.config["active_profile"] = names[(i + step) % len(names)]
        self.pressed.clear()
        return self.config["active_profile"]

    def _fire(self, m, ctx):
        if m.get("enabled", True) is False:
            return
        self.dispatch(m["action"], ctx)

    # --- обработка
    def process(self, msg):
        ev = msg if (isinstance(msg, dict) and msg.get("type") in ("note", "cc", "pitch", "program")) else norm_msg(msg)
        if ev is None:
            return []
        with self.lock:
            fired = []
            for m in self.active_mappings():
                if not matches(m["trigger"], ev):
                    continue
                r = self._handle(m, ev)
                if r:
                    fired.append(m.get("name", ""))
            return fired

    def _handle(self, m, ev):
        key = (m.get("id"), ev["channel"], ev["number"])
        t = ev["type"]
        mode = m.get("mode") or ("press" if t in ("note", "program") else "absolute")
        if t == "note" or (t == "cc" and mode == "button"):
            on = ev["on"] if t == "note" else ev["value"] >= 64
            if t == "cc":
                mode = m.get("button_mode", "press")
                prev = self.last_abs.get(key, 0) >= 64
                self.last_abs[key] = ev["value"]
                if on == prev:
                    return False
            if on:
                vmin, vmax = m.get("velocity_min", 1), m.get("velocity_max", 127)
                if t == "note" and not (vmin <= ev["value"] <= vmax):
                    return False
                if mode == "press":
                    self._fire(m, {"kind": "trigger", "velocity": ev["value"]}); return True
                if mode == "hold":
                    self._fire(m, {"kind": "on"}); return True
                if mode in ("tap", "long"):
                    self.pressed[key] = [self.clock(), m, False]
                return False
            else:
                if mode == "release":
                    self._fire(m, {"kind": "trigger"}); return True
                if mode == "hold":
                    self._fire(m, {"kind": "off"}); return True
                st = self.pressed.pop(key, None)
                if not st:
                    return False
                held = (self.clock() - st[0]) * 1000
                long_ms = m.get("long_ms", 500)
                if mode == "tap" and held < long_ms:
                    self._fire(m, {"kind": "trigger"}); return True
                if mode == "long" and not st[2] and held >= long_ms:
                    self._fire(m, {"kind": "trigger"}); st[2] = True; return True
                return False
        if t == "program":
            self._fire(m, {"kind": "trigger"}); return True
        if t == "pitch":
            self._fire(m, {"kind": "abs", "value": ev["value"] / 16383.0}); return True
        # CC
        v = ev["value"]
        if mode == "absolute":
            self._fire(m, {"kind": "abs", "value": v / 127.0}); return True
        if mode == "abs_to_rel":
            prev = self.last_abs.get(key)
            self.last_abs[key] = v
            if prev is None or prev == v:
                return False
            d = v - prev
            if v in (0, 127) and prev in (0, 127):
                d = 1 if v == 127 else -1
            self._fire(m, {"kind": "rel", "delta": d}); return True
        d = rel_delta(mode, v)
        if d:
            self._fire(m, {"kind": "rel", "delta": d}); return True
        return False

    def tick(self):
        """Вызывать периодически (~20 мс): срабатывание долгого нажатия без отпускания."""
        now = self.clock()
        with self.lock:
            for key, st in list(self.pressed.items()):
                t0, m, done = st
                if not done and m.get("mode") == "long" and (now - t0) * 1000 >= m.get("long_ms", 500):
                    st[2] = True
                    self._fire(m, {"kind": "trigger"})
