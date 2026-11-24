# 🛡️ ALICE — RAPPORT D'IMPLÉMENTATION DU DURCISSEMENT P1
## ARCHITECTURE RÉSEAU, PROTECTION REVERSE PROXY, COOKIES SECURISED ET CSP (MISSION 006)

**Mission ID :** `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Classification :** RAPPORT TECHNIQUE D'INGÉNIERIE SÉCURITÉ P1  
**Date :** 24 Novembre 2026  
**Statut :** IMPLÉMENTÉ ET VALIDÉ EN LOCAL  

---

## 1. VUE D'ENSEMBLE DES MODIFICATIONS

La mission `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006` a apporté des remédiations de niveau P1 structurelles sans aucune rupture de contrat fonctionnel avec l'interface mobile, le client Three.js ou le moteur d'exécution vocal :

```mermaid
flowchart TD
    subgraph Client ["Client Navigateur Mobile"]
        UI["mobile/app.js & index.html"]
        Storage["sessionStorage & HttpOnly Cookie"]
    end

    subgraph Network ["Frontière Réseau & Sécurité"]
        ReverseProxy["Reverse Proxy TLS (Nginx/Caddy)"]
        TrustFilter["get_trusted_client_ip (CIDR Allowlist)"]
        SecHeaders["Security Headers (CSP, HSTS, DENY)"]
    end

    subgraph Backend ["Backend Python ALICE"]
        NetCfg["NetworkConfig (ALICE_BIND_ADDRESS)"]
        HTTPServer["MobileHandler (DualStack HTTP/S)"]
        WSServer["ws_handler (WebSocket Cookie Auth)"]
        SessionMgr["WSSessionManager (CSRF + TTL)"]
    end

    UI -->|1. POST /api/pair (PIN)| HTTPServer
    HTTPServer -->|2. Set-Cookie alice_session (HttpOnly)| Storage
    UI -->|3. WebSocket Upgrade Handshake (Cookie auto)| ReverseProxy
    ReverseProxy -->|4. Forward avec XFF| TrustFilter
    TrustFilter --> Backend
    Backend --> WSServer
    WSServer -->|5. Valide Session & CSRF| SessionMgr
```

---

## 2. DÉTAIL DES CHANGEMENTS PAR COMPOSANT

### 2.1. Centralisation de la Configuration Réseau (`main2.py`)
- **Nouvelle classe `NetworkConfig` :**
  - Encapsule `bind_address`, `http_port`, `ws_bind_address`, `ws_port`, et `trusted_proxies`.
  - Expose les propriétés d'accès `http_host` et `ws_host`.
- **Fonction `get_network_config()` :**
  - Lit les variables d'environnement `ALICE_BIND_ADDRESS` (défaut `0.0.0.0`), `ALICE_HTTP_PORT` (défaut `8080`), `ALICE_WS_BIND_ADDRESS` (défaut = bind HTTP), `ALICE_WS_PORT` (défaut `8765`), et `ALICE_TRUSTED_PROXIES` (défaut `127.0.0.1,::1`).
  - Valide rigoureusement le format d'adresse IP (IPv4 ou IPv6 via `ipaddress.ip_address`) avec repli sécurisé en cas d'injection ou de chaîne invalide.
  - Valide la plage de ports (1 à 65535) et résout automatiquement les collisions entre le port HTTP et le port WebSocket.
  - Parse `ALICE_TRUSTED_PROXIES` en supportant à la fois les adresses IP individuelles et les sous-réseaux CIDR (ex: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.1.0/24`).

### 2.2. Durcissement de la Résolution d'IP et Confiance Proxy (`main2.py`)
- **Fonction `get_trusted_client_ip(handler, client_address)` :**
  - Rejette formellement tout en-tête de transfert (`X-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP`, `Forwarded`) si la connexion immédiate au socket ne provient pas de `trusted_proxies`.
  - En cas de connexion depuis un proxy de confiance :
    - Analyse `X-Forwarded-For` en extrayant strictement l'adresse cliente originelle (leftmost dans la chaîne).
    - Élimine les numéros de ports éventuels (`ip:port` ou `[ipv6]:port`).
    - Prend en charge `X-Real-IP`, `CF-Connecting-IP` (Cloudflare), et `Forwarded` conforme RFC 7239 (`for=...`).
    - En cas d'en-tête malformé ou non conforme, repli immédiat et sécurisé sur l'adresse IP immédiate du socket sans lever d'exception.

