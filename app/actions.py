"""Действия. Вся Windows-специфика импортируется лениво, чтобы модуль грузился и на Linux (для тестов)."""
import os, subprocess, time, webbrowser, sys, threading
from macro import parse_macro, scene_to_steps

# key: (название, [(param, подпись, тип, по умолчанию, варианты)], категория)
ACTIONS = {
    "none":            ("— нет —", [], "Общее"),
    "open":            ("Открыть программу / файл / ссылку", [("target", "Путь, команда или URL", "str", "notepad.exe", None), ("args", "Аргументы", "str", "", None)], "Запуск"),
    "hotkey":          ("Сочетание клавиш", [("keys", "Клавиши (напр. ctrl+shift+s)", "str", "ctrl+c", None)], "Клавиатура"),
    "rel_hotkeys":     ("Крутилка: клавиши вправо/влево", [("up", "Вправо", "str", "ctrl+=", None), ("down", "Влево", "str", "ctrl+-", None)], "Клавиатура"),
    "type_text":       ("Напечатать текст", [("text", "Текст", "text", "Привет!", None)], "Клавиатура"),
    "macro":           ("Макрос (последовательность)", [("steps", "Шаги (по строке)", "text", "hotkey ctrl+a\nwait 100\nhotkey ctrl+c", None)], "Клавиатура"),
    "media":           ("Медиа", [("cmd", "Команда", "choice", "play_pause", ["play_pause", "next", "prev", "stop"])], "Медиа"),
    "master_volume":   ("Громкость системы", [("step", "Шаг для кнопки/энкодера, %", "int", 5, None)], "Звук"),
    "master_mute":     ("Звук системы вкл/выкл", [], "Звук"),
    "app_volume":      ("Громкость приложения", [("process", "Процесс (напр. chrome.exe)", "str", "chrome.exe", None), ("step", "Шаг, %", "int", 5, None)], "Звук"),
    "app_mute":        ("Приложение: звук вкл/выкл", [("process", "Процесс", "str", "chrome.exe", None)], "Звук"),
    "mic_volume":      ("Громкость микрофона", [("step", "Шаг, %", "int", 5, None)], "Звук"),
    "mic_mute":        ("Микрофон вкл/выкл", [("mode", "Режим", "choice", "toggle", ["toggle", "mute", "unmute", "push_to_talk"])], "Звук"),
    "mute_all":        ("Выключить всё (звук + микрофон)", [], "Звук"),
    "audio_output":    ("Сменить устройство вывода", [("device", "Часть имени (пусто = следующее)", "str", "", None)], "Звук"),
    "window":          ("Окна", [("cmd", "Команда", "choice", "alt_tab", ["alt_tab", "minimize", "maximize", "close", "show_desktop", "task_view", "snap_left", "snap_right"])], "Окна"),
    "desktop":         ("Виртуальный рабочий стол", [("cmd", "Команда", "choice", "next", ["next", "prev", "new", "close"])], "Окна"),
    "lock":            ("Заблокировать ПК", [], "Система"),
    "screenshot":      ("Скриншот", [("mode", "Режим", "choice", "snip", ["snip", "full_to_file"])], "Система"),
    "run":             ("Команда cmd / PowerShell", [("shell", "Оболочка", "choice", "powershell", ["powershell", "cmd"]), ("command", "Команда", "text", "Get-Date", None), ("hidden", "Скрыть окно (1/0)", "int", 1, None)], "Система"),
    "brightness":      ("Яркость монитора", [("step", "Шаг, %", "int", 10, None)], "Система"),
    "scroll":          ("Прокрутка мыши", [("lines", "Строк за шаг", "int", 3, None)], "Система"),
    "sleep":           ("Спящий режим", [], "Система"),
    "profile":         ("Переключить профиль", [("name", "Профиль (пусто = следующий)", "str", "", None)], "Профили"),
}


def label(action):
    a = ACTIONS.get(action.get("type", "none"))
    if not a:
        return action.get("type", "?")
    p = action.get("params", {})
    if action.get("type") == "open_links":
        n = len(normalize_urls(p.get("urls", []))[0]); return f"{a[0].split(' (')[0]} ({n} шт.)"
    extra = ", ".join(str(v) for v in p.values() if v not in ("", None) and not isinstance(v, list))[:40]
    return a[0] + (f" ({extra})" if extra else "")


def clamp(x):
    return max(0.0, min(1.0, x))


MAX_LINKS = 10
import re as _re
_URL = _re.compile(r"^(https?|ftp)://[^\s/$.?#][^\s]*$", _re.I)

