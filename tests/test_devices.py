"""Профили устройств: MiniLab 3 без регрессий, корректность всех профилей, миграция конфигов, калибровка по моделям."""
import sys, os, json, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import mido
import pytest
import devices as D
import config as C
import calib as CAL
from engine import Engine, norm_msg
from presets import maybe_minilab_port, is_minilab3
from controller import MacroController
from leds import compute_pad_colors
from test_engine import FakeBackend, FakeHub
from actions import Runner

KINDS = {"knob", "fader", "pad", "white", "black", "button", "encoder", "strip"}
HERE = os.path.dirname(__file__)


def eff_trigs(c):
    """Все триггеры контрола (по банкам), как их увидит программа."""
    if "bank_trigs" in c:
        return [D.default_trig(c, b) for b in range(len(c["bank_trigs"]))]
    return [D.default_trig(c)]


# ---------- MiniLab 3: ровно та же схема, что до профилей

def test_minilab3_matches_legacy_schema():
    legacy = json.load(open(os.path.join(HERE, "data", "minilab3_legacy_controls.json"), encoding="utf-8"))
    new = D.get("minilab3")["controls"]
    assert [c["id"] for c in new] == [c["id"] for c in legacy]
    for n, o in zip(new, legacy):
        assert n["kind"] == o["kind"] and list(n["rect"]) == o["rect"], n["id"]
        if o["kind"] == "pad":   # раньше: нота 36 + 8*банк + i, канал 10; подпись «Пэд A1»
            i = o["pad"]
            assert eff_trigs(n) == [{"type": "note", "channel": 9, "number": 36 + i}, {"type": "note", "channel": 9, "number": 44 + i}]
            assert n["label"].format(bank="A") == f"Пэд A{i + 1}" and n["pad"] == i
        else:
            assert n["label"] == o["label"]
            assert D.default_trig(n) == o["trig"], n["id"]


def test_minilab3_ports_and_calib_order_unchanged():
    from calib import ORDER
    assert D.get("minilab3")["calib"] == ORDER
    for name in ("Minilab3 MIDI", "MIDIIN2 (Minilab3 MIDI)", "MiniFuse 2 MIDI", "Arturia DAW", "Other"):
        assert D.match_port("minilab3", name) == is_minilab3(name)
        assert D.listen_port("minilab3", name) == maybe_minilab_port(name)
    assert D.detect(["Other", "MIDIIN2 (Minilab3 MIDI)"]) == "minilab3"
    assert D.starter("minilab3")[0]["name"] == "Фейдер 1"


# ---------- все профили

@pytest.mark.parametrize("dev", [d["id"] for d in D.all_devices()])
def test_profile_is_consistent(dev):
    d = D.get(dev)
    for k in ("id", "name", "vendor", "title", "size", "ports", "controls", "calib", "pads"):
        assert k in d, k
    ids = [c["id"] for c in d["controls"]]
    assert len(ids) == len(set(ids)), "повтор id"
    W, H = d["size"]
    nb = len(d["banks"]["names"]) if d.get("banks") else 1
    seen = {}
    for c in d["controls"]:
        assert c["kind"] in KINDS and c["label"]
        x, y, w, h = c["rect"]; assert 0 <= x and 0 <= y and x + w <= W and y + h <= H, c["id"]
        assert c.get("verify") in ("official", "family", "community", "unknown"), c["id"]
        if "bank_trigs" in c: assert len(c["bank_trigs"]) == nb and "{bank}" in c["label"]
        if c.get("verify") == "unknown": assert all(t is None for t in eff_trigs(c)) or c["id"] in ("encclick",)
        for b, t in enumerate(eff_trigs(c)):
            if t is None: continue
            assert t["type"] in ("cc", "note", "pitch") and 0 <= t["number"] <= 127
            key = (b if "bank_trigs" in c else None, t["type"], t["number"] if t["type"] != "pitch" else 0, t["channel"])
            assert key not in seen, f"{c['id']} и {seen.get(key)}: одинаковый триггер"
            seen[key] = c["id"]
    for cid, _, typ in d["calib"]:
        assert cid in ids and typ in ("cc", "pitch")
    assert all(p in ids for p in d["pads"])
    for cid, *_ in d.get("starter", []):
        assert cid in ids, cid
    if not d.get("dynamic") and dev != "minilab3":
        assert len(D.starter(dev)) >= 4
        for m in D.starter(dev):
            assert m["trigger"] is not None and m["action"]["type"]


