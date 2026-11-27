# ALICE_010 — MATRICE DES TESTS ADVERSARIAUX

| Suite / Test | Commande | Tests | PASS | FAIL | ERR | Exit | Log |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `tests\security\test_p1_remediation_010_adversarial.py` | `venv\Scripts\python.exe tests\security\test_p1_remediation_010_adversarial.py` | 11 | 11 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\rem010_adv.txt` |
| `tests\security\test_p1_remediation_007_real_sockets.py` | `venv\Scripts\python.exe tests\security\test_p1_remediation_007_real_sockets.py` | 31 | 31 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\p1_007.txt` |
| `tests\security\test_p1_production_exposure_006.py` | `venv\Scripts\python.exe tests\security\test_p1_production_exposure_006.py` | 23 | 23 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\p1_006.txt` |
| `Jarvis Final - SITE\tests\run_all_tests.py` | `venv\Scripts\python.exe "Jarvis Final - SITE\tests\run_all_tests.py"` | 23 | 23 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\m007.txt` |
| `tests\alice_ultimate\` (waves + E2E) | `venv\Scripts\python.exe -m unittest discover ...` & `test_e2e_api_ws_bridge` | 45 | 45 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\ultimate_*.txt` |
| `test_acceptance_004_master.py` (P0) | `venv\Scripts\python.exe ...\test_acceptance_004_master.py` | 86 | 86 | 0 | 0 | `0` | `%TEMP%\ALICE_REM_010_LOGS\p0_master.txt` |

- **NOT_RUN :** `tests/alice_ultimate/performance/test_benchmarks.py` (non relancé pour préserver `benchmark_results.json` intact : `B041282E...`).