def normalize_urls(items):
    """-> (годные URL, ошибки). Пустые строки пропускаются, https:// добавляется сам, максимум 10."""
    ok, bad = [], []
    for raw in items or []:
        u = str(raw).strip()
        if not u:
            continue
        if not _re.match(r"^[a-z][a-z0-9+.-]*://", u, _re.I):
            u = "https://" + u
        if _URL.match(u) and "." in u.split("://", 1)[1].split("/")[0] or u.lower().startswith("http://localhost"):
            ok.append(u)
        else:
            bad.append(str(raw).strip())
    if len(ok) > MAX_LINKS:
        bad.append(f"лишние ссылки (больше {MAX_LINKS}) пропущены")
        ok = ok[:MAX_LINKS]
    return ok, bad

def find_browsers():
    """Установленные браузеры (Windows): имя -> путь к exe."""
    pf = [os.environ.get(k, "") for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
    cand = {"chrome": [r"Google\Chrome\Application\chrome.exe"], "edge": [r"Microsoft\Edge\Application\msedge.exe"],
            "firefox": [r"Mozilla Firefox\firefox.exe"], "yandex": [r"Yandex\YandexBrowser\Application\browser.exe"]}
    out = {}
    for name, rels in cand.items():
        for base in pf:
            for rel in rels:
                p = os.path.join(base, rel)
                if base and os.path.exists(p):
                    out.setdefault(name, p)
    return out


class WinBackend:
    """Реальные вызовы Windows."""
    def __init__(self):
        self._com = threading.local()

    def _co(self):
        if not getattr(self._com, "ok", False):
            import comtypes
            comtypes.CoInitialize()
            self._com.ok = True

    # --- звук
    def _endpoint(self, mic=False):
        self._co()
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetMicrophone() if mic else AudioUtilities.GetSpeakers()
        if hasattr(dev, "EndpointVolume"):
            return dev.EndpointVolume
        from comtypes import CLSCTX_ALL, cast, POINTER
        itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(itf, POINTER(IAudioEndpointVolume))

    def get_vol(self, mic=False): return self._endpoint(mic).GetMasterVolumeLevelScalar()
    def set_vol(self, v, mic=False): self._endpoint(mic).SetMasterVolumeLevelScalar(clamp(v), None)
    def get_mute(self, mic=False): return bool(self._endpoint(mic).GetMute())
    def set_mute(self, m, mic=False): self._endpoint(mic).SetMute(1 if m else 0, None)

    def _sessions(self, proc):
        self._co()
        from pycaw.pycaw import AudioUtilities
        proc = proc.lower()
        return [s for s in AudioUtilities.GetAllSessions() if s.Process and s.Process.name().lower() == proc]

    def app_vol(self, proc, value=None, delta=None):
        for s in self._sessions(proc):
            sv = s.SimpleAudioVolume
            v = value if value is not None else sv.GetMasterVolume() + delta
            sv.SetMasterVolume(clamp(v), None)

    def app_mute_toggle(self, proc):
        for s in self._sessions(proc):
            sv = s.SimpleAudioVolume
            sv.SetMute(0 if sv.GetMute() else 1, None)

    def output_devices(self):
        self._co()
        from pycaw.pycaw import AudioUtilities
        out = []
        for d in AudioUtilities.GetAllDevices():
            st = str(getattr(d, "state", ""))
            if d.id and d.id.startswith("{0.0.0.") and ("Active" in st or st.endswith("1")):
                out.append((d.id, d.FriendlyName or d.id))
        return out

    def default_output_id(self):
        self._co()
        from pycaw.pycaw import AudioUtilities
        d = AudioUtilities.GetSpeakers()
        try:
            return d.id if hasattr(d, "id") else d.GetId()
        except Exception:
            return None

    def set_default_output(self, dev_id):
        self._co()
        import comtypes
        from comtypes import GUID, COMMETHOD, HRESULT, IUnknown
        from ctypes import c_void_p, c_wchar_p, c_int
        class IPolicyConfig(IUnknown):
            _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
            _methods_ = [COMMETHOD([], HRESULT, n, (["in"], c_void_p, "a"), (["in"], c_void_p, "b"), (["in"], c_void_p, "c")) for n in
                         ("GetMixFormat", "GetDeviceFormat", "ResetDeviceFormat", "SetDeviceFormat", "GetProcessingPeriod",
                          "SetProcessingPeriod", "GetShareMode", "SetShareMode", "GetPropertyValue", "SetPropertyValue")] + [
                COMMETHOD([], HRESULT, "SetDefaultEndpoint", (["in"], c_wchar_p, "id"), (["in"], c_int, "role")),
            ]
        pc = comtypes.CoCreateInstance(GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}"), IPolicyConfig, comtypes.CLSCTX_ALL)
        for role in (0, 1, 2):
            pc.SetDefaultEndpoint(dev_id, role)

    # --- клавиатура/мышь
    def hotkey(self, keys):
        import keyboard
        keyboard.send(keys)

    def write(self, text):
        import keyboard
        keyboard.write(text, delay=0.005)

    def media(self, cmd):
        import keyboard
        keyboard.send({"play_pause": "play/pause media", "next": "next track", "prev": "previous track", "stop": "stop media"}[cmd])

    def scroll(self, n):
        import ctypes
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, int(n * 120), 0)

    # --- система
    def open_url(self, url, browser="default"):
        exe = find_browsers().get(browser) if browser != "default" else None
        if exe:
            subprocess.Popen([exe, url])
        else:
            webbrowser.open(url)

    def open(self, target, args=""):
        if "://" in target:
            webbrowser.open(target)
        elif args:
            subprocess.Popen(f'"{target}" {args}', shell=True)
        else:
            try:
                os.startfile(target)
            except OSError:
                subprocess.Popen(target, shell=True)

    def run(self, shell, command, hidden):
        flags = 0x08000000 if hidden else 0  # CREATE_NO_WINDOW
        if shell == "cmd":
            subprocess.Popen(["cmd", "/c", command], creationflags=flags)
        else:
            subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], creationflags=flags)

    def window(self, cmd):
        import ctypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        if cmd == "minimize": u.ShowWindow(h, 6)
        elif cmd == "maximize": u.ShowWindow(h, 3)
        elif cmd == "close": u.PostMessageW(h, 0x0010, 0, 0)
        else:
            self.hotkey({"alt_tab": "alt+tab", "show_desktop": "windows+d", "task_view": "windows+tab",
                         "snap_left": "windows+left", "snap_right": "windows+right"}[cmd])

    def desktop(self, cmd):
        self.hotkey({"next": "ctrl+windows+right", "prev": "ctrl+windows+left", "new": "ctrl+windows+d", "close": "ctrl+windows+f4"}[cmd])

    def lock(self):
        import ctypes
        ctypes.windll.user32.LockWorkStation()

    def sleep(self):
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

    def screenshot(self, mode):
        if mode == "snip":
            self.hotkey("windows+shift+s")
        else:
            from PIL import ImageGrab
            d = os.path.join(os.path.expanduser("~"), "Pictures", "MIDI Screenshots")
            os.makedirs(d, exist_ok=True)
            ImageGrab.grab(all_screens=True).save(os.path.join(d, time.strftime("shot_%Y%m%d_%H%M%S.png")))

    def get_brightness(self):
        import screen_brightness_control as sbc
        return sbc.get_brightness()[0] / 100.0

    def set_brightness(self, v):
        import screen_brightness_control as sbc
        sbc.set_brightness(int(clamp(v) * 100))


