# 🛡️ ALICE — JOURNAL DES MODIFICATIONS TECHNIQUES (CHANGELOG) P0-003
## TRAÇABILITÉ EXHAUSTIVE DES CORRECTIONS DE CODE APPORTÉES POUR LA CLÔTURE DES CONDITIONS C-01 À C-04

- **Projet :** J.A.R.V.I.S / ALICE — SITE-V2
- **Mission :** `ALICE-P0-REMEDIATION-003`
- **Branche :** `main`
- **Date :** 23 novembre 2026
- **Gouvernance :** Aucun commit Git, aucun push, aucun déploiement effectué.

---

## 1. VUE D'ENSEMBLE DES FICHIERS MODIFIÉS

| Fichier Modifié | Chemin Relatif | Condition Adressée | Nature de la Modification |
| :--- | :--- | :---: | :--- |
| [alice_modules.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/alice_modules.py) | `Jarvis Final - SITE/alice_modules.py` | SEC-01 | Ajout de `"open"` et `"input"` dans l'analyse statique AST des builtins interdits. |
| [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) | `Jarvis Final - SITE/main2.py` | C-01, C-02, C-03, C-04 | Réécriture de `is_origin_allowed` ; classe `CrossProcessMemoryLock` ; architecture TLS/WSS et fail-closed ; vérification d'état physique HA en 2 temps. |
| [app.js](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js) | `Jarvis Final - SITE/mobile/app.js` | C-01 | Détection automatique du protocole TLS (`wss://` si la page est chargée en `https://`). |
| [jarvis_agent.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/jarvis_agent.py) | `Jarvis Final - SITE/jarvis_agent.py` | C-03 | Suppression des écritures directes JSON non verrouillées et délégation vers `main2.py`. |

---

## 2. MODIFICATIONS DÉTAILLÉES PAR FICHIER

### 2.1 `Jarvis Final - SITE/alice_modules.py`

#### Contexte et Rationale de Sécurité
L'audit d'acceptation 003 a mis en lumière que l'inspecteur AST n'interdisait pas formellement l'utilisation de `open()` et `input()`. Bien que l'exécution sur l'hôte fût désactivée avec `execution_status: "DISABLED_FOR_SECURITY"`, le statut de sécurité `safety_status` retourné était `SECURE_STATIC_VERIFIED` pour `open('secrets.txt', 'r')`, ce qui constituait une anomalie de classification.

#### Extrait de Diff (Ligne 850) :
```python
<<<< ORIGINEL
        DANGEROUS_BUILTINS = {
            "eval", "exec", "compile", "__import__", "globals", "locals",
            "vars", "breakpoint", "exit", "quit"
        }
==== NOUVEAU
        DANGEROUS_BUILTINS = {
            "eval", "exec", "compile", "__import__", "globals", "locals",
            "vars", "breakpoint", "exit", "quit", "open", "input"
        }
>>>>
```

---

### 2.2 `Jarvis Final - SITE/mobile/app.js`

#### Contexte et Rationale de Sécurité
En alignement avec la condition C-01, le client Web mobile devait négocier une connexion WebSocket sécurisée (`wss://`) dès lors que l'application était servie sous HTTPS, afin d'éviter le blocage par le navigateur pour contenu mixte (*Mixed Content*).

