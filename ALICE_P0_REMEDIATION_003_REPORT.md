# 🛡️ ALICE — RAPPORT TECHNIQUE DE REMÉDIATION DE SÉCURITÉ P0-003
## CLÔTURE DES CONDITIONS CRITIQUES C-01 À C-04 : TLS/WSS, VALIDATION STRICTE D'ORIGINE, VERROUILLAGE MÉMOIRE ET VÉRITÉ DOMOTIQUE

- **Projet :** J.A.R.V.I.S / ALICE — SITE-V2
- **Mission ID :** `ALICE-P0-REMEDIATION-003`
- **Référence audit préalable :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-003`
- **Statut précédent de l'audit :** `CONDITIONALLY_APPROVED`
- **Décision de remédiation :** `REMEDIATION_COMPLETE_PENDING_INDEPENDENT_AUDIT`
- **Date d'exécution :** 23 novembre 2026
- **Branche Git :** `main`
- **HEAD Git au démarrage :** `f9c319557f4a02d8ddf5957505bde91c87947940`
- **Autorisation de déploiement / production :** AUCUNE (STRICTEMENT INTERDIT)

---

## 0. SYNTHÈSE EXÉCUTIVE ET DÉCISION PROVISOIRE

À la suite de la mission d'homologation indépendante `ALICE-P0-INDEPENDENT-ACCEPTANCE-003` qui avait émis un avis `CONDITIONALLY_APPROVED` en pointant quatre conditions suspensives d'architecture et de robustesse (C-01, C-02, C-03, C-04) ainsi qu'un ajustement AST sur SEC-01, la mission `ALICE-P0-REMEDIATION-003` a mis en œuvre l'intégralité des correctifs structurels requis.

### Bilan synthétique des 4 conditions et du renforcement SEC-01 :
1. **Condition C-01 (Transport sécurisé TLS / WSS) — CLÔTURÉE :**
   - Mise en place d'un modèle de transport cohérent : serveur HTTP et serveur WebSocket partagent la même politique TLS via `get_ssl_context()`.
   - Support des certificats locaux configurables par variables d'environnement (`ALICE_SSL_CERT`, `ALICE_SSL_KEY`).
   - Comportement *fail-closed* obligatoire en environnement de production (`ALICE_ENV=production` ou `production` : refus de démarrer sans TLS).
   - Gestion sécurisée des reverse-proxies : extraction de l'IP cliente (`get_trusted_client_ip()`) avec support de `X-Forwarded-For` uniquement en présence de proxys de confiance (`ALICE_TRUSTED_PROXIES`).
   - Alignement du client mobile ([app.js](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js)) : négociation dynamique `wss://` lorsque la page est chargée en `https://`.