def test_detect_by_port_name():
    cases = {"nanoKONTROL2 1 SLIDER/KNOB": "nanokontrol2", "nanoKONTROL2": "nanokontrol2", "X-TOUCH MINI": "xtouch_mini",
             "MPK mini 3": "mpk_mini3", "Launchkey Mini MK3 MIDI 1": "launchkey_mini3", "MIDIIN2 (Launchkey Mini MK3 MIDI)": "launchkey_mini3",
             "KeyLab Essential 49 mk3 MIDI": "keylab_essential3", "Minilab3 MIDI": "minilab3"}
    for port, dev in cases.items():
        assert D.detect([port]) == dev, port
    assert D.detect(["Microsoft GS Wavetable Synth", "loopMIDI Port"]) is None


def test_xtouch_layers_per_official_map():
    enc = D.control("xtouch_mini", "enc1"); btn9 = D.control("xtouch_mini", "btn9"); fader = D.control("xtouch_mini", "fader")
    assert [t["number"] for t in eff_trigs(enc)] == [1, 11]
    assert [t["number"] for t in eff_trigs(btn9)] == [16, 40]
    assert [t["number"] for t in eff_trigs(fader)] == [9, 10]
    push8 = D.control("xtouch_mini", "push8")
    assert [t["number"] for t in eff_trigs(push8)] == [7, 31]


def test_keylab_pads_follow_manual_table():
    a = [D.control("keylab_essential3", f"pad{i}")["bank_trigs"][0]["number"] for i in range(1, 9)]
    b = [D.control("keylab_essential3", f"pad{i}")["bank_trigs"][1]["number"] for i in range(1, 9)]
    assert a == [40, 41, 42, 43, 36, 37, 38, 39] and b == [48, 49, 50, 51, 44, 45, 46, 47]
    assert D.control("keylab_essential3", "knob1")["trig"] is None   # не опубликовано — только калибровка


def test_nanokontrol2_numbers():
    get = lambda cid: D.default_trig(D.control("nanokontrol2", cid))["number"]
    assert [get(f"fader{i}") for i in range(1, 9)] == list(range(0, 8))
    assert [get(f"knob{i}") for i in range(1, 9)] == list(range(16, 24))
    assert (get("s1"), get("m1"), get("r8")) == (32, 48, 71)
    assert (get("play"), get("stop"), get("rew"), get("ff"), get("rec"), get("cycle")) == (41, 42, 43, 44, 45, 46)


# ---------- конфиг

def old_v2_config():
    """Конфиг v2, как его сохраняла прошлая версия (без полей устройств)."""
    cfg = C.default_config()
    for k in ("device", "profile_devices", "device_calib", "generic_controls", "asked_devices"): cfg.pop(k)
    cfg["version"] = 2; cfg["calib"] = {"knob1": {"type": "cc", "channel": 3, "number": 102}}
    cfg["profiles"]["Мой"] = [{"id": "x1", "name": "a", "trigger": {"type": "cc", "channel": None, "number": 102}, "mode": "absolute",
                               "action": {"type": "master_volume", "params": {}}}]
    return json.loads(json.dumps(cfg))


def test_old_config_migrates_to_minilab3():
    cfg = old_v2_config(); before = copy.deepcopy(cfg["profiles"])
    cfg = C.fix(cfg)
    assert cfg["version"] == 3 and cfg["device"] == "minilab3"
    assert cfg["profiles"] == before                                   # назначения не тронуты
    assert C.device_profiles(cfg) == list(before)                      # все старые профили — MiniLab 3
    assert C.calib_for(cfg) == {"knob1": {"type": "cc", "channel": 3, "number": 102}}
    b = FakeBackend(); e = Engine(cfg, Runner(b)); cfg["active_profile"] = "Мой"
    e.process(mido.Message("control_change", channel=3, control=102, value=127)); assert b.vol == 1