#### Extrait de Diff (Lignes 11-15) :
```javascript
<<<< ORIGINEL
const WS_URL = `ws://${window.location.hostname}:8765`;
==== NOUVEAU
const isHttps = window.location.protocol === "https:";
const wsProtocol = isHttps ? "wss:" : "ws:";
const WS_URL = `${wsProtocol}//${window.location.hostname}:8765`;
>>>>
```

---

### 2.3 `Jarvis Final - SITE/jarvis_agent.py`

#### Contexte et Rationale de Sécurité
`jarvis_agent.py` disposait de méthodes autonomes `_load_memory`, `_save_memory`, `remember` et `forget` qui ouvraient directement `jarvis_memoire.json` sans acquérir de verrou, risquant d'écraser les écritures du processus principal ou de corrompre le fichier. Une coquille de syntaxe sur une chaîne multiligne (ligne 102) empêchait également l'import direct.

#### Modifications apportées :
1. **En-tête de dépréciation et imports :**
   ```python
   # Migration P0-003 : Délégation vers la couche mémoire thread-safe et cross-process de main2.py
   import main2
   ```
2. **Correction de syntaxe ligne 102 :**
   Remplacement de la chaîne tronquée avec saut de ligne hors guillemets par une chaîne valide.
3. **Refactorisation des méthodes mémoire :**
   ```python
   def _load_memory(self):
       return main2.charger_memoire()

   def _save_memory(self, memory):
       return main2.sauvegarder_memoire(memory)

   def remember(self, key, value):
       return main2.ajouter_memoire(key, value)

   def forget(self, key):
       return main2.supprimer_memoire(key)
   ```

---

### 2.4 `Jarvis Final - SITE/main2.py`

#### 2.4.1 Imports et Constantes
- Ajout de `import sys`, `import ssl`, `from urllib.parse import urlsplit`, `from typing import Tuple`.
- Définition des constantes de transport :
  - `ALICE_ENV = os.environ.get("ALICE_ENV", "development").strip().lower()`
  - `ALICE_SSL_CERT = os.environ.get("ALICE_SSL_CERT", "").strip()`
  - `ALICE_SSL_KEY = os.environ.get("ALICE_SSL_KEY", "").strip()`
  - `ALICE_TRUSTED_PROXIES = set(...)`
- Définition des constantes Home Assistant :
  - `HA_REQUEST_ACCEPTED = "REQUEST_ACCEPTED"`
  - `HA_STATE_VERIFIED = "STATE_VERIFIED"`
  - `HA_STATE_UNKNOWN = "STATE_UNKNOWN"`
  - `HA_TIMEOUT = "TIMEOUT"`
  - `HA_FAILED = "FAILED"`

#### 2.4.2 Implémentation de `CrossProcessMemoryLock`
```python
class CrossProcessMemoryLock:
    """Verrou hybride thread-safe et cross-process via l'OS."""
    def __init__(self, lock_file: Optional[str] = None, timeout: float = 5.0):
        self.lock_file_path = lock_file or MEMOIRE_LOCK_FILE
        self.timeout = timeout
        self._thread_lock = threading.RLock()
        self._file_handle = None
        self._lock_count = 0
```
- Implémentation du support Windows via `msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)` et POSIX via `fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)`.
- Enveloppement systématique des primitives `charger_memoire`, `sauvegarder_memoire`, `ajouter_memoire`, `supprimer_memoire` dans un bloc `with CROSS_PROCESS_MEMORY_LOCK:`.

#### 2.4.3 Réécriture complète de `is_origin_allowed` (Condition C-02)
- Remplacement des regex permissives par `urllib.parse.urlsplit(origin)`.
- Rejet strict si :
  - `parsed.scheme not in ("http", "https")`
  - `parsed.username or parsed.password` (userinfo)
  - `parsed.path not in ("", "/")`
  - `parsed.query or parsed.fragment`
  - `parsed.port is None or not (1 <= parsed.port <= 65535)`
  - Le port n'appartient pas à l'allowlist de l'environnement (`{8080, 8443, 8765, 5173, 3000}` en dev, `{443, 8443}` en prod).
  - L'hôte possède un point final (`localhost.`) ou ressemble à une usurpation d'IP privée dans un nom DNS (`192.168.attacker.com`).

#### 2.4.4 Architecture TLS/WSS et Reverse-Proxy (Condition C-01)
- **`get_ssl_context() -> Optional[ssl.SSLContext]` :**
  - Instancie un contexte TLS durci (rejet des protocoles obsolètes).
  - Lève une `RuntimeError` bloquante si `ALICE_ENV=production` et que les certificats sont introuvables.
- **`get_trusted_client_ip(client_address, headers) -> str` :**
  - Extrait l'IP cliente directe. N'accepte `X-Forwarded-For` que si l'IP directe provient d'un proxy répertorié dans `ALICE_TRUSTED_PROXIES`.
- **Intégration TLS dans les serveurs :**
  - `start_ws()` passe `ssl=ssl_ctx` à `websockets.serve`.
  - `start_mobile_http_server()` enveloppe le socket serveur avec `ssl_ctx.wrap_socket`.

#### 2.4.5 Vérification physique Home Assistant (Condition C-04)
- **`ha_verifier_changement_etat(entity_id: str, etat_attendu: str) -> Tuple[str, Optional[str]]` :**
  - Interroge l'état matériel réel via l'endpoint `/api/states/<entity_id>`.
  - Effectue jusqu'à 3 vérifications espacées de 0.4s.
  - Retourne le statut formel (`HA_STATE_VERIFIED`, `HA_STATE_UNKNOWN`, `HA_TIMEOUT`, `HA_FAILED`).
- **Mise à niveau de `ha_lumiere` et `ha_interrupteur` :**
  - Paramètre `verify_state=True`.
  - Retourne un dictionnaire enrichi incluant la vérification matérielle.
- **Rétroaction vocale honnête dans `traiter_reponse_ia` :**
  - Différencie explicitement l'acquittement API de l'état physique réel, prévenant toute fausse affirmation.

---
**Statut :** Toutes les modifications ont été auditées, isolées et validées par la suite de tests automatisée.
