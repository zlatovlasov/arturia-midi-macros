import json, os, sys, uuid, copy
from presets import minilab3_profile

APP = "ArturiaMidiMacros"

def config_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, APP)
    os.makedirs(d, exist_ok=True)
    return d

def config_path():
    return os.path.join(config_dir(), "config.json")

def default_config():
    return {"version": 2, "inputs": [], "autostart": True, "start_minimized": True,
            "active_profile": "MiniLab 3", "global": [],
            "profiles": {"MiniLab 3": minilab3_profile(), "Пустой": []},
            "asked_minilab": False, "hotkey": "ctrl+alt+m", "auto_off_fl": False, "start_off": False, "theme": "dark",
            "calib": {}, "voice_pitch_enabled": False, "voice_pitch_output": "CABLE Input", "all_minilab_ports": True}

DEVICE_CCS = {74, 71, 76, 77, 93, 18, 19, 16, 82, 83, 85, 17, 28, 118, 1}

def migrate(cfg):
    """v1 -> v2: ручки/фейдеры/энкодер/полосы MiniLab ловим на любом канале; Pitch -> питч голоса."""
    if cfg.get("version", 1) >= 2:
        return cfg
    for lst in list(cfg.get("profiles", {}).values()) + [cfg.get("global", [])]:
        for m in lst:
            t = m.get("trigger", {})
            if (t.get("type") == "cc" and t.get("channel") == 0 and t.get("number") in DEVICE_CCS) or (t.get("type") == "pitch" and t.get("channel") == 0):
                t["channel"] = None
    ml = cfg.get("profiles", {}).get("MiniLab 3")
    if ml is not None and not any(m.get("trigger", {}).get("type") == "pitch" for m in ml):
        ml.append({"id": new_id(), "name": "Полоса Pitch: питч голоса", "trigger": {"type": "pitch", "channel": None, "number": 0},
                   "mode": "absolute", "action": {"type": "voice_pitch", "params": {"range": 12}}})
    cfg["version"] = 2
    return cfg

def new_id():
    return uuid.uuid4().hex[:8]

def fix(cfg):
    d = default_config()
    cfg.setdefault("version", 1)
    for k, v in d.items():
        cfg.setdefault(k, v)
    migrate(cfg)
    if not cfg["profiles"]:
        cfg["profiles"] = {"Пустой": []}
    if cfg["active_profile"] not in cfg["profiles"]:
        cfg["active_profile"] = next(iter(cfg["profiles"]))
    for lst in list(cfg["profiles"].values()) + [cfg["global"]]:
        for m in lst:
            m.setdefault("id", new_id()); m.setdefault("action", {"type": "none", "params": {}})
    return cfg

def load(path=None):
    path = path or config_path()
    if not os.path.exists(path):
        cfg = default_config(); save(cfg, path); return cfg
    with open(path, encoding="utf-8") as f:
        return fix(json.load(f))

def save(cfg, path=None):
    path = path or config_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def export_to(cfg, path):
    save(cfg, path)

def import_from(path):
    with open(path, encoding="utf-8") as f:
        return fix(json.load(f))

# --- автозапуск (HKCU\...\Run)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

def exe_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    return f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(sys.argv[0])}" --tray'

def set_autostart(on):
    if sys.platform != "win32":
        return False
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, exe_command())
        else:
            try: winreg.DeleteValue(k, APP)
            except FileNotFoundError: pass
    return True
