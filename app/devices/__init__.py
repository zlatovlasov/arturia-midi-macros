"""Профили устройств: у каждой модели свой модуль-словарь (схема, номера CC/нот, калибровка, автоопределение).
Чистая логика без Qt — тестируется на любой ОС. Источники номеров — docs/DEVICES.md.

Поля профиля:
  id, name, vendor, title (надпись на схеме), size (W, H) — холст схемы
  ports      — регулярки по имени MIDI-порта (автоопределение, без учёта регистра)
  listen     — регулярки «доп. портов» того же устройства (слушаем все, если включено в настройках)
  banks      — {"names": ["A", "B"], "label": "Пэды", "rect": (x, y, w, h)} или None
  screen     — (x, y, w, h) экранчика на схеме или None
  controls   — список контролов: id, label (по-русски), kind (knob/fader/pad/white/black/button/encoder/strip),
               trig {type, channel, number} или None (номер не подтверждён — нужна калибровка/«пошевелите»),
               bank_trigs [trig банка A, trig банка B…] — вместо trig, если контрол зависит от банка/слоя,
               rect (x, y, w, h), short — короткая подпись на схеме, verify — official/family/community/unknown
  pads       — id пэдов по порядку (для цветов/подсветки)
  calib      — порядок мастера калибровки: [(id, подпись, тип сообщения)]
  led        — id драйвера подсветки ("minilab3") или None
  dynamic    — True: контролы появляются, когда их шевелят (Generic MIDI)
  starter    — готовый набор назначений: [(id контрола, имя, действие, параметры, доп. поля)]
"""
import re, uuid

from devices import minilab3, keylab_essential3, mpk_mini3, launchkey_mini3, nanokontrol2, xtouch_mini, generic

DEFAULT = "minilab3"
_ALL = [minilab3.DEVICE, keylab_essential3.DEVICE, mpk_mini3.DEVICE, launchkey_mini3.DEVICE,
        nanokontrol2.DEVICE, xtouch_mini.DEVICE, generic.DEVICE]
REGISTRY = {d["id"]: d for d in _ALL}
VERIFIED = ("official", "family")   # остальное (community/unknown) помечаем на схеме «?»


def all_devices():
    return list(_ALL)


def get(dev_id):
    if isinstance(dev_id, dict): return dev_id
    return REGISTRY.get(dev_id) or REGISTRY[DEFAULT]


def _norm(name):
    return (name or "").lower()


def match_port(dev, port_name):
    """Порт принадлежит устройству? (по регуляркам ports)"""
    d = get(dev)
    if d.get("port_match"): return bool(d["port_match"](port_name or ""))
    n = _norm(port_name)
    return any(re.search(p, n) for p in d.get("ports", []))


def listen_port(dev, port_name):
    """Порт, который стоит слушать вместе с выбранным (все входы устройства + его хабы)."""
    d = get(dev)
    if d.get("listen_match"): return bool(d["listen_match"](port_name or ""))
    n = _norm(port_name)
    return match_port(d, port_name) or any(re.search(p, n) for p in d.get("listen", []))


def detect(port_names):
    """-> id первого распознанного устройства среди имён портов или None (Generic не угадывается)."""
    for d in _ALL:
        if d.get("dynamic"): continue
        if any(match_port(d, n) for n in port_names):
            return d["id"]
    return None


def pad_ids(dev):
    return list(get(dev).get("pads", []))


def control(dev, cid):
    return next((c for c in get(dev)["controls"] if c["id"] == cid), None)


def default_trig(c, bank=0):
    """Триггер контрола по умолчанию (для банковых — банк bank). Ручки/фейдеры/энкодеры/кнопки/полосы — канал любой."""
    t = c["bank_trigs"][bank] if "bank_trigs" in c else c.get("trig")
    if t is None: return None
    t = dict(t)
    if c["kind"] in ANY_CHANNEL_KINDS: t["channel"] = None
    return t


ANY_CHANNEL_KINDS = ("strip", "encoder", "button", "knob", "fader")


def starter(dev):
    """Готовый набор назначений для устройства (только для контролов с известным номером)."""
    d = get(dev)
    if d["id"] == "minilab3":
        from presets import minilab3_profile
        return minilab3_profile()
    out = []
    for cid, name, action, params, extra in d.get("starter", []):
        c = control(d, cid)
        t = default_trig(c) if c else None
        if t is None: continue
        m = {"id": uuid.uuid4().hex[:8], "name": name, "trigger": t, "action": {"type": action, "params": dict(params)}}
        m.update(extra)
        out.append(m)
    return out
