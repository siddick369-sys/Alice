# 🛡️ ALICE — MATRICE DE TESTS D'HOMOLOGATION P0-003
## VALIDATION FORENSIQUE DES CONDITIONS C-01, C-02, C-03, C-04 ET RENFORCEMENT SEC-01

- **Projet :** J.A.R.V.I.S / ALICE — SITE-V2
- **Mission :** `ALICE-P0-REMEDIATION-003`
- **Fichier de test exécuté :** [test_remediation_003_comprehensive.py](file:///C:/Users/USER/.gemini/antigravity/brain/9f43747e-d272-4f9c-bf13-f2fb641773ea/scratch/test_remediation_003_comprehensive.py)
- **Environnement d'exécution :** Python 3.11.8 (venv) sous Windows
- **Résultat global :** 63 / 63 tests RÉUSSIS (100.0%) — 0 ÉCHEC

---

### Résumé par Domaine de Test

| Domaine | Condition Audit 003 | Nombre de Tests | Succès | Échecs | Statut |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **SUITE 1** | C-02 Validation stricte des origines et des ports | 39 | 39 | 0 | **PASS** |
| **SUITE 2** | C-01 Architecture TLS / WSS et proxy de confiance | 5 | 5 | 0 | **PASS** |
| **SUITE 3** | C-03 Verrouillage mémoire inter-processus et audit agent | 5 | 5 | 0 | **PASS** |
| **SUITE 4** | C-04 Vérification physique d'état Home Assistant | 6 | 6 | 0 | **PASS** |
| **SUITE 5** | SEC-01 Renforcement AST et interdiction `open`/`input` | 8 | 8 | 0 | **PASS** |
| **TOTAL** | **Toutes suites confondues** | **63** | **63** | **0** | **PASS (100%)** |

---

## 1. SUITE 1 : VALIDATION STRICTE DES ORIGINES ET DES PORTS (CONDITION C-02)

| Test ID | Condition | Description / Payload testé | Résultat attendu | Résultat obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `C02-ORIGIN-01` | C-02 | `http://localhost:8080` (Origine dev autorisée) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-02` | C-02 | `https://localhost:8080` (Origine dev https) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-03` | C-02 | `http://127.0.0.1:8080` (IPv4 loopback) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-04` | C-02 | `http://[::1]:8080` (IPv6 loopback) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-05` | C-02 | `http://localhost:5173` (Vite dev server) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-06` | C-02 | `http://127.0.0.1:5173` (Vite dev IPv4) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-07` | C-02 | `http://192.168.1.10:8080` (IP privée LAN) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-08` | C-02 | `http://127.0.0.1:99999` (Port hors limite > 65535) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-09` | C-02 | `http://localhost:99999` (Port hors limite sur localhost) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-10` | C-02 | `http://127.0.0.1:9999` (Port inattendu hors allowlist) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-11` | C-02 | `http://localhost:3001` (Port inattendu) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-12` | C-02 | `http://192.168.1.10:9999` (Port inattendu sur LAN) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-13` | C-02 | `http://127.0.0.1:0` (Port zéro invalide) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-14` | C-02 | `http://127.0.0.1:-80` (Port négatif invalide) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-15` | C-02 | `http://localhost:80` (Port 80 non configuré dev) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-16` | C-02 | `https://localhost:443` (Port 443 non configuré dev) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-17` | C-02 | `http://localhost.:8080` (Trailing dot suspect) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-18` | C-02 | `http://localhost.evil.com:8080` (Suffixe malveillant) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-19` | C-02 | `http://192.168.attacker.com:8080` (Préfixe IP dans DNS) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-20` | C-02 | `http://10.malicious.net:8080` (Préfixe classe A dans DNS) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-21` | C-02 | `http://169.254.169.254:8080` (Metadata link-local) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-22` | C-02 | `http://8.8.8.8:8080` (IP publique routable) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-23` | C-02 | `http://user:pass@localhost:8080` (Userinfo rejeté) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-24` | C-02 | `http://localhost:8080/unexpected_path` (Path rejeté) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-25` | C-02 | `http://localhost:8080?query=1` (Query rejetée) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-26` | C-02 | `http://localhost:8080#fragment` (Fragment rejeté) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-27` | C-02 | `'null'` (Origine nulle sandboxée) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-28` | C-02 | `''` (Origine chaîne vide) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-29` | C-02 | `'None'` (Origine absente / None en chaîne) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-30` | C-02 | `ftp://localhost:8080` (Schéma non http/https) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-31` | C-02 | `ws://localhost:8080` (Schéma WebSocket direct) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-32` | C-02 | `javascript:alert(1)` (Pseudo-schéma JS) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-33` | C-02 | `data:text/html,payload` (Schéma data) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-34` | C-02 | `http://[:::1]:8080` (IPv6 malformée) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-35` | C-02 | `http://192.168.1.20.nip.io:8080` (DNS wildcard IP) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-36` | C-02 | `https://jarvis.internal:8443` (Prod : Allowlist explicite) | Accepté (`True`) | `True` | **PASS** |
| `C02-ORIGIN-37` | C-02 | `https://evil.internal:8443` (Prod : Rejet si non listé) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-38` | C-02 | `http://127.0.0.1:8080` (Prod : Rejet HTTP clair sans config) | Rejeté (`False`) | `False` | **PASS** |
| `C02-ORIGIN-39` | C-02 | `https://localhost:8443` (Prod : Accepté port 8443) | Accepté (`True`) | `True` | **PASS** |

---

## 2. SUITE 2 : ARCHITECTURE TLS / WSS ET PROXY DE CONFIANCE (CONDITION C-01)

| Test ID | Condition | Description du Test | Entrée / Configuration | Résultat attendu | Résultat obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `C01-TLS-DEV-FALLBACK` | C-01 | Fallback toléré en mode dev sans certificat | `ALICE_ENV=development`, pas de certificat | `get_ssl_context() -> None` sans crash | `None` | **PASS** |
| `C01-TLS-PROD-FAIL-CLOSED` | C-01 | Fail-closed strict en mode production sans certificat | `ALICE_ENV=production`, pas de certificat | Lève `RuntimeError` explicite | `RuntimeError` capturée | **PASS** |
| `C01-TLS-CONTEXT-LOAD` | C-01 | Chargement et configuration TLS durcie | Paire de certificats X.509 auto-signés valides | `SSLContext` initialisé, options durcies | Contexte valide | **PASS** |
| `C01-PROXY-UNTRUSTED` | C-01 | Rejet d'un en-tête `X-Forwarded-For` émis par hôte non approuvé | Socket source `198.51.100.42`, `XFF: 1.2.3.4` | IP socket retenue (`198.51.100.42`) | `198.51.100.42` | **PASS** |
| `C01-PROXY-TRUSTED` | C-01 | Prise en compte de `X-Forwarded-For` depuis un proxy approuvé | Socket source `127.0.0.1`, `XFF: 203.0.113.195` | IP transmise retenue (`203.0.113.195`) | `203.0.113.195` | **PASS** |

---

## 3. SUITE 3 : VERROUILLAGE MÉMOIRE ET AUDIT DE L'AGENT (CONDITION C-03)

| Test ID | Condition | Description du Test | Scénario d'Épreuve | Résultat attendu | Résultat obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `C03-LOCK-REENTRANCY` | C-03 | Réentrance locale sur le même thread | Verrouillage réentrant imbriqué triple niveau | Acquisition sans interblocage | Reentrance OK | **PASS** |
| `C03-LOCK-MULTITHREAD` | C-03 | Résistance concurrente 30 threads | 30 écritures et 10 suppressions concurrentes | 20 entrées nettes, aucune corruption JSON | 20 entrées conservées | **PASS** |
| `C03-CROSS-PROCESS-BLOCKING` | C-03 | Verrouillage OS inter-processus avec timeout | Processus tiers détenant le verrou fichier OS | `TimeoutError` levée après dépassement du timeout | `TimeoutError` capturée | **PASS** |
| `C03-CROSS-PROCESS-RELEASE` | C-03 | Déverrouillage automatique à la fin du processus tiers | Acquisition immédiate après sortie du sous-processus | Acquisition instantanée réussie | Verrou acquis | **PASS** |
| `C03-JARVIS-AGENT-CANONICAL` | C-03 | Intégration de `jarvis_agent.py` aux primitives verrouillées | Appel de `agent.remember("agent_pref", "iron_man_theme")` | Donnée sauvée via `main2.sauvegarder_memoire` | Donnée persistée correctement | **PASS** |

---

## 4. SUITE 4 : VÉRIFICATION PHYSIQUE HOME ASSISTANT (CONDITION C-04)

| Test ID | Condition | Scénario Domotique | Simulation Home Assistant | Comportement Attendu | Message Vocal Constaté | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `C04-LIGHT-STATE-VERIFIED` | C-04 | Allumage salon réussi matériellement | HTTP 200 service, puis `/api/states` renvoie `state: on` | Confirmation vocale explicite avec état matériel vérifié | *"C'est fait, lumière salon allumée. État matériel vérifié."* | **PASS** |
| `C04-LIGHT-PHYSICAL-FAIL` | C-04 | Allumage salon : service accepté mais ampoule physiquement coupée | HTTP 200 service, mais `/api/states` renvoie toujours `state: off` | Alerte utilisateur sur l'échec physique sans mentir | *"Attention : l'ordre a été envoyé à Home Assistant, mais l'appareil salon signale toujours l'état : off."* | **PASS** |
| `C04-LIGHT-STATE-UNKNOWN` | C-04 | Allumage salon : ampoule injoignable ou état indisponible | HTTP 200 service, mais `/api/states` renvoie `state: unavailable` | Notification d'état réel indéterminé | *"L'ordre pour la lumière de salon a été transmis, mais l'état réel de l'ampoule reste indéterminé."* | **PASS** |
| `C04-LIGHT-HTTP-500` | C-04 | Erreur 500 sur l'appel REST Home Assistant | HTTP 500 renvoyé par le service HA | Notification immédiate d'échec de la commande | *"Impossible d'actionner la lumière de salon : la commande Home Assistant a échoué ou l'appareil est injoignable."* | **PASS** |
| `C04-PLUG-STATE-VERIFIED` | C-04 | Activation de prise avec vérification physique | HTTP 200 service, puis `/api/states` renvoie `state: on` | Confirmation explicite d'activation matérielle | *"Prise bureau activée. État matériel vérifié."* | **PASS** |
| `C04-PLUG-PHYSICAL-FAIL` | C-04 | Activation de prise : refus ou équipement bloqué sur off | HTTP 200 service, mais `/api/states` renvoie `state: off` | Avertissement d'état inchangé | *"Attention : l'ordre a été envoyé pour la prise bureau, mais l'équipement signale toujours l'état : off."* | **PASS** |

---

## 5. SUITE 5 : RENFORCEMENT AST ET ANALYSE STATIQUE (SEC-01)

| Test ID | Condition | Snippet Python soumis | Analyse Statique AST | Statut de Sécurité | Exécution Hôte | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `SEC01-AST-OPEN-REJECTED` | SEC-01 | `f = open('secrets.txt', 'r')` | Rejeté (`open` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-INPUT-REJECTED` | SEC-01 | `x = input('password:')` | Rejeté (`input` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-DANGER-exec` | SEC-01 | `exec('a=1')` | Rejeté (`exec` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-DANGER-eval` | SEC-01 | `eval('2+2')` | Rejeté (`eval` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-DANGER-os` | SEC-01 | `import os; os.system('dir')` | Rejeté (module `os` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-DANGER-subp` | SEC-01 | `import subprocess` | Rejeté (`subprocess` interdit) | `REJECTED_UNSAFE_OR_INVALID` | Bloquée | **PASS** |
| `SEC01-AST-SAFE-VALIDATED` | SEC-01 | `def add(a, b): return a + b\ny = add(2, 3)` | Validé syntaxiquement | `SECURE_STATIC_VERIFIED` | N/A | **PASS** |
| `SEC01-EXECUTION-DISABLED` | SEC-01 | Code mathématique valide | N/A | Invariant strict vérifié | `DISABLED_FOR_SECURITY` | **PASS** |

---

## 6. VALIDATION FORENSIQUE DES GAPS ANTÉRIEURS

L'audit contradictoire précédent `ALICE-P0-INDEPENDENT-ACCEPTANCE-003` avait isolé deux défauts spécifiques :
1. **Échec précédent sur le port `99999` :**
   - *Ancien comportement :* Accepté car l'expression régulière précédente ne validait pas la plage numérique du port.
   - *Nouveau comportement testé (`C02-ORIGIN-08`) :* `is_origin_allowed("http://127.0.0.1:99999")` renvoie **`False`**. Validé !
2. **Échec précédent sur l'AST `open()` :**
   - *Ancien comportement :* Validé par l'AST car `open` ne figurait pas dans `DANGEROUS_BUILTINS`.
   - *Nouveau comportement testé (`SEC01-AST-OPEN-REJECTED`) :* `verifier_code_boucle("f = open('secrets.txt', 'r')")` renvoie **`REJECTED_UNSAFE_OR_INVALID`**. Validé !

---
**Fichier de preuve JSON :** `scratch/remediation_003_test_results.json`  
**Certification :** 100% des tests automatisés de remédiation 003 sont vérifiés et reproductibles.
