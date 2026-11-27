# 🛠️ ALICE — GUIDE D'EXPLOITATION & OPÉRATIONS (MISSION 008)

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Date :** 25 Novembre 2026  

---

## 1. DÉMARRAGE ET CONFIGURATION DES FEATURE FLAGS

- **Démarrage standard :** `Jarvis Final - SITE\venv\Scripts\python.exe "Jarvis Final - SITE\main2.py"`
- **Variables d'environnement clés :**
  - `ALICE_ENV=production` + `ALICE_SSL_CERT` / `ALICE_SSL_KEY` pour imposer TLS/WSS.
  - `ALICE_FLAG_<NOM>=1|0` pour surcharger tout flag (ex. `ALICE_FLAG_VOICE_BIOMETRICS=1`, `ALICE_FLAG_ENCRYPTED_VAULT=1`, `ALICE_FLAG_WEBHOOK_CONNECTOR=1`).
- **Par défaut sécuritaire :** Biométrie vocale, surveillance RTSP, mémoire visuelle, automatisation prédictive, agent web autonome, webhooks et coffre-fort sont **désactivés par défaut**.

## 2. GESTION DES RÔLES RBAC & APPAIRAGE

- Au démarrage, `PAIRING_MANAGER.generate_pairing_code(role="OWNER"|"MEMBER"|"GUEST")` émet un PIN à 6 chiffres valable 120s.
- Les invités appairés avec le rôle `GUEST` peuvent dialoguer et piloter les lumières communes (`salon`, `cuisine`, `couloir`), mais sont bloqués côté backend sur les actions système, emails, alarme, coffre-fort et observabilité.

## 3. EXÉCUTION DES TESTS DE VALIDATION

- **Suite complète Mission 008 (46 tests + benchmarks) :**
  `& "Jarvis Final - SITE\venv\Scripts\python.exe" "tests\alice_ultimate\run_ultimate_suite.py"`
- **Suite P1 Hardening 006 (23 tests) :**
  `& "Jarvis Final - SITE\venv\Scripts\python.exe" "tests\security\test_p1_production_exposure_006.py"`
- **Suite Mission 007 (23 tests) :**
  `& "Jarvis Final - SITE\venv\Scripts\python.exe" "Jarvis Final - SITE\tests\run_all_tests.py"`
- **Build Frontend Desktop :**
  `cd "Jarvis Final - SITE\frontend" && npm run build`

## 4. RACCORDEMENT DES SERVICES EXTERNES OPTIONNELS

1. **Home Assistant :** Renseigner `HA_URL` et `HA_TOKEN` réels dans `Jarvis Final - SITE/.env`.
2. **Google Workspace :** Générer `token.pickle` via flux OAuth2 interactif hors production à partir de `credentials.json`.
3. **Caméras RTSP :** Activer `video_monitoring` et enregistrer uniquement les flux autorisés via `VIDEO_SENTINEL.register_camera(...)`.
