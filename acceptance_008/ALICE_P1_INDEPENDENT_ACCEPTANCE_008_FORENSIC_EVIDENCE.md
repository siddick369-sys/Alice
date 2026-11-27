# 🛡️ ALICE-P1-INDEPENDENT-ACCEPTANCE-008 — PREUVES FORENSIQUES

**Mission ID :** `ALICE-P1-INDEPENDENT-ACCEPTANCE-008`  
**Date :** 25 Novembre 2026  

---

## 1. PREUVES D'EXÉCUTION ET CONSTATS CODE

### 1.1. Séparation `peer_ip` / `client_ip` / `desktop_local` (`Jarvis Final - SITE/main2.py:1027-1079`)
- `ws_handler` extrait `ws_headers` via `websocket.request.headers` (`websockets 16.0`), lit `peer_ip = str(websocket.remote_address[0])`, vérifie `is_trusted_proxy_ip(peer_ip)` et `has_proxy_forwarding_headers(ws_headers)`.
- `is_direct_local_desktop` exige cumulativement `not is_proxy_topology`, `not has_fwd`, `is_loopback_ip(peer_ip)`, `is_loopback_ip(client_ip)` et origine autorisée ou absente.

### 1.2. Preuve `FINDING-01` — WS déjà ouvert non fermé lors de `revoke_session`
- **Fichiers/Lignes :** `main2.py:884-894` (`WSSessionManager.revoke_session`) et `main2.py:1135-1208` (`ws_handler` boucle `async for message in websocket`).
- **Sortie brute observée (`task-2316`) :**  
  `[AUDIT FACT] WS already open after revoke_session -> still_in_CONNECTED_CLIENTS=True`
- **Limitation / Impact :** Une reconnexion est immédiatement bloquée (`4001`), mais la connexion WebSocket préexistante reste ouverte.

### 1.3. Preuve `FINDING-02` — Contradiction Guide Nginx `/ws` vs `mobile/app.js:12`
- **Guide (`remediation_007/ALICE_P1_REMEDIATION_007_DEPLOYMENT_GUIDE.md:68-78, 91`) :** Configure Nginx avec `location /ws { proxy_pass http://127.0.0.1:8765; }` sur port `443` et demande de bloquer le port `8765` au pare-feu.
- **Frontend (`Jarvis Final - SITE/mobile/app.js:12`) :** `const WS_URL = \`\${wsProtocol}//\${window.location.hostname}:8765\`;` — tente de joindre le port `8765` au lieu de `/ws` sur le port `443`.

### 1.4. Preuve `FINDING-03` — Default-allow RBAC pour actions non mappées
- **Fichier/Lignes :** `Jarvis Final - SITE/alice_core/security/rbac.py:375-377`.
- **Sortie brute observée (`task-2316`) :**  
  `[AUDIT FACT] RBAC unmapped action 'eteindre_pc' for GUEST -> True` (alors que `"shutdown"` retourne `False`).

### 1.5. Preuve Frontend PWA & Service Worker (`mobile/sw.js` & `mobile/app.js`)
- `mobile/sw.js:36` : `if (url.pathname.startsWith("/api/") || event.request.method !== "GET") { return; }` — aucune route `/api/*` ni réponse d'authentification n'est mise en cache.
- `mobile/app.js:268-271` : purge `localStorage` (`removeItem`) et stocke uniquement `jarvis_session_id` et `jarvis_csrf_token` dans `sessionStorage`.
