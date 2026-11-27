# ALICE_011 — AUDIT COOKIE-03 & SOCKETS RÉELS (F04)

- **Statut F04 :** **`FIXED_VERIFIED`**
- **Inspection (`Jarvis Final - SITE/main2.py`, `MobileHandler.do_POST`) :**
  - Lecture bornée du corps HTTP (`min(content_length, 65536)`) effectuée avant le rejet `403` en production non-HTTPS, accompagnée de `self.close_connection = True`, `Connection: close` et `self.wfile.flush()`.
- **Preuve sur sockets TCP réels (`tests/security/test_p1_remediation_007_real_sockets.py`) :**
  - **31/31 PASS** (exit code `0`) : `COOKIE-01` à `COOKIE-10` (dont `COOKIE-03` HTTP via proxy en production → `403` sans cookie ni `WinError 10053`), `WS-01` à `WS-12` et `TLS-01` à `TLS-08`.
- **Limite :** Tests exécutés sur sockets loopback locaux ; reverse proxy Nginx/Caddy réel non déployé (`INFRASTRUCTURE_NOT_VERIFIED`).