2. **Condition C-02 (Validation stricte des origines et des ports) — CLÔTURÉE :**
   - Remplacement du parsing naïf par `urllib.parse.urlsplit` avec extraction normalisée du couple `(scheme, hostname, port)`.
   - Rejet systématique des vecteurs d'attaque : `userinfo` (`user:pass@host`), chemins d'URL (`/path`), fragments (`#hash`), requêtes (`?query`), points finals de domaine (`localhost.`), et ports hors de la plage `1..65535` (notamment le port `99999` qui avait échoué lors de l'audit 003).
   - Restriction des ports autorisés par environnement : en mode développement `{8080, 8443, 8765, 5173, 3000}` ; en mode production `{443, 8443}` (ou la liste explicite `ALICE_ALLOWED_ORIGINS`).
3. **Condition C-03 (Intégrité de la mémoire et exclusion des accès concurrents) — CLÔTURÉE :**
   - Implémentation de `CrossProcessMemoryLock` dans [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py), combinant un `threading.RLock()` réentrant au niveau applicatif et un verrou au niveau du noyau OS (`msvcrt.locking` sous Windows / `fcntl.flock` sous POSIX) avec gestion de timeout (5.0s par défaut).
   - Intégration du verrou à toutes les opérations canoniques : `charger_memoire`, `sauvegarder_memoire`, `ajouter_memoire`, `supprimer_memoire`.
   - Audit complet de [jarvis_agent.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/jarvis_agent.py) : élimination des écritures JSON directes et non verrouillées, délégation totale vers les primitives protégées de [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py), et correction de syntaxe préexistante.
4. **Condition C-04 (Vérification physique de l'état Home Assistant) — CLÔTURÉE :**
   - Généralisation du cycle en deux temps (Commande $\rightarrow$ Acquittement HTTP $\rightarrow$ Sondage de vérification physique `ha_verifier_changement_etat` $\rightarrow$ Confirmation vocale) aux modules `ha_lumiere` et `ha_interrupteur` (`ha_prise`).
   - Adoption du modèle unifié d'états : `HA_REQUEST_ACCEPTED`, `HA_STATE_VERIFIED`, `HA_FAILED`, `HA_STATE_UNKNOWN`, `HA_TIMEOUT`.
   - Rétroaction vocale honnête : si l'ampoule ou la prise reste physiquement éteinte (par exemple coupure matérielle ou interrupteur mural ouvert), ALICE informe explicitement l'utilisateur du déphasage au lieu d'affirmer un succès trompeur.
5. **Renforcement SEC-01 (Analyse statique AST) — CLÔTURÉ :**
   - Ajout explicite de `"open"` et `"input"` dans la liste `DANGEROUS_BUILTINS` d'[alice_modules.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/alice_modules.py). L'appel `open('secrets.txt', 'r')` est désormais intercepté et rejeté au niveau AST avec le statut `REJECTED_UNSAFE_OR_INVALID`, tout en maintenant l'invariance absolue `execution_status: "DISABLED_FOR_SECURITY"`.

**Résultats de validation :**
- Suite complète de remédiation 003 : **63 tests exécutés, 63 réussis (100.0%)**.
- Zéro régression sur les suites d'acceptation antérieures (les 2 échecs adversariaux de l'audit 003 sont résolus).

**Décision de sécurité :** `REMEDIATION_COMPLETE_PENDING_INDEPENDENT_AUDIT`.
Le système est prêt pour la mission d'homologation contradictoire indépendante `ALICE-P0-INDEPENDENT-ACCEPTANCE-004`.

---

## 1. BASELINE FORENSIQUE PRÉ-REMÉDIATION

### 1.1 Environnement et Git Baseline
- **Répertoire de travail :** `c:\Users\USER\Desktop\Jarvis Final - SITE-V2\Jarvis Final - SITE`
- **Branche active :** `main`
- **Commit HEAD :** `f9c319557f4a02d8ddf5957505bde91c87947940`
- **Sauvegarde externe réalisée avant modification :**
  `C:\Users\USER\.gemini\antigravity\brain\9f43747e-d272-4f9c-bf13-f2fb641773ea\backups\pre_remediation_003\`
  Contenant les copies exactes de [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py), [alice_modules.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/alice_modules.py), [app.js](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js), [index.html](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/index.html), et [jarvis_agent.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/jarvis_agent.py).

### 1.2 Cartographie des dépendances de `jarvis_agent.py`
Une analyse textuelle exhaustive du dépôt a été menée pour identifier tous les appelants de `jarvis_agent.py` :
- Aucun import de `jarvis_agent` n'existe dans `main2.py`, `alice_modules.py` ou l'interface mobile.
- La seule occurrence se trouve dans `install.bat`, qui utilisait un script de substitution pour personnaliser le nom de l'utilisateur.
- `jarvis_agent.py` représentait un prototype autonome datant d'avril 2026. Néanmoins, pour parer à tout risque d'invocation parallèle ou manuelle, ce fichier a été mis en conformité complète avec la couche de synchronisation mémoire de `main2.py`.

---

## 2. TRAITEMENT DE LA CONDITION C-01 : ARCHITECTURE TLS / WSS

### 2.1 Contexte et Risques Identifiés
L'audit 003 a mis en évidence le fait que le serveur HTTP (port 8080) et le serveur WebSocket (port 8765) fonctionnaient en texte clair sur le réseau local. Le code PIN d'appairage mobile et le jeton de session WebSocket transitaient ainsi sans chiffrement, exposant les communications à l'écoute clandestine sur le Wi-Fi.

### 2.2 Architecture Technique Mise en Œuvre
Dans [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) :
1. **Fonction `get_transport_security_mode()` :**
   Détermine le mode de sécurité actif en fonction de `ALICE_ENV` (`development` ou `production`) et de la présence des certificats configurés (`ALICE_SSL_CERT` et `ALICE_SSL_KEY`).
2. **Fonction `get_ssl_context()` :**
   Instancie un `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)` durci :
   - Désactivation obligatoire de SSLv2, SSLv3, TLSv1, TLSv1.1 (protocole TLSv1.2 ou TLSv1.3 requis).
   - Chargement des chaînes de certificats via `ssl_context.load_cert_chain(cert_path, key_path)`.
   - En environnement de production (`ALICE_ENV=production`), si les certificats sont introuvables ou invalides, le système **échoue immédiatement (fail-closed)** en levant une `RuntimeError` explicite interdisant tout repli vers le texte clair.
3. **Sécurisation du serveur WebSocket (`start_ws`) :**
   Le serveur `websockets.serve` intègre le paramètre `ssl=ssl_context`. Si le contexte SSL est actif, le serveur n'accepte que des connexions `wss://`.
