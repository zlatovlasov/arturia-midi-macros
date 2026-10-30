"""Главный выключатель макросов: ВКЛ — порты открыты, ВЫКЛ — все MIDI-порты закрыты (свободны для FL Studio).
Чистая логика, без Qt и Windows: тестируется на любой ОС."""
import subprocess, sys

FL_PROCS = ("fl64.exe", "fl.exe", "fl studio.exe")

BUSY = "порт занят (наверно, FL Studio) — закройте FL или выключите там этот MIDI-вход, потом включите макросы снова"


class MacroController:
    def __init__(self, hub, cfg, list_inputs, on_change=None):
        self.hub, self.cfg, self.list_inputs = hub, cfg, list_inputs
        self.on_change = on_change or (lambda st: None)
        self.enabled = not cfg.get("start_off", False)
        self.fl_running = False
        self.state = {"mode": "off", "open": [], "errors": []}

    def should_open(self):
        return self.enabled and not (self.cfg.get("auto_off_fl", False) and self.fl_running)

    def apply(self):
        if not self.should_open():
            self.hub.close()
            mode = "fl" if self.enabled else "off"
            self.state = {"mode": mode, "open": [], "errors": []}
        else:
            avail = self.list_inputs()
            want = [n for n in self.cfg.get("inputs", []) if n in avail]
            raw = self.hub.open(want)
            failed = {n for n in want if any(str(e).startswith(n + ":") for e in raw)}
            errors = [f"«{n}»: {BUSY}" for n in want if n in failed]
            opened = [n for n in want if n not in failed]
            if not want:
                errors.append("MIDI-вход не выбран или клавиатура не подключена")
            self.state = {"mode": "on" if opened else "error", "open": opened, "errors": errors}
        self.on_change(self.state)
        return self.state

    def set_enabled(self, on):
        self.enabled = bool(on)
        return self.apply()

    def toggle(self):
        return self.set_enabled(not self.enabled)

    def set_fl_running(self, running):
        running = bool(running)
        if running == self.fl_running:
            return None
        self.fl_running = running
        return self.apply() if self.cfg.get("auto_off_fl", False) else None


def fl_is_running(proc_names=None):
    """Есть ли запущенный FL Studio. Работает через tasklist (без лишних зависимостей)."""
    if proc_names is None:
        if sys.platform != "win32":
            return False
        try:
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                 creationflags=0x08000000, timeout=5).stdout
        except Exception:
            return False
        proc_names = [line.split(",")[0].strip('"') for line in out.splitlines() if line]
    return any(p.lower() in FL_PROCS for p in proc_names)
