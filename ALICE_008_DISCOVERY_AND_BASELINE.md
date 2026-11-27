# 🔍 ALICE — PHASE 0 : DISCOVERY, AUDIT COMPLET & BASELINE

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  
**Dépôt actif vérifié :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  
**Branche Git :** `main`  
**HEAD initial :** `fa8a66dcec82a0200a17b60c3265095727c8aa73`  
**Git status initial :** Clean (`nothing to commit, working tree clean`)  

---

## 1. VÉRIFICATION DU DÉPÔT ET BASELINE GIT

### 1.1 Emplacement Réel & Copies Détectées
- **Dépôt actif :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2` (racine Git contenant `Jarvis Final - SITE/`, `tests/`, et 46 rapports d'audits/missions précédents).
- **Autres emplacements observés sur le disque :**
  - `C:\Users\USER\Desktop\Jarvis Final - SITE-V2.zip` (archive statique antérieure)
  - `C:\Users\USER\Desktop\TPI\jarvis.html` et `C:\Users\USER\Documents\TPI\jarvis.html` (anciennes maquettes HTML sans lien avec le serveur actif).
- **Conclusion :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2` est l'unique dépôt actif maintenu.

### 1.2 Sommes de Contrôle SHA-256 Initiales des Fichiers Critiques

| Fichier | SHA-256 |
| :--- | :--- |
| `Jarvis Final - SITE\main2.py` | `47C6CB7B54C7A2310030633E62E88BA0B69F45761B5CB7BFAA7F3F14E74D0C68` |
| `Jarvis Final - SITE\alice_modules.py` | `DA82D7A0D426B870A4F14A7BA3DAD6E73D47E7F0C3C78904BA8FB653A82D7293` |
| `Jarvis Final - SITE\jarvis_agent.py` | `EA7DD54D58FDC886F9CF71F14F254F7B1B3CCD4CE2C003EB76BC659E2B8948B5` |
| `Jarvis Final - SITE\alice_orchestrator.py` | `6C5D078B9255049DB4275923329C357441C878CE63FB2C4925284B74FB1C506F` |
| `Jarvis Final - SITE\alice_rag.py` | `3D2A01A68DB1079066ED86500D9E362258D412869E509EA7150A9DBA14692591` |
| `Jarvis Final - SITE\alice_web_guard.py` | `6D36A070D7CB2064E77393FFF556D85A4B930EA5B8C44492963E2728A3E7D635` |
| `Jarvis Final - SITE\alice_google_adapter.py` | `AEDBFA93246FA316706C6F0EC1231BB024557C4F5D037663301B8C76587998E1` |
| `Jarvis Final - SITE\mobile\app.js` | `8D9C5FF5976F1D60311EE78318D02A45E76AD07F4C9FBF3E85EF02F80A645DF8` |
| `Jarvis Final - SITE\mobile\index.html` | `DC40D6AD0D99C601ADEB42811A9218795519F800583EF302912A18938EEC57B3` |
| `Jarvis Final - SITE\mobile\style.css` | `A47EFB91ED8ABEBD9AF054934FADE3712607518E26D28FB0613BF8307D8436B9` |

### 1.3 Baseline Initiale des Tests (Exécutés Réellement)
- **Suite P0 Adversarial Certification (`test_acceptance_004_master.py`) :** **86/86 PASS (100.0%)**, 0 échec.
- **Suite P1 Hardening 006 (`tests/security/test_p1_production_exposure_006.py`) :** **23/23 PASS**, 0 échec.
- **Suite Fonctionnelle Mission 007 (`Jarvis Final - SITE/tests/run_all_tests.py`) :** **23/23 PASS**, 0 échec.
- **Total Baseline Certifié Initial :** **132 / 132 PASS**.

---

## 2. MATÉRIEL, DÉPENDANCES, LICENCES ET COÛTS

