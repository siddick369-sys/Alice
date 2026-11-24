# 🛡️ ALICE — MATRICE DE TESTS D'HOMOLOGATION FORENSIQUE P0-004
## RÉSULTATS EXHAUSTIFS DE LA SUITE D'ACCEPTATION ADVERSARIALE INDÉPENDANTE

- **Projet :** J.A.R.V.I.S / ALICE — SITE-V2
- **Mission ID :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-004`
- **Référence audit préalable :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-003`
- **Fichier de test exécuté :** [test_acceptance_004_master.py](file:///C:/Users/USER/.gemini/antigravity/brain/9f43747e-d272-4f9c-bf13-f2fb641773ea/scratch/test_acceptance_004_master.py)
- **Environnement d'exécution :** Python 3.11.8 (venv) sous Windows
- **Résultat global :** 86 / 86 tests RÉUSSIS (100.0%) — 0 ÉCHEC

---

### Résumé par Section d'Épreuve

| Section | Domaine d'Audit et de Sécurité | Nb Tests | Succès | Échecs | Statut |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Section 1** | Baseline forensique et intégrité SHA-256 | 3 | 3 | 0 | **PASS** |
| **Section 2** | Condition C-01 : Architecture TLS/WSS et Reverse-Proxy | 11 | 11 | 0 | **PASS** |
| **Section 3** | Condition C-02 : Validation stricte des origines et ports | 46 | 46 | 0 | **PASS** |
| **Section 4** | Condition C-03 : Verrouillage mémoire OS et multiprocessus | 5 | 5 | 0 | **PASS** |
| **Section 5** | Condition C-04 : Vérité domotique Home Assistant | 6 | 6 | 0 | **PASS** |
| **Section 6** | SEC-01 : Analyse statique AST et invariants d'exécution | 7 | 7 | 0 | **PASS** |
| **Section 7** | Scénarios adversariaux combinés (Scénarios A à H) | 8 | 8 | 0 | **PASS** |
| **TOTAL** | **Toutes épreuves d'homologation confondues** | **86** | **86** | **0** | **APPROVED (100%)** |

---

## 1. SECTION 1 : BASELINE FORENSIQUE ET INTÉGRITÉ DU CODE SOURCE

| Test ID | Domaine | Description du Test | Entrée / Cible | Résultat Obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `BASE-01-MAIN2-HASH` | Baseline | Vérification d'intégrité de `main2.py` | `Jarvis Final - SITE/main2.py` | `E1EA29C4A994E4FB...` (64 car.) | **PASS** |
| `BASE-02-ALICE-HASH` | Baseline | Vérification d'intégrité de `alice_modules.py` | `Jarvis Final - SITE/alice_modules.py` | `FC879F59E07B9E4F...` (64 car.) | **PASS** |
| `BASE-03-AGENT-HASH` | Baseline | Vérification d'intégrité de `jarvis_agent.py` | `Jarvis Final - SITE/jarvis_agent.py` | `EA7DD54D58FDC886...` (64 car.) | **PASS** |

---

## 2. SECTION 2 : CONDITION C-01 — TRANSPORT TLS / WSS ET REVERSE-PROXY

| Test ID | Domaine | Description du Scénario | Configuration d'Entrée | Résultat Obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `C01-PROD-FAIL-CLOSED` | C-01 TLS/WSS | Comportement fail-closed sans certificat en production | `ALICE_ENV=production` | `FAIL_CLOSED_TLS_REQUIRED` | **PASS** |
| `C01-JARVIS-PROD-FAIL-CLOSED` | C-01 TLS/WSS | Fail-closed via variable d'environnement Jarvis | `JARVIS_ENV=production` | `FAIL_CLOSED_TLS_REQUIRED` | **PASS** |
| `C01-REQ-TLS-FAIL-CLOSED` | C-01 TLS/WSS | Fail-closed via flag d'exigence TLS explicite | `ALICE_REQUIRE_TLS=1` | `FAIL_CLOSED_TLS_REQUIRED` | **PASS** |
| `C01-DEV-DEGRADED` | C-01 TLS/WSS | Mode dégradé en développement sans certificat | `ALICE_ENV=development` | `DEVELOPMENT_PLAINTEXT_DEGRADED` | **PASS** |
| `C01-PROD-NONEXISTENT-CERT` | C-01 TLS/WSS | Fichiers de certificat introuvables en production | Chemins inexistants | `FAIL_CLOSED_TLS_REQUIRED` | **PASS** |
| `C01-PROD-CORRUPT-CERT` | C-01 TLS/WSS | Certificats corrompus ou invalides | Chaîne non-PEM | `FAIL_CLOSED_TLS_REQUIRED` (sans crash) | **PASS** |
| `C01-PROXY-UNTRUSTED-REJECT` | C-01 Proxy | Rejet de l'en-tête `XFF` émis par un client non approuvé | Client socket direct `198.51.100.25` | IP retenue = `198.51.100.25` | **PASS** |
| `C01-PROXY-TRUSTED-ACCEPT` | C-01 Proxy | Prise en compte de `XFF` depuis un proxy de confiance | Proxy local `127.0.0.1`, `XFF: 203.0.113.88` | IP retenue = `203.0.113.88` | **PASS** |
| `C01-PROXY-CHAIN-FIRST-IP` | C-01 Proxy | Extraction de l'IP originale dans une chaîne de proxies | `XFF: 198.51.100.99, 10.0.0.2` | IP retenue = `198.51.100.99` | **PASS** |
| `C01-PROXY-MALFORMED-FALLBACK` | C-01 Proxy | Repli sécurisé face à une charge non-IP malveillante dans `XFF` | `XFF: <script>alert(1)</script>` | IP socket directe `127.0.0.1` | **PASS** |
| `C01-PROXY-IPV6-TRUSTED` | C-01 Proxy | Prise en compte de proxy de confiance IPv6 loopback | Proxy socket `::1`, `XFF: 2001:db8::1234` | IP retenue = `2001:db8::1234` | **PASS** |

---

## 3. SECTION 3 : CONDITION C-02 — VALIDATION STRICTE DES ORIGINES ET DES PORTS

| Test ID | Domaine | Description du Vecteur | Payload d'Origine Testé | Résultat Obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `C02-ORIGIN-DEV-01` | C-02 Allowlist | Port standard dev http localhost | `http://localhost:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-02` | C-02 Allowlist | Port standard dev https localhost | `https://localhost:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-03` | C-02 Allowlist | Loopback IPv4 dev standard | `http://127.0.0.1:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-04` | C-02 Allowlist | Loopback IPv6 dev standard | `http://[::1]:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-05` | C-02 Allowlist | Serveur de dev Vite (port 5173) | `http://localhost:5173` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-06` | C-02 Allowlist | Serveur de dev React (port 3000) | `http://localhost:3000` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-07` | C-02 Allowlist | Réseau local LAN privé classe C | `http://192.168.1.50:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-08` | C-02 Allowlist | Réseau local LAN privé classe A | `http://10.0.0.5:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-09` | C-02 Allowlist | Réseau local LAN privé classe B | `http://172.16.0.1:8080` | `True` (Accepté) | **PASS** |
| `C02-ORIGIN-DEV-10` | C-02 Allowlist | Port 99999 (> 65535) sur 127.0.0.1 | `http://127.0.0.1:99999` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-11` | C-02 Allowlist | Port 99999 (> 65535) sur localhost | `http://localhost:99999` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-12` | C-02 Allowlist | Port 0 (hors plage RFC 6454) | `http://127.0.0.1:0` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-13` | C-02 Allowlist | Port négatif (-80) | `http://127.0.0.1:-80` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-14` | C-02 Allowlist | Port 9999 hors allowlist | `http://127.0.0.1:9999` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-15` | C-02 Allowlist | Port 3001 hors allowlist | `http://localhost:3001` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-16` | C-02 Allowlist | Port 80 non configuré en dev | `http://localhost:80` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-17` | C-02 Allowlist | Port 443 non configuré en dev | `https://localhost:443` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-18` | C-02 Allowlist | Injection de userinfo (user:pass) | `http://user:pass@localhost:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-19` | C-02 Allowlist | Injection de username seul | `http://user@localhost:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-20` | C-02 Allowlist | Chemin spécifique non vide (/api) | `http://localhost:8080/api/v1` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-21` | C-02 Allowlist | Query string dans l'origine | `http://localhost:8080?bypass=1` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-22` | C-02 Allowlist | Fragment dans l'origine | `http://localhost:8080#section` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-23` | C-02 Allowlist | Nom d'hôte avec point final | `http://localhost.:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-24` | C-02 Allowlist | Sous-domaine d'attaque suffixé | `http://localhost.evil.com:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-25` | C-02 Allowlist | Domaine DNS simulant IP privée C | `http://192.168.attacker.com:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-26` | C-02 Allowlist | Domaine DNS simulant IP privée A | `http://10.attacker.io:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-27` | C-02 Allowlist | Domaine DNS simulant IP privée B | `http://172.malicious.net:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-28` | C-02 Allowlist | Résolveur DNS wildcard `nip.io` | `http://192.168.1.1.nip.io:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-29` | C-02 Allowlist | Métadonnées cloud AWS/GCP | `http://169.254.169.254:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-30` | C-02 Allowlist | Adresse link-local générique | `http://169.254.1.1:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-31` | C-02 Allowlist | IP publique routable (8.8.8.8) | `http://8.8.8.8:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-32` | C-02 Allowlist | IP publique routable (1.1.1.1) | `http://1.1.1.1:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-33` | C-02 Allowlist | Schéma non HTTP/HTTPS (FTP) | `ftp://localhost:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-34` | C-02 Allowlist | Schéma WebSocket dans Origin (ws) | `ws://localhost:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-35` | C-02 Allowlist | Schéma WebSocket sécurisé (wss) | `wss://localhost:8080` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-36` | C-02 Allowlist | Pseudo-schéma `javascript:` | `javascript:alert(1)` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-37` | C-02 Allowlist | Schéma URI de données `data:` | `data:text/html,payload` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-38` | C-02 Allowlist | Chaîne littérale `"null"` iframe | `"null"` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-39` | C-02 Allowlist | Origine chaîne vide `""` | `""` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-40` | C-02 Allowlist | Origine `None` (absente) | `None` | `False` (Rejeté) | **PASS** |
| `C02-ORIGIN-DEV-41` | C-02 Allowlist | Adresse IPv6 malformée | `http://[:::1]:8080` | `False` (Rejeté) | **PASS** |
| `C02-PROD-LOOPBACK-PLAIN-HTTP` | C-02 Allowlist | Loopback en production sur port système | `http://127.0.0.1:8080` | `True` (Port 8080 dans ports) | **PASS** |
| `C02-PROD-REJECT-LAN-BY-DEFAULT` | C-02 Allowlist | Origine LAN privée en prod sans variable | `http://192.168.1.50:8080` | `False` (Rejeté par défaut) | **PASS** |
| `C02-PROD-ACCEPT-HTTPS-8443` | C-02 Allowlist | Origine HTTPS sécurisée en prod (8443) | `https://localhost:8443` | `True` (Accepté) | **PASS** |
| `C02-PROD-CUSTOM-ALLOW-OK` | C-02 Allowlist | Domaine explicite configuré dans la variable | `https://jarvis.internal:8443` | `True` (Accepté) | **PASS** |
| `C02-PROD-CUSTOM-ALLOW-REJECT` | C-02 Allowlist | Domaine hors allowlist explicite en prod | `https://evil.internal:8443` | `False` (Rejeté) | **PASS** |

---

## 4. SECTION 4 : CONDITION C-03 — VERROUILLAGE MÉMOIRE ET MULTIPROCESSUS

| Test ID | Domaine | Description de l'Épreuve | Mécanisme Validé | Résultat Obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `C03-LOCK-REENTRANCY` | C-03 Verrou OS | Réentrance locale sur le même thread sans interblocage | Verrouillage imbriqué triple niveau | Acquis et libéré proprement | **PASS** |
| `C03-MULTIPROCESS-STRESS` | C-03 Multi-Proc | Épreuve de stress avec 3 processus Python concurrents | 45 écritures et 15 suppressions réelles | 30 entrées consolidées, 0 corruption | **PASS** |
| `C03-LOCK-BLOCKED-TIMEOUT` | C-03 Verrou OS | Blocage temporisé d'un second processus en concurrence | Attente et levée d'exception `TimeoutError` | `TimeoutError` déclenchée sous 0.2s | **PASS** |
| `C03-CRASH-LOCK-RECOVERY` | C-03 Crash | Libération automatique après mort brutale du processus | `terminate()` du détenteur du verrou | Verrou récupéré immédiatement | **PASS** |
| `C03-JARVIS-AGENT-INTEGRATION` | C-03 Agent CLI | Délégation de `jarvis_agent.py` vers les primitives sécurisées | Sauvegarde et rechargement canonique | Donnée persistée sous verrou | **PASS** |

---

## 5. SECTION 5 : CONDITION C-04 — VÉRITÉ DOMOTIQUE HOME ASSISTANT

| Test ID | Domaine | Scénario Éprouvé | Simulation Matérielle | Comportement Vocale Constaté | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `C04-LIGHT-VERIFIED-ON` | C-04 Vérité HA | Allumage de lumière confirmé matériellement | HTTP 200 + Sondage `state: on` | *"C'est fait, lumière salon allumée. État matériel vérifié."* | **PASS** |
| `C04-LIGHT-PHYSICAL-TIMEOUT` | C-04 Vérité HA | Allumage accepté par l'API mais ampoule coupée | HTTP 200 + Sondage reste `state: off` | *"Attention : l'ordre a été envoyé à Home Assistant, mais l'appareil salon signale toujours l'état : off."* | **PASS** |
| `C04-LIGHT-UNAVAILABLE` | C-04 Vérité HA | Ampoule injoignable ou hors ligne | HTTP 200 + Sondage `state: unavailable` | *"L'ordre pour la lumière de salon a été transmis, mais l'état réel de l'ampoule reste indéterminé."* | **PASS** |
| `C04-PLUG-VERIFIED-ON` | C-04 Vérité HA | Prise activée et confirmée physiquement | HTTP 200 + Sondage `state: on` | *"Prise bureau activée. État matériel vérifié."* | **PASS** |
| `C04-PLUG-PHYSICAL-TIMEOUT` | C-04 Vérité HA | Prise acceptée par l'API mais bloquée sur off | HTTP 200 + Sondage reste `state: off` | *"Attention : l'ordre a été envoyé pour la prise bureau, mais l'équipement signale toujours l'état : off."* | **PASS** |
| `C04-ALARM-VERIFIED` | C-04 Vérité HA | Armement alarme vérifié au panneau central | HTTP 200 + Sondage `state: armed_away` | *"Alarme armée avec succès. État de la centrale vérifié : armed_away."* | **PASS** |

---

## 6. SECTION 6 : SEC-01 — ANALYSE STATIQUE AST ET EXÉCUTION DÉSACTIVÉE

| Test ID | Domaine | Snippet Python Évalué | Détection AST | Statut de Sécurité | Exécution Hôte | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `SEC01-AST-OPEN` | SEC-01 AST | `with open('secrets.txt', 'r') as f:` | Appel à `open()` détecté | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-INPUT` | SEC-01 AST | `p = input('Enter secret:')` | Appel à `input()` détecté | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-EXEC` | SEC-01 AST | `exec('a=1')` | Appel à `exec()` détecté | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-EVAL` | SEC-01 AST | `eval('2+2')` | Appel à `eval()` détecté | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-COMP` | SEC-01 AST | `compile('print(1)', '', 'exec')` | Appel à `compile()` détecté | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-SAFE-CODE` | SEC-01 AST | `def factorial(n): ...` (math pur) | Aucune instruction dangereuse | `SECURE_STATIC_VERIFIED` | N/A | **PASS** |
| `SEC01-EXECUTION-DISABLED` | SEC-01 Invariant | Code sain validé | Invariant strict du système | `DISABLED_FOR_SECURITY` | Strictement bloquée | **PASS** |

---

## 7. SECTION 7 : SCÉNARIOS ADVERSARIAUX COMBINÉS (A À H)

| Test ID | Scénario | Vecteur d'Attaque Éprouvé | Comportement Attendu | Résultat Constaté | Statut |
| :--- | :---: | :--- | :--- | :--- | :---: |
| `SCENARIO-A-TLS-DOWNGRADE` | A | Mode production sans certificat + requête client | Refus de démarrer en clair (fail-closed) | `FAIL_CLOSED_TLS_REQUIRED` | **PASS** |
| `SCENARIO-B-SPOOFING` | B | Origine publique + en-tête `XFF` forgé vers loopback | Ignorer `XFF` usurpé et rejeter l'origine | IP réelle retenue et origine bloquée | **PASS** |
| `SCENARIO-C-MEMORY-RESILIENCE` | C | Écritures multiprocessus concurrentes + crash | Aucune corruption, zéro interblocage | Validé via Suite 4 | **PASS** |
| `SCENARIO-D-IMPORT-SIDE-EFFECTS` | D | Importation de `jarvis_agent.py` en sous-processus | Aucun serveur HTTP/WS ne démarre | 1 seul thread résiduel, 0 socket | **PASS** |
| `SCENARIO-E-TOKEN-REVOCATION` | E | Rejeu d'un jeton WebSocket révoqué | Jeton invalidé refusé immédiatement | `verify_session -> False` | **PASS** |
| `SCENARIO-F-HA-NO-FALSE-SUCCESS` | F | Code 200 de service HA avec équipement non commuter | Aucun message trompeur de succès | Alerte explicite d'état non changé | **PASS** |
| `SCENARIO-G-DEV-TO-PROD-PORTS` | G | Port Vite (5173) soumis en environnement de prod | Port de dev strictement interdit en prod | `is_origin_allowed -> False` | **PASS** |
| `SCENARIO-H-SESSION-ISOLATION` | H | Session B tentant de confirmer l'extinction de Session A | Blocage cross-session immédiat | *"Action non autorisée... même session"* | **PASS** |

---
**Fichier de résultat brut JSON certifié :** `scratch/acceptance_004_test_results.json`  
**Verdict :** 100% des épreuves sont validées avec succès. Homologation **APPROVED**.
