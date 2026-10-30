import sys, os, mido
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import numpy as np
from engine import Engine, norm_msg, matches
from calib import Calibration, apply, ORDER
from presets import minilab3_profile
import config as C
from controller import MacroController
from test_engine import FakeBackend, FakeHub
from actions import Runner

def cc(ch, n, v=64): return norm_msg(mido.Message("control_change", channel=ch, control=n, value=v))

def test_any_channel_trigger():
    t = {"type": "cc", "channel": None, "number": 74}
    assert matches(t, cc(0, 74)) and matches(t, cc(15, 74)) and not matches(t, cc(0, 75))

def test_calibration_records_and_skips_repeats():
    c = Calibration([("knob1", "Р1", "cc"), ("knob2", "Р2", "cc"), ("pitch", "P", "pitch")])
    assert c.feed(cc(3, 102))
    assert not c.feed(cc(3, 102))          # та же ручка ещё крутится — не засчитываем второй
    assert not c.feed(norm_msg(mido.Message("note_on", note=60, velocity=10)))
    assert c.feed(cc(3, 103))
    assert c.feed(norm_msg(mido.Message("pitchwheel", channel=3, pitch=100)))
    assert c.done and c.result["knob2"] == {"type": "cc", "channel": 3, "number": 103}

def test_calibration_back_and_skip():
    c = Calibration(ORDER); c.skip(); assert c.current()[0] == "knob2"
    c.feed(cc(0, 20)); c.back(); assert c.current()[0] == "knob2" and "knob2" not in c.result

def test_apply_remaps_presets_and_engine():
    cfg = C.default_config(); b = FakeBackend()
    defaults = {"fader1": {"type": "cc", "channel": None, "number": 82}, "knob1": {"type": "cc", "channel": None, "number": 74}}
    n = apply(cfg, {"fader1": {"type": "cc", "channel": 4, "number": 102}, "knob1": {"type": "cc", "channel": 4, "number": 82}}, defaults)
    assert n == 2 and cfg["calib"]["fader1"]["number"] == 102
    e = Engine(cfg, Runner(b))
    e.process(mido.Message("control_change", channel=4, control=102, value=127)); assert b.vol == 1   # фейдер 1 = громкость
    b.vol = 0.5
    e.process(mido.Message("control_change", channel=4, control=82, value=127)); assert b.vol == 0.5   # 82 теперь ручка 1 (яркость)

def test_apply_swap_no_cascade():
    cfg = {"profiles": {"p": [{"trigger": {"type": "cc", "channel": None, "number": 1}}, {"trigger": {"type": "cc", "channel": None, "number": 2}}]}, "global": []}
    apply(cfg, {"a": {"type": "cc", "channel": 0, "number": 2}, "b": {"type": "cc", "channel": 0, "number": 1}},
          {"a": {"type": "cc", "number": 1}, "b": {"type": "cc", "number": 2}})
    assert [m["trigger"]["number"] for m in cfg["profiles"]["p"]] == [2, 1]

def test_migration_v1_any_channel():
    cfg = C.fix({"version": 1, "profiles": {"MiniLab 3": [{"trigger": {"type": "cc", "channel": 0, "number": 74}}, {"trigger": {"type": "note", "channel": 9, "number": 36}}]}})
    ts = [m["trigger"] for m in cfg["profiles"]["MiniLab 3"]]
    assert ts[0]["channel"] is None and ts[1]["channel"] == 9 and any(t["type"] == "pitch" for t in ts)

def test_opens_all_minilab_ports():
    h = FakeHub(); c = {"inputs": ["Minilab3 MIDI"]}
    st = MacroController(h, c, lambda: ["Minilab3 MIDI", "MIDIIN2 (Minilab3 MIDI)", "Other"]).apply()
    assert h.opened == {"Minilab3 MIDI", "MIDIIN2 (Minilab3 MIDI)"} and st["mode"] == "on"
    h2 = FakeHub(busy=["MIDIIN2 (Minilab3 MIDI)"])   # занятый доп. порт — не ошибка
    st = MacroController(h2, dict(c), lambda: ["Minilab3 MIDI", "MIDIIN2 (Minilab3 MIDI)"]).apply()
    assert st["mode"] == "on" and not st["errors"]

def test_pitch_strip_needs_enable_and_vbcable():
    b = FakeBackend(); r = Runner(b); asked = []; r.on_need_vbcable = lambda: asked.append(1)
    r({"type": "voice_pitch", "params": {}}, {"kind": "abs", "value": 0.9}); assert r.pitch is None   # выключено
    r.pitch_enabled = True
    class P:
        stream = None
        def start(s): raise LookupError
    r.pitch = P(); r({"type": "voice_pitch", "params": {}}, {"kind": "abs", "value": 0.9})
    assert asked and not r.pitch_enabled

def test_pitch_shifter_octave():
    from voice_fx import PitchShifter, strip_to_semitones
    assert strip_to_semitones(0.5) == 0 and strip_to_semitones(1.0) == 12 and strip_to_semitones(0.0) == -12
    sr = 48000; ps = PitchShifter(sr); ps.set_semitones(12)
    x = np.sin(2 * np.pi * 300 * np.arange(sr) / sr).astype(np.float32)
    y = np.concatenate([ps.process(x[i:i + 256]) for i in range(0, sr, 256)])[sr // 4:]
    S = np.abs(np.fft.rfft(y * np.hanning(len(y)))); fr = np.fft.rfftfreq(len(y), 1 / sr)
    assert abs((S * fr).sum() / S.sum() - 600) < 15          # энергия переехала на октаву выше
    assert S[np.argmin(abs(fr - 300))] < S.max() * 0.01       # исходного тона не осталось
    ps.set_semitones(0); z = ps.process(x[:256]); assert np.allclose(z, x[:256])
