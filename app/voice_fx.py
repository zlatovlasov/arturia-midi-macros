"""Питч голоса в реальном времени: микрофон -> сдвиг высоты -> виртуальный микрофон VB-Cable («CABLE Input»).
Лёгкий алгоритм без librosa: две «читающие головки» по линии задержки с плавным перекрёстным затуханием
(классический delay-line pitch shifter). Задержка ~30 мс, CPU — копейки."""
import math, threading
import numpy as np

VB_URL = "https://vb-audio.com/Cable/"


class PitchShifter:
    def __init__(self, sr=48000, window_ms=30.0):
        self.sr = sr; self.W = max(64, int(sr * window_ms / 1000))
        self.hist = np.zeros(self.W + 4, dtype=np.float32)   # хвост прошлых сэмплов
        self.phase = 0.0; self.ratio = 1.0

    def set_semitones(self, st):
        self.ratio = 2.0 ** (float(st) / 12.0)

    def process(self, x):
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        n = len(x)
        if n == 0: return x
        if abs(self.ratio - 1.0) < 1e-4:
            self.hist = np.concatenate([self.hist, x])[-len(self.hist):]
            return x.copy()
        buf = np.concatenate([self.hist, x]); H = len(self.hist)
        step = (1.0 - self.ratio) / self.W
        ph = (self.phase + step * np.arange(1, n + 1)) % 1.0
        self.phase = float(ph[-1])
        pos = H + np.arange(n, dtype=np.float64)
        out = np.zeros(n, dtype=np.float32)
        for p in (ph, (ph + 0.5) % 1.0):
            r = pos - (p * self.W + 1)                     # читающая головка (дробный индекс)
            i0 = np.floor(r).astype(np.int64); fr = (r - i0).astype(np.float32)
            s = buf[i0] * (1 - fr) + buf[i0 + 1] * fr
            out += s * (0.5 - 0.5 * np.cos(2 * np.pi * p)).astype(np.float32)   # окна в сумме = 1
        self.hist = buf[-H:]
        return out


def strip_to_semitones(v, rng=12, dead=0.04):
    """v 0..1 (центр 0.5 = норма) -> полутоны, с мёртвой зоной в центре."""
    d = (float(v) - 0.5) * 2
    if abs(d) < dead: return 0.0
    d = (abs(d) - dead) / (1 - dead) * (1 if d > 0 else -1)
    return round(d * rng, 2)


def find_output(sd, want="CABLE Input"):
    """Индекс устройства вывода VB-Cable (или None). Предпочитаем WASAPI/MME с минимальной задержкой."""
    try:
        devs = sd.query_devices()
    except Exception:
        return None
    hits = [i for i, d in enumerate(devs) if d.get("max_output_channels", 0) > 0 and want.lower() in d["name"].lower()]
    return hits[0] if hits else None


class VoicePitch:
    """Поток микрофон -> CABLE Input. start()/stop(), set(v)."""
    def __init__(self, notify=None, output="CABLE Input"):
        self.notify = notify or (lambda t: None); self.output = output
        self.stream = None; self.fx = None; self.lock = threading.Lock(); self.semis = 0.0

    def available(self):
        import sounddevice as sd
        return find_output(sd, self.output) is not None

    def start(self):
        if self.stream: return True
        import sounddevice as sd
        out = find_output(sd, self.output)
        if out is None:
            raise LookupError("VB-Cable не найден")
        sr = int(sd.query_devices(out)["default_samplerate"] or 48000)
        self.fx = PitchShifter(sr); self.fx.set_semitones(self.semis)

        def cb(indata, outdata, frames, t, status):
            with self.lock:
                y = self.fx.process(indata[:, 0])
            outdata[:] = np.repeat(y[:, None], outdata.shape[1], axis=1)

        self.stream = sd.Stream(device=(None, out), samplerate=sr, blocksize=256, latency="low",
                                channels=(1, min(2, sd.query_devices(out)["max_output_channels"])), dtype="float32", callback=cb)
        self.stream.start(); self.notify("Питч голоса: микрофон идёт в «CABLE Output» — выберите его микрофоном в Discord/OBS")
        return True

    def set(self, v, rng=12):
        self.semis = strip_to_semitones(v, rng)
        if self.fx:
            with self.lock: self.fx.set_semitones(self.semis)
        return self.semis

    def stop(self):
        if self.stream:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
        self.stream = None
