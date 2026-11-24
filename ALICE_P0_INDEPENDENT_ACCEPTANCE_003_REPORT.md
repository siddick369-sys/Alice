# 🛡️ RAPPORT D'HOMOLOGATION DE SÉCURITÉ INDÉPENDANTE P0
## CERTIFICATION FORENSIQUE, CONTRADICTOIRE ET ADVERSARIALE APRÈS REMÉDIATION 002

**Mission ID :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-003`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence Audit Précédent :** `ALICE-P0-INDEPENDENT-ACCEPTANCE-002` (Décision : `REJECTED`)  
**Mission de Remédiation Contrôlée :** `ALICE-P0-REMEDIATION-002` (Déclaré : `VALIDÉ 100%`)  
**Date du Rapport :** 23 Novembre 2026  
**Auditeur :** Principal Security Architect & Forensic Auditor (Rôle Indépendant)  
**Mode :** STRICT READ-ONLY / INDEPENDENT SECURITY ACCEPTANCE  
**Statut d'Homologation :** **CONDITIONALLY_APPROVED** (Homologation Conditionnelle avec Registre de Risques Résiduels)

---

## 1. MANDAT ET POSTURE D'AUDIT INDÉPENDANT

Le présent rapport constitue l'homologation contradictoire et forensique de niveau P0 faisant suite à la mission de remédiation `ALICE-P0-REMEDIATION-002`.

L'auditeur indépendant a opéré sous mandat strict d'impartialité :
1. **Zéro confiance dans les déclarations d'auteur :** Les affirmations du rapport `ALICE_P0_REMEDIATION_002_REPORT.md` (66/66 tests réussis, 100%) n'ont pas été acceptées sans vérification de code et contre-épreuves indépendantes.
2. **Distinction formelle des niveaux de preuve :** Différenciation systématique entre :
   - Présence visuelle de code ;
   - Vérification statique ;
   - Test unitaire unithread ou isolé ;
   - Test d'intégration multi-sessions / multi-threads ;
   - Preuve de sécurité face à un comportement adversarial réel.
3. **Strict respect du mode lecture seule :** Aucun fichier source du projet (`main2.py`, `alice_modules.py`, `mobile/app.js`, `mobile/index.html`) n'a été modifié, reformaté ou altéré durant cette mission.
4. **Zéro action physique ou destructrice :** Aucun redémarrage/extinction OS réel n'a été exécuté (`JARVIS_DRY_RUN_SYSTEM_COMMANDS=1`), aucun paquet n'a été transmis à une centrale domotique physique, et aucun secret n'a été divulgué.

---

## 2. BASE FORENSIQUE ET INTÉGRITÉ DU DÉPÔT

### 2.1 État Git et Traçabilité
- **Répertoire de travail :** `c:\Users\USER\Desktop\Jarvis Final - SITE-V2`
- **Branche :** `main`
- **HEAD Git :** `f9c319557f4a02d8ddf5957505bde91c87947940` (Message : *Add Alice & Jarvis complete source code*)
- **Statut Git (`git status --short`) :**
  ```text
  M "Jarvis Final - SITE/alice_modules.py"
  M "Jarvis Final - SITE/main2.py"
  M "Jarvis Final - SITE/mobile/app.js"
  M "Jarvis Final - SITE/mobile/index.html"
  ```
- **Volumétrie des modifications non commitées (`git diff --stat`) :**
  - `alice_modules.py` : 204 lignes modifiées
  - `main2.py` : 927 lignes modifiées
  - `mobile/app.js` : 126 lignes modifiées
  - `mobile/index.html` : 13 lignes modifiées

### 2.2 Empreintes Cryptographiques des Fichiers Critiques (SHA-256)

| Fichier Audité | Empreinte SHA-256 | Taille (octets) | Rôle |
| :--- | :--- | :--- | :--- |
| `Jarvis Final - SITE/main2.py` | `F9AA702943625D3E7EF050A628082CC324ABB6C50485E9E59CB270A8CA57F9FB` | 207 519 | Serveur principal, WebSocket, HTTP, Sessions, Actions PC, Mémoire |
| `Jarvis Final - SITE/alice_modules.py` | `711C697BB5F0C03B3D46FD35B0515229D21CB15370C601A05CB718B88BCAA536` | 56 143 | Modules ALICE, Analyse AST, Confinement d'exécution |
| `Jarvis Final - SITE/mobile/app.js` | `DE7B9C3C11B61678AC577DEAAF38F8E27A57E158460D77057F2308C10D6D0783` | 18 379 | Client JavaScript mobile, gestion appairage et WebSocket |
| `Jarvis Final - SITE/mobile/index.html` | `4C7976C853282B7A3AD0DC318BE440A39DBCD6603FC52946B0D6942AB9B2C33C` | 5 358 | Interface HTML mobile avec modal d'appairage |
| `ALICE_P0_REMEDIATION_002_REPORT.md` | `2561E8E831B4BCA55BCDB8D3930A914D926E71B93137D22FFE8D402D2F54AB68` | 9 559 | Rapport de remédiation soumis au présent audit |

---

## 3. AUDIT CONTRADICTOIRE PAR DOMAINE DE SÉCURITÉ

### 3.1 SEC-04 : Authentification, Appairage et WebSocket

#### 3.1.1 Suppression de l'ancien endpoint `/api/auth/token`
- **Examen du code :** [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L4064-L4071)
  ```python
  if self.path == "/api/auth/token":
      self.send_response(410)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({"error": "Endpoint obsolète et supprimé pour des raisons de sécurité. Utilisez /api/pair."}).encode("utf-8"))
      return
  ```
- **Constat contradictoire :** L'ancien endpoint ne divulgue plus le jeton actif. Le code HTTP 410 Gone est systématiquement retourné. Aucun en-tête `Access-Control-Allow-Origin: *` n'est émis sur cette route.
- **Vérification d'endpoints alternatifs :** L'ensemble de `main2.py` a été scanné pour identifier toute route fournissant un jeton. Seul `POST /api/pair` délivre un jeton, subordonné à la consommation réussie d'un PIN valide.
- **Statut :** **PASS**.

#### 3.1.2 Protocole d'Appairage (`PairingManager`)
- **Examen du code :** [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L490-L536)
  - Génération de PIN : `secrets.randbelow(10)` répété 6 fois (entropie cryptographique standard).
  - Durée de validité : TTL de 120 secondes (`code_ttl = 120.0`).
  - Consommation : `hmac.compare_digest(self.active_pairing_code, code_attempt.strip())`.
  - Invalidation immédiate : `self.active_pairing_code = None` dès le premier succès (anti-rejeu).
  - Verrouillage anti-brute force : `self.failed_attempts >= 5` invalide définitivement le code (`self.active_pairing_code = None`).
- **Analyse contradictoire d'évasion (Reset du compteur de tentatives) :**
  - *Question d'audit :* Un attaquant peut-il réinitialiser `failed_attempts` en appelant un endpoint de régénération ?
  - *Preuve forensique :* `generate_pairing_code()` est appelé **exclusivement** à la ligne 4043 au démarrage du serveur HTTP mobile (`start_mobile_http_server`). **Aucune route HTTP** n'expose l'appel à `generate_pairing_code()`. L'endpoint `GET /api/pair/status` est strictement passif et ne renvoie que l'état d'activité et le temps restant.
  - *Conclusion :* Un attaquant distant ne peut pas réinitialiser le compteur de tentatives via HTTP. La surface d'attaque brute force est bornée à 5 essais sur 1 000 000 de combinaisons ($5 \times 10^{-6}$ probabilité de succès).
- **Statut :** **PASS**.

#### 3.1.3 Validation des Origines (`is_origin_allowed`) et Risque CSWSH
- **Examen du code :** [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L603-L629)
  - Rejet de `None`, chaîne vide et `"null"`.
  - Vérification du protocole : `parsed.scheme in ("http", "https")`.
  - Hôtes loopback admis : `"localhost"`, `"127.0.0.1"`, `"::1"`.
  - Hôtes distants : Conversion obligatoire par `ipaddress.ip_address(host)`.
  - Protection contre DNS Rebinding : Si l'origine est un nom de domaine (ex: `http://192.168.attacker.com`), `ipaddress.ip_address` lève un `ValueError` et l'origine est rejetée.
  - Protection Link-Local / Métadonnées Cloud : `(ip.is_private or ip.is_loopback) and not ip.is_link_local` rejette `http://169.254.169.254`.
