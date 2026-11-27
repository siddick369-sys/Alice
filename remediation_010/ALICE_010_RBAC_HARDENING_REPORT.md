# ALICE_010 — RAPPORT DE DURCISSEMENT RBAC (F02)

- **Finding :** `F02` — Contournement RBAC et autorisation default-allow
- **Statut :** `FIXED_VERIFIED`

## 1. Corrections appliquées
- **`Jarvis Final - SITE/alice_core/security/rbac.py` :**
  - Suppression du fallback permissif `return True, "Action standard autorisée."` dans `RBACPolicyEngine.check_action()`.
  - Ajout d'une liste blanche explicite `PUBLIC_CONVERSATIONAL_ACTIONS` (`meteo`, `alerte_meteo`, `sport_resultats`, `sport_classement`, `sport_live`, `alice_status`, `ha_anniversaires`, `ha_oeufs`).
  - Cartographie exhaustive dans `ACTION_TO_PERMISSION` de toutes les actions de `main2.py` et `api_bridge.py` (`web_agent_check`, `iot_health`, `iot_eco`, `daily_briefing`, `executive_briefing`, `knowledge_graph_*`, `create_doc`, `voir_ecran`, `youtube_play`, etc.), plus ajout de `("files", "read")` et `("web", "browse")` dans `PERMISSION_MATRIX`.
  - Normalisation `.strip().lower()`, rejet explicite des actions vides/`None`/inconnues et capture fail-closed sur exception.
- **`Jarvis Final - SITE/alice_core/api_bridge.py` :**
  - Contrôle RBAC systématique en tête de `dispatch_extended_action()` (`RBAC.check_action`), sur `/api/jobs/stats` (`ops:dashboard`), `/api/iot/routines` (`iot:routine_manage`), `/api/vision/*` (`vision:monitor`), et sur les trames WebSocket `barge_in`, `whisper_mode`, `followup_cancel`, `followup_toggle`.
- **`Jarvis Final - SITE/main2.py` :**
  - `executer_action_pc()` : suppression de tous les contournements `if session_id in RBAC._principals` ; application stricte de `RBAC.get_principal(session_id)` et `RBAC.check_action()` sur les commandes système, lecture/écriture fichiers, `match_web`, musique/YouTube, lancement d'applications, volume et captures d'écran.
  - `ws_handler()` (`file_upload`) : contrôle `RBAC.authorize(..., "files", "write")`.

## 2. Preuves (`tests/security/test_p1_remediation_010_adversarial.py`)
- `TestF02RBACFailClosed` (`6/6 PASS`) : couverture complète des actions de `main2.py`, refus `GUEST` sur `web_agent_check`/`iot_health`/`iot_eco`/`daily_briefing`/`match_web`/YouTube/fichiers, refus des sessions absentes, inconnues, révoquées et des actions vides/`None`/inconnues.