### 2.3. Architecture de Session par Cookie `HttpOnly` et Protection CSRF (`main2.py`)
- **`WSSessionManager` :**
  - Enrichissement de `register_session` avec le paramètre `csrf_token` et gestion d'expiration par `ttl`.
  - Nouvelle méthode `verify_csrf(session_id, csrf_token)` pour immuniser les opérations sensibles.
- **Endpoint `/api/pair` :**
  - Émission de deux cookies sécurisés :
    - `alice_session=<session_id>:<token>; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400` (+ drapeau `; Secure` si HTTPS).
    - `alice_csrf=<csrf_token>; Path=/; SameSite=Strict; Max-Age=86400` (+ drapeau `; Secure` si HTTPS).
  - Élimination de la fuite du jeton secret dans la réponse JSON (sauf demande explicite en mode legacy via `X-Legacy-Client: 1`).
- **Endpoint `/api/revoke_session` :**
  - Exige la validation du jeton CSRF (`X-CSRF-Token` ou cookie).
  - Révoque la session côté serveur et renvoie des en-têtes `Set-Cookie` avec `Max-Age=0` pour effacer les cookies du client.
- **Authentification WebSocket (`ws_handler`) :**
  - Extraction automatique du cookie `alice_session` lors du handshake HTTP Upgrade du navigateur.
  - Si le cookie est présent et valide, la connexion est authentifiée instantanément sans nécessiter de trame JSON d'authentification.
  - Maintien du repli (timeout 5 secondes) pour les clients existants ou non-navigateurs transmettant une trame `{ "type": "auth", "token": "..." }`.

### 2.4. En-têtes de Sécurité HTTP et CSP (`MobileHandler`)
- Déplacement de `MobileHandler` au niveau module pour garantir sa testabilité unitaire et sa modularité.
- Injection systématique des en-têtes via `_set_security_headers()` et surcharge de `end_headers()` :
  - **`Content-Security-Policy` :**  
    `default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' data: blob:; connect-src 'self' ws: wss:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';`
  - **`X-Content-Type-Options` :** `nosniff`
  - **`X-Frame-Options` :** `DENY`
  - **`Referrer-Policy` :** `strict-origin-when-cross-origin`
  - **`Permissions-Policy` :** `microphone=(self), camera=(), geolocation=(), payment=()`
  - **`Strict-Transport-Security` :** `max-age=31536000; includeSubDomains` (lorsque TLS est actif).

### 2.5. Durcissement Frontend Mobile (`mobile/app.js` et `mobile/index.html`)
- **`mobile/index.html` :**
  - Remplacement de l'adresse IP privée codée en dur `http://192.168.1.23:8080` (ligne 39) par une formulation générique `http://<IP_SERVEUR>:8080`.
- **`mobile/app.js` :**
  - Modification de `submitPairingCode` : suppression systématique de tout token résiduel dans `localStorage`, conservation de l'identifiant non-secret de session dans `sessionStorage`.
  - Modification de `connectWS` : ouverture directe de la connexion WebSocket, le navigateur envoyant automatiquement le cookie `alice_session`.
  - Nettoyage automatique de `sessionStorage` et `localStorage` lors de la fermeture de session ou des erreurs d'authentification.

---

## 3. FICHIERS IMPACTÉS ET SOMMES DE CONTRÔLE

| Fichier | Nature de la Modification |
| :--- | :--- |
| `Jarvis Final - SITE/main2.py` | Configuration réseau, `NetworkConfig`, `get_trusted_client_ip`, `MobileHandler` module-scope, cookies `HttpOnly`, CSRF, headers CSP, WebSocket cookie auth. |
| `Jarvis Final - SITE/mobile/app.js` | Suppression de l'écriture du token dans `localStorage`, support transparent des cookies `HttpOnly`. |
| `Jarvis Final - SITE/mobile/index.html` | Suppression de l'IP privée locale en dur dans le warning Chrome. |
| `tests/security/test_p1_production_exposure_006.py` | Nouvelle suite de 23 tests adversariaux dédiés au périmètre P1. |

Aucun composant externe non approuvé n'a été introduit. Les modifications respectent à 100% les interfaces de communication préexistantes.
