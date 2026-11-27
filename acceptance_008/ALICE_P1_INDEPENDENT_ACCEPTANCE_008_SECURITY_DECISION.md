# 🛡️ ALICE-P1-INDEPENDENT-ACCEPTANCE-008 — DÉCISION DE SÉCURITÉ

**Mission ID :** `ALICE-P1-INDEPENDENT-ACCEPTANCE-008`  
**Date :** 25 Novembre 2026  

---

## DÉCISION OFFICIELLE

$$\mathbf{CONDITIONALLY\_APPROVED}$$

### Justification selon le Barème Section 13.1
- **Pourquoi pas `REJECTED` :** Aucun contournement d'authentification WebSocket via proxy (`WS-01`..`WS-12`), aucune fuite de cookie non-`Secure` en production (`COOKIE-01`..`COOKIE-10`), aucune faille CSRF, et aucun défaut fail-closed au démarrage (`TLS-01`..`TLS-08`) n'ont été reproduits. Les **215 tests** exécutés passent à 100%.
- **Pourquoi pas `APPROVED_FOR_NEXT_DEPLOYMENT_REVIEW` :** Les anomalies suivantes empêchent l'approbation directe pour revue de déploiement :

### Conditions Suspensives Obligatoires

1. **`COND-01` (Résolution `FINDING-02` — High) :** Aligner `mobile/app.js:12` et `ALICE_P1_REMEDIATION_007_DEPLOYMENT_GUIDE.md` afin que le client mobile sous reverse proxy se connecte au chemin `/ws` sur le port `443` (ou documenter un port WSS dédié cohérent avec le pare-feu).
2. **`COND-02` (Résolution `FINDING-01` — Medium-High) :** Fermer activement les connexions WebSocket ouvertes dans `CONNECTED_CLIENTS` lors de `WS_SESSION_MANAGER.revoke_session()` et re-vérifier l'état de session dans la boucle de réception `ws_handler`.
3. **`COND-03` (Résolution `FINDING-03` — Medium) :** Remplacer le comportement default-allow de `RBAC.check_action()` (`alice_core/security/rbac.py:375`) par une allowlist explicite des actions conversationnelles inoffensives.
4. **`COND-04` (Résolution `FINDING-04` & `FINDING-05`) :** Versionner la suite P0 `test_acceptance_004_master.py` dans `tests/security/` du dépôt Git, et fournir/valider la configuration réelle du reverse proxy et du pare-feu sur l'infrastructure cible.
