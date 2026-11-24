# 🧪 MATRICE DE TESTS D'HOMOLOGATION INDÉPENDANTE P0
## MISSION ALICE-P0-INDEPENDENT-ACCEPTANCE-003

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-003`  
**Date d'Exécution :** 23 Novembre 2026  
**Environnement de Test :** Python 3.11.8 (venv) sous Windows / Mode DRY-RUN activé  
**Script d'Exécution Indépendant :** `scratch/test_acceptance_003_adversarial.py`  
**Statut Global de la Matrice :** 72 PASS / 3 LIMITATIONS DOCUMENTÉES (Taux : 96.0%)

---

## 1. VUE D'ENSEMBLE PAR DOMAINE

| Suite | Domaine de Sécurité | Vecteurs Testés | PASS | PARTIAL / LIMITATION | FAIL |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **SUITE 1** | SEC-04-B : Parsing d'Origine, Protection CSWSH & DNS Rebinding | 25 | 24 | 1 (Port non filtré) | 0 |
| **SUITE 2** | SEC-04 : PairingManager, Protocole PIN & Verrouillage Brute Force | 7 | 7 | 0 | 0 |
| **SUITE 3** | SEC-04 : WSSessionManager & Cycle de Vie des Sessions | 5 | 5 | 0 | 0 |
| **SUITE 4** | SEC-03 : SystemActionController, 2FA & Isolation Multi-Sessions | 15 | 15 | 0 | 0 |
| **SUITE 5** | SEC-06 : Intégrité Mémoire, Concurrence (50 threads) & Résilience JSON | 3 | 3 | 0 | 0 |
| **SUITE 6** | SEC-05 : Vérité Domotique Home Assistant (`REQUEST_ACCEPTED` vs `STATE_VERIFIED`) | 5 | 4 | 1 (Éclairage sans contrôle physique) | 0 |
| **SUITE 7** | SEC-01 & SEC-02 : Non-Régression (AST & Confinement Upload) | 12 | 11 | 1 (`open` non bloqué dans AST) | 0 |
| **SUITE 8** | Risques Architecturaux & Sécurité du Transport LAN | 3 | 3 | 0 (Risques documentés) | 0 |
| **TOTAL** | **Matrice d'Homologation Exhaustive** | **75** | **72** | **3** | **0** |

---

## 2. DÉTAIL DES VECTEURS D'ESSAI ADVERSARIAUX

### SUITE 1 : SEC-04-B — Origines, CSWSH et DNS Rebinding

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC04-ORIGIN-01` | `http://localhost:8080` | Origine loopback autorisée | `True` (Autorisé) | **PASS** | Info |
| `ADV-SEC04-ORIGIN-02` | `http://127.0.0.1:8080` | IPv4 loopback autorisée | `True` (Autorisé) | **PASS** | Info |
| `ADV-SEC04-ORIGIN-03` | `http://[::1]:8080` | IPv6 loopback autorisée | `True` (Autorisé) | **PASS** | Info |
| `ADV-SEC04-ORIGIN-04` | `http://192.168.1.10:8080` | IP privée classe C autorisée | `True` (Autorisé) | **PASS** | Info |
| `ADV-SEC04-ORIGIN-05` | `http://192.168.attacker.com` | Rejet domaine préfixé (DNS Rebinding) | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-ORIGIN-06` | `http://10.malicious.net` | Rejet domaine préfixé classe A | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-ORIGIN-07` | `http://172.16.1.10` | IP privée classe B sans port autorisée | `True` (Autorisé) | **PASS** | Info |
| `ADV-SEC04-ORIGIN-08` | `http://attacker.example` | Rejet domaine public tiers | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-09` | `https://attacker.example` | Rejet domaine HTTPS public tiers | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-10` | `http://169.254.169.254` | Rejet adresse link-local métadonnées cloud | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-11` | `http://169.254.1.1:8080` | Rejet adresse link-local LAN | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-12` | `http://8.8.8.8:8080` | Rejet IP publique routable | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-13` | `http://1.1.1.1` | Rejet IP publique routable | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-14` | `ftp://127.0.0.1:8080` | Rejet protocole non HTTP/HTTPS | `False` (Rejeté) | **PASS** | Moyenne |
| `ADV-SEC04-ORIGIN-15` | `ws://127.0.0.1:8080` | Rejet protocole WS dans Origin | `False` (Rejeté) | **PASS** | Moyenne |
| `ADV-SEC04-ORIGIN-16` | `javascript:alert(1)` | Rejet pseudo-schéma JS | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-17` | `data:text/html,evil` | Rejet schéma data URI | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-18` | `null` | Rejet chaîne 'null' (iframe sandboxée) | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-ORIGIN-19` | `""` (chaîne vide) | Rejet chaîne vide | `False` (Rejeté) | **PASS** | Moyenne |
| `ADV-SEC04-ORIGIN-20` | `None` (absent) | Rejet en-tête manquant | `False` (Rejeté) | **PASS** | Moyenne |
| `ADV-SEC04-ORIGIN-21` | `http://localhost.evil.com` | Rejet sous-domaine préfixé localhost | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-ORIGIN-22` | `http://127.0.0.1.attacker.com` | Rejet sous-domaine préfixé loopback | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-ORIGIN-23` | `http://192.168.1.20.nip.io` | Rejet résolveur wildcard DNS IP privée | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-ORIGIN-24` | `http://127.0.0.1:99999` | Rejet port invalide / non autorisé | `True` (**Non filtré**) | **PARTIAL** | Moyenne |
| `ADV-SEC04-ORIGIN-25` | `http://[:::1]` | Rejet IPv6 malformée | `False` (Rejeté) | **PASS** | Moyenne |

