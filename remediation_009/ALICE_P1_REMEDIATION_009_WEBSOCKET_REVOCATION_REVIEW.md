# 🛡️ ALICE-P1-REMEDIATION-009 — REVUE RÉVOCATION WEBSOCKET (`FINDING-01`)

- **Défaut initial :** `revoke_session()` supprimait la session en mémoire sans fermer les WebSockets actifs dans `CONNECTED_CLIENTS`, et `ws_handler` ne re-validait pas la session à chaque message.
- **Cause racine :** Absence de liaison entre le cycle de vie de `WSSessionManager` et la boucle asynchrone des connexions `websockets` actives.
- **Correction :**
  1. `WSSessionManager.is_session_active(session_id, token)` vérifie atomiquement sous verrou l'existence, le TTL, l'absence de révocation et l'égalité en temps constant du jeton.
  2. `WSSessionManager.revoke_session()` ferme activement toutes les sockets de `CONNECTED_CLIENTS` portant `session_id` (`code=4001`), y compris depuis un thread HTTP synchrone via `asyncio.run_coroutine_threadsafe`.
  3. `ws_handler` vérifie `_reject_if_session_invalid()` à chaque itération de la boucle `async for message in websocket` et juste avant chaque opération privilégiée (anti-TOCTOU).
- **Preuve :** `TestFinding01WebSocketRevocation` (`2/2 PASS` sur sockets TCP réels : 2 connexions sur session A fermées simultanément, session B isolée et maintenue active, reconnexion bloquée `4001`, changement d'identité rejeté `4001`).
