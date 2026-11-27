# ALICE_010 — CHANGELOG TECHNIQUE

- **`.git/config` (F03) :** Suppression du PAT GitHub de l'URL du remote `origin` via `git remote set-url origin https://github.com/siddick369-sys/Alice.git`.
- **`Jarvis Final - SITE/alice_core/security/rbac.py` (F02) :** Suppression du default-allow dans `check_action()`, ajout de `PUBLIC_CONVERSATIONAL_ACTIONS`, cartographie complète de toutes les actions dans `ACTION_TO_PERMISSION`, ajout de `("files", "read")` et `("web", "browse")`.
- **`Jarvis Final - SITE/alice_core/api_bridge.py` (F02) :** Contrôle RBAC dans `dispatch_extended_action()`, `/api/jobs/stats`, `/api/iot/routines`, `/api/vision/*` et trames WS (`barge_in`, `whisper_mode`, `followup_*`).
- **`Jarvis Final - SITE/main2.py` (F01, F02, F04) :** Suppression des contournements `session_id in RBAC._principals` dans `executer_action_pc()`, contrôle RBAC sur `file_upload` WS, ajout `user_id`/`role` dans `/api/pair`, et lecture bornée du corps `POST` + `Connection: close` avant HTTP `403` dans `MobileHandler.do_POST`.
- **`Jarvis Final - SITE/mobile/app.js` (F01) :** Isolation multi-compte IndexedDB (`aliceOfflineDB_<ownerId>`, filtre `owner_id`, verrou de transition `accountTransitionLock`, compteur `accountEpoch` anti-callback tardif, purge complète au logout/expiration/changement de compte).
- **`Jarvis Final - SITE/alice_web_guard.py` & `alice_core/automation/web_agent.py` (F05) :** Rejet `userinfo`, retrait du port `8080`, déballage `ipv4_mapped`, et pinning IP `_pin_dns_to_validated_ips()` anti-DNS rebinding.
- **`Jarvis Final - SITE/alice_rag.py` (F07) :** Garde-fous anti-ZIP bomb et anti-path traversal dans `extract_text_from_docx()` et `extract_text_from_epub()`.
- **`tests/security/test_p1_remediation_010_adversarial.py` :** Nouvelle suite adversariale (11 tests).
