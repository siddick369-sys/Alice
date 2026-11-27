# 🛡️ ALICE-P1-REMEDIATION-009 — REVUE ROUTAGE MOBILE WSS (`FINDING-02`)

- **Défaut initial :** `mobile/app.js` construisait `WS_URL = ${wsProtocol}//${window.location.hostname}:8765`, incompatible avec un reverse proxy HTTPS exposant `/ws` sur `443` et bloquant `8765` au pare-feu.
- **Correction :** `buildWebSocketUrl(locationObj, configObj)` dans `mobile/app.js:15-52` :
  - En HTTPS : retourne `wss://<host><basePath>/ws` sans jamais viser `:8765` et sans double slash.
  - En production HTTP (`env: "production"`) : lève une erreur explicite sans fallback `ws://`.
  - En développement HTTP local : retourne `ws://<hostname>:8765`.
  - En configuration absente : lève une erreur explicite (`connectWS()` refuse la connexion).
  - Service worker `mobile/sw.js` vérifié : exclut `/api/` et requêtes non-GET.
- **Preuve :** `TestFinding02MobileWssRouting` (`6/6 PASS` via exécution Node réelle de `buildWebSocketUrl` extraite de `mobile/app.js`).
