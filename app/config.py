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
    return {"version": 1, "inputs": [], "autostart": True, "start_minimized": True,
            "active_profile": "MiniLab 3", "global": [],
            "profiles": {"MiniLab 3": minilab3_profile(), "Пустой": []},
            "asked_minilab": False, "hotkey": "ctrl+alt+m", "auto_off_fl": False, "start_off": False, "theme": "dark"}

def new_id():
    return uuid.uuid4().hex[:8]

def fix(cfg):
    d = default_config()
    for k, v in d.items():
        cfg.setdefault(k, v)
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