4. **Sécurisation du serveur HTTP Mobile (`start_mobile_http_server`) :**
   Le socket du `ThreadingHTTPServer` est enveloppé via `ssl_context.wrap_socket(httpd.socket, server_side=True)`.
5. **Filtrage des en-têtes Reverse-Proxy (`get_trusted_client_ip`) :**
   L'en-tête `X-Forwarded-For` n'est pris en compte que si la connexion socket directe provient d'un hôte figurant dans `ALICE_TRUSTED_PROXIES` (par défaut `127.0.0.1`, `::1`). Tout client direct non approuvé se voit attribuer son IP socket réelle, prévenant l'usurpation d'adresse IP source.
6. **Mise à niveau dynamique du client Web Mobile :**
   Dans [app.js](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js) :
   ```javascript
   const isHttps = window.location.protocol === "https:";
   const wsProtocol = isHttps ? "wss:" : "ws:";
   const WS_URL = `${wsProtocol}//${window.location.hostname}:8765`;
   ```

---

## 3. TRAITEMENT DE LA CONDITION C-02 : VALIDATION STRICTE DES ORIGINES ET DES PORTS

### 3.1 Défaillances Précédentes et Vecteurs d'Attaque
Lors de l'audit 003, deux vecteurs contournaient la politique d'origine :
- L'origine `http://127.0.0.1:99999` était acceptée car l'ancien parser ne vérifiait pas la validité du port.
- Les domaines d'attaque tels que `http://192.168.attacker.com` ou `http://localhost.evil.com` nécessitaient une vérification structurelle absolue via un analyseur RFC 3986 formel.

### 3.2 Spécification et Implémentation du Correctif
La fonction `is_origin_allowed(origin: str) -> bool` de [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) a été entièrement réécrite :
1. **Analyse syntaxique stricte avec `urllib.parse.urlsplit` :**
   - Rejet si `parsed.path` n'est ni vide ni `"/"`.
   - Rejet si `parsed.query` ou `parsed.fragment` est présent.
   - Rejet si `parsed.username` ou `parsed.password` est présent (rejet absolu de `http://user:pass@host`).
2. **Validation des schémas :**
   - Seuls les schémas `http` et `https` sont autorisés. Les schémas `ftp`, `ws`, `javascript`, `data` sont immédiatement rejetés.
3. **Validation et filtrage strict des ports :**
   - Le port est converti en entier et doit obligatoirement être compris entre `1` et `65535`.
   - Tout port supérieur à 65535 (ex: `99999`), nul (`0`) ou négatif (`-80`) déclenche un rejet immédiat.
   - En mode développement, seuls les ports du système et de développement sont autorisés : `{8080, 8443, 8765, 5173, 3000}`. Tout autre port (ex: `9999`, `3001`, ou port implicite 80 si non configuré) est rejeté.
   - En mode production, seuls les ports sécurisés `{443, 8443}` (ou ceux spécifiés explicitement via `ALICE_ALLOWED_ORIGINS`) sont acceptés.
