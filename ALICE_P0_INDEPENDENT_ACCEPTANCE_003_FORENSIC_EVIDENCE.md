# 🔬 PREUVES FORENSIQUES ET EXTRAITS DE CODE
## MISSION ALICE-P0-INDEPENDENT-ACCEPTANCE-003

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date d'Établissement :** 23 Novembre 2026  
**Nature du Document :** Preuves forensiques matérielles, extraits de code source vérifiés, différentiels Git et traces d'exécution contradictoires.

---

## 1. EMPREINTES FORENSIQUES ET DIFFÉRENTIEL GIT

### 1.1 Empreintes Cryptographiques (Calculées le 23/11/2026)

```text
Fichier : Jarvis Final - SITE/main2.py
SHA-256 : F9AA702943625D3E7EF050A628082CC324ABB6C50485E9E59CB270A8CA57F9FB
Taille  : 207 519 octets (4 326 lignes)

Fichier : Jarvis Final - SITE/alice_modules.py
SHA-256 : 711C697BB5F0C03B3D46FD35B0515229D21CB15370C601A05CB718B88BCAA536
Taille  : 56 143 octets (1 260 lignes)

Fichier : Jarvis Final - SITE/mobile/app.js
SHA-256 : DE7B9C3C11B61678AC577DEAAF38F8E27A57E158460D77057F2308C10D6D0783
Taille  : 18 379 octets (520 lignes)

Fichier : Jarvis Final - SITE/mobile/index.html
SHA-256 : 4C7976C853282B7A3AD0DC318BE440A39DBCD6603FC52946B0D6942AB9B2C33C
Taille  : 5 358 octets (137 lignes)
```

### 1.2 Métriques Git (`git diff --stat`)

```text
Jarvis Final - SITE/alice_modules.py | 204 +++++++++++++++++++-------------------
Jarvis Final - SITE/main2.py         | 927 +++++++++++++++++++++++++++++++++++++++++++--------------------------------------
Jarvis Final - SITE/mobile/app.js    | 126 ++++++++++++++++++++---
Jarvis Final - SITE/mobile/index.html|  13 ++-
4 files changed, 725 insertions(+), 545 deletions(-)
```

---

## 2. EXTRAITS DE CODE FORENSIQUES VÉRIFIÉS

### 2.1 SEC-04-A : Élimination de `/api/auth/token` et Implantation de `PairingManager`

Fichier : [main2.py:4064-4079](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L4064-L4079)
```python
        def do_GET(self):
            # Ancien endpoint /api/auth/token supprimé et désactivé (SEC-04)
            if self.path == "/api/auth/token":
                self.send_response(410)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Endpoint obsolète et supprimé pour des raisons de sécurité. Utilisez /api/pair."}).encode("utf-8"))
                return

            if self.path == "/api/pair/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(PAIRING_MANAGER.get_status()).encode("utf-8"))
                return

            super().do_GET()
```

Fichier : [main2.py:490-530](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L490-L530)
```python
class PairingManager:
    """Gestionnaire d'appairage mobile avec code PIN à usage unique, TTL court et protection anti-brute force."""
    def __init__(self, code_ttl: float = 120.0, max_failed_attempts: int = 5):
        self.code_ttl = code_ttl
        self.max_failed_attempts = max_failed_attempts
        self.active_pairing_code: Optional[str] = None
        self.code_expires_at: float = 0.0
        self.failed_attempts: int = 0
        self.lock = threading.Lock()

    def generate_pairing_code(self) -> str:
        with self.lock:
            code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
            self.active_pairing_code = code
            self.code_expires_at = time.time() + self.code_ttl
            self.failed_attempts = 0
            print(f"[PAIRING] Nouveau code d'appairage mobile généré : {code} (valable {int(self.code_ttl)}s)")
            return code

    def consume_pairing_code(self, code_attempt: str) -> bool:
        if not code_attempt or not isinstance(code_attempt, str):
            return False
        with self.lock:
            if not self.active_pairing_code:
                return False
            if time.time() > self.code_expires_at:
                self.active_pairing_code = None
                return False
            if self.failed_attempts >= self.max_failed_attempts:
                self.active_pairing_code = None
                return False
            if hmac.compare_digest(self.active_pairing_code, code_attempt.strip()):
                self.active_pairing_code = None  # Usage unique immédiat
                return True
            else:
                self.failed_attempts += 1
                if self.failed_attempts >= self.max_failed_attempts:
                    self.active_pairing_code = None
                    print("[PAIRING] Nombre maximal de tentatives d'appairage atteint. Code invalidé.")
                return False
```

