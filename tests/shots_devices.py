"""Скриншоты схемы каждой модели (python tests/shots_devices.py <папка>; на Linux: QT_QPA_PLATFORM=offscreen)."""
import sys, os, mido, queue
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["APPDATA"] = "/tmp/midishot-dev"
from PySide6.QtWidgets import QApplication
import gui, config as C
import devices as D
from test_engine import FakeBackend, FakeHub

out = sys.argv[1] if len(sys.argv) > 1 else "shots"
os.makedirs(out, exist_ok=True)
app = QApplication(sys.argv); app.setStyleSheet(gui.QSS)

# что «пошевелить» на каждой модели, чтобы схема ожила (номера — из профиля, без выдумок)
def demo_events(dev):
    evs = []
    for c in D.get(dev)["controls"]:
        t = D.default_trig(c)
        if t is None or c["kind"] in ("white", "black"): continue
        ch = t["channel"] if t["channel"] is not None else 0
        if t["type"] == "cc" and c["kind"] in ("knob", "fader", "encoder", "strip"):
            evs.append(mido.Message("control_change", channel=ch, control=t["number"], value=(t["number"] * 37) % 128))
        elif t["type"] == "pitch":
            evs.append(mido.Message("pitchwheel", channel=ch, pitch=2400))
    return evs

GENERIC = [mido.Message("control_change", channel=2, control=n, value=v) for n, v in ((21, 90), (22, 30), (23, 64), (7, 110))]
GENERIC += [mido.Message("note_on", channel=9, note=n, velocity=100) for n in (36, 37, 38, 39)]
GENERIC += [mido.Message("pitchwheel", channel=0, pitch=3000), mido.Message("program_change", channel=0, program=5)]

for d in D.all_devices():
    dev = d["id"]
    cfg = C.default_config(); cfg["asked_minilab"] = True; cfg["asked_devices"] = [x["id"] for x in D.all_devices()]
    cfg["device"] = dev; cfg["inputs"] = ["Demo MIDI"]
    if dev != "minilab3":
        n = d["name"]; cfg["profiles"][n] = D.starter(dev); cfg["profile_devices"][n] = dev; cfg["active_profile"] = n
    hub = FakeHub(); hub.listeners = []; hub.q = queue.Queue()
    gui.Main.fake_outputs = []
    w = gui.Main(cfg, FakeBackend(), hub=hub, save=False, inputs_fn=lambda: ["Demo MIDI"])
    w.led.open = lambda n: True; w.led.send = lambda c: None; w.led.port = None
    w.show(); w.resize(1480, 900); app.processEvents()
    for m in (GENERIC if d.get("dynamic") else demo_events(dev)):
        w.on_midi_ui("Demo MIDI", m)
    app.processEvents(); w.dev.lit.clear(); w.dev.held.clear()
    first = w._first_control()
    if first: w.dev.select_id(first)
    app.processEvents()
    w.grab().save(f"{out}/{dev}-window.png")
    if dev == "keylab_essential3":   # контрол без опубликованного номера: подсказка «пошевелите»
        w.dev.select_id("knob1"); app.processEvents(); w.grab().save(f"{out}/{dev}-unknown-control.png")
        w.on_midi_ui("Demo MIDI", mido.Message("control_change", channel=0, control=96, value=80)); app.processEvents()
        w.grab().save(f"{out}/{dev}-learned-control.png")
    w.dev.resize(1280, int(1280 * w.dev.H / w.dev.W)); app.processEvents()
    w.dev.grab().save(f"{out}/{dev}-schematic.png")
    w.hide(); w.tray.hide(); w.worker.running = False
    print(dev, "ok")