4. **Validation de l'hôte :**
   - Rejet des domaines se terminant par un point final (`localhost.`).
   - Rejet des domaines d'usurpation DNS (`192.168.attacker.com`, `10.evil.org`, `localhost.evil.com`).
   - Rejet strict des adresses de métadonnées cloud (`169.254.169.254`) et des adresses publiques routables (`8.8.8.8`).
   - Acceptation des hôtes de boucle locale (`localhost`, `127.0.0.1`, `::1`) et des adresses privées RFC 1918 uniquement si elles respectent la syntaxe IP exacte et le port autorisé.

---

## 4. TRAITEMENT DE LA CONDITION C-03 : INTÉGRITÉ MÉMOIRE ET VERROUILLAGE INTER-PROCESSUS

### 4.1 Vulnérabilité de Concurrence
Bien que `threading.RLock()` protégeait les threads internes du processus [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py), il n'offrait aucune protection contre les accès concurrents multiprocessus. Si un processus secondaire (par exemple un script utilitaire ou [jarvis_agent.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/jarvis_agent.py)) accédait simultanément à `jarvis_memoire.json`, une corruption de fichier JSON pouvait survenir.

### 4.2 Architecture du Verrou Inter-Processus `CrossProcessMemoryLock`
Une classe dédiée a été implémentée dans [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) :
- **Double niveau de protection :**
  - Verrou de thread réentrant (`threading.RLock`) pour sérialiser les appels au sein du même processus Python sans interblocage.
  - Verrou de fichier OS au niveau du noyau via un fichier dédié `jarvis_memoire.json.crossprocess.lock`.
- **Compatibilité multi-plateforme :**
  - Sous Windows : utilisation de `msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)` pour un verrouillage exclusif non bloquant avec boucle d'attente active et temporisation.
  - Sous Linux/macOS : utilisation de `fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)`.
- **Gestion du timeout et libération déterministe :**
  - Temporisation configurable (5.0s par défaut). Si le verrou ne peut être acquis, une exception `TimeoutError` est levée.
  - Compteur de réentrance par thread pour garantir que la libération du fichier OS n'intervient qu'au déverrouillage de la portée externe.
  - Libération garantie via le protocole gestionnaire de contexte (`with CROSS_PROCESS_MEMORY_LOCK:`).

### 4.3 Migration et Sécurisation de `jarvis_agent.py`
Les méthodes directes de manipulation de mémoire dans [jarvis_agent.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/jarvis_agent.py) ont été refactorisées pour déléguer intégralement aux primitives sécurisées de [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) :
- `_load_memory()` appelle `main2.charger_memoire()`.
- `_save_memory(memory)` appelle `main2.sauvegarder_memoire(memory)`.
- `remember(key, value)` appelle `main2.ajouter_memoire(key, value)`.
- `forget(key)` appelle `main2.supprimer_memoire(key)`.
- Correction de la coquille de syntaxe sur la chaîne multiligne ligne 102.

---

## 5. TRAITEMENT DE LA CONDITION C-04 : VÉRIFICATION D'ÉTAT PHYSIQUE HOME ASSISTANT

### 5.1 Problématique de l'Acquittement Trompeur
Avant la remédiation, les fonctions `ha_lumiere` et `ha_interrupteur` considéraient qu'un code HTTP 200 renvoyé par l'API REST Home Assistant suffisait pour affirmer à l'utilisateur que l'action avait réussi ("C'est fait, lumière allumée"). Si l'ampoule Zigbee était hors ligne ou coupée électriquement, l'utilisateur recevait une confirmation mensongère.

### 5.2 Implémentation du Cycle de Vérification en Deux Temps
Dans [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py) :
1. **Introduction des constantes d'état :**
   ```python
   HA_REQUEST_ACCEPTED = "REQUEST_ACCEPTED"
   HA_STATE_VERIFIED   = "STATE_VERIFIED"
   HA_STATE_UNKNOWN    = "STATE_UNKNOWN"
   HA_TIMEOUT          = "TIMEOUT"
   HA_FAILED           = "FAILED"
   ```
