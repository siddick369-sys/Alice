# RAPPORT D'AUDIT FORENSIQUE, FONCTIONNEL, TECHNIQUE ET OPÉRATIONNEL INTÉGRAL
## PROJET : J.A.R.V.I.S / A.L.I.C.E — SITE-V2
**Mission :** ALICE-FORENSIC-AUDIT-001  
**Auditeur :** Senior Software Architect, Principal Python Engineer, QA Automation, DevSecOps & AI Systems Engineer  
**Date d'audit :** 22 Novembre 2026  
**Mode d'investigation :** READ-ONLY STRICT — CONTRADICTOIRE SANS CONCESSION  
**Statut global du système :** CRITIQUE — RÉVISION MAJEURE REQUISE AVANT TOUTE ÉVOLUTION  

---

## 1. RÉSUMÉ EXÉCUTIF

L'audit forensique approfondi du projet **J.A.R.V.I.S / A.L.I.C.E (SITE-V2)** a été conduit selon une méthodologie rigoureuse et contradictoire, vérifiant chaque ligne de code, chaque point d'entrée réseau, chaque dépendance et chaque affirmation architecturale.

### Constats majeurs :
1. **Divergence substantielle entre discours et réalité technique :** Le projet se présente comme un assistant vocal autonome, fonctionnant « 100% hors-ligne », doté de 16 super-pouvoirs, d'un RAG sémantique, d'un contrôle domotique et d'une vision multimodale. En réalité, **la reconnaissance vocale repose intégralement sur l'API cloud Google (`SpeechRecognition.recognize_google`)** et est **totalement inopérante hors-ligne**. Ollama n'est ni installé, ni en écoute, et le modèle de repli local n'est qu'un ensemble de 5 fonctions regex/dictionnaires basiques.
2. **Défaillances de dépendances majeures (7 bibliothèques clés manquantes) :** L'environnement virtuel du projet (`venv`) ne contient ni `huggingface_hub`, ni `psutil`, ni `easyocr`, ni `rembg`, ni `whisper`, ni `openpyxl`, ni `youtube-transcript-api`. En conséquence directe, **au moins 7 des 16 modules d'Alice sont rigoureusement inopérants dès leur premier appel**.
3. **Vulnérabilités de sécurité critiques :**
   - **RCE Arbitraire sans bac à sable :** Le module `alice_debug_code` (`verifier_code_boucle`) exécute du code arbitraire non filtré via `subprocess.run(["python", temp_file])`.
   - **Traversée de répertoire (Path Traversal) :** La réception de fichier WebSocket (`file_upload`) concatène le nom fourni par le client directement avec `os.path.join(temp_dir, filename)` sans assainissement, permettant l'écrasement de fichiers du système.
   - **Extinction non sollicitée du PC :** Toute phrase contenant le mot « eteins » (ex: « éteins la lumière » sans accentuation) déclenche `os.system("shutdown /s /t 5")` sans confirmation.
   - **Fuite de données privées :** Chaque requête IA envoie l'intégralité du texte extrait de l'écran par OCR dans le prompt vers les API cloud tierces sans consentement granulaire.
