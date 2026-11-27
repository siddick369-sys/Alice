# 🛡️ ALICE-P1-REMEDIATION-009 — REVUE RBAC FAIL-CLOSED (`FINDING-03`)

- **Défaut initial :** `RBAC.authorize()` autorisait par défaut `Role.OWNER` sur une permission inconnue absente de `PERMISSION_MATRIX`.
- **Cause racine :** Fallback permissif résiduel sur ressource/permission non déclarée.
- **Correction :** `RBAC.authorize()` (`alice_core/security/rbac.py:366-380`) rejette désormais systématiquement tout rôle invalide/inconnu et toute permission absente de `PERMISSION_MATRIX` (en complément du rejet strict des actions inconnues/vides/`None` dans `check_action()`).
- **Couverture des call sites :** `test_all_main2_actions_covered_by_rbac` extrait programmatiquement toutes les actions de `main2.py` et vérifie qu'aucune n'est absente de `ACTION_TO_PERMISSION | PUBLIC_CONVERSATIONAL_ACTIONS` (`missing == set()`).
- **Preuve :** `TestFinding03RBACStrictFailClosed` (`4/4 PASS`) + `test_wave1_rbac` (`4/4 PASS`).