class Runner:
    """Выполняет действие с учётом контекста движка (abs/rel/trigger/on/off)."""
    def __init__(self, backend, on_profile=None, notify=None, on_off=None):
        self.b = backend
        self.on_off = on_off or (lambda: None)
        self.state = {"mic_muted": False, "master_muted": False, "all_muted": False}
        self.on_state = lambda st: None   # для подсветки пэдов
        self.voice = None                 # VoiceEngine (vosk), создаётся лениво
        self.on_profile = on_profile or (lambda name, step: None)
        self.notify = notify or (lambda text: None)
        self._out_idx = 0
        self.pitch = None                 # VoicePitch, создаётся лениво
        self.pitch_enabled = False        # включается в настройках
        self.pitch_output = "CABLE Input"
        self.on_need_vbcable = lambda: None
        self._pitch_warned = False

    def __call__(self, action, ctx):
        try:
            self.run(action, ctx)
        except Exception as e:
            self.notify(f"Ошибка «{ACTIONS.get(action.get('type'), ('?',))[0]}»: {e}")

    def _level(self, get, set_, ctx, step):
        k = ctx["kind"]
        if k == "abs": set_(ctx["value"])
        elif k == "rel": set_(get() + ctx["delta"] * step / 100.0)
        elif k in ("trigger", "on"): set_(get() + step / 100.0)  # кнопка: шаг (отрицательный шаг — убавить)

    def _set_state(self, **kw):
        self.state.update(kw); self.on_state(dict(self.state))

    def run(self, a, ctx):
        t, p, b, k = a.get("type", "none"), a.get("params", {}), self.b, ctx["kind"]
        if t == "voice": return self.run_voice(p.get("engine", "windows"), k)
        if t == "voice_pitch": return self.run_pitch(p, ctx)
        press = k in ("trigger", "on")
        if t == "none": return
        if t == "master_volume": return self._level(b.get_vol, b.set_vol, ctx, int(p.get("step", 5)))
        if t == "mic_volume": return self._level(lambda: b.get_vol(True), lambda v: b.set_vol(v, True), ctx, int(p.get("step", 5)))
        if t == "brightness": return self._level(b.get_brightness, b.set_brightness, ctx, int(p.get("step", 10)))
        if t == "app_volume":
            proc, step = p.get("process", ""), int(p.get("step", 5))
            if k == "abs": return b.app_vol(proc, value=ctx["value"])
            d = ctx["delta"] if k == "rel" else 1
            return b.app_vol(proc, delta=d * step / 100.0) if k == "rel" or press else None
        if t == "rel_hotkeys":
            if k == "rel":
                for _ in range(min(abs(ctx["delta"]), 10)):
                    b.hotkey(p["up"] if ctx["delta"] > 0 else p["down"])
            elif press: b.hotkey(p["up"])
            return
        if t == "scroll":
            if k == "rel": b.scroll(ctx["delta"] * int(p.get("lines", 3)) / 3)
            elif press: b.scroll(int(p.get("lines", 3)) / 3)
            return
        if t == "mic_mute":
            m = p.get("mode", "toggle")
            if m == "push_to_talk":
                if k in ("on", "trigger"): b.set_mute(False, True); self._set_state(mic_muted=False)
                if k in ("off",): b.set_mute(True, True); self._set_state(mic_muted=True)
                return
            if not press: return
            new = {"toggle": not b.get_mute(True), "mute": True, "unmute": False}[m]
            b.set_mute(new, True); self._set_state(mic_muted=new)
            self.notify("Микрофон выключен" if new else "Микрофон включён")
            return
        if not press:
            return  # дальше — только «кнопочные» действия
        if t == "master_mute":
            new = not b.get_mute(); b.set_mute(new); self._set_state(master_muted=new); self.notify("Звук выключен" if new else "Звук включён")
        elif t == "mute_all":
            new = not (b.get_mute() and b.get_mute(True))
            b.set_mute(new); b.set_mute(new, True); self._set_state(all_muted=new, mic_muted=new, master_muted=new); self.notify("Всё выключено" if new else "Всё включено")
        elif t == "app_mute": b.app_mute_toggle(p.get("process", ""))
        elif t == "audio_output": self._switch_output(p.get("device", ""))
        elif t == "open": b.open(p.get("target", ""), p.get("args", ""))
        elif t == "hotkey": b.hotkey(p.get("keys", ""))
        elif t == "type_text": b.write(p.get("text", ""))
        elif t == "media": b.media(p.get("cmd", "play_pause"))
        elif t == "window": b.window(p.get("cmd", "alt_tab"))
        elif t == "desktop": b.desktop(p.get("cmd", "next"))
        elif t == "lock": b.lock()
        elif t == "sleep": b.sleep()
        elif t == "screenshot": b.screenshot(p.get("mode", "snip"))
        elif t == "run": b.run(p.get("shell", "powershell"), p.get("command", ""), int(p.get("hidden", 1)))
        elif t == "profile":
            name = p.get("name") or None
            self.on_profile(name, 0 if name else 1)
        elif t == "open_links":
            urls, bad = normalize_urls(p.get("urls", []))
            for i, u in enumerate(urls):
                if i: time.sleep(max(0, int(p.get("delay", 150))) / 1000.0)
                self.b.open_url(u, p.get("browser", "default"))
            if bad: self.notify("Пропущены: " + ", ".join(bad))
        elif t == "macros_off": self.on_off()
        elif t == "macro": self.run_macro(p.get("steps", ""))
        elif t == "scene":
            self.run_steps(scene_to_steps(p.get("steps", []))); self.notify("Сцена выполнена")

    def _switch_output(self, part):
        devs = self.b.output_devices()
        if not devs: return
        if part:
            hit = [d for d in devs if part.lower() in d[1].lower()]
            if not hit: raise RuntimeError(f"нет устройства «{part}»")
            dev = hit[0]
        else:
            cur = self.b.default_output_id()
            ids = [d[0] for d in devs]
            i = ids.index(cur) if cur in ids else -1
            dev = devs[(i + 1) % len(devs)]
        self.b.set_default_output(dev[0])
        self.notify(f"Вывод звука: {dev[1]}")

    def run_voice(self, engine, k):
        """Удержание: on — начать, off — закончить. windows: Win+H (встроенный ввод голосом)."""
        if engine == "windows":
            if k in ("on", "trigger"): self.b.hotkey("windows+h")
            if k == "off": time.sleep(0.5); self.b.hotkey("windows+h")
            return
        if self.voice is None:
            from voice import VoiceEngine
            self.voice = VoiceEngine(notify=self.notify, paste=self.b.write)
        if k in ("on", "trigger"): self.voice.start()
        elif k == "off": self.voice.stop_and_paste()

    def run_pitch(self, p, ctx):
        """Полоса Pitch: центр — обычный голос, вверх/вниз — до ±range полутонов."""
        if ctx["kind"] != "abs": return
        if not self.pitch_enabled:
            if not self._pitch_warned:
                self._pitch_warned = True; self.notify("Питч голоса выключен — включите его в Настройках")
            return
        if self.pitch is None:
            from voice_fx import VoicePitch
            self.pitch = VoicePitch(notify=self.notify, output=self.pitch_output)
        if not self.pitch.stream:
            try: self.pitch.start()
            except LookupError:
                self.pitch_enabled = False; self.on_need_vbcable(); return
        st = self.pitch.set(ctx["value"], int(p.get("range", 12)))
        self._set_state(pitch=st)

    def stop_pitch(self):
        if self.pitch: self.pitch.stop()

    def run_macro(self, src):
        self.run_steps(parse_macro(src))

    def run_steps(self, steps):
        for cmd, arg in steps:
            if cmd == "wait": time.sleep(arg / 1000.0)
            elif cmd in ("hotkey", "key"): self.b.hotkey(arg)
            elif cmd == "text": self.b.write(arg)
            elif cmd == "open": self.b.open(arg)
            elif cmd == "cmd": self.b.run("cmd", arg, 1)
            elif cmd == "ps": self.b.run("powershell", arg, 1)
            elif cmd == "media": self.b.media(arg or "play_pause")
            elif cmd == "volume": self.run({"type": "master_volume", "params": {"step": int(arg or 5)}}, {"kind": "trigger"})
            elif cmd == "mic_mute": self.run({"type": "mic_mute", "params": {}}, {"kind": "trigger"})
            elif cmd == "desktop": self.b.desktop(arg or "next")
            elif cmd == "window": self.b.window(arg or "alt_tab")
            elif cmd == "set_volume": self.b.set_vol(int(arg or 50) / 100.0)
            elif cmd == "app_volume":
                proc, _, v = arg.rpartition(" "); self.b.app_vol(proc.strip(), value=int(v or 100) / 100.0)
            elif cmd == "mic":
                m = arg.lower() in ("off", "выкл", "mute", "0"); self.b.set_mute(m, True); self._set_state(mic_muted=m)
            elif cmd == "links":
                for i, u in enumerate(normalize_urls(arg.split())[0]):
                    if i: time.sleep(0.15)
                    self.b.open_url(u, "default")

ACTIONS["open_links"] = ("Открыть ссылки (до 10)", [("urls", "Ссылки", "urls", ["https://spb-4.ru"], None),
    ("delay", "Пауза между ссылками, мс", "int", 150, None),
    ("browser", "Браузер", "choice", "default", ["default", "chrome", "edge", "firefox", "yandex"])], "Запуск")
ACTIONS["scene"] = ("Сцена (набор шагов)", [("steps", "Шаги по порядку", "steps",
    [{"do": "set_volume", "arg": "40"}, {"do": "mic", "arg": "on"}, {"do": "open", "arg": "Telegram.exe"},
     {"do": "wait", "arg": "800"}, {"do": "links", "arg": "spb-4.ru vlaslovo.ru"}], None)], "Сцены")
ACTIONS["voice"] = ("Голос в текст (держать пэд)", [("engine", "Распознавание", "choice", "windows", ["windows", "vosk"])], "Голос")
ACTIONS["macros_off"] = ("Выключить макросы (отдать порт FL Studio)", [], "Профили")
ACTIONS["voice_pitch"] = ("Питч голоса (полоса Pitch)", [("range", "Диапазон, ± полутонов", "int", 12, None)], "Голос")
