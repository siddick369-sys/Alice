import subprocess
import sys
import os
import time

py_exe = os.path.abspath("Jarvis Final - SITE/venv/Scripts/python.exe")

suites = [
    {
        "name": "Remediation 010 Adversarial",
        "cmd": [py_exe, "-m", "unittest", "tests.security.test_p1_remediation_010_adversarial"],
        "cwd": "."
    },
    {
        "name": "P1 007 Real Sockets",
        "cmd": [py_exe, "-m", "unittest", "tests.security.test_p1_remediation_007_real_sockets"],
        "cwd": "."
    },
    {
        "name": "P1 006 Exposure",
        "cmd": [py_exe, "-m", "unittest", "tests.security.test_p1_production_exposure_006"],
        "cwd": "."
    },
    {
        "name": "Mission 007 Tests",
        "cmd": [py_exe, "tests/run_all_tests.py"],
        "cwd": "Jarvis Final - SITE"
    },
    {
        "name": "Ultimate 008 Waves",
        "cmd": [py_exe, "-m", "unittest", "discover", "-s", "tests/alice_ultimate", "-p", "test_wave*.py"],
        "cwd": "."
    },
    {
        "name": "Ultimate 008 E2E Bridge",
        "cmd": [py_exe, "-m", "unittest", "tests.alice_ultimate.integration.test_e2e_api_ws_bridge"],
        "cwd": "."
    }
]

print("============================================================")
print("RÉCONCILIATION ET RÉ-EXÉCUTION DES SUITES DE TESTS (013)")
print("============================================================")

results = []
for s in suites:
    t0 = time.time()
    res = subprocess.run(s["cmd"], cwd=s["cwd"], capture_output=True, text=True)
    dt = time.time() - t0
    output = res.stdout + res.stderr
    
    # Parse test count from unittest output (e.g. "Ran 42 tests in 1.234s")
    count = "?"
    for line in output.splitlines():
        if line.startswith("Ran ") and "test" in line:
            count = line.split()[1]
            break
            
    is_ok = (res.returncode == 0) and ("FAILED" not in output)
    print(f"[{'PASS' if is_ok else 'FAIL'}] {s['name']} : {count} tests en {dt:.2f}s (Exit {res.returncode})")
    results.append({
        "name": s["name"],
        "count": count,
        "duration": dt,
        "ok": is_ok,
        "output": output[-300:] if len(output) > 300 else output
    })

print("\nRéconciliation terminée.")
