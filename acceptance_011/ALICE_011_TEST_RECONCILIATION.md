# ALICE_011 — RÉCONCILIATION DES TESTS

| Suite | Fichier / Commande | Collectés / Exécutés | PASS | FAIL/ERR | Exit |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Remediation 010 | `tests\security\test_p1_remediation_010_adversarial.py` | 11 / 11 | 11 | 0 | `0` |
| P1 007 Real Sockets | `tests\security\test_p1_remediation_007_real_sockets.py` | 31 / 31 | 31 | 0 | `0` |
| P1 006 Exposure | `tests\security\test_p1_production_exposure_006.py` | 23 / 23 | 23 | 0 | `0` |
| Mission 007 | `Jarvis Final - SITE\tests\run_all_tests.py` | 23 / 23 | 23 | 0 | `0` |
| Ultimate 008 Waves | `python -m unittest discover -s tests\alice_ultimate -p test_wave*.py` | 42 / 42 | 42 | 0 | `0` |
| Ultimate 008 E2E | `python -m unittest tests.alice_ultimate.integration.test_e2e_api_ws_bridge` | 3 / 3 | 3 | 0 | `0` |
| P0 Master (hors dépôt) | `...\scratch\test_acceptance_004_master.py` | 86 / 86 | 86 | 0 | `0` |
| Ultimate 008 Benchmarks | `tests\alice_ultimate\performance\test_benchmarks.py` | 1 / 0 (`NOT_RUN`) | — | — | — |
| Frontend Build (externe) | `tsc --noEmit` + `vite build --outDir %TEMP%\...` | 1 / 1 | 1 | 0 | `0` |

- **Réconciliation exacte :** `219` tests Python exécutés (`219 PASS`, `0 FAIL`, `0 ERROR`, `0 SKIPPED`, `1 NOT_RUN` pour préserver `benchmark_results.json`) + `1` build frontend `PASS` + `1` sonde adversariale indépendante (`independent_probe.py`) confirmant `F02`, `F05`, `F07`. Les chiffres annoncés par la Mission 010 (`219 PASS`) concordent exactement avec la ré-exécution indépendante.
