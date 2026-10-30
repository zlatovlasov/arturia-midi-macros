"""Парсер макросов. Каждая строка — шаг:
  hotkey ctrl+c | key enter | text Привет | wait 300 | open notepad.exe | cmd echo hi | ps Get-Date
  media play_pause | volume +5 | mic_mute | desktop next   (# — комментарий)
  set_volume 40 | app_volume chrome.exe 30 | mic off|on | links ya.ru github.com"""

# Шаги сцены (редактор-список) -> те же (cmd, arg), что и у макроса
SCENE_STEPS = {  # ключ: (подпись, подсказка к значению)
    "open":       ("Открыть программу/файл", "C:\\Program Files\\…\\app.exe или notepad.exe"),
    "links":      ("Открыть ссылки", "через пробел: ya.ru github.com"),
    "set_volume": ("Громкость системы, %", "0–100"),
    "app_volume": ("Громкость приложения", "chrome.exe 30"),
    "mic":        ("Микрофон", "off = выключить, on = включить"),
    "hotkey":     ("Сочетание клавиш", "ctrl+shift+f13"),
    "text":       ("Напечатать текст", "Привет"),
    "media":      ("Медиа", "play_pause / next / prev"),
    "desktop":    ("Рабочий стол", "next / prev / new"),
    "ps":         ("Команда PowerShell", "Get-Date"),
    "wait":       ("Пауза, мс", "500"),
}

def scene_to_steps(items):
    out = []
    for it in items or []:
        cmd, arg = it.get("do"), str(it.get("arg", "")).strip()
        if cmd not in SCENE_STEPS:
            continue
        out.append(("wait", int(arg or 0)) if cmd == "wait" else (cmd, arg))
    return out

def parse_macro(src):
    steps = []
    for n, line in enumerate(src.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cmd, _, arg = line.partition(" ")
        cmd = cmd.lower(); arg = arg.strip()
        if cmd in ("wait", "пауза", "delay"):
            steps.append(("wait", int(arg or 100)))
        elif cmd in ("hotkey", "key", "text", "open", "cmd", "ps", "media", "volume", "mic_mute", "desktop", "window",
                     "set_volume", "app_volume", "mic", "links"):
            steps.append((cmd, arg))
        else:
            raise ValueError(f"Строка {n}: непонятная команда «{cmd}»")
    return steps
