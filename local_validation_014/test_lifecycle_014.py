"""
Test de cycle de vie complet, arrêt propre et idempotence (Mission 014 / F013-03).
"""
import os
import sys
import time
import socket
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(ROOT_DIR, "Jarvis Final - SITE")
PYTHON_EXE = os.path.join(SOURCE_DIR, "venv", "Scripts", "python.exe")

def is_port_listening(port: int) -> bool:
    # IPv4
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
    except Exception:
        pass
    # IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s6:
            s6.settimeout(0.3)
            if s6.connect_ex(("::1", port)) == 0:
                return True
    except Exception:
        pass
    return False

def run_lifecycle_test():
    print("=" * 60)
    print("[LIFECYCLE TEST 014] Démarrage du test de cycle de vie")
    print("=" * 60)

    # 1. Vérification initiale : ports libres
    for p in [8080, 8765, 5173]:
        if is_port_listening(p):
            print(f"[PRE-CHECK] Le port {p} est déjà occupé ! Nettoyage...")
            subprocess.run([PYTHON_EXE, os.path.join(SOURCE_DIR, "stop_alice.py")])
            break

    # 2. Démarrage de main2.py en sous-processus
    print("\n[STEP 1] Démarrage d'ALICE (main2.py)...")
    env = os.environ.copy()
    env["ALICE_BIND_MODE"] = "LOCALHOST"
    env["ALICE_ENV"] = "development"
    proc = subprocess.Popen([PYTHON_EXE, "main2.py"], cwd=SOURCE_DIR, env=env)

    # Attente démarrage (ports 8080 et 8765) - les imports lourds (torch, whisper, cv2) prennent ~18s
    started = False
    for i in range(40):
        time.sleep(1.0)
        p8080 = is_port_listening(8080)
        p8765 = is_port_listening(8765)
        print(f"  Attente T+{i+1}s -> Port 8080: {'UP' if p8080 else 'WAIT'}, Port 8765: {'UP' if p8765 else 'WAIT'}")
        if p8080 and p8765:
            started = True
            break

    if not started:
        print("[FAIL] ALICE n'a pas démarré sur les ports attendus.")
        proc.kill()
        return 1

    print("\n[SUCCESS] ALICE est démarré et écoute sur ses ports locaux.")

    # 3. Arrêt propre via l'utilitaire stop_alice.py
    print("\n[STEP 2] Arrêt ordonné via stop_alice.py...")
    stop_res = subprocess.run([PYTHON_EXE, os.path.join(SOURCE_DIR, "stop_alice.py")])
    print(f"  Code de sortie de stop_alice : {stop_res.returncode}")
    if stop_res.returncode != 0:
        print("[FAIL] stop_alice a retourné un code non nul.")
        return 1

    # 4. Vérification que les ports sont bien libres
    time.sleep(1.0)
    for p in [8080, 8765, 5173]:
        listening = is_port_listening(p)
        print(f"  Vérification post-arrêt Port {p:5d} : {'OCCUPIED (FAIL)' if listening else 'FREE (OK)'}")
        if listening:
            return 1

    # 5. Deuxième arrêt consécutif (test d'idempotence)
    print("\n[STEP 3] Deuxième arrêt consécutif (test d'idempotence)...")
    stop_res_2 = subprocess.run([PYTHON_EXE, os.path.join(SOURCE_DIR, "stop_alice.py")])
    print(f"  Code de sortie du 2e arrêt : {stop_res_2.returncode}")
    if stop_res_2.returncode != 0:
        print("[FAIL] Deuxième arrêt a échoué.")
        return 1

    print("\n[SUCCESS GLOBAL] Le cycle de vie d'ALICE (démarrage -> arrêt propre -> libération des ports -> idempotence) est 100% validé !")
    return 0

if __name__ == "__main__":
    code = run_lifecycle_test()
    sys.exit(code)
