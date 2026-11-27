# ALICE_012_USER_SCENARIOS.md
## Scénarios Utilisateur End-to-End Exécutés — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  
**Script d'exécution réel :** `local_validation_012/run_e2e_scenarios.py`  

---

### Scénario 1 : Parcours d'Appairage Sécurisé & Cycle de Vie de Session
- **Étapes :**
  1. Consultation de `GET /api/pair/status` -> `{"active": true, "remaining_seconds": 30}`.
  2. Tentative d'accès non authentifié à `GET /api/ops/metrics` -> rejet `401 Unauthorized`.
  3. Soumission d'un PIN erroné (`999999`) sur `POST /api/pair` -> rejet `401`.
  4. Soumission du PIN valide généré au démarrage (`842957`) -> `200 OK`, attribution du rôle `OWNER`, dépôt du cookie `HttpOnly` `alice_session`, et émission du jeton `csrf_token`.
  5. Rejeu immédiat du même PIN (`842957`) -> rejet `401` (garantie d'usage unique).
- **Verdict :** **PASS**

### Scénario 2 : Consultation des Endpoints Métier Authentifiés
- **Étapes :** Avec la session `OWNER` fraîchement appairée, consultation successive de :
  - `/api/me`, `/api/ops/metrics`, `/api/flags`, `/api/quick_actions`, `/api/briefing`, `/api/jobs/stats`, `/api/iot/routines`, `/api/kg`, `/api/commitments`.
- **Résultat :** 9/9 endpoints ont répondu `200 OK` avec des données JSON structurées en temps réel.
- **Verdict :** **PASS**

### Scénario 3 : Communication WebSocket Temps Réel
- **Étapes :**
  1. Ouverture d'une connexion WebSocket `ws://127.0.0.1:8765` avec le cookie de session `alice_session`.
  2. Envoi d'une trame JSON `{"action": "user_message", "text": "Bonjour Alice, quel est ton statut ?"}`.
  3. Connexion également vérifiée depuis l'interface Desktop Three.js (`ws://localhost:8765`, état `A.L.I.C.E · connecte`).
- **Verdict :** **PASS**

### Scénario 4 : Synchronisation Hors-Ligne & Protection CSRF
- **Étapes :**
  1. Envoi d'un `POST /api/sync/notes` avec en-tête `Origin: http://127.0.0.1:8080` sans `X-CSRF-Token` -> rejet `403 Forbidden`.
  2. Envoi avec `X-CSRF-Token` valide -> `200 OK` (traitement du lot `ops`, latence mesurée `5.97 ms`).
  3. Relecture via `GET /api/sync/notes` -> `200 OK`.
- **Verdict :** **PASS**

### Scénario 5 : Navigation UI Navigateur Réel (Mobile & Desktop)
- **Étapes :**
  1. Ouverture de `http://127.0.0.1:8080/index.html` via navigateur réel.
  2. Ouverture des panneaux `Diagnostic & Flags` (`⚙️`) et `Notes Hors-Ligne` (`📝`), vérification des états et fermeture propre.
  3. Ouverture de `http://localhost:5173/` et vérification du rendu Three.js + connexion WebSocket.
- **Verdict :** **PASS**

### Scénario 6 : Résilience aux Erreurs & Révocation de Session
- **Étapes :**
  1. Requête vers un endpoint inconnu (`POST /api/unknown_bypass`) -> `404` (comportement fail-closed).
  2. Tentative de Path Traversal (`GET /../main2.py`) -> rejet `404`.
  3. Révocation explicite via `POST /api/revoke_session` -> `200 OK`.
  4. Tentative d'accès à `GET /api/ops/metrics` après révocation -> rejet `401 Unauthorized`.
- **Verdict :** **PASS**
