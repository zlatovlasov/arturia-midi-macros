import sys, os, mido, queue
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["APPDATA"]="/tmp/midishot"
from PySide6.QtWidgets import QApplication
import gui, config as C, theme
from test_engine import FakeBackend, FakeHub
out=sys.argv[1]
app=QApplication(sys.argv); app.setStyleSheet(gui.QSS)
cfg=C.default_config(); cfg["asked_minilab"]=True; cfg["inputs"]=["Minilab3 MIDI"]
P=cfg["profiles"]["MiniLab 3"]
def setpad(note, action, params, mode="press", name=None):
    for m in [m for m in P if m["trigger"].get("number")==note and m["trigger"].get("channel")==9]: P.remove(m)
    P.append({"id":f"x{note}","name":name,"trigger":{"type":"note","channel":9,"number":note},"mode":mode,"action":{"type":action,"params":params}})
setpad(41,"open_links",{"urls":["https://spb-4.ru","https://vlaslovo.ru","https://github.com/zlatovlasov","https://web.telegram.org","https://mail.yandex.ru"],"delay":150,"browser":"chrome"},name="Пэд A6 · Рабочие ссылки")
setpad(42,"scene",{"steps":[{"do":"set_volume","arg":"35"},{"do":"app_volume","arg":"Spotify.exe 20"},{"do":"mic","arg":"on"},{"do":"open","arg":"Telegram.exe"},{"do":"wait","arg":"800"},{"do":"links","arg":"spb-4.ru vlaslovo.ru"},{"do":"hotkey","arg":"ctrl+shift+f13"}]},name="Пэд A7 · Сцена «Работа»")
setpad(38,"voice",{"engine":"windows"},mode="hold",name="Пэд A3 · Голос в текст")
cfg["pad_colors"]={"MiniLab 3":{"37":"#2ee66b","41":"#3b6cff","42":"#8b5cf6","38":"#ffd23a","40":"#ff4fb4"}}
cfg["profile_colors"]={"MiniLab 3":"#ffffff"}
hub=FakeHub(); hub.listeners=[]; hub.q=queue.Queue()
gui.Main.fake_outputs=["Minilab3 MIDI","MiniFuse 2 MIDI"]
w=gui.Main(cfg,FakeBackend(),hub=hub,save=False,inputs_fn=lambda:["Minilab3 MIDI","MiniFuse 2 MIDI"])
w.led.open=lambda n: True; w.led.send=lambda c: None; w.led.port=None
w.runner.state["mic_muted"]=True; w.update_leds()
w.show(); w.resize(1480, 900); app.processEvents()
def feed(ms):
    for m in ms: w.on_midi_ui("Minilab3 MIDI", m)
    app.processEvents()
live=[mido.Message("control_change",channel=0,control=c,value=v) for c,v in ((82,110),(83,70),(85,40),(17,95),(74,100),(71,30),(93,127),(1,80))]
live+=[mido.Message("note_on",channel=0,note=n,velocity=90) for n in (52,55,59)]+[mido.Message("note_on",channel=9,note=39,velocity=110)]
release=[mido.Message("note_off",channel=0,note=n) for n in (52,55,59)]+[mido.Message("note_off",channel=9,note=39)]
def shot(name): app.processEvents(); w.grab().save(f"{out}/{name}.png")
feed(live); shot("dark-live")
feed(release); w.dev.lit.clear()
w.dev.select_id("pad6"); shot("dark-pad-links")
w.dev.select_id("pad7"); shot("dark-scene-editor")
w.dev.select_id("pad3"); shot("dark-voice")
w.dev.select_id("pad2"); shot("dark-pad-colour")
w.cfg["theme"]="light"; w.apply_theme(); w.dev.select_id("pad1")
feed(live); shot("light-live")
feed(release); w.dev.lit.clear(); w.dev.select_id("pad6"); shot("light-pad-links")
w.dev.select_id("pad7"); shot("light-scene-editor")
w.ctl.set_enabled(False); shot("light-off")
w.cfg["theme"]="dark"; w.apply_theme(); shot("dark-off")
w.ctl.set_enabled(True)
d=gui.SettingsDialog(w); d.show(); app.processEvents(); d.grab().save(f"{out}/settings.png")

# ---- v4: монитор, свежая схема (нетронутые серые), калибровка, выбор действия
from picker import ActionPicker
def v4(prefix):
    w.dev.seen.clear(); w.dev.lit.clear(); w.monitor.lines.clear()
    for port,m in (("Minilab3 MIDI",mido.Message("note_on",channel=9,note=36,velocity=100)),
                   ("MIDIIN2 (Minilab3 MIDI)",mido.Message("control_change",channel=0,control=74,value=88)),
                   ("MIDIIN2 (Minilab3 MIDI)",mido.Message("control_change",channel=0,control=82,value=101)),
                   ("Minilab3 MIDI",mido.Message("pitchwheel",channel=0,pitch=2400))):
        w.on_midi_ui(port,m)
    app.processEvents(); shot(f"{prefix}-monitor")
    w.open_calibration(); cal=w.calib
    for n in (102,103,104): cal.feed(norm({"type":"control_change","channel":0,"control":n,"value":70}))
    app.processEvents(); shot(f"{prefix}-calibration"); cal.grab().save(f"{out}/{prefix}-calibration-dialog.png"); cal.reject(); app.processEvents()
    w.dev.select_id("pad6")
    d=ActionPicker(w,"open_links"); d.show(); d.resize(700,580); app.processEvents(); d.grab().save(f"{out}/{prefix}-picker-tiles.png")
    d.open_tile("Звук"); app.processEvents(); d.grab().save(f"{out}/{prefix}-picker-list.png")
    d.q.setText("ссыл"); app.processEvents(); d.grab().save(f"{out}/{prefix}-picker-search.png"); d.close()
from engine import norm_msg as norm
w.cfg["theme"]="dark"; w.apply_theme(); v4("dark")
w.cfg["theme"]="light"; w.apply_theme(); v4("light")
w.cfg["theme"]="dark"; w.apply_theme()