2. **Fonction de vérification `ha_verifier_changement_etat` :**
   - Attend un délai initial (0.4s) pour laisser le temps au bus domotique (Zigbee, Z-Wave, Wi-Fi) de commuter.
   - Interroge l'état matériel réel via l'endpoint `/api/states/<entity_id>`.
   - Effectue jusqu'à 3 tentatives de lecture espacées de 0.4s.
   - Renvoie `(HA_STATE_VERIFIED, etat_reel)` si l'état constaté coïncide avec l'état cible.
   - Renvoie `(HA_STATE_UNKNOWN, etat_reel)` si l'état est `unavailable` ou `unknown`.
   - Renvoie `(HA_TIMEOUT, etat_reel)` si l'appareil reste obstinément dans son état antérieur.
3. **Harmonisation de `ha_lumiere` et `ha_interrupteur` (`ha_prise`) :**
   - Les deux fonctions appellent le service Home Assistant, puis exécutent la vérification physique si la requête initiale est acceptée (HTTP 200).
   - Les dictionnaires de retour contiennent désormais le tuple complet : `{"status": "...", "physical_verified": True/False, "physical_state": "..."}`.
4. **Dialogue utilisateur transparent dans `traiter_reponse_ia` :**
   - État physique vérifié : *"C'est fait, lumière salon allumée. État matériel vérifié."*
   - État physique non changé : *"Attention : l'ordre a été envoyé à Home Assistant, mais l'appareil salon signale toujours l'état : off."*
   - État indisponible : *"L'ordre pour la lumière de salon a été transmis, mais l'état réel de l'ampoule reste indéterminé."*
   - Échec HTTP : *"Impossible d'actionner la lumière de salon : la commande Home Assistant a échoué ou l'appareil est injoignable."*

---

## 6. RENFORCEMENT SEC-01 : ANALYSE STATIQUE AST