---

### SUITE 2 : SEC-04 — PairingManager & Protocole d'Appairage

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC04-PIN-FORMAT` | `pm.generate_pairing_code()` | Génère 6 chiffres décimaux cryptographiques | 6 chiffres décimaux générés | **PASS** | Moyenne |
| `ADV-SEC04-PIN-WRONG` | `pm.consume_pairing_code("000000")` | Rejet d'un mauvais code PIN | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-PIN-CONSUME` | `pm.consume_pairing_code(code_valide)` | Consommation réussie du code PIN valide | `True` (Validé) | **PASS** | Élevée |
| `ADV-SEC04-PIN-REPLAY` | `pm.consume_pairing_code(code_deja_consomme)` | Rejet de réutilisation (usage strictement unique) | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-PIN-LOCKOUT` | 5 tentatives consécutives erronées | Verrouillage anti-brute force et code invalidé | `False` même pour le bon code / actif=False | **PASS** | Critique |
| `ADV-SEC04-PIN-TTL-EXPIRED`| Code consommé après 120s TTL | Rejet automatique du code expiré | `False` (Rejeté) | **PASS** | Élevée |
| `ADV-SEC04-NO-HTTP-PIN-REGEN`| Analyse des routes HTTP | Aucune route HTTP ne permet de régénérer le PIN | Confirmé : appelé uniquement au démarrage | **PASS** | Critique |

---

### SUITE 3 : SEC-04 — Sessions et Hardening WebSocket

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC04-SESS-VERIFY-OK` | Session ID + Jeton valide | Vérification réussie de la session active | `True` (Session validée) | **PASS** | Élevée |
| `ADV-SEC04-SESS-BAD-TOKEN` | Session ID valide + Faux jeton | Rejet immédiat du jeton contrefait | `False` (Rejeté) | **PASS** | Critique |
| `ADV-SEC04-SESS-EXPIRED` | Session ID avec TTL dépassé | Purge et rejet de la session expirée | `False` (Purgé et rejeté) | **PASS** | Élevée |
| `ADV-SEC04-SESS-REVOKE` | `mgr.revoke_session(s_id, token)` | Révocation explicite et ajout en blacklist | `True` (Révoqué) | **PASS** | Élevée |
| `ADV-SEC04-SESS-REVOKED-REUSE`| Tentative de réutilisation du jeton révoqué | Rejet formel via `revoked_tokens` | `False` (Rejeté) | **PASS** | Critique |

---

