# ALICE_011 — REGISTRE DES FINDINGS (F01–F09)

| ID | Domaine | Sévérité | Statut Indépendant 011 | Preuves & Limites |
| :--- | :--- | :---: | :---: | :--- |
| `F01` | IndexedDB multi-compte | P1 | **`FIXED_VERIFIED`** | `app.js` + test Node.js A→B & callback tardif. |
| `F02` | RBAC fail-closed | CRITIQUE | **`FIXED_VERIFIED`** | `0` action non mappée, `TestF02RBACFailClosed` + `independent_probe.py`. |
| `F03` | GitHub PAT | CRITIQUE | **`EXTERNAL_REVOCATION_NOT_VERIFIED`** | `.git/config` propre (`0` PAT en historique), mais `GITHUB_TOKEN` présent dans `.env` et révocation GitHub.com non vérifiable. |
| `F04` | `COOKIE-03` / Socket | P1 | **`FIXED_VERIFIED`** | `test_p1_remediation_007_real_sockets.py` `31/31 PASS` sur sockets TCP réels. |
| `F05` | SSRF / DNS Pinning | P1 | **`FIXED_VERIFIED`** | `12/12` URLs rejetées + `_pin_dns_to_validated_ips` vérifié. |
| `F06` | Hash Manifest 010 | P2 | **`NOT_VERIFIED`** | `ALICE_010_HASH_MANIFEST.md` contenait des empreintes obsolètes pour `main2.py` (`0FC53575...` vs `65765272...`) et `benchmark_results.json` (`B041282E...` vs `2006BE7D...`). |
| `F07` | ZIP bomb DOCX/EPUB | P1 | **`FIXED_VERIFIED`** | Bornes réelles de lecture vérifiées sur 501 entrées, traversées, 22,5 Mo EPUB, 6 Mo DOCX. |
| `F08` | Clé biométrique | P2 | **`ACCEPTED_RISK`** | Clé RAM uniquement ; zéro fuite disque. |
| `F09` | Suite P0 hors dépôt | P2 | **`PARTIALLY_REPRODUCIBLE`** | `86/86 PASS` depuis `scratch/`, mais absente du dépôt Git. |
