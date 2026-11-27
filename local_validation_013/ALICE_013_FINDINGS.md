# ALICE_013_FINDINGS.md
## Registre des Constats, Anomalies et Recommandations — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  

---

### 1. Registre des Constats & Anomalies Identifiées

| ID | Domaine | Gravité | Description du Constat | Cause Racine Établie | Recommandation Minimale Proposée |
|---|---|---|---|---|---|
| **F013-01** | **WebSocket UI Sync** | **MEDIUM** (Cosmétique/Sync) | L'interface Mobile PWA sur `127.0.0.1` conserve le badge `hors-ligne` malgré un handshake WebSocket 101 réussi. | `main2.py:ws_handler` classe toute connexion loopback comme `desktop_local` et ne transmet pas `{"type": "auth_ok"}`. Le client `app.js` n'appelle `setConnected(true)` que sur réception de `auth_ok`. | Modifier `main2.py:1107` pour émettre un message d'acquittement `auth_ok` pour `desktop_local`, ou permettre à `app.js` de parser l'état ouvert. |
| **F013-02** | **Réseau Local (LAN)** | **LOW** (Sensibilisation) | Les ports HTTP `8080` et WebSocket `8765` écoutent sur `0.0.0.0`, les rendant joignables depuis le réseau local. | Conçu pour permettre aux smartphones sur le Wi-Fi d'accéder à l'interface PWA locale. | Ajouter une variable d'environnement `ALICE_BIND_ADDRESS` (défaut `0.0.0.0`, configurable en `127.0.0.1` pour mode monoposte strict). |
| **F013-03** | **Vision GDI BitBlt** | **INFO** (Environnement) | En session sans affichage Windows interactif (service/headless), `mss.grab` ne peut capturer le bureau hôte. | Restriction du modèle de sécurité Windows GDI empêchant `BitBlt` hors console interactive. | Documenter que la sentinelle de capture d'écran de l'hôte nécessite une session de bureau déverrouillée. |

---

### 2. Dépendances Externes Non Testables Localement

- **Home Assistant Physique :** Aucune instance physique joignable sur le sous-réseau local.
- **Caméra RTSP :** Pas de flux matériel RTSP actif.
- **Google OAuth :** Pas de `token.pickle` utilisateur actif.
- **Services IA Cloud :** En l'absence d'accès Internet sortant, le système bascule de façon prouvée sur les moteurs hors-ligne (TTS `pyttsx3`).
