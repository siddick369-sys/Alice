# 🛡️ ALICE — REVUE TECHNIQUE DES COOKIES ET DE L'AUTHENTIFICATION WEBSOCKET
## AUDIT DES SESSIONS, DÉFENSES CSRF ET IDENTIFICATION DE LA FAILLE WEBSOCKET SOUS PROXY

**Mission ID :** `ALICE-P1-HARDENING-006-INDEPENDENT-ACCEPTANCE-AND-EVIDENCE-VERIFICATION`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Document :** `ALICE_P1_GATE006_COOKIE_AND_WEBSOCKET_REVIEW.md`  
**Date :** 24 Novembre 2026  
**Auditeur :** Independent Security Auditor  

---

## 1. AUDIT DE L'ARCHITECTURE DES COOKIES DE SESSION

### 1.1. Émission et Paramètres des Cookies (`POST /api/pair`)
L'analyse forensique de `main2.py` (lignes 4684-4710) montre la génération suivante après validation du code PIN d'appairage à usage unique :

```python
new_session_id = secrets.token_hex(16)
new_token = secrets.token_urlsafe(32)
new_csrf = secrets.token_hex(16)

is_secure = (get_transport_security_mode() in ("TLS_ENFORCED_PRODUCTION", "TLS_ACTIVE_DEVELOPMENT"))
secure_flag = "; Secure" if is_secure else ""

# Cookie de session
session_cookie = f"alice_session={new_session_id}:{new_token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400{secure_flag}"
self.send_header("Set-Cookie", session_cookie)

# Cookie CSRF
csrf_cookie = f"alice_csrf={new_csrf}; Path=/; SameSite=Strict; Max-Age=86400{secure_flag}"
self.send_header("Set-Cookie", csrf_cookie)
```

### 1.2. Évaluation des Attributs de Sécurité
| Attribut | `alice_session` | `alice_csrf` | Conformité / Évaluation |
| :--- | :---: | :---: | :--- |
| **`HttpOnly`** | **Présent** | **Absent (volontaire)** | **CONFORME.** Protège le secret de session contre l'exfiltration XSS, tandis que le cookie CSRF reste lisible par le JavaScript client. |
| **`SameSite`** | `Strict` | `Strict` | **CONFORME.** Bloque l'envoi des cookies lors de requêtes inter-sites (cross-site). |
| **`Path`** | `/` | `/` | **CONFORME.** Couvre l'ensemble de l'application. |
| **`Max-Age`** | `86400` (24h) | `86400` (24h) | **CONFORME.** Durée de vie bornée, cohérente avec le TTL serveur. |
| **`Domain`** | *Non spécifié* | *Non spécifié* | **CONFORME (Host-Only).** Empêche la propagation du cookie aux sous-domaines. |
| **`Secure`** | **Conditionnel** | **Conditionnel** | **NON CONFORME SOUS PROXY.** Voir section 1.3 ci-dessous. |

### 1.3. Constat d'Anomalie : Absence du drapeau `Secure` derrière Reverse Proxy
- **Description :** Dans une architecture avec terminaison TLS sur reverse proxy (Nginx, Caddy, Cloudflare Tunnel), la liaison entre le proxy et le backend ALICE s'effectue en HTTP en clair sur `127.0.0.1:8080`.
- **Mécanisme :**
  1. `get_transport_security_mode()` ne détecte aucun certificat local sur ALICE et renvoie `DEVELOPMENT_PLAINTEXT_DEGRADED`.
  2. `is_secure` vaut donc `False`.
  3. `secure_flag` devient une chaîne vide `""`.
  4. Le code ne vérifie **pas** l'en-tête `X-Forwarded-Proto: https`.
- **Conséquence :** Le cookie `alice_session` est transmis au navigateur client via HTTPS sans la directive `Secure`, ce qui permettrait son émission sur des canaux HTTP non chiffrés en cas de navigation mixte ou d'absence de HSTS strict.

---

## 2. AUDIT DE L'AUTHENTIFICATION WEBSOCKET

