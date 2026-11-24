# 📝 JOURNAL DES MODIFICATIONS — ALICE-P0-REMEDIATION-002

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence Mission :** `ALICE-P0-REMEDIATION-002`  
**Date :** 23 Novembre 2026  
**Branche Git :** `main`  
**HEAD de Référence :** `f9c319557f4a02d8ddf5957505bde91c87947940`  
**Statut de Commit :** AUCUN COMMIT (Strict respect des règles de non-commit / non-push)  

---

## 1. FICHIERS MODIFIÉS

| Fichier | Nature de la Modification | Lignes Impactées |
| :--- | :--- | :---: |
| `Jarvis Final - SITE/main2.py` | Sécurisation WebSocket, Pairing, Session, Mémoire, 2FA, Home Assistant | ~180-200, ~490-640, ~2040-2130, ~3250-3280, ~3980-4110 |
| `Jarvis Final - SITE/mobile/index.html` | Ajout du modal d'appairage sécurisé (code PIN à 6 chiffres) | L33-46 |
| `Jarvis Final - SITE/mobile/app.js` | Handshake WebSocket auth, flux d'appairage POST, élimination boucle infinie | L25-30, L129-245 |

---

## 2. DÉTAIL DES MODIFICATIONS PAR FICHIER

### 2.1. `Jarvis Final - SITE/main2.py`

#### A. Importation Standard
- Ajout de `import ipaddress` en en-tête pour la validation stricte des adresses IPv4/IPv6 privées.

#### B. Mémoire Persistante et Contexte RAG (SEC-06)
- **Déplacement et unification :** Définition de `MEMOIRE_FILE` (chemin absolu), `MEMOIRE_LOCK` (`threading.RLock`), `charger_memoire()`, `sauvegarder_memoire()`, `ajouter_memoire()` et `supprimer_memoire()` en amont de `charger_contexte_rag()`.
- **`charger_contexte_rag()` :** Suppression de la lecture brute `open("jarvis_memoire.json")`. Utilisation directe de `charger_memoire()` sous le verrou `MEMOIRE_LOCK`.
- **`memory_add(cle, valeur)` :** Remplacement complet du corps de la fonction par un appel direct à `ajouter_memoire(cle, valeur)` garantissant l'écriture atomique via fichier `.tmp` et `os.replace`.
- **`memory_forget(cle)` :** Remplacement complet du corps par un appel direct à `supprimer_memoire(cle)` supportant la suppression insensible à la casse et partielle sous verrou.

#### C. Gestionnaire d'Appairage Éphémère (SEC-04-A)
- Implantation de la classe `PairingManager` :
  - Génération de code PIN à 6 chiffres cryptographiquement aléatoires via `secrets.randbelow(10)`.
  - Durée de vie (TTL) limitée à 120 secondes.
  - Consommation à usage unique immédiat (`self.active_pairing_code = None`) dès validation (anti-rejeu).
  - Verrouillage automatique après 5 tentatives infructueuses (anti-brute force).

#### D. Gestionnaire de Sessions Cryptographiques et Validation d'Origine (SEC-04-B)
- Refactorisation de la classe `WSSessionManager` :
  - Suppression de la persistance de token en clair sur disque (`temp_uploads/.ws_session_token`).
  - Gestion d'un dictionnaire multi-sessions en mémoire `self.sessions` (`session_id -> {token, client_type, client_ip, created_at, expires_at, last_seen}`).
  - Création d'une session desktop locale (`desktop_local`) au démarrage.
  - Méthodes `verify_session(session_id, token)` et `revoke_session(session_id, token)`.
  - Réécriture de `is_origin_allowed(origin)` :
    - Rejet immédiat si `origin in (None, "", "null")`.
    - Validation stricte du schéma (`http`, `https`).
    - Autorisation de `localhost`, `127.0.0.1`, `::1`.
    - Analyse stricte par `ipaddress.ip_address(host)`. Si `host` est un nom de domaine DNS distant (ex: `192.168.attacker.com`), une exception `ValueError` est levée et l'origine est rejetée (`False`).
    - Rejet explicite des adresses link-local / métadonnées cloud (`169.254.x.x` via `not ip.is_link_local`).

#### E. Handler WebSocket `ws_handler` (SEC-04-C)
- Contrôle d'origine préalable : fermeture avec code 4003 si origine interdite.
- Authentification par poignée de main :
  - Pour les clients loopback locaux avec origine locale : attribution automatique de la session `desktop_local`.
  - Pour tout client distant (LAN/mobile) : obligation de transmettre un message d'authentification `{"type": "auth", "session_id": ..., "token": ...}` sous 5 secondes. En cas d'échec ou d'expiration, fermeture immédiate avec code 4001.
  - Association de `websocket.session_id` pour le routage des actions.

