import re
import time
import subprocess
import sys
import os
import socket

log_path = os.path.abspath("local_validation_013/logs/alice_server.log")
pin = None
for _ in range(15):
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = re.findall(r"code d.appairage[^:]*:\s*(\d{6})", content)
        if matches:
            pin = matches[-1]
            break
    time.sleep(1)

if not pin:
    print("ERROR: Could not find pairing PIN in server log!")
    sys.exit(1)

print(f"Found active PIN in server log: {pin}")
# Wait for port 8080 and 8765
for port in [8080, 8765]:
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)

target_script = sys.argv[1] if len(sys.argv) > 1 else "local_validation_013/test_ws_lifecycle.py"
py_exe = os.path.abspath("Jarvis Final - SITE/venv/Scripts/python.exe")
script_abs = os.path.abspath(target_script)

res = subprocess.run([py_exe, script_abs, pin], capture_output=False)
sys.exit(res.returncode)
