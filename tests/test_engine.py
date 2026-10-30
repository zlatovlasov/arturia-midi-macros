import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import mido
from engine import Engine
from actions import Runner
from presets import minilab3_profile, is_minilab3
import config as C

class FakeBackend:
    def __init__(s): s.log=[]; s.vol=0.5; s.mic=0.5; s.mute=False; s.micmute=False; s.bri=0.5; s.apps={}; s.devs=[("a","Динамики"),("b","Наушники Arturia")]; s.cur="a"
    def get_vol(s, mic=False): return s.mic if mic else s.vol
    def set_vol(s, v, mic=False):
        v=max(0,min(1,v))
        if mic: s.mic=v
        else: s.vol=v
    def get_mute(s, mic=False): return s.micmute if mic else s.mute
    def set_mute(s, m, mic=False):
        if mic: s.micmute=m
        else: s.mute=m
    def app_vol(s, p, value=None, delta=None): s.apps[p]=value if value is not None else s.apps.get(p,1)+delta
    def app_mute_toggle(s,p): s.log.append(("appmute",p))
    def output_devices(s): return s.devs
    def default_output_id(s): return s.cur
    def set_default_output(s,i): s.cur=i
    def get_brightness(s): return s.bri
    def set_brightness(s,v): s.bri=v
    def __getattr__(s, name):
        return lambda *a: s.log.append((name,)+a)

class Clock:
    t=0.0
    def __call__(s): return s.t

def setup():
    b=FakeBackend(); prof=[]
    cfg={"profiles":{"MiniLab 3":minilab3_profile(),"Второй":[]},"active_profile":"MiniLab 3","global":[]}
    clk=Clock(); r=Runner(b, on_profile=lambda n,st: e.set_profile(n,st))
    e=Engine(cfg,r,clock=clk); return b,e,clk,cfg

def test_faders_abs():
    b,e,_,_=setup()
    e.process(mido.Message("control_change",channel=0,control=82,value=127)); assert b.vol==1
    e.process(mido.Message("control_change",channel=0,control=82,value=0)); assert b.vol==0
    e.process(mido.Message("control_change",channel=0,control=83,value=64)); assert abs(b.mic-64/127)<1e-6
    e.process(mido.Message("control_change",channel=0,control=85,value=127)); assert b.apps["chrome.exe"]==1

def test_channel_aware():
    b,e,_,_=setup()
    e.process(mido.Message("control_change",channel=5,control=82,value=127)); assert b.vol==0.5

def test_relative_encoder():
    b,e,_,_=setup()
    e.process(mido.Message("control_change",channel=0,control=28,value=66)); assert abs(b.vol-0.54)<1e-6
    e.process(mido.Message("control_change",channel=0,control=28,value=63)); assert abs(b.vol-0.52)<1e-6

def test_abs_to_rel_scroll():
    b,e,_,_=setup()
    for v in (10,11,13): e.process(mido.Message("control_change",channel=0,control=76,value=v))
    assert [x[0] for x in b.log]==["scroll","scroll"]

def test_pad_mic_mute_and_velocity_note_off():
    b,e,_,_=setup()
    e.process(mido.Message("note_on",channel=9,note=36,velocity=100)); assert b.micmute
    e.process(mido.Message("note_on",channel=9,note=36,velocity=0))  # note-off через vel 0
    assert b.micmute
    e.process(mido.Message("note_on",channel=9,note=36,velocity=50)); assert not b.micmute
    # та же нота на канале 1 (клавиша) не трогает
    e.process(mido.Message("note_on",channel=0,note=36,velocity=50)); assert not b.micmute

def test_tap_vs_long():
    b,e,clk,_=setup()
    e.process(mido.Message("note_on",channel=9,note=43,velocity=90)); clk.t=0.2
    e.process(mido.Message("note_off",channel=9,note=43)); assert b.log==[("screenshot","snip")]
    b.log.clear(); clk.t=1
    e.process(mido.Message("note_on",channel=9,note=43,velocity=90)); clk.t=1.7; e.tick()
    assert b.log==[("lock",)]
    e.process(mido.Message("note_off",channel=9,note=43)); assert b.log==[("lock",)]

def test_velocity_threshold():
    b,e,_,cfg=setup()
    cfg["profiles"]["Второй"]=[{"id":"x","name":"t","trigger":{"type":"note","channel":None,"number":60},"mode":"press","velocity_min":100,"action":{"type":"hotkey","params":{"keys":"f13"}}}]
    e.set_profile("Второй")
    e.process(mido.Message("note_on",channel=3,note=60,velocity=40)); assert b.log==[]
    e.process(mido.Message("note_on",channel=3,note=60,velocity=120)); assert b.log==[("hotkey","f13")]

