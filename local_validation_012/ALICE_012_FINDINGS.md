# ALICE_012_FINDINGS.md
## Journal des Anomalies Constatées et Corrigées — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  

---

### 1. Anomalies Reproduites et Corrigées (Root-Cause Proven)

| ID | Gravité | Composant | Symptôme Observé | Cause Racine | Correction Appliquée & Statut |
|---|---|---|---|---|---|
| **F012-01** | **CRITICAL (Blocker)** | `Jarvis Final - SITE/main2.py` | Crash immédiat du thread `start_mobile_http_server` (`NameError: name 'socket' is not defined` à la ligne 5205). Le port `8080` ne s'ouvrait jamais. | `import socket` absent des imports globaux (uniquement importé localement dans `obtenir_ip_locale`). | **CORRIGÉ & VÉRIFIÉ** : Ajout de `import socket` en ligne 3 de `main2.py`. Port `8080` écoute désormais normalement. |
| **F012-02** | **HIGH (Blocker UI Hors-Ligne)** | `Jarvis Final - SITE/mobile/orb.js` & `app.js` | Sur mobile PWA en mode hors-ligne (CDN `cdnjs.cloudflare.com` inaccessible), `Uncaught ReferenceError: THREE is not defined` stoppait `app.js` à la ligne 269, empêchant le WebSocket et les boutons de fonctionner. | `createOrb()` accédait directement à `THREE.WebGLRenderer` sans vérifier `typeof THREE === "undefined"`. | **CORRIGÉ & VÉRIFIÉ** : Garde défensive dans `orb.js` retournant un objet fallback no-op + `try/catch` dans `app.js`. 0 erreur JS en navigateur réel. |
| **F012-03** | **LOW (Log Spam)** | `Jarvis Final - SITE/vision_ocr.py` | Répétition toutes les 3s de `[VISION ERROR] Windows graphics function failed (no error provided): BitBlt` en session non interactive. | Absence de limitation de fréquence sur le log d'exception dans `_vision_loop`. | **CORRIGÉ & VÉRIFIÉ** : Rate-limit (1 log / 30s par erreur identique). |

---

### 2. Limitations Opérationnelles Constatées (Sans Correction Requise / Hors Scope Local)

| ID | Type | Description | Impact |
|---|---|---|---|
| **L012-01** | **UX / Sécurité** | Le code PIN d'appairage initial (TTL 120s) n'est généré qu'au démarrage ou par commande vocale. Après expiration, aucun bouton/route HTTP locale ne permet de regénérer un PIN sans redémarrer ou parler à l'assistant. | Faible (contournable par redémarrage ou commande vocale ; intentionnel côté sécurité). |
| **L012-02** | **Asset mineur** | `GET /favicon.ico` retourne `404` sur le serveur mobile. | Cosmétique uniquement. |
| **L012-03** | **Dépendances Externes** | Home Assistant physique, caméra RTSP, Google OAuth et TTS/LLM Cloud (hors-ligne) non testables physiquement sur cet hôte isolé. | Documenté en `NOT_TESTED_EXTERNAL_DEPENDENCY`. |
