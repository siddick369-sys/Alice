# ALICE_012_BASELINE.md
## Baseline Forensique de Validation Locale — Mission 012

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  
**Environnement :** Windows-10-10.0.26200-SP0 (64-bit AMD64)  
**Host :** `scarmma`  
**Python Runtime :** Python 3.11.8 (`Jarvis Final - SITE/venv/Scripts/python.exe`)  
**Repository :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  
**Branche :** `main`  
**Commit HEAD :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`  

---

### 1. État Git initial

- **HEAD commit SHA :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`
- **Branche courante :** `main`
- **Fichiers suivis modifiés (travaux de remédiation & durcissement 008/010) :**
  - `Jarvis Final - SITE/alice_rag.py`
  - `Jarvis Final - SITE/alice_web_guard.py`
  - `Jarvis Final - SITE/frontend/src/main.ts`
  - `Jarvis Final - SITE/knowledge/rag_index.json`
  - `Jarvis Final - SITE/main2.py`
  - `Jarvis Final - SITE/mobile/app.js`
  - `Jarvis Final - SITE/mobile/index.html`
  - `Jarvis Final - SITE/mobile/style.css`

---

### 2. Empreintes SHA-256 des fichiers critiques du Runtime

| Composant | Chemin Relatif | Empreinte SHA-256 |
|---|---|---|
| Serveur Principal & HTTP/WS | `Jarvis Final - SITE\main2.py` | `657652729fd8621c8fbe5f079317f09684bc12619fd67227e34d1a3707a1bb42` |
| Modules ALICE | `Jarvis Final - SITE\alice_modules.py` | `da82d7a0d426b870a4f14a7ba3dad6e73d47e7f0c3c78904ba8fb653a82d7293` |
| Agent Jarvis / LLM Orchestrator | `Jarvis Final - SITE\jarvis_agent.py` | `ea7dd54d58fdc886f9cf71f14f254f7b1b3ccd4ce2c003eb76bc659e2b8948b5` |
| Web Guard & SSRF Protection | `Jarvis Final - SITE\alice_web_guard.py` | `23519ff3946fda429d11250957df22cba775abb79551e37e5a5e24068a645fef` |
| RAG Engine & Document Store | `Jarvis Final - SITE\alice_rag.py` | `b3260f94d0018fa6e5d761ea86011455b6a34f30add75ead06103e4b986bda4d` |
| RBAC Policy Enforcement | `Jarvis Final - SITE\alice_core\security\rbac.py` | `083535cc6af30c52f12d2b6f62e07ef8c68b54e04f57c48f03c4db2e3c62b0a7` |
| API Bridge Controller | `Jarvis Final - SITE\alice_core\api_bridge.py` | `56d2afd96561cece4d88a411f387cbe9331b7782f0107a0a122416ee63033e3f` |
| PWA Mobile Client Script | `Jarvis Final - SITE\mobile\app.js` | `2ea5cb6963092ac139ac3b9a2796640ae7ff6546851ea1509d9ee02ecc69541b` |
| PWA Mobile Entrypoint HTML | `Jarvis Final - SITE\mobile\index.html` | `8449745607347c70d293605c27dff78170c7963bc8bd2a54ccaa6299556617f3` |
| PWA Service Worker | `Jarvis Final - SITE\mobile\sw.js` | `dbd5a82e2430e999849f8750c45fdbdcdf660f84e860749ff8c4448dd3c0384d` |
| Frontend Desktop Main TS | `Jarvis Final - SITE\frontend\src\main.ts` | `558d7f9bed45dd1f95c9eef54bcae72f2bbcb611542a96900c4d2a205c716f2a` |

---

### 3. État Initial des Ports Réseau

Vérification via `netstat -ano | findstr "8080 8765 5173"` avant tout lancement :
- Port HTTP Mobile Backend `8080` : **LIBRE** (aucun processus à l'écoute)
- Port WebSocket Backend `8765` : **LIBRE** (aucun processus à l'écoute)
- Port Frontend Vite `5173` : **LIBRE** (aucun processus à l'écoute)

Conclusion baseline : Environnement propre, aucun artefact résiduel bloquant les ports, intégrité du code conforme aux remédiations validées lors de la Mission 011.
