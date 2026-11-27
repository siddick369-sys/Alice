# ALICE_012_RUNTIME_STABILITY.md
## Rapport de Stabilité Runtime et Ressources — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  

---

### 1. Métriques Système Observées via `/api/ops/metrics` (en charge réelle)

Lors de l'exécution prolongée du serveur ALICE (uptime mesuré `145.3 s` sur la session E2E), les métriques télémétriques retournées en direct par le module d'observabilité étaient :
- **CPU :** `24.5 %`
- **RAM système :** `73.0 %` (sur `15.78 Go` total)
- **Latence API Sync :** `2.2 ms` (GET) à `5.97 ms` (POST batch)
- **Clients WebSocket simultanés :** 2 clients connectés simultanément (`desktop_local` + client E2E) sans fuite ni blocage.

---

### 2. Comportement en Dégradation Gracieuse (Mode Hors-Ligne / Sans Écran)

- **Connexion Internet absente / restreinte :**  
  - `main2.py` détecte l'absence de connectivité externe au démarrage et affiche un avertissement clair sans crasher.
  - `Edge-TTS` bascule automatiquement vers le moteur TTS local (`pyttsx3`) en cas de timeout réseau (`Cannot connect to host speech.platform.bing.com:443`).
- **Session sans bureau GDI interactif (`BitBlt`) :**  
  - Le thread `JarvisVision` capture l'erreur sans interrompre les threads HTTP, WebSocket, Calendrier ou Audio.
- **Audio & Microphone :**  
  - Initialisation réussie de `sr.Microphone()` et `monitor_claps` en arrière-plan sans bloquer la boucle événementielle WebSocket/HTTP.

---

### 3. Propreté de l'Arrêt

- Tous les processus lancés pour la validation (`python.exe` et `vite`) ont été arrêtés proprement en fin de campagne.