- **Défauts et Limitations Découverts :**
  1. **Absence de contrôle du port :** Le code inspecte uniquement `parsed.hostname` et ignore `parsed.port`. Le test adversarial indépendant `ADV-SEC04-ORIGIN-24` (`http://127.0.0.1:99999`) a retourné `True` au lieu de `False`. Tout port anormal (ex: 99999, ou un service web malveillant tournant sur le port 3000 de la machine) est validé par le parser d'origine.
  2. **Allowlist non configurable :** Toute adresse IP privée (`192.168.x.x`, `10.x.x.x`, `172.16.x.x`) est admise comme origine sans allowlist d'hôtes ou de ports prédéfinis.
- **Atténuation constatée :** Même si l'origine d'un serveur tiers sur le réseau local est acceptée par `is_origin_allowed`, le handler WebSocket (`ws_handler`, lignes 680-703) impose une authentification par poignée de main avec `session_id` et `token` dans les 5 secondes. Sans le jeton issu du PIN d'appairage, la connexion est fermée avec le code `4001`.
- **Statut :** **PARTIAL** (Défaut de validation de port documenté).

#### 3.1.4 Client Mobile (`mobile/app.js` et `mobile/index.html`)
- **Examen du code :** [app.js](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/mobile/app.js#L130-L290)
  - Modal d'appairage : Affiché automatiquement si `jarvis_session_id` ou `jarvis_session_token` est absent du `localStorage`.
  - Poignée de main WS : Dès `open`, envoi immédiat de `{"type": "auth", "session_id": ..., "token": ...}`.
  - Gestion des erreurs et boucle infinie : Lors de la réception de `auth_error` ou d'une fermeture avec code `4001` ou `4003`, le client purge immédiatement le `localStorage` (`removeItem`), stoppe toute tentative de reconnexion et affiche le message explicatif dans le modal.
  - Fermeture / Réouverture : Les identifiants stockés dans `localStorage` permettent la reconnexion automatique sans redemander le PIN tant que la session est valide côté serveur.
- **Risque Résiduel Client :** Le jeton de session est stocké dans le `localStorage` du navigateur. En cas de vulnérabilité XSS injectée dans le client web mobile, le jeton pourrait être extrait via JavaScript (voir section Risques Résiduels).
- **Statut :** **PASS**.

#### 3.1.5 Sécurité du Transport Réseau (LAN en Clair)
- **Constat forensique :** Le serveur HTTP mobile ([main2.py:4155](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L4155)) est instancié via `http.server.HTTPServer(("0.0.0.0", 8080), MobileHandler)` sans `ssl.SSLContext`. Le serveur WebSocket écoute sur `ws://` (port 8765) sans couche TLS/WSS.
- **Conséquence :** Sur un réseau Wi-Fi local non chiffré ou partagé, le code PIN à 6 chiffres et les jetons de session transitent en clair. Un tiers pratiquant une écoute passive (promiscuous mode) ou un empoisonnement ARP peut intercepter le PIN ou le jeton de session.
- **Statut :** **RISQUE RÉSIDUEL DOCUMENTÉ (HIGH)**.

---

### 3.2 SEC-06 : Intégrité et Concurrence de la Mémoire Persistante

#### 3.2.1 Références et Unification des Écritures
- **Examen exhaustif du dépôt :**
  - Dans `main2.py` : L'intégralité des fonctions de manipulation de la mémoire (`charger_memoire`, `sauvegarder_memoire`, `ajouter_memoire`, `supprimer_memoire`, `memory_add`, `memory_forget`, `charger_contexte_rag`) pointe rigoureusement sur le chemin absolu `MEMOIRE_FILE` ([main2.py:173](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L173)) et acquiert systématiquement le verrou réentrant `MEMOIRE_LOCK = threading.RLock()`.
  - Les anciennes fonctions vulnérables `memory_add` ([main2.py:2237](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L2237)) et `memory_forget` ([main2.py:2245](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L2245)) délèguent sans exception à `ajouter_memoire` et `supprimer_memoire`.
  - Écriture atomique : `sauvegarder_memoire` ([main2.py:194-210](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L194-L210)) écrit dans un fichier temporaire unique (`temp_file = f"{MEMOIRE_FILE}.{os.getpid()}_{time.time_ns()}.tmp"`), exécute `f.flush()`, force l'écriture disque avec `os.fsync(f.fileno())`, et remplace le fichier cible via l'opération atomique OS `os.replace`.
- **Découverte Forensique Hors-Flux :** Le script `Jarvis Final - SITE/jarvis_agent.py` (scaffold autonome datant d'avril 2026, non importé par `main2.py`) contient des méthodes `_load_memory` et `_save_memory` manipulant `jarvis_memoire.json` sans verrou et sans écriture atomique. Bien que ce module ne soit pas actif dans l'exécution de `main2.py`, son existence dans l'arbre source représente un risque en cas d'exécution manuelle.
- **Test de Concurrence Adversariale Lourd (Scénario D) :**
  - Exécution de 50 threads concurrents exécutant simultanément des ajouts, des lectures et des suppressions.
  - Résultat : 0 exception, 0 perte de données, 0 corruption JSON, structure finale parfaitement intègre.
  - Test de tolérance aux pannes : Injection intentionnelle de JSON tronqué/corrompu dans le fichier mémoire. `charger_memoire()` intercepte l'erreur sans crasher et retourne `{}`. L'écriture ultérieure via `sauvegarder_memoire()` répare et réinitialise un JSON valide.
- **Évaluation Multi-Processus :** `threading.RLock` garantit l'exclusion mutuelle uniquement entre les threads d'un même processus Python. Si deux processus distincts tentaient d'exécuter `main2.py`, un verrou inter-processus OS (`portalocker` ou `msvcrt.locking`) serait nécessaire.
- **Statut :** **PASS** (au périmètre multi-threads de `main2.py`, limitation multi-processus documentée).

---

### 3.3 SEC-03 : Isolation et Confirmation des Actions Système

#### 3.3.1 Isolation Multi-Sessions (`SystemActionController`)
- **Examen du code :** [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L1960-L2118)
  - `self.pending_actions: Dict[str, Dict[str, Any]]` indexe chaque demande d'extinction/redémarrage par `session_id`.
  - Rejet de la confirmation croisée ([main2.py:2028-2033](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L2028-L2033)) : Si la session B tente d'émettre `"confirmer l'extinction"` alors qu'une action est en attente pour la session A, le contrôleur rejette catégoriquement la tentative (`"Action non autorisée : la confirmation d'extinction doit provenir de la même session que la demande initiale."`) et trace un événement audit `CROSS_SESSION_ATTEMPT`.
  - Expiration effective : TTL de 30 secondes vérifié à chaque confirmation. Au-delà, l'action est supprimée avec trace `ACTION_EXPIRED`.
  - Usage unique : L'entrée est purgée du dictionnaire dès confirmation (`del self.pending_actions[session_id]`). Le rejeu immédiat de la confirmation est rejeté.
  - Désambiguïsation d'action : Si l'action en attente est `shutdown` et que l'utilisateur dit `"confirmer le redémarrage"`, la confirmation est refusée et l'action d'extinction reste préservée en attente.

#### 3.3.2 Filtrage Linguistique et Faux Positifs
- **Méthodes auditées :** `is_thought_or_conditional`, `is_negation`, `is_domotique_intent`.
- **Résultats des vecteurs d'attaque linguistique :**
  - `« Je pense éteindre mon PC »` -> **Ignoré (None)** (Filtre pensée).
  - `« J'hésite à éteindre mon ordinateur »` -> **Ignoré (None)** (Filtre hésitation).
  - `« Si j'éteignais mon PC ? »` -> **Ignoré (None)** (Filtre conditionnel).
  - `« Comment éteindre un PC ? »` -> **Ignoré (None)** (Filtre interrogatif).
  - `« N'éteins pas mon PC »` -> **Ignoré (None)** (Filtre négation).
  - `« Éteins la lumière du salon »` -> **Ignoré (None)** (Filtre domotique).
  - `« Éteins mon PC »` -> **Déclenchement 2FA explicite** (Demande de confirmation 30s).
- **Statut :** **PASS**.

---

### 3.4 SEC-05 : Vérité Opérationnelle et Vérification d'État Home Assistant

#### 3.4.1 Distinguo Fondamental : `REQUEST_ACCEPTED` vs `STATE_VERIFIED`
Le rapport de remédiation 002 affirmait avoir éliminé les confirmations mensongères en distinguant acceptation de commande et état vérifié. L'audit indépendant a procédé à l'analyse différentielle de toutes les entités domotiques dans [main2.py](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L3170-L3300).

#### 3.4.2 Alarme (`ha_alarme`) : Implantation Conforme
- Lignes [3258-3286](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L3258-L3286) :
  1. Appel du service HA `ha_appeler_service("alarm_control_panel", ...)`.
  2. En cas de retour 200, ALICE interroge **immédiatement l'état physique réel** via `ha_get_etat("alarm_control_panel.home_base_2")`.
  3. Si l'état physique retourné correspond (`armed_away`, `armed_home`, `disarmed`), ALICE confirme la réussite avec l'état exact.
  4. Si l'état physique reste `unknown`/`inconnu`, ALICE alerte : *« Ordre d'armement transmis à Home Assistant, mais l'état physique de la centrale reste indéterminé. »*
  5. Si l'état physique contredit l'ordre (ex: centrale restée `disarmed`), ALICE signale l'alerte : *« Alerte : l'ordre d'armement a été transmis, mais la centrale signale l'état suivant : disarmed. »* (Validé par le test adversarial indépendant `ADV-SEC05-ALARM-ARM-PHYSICAL-FAIL`).

#### 3.4.3 Éclairages et Prises (`ha_lumiere`, `ha_prise`, `ha_thermostat`) : Limitation Identifiée
- Lignes [3172-3208](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L3172-L3208) :
  - `success = ha_lumiere(entity_id, etat, ...)`
  - Dans `ha_lumiere` ([main2.py:1413-1421](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L1413-L1421)), la fonction retourne la valeur booléenne de `ha_appeler_service`, qui correspond uniquement à `response.status_code == 200`.
  - **Constat contradictoire :** Dès que le bus Home Assistant renvoie HTTP 200, ALICE annonce vocalement : *« Lumière salon allumée. »* sans exécuter de lecture de contrôle `ha_get_etat(entity_id)` pour vérifier si l'ampoule Zigbee/Wi-Fi s'est effectivement allumée.
  - Le test adversarial indépendant `ADV-SEC05-LIGHT-ACK-LIMITATION` a confirmé qu'en forçant `ha_get_etat` à retourner `'off'` malgré un HTTP 200, ALICE confirme néanmoins l'allumage.
- **Évaluation :** Les confirmations aveugles sur erreur HTTP 500 ou crash ont bien été éliminées (l'échec de la requête est détecté), mais la vérification physique en deux temps (`REQUEST_ACCEPTED` vs `STATE_VERIFIED`) n'a été déployée que sur la centrale d'alarme et non sur l'éclairage/climatisation.
- **Statut :** **PARTIAL** (Défaut de vérification physique sur l'éclairage documenté).

---

### 3.5 SEC-01 & SEC-02 : Non-Régression

#### 3.5.1 SEC-01 : Neutralisation de l'Exécution Arbitraire de Code
- **Examen du code :** [alice_modules.py:838-960](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/alice_modules.py#L838-L960)
  - La fonction `verifier_code_boucle` n'exécute **plus aucun code** sur la machine hôte.
  - `execution_status: "DISABLED_FOR_SECURITY"` est systématiquement assigné.
  - Analyse statique AST : Détection des imports `os`, `sys`, `subprocess`, etc., et des builtins `exec`, `eval`, `__import__`, `compile`, `breakpoint`.
  - *Observation d'audit :* La liste `DANGEROUS_BUILTINS` ne contient pas la fonction `open`. Le test unitaire `ADV-SEC01-AST-05` (`open('secrets.txt')`) a donc été classé valide sur le plan statique. Toutefois, comme le code n'est **jamais exécuté**, aucun impact direct d'exécution arbitraire n'en découle.
- **Statut :** **PASS**.

#### 3.5.2 SEC-02 : Confinement des Téléversements et Path Traversal
- **Examen du code :** [main2.py:749-838](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/Jarvis%20Final%20-%20SITE/main2.py#L749-L838)
  - Nettoyage du nom de fichier : `clean_name = os.path.basename(raw_filename.replace("\\", "/"))`.
  - Whitelist stricte d'extensions autorisées (`ALLOWED_EXTS`) et blacklist explicite d'exécutables (`FORBIDDEN_EXTS`).
  - Stockage sous identifiant aléatoire imprévisible : `f"{uuid.uuid4().hex}_{safe_filename}"`.
  - Confinement canonique absolu : `os.path.realpath(file_path).startswith(os.path.realpath(temp_dir) + os.sep)`.
  - Limitation de taille : 15 Mo en base64, 10 Mo décodé.
- **Statut :** **PASS**.

---

## 4. AUDIT DE QUALITÉ DES 66 TESTS ANNONCÉS PAR LA MISSION 002

L'audit approfondi de `scratch/test_remediation_002_full.py` a révélé :
1. **Tests rigoureux et pertinents (55 tests) :** Les suites 1 (parsing d'origine IP/DNS rebinding), 2 (PairingManager), 3 (sessions), 4 (actions PC/2FA/filtres) et 6 (alarme vérifiée) testent directement le code de production et confirment les propriétés annoncées.
2. **Faiblesses et angles morts méthodologiques :**
   - **SEC-02 Confinement (Suite 7, 6 tests) :** Le test reproduit localement la formule de nettoyage dans une boucle de test sans traverser le handler WebSocket réel de `main2.py`.
   - **SEC-04 Validation d'Origine (Suite 1, 18 tests) :** Tous les tests appellent `is_origin_allowed(origin)` directement. Aucun ne teste l'impact d'un port invalide ou malformé (`:99999`).
   - **SEC-05 Domotique (Suite 6, 4 tests) :** Les tests ne portent que sur `ha_alarme`. Aucun test n'a été inclus pour `ha_lumiere` afin de vérifier si l'éclairage présentait la même garantie d'état physique.
3. **Reconstitution de l'historique d'échec initial :**
   - Les traces de l'exécution initiale révèlent que l'échec intermédiaire était dû à l'évaluation initiale de `169.254.169.254` (corrigée par l'ajout de `and not ip.is_link_local`), à la correspondance partielle de `"confirmer le redémarrage"` pour une extinction (corrigée par les vérifications de mots-clés conflictuels) et à un mock manquant de `demander_ia_stream`.
   - Aucun test n'a été frauduleusement supprimé pour forcer le résultat de 66/66.

---

## 5. RÉSULTATS DU BANC D'ESSAI ADVERSARIAL INDÉPENDANT 003

L'auditeur indépendant a développé et exécuté une suite d'homologation contradictoire (`scratch/test_acceptance_003_adversarial.py`) comportant **75 vecteurs d'évaluation** :

| Domaine Audité | Nombre de Vecteurs | Succès | Échecs / Limitations | Taux de Validation |
| :--- | :---: | :---: | :---: | :---: |
| **SEC-04-B : Origine & CSWSH** | 25 | 24 | 1 (Port non filtré) | **96.0%** |
| **SEC-04 : PairingManager & Anti-Brute Force** | 7 | 7 | 0 | **100.0%** |
| **SEC-04 : Sessions & Cycle de Vie** | 5 | 5 | 0 | **100.0%** |
| **SEC-03 : Actions PC & Isolation Multi-Sessions** | 15 | 15 | 0 | **100.0%** |
| **SEC-06 : Concurrence Mémoire (50 threads)** | 3 | 3 | 0 | **100.0%** |
| **SEC-05 : Vérité Domotique & État Physique** | 5 | 4 | 1 (Lumière sans confirmation physique) | **80.0%** |
| **SEC-01 & SEC-02 : Non-Régression (AST & Upload)** | 12 | 11 | 1 (`open` non interdit dans AST) | **91.7%** |
| **Risques Architecturaux & Transport** | 3 | 3 | 0 (Risques confirmés et documentés) | **100.0%** |
| **TOTAL GÉNÉRAL** | **75** | **72** | **3 (Limitations documentées)** | **96.0%** |

### Synthèse des Scénarios Combinés (Section 8 du Mandat)
- **Scénario A (Origine malveillante + client non authentifié) :** Connexion fermée avant authentification (Code 4003). -> **CONFORME**.
- **Scénario B (PIN expiré + reconnexion + réutilisation) :** PIN expiré rejeté (401), réutilisation rejetée (usage unique). -> **CONFORME**.
- **Scénario C (Deux sessions + confirmation croisée) :** Confirmation par la session tierce rejetée avec audit. -> **CONFORME**.
- **Scénario D (Concurrence mémoire 50 threads + lecture + suppression) :** Aucune corruption, JSON intègre. -> **CONFORME**.
- **Scénario E (Home Assistant 200 + centrale d'alarme désarmée) :** ALICE alerte l'utilisateur que l'état matériel est contradictoire. -> **CONFORME**.
- **Scénario F (Session révoquée + ancien jeton) :** Rejet immédiat via la blacklist `revoked_tokens` (Code 4001). -> **CONFORME**.
- **Scénario G (XSS + vol de jeton mobile) :** Vulnérabilité architecturale confirmée du `localStorage`. -> **RISQUE IDENTIFIÉ**.
- **Scénario H (Origine autorisée + IP inattendue / Origine interdite + IP privée) :** Validé, étanchéité de conversion IP. -> **CONFORME**.

---

## 6. REGISTRE DES DÉFAUTS CONFIRMÉS ET RISQUES RÉSIDUELS

### 6.1 Défaut DEF-01 : Validation Incomplète des Ports dans `is_origin_allowed`
- **Gravité :** MOYENNE (Medium / CVSS 4.3)
- **Fichier :** `Jarvis Final - SITE/main2.py`
- **Fonction :** `is_origin_allowed(self, origin)` (lignes 603-629)
- **Description :** La fonction extrait `host = parsed.hostname` et valide directement si l'hôte est local ou privé, sans vérifier `parsed.port`.
- **Scénario reproductible :** Un en-tête `Origin: http://127.0.0.1:99999` ou `http://192.168.1.50:3000` est accepté.
- **Impact :** Un service web non fiable tournant sur une machine autorisée mais sur un port arbitraire peut initier la poignée de main WebSocket. L'impact reste atténué par l'obligation de fournir un jeton de session valide sous 5s.
- **Recommandation :** Valider explicitement `parsed.port in (8080, 5173)` et restreindre à une allowlist stricte.

### 6.2 Défaut DEF-02 : Absence de Vérification d'État Physique sur les Éclairages (`ha_lumiere`)
- **Gravité :** FAIBLE à MOYENNE (Low-Medium / CVSS 3.7)
- **Fichier :** `Jarvis Final - SITE/main2.py`
- **Fonction :** `traiter_reponse_ia` (lignes 3179-3198) et `ha_lumiere` (lignes 1413-1421)
- **Description :** ALICE confirme l'allumage d'une pièce dès que l'API Home Assistant renvoie HTTP 200, sans interroger `ha_get_etat` pour vérifier l'état réel de l'ampoule.
- **Impact :** Si une ampoule Zigbee est hors tension physique (interrupteur mural éteint), Home Assistant accepte le service mais l'ampoule ne s'allume pas ; ALICE annonce faussement que la lumière est allumée.
- **Recommandation :** Généraliser le pattern à deux temps mis en place sur `ha_alarme` aux entités d'éclairage critiques.

### 6.3 Risque Résiduel RSK-01 : Transport Réseau en Clair (HTTP / WS sur LAN)
- **Gravité :** ÉLEVÉE (High / CVSS 7.1 sur réseau non de confiance)
- **Localisation :** `main2.py:4155` (HTTPServer) et `main2.py:640` (ws_handler)
- **Description :** Les communications LAN s'effectuent sans TLS/HTTPS et sans WSS.
- **Impact :** Écoute clandestine possible du code PIN d'appairage et du jeton de session sur un réseau Wi-Fi partagé.
- **Recommandation :** Imposer un certificat TLS (même auto-signé ou via reverse proxy Nginx/Caddy avec Let's Encrypt / mkcert).

### 6.4 Risque Résiduel RSK-02 : Stockage du Jeton de Session dans `localStorage`
- **Gravité :** MOYENNE (Medium / CVSS 5.4)
- **Localisation :** `Jarvis Final - SITE/mobile/app.js` (lignes 172-173, 205-206)
- **Description :** Les identifiants `jarvis_session_id` et `jarvis_session_token` sont stockés dans le stockage local du navigateur.
- **Impact :** Vulnérable à l'exfiltration en cas de faille Cross-Site Scripting (XSS) sur le client web mobile.
- **Recommandation :** Migrer vers un cookie HTTP-Only avec directive `SameSite=Strict`.

### 6.5 Risque Résiduel RSK-03 : Concurrence Mémoire Multi-Processus
- **Gravité :** FAIBLE (Low / CVSS 2.5)
- **Localisation :** `main2.py:174` (`MEMOIRE_LOCK = threading.RLock()`)
- **Description :** Le verrou mémoire protège les threads d'un même processus mais ne verrouille pas le fichier au niveau OS face à des processus concurrents indépendants.
- **Impact :** Si plusieurs instances de `main2.py` ou le script `jarvis_agent.py` sont exécutés en parallèle, un écrasement peut survenir.
- **Recommandation :** Archiver ou supprimer `jarvis_agent.py` et intégrer un verrou de fichier OS (`msvcrt` sur Windows ou `portalocker`).

---

## 7. DÉCISION FORENSIQUE FINALE

Sur la base de l'examen contradictoire exhaustif du code source, de la vérification des différentiels Git, de l'audit de qualité des tests existants et de l'exécution réussie de 72/75 vecteurs adversariaux indépendants :

La décision de sécurité prononcée est :

# **CONDITIONALLY_APPROVED** (Homologation Conditionnelle)

### Justification de la Décision :
1. **Élimination formelle des failles critiques ayant motivé le REJECTED précédent :** L'ancien endpoint divulguant le jeton a été supprimé, le contournement CSWSH par domaine DNS préfixé est neutralisé, l'appairage mobile avec PIN éphémère est opérationnel, la mémoire est protégée par verrou et écriture atomique, la confirmation d'extinction est hermétiquement isolée par session, et l'alarme vérifie son état matériel réel.
2. **Acceptabilité des risques résiduels sous conditions d'usage :** Les défauts confirmés (absence de filtrage des ports dans l'origine, absence de vérification physique sur les lumières, transport HTTP/WS sans TLS sur le LAN) ne permettent pas une homologation inconditionnelle (`APPROVED`), mais ne justifient pas un rejet bloquant (`REJECTED`) dans un cadre d'usage domestique supervisé sur réseau privé de confiance.

### Conditions Obligatoires pour Déploiement Définitif :
1. **Condition C-01 :** Déployer un reverse proxy HTTPS/WSS (ou activer TLS dans `main2.py`) avant toute utilisation sur un réseau Wi-Fi non strictement privé.
2. **Condition C-02 :** Restreindre la validation d'origine dans `is_origin_allowed` à une allowlist explicite de ports autorisés (ex: 8080, 5173).
3. **Condition C-03 :** Supprimer ou mettre à jour le fichier orphelin `jarvis_agent.py` pour éliminer tout risque d'écriture non protégée dans `jarvis_memoire.json`.
4. **Condition C-04 :** Étendre la vérification d'état physique en deux temps aux éclairages et actionneurs domotiques à fort impact.
