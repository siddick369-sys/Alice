# ALICE_013_BASELINE.md
## Baseline Forensique Initiale — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  
**Environnement :** Windows-10-10.0.26200-SP0 (64-bit AMD64)  
**Host :** `scarmma`  
**Python Runtime :** Python 3.11.8 (`Jarvis Final - SITE/venv/Scripts/python.exe`)  
**Repository :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  
**Branche :** `main`  
**Commit HEAD :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`  
**Mode d'intervention :** `STRICT_READ_ONLY`  

---

### 1. État Git Initial & Historique de Référence

- **HEAD SHA-1 :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`
- **Branche :** `main`
- **Fichiers suivis modifiés dans le répertoire de travail :**
  - `Jarvis Final - SITE/alice_rag.py` (Missions 008/010)
  - `Jarvis Final - SITE/alice_web_guard.py` (Missions 008/010)
  - `Jarvis Final - SITE/frontend/src/main.ts` (Missions 008/010)
  - `Jarvis Final - SITE/knowledge/rag_index.json` (Missions 008/010)
  - `Jarvis Final - SITE/main2.py` (Missions 008/010 + Fix socket Mission 012)
  - `Jarvis Final - SITE/mobile/app.js` (Missions 008/010 + Fix try/catch orb Mission 012)
  - `Jarvis Final - SITE/mobile/index.html` (Missions 008/010)
  - `Jarvis Final - SITE/mobile/orb.js` (Fix fallback Three.js Mission 012)
  - `Jarvis Final - SITE/mobile/style.css` (Missions 008/010)
  - `Jarvis Final - SITE/vision_ocr.py` (Fix rate-limit BitBlt Mission 012)

---

### 2. Empreintes Cryptographiques SHA-256 des Composants Critiques

| Composant | Fichier | Empreinte SHA-256 Actuelle (013) | Empreinte Baseline 012 | Statut Concordance |
|---|---|---|---|---|
| Serveur Principal | `Jarvis Final - SITE\main2.py` | `4054910e9fbf4693303cfccee43d10b7addd1afbc7a83cf2b926540e3a14e622` | `657652729fd86...` | Modifié (ajout `import socket`) |
| Modules ALICE | `Jarvis Final - SITE\alice_modules.py` | `da82d7a0d426b870a4f14a7ba3dad6e73d47e7f0c3c78904ba8fb653a82d7293` | `da82d7a0d426b...` | **STABLE (Identique)** |
| Agent Jarvis | `Jarvis Final - SITE\jarvis_agent.py` | `ea7dd54d58fdc886f9cf71f14f254f7b1b3ccd4ce2c003eb76bc659e2b8948b5` | `ea7dd54d58fdc...` | **STABLE (Identique)** |
| Web Guard (SSRF) | `Jarvis Final - SITE\alice_web_guard.py` | `23519ff3946fda429d11250957df22cba775abb79551e37e5a5e24068a645fef` | `23519ff3946fd...` | **STABLE (Identique)** |
| RAG Engine | `Jarvis Final - SITE\alice_rag.py` | `b3260f94d0018fa6e5d761ea86011455b6a34f30add75ead06103e4b986bda4d` | `b3260f94d0018...` | **STABLE (Identique)** |
| Vision OCR | `Jarvis Final - SITE\vision_ocr.py` | `7e2be3cdac45896e9e78cdbc3cae746f77fa0a28c2b30c40a1f901f3d67b2d62` | N/A | Modifié (rate-limit BitBlt) |
| RBAC Policy | `Jarvis Final - SITE\alice_core\security\rbac.py` | `083535cc6af30c52f12d2b6f62e07ef8c68b54e04f57c48f03c4db2e3c62b0a7` | `083535cc6af30...` | **STABLE (Identique)** |
| API Bridge | `Jarvis Final - SITE\alice_core\api_bridge.py` | `56d2afd96561cece4d88a411f387cbe9331b7782f0107a0a122416ee63033e3f` | `56d2afd96561c...` | **STABLE (Identique)** |
| Mobile PWA Script | `Jarvis Final - SITE\mobile\app.js` | `ad6eb7120c9050252bd2c7a060817bab62a8f453da13bcf5fbda8639f889192d` | `2ea5cb6963092...` | Modifié (try/catch orb) |
| Mobile PWA HTML | `Jarvis Final - SITE\mobile\index.html` | `8449745607347c70d293605c27dff78170c7963bc8bd2a54ccaa6299556617f3` | `8449745607347...` | **STABLE (Identique)** |
| Mobile PWA Orb | `Jarvis Final - SITE\mobile\orb.js` | `e790adc7360cf24d3fa6161277b539306df51063383650b91c46a997ac5a5dd4` | N/A | Modifié (fallback Three.js) |
| Service Worker | `Jarvis Final - SITE\mobile\sw.js` | `dbd5a82e2430e999849f8750c45fdbdcdf660f84e860749ff8c4448dd3c0384d` | `dbd5a82e2430e...` | **STABLE (Identique)** |
| Desktop Main TS | `Jarvis Final - SITE\frontend\src\main.ts` | `558d7f9bed45dd1f95c9eef54bcae72f2bbcb611542a96900c4d2a205c716f2a` | `558d7f9bed45d...` | **STABLE (Identique)** |

---

### 3. État des Processus et Ports avant Audit 013

- **Ports TCP :**
  - `8080` (HTTP Mobile Server) : **LIBRE** (aucun processus à l'écoute)
  - `8765` (WebSocket Server) : **LIBRE** (aucun processus à l'écoute)
  - `5173` (Frontend Vite Dev Server) : **LIBRE** (aucun processus à l'écoute)
- **Processus ALICE :** Aucun processus ALICE en cours d'exécution. (PID 21452 identifié comme script externe indépendant `scratch\test_verify_vps_readonly.py`).

---

### 4. Modifications Introduites lors de la Mission 012

1. **`Jarvis Final - SITE/main2.py`** : Ligne 4, ajout de `import socket` au niveau des imports globaux standard.
2. **`Jarvis Final - SITE/mobile/orb.js`** : Lignes 5-14, ajout de la garde `if (typeof THREE === "undefined")` renvoyant un objet no-op (`setState`, `setVolume`, `triggerDemo`, `destroy`).
3. **`Jarvis Final - SITE/mobile/app.js`** : Lignes 266-276, ajout d'un bloc `try / catch` autour de l'appel `createOrb(canvas)`.
4. **`Jarvis Final - SITE/vision_ocr.py`** : Lignes 110-138, rate-limiting des exceptions répétitives de capture Windows GDI (`BitBlt`) à 1 log toutes les 30 secondes en session non interactive.
