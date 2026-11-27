# 🛡️ ALICE — REVUE DE SÉCURITÉ ET PROTECTION DE LA VIE PRIVÉE (MISSION 008)

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Date :** 25 Novembre 2026  

---

## 1. CONTINUITÉ DES CONTRÔLES P0 / P1

- **C-01 (TLS/WSS fail-closed) :** Inchangé et fonctionnel (`FAIL_CLOSED_TLS_REQUIRED` en production sans certificat).
- **C-02 (Validation d'origine RFC 6454) :** Inchangée.
- **C-03 (Verrou mémoire cross-process & écriture atomique) :** Inchangé ; étendu aux nouveaux magasins JSON par écriture `.tmp` + `os.replace`.
- **C-04 (Vérité terrain Home Assistant) :** Préservé dans `ha_client.py` et `self_healing.py` (`UNCONFIGURED`, `STALE`, `STATE_UNKNOWN`).
- **P1 (Cookies HttpOnly, CSRF, CSP, anti-XSS) :** 23/23 PASS confirmé après modifications finales de `main2.py` et `mobile/*`.

## 2. GARDE-FOUS SPÉCIFIQUES MISSION 008

1. **RBAC Côté Backend (`alice_core/security/rbac.py`) :**
   - Vérification sur toutes les routes `/api/*`, messages WS, `executer_action_pc` (correction d'une faille détectée lors des tests E2E sur `"lis mes emails"`), et actions JSON IA.
   - Rôle `GUEST` strictement bloqué sur : arrêt/reboot PC, fichiers, emails, désarmement alarme, coffre-fort, observabilité et webhooks.
2. **Coffre-Fort Chiffré (`alice_core/security/vault.py`) :**
   - AES-256-GCM avec nonce aléatoire 96 bits unique, dérivation Scrypt + sel 128 bits, auto-verrouillage, rotation de clé.
   - Exclusion explicite des répertoires/fichiers `*vault*` dans `alice_rag.py` et `watchdog.py`, et masquage des clés `vault_data` dans `audit.py` et `agent_swarm.py`.
3. **Biométrie Vocale & Vie Privée (`voice_id.py`, `acoustic_context.py`, `video_sentinel.py`, `visual_memory.py`) :**
   - Flags `voice_biometrics`, `video_monitoring`, `visual_memory`, `emotion_context`, `encrypted_vault`, `webhook_connector`, `predictive_automation`, `web_automation` tous **désactivés par défaut (`False`)**.
   - Empreintes vocales locales stockées chiffrées AES-256-GCM ; anti-rejeu SHA-256 ; inconnus -> `GUEST` ; Voice ID seul **insuffisant** pour les actions critiques (`sufficient_for_sensitive_actions=False`).
   - Reconnaissance faciale interdite (`face_recognition_enabled=False`) ; suppression des métadonnées EXIF sur captures mobiles (`analyzer.py`).
4. **Webhooks & Agent Web (`webhooks.py`, `web_agent.py`) :**
   - HMAC-SHA256 temps constant, fenêtre ±300s, cache anti-rejeu de nonces, rotation avec période de grâce, interdiction des actions critiques (`shutdown`, `ha_alarme`, `vault_*`) via webhook.
   - Validation SSRF `WEB_GUARD` à chaque saut de redirection HTTP (`allow_redirects=False`) et arrêt immédiat sur CAPTCHA/MFA sans contournement.
