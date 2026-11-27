# ALICE_012_FUNCTIONAL_TEST_MATRIX.md
## Matrice de Validation Fonctionnelle — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  

---

### Matrice des Composants et Parcours Réels Testés

| ID | Domaine / Fonctionnalité | Méthode de Test | Résultat | Preuve / Statut |
|---|---|---|---|---|
| **FT-01** | Démarrage Backend `main2.py` | Exécution réelle (`run_alice.py`) | **PASS** (après fix `import socket`) | PID actif, ports `8080` & `8765` à l'écoute |
| **FT-02** | Démarrage Frontend Vite `5173` | Sous-processus Vite + Navigateur | **PASS** | HTTP `200 OK`, build `tsc && vite build` OK |
| **FT-03** | Interface Mobile PWA `8080` | Navigateur réel + HTTP GET | **PASS** (après fix `orb.js`) | `index.html`, `app.js`, `manifest.json` 200 OK |
| **FT-04** | Appairage PIN Mobile (`/api/pair`) | Requête POST réelle avec PIN loggé | **PASS** | PIN `842957` -> 200 OK, cookie `alice_session`, CSRF |
| **FT-05** | Usage unique & expiration PIN | Replay PIN + PIN invalide + TTL | **PASS** | Replay rejeté `401`, PIN erroné `401`, TTL 120s respecté |
| **FT-06** | WebSocket Authentifié (`/ws`) | Handshake WS réel avec cookie | **PASS** | Connexion établie, transmission message `user_message` |
| **FT-07** | Observabilité & Métriques (`/api/ops/metrics`) | GET authentifié & non-auth | **PASS** | 401 si anonyme, 200 si appairé (CPU/RAM/Uptime réels) |
| **FT-08** | Feature Flags (`/api/flags`) | GET authentifié | **PASS** | 200 OK, liste complète des flags retournée |
| **FT-09** | Actions Rapides (`/api/quick_actions`) | GET authentifié | **PASS** | 200 OK, actions (`Mode Cinéma`, etc.) retournées |
| **FT-10** | Briefing Quotidien (`/api/briefing`) | GET authentifié | **PASS** | 200 OK, structure `morning_briefing` retournée |
| **FT-11** | File de Jobs & Routines (`/api/jobs/stats`, `/api/iot/routines`) | GET authentifiés | **PASS** | 200 OK |
| **FT-12** | Knowledge Graph (`/api/kg`) & Commitments | GET & POST authentifiés | **PASS** | GET 200 OK ; validation stricte schéma POST (400 si champ manquant) |
| **FT-13** | Synchronisation Notes Hors-Ligne (`/api/sync/notes`) | POST avec/sans CSRF + GET | **PASS** | 403 sans CSRF (avec `Origin`), 200 avec CSRF |
| **FT-14** | Révocation de session (`/api/revoke_session`) | POST puis ré-accès API | **PASS** | 200 OK puis `401` sur appel ultérieur |
| **FT-15** | Suite de régression unitaire & sécurité | `unittest discover -s tests` | **PASS** | 46/46 tests passés en 14.94s |
| **FT-16** | Domotique Home Assistant réelle | Environnement local | **NOT_TESTED_EXTERNAL_DEPENDENCY** | Pas d'instance HA physique sur le réseau local |
| **FT-17** | Caméra RTSP / Google OAuth | Environnement local | **NOT_TESTED_EXTERNAL_DEPENDENCY** | Pas de flux RTSP ni token OAuth actif |
| **FT-18** | LLM Cloud (Gemini/Groq) & Edge-TTS | Environnement hors-ligne | **DEGRADED_EXTERNAL_OFFLINE** | Réseau externe restreint, bascule prévue vers fallback local |
