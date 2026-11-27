# 🛡️ ALICE-P1-REMEDIATION-007 — GUIDE DE DÉPLOIEMENT CORRIGÉ

**Mission ID :** `ALICE-P1-REMEDIATION-007`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Statut :** Cohérent avec l'implémentation réelle de `main2.py`  

> **Note :** Ce document décrit l'architecture technique et les paramètres attendus par le code corrigé. Aucune opération de déploiement réel n'a été exécutée durant la mission.

---

## 1. ARCHITECTURES DE PRODUCTION SUPPORTÉES (FAIL-CLOSED)

Le backend ALICE (`main2.py`) impose une politique **fail-closed** en production (`ALICE_ENV=production` et `JARVIS_ENV=production` cohérents). Deux topologies de production sont explicitement supportées :

### Mode 1 — TLS Direct (`ALICE_TLS_TERMINATION=direct`, défaut)
Le backend Python termine lui-même TLS/WSS à l'aide de certificats locaux valides.
- **Variables requises :**
  - `ALICE_ENV=production` et `JARVIS_ENV=production`
  - `ALICE_TLS_TERMINATION=direct`
  - `ALICE_SSL_CERT=<chemin_cert.pem>`
  - `ALICE_SSL_KEY=<chemin_key.pem>`
- **Comportement fail-closed :** Si le certificat ou la clé est absent, illisible ou non apparié, `get_transport_security_mode()` renvoie `FAIL_CLOSED_TLS_REQUIRED` et les serveurs HTTP/WS refusent de démarrer. Aucun fallback HTTP en clair.

### Mode 2 — TLS Terminé par Reverse Proxy Approuvé (`ALICE_TLS_TERMINATION=proxy`)
Le reverse proxy (Nginx ou Caddy) termine TLS/WSS en façade publique et transmet le trafic au backend Python sur l'interface locale de bouclage (`127.0.0.1` ou `::1`).
- **Variables requises :**
  - `ALICE_ENV=production` et `JARVIS_ENV=production`
  - `ALICE_TLS_TERMINATION=proxy`
  - `ALICE_BIND_ADDRESS=127.0.0.1` *(obligatoirement loopback)*
  - `ALICE_HTTP_PORT=8080`
  - `ALICE_WS_BIND_ADDRESS=127.0.0.1` *(obligatoirement loopback)*
  - `ALICE_WS_PORT=8765`
  - `ALICE_TRUSTED_PROXIES=127.0.0.1,::1` *(non vide, IP/CIDR valides uniquement)*
  - `ALICE_ALLOWED_ORIGINS=https://alice.example.com` *(remplacer par le domaine réel)*
- **Comportement fail-closed :**
  - Si `ALICE_TRUSTED_PROXIES` est vide ou contient un nom d'hôte/IP invalide -> `FAIL_CLOSED_PROXY_CONFIG_INVALID` (arrêt).
  - Si `ALICE_BIND_ADDRESS` ou `ALICE_WS_BIND_ADDRESS` est une adresse publique/non-loopback (ex: `0.0.0.0`) -> `FAIL_CLOSED_PROXY_PUBLIC_BIND` (arrêt).
  - Si `ALICE_ENV` et `JARVIS_ENV` sont contradictoires -> `FAIL_CLOSED_CONFIG_CONFLICT` (arrêt).

---

## 2. CONTRAT DU REVERSE PROXY (NGINX — EXEMPLE DE CONFIGURATION)

> **Avertissement :** L'exemple ci-dessous illustre le contrat attendu par `main2.py`. Adaptez le `server_name` et les chemins de certificats à votre infrastructure réelle.

Le proxy **doit impérativement écraser** les en-têtes `X-Forwarded-For`, `X-Real-IP` et `X-Forwarded-Proto` fournis par le client externe afin d'empêcher toute usurpation :

```nginx
server {
    listen 443 ssl http2;
    server_name alice.example.com;

    ssl_certificate     /etc/letsencrypt/live/alice.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alice.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Interface Web & API REST (/api/pair, /api/revoke_session, ...)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host              $host;
        # Écrase tout header XFF/X-Real-IP/XFP forgé par le client :
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Tunnel WebSocket sécurisé (WSS -> WS loopback)
    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "Upgrade";
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

---

## 3. COOKIES, AUTHENTIFICATION WEBSOCKET ET PARE-FEU

1. **Cookies (`alice_session` & `alice_csrf`) :**
   - `POST /api/pair` vérifie `is_request_https_secure()`. En production, si `X-Forwarded-Proto` est absent, vaut `http`, est multiple (`https, http`) ou provient d'un pair non approuvé, le backend **refuse** l'appairage (`403`) et n'émet aucun cookie.
   - Lorsque HTTPS est prouvé, `alice_session` est émis avec `HttpOnly; SameSite=Strict; Path=/; Max-Age=86400; Secure`, et `alice_csrf` avec `SameSite=Strict; Path=/; Max-Age=86400; Secure`.
2. **Authentification WebSocket :**
   - En mode `proxy`, aucune connexion ne reçoit le privilège `desktop_local`, même si le socket TCP provient de `127.0.0.1`. Chaque client doit s'authentifier via le cookie `alice_session` ou la poignée de main JSON `auth`.
3. **Pare-feu hôte (Firewall) :**
   - Bloquer tout trafic entrant externe sur les ports backend (`8080`, `8765`). Seuls les ports `443` (HTTPS/WSS) du reverse proxy doivent être accessibles depuis le réseau.
4. **Panne du reverse proxy :**
   - En cas d'arrêt du proxy, le backend reste isolé sur `127.0.0.1` et n'est pas joignable depuis l'extérieur.

---

## 4. ERREURS DE CONFIGURATION COURANTES ET ROLLBACK CONCEPTUEL

| Code d'État Retourné | Cause | Action Corrective |
| :--- | :--- | :--- |
| `FAIL_CLOSED_TLS_REQUIRED` | Mode `direct` en production sans certificat valide. | Fournir `ALICE_SSL_CERT` / `ALICE_SSL_KEY` valides ou basculer en mode `proxy` avec proxy configuré. |
| `FAIL_CLOSED_PROXY_PUBLIC_BIND` | Mode `proxy` avec `ALICE_BIND_ADDRESS=0.0.0.0` ou `::`. | Fixer `ALICE_BIND_ADDRESS=127.0.0.1` et `ALICE_WS_BIND_ADDRESS=127.0.0.1`. |
| `FAIL_CLOSED_PROXY_CONFIG_INVALID` | `ALICE_TRUSTED_PROXIES` vide ou contenant un hostname. | Fournir uniquement des IP ou CIDR explicites (ex: `127.0.0.1,::1`). |
| `FAIL_CLOSED_CONFIG_CONFLICT` | `ALICE_ENV` et `JARVIS_ENV` ont des valeurs différentes. | Aligner les deux variables sur la même valeur (`production` ou `development`). |

**Rollback conceptuel :** En cas d'anomalie après mise à jour, restaurer les fichiers modifiés vers la révision Git de référence (`fa8a66d` ou `b1f67aa` selon le périmètre) et re-valider la suite P0 avant toute remise en service locale.
