# 🛡️ ALICE-P1-REMEDIATION-009 — REVUE EN-TÊTES PROXY & `verify_token` (`FINDING-06`)

- **Défauts initiaux :**
  1. `get_trusted_client_ip()` utilisait `headers.get("X-Forwarded-For")` sans vérifier les en-têtes dupliqués via `get_all()`, ne rejetait pas les entrées vides dans une chaîne XFF, et traitait mal un dictionnaire `{"headers": ...}` passé par `ws_handler`.
  2. `ws_handler` appelait `WS_SESSION_MANAGER.verify_token(tok)` (méthode inexistante) sur les trames `auth` post-connexion.
- **Correction :**
  1. Extraction propre `handler["headers"]` si présent, rejet de tout en-tête dupliqué (`len(vals) > 1`), rejet de toute chaîne `XFF` contenant un élément vide ou invalide, et normalisation `ipv4_mapped` (`::ffff:203.0.113.44` -> `203.0.113.44`).
  2. Suppression totale de `verify_token` et validation via `WS_SESSION_MANAGER.verify_session(session_id, tok)` avec fermeture `4001` en cas d'échec ou de tentative de changement de `session_id`.
- **Preuve :** `TestFinding06ProxyHeadersAndVerifyToken` (`4/4 PASS`) + résolution IP réelle `203.0.113.10` vérifiée dans les logs WebSocket.