def test_config_roundtrip(tmp_path):
    p = str(tmp_path / "c.json"); cfg = C.fix(old_v2_config()); cfg["device"] = "nanokontrol2"
    C.save(cfg, p); again = C.load(p)
    assert again["device"] == "nanokontrol2" and again["version"] == 3


def test_calibration_is_per_device():
    cfg = C.fix(old_v2_config())
    cfg["profiles"]["KL"] = [{"id": "k", "trigger": {"type": "cc", "channel": None, "number": 102}, "action": {"type": "none", "params": {}}}]
    cfg["profile_devices"]["KL"] = "keylab_essential3"
    n = CAL.apply(cfg, {"knob1": {"type": "cc", "channel": 0, "number": 96}}, {"knob1": {"type": "cc", "channel": None, "number": 102}}, device="keylab_essential3")
    assert n == 1 and cfg["profiles"]["KL"][0]["trigger"]["number"] == 96
    assert cfg["profiles"]["Мой"][0]["trigger"]["number"] == 102      # профиль MiniLab не тронут
    assert C.calib_for(cfg, "keylab_essential3")["knob1"]["number"] == 96
    assert cfg["calib"]["knob1"]["number"] == 102                       # калибровка MiniLab отдельно


def test_profile_cycling_stays_on_device():
    cfg = C.fix(old_v2_config())
    cfg["profiles"]["nano A"] = []; cfg["profiles"]["nano B"] = []
    cfg["profile_devices"].update({"nano A": "nanokontrol2", "nano B": "nanokontrol2"})
    cfg["device"] = "nanokontrol2"; cfg["active_profile"] = "nano A"
    e = Engine(cfg, lambda a, c: None)
    assert e.set_profile(step=1) == "nano B" and e.set_profile(step=1) == "nano A"


def test_controller_listens_all_ports_of_active_device():
    h = FakeHub(); c = {"inputs": ["nanoKONTROL2 1 SLIDER/KNOB"], "device": "nanokontrol2"}
    st = MacroController(h, c, lambda: ["nanoKONTROL2 1 SLIDER/KNOB", "nanoKONTROL2 2", "Minilab3 MIDI"]).apply()
    assert h.opened == {"nanoKONTROL2 1 SLIDER/KNOB", "nanoKONTROL2 2"} and st["mode"] == "on"


def test_pad_colors_for_other_device():
    cfg = C.fix(old_v2_config()); n = "LK"
    cfg["profiles"][n] = D.starter("launchkey_mini3"); cfg["profile_devices"][n] = "launchkey_mini3"; cfg["active_profile"] = n
    trigs = [D.default_trig(D.control("launchkey_mini3", f"pad{i}")) for i in range(1, 17)]
    cols = compute_pad_colors(cfg, 0, {"mic_muted": True}, trigs=trigs)
    assert len(cols) == 16 and cols[8] == "#ff2020"                    # пэд 9 = микрофон (выключен) -> красный
    assert compute_pad_colors(C.default_config(), 0, {"mic_muted": False})[0] == "#2ee66b"   # MiniLab как раньше


# ---------- схема (Qt offscreen)

@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def ev(msg): return norm_msg(msg)


def test_view_minilab_bank_switch_like_before(qapp):
    from device import DeviceView
    v = DeviceView()
    c = v.on_event(ev(mido.Message("note_on", channel=9, note=45, velocity=90)))
    assert c["id"] == "pad2" and v.bank == 1 and v.label(c) == "Пэд B2"
    c = v.on_event(ev(mido.Message("control_change", channel=7, control=74, value=10)))
    assert c["id"] == "knob1"                                          # ручки — на любом канале
    assert v.on_event(ev(mido.Message("note_on", channel=9, note=60, velocity=9))) is None