def test_profile_switch_and_output():
    b,e,_,cfg=setup()
    e.process(mido.Message("note_on",channel=9,note=44,velocity=90)); assert b.cur=="b"
    e.process(mido.Message("note_on",channel=9,note=51,velocity=90)); e.process(mido.Message("note_off",channel=9,note=51)); assert cfg["active_profile"]=="Второй"

def test_button_cc_and_pitch_and_macro():
    b,e,_,cfg=setup()
    b.mute=False
    e.process(mido.Message("control_change",channel=0,control=118,value=127)); assert b.mute
    e.process(mido.Message("control_change",channel=0,control=118,value=0)); assert b.mute
    cfg["global"]=[{"id":"p","name":"pb","trigger":{"type":"pitch","channel":0},"mode":"absolute","action":{"type":"brightness","params":{}}},
                   {"id":"m","name":"mac","trigger":{"type":"program","channel":0,"number":3},"action":{"type":"macro","params":{"steps":"hotkey ctrl+a\nwait 1\ntext hi"}}}]
    e.process(mido.Message("pitchwheel",channel=0,pitch=8191)); assert b.bri==1
    e.process(mido.Message("program_change",channel=0,program=3)); assert b.log[-2:]==[("hotkey","ctrl+a"),("write","hi")]

def test_config_roundtrip():
    d=tempfile.mkdtemp(); p=os.path.join(d,"c.json")
    cfg=C.default_config(); C.save(cfg,p); c2=C.load(p)
    assert len(c2["profiles"]["MiniLab 3"])==len(minilab3_profile())
    assert json.load(open(p,encoding="utf-8"))["active_profile"]=="MiniLab 3"

def test_detect():
    assert is_minilab3("Minilab3 MIDI 0") and is_minilab3("MiniLab 3 MIDI") and not is_minilab3("KeyLab mkII")

# ---------- главный выключатель
from controller import MacroController, fl_is_running, BUSY

class FakeHub:
    def __init__(s, busy=()): s.opened=set(); s.busy=set(busy); s.closes=0
    def open(s, names):
        for n in list(s.opened):
            if n not in names: s.opened.discard(n)
        errs=[]
        for n in names:
            if n in s.busy: errs.append(f"{n}: MMSYSERR_ALLOCATED")
            else: s.opened.add(n)
        return errs
    def close(s): s.opened.clear(); s.closes+=1

def mk(busy=(), **cfg):
    c={"inputs":["Minilab3 MIDI"], **cfg}; h=FakeHub(busy); states=[]
    return MacroController(h, c, lambda: ["Minilab3 MIDI","Other"], states.append), h, states, c

def test_toggle_closes_and_reopens():
    m,h,st,_=mk(); m.apply(); assert h.opened=={"Minilab3 MIDI"} and m.state["mode"]=="on"
    m.toggle(); assert h.opened==set() and m.state["mode"]=="off"
    m.toggle(); assert h.opened=={"Minilab3 MIDI"} and st[-1]["mode"]=="on"

def test_start_off():
    m,h,_,_=mk(start_off=True); m.apply(); assert h.opened==set() and m.state["mode"]=="off"

def test_busy_port_error():
    m,h,_,_=mk(busy={"Minilab3 MIDI"}); s=m.apply()
    assert s["mode"]=="error" and BUSY in s["errors"][0]

def test_auto_off_fl():
    m,h,_,c=mk(auto_off_fl=True); m.apply()
    m.set_fl_running(True); assert h.opened==set() and m.state["mode"]=="fl"
    m.set_fl_running(False); assert h.opened=={"Minilab3 MIDI"}
    c["auto_off_fl"]=False; m.set_fl_running(True); assert h.opened=={"Minilab3 MIDI"}

def test_fl_detect():
    assert fl_is_running(["explorer.exe","FL64.exe"]) and not fl_is_running(["chrome.exe"])

def test_pad_long_press_turns_off():
    b=FakeBackend(); offs=[]
    cfg={"profiles":{"P":minilab3_profile()},"active_profile":"P","global":[]}
    clk=Clock(); e=Engine(cfg, Runner(b, on_off=lambda: offs.append(1), on_profile=lambda n,s: None), clock=clk)
    e.process(mido.Message("note_on",channel=9,note=51,velocity=90)); clk.t=2; e.tick()
    assert offs==[1]

# ---------- открыть ссылки
from actions import normalize_urls, MAX_LINKS

def test_normalize_urls():
    ok, bad = normalize_urls(["spb-4.ru", " https://vlaslovo.ru/a?b=1 ", "", "http://localhost:3000", "не ссылка", "ftp://x.org"])
    assert ok == ["https://spb-4.ru", "https://vlaslovo.ru/a?b=1", "http://localhost:3000", "ftp://x.org"]
    assert bad == ["не ссылка"]

