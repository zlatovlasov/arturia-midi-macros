"""Офлайн «голос в текст» через Vosk (русская малая модель ~45 МБ, скачивается при первом использовании)."""
import os, threading, queue, json, zipfile, urllib.request
from config import config_dir

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
MODEL_DIR = "vosk-model-small-ru-0.22"
RATE = 16000


def model_path():
    return os.path.join(config_dir(), MODEL_DIR)


def download_model(progress=lambda pct: None):
    dst = model_path()
    if os.path.isdir(dst):
        return dst
    zp = dst + ".zip"
    def hook(blocks, bs, total):
        if total > 0: progress(min(100, int(blocks * bs * 100 / total)))
    urllib.request.urlretrieve(MODEL_URL, zp, hook)
    with zipfile.ZipFile(zp) as z:
        z.extractall(config_dir())
    os.remove(zp)
    return dst


class VoiceEngine:
    def __init__(self, notify, paste):
        self.notify, self.paste = notify, paste
        self.model = None; self.stream = None; self.q = queue.Queue(); self.loading = False

    def _ensure_model(self):
        if self.model: return True
        if self.loading: return False
        self.loading = True
        def load():
            try:
                last = [-1]
                def prog(p):
                    if p // 10 != last[0]: last[0] = p // 10; self.notify(f"Скачиваю русскую модель распознавания: {p}%")
                path = download_model(prog)
                from vosk import Model, SetLogLevel
                SetLogLevel(-1); self.model = Model(path)
                self.notify("Голосовой ввод готов: держите пэд и говорите")
            except Exception as e:
                self.notify(f"Голосовой ввод: {e}")
            finally:
                self.loading = False
        threading.Thread(target=load, daemon=True).start()
        return False

    def start(self):
        if not self._ensure_model(): return
        import sounddevice as sd
        self.q = queue.Queue()
        self.stream = sd.RawInputStream(samplerate=RATE, blocksize=4000, dtype="int16", channels=1,
                                        callback=lambda data, n, t, st: self.q.put(bytes(data)))
        self.stream.start(); self.notify("Слушаю…")

    def stop_and_paste(self):
        if not self.stream: return
        self.stream.stop(); self.stream.close(); self.stream = None
        from vosk import KaldiRecognizer
        rec = KaldiRecognizer(self.model, RATE)
        while not self.q.empty():
            rec.AcceptWaveform(self.q.get())
        text = json.loads(rec.FinalResult()).get("text", "").strip()
        if text:
            self.paste(text[0].upper() + text[1:] + " ")
            self.notify(f"Распознано: {text}")
        else:
            self.notify("Ничего не расслышал")