def test_view_xtouch_layer_b(qapp):
    from device import DeviceView
    v = DeviceView("xtouch_mini")
    c = v.on_event(ev(mido.Message("control_change", channel=10, control=12, value=64)))
    assert c["id"] == "enc2" and v.bank == 1 and v.label(c) == "Энкодер 2 · слой B"


def test_view_unknown_control_then_calibrated(qapp):
    from device import DeviceView
    v = DeviceView("keylab_essential3")
    k = next(c for c in v.controls if c["id"] == "knob1")
    assert v.trig(k) is None and v.on_event(ev(mido.Message("control_change", channel=0, control=96, value=1))) is None
    v.set_calib({"knob1": {"type": "cc", "channel": 0, "number": 96}})
    assert v.on_event(ev(mido.Message("control_change", channel=5, control=96, value=1)))["id"] == "knob1"


def test_view_generic_learns(qapp):
    from device import DeviceView
    v = DeviceView("generic"); added = []; v.on_new_control = added.append
    c = v.on_event(ev(mido.Message("control_change", channel=2, control=21, value=5)))
    assert c and c["label"] == "CC 21 · кан. 3" and len(added) == 1
    assert v.on_event(ev(mido.Message("control_change", channel=2, control=21, value=9)))["id"] == c["id"] and len(added) == 1
    v.on_event(ev(mido.Message("note_off", channel=0, note=60))); assert len(v.controls) == 1   # отпускание не создаёт контрол
    v2 = DeviceView("generic"); v2.set_device("generic", {}, added)
    assert [x["id"] for x in v2.controls] == [c["id"]]                 # восстанавливается из конфига


def test_main_window_switches_device(qapp, tmp_path):
    import queue, gui
    os.environ["APPDATA"] = str(tmp_path)
    cfg = C.fix(old_v2_config()); hub = FakeHub(); hub.listeners = []; hub.q = queue.Queue()
    w = gui.Main(cfg, FakeBackend(), hub=hub, save=False, inputs_fn=lambda: ["nanoKONTROL2"])
    try:
        assert w.dev.device == "minilab3"
        w.set_device("nanokontrol2")
        assert cfg["device"] == "nanokontrol2" and C.profile_device(cfg, cfg["active_profile"]) == "nanokontrol2"
        assert cfg["profiles"][cfg["active_profile"]]                     # стартовый набор создан
        w.on_midi_ui("nanoKONTROL2", mido.Message("control_change", channel=0, control=0, value=127))
        assert w.dev.sel["id"] == "fader1"
        w.set_device("minilab3")
        assert cfg["active_profile"] in C.device_profiles(cfg, "minilab3") and w.dev.device == "minilab3"
    finally:
        w.worker.running = False; w.tray.hide()


def test_fix_keeps_active_profile_on_device():
    cfg = C.fix(old_v2_config())
    cfg["profiles"]["nano"] = []; cfg["profile_devices"]["nano"] = "nanokontrol2"; cfg["device"] = "nanokontrol2"
    assert C.fix(cfg)["active_profile"] == "nano"


def test_main_creates_starter_for_device_without_profile(qapp, tmp_path):
    import queue, gui
    cfg = C.fix(old_v2_config()); cfg["device"] = "xtouch_mini"; hub = FakeHub(); hub.listeners = []; hub.q = queue.Queue()
    w = gui.Main(cfg, FakeBackend(), hub=hub, save=False, inputs_fn=lambda: ["X-TOUCH MINI"])
    try:
        assert w.dev.device == "xtouch_mini" and C.profile_device(cfg, cfg["active_profile"]) == "xtouch_mini"
        assert cfg["inputs"] == ["X-TOUCH MINI"]
        w.on_midi_ui("X-TOUCH MINI", mido.Message("note_on", channel=10, note=33, velocity=127))   # кнопка 2, слой B
        assert w.dev.bank == 1 and w.dev.sel["id"] == "btn2"
    finally:
        w.worker.running = False; w.tray.hide()
