# ALICE_011 — DÉCISION FINALE DE SÉCURITÉ

- **Mission ID :** `ALICE-P1-INDEPENDENT-ACCEPTANCE-011`
- **Décision Finale :** **`CONDITIONALLY_APPROVED`**
- **Autorisation de publication / déploiement / exposition publique :** **NON ACCORDÉE**

## Motivation
Les corrections techniques critiques et P1 (`F01` IndexedDB, `F02` RBAC fail-closed, `F04` COOKIE-03, `F05` SSRF/DNS pinning, `F07` ZIP bomb) sont indépendamment vérifiées (**219/219 PASS**, zéro régression détectée). Toutefois, la décision est maintenue à **`CONDITIONALLY_APPROVED`** en raison des réserves ouvertes suivantes :
1. **`F03` (`EXTERNAL_REVOCATION_NOT_VERIFIED`) :** La révocation du PAT GitHub sur GitHub.com n'est pas vérifiable localement et `GITHUB_TOKEN` reste présent dans les fichiers `.env` locaux.
2. **`F06` (`NOT_VERIFIED`) :** Divergence d'empreintes SHA-256 constatée dans `ALICE_010_HASH_MANIFEST.md` pour `main2.py` et `benchmark_results.json`.
3. **`F09` (`PARTIALLY_REPRODUCIBLE`) :** La suite P0 (86 tests) reste stockée hors du dépôt Git (`scratch/`).
4. **Infrastructure (`INFRASTRUCTURE_NOT_VERIFIED`) :** Reverse proxy Nginx/Caddy, certificats de production, pare-feu et services externes (HA, Google Workspace, RTSP) non présents sur l'hôte.