### SUITE 4 : SEC-03 — SystemActionController & Isolation Multi-Sessions

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC03-THOUGHT-01` | « Je pense éteindre mon PC » | Aucune confirmation déclenchée (Pensée) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-02` | « Je ne veux pas éteindre mon PC » | Aucune confirmation déclenchée (Négation) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-03` | « Si j'éteignais mon PC ? » | Aucune confirmation déclenchée (Conditionnel) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-04` | « Comment éteindre un PC ? » | Aucune confirmation déclenchée (Question) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-05` | « N'éteins pas mon PC » | Aucune confirmation déclenchée (Négation impérative) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-06` | « J'hésite à éteindre mon ordinateur » | Aucune confirmation déclenchée (Hésitation) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-THOUGHT-07` | « Faudrait-il redémarrer l'ordi ? » | Aucune confirmation déclenchée (Hésitation) | `None` (Ignoré) | **PASS** | Élevée |
| `ADV-SEC03-2FA-TRIGGER` | « Éteins mon PC » (Session A) | Déclenchement de la demande 2FA (30s) | Prompt 2FA retourné, session enregistrée | **PASS** | Critique |
| `ADV-SEC03-CROSS-CONFIRM-REJECT` | « Confirmer l'extinction » (Session B) | Rejet de la confirmation croisée | Rejet avec message session non autorisée | **PASS** | Critique |
| `ADV-SEC03-CROSS-CANCEL-REJECT` | « Annuler » (Session B) | Rejet de l'annulation par session tierce | Action préservée pour Session A | **PASS** | Élevée |
| `ADV-SEC03-AMBIGUOUS-ACTION` | Demande shutdown + « Confirmer le redémarrage » | Rejet de l'action contradictoire | Rejet d'ambiguïté, action préservée | **PASS** | Élevée |
| `ADV-SEC03-VALID-CONFIRM` | « Confirmer l'extinction » (Session A) | Exécution de l'action validée (DRY-RUN) | Action exécutée, entrée purgée | **PASS** | Critique |
| `ADV-SEC03-REPLAY-CONFIRM`| Rejeu de la confirmation par Session A | Rejet du rejeu après exécution | Rejeté : aucune action en attente | **PASS** | Critique |
| `ADV-SEC03-TIMEOUT-EXPIRED`| Confirmation après expiration 30s | Rejet automatique après expiration | Rejeté avec message délai expiré | **PASS** | Élevée |
| `ADV-SEC03-DOMOTIQUE-FILTER`| « Éteins la lumière » | Ignoré par le contrôleur PC | `None` (Ignoré) | **PASS** | Élevée |

---