### 2.1 Configuration Matérielle et Système Vérifiée
- **OS :** Windows 10 (build 26200)
- **Python :** `3.11.8` (`Jarvis Final - SITE\venv`)
- **CPU :** 8 cœurs logiques
- **RAM :** 15.78 Go total (3.67 Go disponibles lors de l'audit — charge hôte à 76%)
- **Audio :** 19 périphériques audio détectés via `PyAudio 0.2.14`
- **Tesseract OCR :** `v5.5.0.20241111` installé (`C:\Program Files\Tesseract-OCR\tesseract.exe`), langues `eng` et `fra` opérationnelles dans `tessdata/`.
- **Node.js :** Installé (`C:\Program Files\nodejs\node.exe`), `frontend/` utilise Vite 6 / TypeScript 5.7 / Three.js 0.170.0.

### 2.2 État des Bibliothèques Python & Contraintes de Licences / Coûts
- **Installées et prêtes dans le `venv` :**
  - `cryptography 46.0.7` (Apache-2.0/BSD) — chiffrement AES-256-GCM, PBKDF2, HMAC.
  - `numpy 2.4.4` (BSD-3-Clause) — calcul matriciel DSP audio, projections vectorielles denses, géométrie ROI.
  - `opencv-python 4.13.0.92` (Apache-2.0) — capture RTSP, HOG détecteur de personnes, soustraction de fond MOG2, prétraitement d'images.
  - `pytesseract 0.3.13` (Apache-2.0) + Tesseract 5.5 (Apache-2.0) — OCR local hors-ligne.
  - `PyPDF2 3.0.1` (BSD-3-Clause), `pillow 12.2.0` (MIT-CMU), `websockets 16.0` (BSD), `pydantic 2.13.3` (MIT), `edge-tts 7.2.8` (LGPL/MIT), `pyttsx3 2.99` (MPL-2.0), `pygame 2.6.1` (LGPL), `SpeechRecognition 3.16.0` (BSD), `PyAudio 0.2.14` (MIT), `google-genai 1.73.1`, `openai 2.32.0`, `groq 1.2.0`.
- **Absentes dans le `venv` actuel (impact diagnostiqué) :**
  - `psutil` absent → casse silencieusement `diagnostic_pc()` et `suivi_productivite()` (`psutil = None`). *Décision architecture :* Fournir un collecteur natif Windows/POSIX par `ctypes` (`GetSystemTimes` / `GlobalMemoryStatusEx`) + `shutil.disk_usage` sans dépendance obligatoire, rendant l'observabilité opérationnelle immédiatement.
  - `huggingface_hub` absent → `alice_modules.hf_client` est toujours `None`.
  - `onnxruntime` absent → RAG hybride doit utiliser une projection vectorielle dense locale en `numpy` + BM25 + RRF avec support pluggable ONNX optionnel.
  - `ultralytics` / PyTorch absent → Inadapté à une empreinte RAM libre de ~3.6 Go. *Décision architecture :* OpenCV HOG + MOG2 + validation temporelle/météorologique natifs et légers + connecteur pluggable ONNX/Gemini Vision.
  - `watchdog`, `python-docx`, `ebooklib` absents → Implémentation native en bibliothèque standard (`os.scandir` + vérification de stabilité fichier ; extracteurs natifs `.docx` et `.epub` via `zipfile` + `xml.etree.ElementTree` + `html.parser`).
- **Coûts externes & État réel `.env` (sans divulgation de secrets) :**
  - `GEMINI_API_KEY`, `GROQ_API_KEY`, `SERPAPI_API_KEY`, `YOUTUBE_API_KEY`, `HF_TOKEN` : configurés dans `.env`. Attention aux quotas gratuits (15 RPM Gemini Flash, risques 429).
  - `HA_URL`, `HA_TOKEN` : **Non configurés (`configured=False`, valeurs placeholder)**. Home Assistant n'est pas joignable depuis cet environnement hôte.
  - `credentials.json` présent mais `token.pickle` **absent (`HAS_TOKEN=False`)** : Google Workspace est isolé en état `AUTH_REQUIRED`.
  - Caméra RTSP / IP physique : Aucune caméra configurée dans l'environnement.

---

## 3. INVENTAIRE ET STATUT RÉEL DES 30 FONCTIONNALITÉS (PHASE 0)

| ID | Fonctionnalité | Implémentation existante constatée | Statut réel | Prérequis critiques / Blocages |
| :--- | :--- | :--- | :---: | :--- |
| `ALICE-VOICE-001` | Real-Time Barge-In | `STOP_PARLER` booléen dans `main2.py`, bouton STOP mobile, détection post-capture `"tais-toi"` dans `ecouter()` | **PARTIAL** | Manque automate d'états audio, vidage buffers WS, annulation async TTS et anti-écho |
| `ALICE-VOICE-002` | Voice ID / Multi-Speaker | Aucune empreinte ni profil vocal (`Aboubakar` codé en dur) | **MISSING** | Dépend de RBAC (28), chiffrement Vault (29), pipeline audio (01) |
| `ALICE-VOICE-003` | Acoustic Mood and Context | `detecter_humeur_audio` via `huggingface_hub` (lib absente) sur fichier WAV statique | **PARTIAL** | Manque extracteur acoustique temps réel local, adaptation prompt, opt-out |
| `ALICE-VOICE-004` | Whisper Mode | Aucune détection chuchotement ni profil nuit configuré | **MISSING** | Dépend de l'extracteur acoustique et profil TTS |
| `ALICE-VOICE-005` | Follow-Up Listen | `jarvis_actif` + `SESSION_TIMEOUT=30.0` dans boucle bloquante | **PARTIAL** | Manque fenêtre 5s configurable, indicateur WS/UI visible et annulation |
| `ALICE-IOT-006` | Predictive Routines | Aucun historique ni détection de récurrence | **MISSING** | Dépend des événements HA et du gestionnaire de consentement ; HA absent ici |
| `ALICE-IOT-007` | Eco-Manager | `ha_consommation`, `ha_energie` et `HA_TARIFS` dans `main2.py` | **PARTIAL** | Manque moteur de délestage, protection critiques, données périmées ; HA absent |
| `ALICE-IOT-008` | Self-Healing IoT | `ha_batterie` manuel sur dictionnaire statique | **PARTIAL** | Manque scan flotte, latence, retry borné non destructif ; HA absent |
| `ALICE-IOT-009` | Dynamic Presence Simulation | Toggle basique `switch.simulation` via `ha_simulation` | **PARTIAL** | Manque planning réaliste multi-pièces et garde-fous alarme/serrures |
| `ALICE-IOT-010` | Smart Thermal Comfort | `ha_thermostat` direct sans retour d'état ni régulation | **PARTIAL** | Manque hystérésis, présence, météo, protection antigel |
| `ALICE-MEM-011` | Hybrid Vector + BM25 RAG | `alice_rag.py` (TF-IDF + bigrammes + SHA-256 JSON + XLSX/PDF/TXT) | **PARTIAL** | Manque BM25 pur, vecteurs denses, fusion RRF, isolation utilisateurs, auto-réparation |
| `ALICE-MEM-012` | Personal Knowledge Graph | `jarvis_memoire.json` plat clé-valeur uniquement | **MISSING** | Dépend de l'isolation RBAC (28) et persistance atomique |
| `ALICE-MEM-013` | Hot-Folder Watchdog | Indexation manuelle à la demande seulement | **MISSING** | Dépend du moteur RAG (11) et support DOCX/EPUB |
| `ALICE-MEM-014` | Executive Briefing | Absent | **MISSING** | Dépend de RAG/Extraction (11, 13) |
| `ALICE-MEM-015` | Commitment Tracker | `add_reminder` stocke un tableau jamais évalué | **MISSING** | Dépend de l'agenda/emails (Google `AUTH_REQUIRED`) et jobs/rappels |
| `ALICE-VISION-016` | On-Demand Visual Analysis | `screen_capture.ts` Desktop + `analyser_photo` fichier PC | **PARTIAL** | Manque parcours mobile capture → prévisualisation → confirmation → rétention |
| `ALICE-VISION-017` | Smart OCR Receipts | `vision_ocr.py` Tesseract sur capture écran PC | **PARTIAL** | Manque extraction structurée HT/TVA/TTC, vérification mathématique et export XLSX |
| `ALICE-VISION-018` | Intelligent RTSP Video Sentinel | `analyser_video_surveillance` lit une capture bureau `pyautogui` | **MISSING** | Aucun flux RTSP ni détecteur local HOG/MOG2, ni caméra physique ici |
| `ALICE-VISION-019` | Visual Memory | Absent | **MISSING** | Dépend des événements horodatés de Vision/Sentinel (16, 18) |
| `ALICE-VISION-020` | Contextual Safety Zones | Absent | **MISSING** | Dépend des détections spatiales de Video Sentinel (18) |
| `ALICE-AUTO-021` | Proactive Morning / Evening Briefing | `monitor_calendar` logge seulement en console | **PARTIAL** | Manque planificateur matin/soir, mode silencieux, protection invités, agrégation |
| `ALICE-AUTO-022` | Agent Swarm | `alice_orchestrator.py` gère une seule commande | **MISSING** | Dépend de l'orchestrateur 9 états et RBAC (28) |
| `ALICE-AUTO-023` | Autonomous Web Agent | `agent_web_action` + `WEB_GUARD` (navigateur OS + screenshot) | **PARTIAL** | Manque contrôle redirections, suivi prix/colis, confirmation transaction |
| `ALICE-AUTO-024` | Long-Running Jobs | `asyncio.ensure_future` sans suivi ni file | **MISSING** | Dépend de l'orchestrateur (007) et notifications mobile WS |
| `ALICE-AUTO-025` | Universal Automation Connector | Absent | **MISSING** | Dépend de RBAC (28), Audit log et validation schéma |
| `ALICE-MOBILE-026` | Resilient Offline PWA | `mobile/` sans `manifest.json`, ni `sw.js`, ni stockage offline | **MISSING** | Dépend de RBAC/sessions et WebSocket |
| `ALICE-MOBILE-027` | Home Screen Shortcuts & Widgets | Absent | **MISSING** | Dépend de PWA (26), RBAC (28) et confirmations |
| `ALICE-SEC-028` | Multi-User RBAC / Guest Mode | `WSSessionManager` gère des sessions desktop/mobile sans rôles | **PARTIAL** | Critique (Wave 1) — prérequis de Voice ID, KG, Vault, Webhooks, Ops |
| `ALICE-SEC-029` | Encrypted Sensitive Data Vault | `cryptography` installé mais aucun coffre-fort implémenté | **MISSING** | Dépend de RBAC (28) et Audit log |
| `ALICE-OPS-030` | Observability & Self-Diagnostics Dashboard | `diagnostic_pc` cassé (`psutil` absent), logs fichiers bruts | **PARTIAL** | Dépend de RBAC (28) pour accès Admin sécurisé |

---

## 4. RISQUES IDENTIFIÉS ET STRATÉGIE DE MITIGATION

1. **Régression sur les contrôles P0/P1 existants :** `test_p1_production_exposure_006.py` interdit strictement `.innerHTML`, `.outerHTML`, `document.write`, `eval(`, `localStorage` tokens, et vérifie les en-têtes CSP exacts de `MobileHandler`. *Mitigation :* Utilisation exclusive d'APIs DOM sécurisées (`createElement`, `textContent`) dans `mobile/app.js` et non-régression systématique à chaque vague.
2. **Effets de bord à l'import de `main2.py` :** Les suites P0/P1 importent `main2` directement. Tout thread, boucle ou socket lancé à l'import casserait le gating. *Mitigation :* Tous les démons (Watchdog, Jobs, Briefings, RTSP Sentinel) seront strictement instanciés en mode passif et démarrés uniquement dans `start_ia()` ou par appel explicite `.start()`.
3. **Indisponibilité matérielle/externe (HA, OAuth Google, RTSP) :** Aucun serveur Home Assistant actif, pas de `token.pickle`, pas de caméra IP. *Mitigation :* Implémentation réelle complète côté code et protocole avec bascule explicite en état dégradé (`UNAVAILABLE` / `AUTH_REQUIRED` / `UNKNOWN`) et marquage transparent `PARTIAL` dans les rapports d'acceptation là où le matériel externe est absent.
4. **Contrainte RAM (~3.6 Go libres) :** Pas de PyTorch/YOLO lourd. *Mitigation :* Algorithmes natifs légers en C/C++ via `numpy` + `cv2` (HOG + MOG2 + FFT) et `cryptography` (OpenSSL AES-GCM).

---

## 5. ROADMAP ET STRATÉGIE DE TESTS

Le déploiement suivra strictement l'ordre **Wave 0 (Fondation) → Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5 → Wave 6**, avec exécution systématique d'une suite dédiée dans `tests/alice_ultimate/` (unitaires, intégration, sécurité adversariale, concurrence, erreurs, performance) et ré-exécution globale des **132 tests de non-régression P0/P1/007** à chaque frontière de vague.