### 2.1. Handshake et Authentification par Cookie
Le protocole WebSocket extrait les cookies transmis lors de la requête initiale HTTP Upgrade (RFC 6455) :
- `ws_handler` parse l'en-tête `Cookie` via `http.cookies.SimpleCookie`.
- Extrait `alice_session` (`<session_id>:<token>`).
- Valide le couple via `WS_SESSION_MANAGER.verify_session(session_id, token)`.
- Si valide, la connexion est immédiatement enregistrée et authentifiée.
- Un repli de 5 secondes existe pour les clients n'utilisant pas de cookies (requérant une trame `{"type": "auth", "session_id": "...", "token": "..."}`).

---

## 3. FAILLE CRITIQUE : BYPASS D'AUTHENTIFICATION WEBSOCKET SOUS PROXY (CVSS 8.8)

### 3.1. Analyse Détaillée du Code Vulnérable
Dans `Jarvis Final - SITE/main2.py`, lignes 950-963 :

```python
    # 3. Authentification et Session (P1 / Hardening 006)
    client_ip = "127.0.0.1"
    if websocket.remote_address and len(websocket.remote_address) > 0:
        client_ip = websocket.remote_address[0]

    is_loopback = client_ip in ("127.0.0.1", "::1", "localhost")
    authenticated = False
    session_id = "desktop_local"

    # Si client loopback et origine locale/absente, autoriser avec session locale
    if is_loopback and (not origin or WS_SESSION_MANAGER.is_origin_allowed(origin)):
        authenticated = True
        session_id = "desktop_local"
        websocket.session_id = session_id
```

### 3.2. Scénario d'Attaque
1. ALICE est déployée en **Topologie A** (Nginx sur port 443 proxying vers `127.0.0.1:8765`), avec `ALICE_ALLOWED_ORIGINS=https://alice.mon-domaine.local`.
2. Un attaquant non appairé (aucun cookie, aucun PIN) ouvre une connexion WebSocket depuis son navigateur ou un script vers `wss://alice.mon-domaine.local/ws`.
3. Le reverse proxy Nginx ouvre une connexion TCP locale vers `127.0.0.1:8765`.
4. Le serveur WebSocket d'ALICE lit `websocket.remote_address[0]` qui vaut `127.0.0.1`.
5. La variable `is_loopback` est évaluée à `True`.
6. L'en-tête `Origin` vaut `https://alice.mon-domaine.local`, qui est présent dans `ALICE_ALLOWED_ORIGINS` (`is_origin_allowed` renvoie `True`).
7. **RÉSULTAT :** La condition est satisfaite. L'attaquant est immédiatement marqué `authenticated = True` avec le rôle `desktop_local`, lui donnant un contrôle total sur l'interface vocale et les commandes JARVIS **sans authentification**.

### 3.3. Cause Racine et Remédiation Requise
- **Cause :** `ws_handler` se base sur `websocket.remote_address` sans utiliser `get_trusted_client_ip` pour résoudre l'adresse réelle transmise dans `X-Forwarded-For`.
- **Remédiation requise :**
  1. Extraire les en-têtes de la requête WebSocket Upgrade (`websocket.request.headers`).
  2. Résoudre la véritable adresse client via `get_trusted_client_ip`.
  3. Ne considérer `is_loopback` comme vrai **QUE SI** l'IP réelle du client final est une adresse de bouclage et qu'aucun proxy ne transmet une IP distante.

---

## 4. DÉFENSE CONTRE LE CROSS-SITE WEBSOCKET HIJACKING (CSWSH)

- Lorsque la connexion provient d'un domaine externe (`Origin: https://evil.com`), `is_origin_allowed(origin)` renvoie `False`.
- La connexion est alors rejetée avec le code de fermeture `4003 Forbidden Origin` (ligne 946).
- **Limite constatée :** La protection CSWSH est efficace contre les sites tiers arbitraires, mais la faille de bypass loopback documentée ci-dessus neutralise toute sécurité lorsque l'attaquant interagit directement avec l'URL publique de l'application.

---

## 5. CONCLUSION DE LA REVUE

1. **Le stockage des secrets dans `localStorage` a été supprimé avec succès.**
2. **Le cookie `alice_session` utilise bien `HttpOnly; SameSite=Strict`.**
3. **Cependant, deux vulnérabilités bloquantes empêchent l'homologation de production :**
   - Le bypass de l'authentification WebSocket en Topologie A (reverse proxy local) accordant les droits `desktop_local` à tout visiteur.
   - L'omission du drapeau `Secure` sur les cookies émis derrière un reverse proxy HTTPS en clair sur la boucle locale.