def test_links_limit():
    ok, bad = normalize_urls([f"site{i}.ru" for i in range(13)])
    assert len(ok) == MAX_LINKS and bad

def test_links_action_opens_all():
    b=FakeBackend(); notes=[]
    r=Runner(b, notify=notes.append)
    r({"type":"open_links","params":{"urls":["ya.ru","https://github.com","bad url"],"delay":0,"browser":"edge"}},{"kind":"trigger"})
    assert b.log==[("open_url","https://ya.ru","edge"),("open_url","https://github.com","edge")]
    assert notes and "bad url" in notes[0]
    b.log.clear(); r({"type":"open_links","params":{"urls":["ya.ru"]}},{"kind":"abs","value":0.3})
    assert b.log==[]  # от фейдера не открывает

def test_links_from_pad():
    b=FakeBackend()
    cfg={"profiles":{"P":[{"id":"l","name":"L","trigger":{"type":"note","channel":9,"number":40},"mode":"press",
        "action":{"type":"open_links","params":{"urls":["a.ru","b.ru","c.ru"],"delay":0}}}]},"active_profile":"P","global":[]}
    e=Engine(cfg, Runner(b)); e.process(mido.Message("note_on",channel=9,note=40,velocity=80))
    assert [x[1] for x in b.log]==["https://a.ru","https://b.ru","https://c.ru"]

# ---------- сцены, голос, подсветка
from macro import scene_to_steps, parse_macro
from leds import pad_sysex, compute_pad_colors, LedOut, MUTED, LIVE
from presets import maybe_minilab_port

def test_scene_runs_in_order():
    b=FakeBackend(); r=Runner(b)
    steps=[{"do":"set_volume","arg":"40"},{"do":"app_volume","arg":"chrome.exe 30"},{"do":"mic","arg":"off"},
           {"do":"open","arg":"Telegram.exe"},{"do":"wait","arg":"1"},{"do":"links","arg":"ya.ru github.com"},{"do":"bogus","arg":"x"}]
    r({"type":"scene","params":{"steps":steps}},{"kind":"trigger"})
    assert abs(b.vol-0.4)<1e-9 and abs(b.apps["chrome.exe"]-0.3)<1e-9 and b.micmute and r.state["mic_muted"]
    assert b.log==[("open","Telegram.exe"),("open_url","https://ya.ru","default"),("open_url","https://github.com","default")]

def test_macro_new_cmds():
    assert parse_macro("set_volume 20\nmic on\nlinks a.ru") == [("set_volume","20"),("mic","on"),("links","a.ru")]

def test_voice_windows_hold():
    b=FakeBackend(); r=Runner(b)
    cfg={"profiles":{"P":[{"id":"v","name":"v","trigger":{"type":"note","channel":9,"number":37},"mode":"hold","action":{"type":"voice","params":{"engine":"windows"}}}]},"active_profile":"P","global":[]}
    e=Engine(cfg,r); e.process(mido.Message("note_on",channel=9,note=37,velocity=90)); assert b.log==[("hotkey","windows+h")]
    e.process(mido.Message("note_off",channel=9,note=37)); assert b.log==[("hotkey","windows+h")]*2

def test_pad_sysex_bytes():
    d=pad_sysex(0,"#ff0000"); assert d==[0x00,0x20,0x6B,0x7F,0x42,0x02,0x02,0x16,0x04,0x7F,0x00,0x00]
    assert pad_sysex(7,"#ffffff")[8]==0x0B

def test_pad_colors_state():
    cfg={"profiles":{"MiniLab 3":minilab3_profile()},"active_profile":"MiniLab 3","global":[],
         "pad_colors":{"MiniLab 3":{"37":"#2ee66b"}},"profile_colors":{"MiniLab 3":"#ffffff"}}
    c=compute_pad_colors(cfg,0,{"mic_muted":True}); assert c[0]==MUTED and c[1]=="#2ee66b" and c[2]=="#595959"
    c=compute_pad_colors(cfg,0,{"mic_muted":False}); assert c[0]==LIVE
    c=compute_pad_colors(cfg,0,{"all_muted":True}); assert c[4]==MUTED
    assert compute_pad_colors(cfg,0,{},enabled=False)==["#000000"]*8

def test_led_port_choice_and_suggest():
    assert LedOut.find_output(["MiniFuse 2 MIDI","Minilab3 MIDI","Minilab3 DIN THRU"])=="Minilab3 MIDI"
    assert LedOut.find_output(["MiniFuse 2 MIDI"]) is None
    assert maybe_minilab_port("MiniFuse 2 MIDI In") and not maybe_minilab_port("Microsoft GS Wavetable Synth")
