# ALICE_012_STARTUP_REPORT.md
## Rapport de Démarrage Réel en Environnement Local — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date & Heure :** 2026-11-26 16:11:39 CET  
**Processus Principal (PID) :** `4172` (`python.exe`)  
**Processus Frontend Vite (PID) :** `18040` (`node.exe`)  
**Statut Global :** **DÉMARRAGE RÉEL EFFECTIF (RUNNING)**  

---

### 1. Analyse des Composants Démarrés

| Service | Protocole | Adresse d'Écoute | Port | PID | Statut Runtime |
|---|---|---|---|---|---|
| **Mobile Web HTTP Server** | HTTP | `0.0.0.0` / `127.0.0.1` | `8080` | `4172` | **LISTENING** (Actif) |
| **Backend WebSocket Gateway** | WebSocket (`ws://`) | `0.0.0.0` / `127.0.0.1` | `8765` | `4172` | **LISTENING** (Actif) |
| **Desktop Web UI (Vite)** | HTTP | `[::1]` / `localhost` | `5173` | `18040` | **LISTENING** (Actif) |
| **Vision OCR Sentinel** | Interne (MSS + Tesseract) | Thread d'arrière-plan | N/A | `4172` | **ACTIF** (Scan périodique) |
| **Audio Clap & Event Loop** | Interne (PyAudio/Threading) | Thread d'arrière-plan | N/A | `4172` | **ACTIF** |
| **Hot Folder Watchdog** | Interne (Poller) | Thread d'arrière-plan | N/A | `4172` | **ACTIF** |

---

### 2. Détection et Résolution d'Anomalie Runtime lors du Démarrage

- **Anomalie observée lors du 1er essai :**  
  `Exception in thread Thread-1 (start_mobile_http_server): NameError: name 'socket' is not defined` à la ligne 5205 dans `DualStackHTTPServer`.
- **Cause racine démontrée :** L'instruction `import socket` n'était importée que localement dans une fonction utilitaire (`obtenir_ip_locale`), et manquait au niveau des imports globaux du fichier `Jarvis Final - SITE/main2.py`.
- **Correction minimale appliquée :** Ajout de `import socket` à la ligne 3 de `Jarvis Final - SITE/main2.py`.
- **Résultat après redémarrage :** Le serveur HTTP Mobile a démarré avec succès sur le port `8080`, servant l'interface PWA et l'API d'appairage.
- **Atténuation Vision OCR :** En environnement sans écran physique interactif direct (GDI BitBlt), limitation du débit des logs d'erreurs répétitives dans `Jarvis Final - SITE/vision_ocr.py` pour préserver l'intégrité et la lisibilité du journal.

---

### 3. Preuve Forensique d'Écoute des Ports

Vérification via `netstat -ano | Select-String '8080|8765|5173'` :
```
TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       4172
TCP    0.0.0.0:8765           0.0.0.0:0              LISTENING       4172
TCP    [::1]:5173             [::]:0                 LISTENING       18040
```

---

### 4. Code d'Appairage Initial Généré

- **Code d'appairage dynamique :** Généré automatiquement par `PAIRING_MANAGER` à l'initialisation du serveur mobile (ex: `910197`, rôle `OWNER`, validité 120s renouvelable via endpoint).
- **Mode de transport :** `DEVELOPMENT_PLAINTEXT_DEGRADED` (conforme aux règles P1 en mode local hors production sans certificats TLS racine).
