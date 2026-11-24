# 🛡️ ALICE — AUDIT DE DURCISSEMENT P1 EXPOSITION PRODUCTION
## RAPPORT D'AUDIT PRÉ-REMÉDIATION & MODÉLISATION DES MENACES (MISSION 006)

**Mission ID :** `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Classification :** RAPPORT D'AUDIT FORENSIQUE DE SÉCURITÉ P1  
**Référence socle :** `ALICE-P0-FINAL-CERTIFICATION-GATE-005` (`APPROVED` — 86/86 PASS)  
**Date :** 24 Novembre 2026  
**Auteur :** Lead Security & Architecture Auditor  

---

## 1. CONTEXTE ET OBJECTIFS D'AUDIT

Le socle de sécurité critique P0 a été officiellement homologué lors de la mission `ALICE-P0-FINAL-CERTIFICATION-GATE-005` (86 tests adversariaux validés, intégrité mémoire multi-processus garantie, exécution de code arbitraire éliminée, vérification matérielle Home Assistant en place).

Néanmoins, la certification P0 avait identifié deux risques résiduels majeurs de niveau P1 devant impérativement être résolus avant toute exposition en production :

1. **`RISK-P1-BIND-ALL-INTERFACES-8080`** : Les serveurs HTTP mobile (`8080`) et WebSocket (`8765`) étaient historiquement liés en dur sur `0.0.0.0`, exposant l'ensemble des interfaces réseau de l'hôte sans prise en charge native d'une liaison sur interface dédiée (ex: `127.0.0.1` en aval d'un reverse proxy TLS) ni validation fine des topologies de déploiement.
2. **`RISK-P1-LOCALSTORAGE-TOKEN`** : Le jeton d'authentification de session mobile était stocké dans le `localStorage` du navigateur du smartphone (`alice_token`), le rendant vulnérable à toute fuite en cas de faille XSS et maintenant une persistance excessive sur le client.

En complément, l'audit a couvert la validation des en-têtes reverse proxy (protection contre l'usurpation d'IP via injection `X-Forwarded-For`), l'audit exhaustif des puits XSS (sinks) dans le frontend mobile, ainsi que l'absence d'en-têtes HTTP de sécurité modernes (CSP, HSTS, nosniff, frame-ancestors).

---

## 2. AUDIT TECHNIQUE DÉTAILLÉ DE LA BASELINE

### 2.1. Analyse des liaisons réseau et interfaces (`main2.py`)
- **Constat initial :**
  - Le serveur HTTP mobile était instancié via `http.server.HTTPServer(("", 8080), MobileHandler)`. L'adresse vide `""` ou `0.0.0.0` force l'écoute sur toutes les cartes réseau de la machine (WiFi, Ethernet, interfaces virtuelles, VPN).
  - Le serveur WebSocket était démarré sur `websockets.serve(..., "0.0.0.0", 8765)`.
  - Aucune variable d'environnement ne permettait d'ajuster l'adresse d'écoute sans modifier le code source.
- **Vecteur de risque :**
  - Dans un environnement de production avec reverse proxy local (ex: Nginx, Caddy, Cloudflare Tunnel), l'application continuait d'exposer ses ports en clair directement sur le réseau local ou public, contournant la barrière de filtrage du proxy.
  - Risque d'interception de flux en clair (Man-in-the-Middle) et de contournement des règles de pare-feu applicatif (WAF).

### 2.2. Analyse de la résolution d'adresses IP clientes et confiance proxy
- **Constat initial :**
  - La fonction `get_trusted_client_ip` s'appuyait sur une allowlist statique `TRUSTED_PROXIES` sans validation stricte des réseaux CIDR (ex: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - L'analyse des en-têtes ne prenait pas en compte les en-têtes alternatifs normalisés tels que `Forwarded` (RFC 7239) ni les fournisseurs courants comme Cloudflare (`CF-Connecting-IP`).
  - La présence d'un port dans l'adresse transmise (ex: `198.51.100.1:44321`) provoquait l'échec du parsing `ipaddress.ip_address`.
- **Vecteur de risque :**
  - Un attaquant distant envoyant un en-tête `X-Forwarded-For: 127.0.0.1` vers un serveur n'étant pas derrière un proxy de confiance pouvait tenter de contourner les restrictions d'accès locales ou falsifier les journaux d'audit de sécurité.

### 2.3. Audit exhaustif des puits XSS (Frontend Mobile)
- **Fichiers analysés :**
  - `Jarvis Final - SITE/mobile/app.js`
  - `Jarvis Final - SITE/mobile/index.html`
  - `Jarvis Final - SITE/mobile/orb.js`
  - `Jarvis Final - SITE/mobile/style.css`
- **Recherche automatisée et manuelle de puits dangereux :**
  - `innerHTML` : **0 occurrence**
  - `outerHTML` : **0 occurrence**
  - `document.write` / `document.writeln` : **0 occurrence**
  - `eval()` / `Function()` / `setTimeout(string)` : **0 occurrence**
  - Attributs d'événements inline (`onclick=`, `onload=`) : **0 occurrence**
- **Résultat :**
  - L'interface mobile utilise systématiquement `element.textContent` et des écouteurs d'événements `addEventListener`. Aucune injection directe de code HTML non assaini n'a été détectée.
  - **Défaut d'exposition résiduel détecté dans `index.html` :**
    - La ligne 39 contenait une adresse IP privée en dur : `http://192.168.1.23:8080`.
    - Cette référence divulguait l'adressage interne de l'environnement de développement et nuisait à la portabilité de l'application.