#### F. Contrôleur d'Actions Système `SystemActionController` (SEC-03)
- Remplacement du singleton `self.pending_action` par un dictionnaire multi-sessions `self.pending_actions = {}` indexé par `session_id`.
- Implantation du filtre `is_thought_or_conditional(cmd_clean)` ignorant les formulations réflexives (« je pense », « j'hésite », « j'aimerais peut-être », etc.).
- Dans `process_command(cmd, session_id, client_ip)` :
  - Interdiction de confirmation croisée : une confirmation soumise avec une session différente de la session ayant initié l'extinction est rejetée.
  - Désambiguïsation stricte : rejet d'une confirmation de redémarrage pour une extinction en attente (et vice-versa).
  - Propagation de `session_id` et `client_ip` depuis `traiter_reponse_ia` et `ecouter`.

#### G. Vérité Opérationnelle Home Assistant (SEC-05)
- Dans `traiter_reponse_ia` pour l'action `ha_alarme` :
  - Appel du service `alarm_arm_away` ou `alarm_disarm`.
  - En cas de réponse HTTP 200, interrogation immédiate de l'état matériel via `ha_get_etat("alarm_control_panel.home_base_2")`.
  - ALICE confirme uniquement si l'état physique réel correspond (`armed_away`, `armed_home`, `disarmed`).
  - Si l'état physique reste `unknown`/`inconnu`, émission d'un avertissement explicite d'état physique non confirmé.

#### H. Serveur HTTP Mobile `start_mobile_http_server` (SEC-04-A)
- Suppression définitive de la route vulnérable `GET /api/auth/token` (renvoie désormais 410 Gone sans wildcard CORS).
- Ajout de la route `POST /api/pair` : reçoit le code PIN, le valide via `PAIRING_MANAGER.consume_pairing_code`, enregistre la session et retourne `session_id` et `token`.
- Ajout de la route `POST /api/revoke_session` pour clore une session mobile.
- Configuration CORS restrictive : seuls les hôtes validés par `WS_SESSION_MANAGER.is_origin_allowed` reçoivent un en-tête `Access-Control-Allow-Origin` reflétant leur propre origine.

---

### 2.2. `Jarvis Final - SITE/mobile/index.html`

- Insertion d'une boîte de dialogue modale d'appairage `#pairing-modal` contenant :
  - Champ de saisie numérique à 6 chiffres (`#pairing-code-input`).
  - Bouton d'action `#pairing-submit-btn`.
  - Zone d'affichage des messages d'erreur `#pairing-error`.

---

### 2.3. `Jarvis Final - SITE/mobile/app.js`

- Déclaration des références DOM pour le modal d'appairage.
- Implantation des fonctions `showPairingModal`, `hidePairingModal` et `submitPairingCode`.
- Dans `submitPairingCode` : appel asynchrone à `POST /api/pair`. En cas de succès, stockage des identifiants dans `localStorage` (`jarvis_session_id`, `jarvis_session_token`) et lancement de `connectWS()`.
- Dans `connectWS()` :
  - Vérification de la présence des identifiants locaux. Si absents, affichage du modal d'appairage sans tenter de connexion WebSocket à l'aveugle.
  - À l'ouverture du WebSocket (`ws.onopen`), transmission immédiate du payload d'authentification `{ "type": "auth", "session_id": ..., "token": ... }`.
  - En cas d'erreur `auth_error` ou de fermeture avec code 4001 : suppression des identifiants locaux invalides, suspension définitive du timer de reconnexion automatique et réaffichage du modal d'appairage.

---

## 3. IMPACT SUR LES INTERFACES ET LA COMPATIBILITÉ

1. **Interface Desktop locale (`localhost:5173`) :**
   - Connectivité transparente et fluide préservée.
   - Session locale en mémoire `desktop_local` automatiquement assignée sans intervention utilisateur.
   - Compilation TypeScript vérifiée avec 0 erreur (`npx tsc --noEmit`).

2. **Interface Mobile LAN (`http://<ip>:8080`) :**
   - Fin définitive de la boucle de déconnexion toutes les 5 secondes.
   - Première connexion : saisie rapide du code à 6 chiffres généré sur le terminal d'Alice.
   - Connexions ultérieures : reconnexion automatique instantanée via les identifiants stockés dans le `localStorage`.
