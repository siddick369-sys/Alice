# 🛡️ ALICE-P1-REMEDIATION-007 — CHANGELOG TECHNIQUE

**Mission ID :** `ALICE-P1-REMEDIATION-007`  
**Repository :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  
**Branche :** `main` | **HEAD :** `fa8a66d`  
**Date :** 25 Novembre 2026  

---

## 1. FICHIERS APPLICATIFS MODIFIÉS

### 1.1. `Jarvis Final - SITE/main2.py`

| Fonction / Classe | Problème Traité | Modification Effectuée | Justification & Impact | Tests Associés |
| :--- | :--- | :--- | :--- | :--- |
| `NetworkConfig` & `get_network_config()` | `ALICE_TRUSTED_PROXIES=""` retombait silencieusement sur `127.0.0.1,::1` ; les proxies invalides étaient ignorés sans bloquer le démarrage. | Distinction entre `ALICE_TRUSTED_PROXIES is None` (défaut) et chaîne vide explicite ; collecte des entrées non-IP/CIDR dans `invalid_proxies`. | Empêche un démarrage permissif si la liste des proxies approuvés est mal configurée en mode proxy. | `TLS-04`, `TLS-05` |
| `is_loopback_ip()`, `is_trusted_proxy_ip()`, `has_proxy_forwarding_headers()` | Comparaisons de chaînes naïves sur `127.0.0.1`/`::1` sans support IPv4-mapped IPv6 (`::ffff:127.0.0.1`) ni détection des headers de forwarding. | Création de validateurs IP stricts basés sur `ipaddress` avec normalisation `ipv4_mapped`, support CIDR et détection des 6 en-têtes proxy standard. | Normalisation IPv4/IPv6 robuste et séparation stricte entre connexion directe et connexion proxifiée. | `IP-01`, `IP-02`, `WS-03` |
| `ws_handler(websocket)` | **Critique (Lot A) :** `websocket.remote_address[0] == "127.0.0.1"` accordait automatiquement `desktop_local` aux clients arrivant via reverse proxy local. | Extraction unique des en-têtes Upgrade (`websocket.request.headers`), séparation stricte `peer_ip` / `client_ip` via `get_trusted_client_ip`, et interdiction absolue de `desktop_local` si `ALICE_TLS_TERMINATION=proxy` ou si un header de forwarding est présent. | Élimine définitivement le contournement d'authentification WebSocket sous reverse proxy. | `WS-01` à `WS-12` |
| `is_production_env()`, `get_transport_security_mode()` | **Critique (Lot C) :** `JARVIS_ENV=production` exigeait des certificats locaux même derrière un reverse proxy TLS, provoquant `FAIL_CLOSED_TLS_REQUIRED`. Détection manquante des conflits `ALICE_ENV`/`JARVIS_ENV`. | Ajout du mode `ALICE_TLS_TERMINATION=proxy` (`PROXY_TLS_TERMINATED`) exigeant `trusted_proxies` non vide/valide et bind loopback (`127.0.0.1`/`::1`) pour HTTP et WS. Rejet fail-closed (`FAIL_CLOSED_CONFIG_CONFLICT`, `FAIL_CLOSED_PROXY_PUBLIC_BIND`, `FAIL_CLOSED_PROXY_CONFIG_INVALID`). | Permet la terminaison TLS sur reverse proxy sans affaiblir le fail-closed en production. | `TLS-01` à `TLS-08` |
| `is_request_https_secure(handler, peer_ip)` | **Élevé (Lot B) :** `Secure` sur `alice_session` et `alice_csrf` ignorait `X-Forwarded-Proto: https` derrière un proxy TLS. | Vérification stricte : TLS direct OU (`is_trusted_proxy_ip(peer_ip)` ET `X-Forwarded-Proto == "https"` unique sans virgule/en-têtes multiples). | Empêche la perte de l'attribut `Secure` sous proxy tout en bloquant l'usurpation `X-Forwarded-Proto`. | `COOKIE-01` à `COOKIE-07` |
| `MobileHandler._set_security_headers()` | HSTS absent lorsque TLS est terminé par un reverse proxy approuvé. | Émission de `Strict-Transport-Security` basée sur `is_request_https_secure()`. | Garantit l'en-tête HSTS sur les réponses HTTPS directes et proxifiées. | `COOKIE-01`, `COOKIE-02` |
| `MobileHandler.do_POST` (`/api/pair` & `/api/revoke_session`) | Émission potentielle de cookies non-`Secure` en production HTTP ; attributs incohérents à la révocation. | Refus HTTP `403` sans cookie en production si `not is_secure` ; ajout de `{secure_flag}` sur les `Set-Cookie` de suppression (`Max-Age=0`) ; exigence stricte de `X-CSRF-Token` si cookie présent lors de la révocation. | Garantit qu'aucun cookie de session non-`Secure` n'est émis en production. | `COOKIE-01` à `COOKIE-10` |
| `start_ws()` & `start_mobile_http_server()` | Ne vérifiaient que `FAIL_CLOSED_TLS_REQUIRED` et tentaient de charger `get_ssl_context()` en mode proxy. | Blocage systématique sur tout mode `FAIL_CLOSED_*` ; `ssl_ctx = None` en mode `PROXY_TLS_TERMINATED` sur loopback. | Cohérence stricte entre démarrage réseau et politique de sécurité. | `TLS-03` à `TLS-08` |

---

## 2. FICHIERS DE TESTS AJOUTÉS

| Fichier | Description | Nombre de Tests |
| :--- | :--- | :---: |
| `tests/security/test_p1_remediation_007_real_sockets.py` | Suite de tests d'acceptation réseau réels sur véritables sockets TCP (`websockets.serve` + `http.server.HTTPServer` + certificats X.509 temporaires) couvrant `WS-01`..`WS-12`, `COOKIE-01`..`COOKIE-10`, `TLS-01`..`TLS-08`, et normalisation IPv4/IPv6. | **31 tests** |

---

## 3. FICHIERS AUDITÉS NON MODIFIÉS

- `Jarvis Final - SITE/mobile/app.js` : Vérifié conforme (zéro écriture dans `localStorage`, protocole dynamique `wss:` sous `https:`, double-submit CSRF).
- `Jarvis Final - SITE/mobile/index.html` : Vérifié conforme (aucune IP privée codée en dur, zéro script inline).
- `Jarvis Final - SITE/alice_modules.py` & `jarvis_agent.py` : Vérifiés conformes (aucune régression P0).
