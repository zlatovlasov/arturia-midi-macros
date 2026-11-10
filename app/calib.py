"""Калибровка ручек: пользователь по очереди двигает контролы, мы запоминаем реальные CC/канал
и переназначаем схему и пресеты. Чистая логика без Qt — тестируется на любой ОС."""

# порядок мастера: id контрола на схеме, подпись, ожидаемый тип сообщения
ORDER = ([(f"knob{i}", f"Ручка {i}", "cc") for i in range(1, 9)]
         + [(f"fader{i}", f"Фейдер {i}", "cc") for i in range(1, 5)]
         + [("enc", "Главный энкодер (покрутите)", "cc"), ("encclick", "Главный энкодер: нажмите", "cc"),
            ("mod", "Полоса Mod", "cc"), ("pitch", "Полоса Pitch", "pitch")])


class Calibration:
    def __init__(self, order=ORDER):
        self.order = list(order); self.i = 0; self.result = {}

    @property
    def done(self):
        return self.i >= len(self.order)

    def current(self):
        return None if self.done else self.order[self.i]

    def taken(self, ev, except_id=None):
        return any(cid != except_id and r["type"] == ev["type"] and r["number"] == ev["number"] and r["channel"] == ev["channel"]
                   for cid, r in self.result.items())

    def feed(self, ev):
        """ev — нормализованное сообщение (engine.norm_msg). True, если шаг принят и мастер перешёл дальше."""
        cur = self.current()
        if not cur or ev is None or ev["type"] != cur[2]:
            return False
        if self.taken(ev, cur[0]):
            return False   # это контрол из прошлого шага (например, ещё «докатывается») — ждём другой
        self.result[cur[0]] = {"type": ev["type"], "channel": ev["channel"], "number": ev["number"] if ev["type"] != "pitch" else 0}
        self.i += 1
        return True

    def skip(self):
        if not self.done: self.i += 1

    def back(self):
        if self.i > 0:
            self.i -= 1; self.result.pop(self.order[self.i][0], None)


def _same(t, old):
    return t.get("type") == old["type"] and (old["type"] == "pitch" or t.get("number") == old["number"])


def _calib_store(cfg, device):
    if device in (None, "minilab3"):
        return cfg.setdefault("calib", {})   # MiniLab 3 — старое поле, совместимо с прошлыми версиями
    return cfg.setdefault("device_calib", {}).setdefault(device, {})


def apply(cfg, result, defaults, device=None, keep_channel=False):
    """result: id -> новый триггер; defaults: id -> старый триггер (со схемы).
    Сохраняет калибровку устройства (MiniLab 3 — cfg["calib"]) и переносит назначения его профилей со старого CC на новый.
    Канал в назначениях ставится «любой» (None) — так работает при любой программе устройства
    (keep_channel=True — оставить канал как пришёл: для нот/пэдов).
    Возвращает число переназначенных назначений."""
    calib = _calib_store(cfg, device)
    moves = []
    for cid, new in result.items():
        old = calib.get(cid) or defaults.get(cid)
        if old: moves.append((old, new))
        calib[cid] = dict(new)
    n = 0
    dev = device or "minilab3"
    pd = cfg.get("profile_devices", {})
    lists = [lst for name, lst in cfg.get("profiles", {}).items() if pd.get(name, "minilab3") == dev] + [cfg.get("global", [])]
    for lst in lists:
        for m in lst:
            t = m.get("trigger", {})
            for old, new in moves:
                if _same(t, old):
                    m["trigger"] = {"type": new["type"], "channel": new["channel"] if keep_channel else None, "number": new["number"]}
                    n += 1; break   # одно назначение переносим один раз (без «каскада»)
    return n
