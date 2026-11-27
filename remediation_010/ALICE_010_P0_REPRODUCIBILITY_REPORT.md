# ALICE_010 — REPRODUCTIBILITÉ P0 & ERRATUM F06 (F06 & F09)

## 1. Erratum documentaire `main2.py` (F06)
- **Statut :** `FIXED_VERIFIED` *(erratum distinct sans modification rétroactive de `ALICE_008_ACCEPTANCE_REPORT.md`)*
- `ALICE_008_ACCEPTANCE_REPORT.md` (19:44:24) déclarait `main2.py = 6FD50736DD692B7A330580747BB1F703A86FED7411A59AC44540828D9FD9CF23`.
- `main2.py` a été modifié à 19:52:48 (`CFDB9D3E40ED1D536C131C7521936FDD589B1D37B57F2BAD29C07B951D9C96C0` en baseline 010), puis durci en Mission 010 (`0FC53575170FC536E32F1ACB6D5802FAF10052CDB396C338B7BF4B3D373166AF`).

## 2. Reproductibilité de la suite P0 (F09)
- **Statut :** `ACCEPTED_RISK` *(localisée et ré-exécutée, non copiée automatiquement dans le dépôt sans autorisation)*
- **Emplacement réel :** `C:\Users\USER\.gemini\antigravity\brain\9f43747e-d272-4f9c-bf13-f2fb641773ea\scratch\test_acceptance_004_master.py`.
- **Résultat post-remédiation 010 :** **86/86 PASS (100.0%)**, exit code `0`.
- **Recommandation :** Intégrer `test_acceptance_004_master.py` sous `tests/security/` lors d'un commit ultérieur autorisé et relever le timeout de `SCENARIO-D` (`5.0s` → `10.0s`) pour absorber l'import à froid de `google.genai`.
