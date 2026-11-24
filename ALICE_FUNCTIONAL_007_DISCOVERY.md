# 🔍 ALICE — RAPPORT D'INVENTAIRE FORENSIQUE ET CARTOGRAPHIE FONCTIONNELLE
## PHASE A : FORENSIC DISCOVERY & AUDIT DE L'EXISTANT

**Mission ID :** `ALICE-FUNCTIONAL-PLATFORM-EVOLUTION-007`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  
**Classification :** PRODUCT ENGINEERING / FORENSIC DISCOVERY  
**Référence Sécurité :** P0 Gate-005 (Homologation 86/86 PASS certifiée au commit `b1f67aa`)  
**Branche Git :** `main`  
**Commit HEAD :** `b1f67aa2003deb6abbaa06f1e50827812a513de6`  
**Répertoire racine :** `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`  

---

## 1. CARTOGRAPHIE TECHNIQUE DU SYSTÈME RÉEL

L'inspection forensique du dépôt démontre que l'ensemble du code source applicatif est concentré sous le sous-dossier `Jarvis Final - SITE/`. L'arborescence racine contient les archives d'audit de sécurité antérieures (Gate-001 à Gate-005).

```
Jarvis Final - SITE-V2/
├── .gitignore
├── README.md
├── ALICE_P0_*.md (Dossiers d'homologation P0)
└── Jarvis Final - SITE/
    ├── main2.py                 (4630 lignes : Serveur central HTTP/WS, boucle IA, dispatch d'actions)
    ├── alice_modules.py         (1260 lignes : 16 modules experts Alice, RateLimiter, client HF/Gemini)
    ├── jarvis_agent.py          (154 lignes : Classe autonome JarvisAgent, prompt et mémoire)
    ├── vision_ocr.py            (188 lignes : JarvisVision, Tesseract OCR 5.5, EasyOCR, boucle écran)
    ├── list_models.py           (Utilitaire de listing des modèles Gemini)
    ├── credentials.json         (Identifiants client OAuth2 Google - sans jeton actif)
    ├── jarvis_memoire.json      (Fichier mémoire persistant JSON)
    ├── knowledge/               (Base documentaire locale : Classeur1.xlsx)
    ├── tessdata/                (eng.traineddata, fra.traineddata pour Tesseract)
    ├── mobile/                  (Client web mobile dédié)
    │   ├── index.html           (Structure UI mobile, modale appairage PIN, orbe Three.js)
    │   ├── app.js               (531 lignes : Client WebSocket, SpeechRecognition, gestion TTS)
    │   ├── orb.js               (Rendu 3D Canvas de l'orbe énergétique)
    │   └── style.css            (Feuille de style mobile)
    ├── frontend/                (Client web Desktop Vite/TypeScript)
    │   ├── index.html
    │   ├── package.json
    │   └── src/ (main.ts, orb.ts, avatar.ts, screen_capture.ts)
    └── venv/                    (Environnement virtuel Python 3.11.8)
```

---

### 1.1 Architecture Backend (`main2.py`)
- **Serveur HTTP / WebSockets Hybride :**
  - Serveur HTTP multithreadé (`ThreadingHTTPServer`) servant les assets statiques de l'application mobile (`mobile/`).
  - Serveur WebSocket asynchrone (`websockets` sous `asyncio`) sur le port 8765, gérant le streaming audio, les ordres de capture d'écran et les commandes textuelles/vocales.
  - Sécurité des transports : Prise en charge TLS/WSS en production avec mode fail-closed (`FAIL_CLOSED_TLS_REQUIRED`) certifié C-01.
- **Gestionnaire de Sessions & Appairage (`WSSessionManager`, `PairingManager`) :**
  - Contrôle d'origine strict (`is_origin_allowed`) neutralisant les attaques CSWSH (C-02).
  - Appairage PIN cryptographique à 6 chiffres pour les terminaux mobiles distants (SEC-04).
  - Validation des sessions locales (loopback 127.0.0.1/::1) et distantes avec jetons rotatifs.
