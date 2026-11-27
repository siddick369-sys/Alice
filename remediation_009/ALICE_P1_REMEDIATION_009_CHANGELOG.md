# 🛡️ ALICE-P1-REMEDIATION-009 — CHANGELOG TECHNIQUE

**Mission ID :** `ALICE-P1-REMEDIATION-009`  

| Fichier | Fonction / Zone | Finding | Modification | Tests Associés |
| :--- | :--- | :---: | :--- | :--- |
| `Jarvis Final - SITE/main2.py` | `WSSessionManager.is_session_active()` & `revoke_session()` | `FINDING-01` | Ajout de `is_session_active()` ; `revoke_session()` marque `_revoked = True`, retire de `CONNECTED_CLIENTS` et planifie `ws.close(code=4001)` via `run_coroutine_threadsafe`. | `test_active_ws_closed_immediately_on_revoke_and_multi_conn_isolated` |
| `Jarvis Final - SITE/main2.py` | `ws_handler()` | `FINDING-01` & `FINDING-06` | Liaison `_auth_token`, `_ws_loop`, `_revoked` ; contrôle `_reject_if_session_invalid()` à chaque trame et avant chaque action privilégiée ; remplacement de `verify_token` par `verify_session(session_id, tok)` avec refus de changement de `session_id`. | `test_no_privileged_action_or_identity_switch_after_revocation`, `test_verify_token_removed_and_ws_auth_revalidation_paths` |
| `Jarvis Final - SITE/main2.py` | `is_request_https_secure()` & `get_trusted_client_ip()` | `FINDING-06` | Extraction correcte de `handler["headers"]` ; rejet des en-têtes dupliqués (`get_all`), des entrées vides dans `XFF`, et normalisation `ipv4_mapped`. | `test_duplicate_xff_headers_rejected`, `test_empty_entry_in_xff_chain_rejected`, `test_ipv4_mapped_ipv6_normalized_in_xff` |
| `Jarvis Final - SITE/alice_core/security/rbac.py` | `RBACPolicyEngine.authorize()` | `FINDING-03` | Suppression du fallback `OWNER` sur permission inconnue ; rejet explicite de tout rôle inconnu ou permission absente de `PERMISSION_MATRIX`. | `test_unknown_empty_none_unmapped_actions_denied_even_for_owner`, `test_unknown_role_and_unknown_permission_denied`, `test_all_main2_actions_covered_by_rbac` |
| `Jarvis Final - SITE/mobile/app.js` | `buildWebSocketUrl()` & `connectWS()` | `FINDING-02` | Construction `wss://<host><basePath>/ws` en HTTPS (sans `:8765`), refus `ws://` en production, maintien du mode local HTTP dev, garde `if (!WS_URL)` dans `connectWS()`. | `TestFinding02MobileWssRouting` (6 tests via Node) |
