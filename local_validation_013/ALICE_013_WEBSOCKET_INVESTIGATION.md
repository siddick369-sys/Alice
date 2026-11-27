# ALICE_013_WEBSOCKET_INVESTIGATION.md
## Enquête Forensique & Résolution de la Contradiction WebSocket — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  
**Objectif :** Résoudre la contradiction apparente constatée lors de la Mission 012 où l'interface Mobile PWA affichait le badge visuel `hors-ligne` alors que le journal serveur et la console annonçaient une connexion WebSocket active.

---

### 1. Analyse de la Contradiction Visuelle (Mobile PWA)

Lors de la Mission 012, les éléments suivants ont été observés simultanément :
- **Console DevTools :** `[WS] Connecté à ws://127.0.0.1:8765`
- **Journal Serveur :** `[WEB] Interface connectée (Clients actifs: 1, IP: 127.0.0.1, Session: desktop_local)`
- **Capture UI Mobile (`index.html`) :** Badge supérieur droit affichant `hors-ligne` (`uid=1_5`).

---

### 2. Démonstration de la Cause Racine dans le Code Source

L'audit approfondi du code montre une discordance architecturale entre le client Mobile (`mobile/app.js`), le client Desktop (`frontend/src/main.ts`) et le serveur WebSocket (`main2.py:ws_handler`) :

#### A. Côté Client Mobile (`Jarvis Final - SITE/mobile/app.js`)
```javascript
// Ligne 346: Le badge ne bascule sur "connecté" QUE via setConnected(true)
function setConnected(ok) {
  badgeEl.classList.toggle("connected", ok);
  badgeEl.classList.toggle("disconnected", !ok);
  badgeLabelEl.textContent = ok ? "connecté" : "hors-ligne";
}
setConnected(false); // Initialisé à false ("hors-ligne")

// Lignes 421-433: À l'ouverture de la socket (open), setConnected(true) N'EST PAS APPELÉ !
ws.addEventListener("open", () => {
  console.log("[WS] Connecté à", WS_URL);
});

// setConnected(true) est conditionné STRICTEMENT à la réception de {"type": "auth_ok"} :
ws.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "auth_ok") {
    setConnected(true);
    hidePairingModal();
  }
});
```

#### B. Côté Serveur Backend (`Jarvis Final - SITE/main2.py`)
```python
# Lignes 1093-1111: Traitement spécial pour toute connexion provenant de loopback (127.0.0.1 / ::1)
is_direct_local_desktop = (
    not is_proxy_topology
    and not has_fwd
    and is_loopback_ip(peer_ip)
    and is_loopback_ip(client_ip)
    and (not origin or WS_SESSION_MANAGER.is_origin_allowed(origin))
)

if is_direct_local_desktop:
    authenticated = True
    session_id = "desktop_local"
    auth_token = WS_SESSION_MANAGER.desktop_token
    websocket.session_id = session_id

# Ligne 1113: Le parsing du Cookie de session alice_session est court-circuité !
if not authenticated:
    cookie_hdr = ws_headers.get("Cookie")
    # ... vérification cookie et émission de {"type": "auth_ok"} ...
```

#### C. Côté Client Desktop (`Jarvis Final - SITE/frontend/src/main.ts`)
```typescript
// Lignes 87-89: Le desktop passe immédiatement à "connecte" dès l'ouverture TCP
ws.addEventListener("open", () => {
  setConnected(true);
});
```

---

### 3. Conclusion et Démontage des États

La contradiction est désormais résolue et expliquée avec certitude :

1. **Processus démarré :** OUI (PID actif).
2. **Port ouvert :** OUI (Port `8765` en écoute).
3. **Handshake réseau réussi :** OUI (HTTP `101 Switching Protocols`, TCP connecté).
4. **Session authentifiée :**
   - Sur Desktop (`main.ts`) : Authentifié implicitement comme `desktop_local` (affichage `connecte`).
   - Sur Mobile (`app.js`) en local (`127.0.0.1`) : Le serveur assigne silencieusement `desktop_local` sans parser le cookie et **sans émettre** le message applicatif `{"type": "auth_ok"}`.
5. **État de l'interface :** Le client mobile PWA attend le signal `auth_ok` pour basculer son badge. En l'absence de ce message, il maintient son état défensif `hors-ligne`, bien que la socket réseau sous-jacente soit fonctionnelle et transmette les messages.

---

### 4. Recommandation Minimale de Remédiation (Pour autorisation future)

Dans `Jarvis Final - SITE/main2.py`, ne pas court-circuiter le cookie si présent, ou émettre un acquittement de session (`auth_ok` ou `session_ready`) pour les clients loopback :
```python
if is_direct_local_desktop:
    # Si le client mobile fournit un cookie alice_session, prioriser la session mobile
    if cookie_hdr and "alice_session" in cookie_hdr:
        # parser et valider la session mobile réelle
        ...
    else:
        authenticated = True
        session_id = "desktop_local"
        await websocket.send(json.dumps({"type": "auth_ok", "session_id": "desktop_local"}))
```
*Note : Conformément au mandat STRICT READ-ONLY de la Mission 013, cette modification n'a pas été appliquée au code.*
