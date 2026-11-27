"""
Utilitaire d'arrêt propre et de vérification des ports d'ALICE (Mission 014 / F013-03).
Garantit l'arrêt propre des processus et retourne le code de sortie 0.
"""
import sys
import time
import subprocess
import socket

PORTS = [8080, 8765, 5173]

def check_port_free(port: int) -> bool:
    # Vérification IPv4
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return False
    except Exception:
        pass
    # Vérification IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s6:
            s6.settimeout(0.3)
            if s6.connect_ex(("::1", port)) == 0:
                return False
    except Exception:
        pass
    return True

def get_pids_on_ports(ports):
    pids = set()
    try:
        raw_out = subprocess.check_output(["netstat", "-ano"])
        out = ""
        for enc in ("cp1252", "cp850", "utf-8"):
            try:
                out = raw_out.decode(enc)
                break
            except Exception:
                pass
        if not out:
            out = raw_out.decode("latin-1", errors="replace")

        for line in out.splitlines():
            line = line.strip()
            for p in ports:
                pattern = f":{p} "
                if pattern in line and any(k in line.upper() for k in ["LISTENING", "ÉCOUTE", "ECOUTE"]):
                    parts = line.split()
                    try:
                        pid = int(parts[-1])
                        if pid > 0:
                            pids.add(pid)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"[STOP ALICE] Erreur netstat : {e}")
    return pids

def stop_alice():
    print("=" * 60)
    print("[STOP ALICE] Arrêt ordonné des composants ALICE...")
    print("=" * 60)

    pids = get_pids_on_ports(PORTS)
    if not pids:
        print("[STOP ALICE] Aucun port ALICE en écoute (8080, 8765, 5173 déjà libres).")
    else:
        print(f"[STOP ALICE] PIDs détectés sur les ports ALICE : {pids}")
        for pid in pids:
            try:
                print(f"[STOP ALICE] Terminaison du processus {pid}...")
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"[STOP ALICE] Erreur terminaison PID {pid} : {e}")

    # Vérification après terminaison
    time.sleep(1.0)
    all_free = True
    print("\n[STOP ALICE] Vérification de l'état des ports :")
    for p in PORTS:
        free = check_port_free(p)
        status = "FREE (OK)" if free else "OCCUPIED (FAIL)"
        print(f"  Port {p:5d} : {status}")
        if not free:
            all_free = False

    if all_free:
        print("\n[STOP ALICE] Succès : Tous les ports ALICE sont libres.")
        return 0
    else:
        print("\n[STOP ALICE] Attention : Certains ports sont encore occupés.")
        return 1

if __name__ == "__main__":
    code = stop_alice()
    sys.exit(code)