- **Boucle Principale d'Orchestration (`traiter_reponse_ia`) :**
  - Cascade de résolution locale (calculs mathématiques, syntaxe française, conversions d'unités, traductions).
  - Filtrage des actions système critiques via `SystemActionController` avec isolation multi-session.
  - Génération de streaming via l'IA (Google Gemini 2.5/2.0 avec fallback local ou Grok).
  - Parsing regex des blocs JSON d'actions (`re.findall(r'\{.*?\}', ...)`).
  - Dispatch synchrone/asynchrone vers 70 actions répertoriées.

---

### 1.2 Architecture Frontend Desktop & Mobile
- **Frontend Mobile (`mobile/app.js`, `mobile/index.html`) :**
  - Rendu 3D d'un orbe réactif en WebGL via Three.js r128 (`mobile/orb.js`).
  - Reconnaissance vocale client via `webkitSpeechRecognition` / `SpeechRecognition`.
  - Synthèse vocale hybride : réception audio base64 généré côté serveur (Edge-TTS) avec repli vers la synthèse vocale Web Speech API (`SpeechSynthesisUtterance`).
  - *Lacune constatée :* Absence totale de suivi d'états d'exécution des commandes (ni statut `RUNNING`, ni accusé `SUCCEEDED`/`FAILED`, ni modale de confirmation pour actions critiques).
- **Frontend Desktop (`frontend/src/main.ts`) :**
  - Application Single-Page sous Vite et TypeScript.
  - Visualisation d'orbe 3D Three.js et avatar.
  - Capture d'écran dynamique (`screen_capture.ts`) via l'API `getDisplayMedia` du navigateur, transmise en WebSocket vers le backend Python pour la vision IA.

---

### 1.3 Architecture de la Mémoire et RAG
- **Mémoire Factuelle Court/Moyen Terme :**
  - Stockage dans `jarvis_memoire.json`.
  - Verrouillage inter-processus et atomique certifié (`CrossProcessMemoryLock` via `msvcrt.locking` sous Windows / `fcntl.flock` sous POSIX) avec écriture atomique `os.replace`.
  - Schéma : dictionnaire clé/valeur associant `{"valeur": str, "timestamp": str}`.
- **RAG Documentaire :**
  - Fonction `charger_contexte_rag()` dans `main2.py` : injection brute de documents `.txt` et `.pdf` dans le prompt système de l'IA.
  - Fonction `indexer_knowledge_base()` et `recherche_semantique()` dans `alice_modules.py` : découpage naïf en chunks de 500 caractères stockés dans un dictionnaire Python en mémoire (`self._vector_store`). Recherche par simple comptage d'occurrences de mots-clés.
  - *Lacune constatée :* Aucune persistance des chunks vectoriels, échec si `HF_TOKEN` est absent (dépendance artificielle non utilisée), aucun support des fichiers `.xlsx` pourtant présents dans `knowledge/` (`Classeur1.xlsx`).

---

### 1.4 Architecture des Intégrations Externes
- **Home Assistant (`HA_URL`, `HA_TOKEN`) :**
  - API REST `/api/services/{domain}/{service}` et `/api/states/{entity_id}`.
  - Implémentation certifiée C-04 : Découplage strict entre l'envoi de l'ordre HTTP et la vérification de l'état physique réel (`ha_verifier_changement_etat`).
- **Google Workspace (`credentials.json`, `token.pickle`) :**
  - Modules Google Docs, Drive, Gmail, Sheets, Calendar.
  - *Constat d'audit :* `credentials.json` est un fichier de secrets client valide, mais `token.pickle` est absent. Les fonctions échouent ou ouvrent un serveur OAuth local interactif bloquant le serveur en arrière-plan.
- **Moteur de Vision OCR (`vision_ocr.py`) :**
  - Tesseract OCR v5.5.0 installé sur le système hôte (`C:\Program Files\Tesseract-OCR\tesseract.exe`), données linguistiques `fra` et `eng` opérationnelles.
  - Traitement d'image OpenCV (niveaux de gris, redimensionnement bicubique, flou gaussien, binarisation adaptative Otsu).
  - EasyOCR présent en mode optionnel paresseux.

---

## 2. CARTOGRAPHIE FONCTIONNELLE EXHAUSTIVE

| Feature ID | Fonctionnalité | Implémentation | API / Protocole | Interface | Dépendances | État | Risque | Priorité | Action Recommandée |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **FEAT-ORCH-01** | Reconnaissance intention & classification | `main2.py:traiter_reponse_ia` | Gemini / Grok / Local Regex | Mobile / Web / Vocal | `google-genai`, `re` | **WORKING** | IA Hallucination | P1 | Structurer le cycle d'analyse |
| **FEAT-ORCH-02** | Contrat de cycle de vie de commande | Non implémenté (fire-and-forget) | WebSocket `mobile_command` | N/A (manquant) | `websockets` | **MISSING** | Manque de traçabilité | P0 | **Implémenter le cycle 9 états** |
| **FEAT-ORCH-03** | Commandes PC sensibles (Arrêt/Reboot) | `main2.py:SystemActionController` | Commandes locales OS | Console / Voix | `os`, `subprocess` | **WORKING** | Sécurité système | P0 | Conserver isolation de session |
| **FEAT-ORCH-04** | Lancement d'applications PC | `main2.py:lancer_app` | `subprocess.Popen` | Voix / Mobile | `os`, `subprocess` | **WORKING** | RCE si non filtré | P1 | Validation stricte des chemins |
| **FEAT-ORCH-05** | Gestion de fichiers locale | `main2.py:ouvrir_dossier`, `trier_*` | OS File System | Voix / Mobile | `pathlib`, `shutil` | **WORKING** | Path traversal | P1 | Restreindre aux dossiers sûrs |
| **FEAT-ORCH-06** | Synthèse vocale TTS & Streaming | `main2.py:parler`, `edge-tts` | Async TTS / Pygame | Haut-parleur / Web | `edge_tts`, `pygame` | **WORKING** | Latence audio | P2 | Conserver le streaming |
| **FEAT-ORCH-07** | Détection vocale & réveil | `main2.py:ecouter`, `monitor_claps` | PyAudio / SpeechRecognition | Micro PC | `speech_recognition` | **PARTIAL** | Blocage I/O micro | P2 | Découplage async maîtrisé |
| **FEAT-MEM-01** | Mémoire factuelle persistante | `main2.py:charger/sauvegarder_memoire` | JSON avec `CrossProcessMemoryLock` | Voix / Mobile | `msvcrt`, `json` | **WORKING** | Concurrence multi-proc | P0 | Maintenir le verrou cross-process |
| **FEAT-MEM-02** | RAG Documentaire & Sémantique | `main2.py:charger_contexte_rag` | Injection prompt / Dict mémoire | Voix / Mobile | `PyPDF2`, `pathlib` | **PARTIAL** | Débordement token, HF requis | P1 | **Rénover moteur RAG local & XLSX** |
| **FEAT-WEB-01** | Recherche Web SerpAPI | `main2.py:recherche_web_serpapi` | REST `https://serpapi.com` | Voix / Mobile | `requests` | **PARTIAL** | Dépendance clé API externe | P2 | Gérer l'absence de clé proprement |
| **FEAT-WEB-02** | Agent Web autonome visuel | `alice_modules.py:agent_web_action` | `webbrowser` + Gemini Vision | Écran PC | `pyautogui`, `PIL` | **PARTIAL** | SSRF, URL non validée | P1 | **Sécuriser URL & filtrage SSRF** |
| **FEAT-WEB-03** | Recherche & Lecture YouTube | `main2.py:chercher_youtube` | `yt-dlp` / Webbrowser | Navigateur | `webbrowser` | **WORKING** | Timeout réseau | P2 | Conserver |
| **FEAT-GW-01** | Adaptateur Google Workspace Auth | `main2.py:get_google_creds` | OAuth2 Google API | Navigateur | `google_auth_oauthlib` | **BLOCKED** | Token absent, blocage console | P1 | **Créer Adaptateur testable** |
| **FEAT-GW-02** | Google Docs (Création/Édition) | `main2.py:creer_google_doc` | Google Docs API v1 | Navigateur | `googleapiclient` | **BLOCKED** | Auth manquante | P2 | Adaptateur découplé |
| **FEAT-GW-03** | Google Sheets | `main2.py:creer_google_sheet` | Google Sheets API v4 | Navigateur | `googleapiclient` | **BLOCKED** | Auth manquante | P2 | Adaptateur découplé |
| **FEAT-GW-04** | Gmail (Lecture/Rédaction) | `main2.py:lire_emails`, `alice_rediger_email` | Gmail API v1 | Voix / Sortie texte | `googleapiclient` | **PARTIAL** | Envoi email sans confirmation | P1 | **Exiger confirmation explicite** |
| **FEAT-GW-05** | Google Calendar | `main2.py:lister_evenements_calendar` | Google Calendar API v3 | Voix / Sortie texte | `googleapiclient` | **BLOCKED** | Auth manquante | P2 | Adaptateur découplé |
| **FEAT-MOB-01** | Connexion Mobile WSS & TLS | `main2.py:start_mobile_http_server` | WSS port 8765 | Mobile browser | `ssl`, `websockets` | **WORKING** | Certificats prod | P0 | Certifié C-01 (conserver) |
| **FEAT-MOB-02** | Appairage PIN Mobile | `main2.py:PairingManager` | HTTP POST `/pair` | Modale PIN mobile | `secrets` | **WORKING** | Brute force PIN | P0 | Certifié SEC-04 (conserver) |
| **FEAT-MOB-03** | Orbe 3D Mobile & Audio distant | `mobile/app.js`, `mobile/orb.js` | WebGL Three.js + Base64 Audio | Écran mobile | `three.min.js` | **WORKING** | Performance mobile | P2 | Conserver |
| **FEAT-MOB-04** | Traçabilité des commandes Mobile | Non implémenté | WebSocket | Écran mobile | `mobile/app.js` | **MISSING** | Absence de feedback | P1 | **Implémenter UI cycle de vie** |
| **FEAT-OCR-01** | OCR Temps Réel Écran | `vision_ocr.py:JarvisVision` | Tesseract v5.5 CLI / C++ | Arrière-plan | `pytesseract`, `cv2` | **WORKING** | Charge CPU continue | P2 | Vérifié fonctionnel |
| **FEAT-OCR-02** | Téléversement sécurisé & OCR Doc | `main2.py:ws_handler (file_upload)` | WebSocket payload b64 | Client Web | `main2.py` | **WORKING** | Path traversal | P0 | Certifié SEC-02 (conserver) |
| **FEAT-AUTO-01** | Rappels & Workflows programmés | `main2.py:add_reminder` | Enregistrement JSON mémoire | Voix / Mémoire | `datetime` | **PARTIAL** | Aucun scheduler d'exécution | P2 | Ajouter moteur de déclenchement |
| **FEAT-AUTO-02** | Mode Iron Man (Clap Detection) | `main2.py:monitor_claps` | PyAudio RMS stream | Matériel PC | `pyaudio` | **WORKING** | Faux positifs claquements | P3 | Conserver |
| **FEAT-HA-01** | Domotique Home Assistant Lumières/Prises | `main2.py:ha_lumiere`, `ha_interrupteur` | REST API Home Assistant | Voix / Mobile | `requests` | **WORKING** | Indisponibilité passerelle HA | P0 | Certifié C-04 (vérité terrain) |
| **FEAT-HA-02** | Domotique Capteurs (Temp, Batterie) | `main2.py:ha_get_etat` | REST API Home Assistant | Voix / Mobile | `requests` | **WORKING** | Entités non configurées | P2 | Gérer l'état inconnu |
| **FEAT-SURV-01** | Vidéosurveillance par image IA | `alice_modules.py:analyser_video_surveillance` | Gemini Vision | Sortie texte | `PIL`, `google-genai` | **PARTIAL** | Pas de flux caméra RTSP réel | P3 | Documenter périmètre réel |
| **FEAT-OBS-01** | Journalisation d'audit de sécurité | `main2.py:SystemActionController.log_audit`| Fichier texte local append-only | `security_audit.log` | `datetime` | **WORKING** | Remplissage disque | P1 | Conserver & anonymiser |
| **FEAT-OBS-02** | Métriques et Santé du système | `alice_modules.py:get_status`, `diagnostic_pc` | Inspection locale psutil/win32 | Voix / JSON | `psutil` | **PARTIAL** | Métriques non exposées au web | P2 | Exposer état des services |

---

## 3. SYNTHÈSE FORENSIQUE DE L'INVENTAIRE

1. **Le socle de sécurité P0 (Gate-005) est robuste et validé :**
   Les mécanismes `CrossProcessMemoryLock`, `SystemActionController`, `WSSessionManager`, `PairingManager` et la vérification d'état physique Home Assistant sont pleinement opérationnels et certifiés par 86 tests reproductibles.
2. **Le maillon faible fonctionnel réside dans l'absence de contrat d'exécution de bout en bout :**
   Le backend traite les commandes en aveugle (« fire-and-forget »). L'interface mobile ne reçoit aucune télémétrie de progression et ne peut ni afficher le statut d'une action (`VALIDATING`, `RUNNING`, `SUCCEEDED`, `FAILED`), ni demander une confirmation interactive visuelle pour les ordres sensibles.
3. **Le système RAG actuel est rudimentaire et partiellement défaillant :**
   Il dépend d'un token HuggingFace non nécessaire, ne persiste aucun index, n'analyse pas les tableurs `.xlsx` existants et procède à une recherche par simple comptage de mots.
4. **Les intégrations externes (Google Workspace) requièrent un adaptateur découplé :**
   Sans `token.pickle`, les appels bloquent ou échouent sans retour gracieux. Un adaptateur d'intégration testable avec politique de confirmation stricte est nécessaire.
