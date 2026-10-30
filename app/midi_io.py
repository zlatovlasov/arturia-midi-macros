import queue, threading, time

def list_inputs():
    try:
        import mido
        return list(dict.fromkeys(mido.get_input_names()))
    except Exception:
        return []

class MidiHub:
    """Открывает выбранные входы; все сообщения кладёт в очередь и отдаёт в listeners (для монитора/«Назначить»)."""
    def __init__(self):
        self.ports = {}
        self.q = queue.Queue()
        self.listeners = []

    def _cb(self, name):
        def f(msg):
            self.q.put(msg)
            for l in list(self.listeners):
                try: l(name, msg)
                except Exception: pass
        return f

    def open(self, names):
        import mido
        errors = []
        for n in list(self.ports):
            if n not in names:
                self.ports.pop(n).close()
        for n in names:
            if n in self.ports: continue
            try:
                self.ports[n] = mido.open_input(n, callback=self._cb(n))
            except Exception as e:
                errors.append(f"{n}: {e}")
        return errors

    def close(self):
        for p in self.ports.values():
            try: p.close()
            except Exception: pass
        self.ports.clear()

class Worker(threading.Thread):
    """Поток: берёт MIDI из очереди -> engine.process, и тикает долгие нажатия.
    Подряд идущие абсолютные CC одного контрола схлопываются (берётся последнее значение)."""
    def __init__(self, hub, engine):
        super().__init__(daemon=True)
        self.hub, self.engine, self.running = hub, engine, True

    def run(self):
        while self.running:
            try:
                msg = self.hub.q.get(timeout=0.02)
                batch = [msg]
                while True:
                    try: batch.append(self.hub.q.get_nowait())
                    except queue.Empty: break
                last = {}
                for i, m in enumerate(batch):
                    if m.type in ("control_change", "pitchwheel"):
                        last[(m.type, m.channel, getattr(m, "control", -1))] = i
                for i, m in enumerate(batch):
                    k = (m.type, getattr(m, "channel", 0), getattr(m, "control", -1))
                    if k in last and last[k] != i and self._is_abs(m):
                        continue
                    self.engine.process(m)
            except queue.Empty:
                pass
            except Exception as e:
                print("worker:", e)
            self.engine.tick()

    def _is_abs(self, m):
        if m.type == "pitchwheel": return True
        for mp in self.engine.active_mappings():
            t = mp["trigger"]
            if t["type"] == "cc" and t.get("number") == m.control and mp.get("mode", "absolute") == "absolute":
                return True
        return False
