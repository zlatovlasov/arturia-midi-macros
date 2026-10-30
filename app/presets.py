"""Готовый профиль для Arturia MiniLab 3 по заводской MIDI-карте (руководство v1.0.5):
 ручки 1-8: CC 74,71,76,77,93,18,19,16 (кан. 1); фейдеры 1-4: CC 82,83,85,17 (кан. 1);
 пэды банк A: ноты 36-43, банк B: 44-51 (кан. 10); клавиши 48-72 (кан. 1);
 полоса Mod: CC 1; полоса Pitch: pitch bend; главный энкодер: CC 28 (относительный, 64 = центр);
 нажатие главного энкодера — CC 118 (не подтверждено, переназначьте через «Назначить»)."""
import uuid

def _m(name, ttype, ch, num, action, params=None, **kw):
    d = {"id": uuid.uuid4().hex[:8], "name": name,
         "trigger": {"type": ttype, "channel": ch, "number": num},
         "action": {"type": action, "params": params or {}}}
    d.update(kw)
    return d

PAD_CH = 9   # канал 10
CH1 = 0
ANY = None   # ручки/фейдеры/энкодер/полосы: любой канал (у разных прошивок/программ MiniLab свой канал)
KNOBS = [74, 71, 76, 77, 93, 18, 19, 16]
FADERS = [82, 83, 85, 17]

def minilab3_profile():
    P = []
    # фейдеры
    P.append(_m("Фейдер 1", "cc", ANY, 82, "master_volume", {"step": 5}, mode="absolute"))
    P.append(_m("Фейдер 2", "cc", ANY, 83, "mic_volume", {"step": 5}, mode="absolute"))
    P.append(_m("Фейдер 3", "cc", ANY, 85, "app_volume", {"process": "chrome.exe", "step": 5}, mode="absolute"))
    P.append(_m("Фейдер 4", "cc", ANY, 17, "app_volume", {"process": "Telegram.exe", "step": 5}, mode="absolute"))
    # ручки
    P.append(_m("Ручка 1", "cc", ANY, 74, "brightness", {"step": 10}, mode="absolute"))
    P.append(_m("Ручка 2", "cc", ANY, 71, "app_volume", {"process": "Spotify.exe", "step": 5}, mode="absolute"))
    P.append(_m("Ручка 3", "cc", ANY, 76, "scroll", {"lines": 3}, mode="abs_to_rel"))
    P.append(_m("Ручка 4", "cc", ANY, 77, "rel_hotkeys", {"up": "ctrl+=", "down": "ctrl+-"}, mode="abs_to_rel"))
    P.append(_m("Ручка 5", "cc", ANY, 93, "rel_hotkeys", {"up": "ctrl+tab", "down": "ctrl+shift+tab"}, mode="abs_to_rel"))
    P.append(_m("Ручка 6", "cc", ANY, 18, "none", {}, mode="absolute"))
    P.append(_m("Ручка 7", "cc", ANY, 19, "none", {}, mode="absolute"))
    P.append(_m("Ручка 8", "cc", ANY, 16, "none", {}, mode="absolute"))
    # главный энкодер
    P.append(_m("Главный энкодер", "cc", ANY, 28, "master_volume", {"step": 2}, mode="relative_offset64"))
    P.append(_m("Главный энкодер: нажатие", "cc", ANY, 118, "master_mute", {}, mode="button", button_mode="press"))
    # полоса Mod — громкость Discord, Pitch — питч голоса (включается в настройках)
    P.append(_m("Полоса Mod", "cc", ANY, 1, "app_volume", {"process": "Discord.exe", "step": 5}, mode="absolute"))
    P.append(_m("Полоса Pitch: питч голоса", "pitch", ANY, 0, "voice_pitch", {"range": 12}, mode="absolute"))
    # пэды, банк A
    P.append(_m("Пэд A1", "note", PAD_CH, 36, "mic_mute", {"mode": "toggle"}, mode="press"))
    P.append(_m("Пэд A2", "note", PAD_CH, 37, "media", {"cmd": "play_pause"}, mode="press"))
    P.append(_m("Пэд A3", "note", PAD_CH, 38, "media", {"cmd": "prev"}, mode="press"))
    P.append(_m("Пэд A4", "note", PAD_CH, 39, "media", {"cmd": "next"}, mode="press"))
    P.append(_m("Пэд A5", "note", PAD_CH, 40, "mute_all", {}, mode="press"))
    P.append(_m("Пэд A6", "note", PAD_CH, 41, "open", {"target": "https://ya.ru", "args": ""}, mode="press"))
    P.append(_m("Пэд A7", "note", PAD_CH, 42, "open", {"target": "explorer.exe", "args": ""}, mode="press"))
    P.append(_m("Пэд A8 (коротко)", "note", PAD_CH, 43, "screenshot", {"mode": "snip"}, mode="tap", long_ms=600))
    P.append(_m("Пэд A8 (долго)", "note", PAD_CH, 43, "lock", {}, mode="long", long_ms=600))
    # пэды, банк B
    P.append(_m("Пэд B1", "note", PAD_CH, 44, "audio_output", {"device": ""}, mode="press"))
    P.append(_m("Пэд B2", "note", PAD_CH, 45, "desktop", {"cmd": "prev"}, mode="press"))
    P.append(_m("Пэд B3", "note", PAD_CH, 46, "desktop", {"cmd": "next"}, mode="press"))
    P.append(_m("Пэд B4", "note", PAD_CH, 47, "window", {"cmd": "show_desktop"}, mode="press"))
    P.append(_m("Пэд B5", "note", PAD_CH, 48, "window", {"cmd": "minimize"}, mode="press"))
    P.append(_m("Пэд B6", "note", PAD_CH, 49, "hotkey", {"keys": "ctrl+shift+esc"}, mode="press"))
    P.append(_m("Пэд B7", "note", PAD_CH, 50, "open", {"target": "calc.exe", "args": ""}, mode="press"))
    P.append(_m("Пэд B8 (коротко)", "note", PAD_CH, 51, "profile", {"name": ""}, mode="tap", long_ms=1500))
    P.append(_m("Пэд B8 (долго): выключить макросы", "note", PAD_CH, 51, "macros_off", {}, mode="long", long_ms=1500))
    return P

def is_minilab3(port_name):
    return "minilab3" in port_name.lower().replace(" ", "").replace("_", "")

def maybe_minilab_port(port_name):
    """MiniLab 3 напрямую или через MIDI-вход/USB-хаб звуковой карты Arturia (MiniFuse, AudioFuse)."""
    n = port_name.lower()
    return is_minilab3(port_name) or "arturia" in n or "minifuse" in n or "audiofuse" in n
