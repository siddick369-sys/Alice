# ALICE_011 — AUDIT INDÉPENDANT RBAC FAIL-CLOSED (F02)

- **Statut F02 :** **`FIXED_VERIFIED`**
- **Couverture recalculée indépendamment (`independent_probe.py`) :**
  - `main2.py` + `api_bridge.py` : `0` action non classifiée (`UNMAPPED_ACTIONS = []`).
  - `PUBLIC_CONVERSATIONAL_ACTIONS` (8 actions minimales : `alice_status`, `alerte_meteo`, `ha_anniversaires`, `ha_oeufs`, `meteo`, `sport_classement`, `sport_live`, `sport_resultats`) : aucune action système, fichier, réseau ou domotique physique.
- **Tests adversariaux vérifiés (`independent_probe.py` + `TestF02RBACFailClosed`) :**
  - `GUEST` autorisé sur `meteo`, refusé sur `web_agent_check`, `iot_health`, `iot_eco`, `daily_briefing`, `executive_briefing`, `knowledge_graph_add`, `match_web`, YouTube, volume, fichiers.
  - Session absente (`""`, `None`), inconnue (`unreg_011`), révoquée (`revoked_010`) : refusées sur `executer_action_pc` et `RBAC.check_action`.
  - Actions inconnues/vides/`None`/casse mixte : refusées (`OWNER` inclus pour actions inconnues).
