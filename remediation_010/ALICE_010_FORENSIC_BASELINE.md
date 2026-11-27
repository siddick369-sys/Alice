# ALICE_010 — FORENSIC BASELINE & PROTECTION DU WORKING TREE

- **Mission ID :** `ALICE-P1-REMEDIATION-010`
- **Dépôt (`git rev-parse --show-toplevel`) :** `C:/Users/USER/Desktop/Jarvis Final - SITE-V2`
- **Branche :** `main`
- **HEAD :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`
- **Statut Git initial :** `107` lignes (`7` fichiers suivis modifiés : `alice_rag.py`, `frontend/src/main.ts`, `knowledge/rag_index.json`, `main2.py`, `mobile/app.js`, `mobile/index.html`, `mobile/style.css` ; fichiers non suivis : `alice_core/`, `tests/`, `audit_gate_006/`, `remediation_007/`, `ALICE_008_*.md`).

## Empreintes SHA-256 initiales (pré-remédiation)
| Fichier | SHA-256 |
| :--- | :--- |
| `Jarvis Final - SITE\main2.py` | `CFDB9D3E40ED1D536C131C7521936FDD589B1D37B57F2BAD29C07B951D9C96C0` |
| `Jarvis Final - SITE\alice_core\security\rbac.py` | `C954E7F4F4B186CC514127BE4505DE06F1EC0B586AB108D6B787255A19643640` |
| `Jarvis Final - SITE\alice_core\api_bridge.py` | `8CB70CB5889FBCD47E8038F30DC4F1D07FBB5C036D33C1B4421199D7E5542C65` |
| `Jarvis Final - SITE\mobile\app.js` | `C9C279B9A60232AB32D3A229EEE34BD1F96F12311D129051FF1E16C6EEE0E06D` |
| `Jarvis Final - SITE\mobile\index.html` | `8449745607347C70D293605C27DFF78170C7963BC8BD2A54CCAA6299556617F3` |
| `Jarvis Final - SITE\mobile\sw.js` | `DBD5A82E2430E999849F8750C45FDBDCDF660F84E860749FF8C4448DD3C0384D` |
| `Jarvis Final - SITE\alice_web_guard.py` | `6D36A070D7CB2064E77393FFF556D85A4B930EA5B8C44492963E2728A3E7D635` |
| `Jarvis Final - SITE\alice_core\automation\web_agent.py` | `5F7BC43545343752C5F1CAFB88B80705B34805DC507C9369373DA59B341FA492` |
| `Jarvis Final - SITE\alice_rag.py` | `1341DD36E578F2629A2BBFC610F4D1AD7B00104FCB1679885AFD2D0594AF5BDA` |
| `Jarvis Final - SITE\alice_core\voice\voice_id.py` | `305293D93E1EFA8E781F19CAAF3024598CF107D9D9E00DD04A8718C021B5C872` |
| `Jarvis Final - SITE\alice_core\mobile_sync\offline_sync.py` | `295C59132C6C84967827540BE16C25AB7B82A774F646135A8B3D344E7AB9AEA3` |
| `tests\security\test_p1_production_exposure_006.py` | `D5B924EBB1050451DBC2F07006847128C5421DA7C73DBE01AFE39C85E39172D9` |
| `tests\security\test_p1_remediation_007_real_sockets.py` | `580728D5F402BCBBF091D783A2A23B133D2277D2D2D273B26A3DA09940C5B77D` |
| `tests\alice_ultimate\performance\benchmark_results.json` | `B041282EE2113871A8905E074CCE228DE94A165027FA86367498ED78E12AFA20` |

## Effets secondaires de tests identifiés
- `tests/alice_ultimate/performance/test_benchmarks.py` écrit directement dans `tests/alice_ultimate/performance/benchmark_results.json`. Lors de Phase H, cette suite de benchmarks sera exécutée sur copie isolée ou sans écraser le manifeste existant.
