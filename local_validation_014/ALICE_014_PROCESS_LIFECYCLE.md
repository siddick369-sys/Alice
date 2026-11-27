# 🛡️ ALICE-014 — PROCESS LIFECYCLE & CLEAN SHUTDOWN REPORT
**Mission :** `ALICE-LOCAL-RUNTIME-REMEDIATION-014`  
**Constat traité :** `F013-03` (Arrêt non confirmé et codes de sortie 1 lors de la vérification des ports)  
**Résultat :** RÉSOLU — ARRÊT PROPRE, LIBÉRATION DES PORTS & IDEMPOTENCE VALIDÉE  
**Fichiers créés / modifiés :**
- [stop_alice.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/stop_alice.py)
- [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py)
- [local_validation_014/test_lifecycle_014.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/local_validation_014/test_lifecycle_014.py)

---

## 1. Cause Racine du Constat F013-03

L'investigation technique a identifié deux causes distinctes :
1. **Comportement de `Get-NetTCPConnection` dans PowerShell** :
   Dans la mission 013, la commande de vérification utilisait `Get-NetTCPConnection -LocalPort 8080 -ErrorAction Stop`. Lorsque le port est **parfaitement libre**, la commande lève une exception PowerShell (`No matching MSFT_NetTCPConnection objects found`) et termine le script avec le code de sortie 1.
2. **Absence d'un gestionnaire centralisé d'arrêt dans `main2.py`** :
   Les instances de `DualStackHTTPServer` et de `websockets.serve` n'étaient pas conservées dans des variables globales fermables proprement.
3. **Erreur d'encodage `netstat -ano` sous Windows Français** :
   L'appel à `subprocess.check_output(["netstat", "-ano"], text=True)` échouait avec `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x90` en raison de la présence de caractères accentués (ex. `ÉCOUTE`).

---

## 2. Remédiation Implémentée

### 2.1 Gestionnaire d'arrêt centralisé dans `main2.py`
Ajout de la fonction `stop_alice_runtime()` :
- Clôture de l'ensemble des sockets WebSocket connectées avec le code normal 1000 (`Server shutting down`).
- Appel de `HTTP_SERVER.shutdown()` et `HTTP_SERVER.server_close()`.
- Appel de `WS_SERVER_OBJ.close()`.
- Arrêt du service `jarvis_vision.stop()`.
- Terminaison de l'arbre de processus de Vite via `taskkill /F /T /PID`.
- Enregistrement des signaux système `SIGINT` et `SIGTERM`.

### 2.2 Utilitaire d'Arrêt Dédié (`stop_alice.py`)
- Décode la sortie de `netstat` en essayant `cp1252`, `cp850` et `latin-1`.
- Identifie avec précision les PIDs écoutant sur 8080, 8765 et 5173.
- Termine les processus enfants et parents.
- Vérifie la libération effective des ports en IPv4 (`127.0.0.1`) et en IPv6 (`::1`).
- Retourne **code de sortie 0** si tous les ports sont libres.
- Est strictement **idempotent** (un appel sur des ports déjà libres réussit immédiatement avec le code 0).

---

## 3. Preuve d'Exécution du Test de Cycle de Vie

Exécution réelle via `local_validation_014/test_lifecycle_014.py` :
```
[STEP 1] Démarrage d'ALICE (main2.py)...
  Attente T+10s -> Port 8080: UP, Port 8765: UP
[SUCCESS] ALICE est démarré et écoute sur ses ports locaux.

[STEP 2] Arrêt ordonné via stop_alice.py...
[STOP ALICE] PIDs détectés sur les ports ALICE : {16856, 28456}
[STOP ALICE] Terminaison du processus 16856...
[STOP ALICE] Terminaison du processus 28456...
  Port  8080 : FREE (OK)
  Port  8765 : FREE (OK)
  Port  5173 : FREE (OK)
  Code de sortie de stop_alice : 0

[STEP 3] Deuxième arrêt consécutif (test d'idempotence)...
[STOP ALICE] Aucun port ALICE en écoute (8080, 8765, 5173 déjà libres).
  Code de sortie du 2e arrêt : 0

[SUCCESS GLOBAL] Le cycle de vie d'ALICE est 100% validé !
```
Code de retour final : `0`.