---

### 2.2 SEC-04-B : Parsing d'Origine et Protection CSWSH

Fichier : [main2.py:603-629](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L603-L629)
```python
    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Validation stricte des origines par adresse IP ou localhost (protection CSWSH)."""
        if not origin or origin == "null":
            return False
        try:
            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https"):
                return False
            host = parsed.hostname
            if not host:
                return False

            # Origines locales autorisées
            if host in ("localhost", "127.0.0.1", "::1"):
                return True

            # Analyse stricte par adresse IP (rejet absolu de tout domaine DNS distant et adresses link-local)
            try:
                ip = ipaddress.ip_address(host)
                if (ip.is_private or ip.is_loopback) and not ip.is_link_local:
                    return True
            except ValueError:
                # C'est un nom de domaine distant, rejet impératif !
                return False
        except Exception:
            return False
        return False
```

---

### 2.3 SEC-04-C : Client Mobile et Gestion d'Authentification

Fichier : [mobile/app.js:201-246](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js#L201-L246)
```javascript
function connectWS() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }

  const sessionId = localStorage.getItem("jarvis_session_id");
  const token = localStorage.getItem("jarvis_session_token");

  // Si pas de session enregistrée, afficher le modal d'appairage (SEC-04-C)
  if (!sessionId || !token) {
    setConnected(false);
    showPairingModal();
    return;
  }

  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    console.log("[WS] Connecté à", WS_URL, "- Transmission du handshake d'authentification");
    ws.send(JSON.stringify({
      type: "auth",
      session_id: sessionId,
      token: token
    }));
  });

  ws.addEventListener("message", (event) => {
    try {
      const data = json.parse(event.data);

      if (data.type === "auth_ok") {
        console.log("[WS] Authentification réussie (Session:", data.session_id, ")");
        setConnected(true);
        hidePairingModal();
        return;
      }

      if (data.type === "auth_error") {
        console.warn("[WS] Erreur authentification :", data.message);
        localStorage.removeItem("jarvis_session_id");
        localStorage.removeItem("jarvis_session_token");
        setConnected(false);
        showPairingModal("Session invalide ou expirée. Veuillez saisir un nouveau code.");
        try { ws.close(4001, "Auth error"); } catch(e) {}
        return;
      }
```

---

### 2.4 SEC-06 : Mémoire Persistante — Verrouillage et Écriture Atomique

Fichier : [main2.py:173-210](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L173-L210)
```python
MEMOIRE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memoire.json")
MEMOIRE_LOCK = threading.RLock()

def charger_memoire():
    """Charge la mémoire de manière thread-safe avec résilience face aux corruptions."""
    with MEMOIRE_LOCK:
        if os.path.exists(MEMOIRE_FILE):
            try:
                with open(MEMOIRE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception as e:
                print(f"[MEMOIRE] Erreur lecture fichier mémoire (corruption potentielle) : {e}")
                return {}
        return {}

def sauvegarder_memoire(memoire):
    """Sauvegarde atomique de la mémoire avec verrouillage et remplacement sécurisé."""
    if not isinstance(memoire, dict):
        print("[MEMOIRE] Format de mémoire invalide, sauvegarde ignorée.")
        return False
    with MEMOIRE_LOCK:
        temp_file = f"{MEMOIRE_FILE}.{os.getpid()}_{time.time_ns()}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(memoire, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, MEMOIRE_FILE)
            return True
        except Exception as e:
            print(f"[MEMOIRE] Erreur sauvegarde atomique mémoire : {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return False
```

---

### 2.5 SEC-03 : Contrôleur Système Multi-Sessions et Isolation de Confirmation

Fichier : [main2.py:2026-2057](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L2026-L2057)
```python
        # 2. Confirmation d'une action en attente
        if "confirmer" in cmd_clean or "confirme" in cmd_clean:
            if session_id not in self.pending_actions:
                # Vérifier si une AUTRE session a une confirmation en cours (protection cross-session !)
                if self.pending_actions:
                    self.log_audit("CROSS_SESSION_ATTEMPT", "Tentative de confirmation croisée rejetée", client_ip, session_id)
                    return "Action non autorisée : la confirmation d'extinction doit provenir de la même session que la demande initiale."
                return "Aucune commande système sensible n'est actuellement en attente de confirmation pour votre session."

            now = time.time()
            action_data = self.pending_actions[session_id]
            if now > action_data["expires_at"]:
                expired_action = action_data["action"]
                del self.pending_actions[session_id]
                self.log_audit("ACTION_EXPIRED", f"Action {expired_action} expirée après 30s", client_ip, session_id)
                return "Le délai de confirmation de 30 secondes a expiré. L'action est annulée par sécurité."

            action = action_data["action"]
            # Vérifier la correspondance de l'action sans ambiguïté
            if action == "shutdown":
                if any(kw in cmd_clean for kw in ["redemarr", "redémarr", "reboot"]):
                    return "Confirmation ambiguë rejetée : l'action en attente est une extinction, pas un redémarrage."
                if not any(kw in cmd_clean for kw in ["eteindre", "éteindre", "extinction", "confirmer", "confirme"]):
                    return "Confirmation ambiguë rejetée. Dites exactement 'confirmer l'extinction' pour valider."
            elif action == "reboot":
                if any(kw in cmd_clean for kw in ["eteindre", "éteindre", "extinction"]):
                    return "Confirmation ambiguë rejetée : l'action en attente est un redémarrage, pas une extinction."
                if not any(kw in cmd_clean for kw in ["redemarr", "redémarr", "reboot", "confirmer", "confirme"]):
                    return "Confirmation ambiguë rejetée. Dites exactement 'confirmer le redémarrage' pour valider."

            del self.pending_actions[session_id]
            self.log_audit("ACTION_CONFIRMED", f"Action {action} validée et déclenchée", client_ip, session_id)
```

---

### 2.6 SEC-05 : Vérité Domotique — Vérification Physique sur Alarme

Fichier : [main2.py:3266-3286](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L3266-L3286)
```python
                    else:
                        # Vérification de l'état physique réel (SEC-05 : REQUEST_ACCEPTED != STATE_VERIFIED)
                        etat_reel = ha_get_etat(alarm_entity)
                        if etat_reel in ["armed_away", "armed_home", "armed_night", "arming", "pending"]:
                            await parler(f"Alarme armée avec succès. État de la centrale vérifié : {etat_reel}.")
                        elif etat_reel in ["unknown", "inconnu"]:
                            await parler("Ordre d'armement transmis à Home Assistant, mais l'état physique de la centrale reste indéterminé.")
                        else:
                            await parler(f"Alerte : l'ordre d'armement a été transmis, mais la centrale signale l'état suivant : {etat_reel}.")
                else:
                    service_ok = ha_appeler_service("alarm_control_panel", "alarm_disarm", alarm_entity)
                    if not service_ok:
                        await parler("Impossible de désarmer l'alarme : la requête vers Home Assistant a échoué.")
                    else:
                        # Vérification de l'état physique réel (SEC-05)
                        etat_reel = ha_get_etat(alarm_entity)
                        if etat_reel in ["disarmed", "disarming"]:
                            await parler("Alarme désarmée avec succès. État physique confirmé.")
                        elif etat_reel in ["unknown", "inconnu"]:
                            await parler("Ordre de désarmement transmis, mais la confirmation de l'état de la centrale est en attente.")
                        else:
                            await parler(f"Attention : l'ordre de désarmement a été transmis, mais la centrale signale : {etat_reel}.")
```

---

## 3. TRACES BRUTES D'EXÉCUTION DU BANC D'ESSAI ADVERSARIAL

Extrait du journal d'exécution de `scratch/test_acceptance_003_adversarial.py` :

```text
================================================================================
ALICE-P0-INDEPENDENT-ACCEPTANCE-003 : ADVERSARIAL CERTIFICATION SUITE
================================================================================
pygame 2.6.1 (SDL 2.28.4, Python 3.11.8)
Hello from the pygame community. https://www.pygame.org/contribute.html
[ALICE MODULES] 16 modules chargés et prêts.

--- 1. ORIGIN PARSER & CSWSH ADVERSARIAL VECTORS ---
[PASS] ADV-SEC04-ORIGIN-01 | SEC-04-B Origin Validation | Origin 'http://localhost:8080' -> Expected True, got True. (Localhost with port 8080)
[PASS] ADV-SEC04-ORIGIN-02 | SEC-04-B Origin Validation | Origin 'http://127.0.0.1:8080' -> Expected True, got True. (IPv4 loopback with port 8080)
[PASS] ADV-SEC04-ORIGIN-03 | SEC-04-B Origin Validation | Origin 'http://[::1]:8080' -> Expected True, got True. (IPv6 loopback with port 8080)
[PASS] ADV-SEC04-ORIGIN-04 | SEC-04-B Origin Validation | Origin 'http://192.168.1.10:8080' -> Expected True, got True. (Legitimate private IP Class C with port)
[PASS] ADV-SEC04-ORIGIN-05 | SEC-04-B Origin Validation | Origin 'http://192.168.attacker.com' -> Expected False, got False. (Domain with private IP prefix (DNS Rebinding/Spoofing))
[PASS] ADV-SEC04-ORIGIN-06 | SEC-04-B Origin Validation | Origin 'http://10.malicious.net' -> Expected False, got False. (Domain with private IP prefix (Class A spoofing))
[PASS] ADV-SEC04-ORIGIN-07 | SEC-04-B Origin Validation | Origin 'http://172.16.1.10' -> Expected True, got True. (Private IP Class B without port)
[PASS] ADV-SEC04-ORIGIN-08 | SEC-04-B Origin Validation | Origin 'http://attacker.example' -> Expected False, got False. (Public adversarial domain)
[PASS] ADV-SEC04-ORIGIN-09 | SEC-04-B Origin Validation | Origin 'https://attacker.example' -> Expected False, got False. (Public HTTPS adversarial domain)
[PASS] ADV-SEC04-ORIGIN-10 | SEC-04-B Origin Validation | Origin 'http://169.254.169.254' -> Expected False, got False. (Link-local cloud metadata service (MUST BE BLOCKED))
[PASS] ADV-SEC04-ORIGIN-11 | SEC-04-B Origin Validation | Origin 'http://169.254.1.1:8080' -> Expected False, got False. (Link-local address (MUST BE BLOCKED))
[PASS] ADV-SEC04-ORIGIN-12 | SEC-04-B Origin Validation | Origin 'http://8.8.8.8:8080' -> Expected False, got False. (Public DNS IP (MUST BE BLOCKED))
[PASS] ADV-SEC04-ORIGIN-13 | SEC-04-B Origin Validation | Origin 'http://1.1.1.1' -> Expected False, got False. (Public IP (MUST BE BLOCKED))
[PASS] ADV-SEC04-ORIGIN-14 | SEC-04-B Origin Validation | Origin 'ftp://127.0.0.1:8080' -> Expected False, got False. (Unexpected FTP scheme)
[PASS] ADV-SEC04-ORIGIN-15 | SEC-04-B Origin Validation | Origin 'ws://127.0.0.1:8080' -> Expected False, got False. (WebSocket scheme in Origin header (Origin is HTTP/HTTPS))
[PASS] ADV-SEC04-ORIGIN-16 | SEC-04-B Origin Validation | Origin 'javascript:alert(1)' -> Expected False, got False. (Javascript pseudo-scheme)
[PASS] ADV-SEC04-ORIGIN-17 | SEC-04-B Origin Validation | Origin 'data:text/html,evil' -> Expected False, got False. (Data URI)
[PASS] ADV-SEC04-ORIGIN-18 | SEC-04-B Origin Validation | Origin 'null' -> Expected False, got False. (Null string origin)
[PASS] ADV-SEC04-ORIGIN-19 | SEC-04-B Origin Validation | Origin '' -> Expected False, got False. (Empty string origin)
[PASS] ADV-SEC04-ORIGIN-20 | SEC-04-B Origin Validation | Origin 'None' -> Expected False, got False. (Missing origin)
[PASS] ADV-SEC04-ORIGIN-21 | SEC-04-B Origin Validation | Origin 'http://localhost.evil.com' -> Expected False, got False. (Subdomain with localhost prefix)
[PASS] ADV-SEC04-ORIGIN-22 | SEC-04-B Origin Validation | Origin 'http://127.0.0.1.attacker.com' -> Expected False, got False. (Subdomain with loopback prefix)
[PASS] ADV-SEC04-ORIGIN-23 | SEC-04-B Origin Validation | Origin 'http://192.168.1.20.nip.io' -> Expected False, got False. (Wildcard DNS resolver for private IP)
[FAIL] ADV-SEC04-ORIGIN-24 | SEC-04-B Origin Validation | Origin 'http://127.0.0.1:99999' -> Expected False, got True. (Invalid port outside 0-65535)
[PASS] ADV-SEC04-ORIGIN-25 | SEC-04-B Origin Validation | Origin 'http://[:::1]' -> Expected False, got False. (Malformed IPv6)

--- 2. PAIRING PROTOCOL & ATTACK RESISTANCE ---
[PAIRING] Nouveau code d'appairage mobile généré : 502470 (valable 120s)
[PASS] ADV-SEC04-PIN-FORMAT | SEC-04 PairingManager | Cryptographic 6-digit PIN format -> Generated PIN: 502470
[PASS] ADV-SEC04-PIN-WRONG | SEC-04 PairingManager | Reject incorrect PIN attempt -> Wrong PIN correctly rejected
[PASS] ADV-SEC04-PIN-CONSUME | SEC-04 PairingManager | Accept valid PIN on first attempt -> Valid PIN consumed
[PASS] ADV-SEC04-PIN-REPLAY | SEC-04 PairingManager | Reject replayed PIN (strictly single-use) -> Replay attempt blocked
[PAIRING] Nouveau code d'appairage mobile généré : 203875 (valable 120s)
[PAIRING] Nombre maximal de tentatives d'appairage atteint. Code invalidé.
[PASS] ADV-SEC04-PIN-LOCKOUT | SEC-04 PairingManager | Enforce lockout after 5 failed attempts -> Lockout enforced. Status active=False, remaining=0
[PAIRING] Nouveau code d'appairage mobile généré : 446702 (valable 120s)
[PASS] ADV-SEC04-PIN-TTL-EXPIRED | SEC-04 PairingManager | Reject expired PIN after TTL (120s) -> Expired PIN rejected
[PASS] ADV-SEC04-NO-HTTP-PIN-REGEN | SEC-04 PairingManager | No remote HTTP endpoint exists to regenerate PIN or reset lockout -> Forensically verified: generate_pairing_code() is called ONLY at server startup (main2.py:4043)

--- 3. SESSION LIFECYCLE & WS HARDENING ---
[PASS] ADV-SEC04-SESS-VERIFY-OK | SEC-04 Session | Verify legitimate active session -> Session verified
[PASS] ADV-SEC04-SESS-BAD-TOKEN | SEC-04 Session | Reject incorrect token for valid session_id -> Forged token rejected
[PASS] ADV-SEC04-SESS-EXPIRED | SEC-04 Session | Reject session whose TTL has expired -> Expired session purged and rejected
[PASS] ADV-SEC04-SESS-REVOKE | SEC-04 Session | Revoke active session -> Session successfully revoked
[PASS] ADV-SEC04-SESS-REVOKED-REUSE | SEC-04 Session | Reject connection with revoked session token (Scenario F) -> Revoked token rejected via revoked_tokens blacklist
[PASS] ADV-SEC04-MULTI-SESSION | SEC-04 Session | Maintain multiple distinct mobile sessions -> Session 1: 5240212f..., Session 2: eb4878a8...

--- 4. SYSTEM ACTION CONTROLLER ISOLATION & LINGUISTIC FILTERING ---
[PASS] ADV-SEC03-THOUGHT-01 | SEC-03 Linguistic Filter | Filter out 'Je pense éteindre mon PC.' -> Desc: Thought expression, Result: None
[PASS] ADV-SEC03-THOUGHT-02 | SEC-03 Linguistic Filter | Filter out 'Je ne veux pas éteindre mon PC.' -> Desc: Negation, Result: None
[PASS] ADV-SEC03-THOUGHT-03 | SEC-03 Linguistic Filter | Filter out 'Si j'éteignais mon PC ?' -> Desc: Hypothesis, Result: None
[PASS] ADV-SEC03-THOUGHT-04 | SEC-03 Linguistic Filter | Filter out 'Comment éteindre un PC ?' -> Desc: Question/informational, Result: None
[PASS] ADV-SEC03-THOUGHT-05 | SEC-03 Linguistic Filter | Filter out 'N'éteins pas mon PC.' -> Desc: Explicit negative imperative, Result: None
[PASS] ADV-SEC03-THOUGHT-06 | SEC-03 Linguistic Filter | Filter out 'J'hésite à éteindre mon ordinateur' -> Desc: Hesitation, Result: None
[PASS] ADV-SEC03-THOUGHT-07 | SEC-03 Linguistic Filter | Filter out 'Faudrait-il redémarrer l'ordi ?' -> Desc: Indirect thought, Result: None
[PASS] ADV-SEC03-2FA-TRIGGER | SEC-03 2FA Trigger | Imperative command prompts for confirmation -> Pending action recorded for session 5240212f
[PASS] ADV-SEC03-CROSS-CONFIRM-REJECT | SEC-03 Multi-Session Isolation | Reject cross-session confirmation attack (Scenario C) -> Cross-session attempt blocked. Pending action preserved for 5240212f
[PASS] ADV-SEC03-CROSS-CANCEL-REJECT | SEC-03 Multi-Session Isolation | Reject cross-session cancellation attempt -> Cancellation attack from foreign session rejected
[PASS] ADV-SEC03-AMBIGUOUS-ACTION | SEC-03 Disambiguation | Reject confirmation of conflicting action (reboot instead of shutdown) -> Ambiguity blocked, pending action preserved
[PASS] ADV-SEC03-VALID-CONFIRM | SEC-03 Confirmation Execution | Execute confirmed action for legitimate owner session (DRY-RUN) -> Response: [DRY-RUN] Commande shutdown confirmée avec succès. Aucune interruption OS réelle appliquée.
[PASS] ADV-SEC03-REPLAY-CONFIRM | SEC-03 Anti-Replay | Reject replay of confirmation after action already executed -> Replay rejected
[PASS] ADV-SEC03-TIMEOUT-EXPIRED | SEC-03 Timeout | Reject confirmation after 30-second TTL expiration -> Expired action purged and rejected

--- 5. MEMORY CONCURRENCY, ATOMIC WRITES & RECOVERY ---
[PASS] ADV-SEC06-CONCURRENCY-50 | SEC-06 Memory Concurrency | 50 concurrent write/read/delete threads without corruption (Scenario D) -> Errors: 0, Remaining keys: 25 (expected 25)
[MEMOIRE] Erreur lecture fichier mémoire (corruption potentielle) : Unterminated string starting at: line 1 column 2 (char 1)
[PASS] ADV-SEC06-CORRUPT-RESILIENCE | SEC-06 Fault Tolerance | charger_memoire recovers gracefully from corrupted JSON -> Returned empty dict on corrupted JSON: {}
[MEMOIRE] Erreur lecture fichier mémoire (corruption potentielle) : Unterminated string starting at: line 1 column 2 (char 1)
[PASS] ADV-SEC06-RESTORE-AFTER-CORRUPT | SEC-06 Fault Tolerance | Memory recovers and saves valid JSON after encountering corruption -> Atomic save recovered storage

--- 6. HOME ASSISTANT STATE VERIFICATION & PHYSICAL INTEGRITY ---
[JARVIS] Réponse complète : {"action": "ha_alarme", "etat": "on"}
[JARVIS] Execution de l'action : {"action": "ha_alarme", "etat": "on"}
[HA DEBUG] Calling alarm_control_panel/alarm_arm_away for alarm_control_panel.home_base_2 with None
[HA DEBUG] Response 200: [{"success": true}]
[PASS] ADV-SEC05-ALARM-ARM-VERIFIED | SEC-05 State Verification | ha_alarme reports success when state is armed_away -> Spoken: ["Alarme armée avec succès. État de la centrale vérifié : armed_away."]
[JARVIS] Réponse complète : {"action": "ha_alarme", "etat": "on"}
[JARVIS] Execution de l'action : {"action": "ha_alarme", "etat": "on"}
[HA DEBUG] Calling alarm_control_panel/alarm_arm_away for alarm_control_panel.home_base_2 with None
[HA DEBUG] Response 200: [{"success": true}]
[PASS] ADV-SEC05-ALARM-ARM-PHYSICAL-FAIL | SEC-05 State Verification | ha_alarme detects and alerts when state remains disarmed despite HTTP 200 (Scenario E) -> Spoken: ["Alerte : l'ordre d'armement a été transmis, mais la centrale signale l'état suivant : disarmed."]
[JARVIS] Réponse complète : {"action": "ha_alarme", "etat": "on"}
[JARVIS] Execution de l'action : {"action": "ha_alarme", "etat": "on"}
[HA DEBUG] Calling alarm_control_panel/alarm_arm_away for alarm_control_panel.home_base_2 with None
[HA DEBUG] Response 200: [{"success": true}]
[PASS] ADV-SEC05-ALARM-ARM-UNKNOWN | SEC-05 State Verification | ha_alarme alerts user when physical state is unknown -> Spoken: ["Ordre d'armement transmis à Home Assistant, mais l'état physique de la centrale reste indéterminé."]
[JARVIS] Réponse complète : {"action": "ha_alarme", "etat": "on"}
[JARVIS] Execution de l'action : {"action": "ha_alarme", "etat": "on"}
[HA DEBUG] Calling alarm_control_panel/alarm_arm_away for alarm_control_panel.home_base_2 with None
[HA DEBUG] Response 500: {"error": "HA Internal Error"}
[PASS] ADV-SEC05-ALARM-HTTP-500 | SEC-05 State Verification | ha_alarme reports failure when HTTP status is 500 -> Spoken: ["Impossible d'armer l'alarme : la requête vers Home Assistant a échoué."]
[JARVIS] Réponse complète : {"action": "ha_lumiere", "piece": "salon", "etat": "on"}
[JARVIS] Execution de l'action : {"action": "ha_lumiere", "piece": "salon", "etat": "on"}
[HA DEBUG] Calling light/turn_on for light.salon with {}
[HA DEBUG] Response 200: [{"success": true}]
[PASS] ADV-SEC05-LIGHT-ACK-LIMITATION | SEC-05 State Verification Limitation | ha_lumiere confirms based on service ACK (HTTP 200) without polling ha_get_etat -> Spoken: ['Lumière salon allumée.'] (Forensic note: ha_lumiere has no two-stage verification like ha_alarme)

--- 7. NON-REGRESSION : SEC-01 AST & SEC-02 UPLOAD HARDENING ---
[ALICE MODULES] 16 modules chargés et prêts.
[PASS] ADV-SEC01-AST-01 | SEC-01 Static AST Analysis | Verify '__import__('os').system('...' -> Desc: Direct dynamic import, got safe=False, status=REJECTED_UNSAFE_OR_INVALID
[PASS] ADV-SEC01-AST-02 | SEC-01 Static AST Analysis | Verify 'import sys; sys.exit(0)...' -> Desc: System module import, got safe=False, status=REJECTED_UNSAFE_OR_INVALID
[PASS] ADV-SEC01-AST-03 | SEC-01 Static AST Analysis | Verify 'eval('1+1')...' -> Desc: eval call, got safe=False, status=REJECTED_UNSAFE_OR_INVALID
[PASS] ADV-SEC01-AST-04 | SEC-01 Static AST Analysis | Verify 'exec('a=1')...' -> Desc: exec call, got safe=False, status=REJECTED_UNSAFE_OR_INVALID
[FAIL] ADV-SEC01-AST-05 | SEC-01 Static AST Analysis | Verify 'open('secrets.txt', 'r')...' -> Desc: File open call, got safe=True, status=SECURE_STATIC_VERIFIED
[PASS] ADV-SEC01-AST-06 | SEC-01 Static AST Analysis | Verify 'def compute(x): return x ...' -> Desc: Safe mathematical code, got safe=True, status=SECURE_STATIC_VERIFIED
[PASS] ADV-SEC02-UPLOAD-01 | SEC-02 Upload Hardening | Filter '../../../Windows/System32/calc.exe' -> Desc: Traversal to System32 with .exe, allowed=False, confined=True
[PASS] ADV-SEC02-UPLOAD-02 | SEC-02 Upload Hardening | Filter '..\..\boot.ini' -> Desc: Windows traversal with .ini, allowed=False, confined=True
[PASS] ADV-SEC02-UPLOAD-03 | SEC-02 Upload Hardening | Filter 'evil.bat' -> Desc: Executable script .bat, allowed=False, confined=True
[PASS] ADV-SEC02-UPLOAD-04 | SEC-02 Upload Hardening | Filter 'payload.ps1' -> Desc: Powershell script .ps1, allowed=False, confined=True
[PASS] ADV-SEC02-UPLOAD-05 | SEC-02 Upload Hardening | Filter 'legit_document.pdf' -> Desc: Safe PDF document, allowed=True, confined=True
[PASS] ADV-SEC02-UPLOAD-06 | SEC-02 Upload Hardening | Filter 'research_notes.md' -> Desc: Safe Markdown file, allowed=True, confined=True

--- 8. TRANSPORT & CLIENT-SIDE ARCHITECTURAL RESIDUAL RISKS ---
[PASS] ADV-RISK-CLEARTEXT-LAN | Transport Security | HTTP 8080 and WS 8765 operate without TLS/WSS over LAN -> VULNERABILITY CONFIRMED: Plain HTTP/WS transmits PIN and session token in cleartext over Wi-Fi/LAN.
[PASS] ADV-RISK-LOCALSTORAGE-XSS | Client-Side Storage | Session token stored in window.localStorage rather than HttpOnly cookie -> VULNERABILITY CONFIRMED: In case of DOM-XSS on mobile client, jarvis_session_token can be extracted via document.location / fetch.
[PASS] ADV-RISK-MULTIPROCESS-LOCK | Memory Architecture | threading.RLock protects multi-threading but does not synchronize multi-process access -> ARCHITECTURAL LIMITATION: If multiple processes run main2.py or jarvis_agent.py simultaneously, race conditions can occur.

================================================================================
ADVERSARIAL CERTIFICATION SUITE RESULT : 73/75 PASSED (97.3%)
FAILURES : 2
================================================================================
```
