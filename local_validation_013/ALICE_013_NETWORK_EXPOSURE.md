# ALICE_013_NETWORK_EXPOSURE.md
## Audit d'Exposition Réseau des Ports Locaux — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  

---

### 1. Analyse des Adresses de Liaison (Bindings)

| Service | Port | Binding Configuré | Adresses Réelles Observées | Risque Identifié |
|---|---|---|---|---|
| **Mobile HTTP / REST API** | `8080` | `0.0.0.0` (Toutes interfaces) | `127.0.0.1`, `localhost`, `10.231.0.4` | Exposition sur le réseau local Wi-Fi / Ethernet |
| **Passerelle WebSocket** | `8765` | `0.0.0.0` (Toutes interfaces) | `127.0.0.1`, `localhost`, `10.231.0.4` | Écoute non chiffrée `ws://` accessible sur le LAN |
| **Frontend Desktop Vite** | `5173` | Par défaut Vite (`localhost`) | `[::1]:5173` (IPv6 Loopback) | Restreint à la machine locale (Loopback) |

---

### 2. Justification Métier vs Risques de Sécurité

#### A. Pourquoi `0.0.0.0` a-t-il été retenu ?
Dans la vision produit d'ALICE, l'interface mobile PWA doit pouvoir être ouverte depuis un smartphone ou une tablette connecté au même réseau Wi-Fi local :
`Mobile : ouvrir http://192.168.1.23:8080 sur votre tel/tablette`  
Si le serveur HTTP et le WebSocket étaient liés strictement à `127.0.0.1`, aucun équipement mobile externe ne pourrait atteindre le serveur d'appairage.

#### B. Risques Associés en Mode Clair (`http://` et `ws://`)
1. **Écoute passive sur le Wi-Fi (Sniffing) :**  
   En mode local sans TLS (`DEVELOPMENT_PLAINTEXT_DEGRADED`), les cookies de session et les trames WebSocket transitent en clair. Sur un Wi-Fi ouvert ou partagé, un attaquant pourrait intercepter la session.
2. **Rejeu de Code PIN :**  
   Mitigé : Le code PIN est à usage unique et possède un TTL court (120 secondes). Un code intercepté après usage est immédiatement rejeté.
3. **Protection contre le Rebinding DNS et CSRF :**  
   Mitigé : La vérification stricte de l'en-tête `Origin` (`WS_SESSION_MANAGER.is_origin_allowed`) et la validation `X-CSRF-Token` sur toutes les requêtes POST empêchent un site web distant malveillant d'exécuter des actions à l'insu de l'utilisateur.

---

### 3. Recommandations de Durcissement pour la Production

1. En environnement de production (`ALICE_ENV=production`), le mode `FAIL_CLOSED_TLS_REQUIRED` est déjà codé dans `main2.py` pour forcer HTTPS/WSS ou exiger un reverse proxy TLS terminateur de confiance (`ALICE_TRUSTED_PROXIES`).
2. Pour un usage strictement monoposte (sans mobile externe), ajouter une variable de configuration d'environnement `ALICE_BIND_ADDRESS=127.0.0.1` pour permettre à l'utilisateur de restreindre l'écoute à la seule boucle locale s'il ne souhaite pas d'accès depuis son réseau local.
