import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def single_instance():
    if sys.platform != "win32": return True
    import ctypes
    ctypes.windll.kernel32.CreateMutexW(None, False, "ArturiaMidiMacrosMutex")
    return ctypes.windll.kernel32.GetLastError() != 183

if __name__ == "__main__":
    if not single_instance(): sys.exit(0)
    from gui import run
    sys.exit(run(sys.argv))
