# ALICE_014_BASELINE.md
## Baseline Forensique Initiale — Mission 014

**Mission ID :** `ALICE-LOCAL-RUNTIME-REMEDIATION-014`  
**Date :** 2026-11-27  
**Environnement :** Windows-10-10.0.26200-SP0 (64-bit AMD64)  
**Host :** `scarmma`  
**Python Runtime :** Python 3.11.8 (`Jarvis Final - SITE/venv/Scripts/python.exe`)  
**Repository :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  
**Branche :** `main`  
**Commit HEAD :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`  
**Mode :** `CONTROLLED_LOCAL_REMEDIATION_AND_REGRESSION_VALIDATION`  

---

### 1. État Git Initial & Historique de Référence

- **HEAD SHA-1 :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`
- **Branche :** `main`
- **Fichiers suivis modifiés préexistants :**
  - `Jarvis Final - SITE/alice_rag.py`
  - `Jarvis Final - SITE/alice_web_guard.py`
  - `Jarvis Final - SITE/frontend/src/main.ts`
  - `Jarvis Final - SITE/knowledge/rag_index.json`
  - `Jarvis Final - SITE/main2.py`
  - `Jarvis Final - SITE/mobile/app.js`
  - `Jarvis Final - SITE/mobile/index.html`
  - `Jarvis Final - SITE/mobile/orb.js`
  - `Jarvis Final - SITE/mobile/style.css`
  - `Jarvis Final - SITE/vision_ocr.py`

---

### 2. Empreintes Cryptographiques SHA-256 Initiales des Fichiers Critiques

| Composant | Chemin Relatif | Empreinte SHA-256 Initiale |
|---|---|---|
| Serveur Principal | `Jarvis Final - SITE\main2.py` | `4054910e9fbf4693303cfccee43d10b7addd1afbc7a83cf2b926540e3a14e622` |
| Modules ALICE | `Jarvis Final - SITE\alice_modules.py` | `da82d7a0d426b870a4f14a7ba3dad6e73d47e7f0c3c78904ba8fb653a82d7293` |
| Agent Jarvis | `Jarvis Final - SITE\jarvis_agent.py` | `ea7dd54d58fdc886f9cf71f14f254f7b1b3ccd4ce2c003eb76bc659e2b8948b5` |
| Web Guard (SSRF) | `Jarvis Final - SITE\alice_web_guard.py` | `23519ff3946fda429d11250957df22cba775abb79551e37e5a5e24068a645fef` |
| RAG Engine | `Jarvis Final - SITE\alice_rag.py` | `b3260f94d0018fa6e5d761ea86011455b6a34f30add75ead06103e4b986bda4d` |
| Vision OCR | `Jarvis Final - SITE\vision_ocr.py` | `7e2be3cdac45896e9e78cdbc3cae746f77fa0a28c2b30c40a1f901f3d67b2d62` |
| RBAC Policy | `Jarvis Final - SITE\alice_core\security\rbac.py` | `083535cc6af30c52f12d2b6f62e07ef8c68b54e04f57c48f03c4db2e3c62b0a7` |
| API Bridge | `Jarvis Final - SITE\alice_core\api_bridge.py` | `56d2afd96561cece4d88a411f387cbe9331b7782f0107a0a122416ee63033e3f` |
| Mobile PWA Script | `Jarvis Final - SITE\mobile\app.js` | `ad6eb7120c9050252bd2c7a060817bab62a8f453da13bcf5fbda8639f889192d` |
| Mobile PWA HTML | `Jarvis Final - SITE\mobile\index.html` | `8449745607347c70d293605c27dff78170c7963bc8bd2a54ccaa6299556617f3` |
| Mobile PWA Orb | `Jarvis Final - SITE\mobile\orb.js` | `e790adc7360cf24d3fa6161277b539306df51063383650b91c46a997ac5a5dd4` |
| Service Worker | `Jarvis Final - SITE\mobile\sw.js` | `dbd5a82e2430e999849f8750c45fdbdcdf660f84e860749ff8c4448dd3c0384d` |
| Desktop Main TS | `Jarvis Final - SITE\frontend\src\main.ts` | `558d7f9bed45dd1f95c9eef54bcae72f2bbcb611542a96900c4d2a205c716f2a` |

---

### 3. État Initial des Processus et Ports Réseau

Vérification via `Get-NetTCPConnection` et `netstat -ano` :
- Port HTTP `8080` : **LIBRE** (aucun processus à l'écoute)
- Port WebSocket `8765` : **LIBRE** (aucun processus à l'écoute)
- Port Vite `5173` : **LIBRE** (aucun processus à l'écoute)
- Processus ALICE actifs : **AUCUN**

Conclusion baseline : Environnement parfaitement propre, prêt pour la remédiation ciblée 014.
