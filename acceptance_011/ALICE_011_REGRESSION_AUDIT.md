# ALICE_011 — AUDIT DE NON-RÉGRESSION (006–009, FRONTEND, INTÉGRATIONS)

- **Aucune régression fonctionnelle ou sécuritaire détectée** après la remédiation 010 :
  - **WebSocket / WSS / Cookies / TLS (006–007) :** `31/31 PASS` sur sockets TCP/WS réels (`WS-01`..`12`, `COOKIE-01`..`10`, `TLS-01`..`08`) + `23/23 PASS` (`test_p1_production_exposure_006.py`).
  - **Socle P0 (004) :** `86/86 PASS`.
  - **Mission 007 :** `23/23 PASS` (`run_all_tests.py`).
  - **Mission 008 (waves + E2E) :** `45/45 PASS` (`42` waves + `3` E2E).
  - **Frontend Desktop :** `npx tsc --noEmit` (`0`) et `npx vite build --outDir %TEMP%\ALICE_ACC_011\frontend_dist` (`0`, `2.08s`) sans écriture dans le dépôt.
- **Intégrations externes & Infrastructure :**
  - `HA_URL`/`HA_TOKEN`, `token.pickle` Google Workspace et caméra RTSP physique absents sur l'hôte (non testables en réel).
  - Reverse proxy Nginx/Caddy et pare-feu de production : **`INFRASTRUCTURE_NOT_VERIFIED`**.
