import re
import time
import subprocess
import sys
import os
import socket

log_path = os.path.abspath("local_validation_012/logs/alice_server.log")
pin = None
for _ in range(15):
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = re.findall(r"Nouveau code d'appairage[^:]*:\s*(\d{6})", content)
        if matches:
            pin = matches[-1]
            break
    time.sleep(1)

if not pin:
    print("ERROR: Could not find pairing PIN in server log!")
    sys.exit(1)

print(f"Found active PIN in server log: {pin}")
for _ in range(15):
    try:
        with socket.create_connection(("127.0.0.1", 8080), timeout=1):
            break
    except OSError:
        time.sleep(0.5)

py_exe = os.path.abspath("Jarvis Final - SITE/venv/Scripts/python.exe")
script = os.path.abspath("local_validation_012/run_e2e_scenarios.py")
res = subprocess.run([py_exe, script, pin], capture_output=False)
sys.exit(res.returncode)
