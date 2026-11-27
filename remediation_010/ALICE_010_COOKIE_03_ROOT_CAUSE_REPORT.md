# ALICE_010 — ANALYSE CAUSE RACINE COOKIE-03 (F04)

- **Finding :** `F04` — Erreur `ConnectionAbortedError: [WinError 10053]` sur `test_cookie03_proxy_http_in_production_refused`
- **Statut :** `FIXED_VERIFIED`

## 1. Cause racine
Dans `Jarvis Final - SITE/main2.py`, `MobileHandler.do_POST` (`/api/pair`) vérifiait `is_request_https_secure()` et renvoyait HTTP `403` puis quittait la méthode **avant** de lire `Content-Length` depuis `self.rfile`. Sur Windows Winsock, la fermeture du socket serveur alors que le corps `POST` du client est encore dans le tampon de réception déclenchait un TCP RST (`WinError 10053`) avant que `http.client` ne lise la réponse `403`.

## 2. Correction appliquée (`main2.py`)
- Lecture bornée du corps HTTP (`self.rfile.read(min(content_length, 65536))`) avant le contrôle `is_production_env() and not is_secure`, puis fermeture propre (`self.close_connection = True`, en-tête `Connection: close`, `self.wfile.flush()`).
- Aucun affaiblissement de la politique fail-closed HTTPS/TLS ni de l'attribut `Secure`.

## 3. Preuve
- Exécution réelle sur sockets TCP de `tests/security/test_p1_remediation_007_real_sockets.py` : **31/31 PASS** (dont `COOKIE-03` PASS, `0` ERROR).
