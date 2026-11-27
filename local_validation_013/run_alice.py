import sys
import os
import time

site_dir = os.path.abspath("Jarvis Final - SITE")
sys.path.insert(0, site_dir)
os.chdir(site_dir)

log_path = os.path.abspath("../local_validation_013/logs/alice_server.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            try:
                f.write(obj)
                f.flush()
            except Exception:
                pass
    def flush(self):
        for f in self.files:
            try:
                f.flush()
            except Exception:
                pass

log_file = open(log_path, "a", encoding="utf-8", errors="replace")
sys.stdout = Tee(sys.__stdout__, log_file)
sys.stderr = Tee(sys.__stderr__, log_file)

print(f"[RUNNER-013] Starting ALICE main2 at {time.strftime('%Y-%m-%d %H:%M:%S')} (PID: {os.getpid()})")
import main2

try:
    main2.main()
except Exception as e:
    print(f"[RUNNER ERROR] main2.main() crashed: {e}")
    import traceback
    traceback.print_exc()
