# 🛡️ ALICE-014 — CRYPTOGRAPHIC HASH MANIFEST
**Mission :** `ALICE-LOCAL-RUNTIME-REMEDIATION-014`  
**Classification :** INTÉGRITÉ LOGICIELLE & PREUVE FORENSIQUE  
**Algorithme :** SHA-256  
**Date :** 2026-11-27T08:35:00+01:00  

---

## 1. Empreintes Numériques SHA-256 des Fichiers Clés

| Fichier | Empreinte SHA-256 | Description |
|---|---|---|
| `Jarvis Final - SITE/main2.py` | `78911B2BCB552F90E4ACB87968F0C4329A30DD7A7EC378BB0FD701BC7484D522` | Backend unifié avec correctifs F013-01, 02, 03 |
| `Jarvis Final - SITE/frontend/src/main.ts` | `E312EEED04FF3983A33408F0B06ECC23317F48330A1CC0EB5BE603BE6FC9732A` | Frontend Desktop avec synchronisation auth_ok |
| `Jarvis Final - SITE/stop_alice.py` | `8485432939BBEDD5B4AB4948DE65D426D4998743C8A0F636871A98D301D7A190` | Utilitaire d'arrêt ordonné et libération des ports |
| `tests/test_remediation_014.py` | `9A5EF17C801DC605EDEB379765A182E4E080F1DD211E3AC9BDE6687CED76266A` | Suite adversariale WebSocket & Binding |
| `tests/test_multimodal_014.py` | `4F584D3BF4F53D7ADE85510393638EEB4D8BC41966641F6E6DF9E057CFF37E0C` | Suite multimodale (Assistant, Audio, Vision) |
| `local_validation_014/test_lifecycle_014.py` | `AE5A88DB0BB67B1CA6AE5BD7312CB26819DAA850A0675E1E4EF7BBE76902B530` | Script de validation du cycle de vie complet |
| `local_validation_014/run_all_014_suites.py` | `93AB85970A4C38BF654ACF7670EF08DD041218421BC44B8E1B0F3792935B69D2` | Exécuteur global des 165 tests du dépôt |

---

## 2. Empreintes des Fichiers Sources Préexistants (Préservés)

| Fichier | Empreinte SHA-256 | Statut |
|---|---|---|
| `Jarvis Final - SITE/mobile/app.js` | `375AEB048299CDDF4DFAC3919ED63E013FA86F6A6E0E68CEE31BEF2BEB909191` | Préservé intact |
| `Jarvis Final - SITE/mobile/index.html` | `A838ED0EFE8E12F3D9EE3BF60C0392C1D262F6BFDE12678C3D29548484B157D0` | Préservé intact |
| `Jarvis Final - SITE/alice_core/security/rbac.py` | `5DE628B897EF3BC2FDB06C1985474B924A224FA254593BAF8B44CECE261642BA` | Préservé intact |
| `Jarvis Final - SITE/alice_core/api_bridge.py` | `A6D63E6F0E0B1953D74B46960F174981C0CF57388C8384931A97143AFDBF4660` | Préservé intact |
| `Jarvis Final - SITE/vision_ocr.py` | `9CFB9D6E506B62D696E0C7E5BEBD32CE35616BE3DDCDBFA535BBE29A646E1363` | Préservé intact |