### 6.1 Constat de l'Audit 003
L'audit 003 avait constaté que `hub.verifier_code_boucle("f = open('secrets.txt', 'r')", langage="python")` était accepté par l'AST (bien que son exécution sur l'hôte était strictement bloquée avec `execution_status: "DISABLED_FOR_SECURITY"`).

### 6.2 Traitement dans `alice_modules.py`
Dans [alice_modules.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/alice_modules.py), ligne 850 :
- Ajout de `"open"` et `"input"` dans l'ensemble `DANGEROUS_BUILTINS`.
- L'inspecteur d'AST détecte désormais tout appel statique à `open()` ou `input()` et rejette le script avec :
  - `safety_status = "REJECTED_UNSAFE_OR_INVALID"`
  - `success = False`
  - Message explicite : `"Utilisation d'une fonction interne interdite : open"`.

---

## 7. RÉSULTATS DES TESTS ET PREUVES EMPIRIQUES

Le banc de test exhaustif [test_remediation_003_comprehensive.py](file:///C:/Users/USER/.gemini/antigravity/brain/9f43747e-d272-4f9c-bf13-f2fb641773ea/scratch/test_remediation_003_comprehensive.py) a validé 63 scénarios ciblés.

| Suite de Tests | Périmètre | Nb Tests | Succès | Échecs | Taux de Réussite |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Suite 1** | Validation stricte des origines et des ports (C-02) | 39 | 39 | 0 | 100.0% |
| **Suite 2** | Architecture TLS / WSS & En-têtes Proxy (C-01) | 5 | 5 | 0 | 100.0% |
| **Suite 3** | Verrouillage mémoire inter-processus & audit agent (C-03) | 5 | 5 | 0 | 100.0% |
| **Suite 4** | Vérification physique de l'état Home Assistant (C-04) | 6 | 6 | 0 | 100.0% |
| **Suite 5** | Renforcement analyse statique AST & Invariant (SEC-01) | 8 | 8 | 0 | 100.0% |
| **TOTAL** | **Validation P0-003 Complète** | **63** | **63** | **0** | **100.0%** |

### Preuves d'exécution notables :
1. **Rejet du port 99999 :**
   ```text
   [PASS] C02-ORIGIN-08 | C-02 Origin Validation | Origin 'http://127.0.0.1:99999' -> Expected False, got False.
   ```
2. **Rejet de `open()` au niveau AST :**
   ```text
   [PASS] SEC01-AST-OPEN-REJECTED | SEC-01 AST Static Review | open() call is statically flagged and rejected -> Status: REJECTED_UNSAFE_OR_INVALID
   ```
3. **Sérialisation inter-processus démontrée :**
   ```text
   [PASS] C03-CROSS-PROCESS-BLOCKING | C-03 Cross-Process Lock | Lock blocks secondary process and respects timeout (TimeoutError raised)
   [PASS] C03-CROSS-PROCESS-RELEASE | C-03 Cross-Process Lock | Lock released automatically when child process exits
   ```
4. **Vérification d'état physique matériel :**
   ```text
   [PASS] C04-LIGHT-STATE-VERIFIED | C-04 Physical Verification | ha_lumiere confirms only after physical state verified -> Spoken: ["C'est fait, lumière salon allumée. État matériel vérifié."]
   [PASS] C04-LIGHT-PHYSICAL-FAIL | C-04 Physical Verification | ha_lumiere detects and warns when physical bulb remains 'off' despite HTTP 200 -> Spoken: ["Attention : l'ordre a été envoyé à Home Assistant, mais l'appareil salon signale toujours l'état : off."]
   ```

---

## 8. RISQUES RÉSIDUELS ET LIMITATIONS CONNUES

Bien que les quatre conditions aient été rigoureusement traitées dans le code, les aspects opérationnels suivants subsistent en environnement réel :
1. **Génération et Déploiement des Certificats TLS Locaux :**
   En développement sur réseau local résidentiel (ex: `192.168.1.x`), l'obtention de certificats TLS valides sans avertissement navigateur nécessite soit l'utilisation d'une autorité de certification locale (type `mkcert`), soit l'utilisation d'un nom de domaine avec challenge DNS (Let's Encrypt / DuckDNS). Un guide de configuration opérationnelle a été documenté pour les utilisateurs.
2. **Stockage du Jeton dans le LocalStorage :**
   Le jeton de session WebSocket sur le client mobile est persisté dans `localStorage` afin de survivre au rechargement de page. En cas de faille XSS sur le client mobile, ce jeton pourrait être extrait. Une migration future vers des cookies `HttpOnly; SameSite=Strict` adossés à une authentification de session HTTP est recommandée.
3. **Latence Domotique Réseau :**
   La vérification matérielle en deux temps introduit un délai incompressible de 400 à 1200 ms avant la réponse vocale d'ALICE, ce qui est nécessaire pour garantir la véracité physique mais peut être perçu par l'utilisateur comme un léger temps de latence.

---

## 9. RECOMMANDATIONS POUR L'AUDIT D'HOMOLOGATION 004

Il est recommandé à l'équipe d'audit indépendant de la mission `ALICE-P0-INDEPENDENT-ACCEPTANCE-004` de porter une attention particulière aux points suivants :
1. **Tests adversariaux sur le parser `urlsplit` :** Soumettre des origines avec des encodages punycode, des homoglyphes, des IPv6 tronquées, et des adresses à double point.
2. **Épreuve d'endurance multiprocessus :** Lancer simultanément 5 processus Python concurrents effectuant des écritures intensives dans `jarvis_memoire.json` pour éprouver la résistance du `CrossProcessMemoryLock`.
3. **Tests d'émulation réseau Home Assistant :** Vérifier le comportement en cas de micro-coupures de connexion pendant le sondage de vérification physique.

---
**Rédigé par :** Lead Security & Architecture Engineer  
**Statut de la décision :** `REMEDIATION_COMPLETE_PENDING_INDEPENDENT_AUDIT`  
**Prochaine étape :** Mandatement de l'audit contradictoire `ALICE-P0-INDEPENDENT-ACCEPTANCE-004`