4. **Bugs de blocage de l'Event Loop et rupture de protocole :**
   - **Capture d'écran Web brisée par indentation :** Dans `main2.py`, le traitement du retour de capture d'écran est indenté à l'intérieur du bloc `file_upload`. La capture d'écran demandée au frontend expire systématiquement après 15 secondes d'attente.
   - **Corruption définitive de la mémoire :** La fonction `add_reminder` insère une liste dans `jarvis_memoire.json`. Lors du prochain appel, `construire_contexte_memoire` tente d'accéder à `data['valeur']` sur cette liste, provoquant un `TypeError` fatal qui bloque tout le démarrage et les requêtes IA.
   - **Appels synchrones bloquants dans le thread asynchrone :** `time.sleep` (jusqu'à 14 secondes dans `action_whatsapp_appel`), `requests.get/post` synchrones (timeouts de 5s répétés sur Home Assistant et météo) bloquent l'event loop asyncio, figeant les WebSockets et l'affichage de l'orbe 3D.
   - **Affirmations d'actions sans vérification :** Toutes les commandes domotiques Home Assistant annoncent le succès vocalement sans jamais vérifier si l'API a retourné un code d'erreur ou si l'équipement a réagi.

---

## 2. ÉTAT INITIAL DU PROJET

L'arborescence analysée est située dans `C:\Users\USER\Desktop\Jarvis Final - SITE-V2`.
- Le dossier racine contient un sous-dossier principal `Jarvis Final - SITE`, un fichier de notes `lire.txt`, un fichier `README.md` et un fichier `.gitignore`.
- Le projet a fait l'objet d'une personnalisation automatisée par `install.bat`, ayant substitué globalement la chaîne `'Mickael'` par `'Aboubakar Ibrahim Siddick'` dans `main2.py` et `jarvis_agent.py`, y compris au sein de clés de dictionnaires python (`APPAREILS_BATTERIE`).
- Deux lanceurs batch concurrents coexistent : `DEMARRER_JARVIS.bat` (fonctionnel avec chemin relatif vers `.\venv`) et `DÉMARRER_JARVIS.bat` (défectueux, contenant un chemin absolu codé en dur vers un compte utilisateur étranger `c:\Users\ASUS TUF\Desktop\MON_JARVIS\.venv-1`).
- 57 fichiers audio résiduels `.mp3` générés par `edge-tts` polluent la racine de `Jarvis Final - SITE` pour un volume de ~7.86 Mo, attestant de l'échec récurrent de la suppression automatique des fichiers temporaires audio sur Windows.

---

## 3. INVENTAIRE FORENSIQUE COMPLET

### 3.1. Métriques globales
- **Nombre total de fichiers catalogués :** 100 fichiers
- **Fichiers audio résiduels (.mp3) :** 57 fichiers (7 859 808 octets)
- **Fichiers de code source Python (.py) :** 5 fichiers (5 218 lignes)
- **Fichiers TypeScript / JavaScript (.ts, .js) :** 8 fichiers
- **Fichiers HTML / CSS :** 6 fichiers
- **Scripts Batch (.bat) :** 5 fichiers
- **Fichiers de données et mémoires (.json, .xlsx, .pdf, .traineddata) :** 10 fichiers

### 3.2. Inventaire détaillé des fichiers du projet

| Chemin relatif | Taille | Lignes | Type | Rôle réel & État |
|---|---|---|---|---|
| `main2.py` | 172 572 B | 3 673 | Python | **Cœur monolithique** : WebSocket, HTTP mobile, orchestration IA, TTS, STT, Domotique, RAG basique, actions PC. Actif, dette technique critique. |
| `alice_modules.py` | 52 987 B | 1 220 | Python | **16 modules Alice** (HF + Gemini). Actif mais 7/16 modules bloqués par dépendances manquantes. |
| `vision_ocr.py` | 7 113 B | 188 | Python | Capture d'écran `mss` + OCR Tesseract / EasyOCR. EasyOCR indisponible. Actif via thread d'arrière-plan. |
| `jarvis_agent.py` | 4 654 B | 129 | Python | **Script autonome CLI expérimental**. **SYNTAX ERROR L77** (invalide). Non importé par `main2.py` (déconnecté). |
| `list_models.py` | 259 B | 8 | Python | Utilitaire de test des modèles Groq. Isolé / manuel. |
| `jarvis_memoire.json` | 377 B | 18 | JSON | Mémoire clé/valeur utilisateur. Vulnérable à la corruption de schéma via `add_reminder`. |
| `.env` | 382 B | 11 | Config | Variables d'environnement. Clés présentes : GEMINI, GROQ, SERPAPI, HF. Placeholders : HA_TOKEN, XAI_API_KEY. |
| `credentials.json` | 410 B | 1 | JSON | Identifiants client OAuth 2.0 Google. Présent mais sans jeton validé (`token.pickle` absent). |
| `VOS_API.txt` | 657 B | 30 | Doc | Guide utilisateur d'obtention des clés API. |
| `METTRE_ICI_VOTRE_CREDENTIALS_JSON.txt` | 391 B | 9 | Doc | Instructions OAuth Google. |
| `lire.txt` | 3 768 B | 34 | Doc | Spécification théorique et souhaits d'évolution. Non représentatif du code réel. |
| `requirements.txt` | 3 224 B | 165 | Config | Dépendances pip. Incomplet (manque `psutil`, `huggingface_hub`, `rembg`, `whisper`, `easyocr`). Contient des libs inutilisées (`Panda3D`, `ursina`). |
| `DEMARRER_JARVIS.bat` | 123 B | 6 | Batch | Lanceur opérationnel via `.\venv\Scripts\python.exe main2.py`. |
| `DÉMARRER_JARVIS.bat` | 556 B | 19 | Batch | **Lanceur brisé** : pointe vers `c:\Users\ASUS TUF\Desktop\MON_JARVIS\.venv-1`. |
| `install.bat` | 10 164 B | 286 | Batch | Script d'installation automatique. Modifie le code source en direct (remplacement de prénom). |
| `frontend/package.json` | 357 B | 19 | Node | Config interface Three.js + Vite. Dépendance `three: ^0.170.0`. |
| `frontend/src/main.ts` | 8 363 B | 227 | TS | Contrôleur Web : WebSocket, Orbe, PTT, Upload, Capture d'écran. |
| `frontend/src/orb.ts` | 27 352 B | 673 | TS | Particules Three.js (2000 points, liaisons, électrons, modes idle/listen/think/speak). |
| `frontend/src/screen_capture.ts` | 2 175 B | 68 | TS | Capture écran via `navigator.mediaDevices.getDisplayMedia`. |
| `frontend/src/avatar.ts` | 4 667 B | 125 | TS | **Code mort / Déconnecté** : Mesh 3D tête robotique alternatif, non importé dans `main.ts`. |
| `frontend/dist/` | ~480 KB | - | Build | **Bundle obsolète** : build ancien non synchronisé avec `index.html` (manque upload/inputs). |
| `mobile/index.html` | 3 748 B | 84 | HTML | Interface Web mobile PTT. Avertissement HTTPS avec IP codée en dur `192.168.1.23`. |
| `mobile/app.js` | 14 287 B | 411 | JS | Logique mobile : Web Speech API, Audio Base64, fallback synthèse vocale locale. |
| `mobile/orb.js` | 20 652 B | 563 | JS | Port Vanilla JS de l'orbe Three.js pour navigateur mobile. |
| `knowledge/Classeur1.xlsx` | 17 698 B | - | Excel | Document présent dans la base mais **totalement ignoré** par le RAG (ni lu par `main2.py` ni par `alice_modules.py`). |
| `tessdata/*.traineddata` | ~5.2 MB | - | Data | Dictionnaires Tesseract eng/fra. Utilisés correctement par pytesseract. |

---

## 4. ARCHITECTURE RÉELLEMENT OBSERVÉE

Contrairement à une architecture modulaire en microservices ou en couches propres, l'application est structurée autour d'un **monolithe asynchrone dense (`main2.py`)** couplé à des threads concurrents mal isolés :

```
                        +---------------------------------------+
                        |      Clients Navigateurs & Mobiles    |
                        +---------------------------------------+
                                  |                     |
                HTTP :8080 (mobile/ SimpleHTTP)         | WS :8765 (websockets)
                                  v                     v
                        +---------------------------------------+
                        |    main2.py (Monolithe 3673 lignes)   |
                        +---------------------------------------+
                               /          |                                        /           |                                        v            v            v
                   Thread écoute   Thread Claps   Thread Monitor
                   Microphone STT  Audioop RMS    System / Agenda
                   (Google Cloud)  (Seuil 1200)   (psutil crash)
                             \            |            /
                              v           v           v
                        +---------------------------------------+
                        |    Moteur de décision & Actions       |
                        |      traiter_reponse_ia (L2473)       |
                        +---------------------------------------+
                         /         |            |                                 v          v            v          v
                 Cloud IA    Home Assistant   Windows    AliceModules
                 Gemini 2.5  (Requests sync   PyAutoGUI  (alice_modules.py)
                 Groq (KO)    Timeout 5s)     os.system  (7/16 KO par venv)
                 Grok (KO)                    shutdown!
                 Ollama (KO)
```

---

## 5. MATRICE COMPLÈTE DES FONCTIONNALITÉS ET TRAÇABILITÉ

Chaque fonctionnalité annoncée dans `README.md`, `lire.txt` ou le code a été passée au crible :

| ID | Fonctionnalité | Composant / Fichier | Ligne / Méthode | Dépendances réelles | Statut | Justification technique & Preuve |
|---|---|---|---|---|---|---|
| F01 | Orbe 3D Three.js Desktop | `frontend/src/orb.ts` | L29 `createOrb` | Three.js | **IMPLEMENTED_AND_VERIFIED** | Rendu Three.js fluide, modes idle/listen/think/speak validés par typage et code. |
| F02 | Avatar 3D Tête Robotique | `frontend/src/avatar.ts` | L11 `createAvatar` | Three.js | **DISCONNECTED** | Fichier présent mais jamais importé dans `main.ts` ni référencé dans l'UI. |
| F03 | Interface Mobile Responsive | `mobile/index.html` | L1-84 | Three.js CDN | **PARTIALLY_IMPLEMENTED** | UI affichable, mais bloquée sur smartphone sans HTTPS pour le micro. |
| F04 | Synthèse vocale Edge-TTS | `main2.py` | L1815 `parler` | edge-tts, pygame | **IMPLEMENTED_AND_VERIFIED** | Génération fonctionnelle, voix `fr-FR-HenriNeural`, mais laisse des MP3 orphelins. |
| F05 | Synthèse vocale pyttsx3 | `main2.py` | L1895 | pyttsx3 | **IMPLEMENTED_AND_VERIFIED** | Fallback offline fonctionnel si Edge-TTS indisponible. |
| F06 | Parallélisation vocale | `main2.py` | L2526 | asyncio.gather | **IMPLEMENTED_BUT_BROKEN** | Lancer la phrase 2 coupe immédiatement la phrase 1 (`STOP_PARLER=True` L1820). |
| F07 | Reconnaissance vocale micro | `main2.py` | L3246 `ecouter` | SpeechRecognition | **PARTIALLY_IMPLEMENTED** | Fonctionne en ligne via `recognize_google`, mais 100% inopérante hors-ligne. |
| F08 | Clap Detection (Iron Man) | `main2.py` | L3338 `monitor_claps` | audioop, pyaudio | **IMPLEMENTED_BUT_BROKEN** | Conflit micro avec `ecouter()`, faux positifs élevés, `audioop` déprécié/retiré en Python 3.13. |
| F09 | Wake Word Local (Porcupine/Snowboy) | - | - | - | **NOT_IMPLEMENTED** | Annoncé dans `lire.txt`, aucun SDK ni modèle local. Simple test textuel post-STT cloud. |
| F10 | Cerveau Google Gemini | `main2.py` | L2158 `_call_gemini` | google.genai | **IMPLEMENTED_AND_VERIFIED** | Clé active, modèle `gemini-2.5-flash` détecté et fonctionnel. |
| F11 | Cerveau Groq (Qwen) | `main2.py` | L2414 `demander_groq` | groq / openai | **IMPLEMENTED_BUT_BROKEN** | Noms de modèles invalides (`qwen3.6-27b`, `qwen-2.5-32b`). Modèle réel : `qwen/qwen3.8-27b`. Erreur 404. |
| F12 | Cerveau xAI Grok | `main2.py` | L2335 `demander_grok` | openai | **BLOCKED** | Clé placeholder dans `.env` (`VOTRE_CLE_ICI`). Non utilisable. |
| F13 | Cerveau local Ollama | `main2.py` | L2366 `demander_ollama` | requests (HTTP 11434) | **BLOCKED** | Service Ollama absent du système (`TcpTestSucceeded: False`), package python non installé. |
| F14 | Solveur Mathématique Local | `main2.py` | L1980 | re, math, eval | **IMPLEMENTED_BUT_BROKEN** | Bug regex L1999 : « racine de 25 » transformé en `sqrt25` -> `NameError`, retourne `None`. |
| F15 | Dictionnaire Français Local | `main2.py` | L2032 | dict interne | **IMPLEMENTED_AND_VERIFIED** | Dictionnaire statique de 5 mots et verbes être/avoir. Extrêmement limité. |
| F16 | Convertisseur d'unités Local | `main2.py` | L2067 | re, float | **IMPLEMENTED_AND_VERIFIED** | Conversions km/miles, °C/°F, EUR/USD fonctionnelles. |
| F17 | Traduction locale | `main2.py` | L2114 | dict interne | **IMPLEMENTED_AND_VERIFIED** | Traduction mot-à-mot de 10 mots courants (en, es, de). |
| F18 | Diagnostic PC | `main2.py` | L1696 & L1790 | psutil | **IMPLEMENTED_BUT_BROKEN** | Fonctions définies 2 fois. `psutil` absent du venv -> `AttributeError`, retourne `None`. |
| F19 | Mode Focus | `main2.py` | L2962 | webbrowser, HA | **PARTIALLY_IMPLEMENTED** | Modifie la variable globale et ouvre YouTube, mais échoue silencieusement sur HA. |
| F20 | Lancement d'applications | `main2.py` | L1465 `lancer_app` | subprocess, where | **IMPLEMENTED_AND_VERIFIED** | Dictionnaire d'applications + fallback PATH et raccourcis menu Démarrer. |
| F21 | Contrôle volume / capture PC | `main2.py` | L1663 `executer_action_pc` | pyautogui | **IMPLEMENTED_AND_VERIFIED** | Touches multimédias et capture d'écran bureau opérationnelles. |
| F22 | Extinction Système PC | `main2.py` | L1681 | os.system | **IMPLEMENTED_BUT_BROKEN** | Déclenchement abusif sur le mot « eteins », aucun dialogue de confirmation. |
| F23 | Capture d'écran frontend | `main2.py` | L512 `request_screen_capture` | WebSocket, main.ts | **IMPLEMENTED_BUT_BROKEN** | Message `screen_frame` ignoré car indenté dans `file_upload`. Timeout 15s systématique. |
| F24 | Upload de fichiers Web | `main2.py` | L459 | base64, open | **IMPLEMENTED_AND_VERIFIED** | Réception base64 et extraction texte fonctionnelles, mais vulnérable au Path Traversal. |
| F25 | Extraction texte documents | `main2.py` | L112 `extraire_texte_doc` | PyPDF2, open | **PARTIALLY_IMPLEMENTED** | Lit TXT, code et PDF (via PyPDF2 déprécié). Ignore Excel (`.xlsx`), DOCX, etc. |
| F26 | Écriture de fichier PC | `main2.py` | L141 `ecrire_fichier_pc` | open | **IMPLEMENTED_AND_VERIFIED** | Écriture effective, mais aucun contrôle de sécurité (écrasement arbitraire). |
| F27 | Recherche YouTube | `main2.py` | L1449 `chercher_youtube` | requests (Google API) | **IMPLEMENTED_AND_VERIFIED** | Recherche opérationnelle avec la clé API configurée. |
| F28 | Météo Open-Meteo | `main2.py` | L1265 `get_meteo_actuelle` | requests | **IMPLEMENTED_AND_VERIFIED** | Géocodage et prévisions sans clé API externes opérationnels. |
| F29 | Alertes météo | `main2.py` | L1298 `get_alertes_meteo` | requests | **IMPLEMENTED_AND_VERIFIED** | Analyse des codes météo et alertes pluie/vent/orage opérationnelle. |
| F30 | Recherche SerpAPI | `main2.py` | L1075 | requests | **IMPLEMENTED_AND_VERIFIED** | Clé présente, interrogation Google Search via SerpAPI fonctionnelle. |
| F31 | Football TheSportsDB | `main2.py` | L1337 | requests | **IMPLEMENTED_AND_VERIFIED** | Requêtes API TheSportsDB v1 fonctionnelles. |
| F32 | Classement TheSportsDB | `main2.py` | L1400 | requests | **PARTIALLY_IMPLEMENTED** | Saison codée en dur à `2024-2025`. Obsolète. |
| F33 | Domotique Lumières | `main2.py` | L2664 `ha_lumiere` | requests (HA REST) | **IMPLEMENTED_BUT_BROKEN** | Ignore le statut HTTP réel. Clé token invalide dans `.env`. |
| F34 | Domotique Prises | `main2.py` | L2688 `ha_prise` | requests (HA REST) | **IMPLEMENTED_BUT_BROKEN** | Confirmation aveugle sans vérification du retour HA. |
| F35 | Domotique Capteurs / Temp / Batt | `main2.py` | L2695-L2728 | requests (HA REST) | **PARTIALLY_IMPLEMENTED** | Noms d'entités ultra-spécifiques et codés en dur pour un domicile particulier. |
| F36 | Domotique Alarme / Scènes | `main2.py` | L2733-L2745 | requests (HA REST) | **IMPLEMENTED_BUT_BROKEN** | Aucune confirmation d'armement réel. Entités codées en dur. |
| F37 | Domotique Linky Énergie | `main2.py` | L2788 `ha_energie` | requests (HA REST) | **IMPLEMENTED_BUT_BROKEN** | Boucle synchrone de 6 requêtes HTTP successives bloquant l'event loop jusqu'à 30s. |
| F38 | Domotique Aspirateur Bob | `main2.py` | L2832 `ha_aspirateur` | requests (HA REST) | **IMPLEMENTED_BUT_BROKEN** | Entité `vacuum.bob` codée en dur, pas de gestion d'erreur. |
| F39 | Google Docs Création/Modif | `main2.py` | L745 & L763 | googleapiclient | **BLOCKED** | Absence de jeton `token.pickle`. Déclenche `flow.run_local_server()` bloquant. |
| F40 | Google Gmail Lecture | `main2.py` | L781 `lire_emails` | googleapiclient | **BLOCKED** | Bloqué par l'absence d'authentification OAuth préalable. |
| F41 | Google Calendar Agenda | `main2.py` | L799 & L1753 | googleapiclient | **BLOCKED** | Fonctions dupliquées. Bloqué par l'absence d'authentification OAuth. |
| F42 | Google Sheets Création | `main2.py` | L818 `creer_google_sheet` | googleapiclient | **BLOCKED** | Bloqué par l'absence d'authentification OAuth. |
| F43 | WhatsApp Appel Audio | `main2.py` | L2443 `action_whatsapp_appel` | pyautogui, os.system | **IMPLEMENTED_BUT_BROKEN** | 14s de `time.sleep` bloquant l'event loop. Dépendance totale à l'UI desktop. |
| F44 | Vision OCR Surveillance | `vision_ocr.py` | L110 `_vision_loop` | mss, pytesseract | **IMPLEMENTED_AND_VERIFIED** | Thread actif, capture d'écran locale et OCR Tesseract fonctionnels. |
| F45 | Clic Visuel IA | `main2.py` | L830 `jarvis_vision_cliquer` | Gemini, Groq, pyautogui | **IMPLEMENTED_BUT_BROKEN** | Fallback Groq sur modèle inexistant, puis « clic aveugle » dangereux en haut à droite. |
| F46 | Écriture Visuelle IA | `main2.py` | L922 `jarvis_vision_ecrire` | Gemini, pyautogui | **IMPLEMENTED_BUT_BROKEN** | `time.sleep` bloquants, dépend de coordonnées normalisées souvent imprécises. |
| F47 | Gestion Fichiers (Trier/Déplacer) | `main2.py` | L270-L384 | shutil, os | **IMPLEMENTED_AND_VERIFIED** | Fonctions de tri et déplacement effectives, mais sans confirmation ni garde-fou. |
| F48 | Mémoire persistante | `main2.py` | L391 & L1713 | json | **PARTIALLY_IMPLEMENTED** | Doublon de code (`ajouter_memoire` vs `memory_add`). Pas de verrou fichier. |
| F49 | Rappels GPS (add_reminder) | `main2.py` | L2982 | json | **IMPLEMENTED_BUT_BROKEN** | Casse le format de `jarvis_memoire.json`. Jamais lu ni déclenché par la suite. |
| F50 | RAG contextuel prompt | `main2.py` | L165 `charger_contexte_rag` | os, extraire_texte_doc | **PARTIALLY_IMPLEMENTED** | Concatène brutalement tous les fichiers texte/PDF dans le prompt. Aucun vecteur. |
| F51 | Alice 01 - Génération d'images | `alice_modules.py` | L129 `generer_image` | huggingface_hub | **BLOCKED** | `huggingface_hub` non installé dans le venv. Client HF toujours `None`. |
| F52 | Alice 02 - Transcription Whisper | `alice_modules.py` | L180 `transcrire_audio` | huggingface_hub | **BLOCKED** | `huggingface_hub` non installé dans le venv. Client HF toujours `None`. |
| F53 | Alice 03 - Suppression de fond | `alice_modules.py` | L228 `supprimer_fond` | huggingface_hub, PIL | **BLOCKED** | `huggingface_hub` non installé dans le venv. Client HF toujours `None`. |
| F54 | Alice 04 - Analyse d'humeur audio | `alice_modules.py` | L301 `detecter_humeur_audio` | huggingface_hub | **BLOCKED** | `huggingface_hub` non installé dans le venv. Client HF toujours `None`. |
| F55 | Alice 05 - TTS custom HF | `alice_modules.py` | L355 `synthese_vocale_custom`| huggingface_hub | **BLOCKED** | `huggingface_hub` non installé dans le venv. Client HF toujours `None`. |
| F56 | Alice 06 - Analyse écran Gemini | `alice_modules.py` | L404 `analyser_ecran_contextuel`| google.genai, PIL | **IMPLEMENTED_AND_VERIFIED** | Analyse multimodale Gemini fonctionnelle. |
| F57 | Alice 07 - Lecture de photos | `alice_modules.py` | L461 `analyser_photo` | google.genai, PIL | **IMPLEMENTED_AND_VERIFIED** | Analyse d'images locales fonctionnelle. |
| F58 | Alice 08 - Vidéosurveillance | `alice_modules.py` | L513 `analyser_video_surveillance`| google.genai, pyautogui | **PARTIALLY_IMPLEMENTED** | Ne lit pas de flux RTSP/caméra. Analyse uniquement un screenshot local. |
| F59 | Alice 09 - Assistant de codage | `alice_modules.py` | L576 `assistant_codage` | google.genai | **IMPLEMENTED_AND_VERIFIED** | Agrégation de code et requête grand contexte Gemini fonctionnelles. |
| F60 | Alice 10 - Agent Web autonome | `alice_modules.py` | L655 `agent_web_action` | webbrowser, pyautogui | **PARTIALLY_IMPLEMENTED** | Ouvre la page et prend un screenshot. Ne boucle pas et ne clique pas réellement. |
| F61 | Alice 11 - Rédaction d'emails | `alice_modules.py` | L717 `rediger_email` | google.genai | **IMPLEMENTED_AND_VERIFIED** | Génération de texte d'email soignée avec signature. Sauvegarde locale. |
| F62 | Alice 12 - Planificateur agenda | `alice_modules.py` | L770 `planifier_agenda` | google.genai | **IMPLEMENTED_AND_VERIFIED** | Suggestions de créneaux deep work et pauses via prompt Gemini. |
| F63 | Alice 13 - Auto-debug de code | `alice_modules.py` | L836 `verifier_code_boucle` | subprocess, google.genai | **IMPLEMENTED_BUT_BROKEN** | Exécute du code arbitraire sans sandbox (RCE). Boucle de correction active. |
| F64 | Alice 14 - RAG vectoriel | `alice_modules.py` | L942 `indexer_knowledge_base` | huggingface_hub | **BLOCKED** | Bloqué par l'absence de client HF. En réalité, un simple découpage 500 chars sans vecteur. |
| F65 | Alice 15 - Analyse vidéo YouTube| `alice_modules.py` | L1025 `analyser_video_youtube`| google.genai | **PARTIALLY_IMPLEMENTED** | Envoie l'URL dans le prompt Gemini sans utiliser d'API de transcription YouTube. |
| F66 | Alice 16 - Suivi productivité | `alice_modules.py` | L1096 `suivi_productivite` | psutil | **BLOCKED** | `psutil` absent du venv. Renvoie systématiquement une erreur. |
| F67 | Alice Status | `alice_modules.py` | L1193 `get_status` | interne | **IMPLEMENTED_AND_VERIFIED** | Retourne le dictionnaire des quotas et statuts des modules. |
| F68 | Script Jarvis CLI | `jarvis_agent.py` | L1-129 | google.genai | **IMPLEMENTED_BUT_BROKEN** | Erreur de syntaxe L77 (`."\n`). Script complètement inutilisable. |

---

## 6. ANALYSE DÉTAILLÉE DU BACKEND CENTRAL MAIN2.PY

Le fichier `main2.py` est un **monolithe de 3 673 lignes** qui centralise de manière disproportionnée les responsabilités d'entrées/sorties réseau, de logique métier, de pilotage système et de gestion de threads.

### 6.1. Serveur WebSocket (Port 8765)
- **Gestion des connexions :** `websockets.serve(ws_handler, "0.0.0.0", 8765)` écoute sur toutes les interfaces réseau sans aucune authentification (aucun token, aucun mot de passe, aucune restriction CORS ou d'origine). Tout appareil sur le réseau local peut s'y connecter.
- **Violation de thread-safety asyncio :** Le serveur WebSocket tourne dans un thread dédié (`asyncio.run(start_ws())`), mais des coroutines tournant sur d'autres boucles d'événements créées à la volée (dans le thread principal `ecouter()`) tentent d'appeler `ws.send()` directement via `send_web_state()` et `send_web_volume()`. Cela viole les garanties de thread-safety de la bibliothèque `websockets` et provoque des comportements imprévisibles sous charge.
- **Simulation trompeuse du volume audio :** La fonction `send_web_volume` n'envoie pas l'amplitude réelle de la voix générée mais une courbe sinusoïdale artificielle calculée mathématiquement (`0.4 + 0.3 * math.sin(t_audio) + ...`).
- **Arrêt violent de ports :** `liberer_port(8765)` exécute `taskkill /F /PID` sur tout processus écoutant sur le port 8765. Si une autre application légitime utilise ce port, elle est éliminée sans avertissement.

### 6.2. Serveur mobile HTTP (Port 8080)
- `SimpleHTTPRequestHandler` sert le dossier `mobile/` sur `0.0.0.0:8080`.
- Il ne dispose d'aucun support HTTPS. En conséquence, les navigateurs modernes (Chrome sur Android, Safari sur iOS) appliquent leur politique de sécurité stricte interdisant l'accès au microphone (`getUserMedia` et Web Speech API) sur les origines non sécurisées.

### 6.3. Moteur de décision et chaîne d'exécution
- La fonction `traiter_reponse_ia` (754 lignes) est un gigantesque bloc d'embranchements `if/elif` traitant 67 actions différentes.
- **Faux succès systématiques :** Les retours de Home Assistant sont ignorés. Si Home Assistant renvoie HTTP 401 Unauthorized ou HTTP 404 Entity Not Found, ALICE affirme : « C'est fait, lumière allumée » ou « Alarme activée ».

---

## 7. AUDIT DU CERVEAU IA HYBRIDE

### 7.1. Google Gemini
- **SDK :** `google.genai` v1.73.1 présent.
- **Clé API :** Détectée, valide et opérationnelle.
- **Modèles configurés :** `MODELS_LIST = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]`. L'appel à l'API confirme la présence de `gemini-2.5-flash`.
- **Comportement :** Stable, streaming textuel fonctionnel, intégration Google Search tool active.

### 7.2. Groq
- **SDK :** `groq` v1.2.0 et `openai` v1.x installés.
- **Clé API :** Clé active et authentifiée avec succès sur l'API Groq.
- **Modèles :** Les modèles demandés par `main2.py` (`qwen3.6-27b`, `qwen-2.5-32b`) **n'existent pas sur Groq**. Le modèle Qwen réel disponible est `qwen/qwen3.8-27b`. En conséquence, chaque tentative d'appel à Groq échoue avec une erreur HTTP 404 (Model Not Found).

### 7.3. xAI Grok
- **SDK :** Utilisé via l'émulation OpenAI.
- **Clé API :** Clé factice dans `.env` (`VOTRE_CLE_ICI`). Le client `grok_client` n'est donc jamais instancié (`grok_client = None`).

### 7.4. Fournisseur local Ollama
- **État :** Ollama n'est pas installé sur le système hôte, n'écoute pas sur le port 11434 (`TcpTestSucceeded: False`), et le module python `ollama` est absent du venv.
- **Conséquence :** L'affirmation d'un mode de secours 100% hors-ligne via LLM local est fausse.

### 7.5. Préprocesseur local
- Les fonctions de secours local (`resoudre_math_localement`, `resoudre_francais_localement`, `resoudre_conversion_localement`, `resoudre_traduction_localement`, `reponse_locale`) interceptent les requêtes avant l'IA.
- **Bug avéré :** `resoudre_math_localement` échoue sur « racine de 25 » en raison d'une regex mal conçue (`r'racine\s+(?:carrée\s+de\s+)?(\d+)'`), générant l'expression invalide `sqrt25`.

---

## 8. AUDIT VOCAL COMPLET

### 8.1. Reconnaissance vocale (STT)
- Le pipeline utilise `SpeechRecognition.recognize_google(audio, language="fr-FR")`.
- **Dépendance Internet absolue :** Ce service est un endpoint web gratuit de Google. En cas de coupure réseau, la fonction lève `RequestError` ou une erreur de socket DNS (`getaddrinfo failed`). Aucune reconnaissance vocale locale (Vosk, Whisper local, etc.) n'est présente dans le flux principal.

### 8.2. Synthèse vocale (TTS)
- Moteur primaire : `edge_tts` avec voix `fr-FR-HenriNeural`. Qualité audio excellente.
- Moteur secondaire : `pyttsx3` pour le mode déconnecté.
- **Défaut de nettoyage des fichiers temporaires :** Chaque synthèse crée un fichier `jarvis_tts_<timestamp>_<random>.mp3` dans le répertoire de travail. À la fin de la lecture, `os.remove(tmp)` est souvent bloqué par le handle encore ouvert de `pygame.mixer`, laissant 57 fichiers MP3 orphelins (7.86 Mo accumulés).

### 8.3. Pipeline parallèle et conflits vocaux
- Le streaming tente de prononcer les phrases au fur et à mesure de leur réception via `tasks.append(asyncio.create_task(parler(sentence)))`.
- Or, dès que la phrase 2 démarre, `is_speaking` étant vrai, elle force `STOP_PARLER = True` (L1820), ce qui provoque l'interruption immédiate de la lecture de la phrase 1 dans `pygame.mixer.music.stop()` (L1874). Les phrases se tronquent mutuellement.

### 8.4. Clap Detection vs Wake Word
- Le système de battement de mains calcule le RMS audio via `audioop.rms` dans un thread en boucle continue.
- Il ne s'agit aucunement d'un modèle d'apprentissage pour Wake Word (tel que Porcupine ou openWakeWord).
- Il partage le même microphone que `SpeechRecognition`, créant des risques de contention sur l'accès au pilote audio Windows.

---

## 9. AUDIT DÉTAILLÉ DES 16 MODULES ALICE (`alice_modules.py`)

| Module | Fonction | Dépendance requise | Présente dans venv | Résultat de l'audit |
|---|---|---|---|---|
| 01. Génération d'images | `generer_image` | `huggingface_hub` | **NON** | **BLOQUÉ** : `hf_client` est `None`. Renvoie erreur immédiate. |
| 02. Transcription audio | `transcrire_audio` | `huggingface_hub` | **NON** | **BLOQUÉ** : `hf_client` est `None`. |
| 03. Suppression de fond | `supprimer_fond` | `huggingface_hub` | **NON** | **BLOQUÉ** : `hf_client` est `None`. |
| 04. Analyse d'humeur audio | `detecter_humeur_audio` | `huggingface_hub` | **NON** | **BLOQUÉ** : `hf_client` est `None`. |
| 05. Synthèse vocale custom | `synthese_vocale_custom` | `huggingface_hub` | **NON** | **BLOQUÉ** : `hf_client` est `None`. |
| 06. Analyse écran contextuelle | `analyser_ecran_contextuel` | `google.genai`, `PIL` | **OUI** | **FONCTIONNEL** : Requête multimodale Gemini opérationnelle. |
| 07. Lecture de photos | `analyser_photo` | `google.genai`, `PIL` | **OUI** | **FONCTIONNEL** : Analyse d'images locales opérationnelle. |
| 08. Vidéosurveillance | `analyser_video_surveillance` | `google.genai`, `pyautogui` | **OUI** | **PARTIEL** : Capture d'écran statique locale uniquement. Pas de vidéo réelle. |
| 09. Assistant de codage | `assistant_codage` | `google.genai` | **OUI** | **FONCTIONNEL** : Collecte les fichiers du projet et interroge Gemini. |
| 10. Agent Web autonome | `agent_web_action` | `webbrowser`, `pyautogui` | **OUI** | **PARTIEL** : Ouvre l'URL et capture l'écran. Pas d'actions itératives réelles. |
| 11. Rédaction d'emails | `rediger_email` | `google.genai` | **OUI** | **FONCTIONNEL** : Génération de texte soignée, enregistrée dans `alice_outputs`. |
| 12. Planificateur d'agenda | `planifier_agenda` | `google.genai` | **OUI** | **FONCTIONNEL** : Analyse heuristique et conseils d'organisation via prompt. |
| 13. Vérification de code en boucle | `verifier_code_boucle` | `subprocess`, `google.genai` | **OUI** | **CRITIQUE (RCE)** : Exécute du code arbitraire non sandboxté. |
| 14. RAG sémantique | `indexer_knowledge_base` | `huggingface_hub` | **NON** | **BLOQUÉ & TROMPEUR** : `hf_client` est `None`. Tente de lire les PDF en UTF-8 brut. Recherche par simples mots-clés. |
| 15. Analyse vidéo YouTube | `analyser_video_youtube` | `google.genai` | **OUI** | **PARTIEL** : Pas d'extraction de sous-titres (`youtube-transcript-api` absente). Dépend de Gemini. |
| 16. Suivi de productivité | `suivi_productivite` | `psutil` | **NON** | **BLOQUÉ** : `psutil` absent du venv. Renvoie systématiquement une erreur. |

---

## 10. AUDIT VISION ET OCR (`vision_ocr.py`)

- **Composants :** `mss` v10.2.0, `cv2` (opencv-python v4.13.0), `pytesseract` v0.3.13, Tesseract OCR v5.5.0 installé sur le système hôte à `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **EasyOCR :** Non installé dans le venv (`easy_reader` reste `None`).
- **Prétraitement d'image :** Binarisation adaptative Otsu, flou gaussien et redimensionnement x2 correctement implémentés.
- **Thread de vision :** `JarvisVision.start()` capture l'écran en boucle non bloquante toutes les 3 secondes et met à jour `last_text`.
- **Vulnérabilité opérationnelle du Clic Aveugle :** Dans `main2.py` (L907-L915), si l'OCR ne trouve pas de coordonnées pour une instruction contenant « whatsapp » ou « appel », le système clique aveuglément aux coordonnées fixes `(screen_width - 150, 100)`. Cela peut déclencher la fermeture inopinée d'une fenêtre ou l'appui sur un bouton arbitraire.

---

## 11. AUDIT DE L'AUTOMATISATION WINDOWS

- **Lancement d'applications :** Dictionnaire très complet d'exécutables (`chrome.exe`, `code.exe`, `discord.exe`, etc.) avec fallbacks sur la commande système `where` et sur la recherche de raccourcis `.lnk` dans le menu Démarrer.
- **Gestion des fichiers :** `trier_par_type` et `trier_par_date` déplacent physiquement les fichiers dans des sous-dossiers. Si la cible courante est configurée sur le Bureau (`Desktop`), les fichiers sont réorganisés sans confirmation préalable.
- **Extinction sauvage du système :** La présence de `"eteins" in cmd` (L1681) déclenche immédiatement `shutdown /s /t 5`.

---

## 12. AUDIT DOMOTIQUE HOME ASSISTANT

- **Configuration :** `HA_URL` et `HA_TOKEN` dans `.env`. Le token présent est un placeholder court (`len=9`).
- **Endpoints :** Les appels utilisent l'API REST `/api/services/{domaine}/{service}` et `/api/states/{entity_id}`.
- **Défaut de couplage rigide :** Les entités configurées dans `PIECES_LUMIERES`, `PIECES_PRISES`, `PIECES_CAPTEURS`, `APPAREILS_BATTERIE` sont entièrement spécifiques à la configuration personnelle de l'auteur original (ex: `sensor.sm_s921b_battery_level`, `sensor.tiktok_followers_techenclair`, `input_select.ramassage_des_oeufs`, `sensor.bob_batterie`).
- **Absence de contrôle des retours :** Les fonctions `ha_lumiere`, `ha_interrupteur`, `ha_thermostat` renvoient un booléen qui n'est **jamais vérifié** par le routeur `traiter_reponse_ia`. ALICE annonce le succès même en cas d'échec total (erreur 401, timeout, entité inexistante).
- **Blocages réseau :** Les requêtes `requests` synchrones dans le flux async bloquent l'application pendant 5 secondes par requête en cas d'indisponibilité du serveur Home Assistant.

---

## 13. AUDIT GOOGLE WORKSPACE ET COMMUNICATION

- **Authentification OAuth :** Utilise `google_auth_oauthlib.flow.InstalledAppFlow` avec fichier local `credentials.json`.
- **Fichier de jeton absent :** `token.pickle` n'existe pas dans le dépôt. Tout appel à Google Docs, Sheets, Gmail ou Calendar déclenche `flow.run_local_server(port=0)`, ouvrant un navigateur et bloquant l'exécution de l'assistant jusqu'à validation manuelle.
- **Duplication de code :** `lister_evenements_calendar` (L799) et `get_google_calendar_events` (L1753) effectuent la même tâche avec des logiques redondantes.
- **WhatsApp :** L'implémentation repose entièrement sur le protocole `start whatsapp://` suivi de simulations de frappes clavier `pyautogui` et de 14 secondes cumulées de `time.sleep()`. Aucun appel vidéo/audio via API officielle.

---

## 14. AUDIT DU FRONTEND DESKTOP (`frontend/`)

- **Technologies :** Vite 6.0, TypeScript 5.7, Three.js 0.170.0.
- **Typage :** La compilation `tsc --noEmit` réussit sans aucune erreur TypeScript.
- **Orbe 3D :** Shader de particules avancé, réactif aux changements d'état (`idle`, `listening`, `thinking`, `speaking`) et au volume audio.
- **Bug de synchronisation du build :** Le dossier `frontend/dist/` contient un artefact de compilation antérieur, ne comportant ni la barre de commande textuelle ni le bouton d'upload de fichier présents dans `frontend/index.html`.
- **Composant orphelin :** `avatar.ts` (modèle 3D alternatif) est compilable mais déconnecté.

---

## 15. AUDIT DE L'INTERFACE MOBILE (`mobile/`)

- **Architecture :** Application Web statique (HTML/CSS/Vanilla JS) servie par le serveur HTTP Python sur le port 8080.
- **Blocage de sécurité navigateur :** Chrome Android et Safari iOS exigent un contexte sécurisé (HTTPS ou localhost) pour autoriser le microphone. En accédant via HTTP sur l'IP locale (ex: `http://192.168.1.XX:8080`), la reconnaissance vocale mobile est **bloquée par défaut**.
- **Contournement bricolé :** L'interface affiche une bannière demandant à l'utilisateur de modifier les drapeaux internes de Chrome (`chrome://flags` -> `Insecure origins treated as secure`), avec une adresse IP codée en dur (`192.168.1.23`) qui ne correspond pas nécessairement à la machine actuelle. Sur iPhone (Safari), ce contournement est impossible.

---

## 16. AUDIT MÉMOIRE ET RAG

### 16.1. Mémoire persistante (`jarvis_memoire.json`)
- Fichier JSON stockant les faits utilisateur.
- **Bug critique de corruption de schéma :** L'action `add_reminder` (L2988) écrit :
  `mem["reminders"].append({"type": type_rem, "task": task, "date": ...})`
  Or, `construire_contexte_memoire` (L424-L425) itère sur chaque élément en supposant qu'il s'agit d'un dictionnaire avec clé `'valeur'` :
  `for cle, data in memoire.items(): lignes.append(f" - {cle} : {data['valeur']} ...")`
  Quand `cle == "reminders"`, `data` est une liste, ce qui déclenche immédiatement :
  `TypeError: list indices must be integers or slices, not str`.
  Ce bogue rend impossible la génération du prompt système et paralyse toutes les requêtes IA ultérieures.

### 16.2. Mécanisme RAG
- Dans `main2.py` : Aucune vectorisation ni recherche sémantique. Les fichiers `.txt` et `.pdf` de `knowledge/` sont lus en bloc et injectés intégralement dans le prompt. Les fichiers Excel (`.xlsx`) sont ignorés.
- Dans `alice_modules.py` : `indexer_knowledge_base` et `recherche_semantique` prétendent utiliser HuggingFace, mais se limitent à découper le texte en morceaux de 500 caractères et effectuent une recherche par comptage de mots-clés. De plus, les PDF sont lus avec `read_text(encoding="utf-8")`, ce qui échoue sur des fichiers binaires.

---

## 17. AUDIT INSTALLATION ET DÉMARRAGE

- **`install.bat` :**
  - Vérifie les droits administrateur, installe les dépendances pip et npm.
  - **Pratique destructrice :** Réécrit directement le code source Python de `main2.py` et `jarvis_agent.py` pour changer le prénom via un script temporaire `temp_rename.py`.
  - N'installe pas les dépendances nécessaires aux modules Alice (`huggingface_hub`, `psutil`, `rembg`, `whisper`, etc.).
- **`DEMARRER_JARVIS.bat` :** Fonctionnel sur la machine locale (`.\venv\Scripts\python.exe main2.py`).
- **`DÉMARRER_JARVIS.bat` :** Défaillant (contient le chemin codé en dur `c:\Users\ASUS TUF\Desktop\MON_JARVIS\.venv-1\Scripts\python.exe`).

---

## 18. AUDIT DE SÉCURITÉ APPROFONDI

| Risque | Vulnérabilité | Vecteur d'attaque | Impact | Niveau | Preuve / Fichier |
|---|---|---|---|---|---|
| SEC-01 | Exécution de code à distance (RCE) | `alice_debug_code` / `verifier_code_boucle` | Exécution arbitraire de scripts non vérifiés avec privilèges utilisateur. | **CRITICAL** | `alice_modules.py` L870 (`subprocess.run(["python", temp_file])`) |
| SEC-02 | Traversée de chemin (Path Traversal) | Upload de fichier WebSocket (`file_upload`) | Écrasement de fichiers système ou de fichiers sources du projet. | **HIGH** | `main2.py` L467 (`os.path.join(temp_dir, filename)`) |
| SEC-03 | Extinction système intempestive | Commande vocale / texte contenant « eteins » | Arrêt forcé de la machine hôte en 5 secondes. | **HIGH** | `main2.py` L1681 (`os.system("shutdown /s /t 5")`) |
| SEC-04 | Fuite de données personnelles | OCR écran injecté dans prompt Gemini | Transmission automatique de données confidentielles aux API cloud tierces. | **HIGH** | `main2.py` L429 & L539 (injection de tout l'écran OCR dans le prompt) |
| SEC-05 | Désérialisation non sécurisée Pickle | `token.pickle` Google OAuth | Risque RCE si le fichier de jeton est altéré. | **MEDIUM** | `main2.py` L711 (`pickle.load(f)`) |
| SEC-06 | Absence d'authentification WebSocket | Port 8765 ouvert sur `0.0.0.0` | Tout hôte du réseau local peut envoyer des commandes, téléverser des fichiers et contrôler le PC. | **HIGH** | `main2.py` L3469 |
| SEC-07 | Tuer de processus arbitraire | `liberer_port` | Tue sans avertissement tout processus écoutant sur 8765. | **MEDIUM** | `main2.py` L3421 (`taskkill /F /PID`) |

---

## 19. RÉSULTATS DES TESTS AUTOMATISÉS

Une suite de tests unitaires et de vérification statique a été exécutée dans un environnement scratch isolé extérieur au projet :

| ID | Test | Type | Résultat attendu | Résultat observé | Statut |
|---|---|---|---|---|---|
| T01 | Importation syntaxique Python | Statique | 0 erreur de syntaxe | Erreur de syntaxe dans `jarvis_agent.py` L77 | **FAIL** |
| T02 | Compilation TypeScript Frontend | Statique | 0 erreur de typage | Compilation `tsc --noEmit` réussie | **PASS** |
| T03 | Vérification des packages Venv | Intégration | Tous les modules installés | 7 packages majeurs manquants (`psutil`, `huggingface_hub`, etc.) | **FAIL** |
| T04 | Disponibilité API Gemini | Réel | Connexion & listing modèles | Clé valide, modèle `gemini-2.5-flash` actif | **PASS** |
| T05 | Disponibilité API Groq | Réel | Modèles `qwen3.6-27b` présents | Clé valide mais modèles configurés inexistants (HTTP 404) | **FAIL** |
| T06 | Détection Service Ollama | Réel | Écoute sur 127.0.0.1:11434 | Port fermé, service non installé | **FAIL** |
| T07 | Tesseract OCR exécutable | Système | Exécutable présent | Tesseract v5.5.0 détecté et opérationnel | **PASS** |
| T08 | Solveur Mathématique Simple | Unitaire | Calcul correct (5 fois 3 = 15) | Retourne 15 | **PASS** |
| T09 | Solveur Mathématique Racine | Unitaire | « racine de 25 » = 5 | Échoue (`NameError: sqrt25`), retourne `None` | **FAIL** |
| T10 | RateLimiter Alice | Unitaire | Bloque après 3 appels | Bloque le 4ème appel et calcule le délai | **PASS** |
| T11 | Conseils de productivité Alice | Unitaire | Conseils gradués selon score | Conseils conformes aux seuils | **PASS** |
| T12 | Détection cerveau Grok/Gemini | Unitaire | Détecte mots-clés Twitter | Détection conforme | **PASS** |
| T13 | Nettoyage de commande | Unitaire | Retire « jarvis » en préfixe | Nettoyage conforme | **PASS** |
| T14 | Test corruption schéma mémoire | Simulé | Détecte l'exception TypeError | `TypeError` confirmé sur `data['valeur']` avec listes | **PASS** |

---

## 20. ANALYSE DE RÉSILIENCE (20 SCÉNARIOS)

1. **Internet coupé :** Reconnaissance vocale HS (Google STT lève une exception réseau). LLMs cloud HS. Ollama non installé. Seules les questions simples du dictionnaire local fonctionnent via texte.
2. **Gemini indisponible :** Bascule vers SerpAPI, puis Groq (qui échoue par mauvais nom de modèle), puis Grok (clé factice), puis Ollama (absent), puis réponse locale. Dégradation lente mais fonctionnelle pour les commandes locales.
3. **Groq indisponible :** Échoue silencieusement et tente le modèle suivant.
4. **Grok indisponible :** `grok_client` est `None`, ignoré proprement.
5. **Ollama arrêté :** Détecté par exception de connexion HTTP, bascule sur le fallback suivant.
6. **Modèle local absent :** Ollama renvoie 404 (non applicable ici car le démon est absent).
7. **Microphone indisponible :** `sr.Microphone()` lève une exception lors de l'initialisation, boucle dans un `sleep(1)`.
8. **Haut-parleurs indisponibles :** `pygame.mixer` lève une exception capturée, bascule vers `pyttsx3`, puis termine silencieusement.
9. **WebSocket interrompu :** Le frontend gère une reconnexion automatique toutes les 2 secondes. Reconnexion propre.
10. **Client mobile déconnecté :** `CONNECTED_CLIENTS.discard(websocket)` nettoie la référence. Aucun crash backend.
11. **Home Assistant indisponible :** Les requêtes `requests` attendent 5 secondes chacune, figeant temporairement le backend, puis ALICE annonce quand même le succès vocalement.
12. **Google API indisponible :** `get_google_creds` bloque sur le serveur local OAuth ou lève une exception gérée.
13. **Tesseract absent :** Géré par un bloc try/except dans `jarvis_vision_cliquer`, mais OCR inopérant.
14. **Fichier PDF corrompu :** `PyPDF2` lève une exception, interceptée dans `extraire_texte_doc`, renvoie chaîne vide sans crash.
15. **JSON mémoire corrompu :** Si `jarvis_memoire.json` est un JSON invalide, `charger_memoire()` renvoie `{}` grâce au `except Exception: return {}`. En revanche, si la structure contient une liste via `add_reminder`, plantage au prompt.
16. **RAM insuffisante :** Aucune gestion active de saturation mémoire.
17. **CPU saturé :** Traitement vocal ralenti, saccades dans l'orbe Three.js.
18. **Erreur de lecture d'un fichier :** Interceptée par `try/except` dans `extraire_texte_doc`.
19. **Réponse IA malformée :** L'extraction regex `\{.*?\}` ignore le texte non-JSON sans planter.
20. **Action Windows refusée :** `subprocess` et `os` interceptent les erreurs et renvoient un message d'échec sans crasher le serveur.

---

## 21. ANALYSE DES PERFORMANCES ET GOULOTS D'ÉTRANGLEMENT

- **Blocage de l'Event Loop :** L'exécution de fonctions synchrones (`requests`, `time.sleep`, `subprocess.check_output`) au sein de l'event loop asyncio principal fige le traitement des messages WebSockets et le rafraîchissement des clients.
- **Accrétion de fichiers MP3 :** L'impossibilité de déverrouiller les fichiers audio avant `os.remove` consomme de l'espace disque et encombre le dossier racine.
- **RAG volumineux :** L'injection intégrale du contenu des documents dans chaque invite système augmente drastiquement la latence réseau des appels Gemini (jusqu'à plusieurs secondes par requête) et risque de saturer les quotas gratuits.

---

## 22. DETTE TECHNIQUE ET ARCHITECTURE

1. **Monolithe surdimensionné :** `main2.py` totalise 3 673 lignes et mélange HTTP, WebSocket, TTS, STT, Domotique, scraping, et sécurité Windows.
2. **Code dupliqué :**
   - `diagnostic_pc` défini aux lignes 1696 et 1790.
   - `update_productivity` défini aux lignes 1781 et 1807.
   - `ajouter_memoire` (L407) et `memory_add` (L1713).
   - `lister_evenements_calendar` (L799) et `get_google_calendar_events` (L1753).
3. **Bibliothèques dépréciées :**
   - `audioop` (supprimé dans Python 3.13).
   - `PyPDF2` (déprécié au profit de `pypdf`).
   - `datetime.utcnow()` (déprécié dans Python 3.12+).
4. **Dépendances inutiles :** `Panda3D`, `ursina`, `sswg` installés mais non utilisés.

---

## 23. BUGS IDENTIFIÉS (SYNTHÈSE DÉTAILLÉE)

| Réf | Gravité | Fichier | Ligne(s) | Description du bug & Conséquence |
|---|---|---|---|---|
| BUG-01 | **CRITIQUE** | `alice_modules.py` | L870 | Exécution de code non filtré via `subprocess.run` (Vecteur RCE). |
| BUG-02 | **CRITIQUE** | `main2.py` | L425 & L2988 | `add_reminder` écrit une liste dans `jarvis_memoire.json`, provoquant un `TypeError` bloquant tout le backend. |
| BUG-03 | **CRITIQUE** | `main2.py` | L1681 | Commande contenant « eteins » déclenchant l'extinction immédiate de l'ordinateur. |
| BUG-04 | **HAUTE** | `main2.py` | L486-493 | Traitement du retour d'écran indenté dans `file_upload`, bloquant toute capture d'écran Web. |
| BUG-05 | **HAUTE** | `main2.py` | L467 | Absence d'assainissement de `filename` dans `file_upload` (Path Traversal). |
| BUG-06 | **HAUTE** | `main2.py` | L1820 & L2526 | Conflit dans le TTS parallèle : la phrase suivante coupe la phrase en cours. |
| BUG-07 | **HAUTE** | `jarvis_agent.py` | L77 | Erreur de syntaxe Python (`."\n`) empêchant toute exécution du script. |
| BUG-08 | **MOYENNE** | `main2.py` | L2428 & L3524 | Noms de modèles Groq inexistants (`qwen3.6-27b`), requêtes en erreur 404. |
| BUG-09 | **MOYENNE** | `main2.py` | L1999 | Regex de `resoudre_math_localement` échouant sur « racine de X ». |
| BUG-10 | **MOYENNE** | `main2.py` | L2448-2463 | 14 secondes de `time.sleep` synchrone dans `action_whatsapp_appel` figeant le serveur. |
| BUG-11 | **MOYENNE** | `main2.py` | L2664-2845 | Retour HTTP des actions Home Assistant ignoré, succès annoncé vocalement à tort. |
| BUG-12 | **MOYENNE** | `main2.py` | L911 | Clic visuel aveugle aux coordonnées `(width - 150, 100)`. |
| BUG-13 | **MOYENNE** | `main2.py` | L1409 | Saison sportive codée en dur à `2024-2025`. |
| BUG-14 | **BASSE** | `main2.py` | L1928-1930 | Fichiers temporaires MP3 non nettoyés sur Windows (57 fichiers orphelins). |
| BUG-15 | **BASSE** | `frontend/dist` | - | Build frontend obsolète non synchronisé avec le code source de `index.html`. |

---

## 24. FONCTIONNALITÉS INCOMPLÈTES
- **RAG (`main2.py` et `alice_modules.py`) :** Aucune indexation vectorielle réelle. Concaténation de chaînes brutes ou comptage basique de mots-clés. Fichiers Excel ignorés.
- **Vidéosurveillance Alice :** Ne lit aucun flux RTSP de caméra IP ; prend une capture statique du bureau Windows.
- **Agent Web Alice :** Ouvre une page Web et s'arrête après un screenshot ; ne réalise pas de parcours de navigation multi-étapes.

---

## 25. FONCTIONNALITÉS DÉCONNECTÉES
- **`frontend/src/avatar.ts` :** Modèle 3D complet jamais affiché ni connecté.
- **`jarvis_agent.py` :** Script autonome jamais invoqué par l'application principale.
- **Rappels GPS (`add_reminder`) :** Enregistrés dans la mémoire mais jamais relus, planifiés ni déclenchés.
- **Double fonction `diagnostic_pc` et `update_productivity` :** Secondes déclarations écrasant les premières.

---

## 26. FONCTIONNALITÉS NON TESTABLES EN ENVIRONNEMENT ACTUEL
- **Google Workspace (Docs, Sheets, Gmail, Calendar) :** Bloqué par l'absence d'authentification interactive initiale (`token.pickle` manquant).
- **Home Assistant :** Bloqué par un token placeholder et une URL de réseau local privé spécifique (`192.168.1.XX`).
- **xAI Grok :** Bloqué par l'absence de clé API valide dans `.env`.
- **Microphone mobile :** Bloqué sur les appareils réels par l'absence de protocole HTTPS sur le serveur port 8080.

---

## 27. PRIORISATION DES PROBLÈMES (TOP 20)

1. **[P0 - SÉCURITÉ]** Neutraliser ou sécuriser l'exécution de code arbitraire dans `verifier_code_boucle`.
2. **[P0 - STABILITÉ]** Corriger le bug de corruption de structure dans `add_reminder` / `construire_contexte_memoire`.
3. **[P0 - SÉCURITÉ]** Sécuriser la commande d'extinction PC pour exiger une confirmation explicite et exclure les faux positifs vocaux.
4. **[P0 - SÉCURITÉ]** Assainir le nom de fichier dans l'upload WebSocket (`os.path.basename`) contre les attaques Path Traversal.
5. **[P0 - FONCTIONNEL]** Corriger l'indentation de `screen_frame` dans `ws_handler` pour rétablir la capture d'écran frontend.
6. **[P0 - PACKAGING]** Installer les dépendances manquantes dans le venv (`huggingface_hub`, `psutil`, `pypdf`, `openpyxl`).
7. **[P1 - IA]** Mettre à jour les identifiants de modèles Groq vers les modèles actuellement en production (`qwen/qwen3.8-27b`).
8. **[P1 - PERFORMANCE]** Remplacer tous les `time.sleep` par `await asyncio.sleep` et envelopper les appels `requests` dans `asyncio.to_thread`.
9. **[P1 - AUDIO]** Corriger la gestion de `STOP_PARLER` dans le pipeline TTS parallèle pour éviter le hachage des phrases.
10. **[P1 - AUDIO]** Implémenter un nettoyage différé ou un gestionnaire de contexte robuste pour la suppression des fichiers temporaires MP3.
11. **[P1 - DOMOTIQUE]** Conditionner les messages vocaux de confirmation au code de retour effectif des appels API Home Assistant.
12. **[P1 - SÉCURITÉ]** Ajouter une authentification par jeton sur la connexion WebSocket (`ws://0.0.0.0:8765`).
13. **[P1 - MOBILE]** Configurer le serveur mobile HTTP avec un certificat SSL auto-signé pour débloquer l'accès micro sur mobile.
14. **[P2 - QUALITÉ]** Corriger la syntaxe de `jarvis_agent.py` ligne 77.
15. **[P2 - QUALITÉ]** Éliminer les fonctions dupliquées (`diagnostic_pc`, `update_productivity`, `memory_add`, etc.).
16. **[P2 - RAG]** Remplacer la concaténation brute du RAG par une bibliothèque vectorielle locale légère (ex: ChromaDB ou SQLite-vec).
17. **[P2 - OCR]** Supprimer la logique de « clic aveugle » aux coordonnées fixes dans `jarvis_vision_cliquer`.
18. **[P2 - FRONTEND]** Reconstruire le bundle `frontend/dist/` (`npm run build`) pour refléter les fonctionnalités récentes.
19. **[P2 - ARCHITECTURE]** Modulariser `main2.py` en séparant les routeurs domotique, IA, système et réseau.
20. **[P2 - SCRIPTS]** Corriger le chemin codé en dur dans `DÉMARRER_JARVIS.bat`.

---

## 28. PLAN DE REMÉDIATION RECOMMANDÉ

Le projet ne doit en aucun cas faire l'objet de nouvelles fonctionnalités tant que les fondations techniques ne sont pas assainies.

### Phase 1 : Stabilisation Critique & Sécurité (P0)
- Corriger le bug mémoire `add_reminder` et `construire_contexte_memoire`.
- Corriger l'indentation de capture d'écran dans `ws_handler`.
- Supprimer l'extinction sauvage sans confirmation.
- Assainir le chemin d'upload de fichiers.
- Installer les dépendances manquantes dans le `venv` et mettre à jour `requirements.txt`.

### Phase 2 : Fiabilité Opérationnelle & Performance (P1)
- Convertir les opérations bloquantes de `main2.py` en opérations asynchrones non bloquantes (`asyncio.to_thread`).
- Corriger le flux audio parallèle pour empêcher l'interruption prématurée des phrases.
- Vérifier les codes de retour HTTP sur Home Assistant avant d'émettre une confirmation vocale.
- Rectifier les identifiants de modèles Groq.

### Phase 3 : Modularisation & Refonte Architecturale (P2)
- Découper `main2.py` en modules spécialisés : `network/websocket_server.py`, `core/router.py`, `integrations/home_assistant.py`, `services/tts_service.py`.
- Adopter une véritable base vectorielle locale pour le RAG.
- Remplacer Google STT par une solution de reconnaissance vocale locale optionnelle (ex: Faster-Whisper) pour rendre l'affirmation « 100% hors-ligne » réelle.

---

## 29. CONCLUSION ET NIVEAU DE MATURITÉ RÉEL DU PROJET

### Évaluation du niveau de maturité : **NIVEAU 1.5 / 5**
- **Niveau 0 : Concept uniquement.**
- **Niveau 1 : Code partiellement présent.**
- **Niveau 2 : Fonctionnalités implémentées mais insuffisamment testées.**
- **Niveau 3 : Fonctionnement validé en tests isolés.**
- **Niveau 4 : Intégration complète et validée en environnement représentatif.**
- **Niveau 5 : Système robuste, sécurisé, observable et couvert par des tests.**

Le projet possède des interfaces visuelles soignées (l'orbe Three.js Desktop est impressionnante et bien conçue) et une intégration Gemini 2.5 fonctionnelle. Cependant, en raison du monolithe fragile, des dépendances manquantes paralysant près de la moitié des modules d'Alice, de bugs critiques bloquants (mémoire, capture d'écran, extinction intempestive), de failles de sécurité majeures et de l'absence totale de tests automatisés, **le projet ne dépasse pas le Niveau 1.5**.

**Recommandation formelle :** **NÉCESSITE UNE REFONTE CIBLÉE ET DES CORRECTIONS PRÉALABLES INDISPENSABLES AVANT TOUTE ÉVOLUTION FONCTIONNELLE.**