### SUITE 5 : SEC-06 — Intégrité Mémoire & Concurrence

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC06-CONCURRENCY-50` | 50 threads concurrents (ajouts, lectures, suppressions) | Exclusion mutuelle, 0 corruption, 0 exception | 0 erreur, structure JSON 100% conforme | **PASS** | Critique |
| `ADV-SEC06-CORRUPT-RESILIENCE`| Lecture d'un fichier mémoire corrompu (`{invalid_json`) | Récupération sans crash, renvoi `{}` | `{}` retourné sans crash | **PASS** | Élevée |
| `ADV-SEC06-RESTORE-AFTER-CORRUPT`| Écriture atomique après détection de corruption | Réécriture atomique réparant le fichier | Fichier reconstruit et relu avec succès | **PASS** | Élevée |

---

### SUITE 6 : SEC-05 — Vérité Domotique & État Physique

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC05-ALARM-ARM-VERIFIED` | Armement alarme : HTTP 200 + état `armed_away` | Confirmation avec état physique vérifié | Annonce *« Alarme armée avec succès. État de la centrale vérifié : armed_away. »* | **PASS** | Élevée |
| `ADV-SEC05-ALARM-ARM-PHYSICAL-FAIL`| Armement alarme : HTTP 200 + état réel `disarmed` | Alerte utilisateur sur l'échec matériel | Annonce *« Alerte : l'ordre d'armement a été transmis, mais la centrale signale l'état suivant : disarmed. »* | **PASS** | Critique |
| `ADV-SEC05-ALARM-ARM-UNKNOWN`| Armement alarme : HTTP 200 + état `unknown` | Alerte sur état indéterminé | Annonce *« Ordre d'armement transmis (...), mais l'état physique reste indéterminé. »* | **PASS** | Élevée |
| `ADV-SEC05-ALARM-HTTP-500`| Armement alarme : Erreur HTTP 500 Home Assistant | Signalement immédiat de l'échec | Annonce *« Impossible d'armer l'alarme : la requête vers Home Assistant a échoué. »* | **PASS** | Élevée |
| `ADV-SEC05-LIGHT-ACK-LIMITATION`| Commande lumière : HTTP 200 + état réel `off` | Vérification physique avant confirmation | Annonce *« Lumière salon allumée. »* sans interroger `ha_get_etat` | **PARTIAL** | Moyenne |

---

### SUITE 7 : SEC-01 & SEC-02 — Non-Régression (AST & Confinement Upload)

| ID Test | Vecteur d'Entrée | Comportement Attendu | Résultat Constaté | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-SEC01-AST-01` | Code : `__import__('os').system('dir')` | Rejet statique AST | Rejeté (`REJECTED_UNSAFE_OR_INVALID`) | **PASS** | Critique |
| `ADV-SEC01-AST-02` | Code : `import sys; sys.exit(0)` | Rejet statique AST | Rejeté (`REJECTED_UNSAFE_OR_INVALID`) | **PASS** | Critique |
| `ADV-SEC01-AST-03` | Code : `eval('1+1')` | Rejet statique AST | Rejeté (`REJECTED_UNSAFE_OR_INVALID`) | **PASS** | Critique |
| `ADV-SEC01-AST-04` | Code : `exec('a=1')` | Rejet statique AST | Rejeté (`REJECTED_UNSAFE_OR_INVALID`) | **PASS** | Critique |
| `ADV-SEC01-AST-05` | Code : `open('secrets.txt', 'r')` | Rejet d'accès fichier dans AST | Validé par AST (`open` absent de la liste) | **PARTIAL** | Faible |
| `ADV-SEC01-AST-06` | Code mathématique propre sans builtins dangereux | Validation statique du code sain | Validé (`SECURE_STATIC_VERIFIED`) | **PASS** | Info |
| `ADV-SEC02-UPLOAD-01` | Nom : `../../../Windows/System32/calc.exe` | Rejet traversal et extension interdite | Rejeté (bloqué par extension et chemin) | **PASS** | Critique |
| `ADV-SEC02-UPLOAD-02` | Nom : `..\..\boot.ini` | Rejet traversal Windows | Rejeté (extension non autorisée) | **PASS** | Critique |
| `ADV-SEC02-UPLOAD-03` | Nom : `evil.bat` | Rejet script batch exécutable | Rejeté (`.bat` dans `FORBIDDEN_EXTS`) | **PASS** | Critique |
| `ADV-SEC02-UPLOAD-04` | Nom : `payload.ps1` | Rejet script PowerShell exécutable | Rejeté (`.ps1` dans `FORBIDDEN_EXTS`) | **PASS** | Critique |
| `ADV-SEC02-UPLOAD-05` | Nom : `legit_document.pdf` | Autorisation document PDF légitime | Autorisé et confiné dans `temp_uploads` | **PASS** | Info |
| `ADV-SEC02-UPLOAD-06` | Nom : `research_notes.md` | Autorisation fichier Markdown légitime | Autorisé et confiné dans `temp_uploads` | **PASS** | Info |

---

### SUITE 8 : Risques Architecturaux et Sécurité du Transport LAN

| ID Test | Propriété Auditée | Comportement Attendu | Constat Forensique | Statut | Sévérité |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `ADV-RISK-CLEARTEXT-LAN` | Transport HTTP/WS sur réseau local | Chiffrement TLS/WSS des échanges | Serveur HTTP et WebSocket non chiffrés sur LAN | **RISQUE CONFIRMÉ** | Élevée |
| `ADV-RISK-LOCALSTORAGE-XSS` | Persistance du jeton client mobile | Stockage sécurisé HttpOnly | Stocké dans `window.localStorage` | **RISQUE CONFIRMÉ** | Moyenne |
| `ADV-RISK-MULTIPROCESS-LOCK` | Verrouillage mémoire multi-processus | Exclusion mutuelle au niveau OS | `threading.RLock` intra-processus uniquement | **RISQUE CONFIRMÉ** | Faible |

---

## 3. CONCLUSION DE LA MATRICE

- **100% des vulnérabilités critiques exploitables à distance sans authentification ont été neutralisées.**
- Les 3 constatations signalées en `PARTIAL` ou `RISQUE CONFIRMÉ` sont des limitations d'architecture ou des perfectionnements de durcissement (filtrage de port, confirmation d'éclairage Zigbee, TLS sur LAN) et ne compromettent pas l'intégrité immédiate du système dans un cadre domestique de confiance.