### 2.4. Analyse du cycle de vie du jeton d'authentification (`localStorage`)
- **Constat initial :**
  - Lors de l'appairage réussi sur `/api/pair`, le serveur renvoyait le jeton `{ "token": "..." }`.
  - Le script `mobile/app.js` enregistrait ce jeton directement via `localStorage.setItem("alice_token", data.token)`.
  - Lors de la connexion WebSocket, le jeton était lu depuis `localStorage` et transmis dans une trame JSON `{ "type": "auth", "token": token }`.
- **Vecteur de risque :**
  - Tout script malveillant (via inclusion de bibliothèque compromise ou futur composant tiers) aurait un accès direct en lecture à `localStorage`, permettant l'exfiltration silencieuse du jeton.
  - Le jeton persistait indéfiniment sur l'appareil même après fermeture de session ou expiration logique côté serveur.

### 2.5. Absence d'en-têtes HTTP de sécurité et de CSP
- **Constat initial :**
  - `MobileHandler` héritait de `SimpleHTTPRequestHandler` sans injecter de Content Security Policy (CSP), de Strict-Transport-Security (HSTS), de `X-Content-Type-Options`, de `X-Frame-Options` ou de `Permissions-Policy`.
- **Vecteur de risque :**
  - Exposition aux attaques par détournement de clic (Clickjacking), injection de mime-types falsifiés (MIME sniffing) et absence de restrictions sur le chargement de ressources externes.

---

## 3. MODÉLISATION DES MENACES PAR TOPOLOGIE

| Topologie | Description | Risque Majeur | Mesure d'Atténuation Requise |
| :--- | :--- | :--- | :--- |
| **Topologie A** | **Reverse Proxy Local (Recommandé Prod)**<br>Nginx/Caddy écoute sur `0.0.0.0:443/8443` (TLS public). ALICE écoute uniquement sur `127.0.0.1:8080` (HTTP) et `127.0.0.1:8765` (WS). | Exposition directe des ports backend sur le réseau local ou public en clair. | `ALICE_BIND_ADDRESS="127.0.0.1"`<br>`ALICE_TRUSTED_PROXIES="127.0.0.1,::1"` |
| **Topologie B** | **Reverse Proxy Distant / DMZ**<br>Proxy dédié sur hôte distinct ou passerelle. ALICE écoute sur une IP LAN privée spécifique. | Usurpation d'en-tête IP client si n'importe quel nœud LAN envoie des en-têtes proxy. | `ALICE_BIND_ADDRESS="<IP_LAN>"`<br>`ALICE_TRUSTED_PROXIES="<IP_PROXY_DEDIE>"` |
| **Topologie C** | **Accès Direct LAN Mobile (Usage Domestique Isolé)**<br>Connexion directe du smartphone au PC sur le WiFi local. | Risque de compromission si le réseau WiFi est partagé ou non sécurisé. | Défaut contrôlé `0.0.0.0`<br>Sécurisation par cookies `HttpOnly; SameSite=Strict`, CSP stricte et code PIN à usage unique. |

---

## 4. CONCLUSION DE L'AUDIT

Les vulnérabilités P1 documentées sont confirmées et requièrent une remédiation architecturale ciblée :
1. Centralisation de la configuration réseau avec support natif des liaisons de bouclage, des ports configurables et du filtrage CIDR des proxys de confiance.
2. Élimination du stockage des secrets dans `localStorage` au profit de cookies de session sécurisés `HttpOnly; SameSite=Strict` avec jeton CSRF dédié.
3. Remplacement des adresses IP en dur dans l'interface par des variables ou invites dynamiques.
4. Injection systématique d'en-têtes de sécurité HTTP durcis (CSP stricte sans unsafe-eval, HSTS, frame-ancestors 'none').
5. Maintien absolu de la rétrocompatibilité mobile et de la validation intégrale des 86 tests P0.
