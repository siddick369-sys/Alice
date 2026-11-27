# ALICE_011 — AUDIT REPRODUCTIBILITÉ P0 (F09)

- **Statut F09 :** **`PARTIALLY_REPRODUCIBLE`**
- **Constatations :**
  - Le script maître P0 (`test_acceptance_004_master.py`, SHA-256 `3E1FC453C19AFAEF71FDB6A56FB6905D2CA3FB11AEC9FF3E0585EB8343A8393A`) réside hors du dépôt Git (`C:\Users\USER\.gemini\antigravity\brain\9f43747e-d272-4f9c-bf13-f2fb641773ea\scratch\test_acceptance_004_master.py`).
  - Exécuté en lecture seule depuis son emplacement réel : **86/86 PASS (100.0%)**, exit code `0` (incluant `SCENARIO-D-IMPORT-SIDE-EFFECTS` → `THREADS: 1`).
  - Dette ouverte : tant que ce script n'est pas versionné dans le dépôt Git, la reproductibilité P0 dépend d'un répertoire externe de session.
