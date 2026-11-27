# 🏗️ ALICE — ARCHITECTURE CIBLE & CONTRATS DE CONCEPTION (MISSION 008)

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  

---

## 1. PRINCIPES ARCHITECTURAUX FONDAMENTAUX

1. **Unification autour d'un noyau modulaire `alice_core/` :** Les 30 fonctionnalités s'organisent dans 6 couches métier partageant les mêmes mécanismes de sécurité (`RBAC`, `FeatureFlags`, `AuditLogger`, `CommandLifecycleManager`).
2. **Aucun effet de bord à l'import (`import main2` sûr) :** Aucune tâche asynchrone, thread système, écoute micro ou capture RTSP n'est démarrée lors du chargement des modules ; le démarrage explicite s'opère via `start_ia()` ou des méthodes `.start()` contrôlées.
3. **Orchestrateur unique (9 états) :** Tous les traitements longs (`Jobs`), délégations (`Agent Swarm`), actions IoT et confirmations transitent par `ORCHESTRATOR` (`alice_orchestrator.py`) pour préserver l'idempotence et les preuves d'exécution P0/P1.
4. **Dégradation gracieuse systématique (`Fail-Closed` sécurité, `Fail-Safe` confort) :**
   - Si un module sécuritaire manque ou échoue (`RBAC`, `Vault`), accès refusé.
   - Si un fournisseur matériel ou cloud est indisponible (`HA`, `Tesseract`, `Gemini`, `ONNX`, `RTSP`), bascule explicite vers l'alternative locale ou retour d'un statut `UNKNOWN` / `UNAVAILABLE` sans jamais simuler un succès.
5. **Conformité P0/P1 stricte sur le Frontend Mobile :**
   - Zéro `.innerHTML`, `.outerHTML`, `document.write`, `eval()`.
   - Zéro jeton stocké dans `localStorage`.
   - En-têtes CSP, HSTS, `X-Frame-Options: DENY` et cookies `HttpOnly` conservés intacts dans `MobileHandler`.

---

## 2. ARCHITECTURE LOGIQUE DES COUCHES (`alice_core/`)

```
Jarvis Final - SITE/alice_core/
├── feature_flags.py               # Registry centralisé (opt-in sécuritaire par défaut)
├── security/
│   ├── rbac.py                    # OWNER, ADMIN, MEMBER, GUEST, SERVICE_AGENT + audit
│   ├── vault.py                   # Coffre AES-256-GCM + dérivation PBKDF2/Scrypt + auto-lock
│   └── audit.py                   # Journal d'audit inviolable & rédaction de secrets
├── ops/
│   └── observability.py           # Télémétrie Win32/POSIX sans psutil, latences p50/p95, santé services
├── voice/
│   ├── pipeline.py                # Automate audio 6 états + Barge-In async + anti-écho
│   ├── whisper_mode.py            # Détecteur acoustique murmure vs volume faible + profil nuit
│   ├── followup.py                # Fenêtre Follow-Up Listen (5s configurable) + annulation
│   ├── voice_id.py                # Embeddings locaux NumPy chiffrés, consentement, anti-rejeu
│   └── acoustic_context.py        # Contexte prosodique probabiliste + adaptation prompt/TTS
├── memory/
│   ├── knowledge_graph.py         # Graphe relationnel typé, provenance, confiance, isolation user
│   ├── watchdog.py                # Hot-folder watchdog (PDF/XLSX/DOCX/MD/EPUB), hash, queue
│   ├── briefing.py                # Executive Briefing (Extrait / Interprété / Recommandé / Manquant)
│   └── commitments.py             # Tracker d'engagements (5 états) + filtre citations/hypothèses
├── iot/
│   ├── routines.py                # Détection d'habitudes HA + gestion consentement utilisateur
│   ├── eco_manager.py             # Mesures conso, tarifs, seuils, délestage protégé
│   ├── self_healing.py            # Diagnostic flotte (batterie, latence, offline) + retry borné
│   ├── presence.py                # Simulation absence réaliste + verrou alarme/serrures/caméras
│   └── thermal.py                 # Confort thermique avec hystérésis et protection antigel
├── vision/
│   ├── analyzer.py                # Pipeline mobile Capture -> Preview -> Confirm -> Rétention
│   ├── ocr_receipts.py            # Tesseract 5.5 + OpenCV + vérif HT/TVA/TTC + export XLSX natif
│   ├── video_sentinel.py          # Détecteur OpenCV HOG/MOG2 temporel/météo + garde RTSP
│   ├── visual_memory.py           # Index événements visuels horodatés + politique de purge
│   └── safety_zones.py            # Zones polygonales + validation temporelle + avertissement légal
├── automation/
│   ├── daily_briefing.py          # Briefings matin/soir + filtre confidentialité mode invité
│   ├── agent_swarm.py             # Délégation bornée (profondeur, tokens, temps, appels, RBAC)
│   ├── web_agent.py               # Suivi Web sur WebGuard (redirections, taille, anti-CAPTCHA)
│   ├── jobs.py                    # File persistante SQLite/JSON + retries + push post-confirmation
│   └── webhooks.py                # Passerelle HMAC-SHA256 temps constant + anti-rejeu nonce/TTL
└── mobile_sync/
    └── offline_sync.py            # Synchronisation idempotente + résolution conflits + Quick Actions
```

---

## 3. CONTRAT DE FEATURE FLAGS SÉCURITAIRES (`feature_flags.py`)

Toutes les fonctionnalités sensibles ou proactives disposent d'un drapeau contrôlé exclusivement côté backend (indépendant du frontend) :

| Flag | Défaut | Justification Sécurité |
| :--- | :---: | :--- |
| `barge_in_enabled` | `True` | Amélioration UX vocale non invasive |
| `whisper_mode_enabled` | `True` | Profil acoustique passif sans stockage biométrique |
| `followup_listen_enabled` | `True` | Fenêtre limitée (5s) et annulable, indicateur visible |
| `emotion_context` | `False` | Traitement acoustique désactivable & opt-in (privacité) |
| `voice_biometrics` | `False` | Données biométriques sensibles — consentement explicite requis |
| `predictive_automation` | `False` | Aucune automatisation domotique proactive sans consentement |
| `video_monitoring` | `False` | Flux caméras RTSP désactivés par défaut |
| `visual_memory` | `False` | Rétention d'observations visuelles opt-in |
| `agent_swarm` | `True` | Borné strictement par budgets et permissions RBAC |
| `web_automation` | `False` | Navigation autonome encadrée par `WEB_GUARD` |
| `offline_sync` | `True` | Uniquement pour notes/tâches non confidentielles |
| `encrypted_vault` | `False` | Requiert initialisation mot de passe maître / dérivation clé |
| `webhook_connector` | `False` | Endpoints externes désactivés jusqu'à configuration HMAC |

---

## 4. SCHÉMA DE SÉCURITÉ RBAC ET PROTECTION DES DONNÉES

### 4.1 Hiérarchie des Rôles (`alice_core/security/rbac.py`)
1. `OWNER` (niveau 100) : Tous droits, déverrouillage coffre-fort après vérification secondaire, gestion RBAC, armement/désarmement alarme.
2. `ADMIN` (niveau 80) : Administration observabilité, connecteurs, configuration système (sans lecture coffre-fort personnel du Owner par défaut).
3. `MEMBER` (niveau 50) : Commandes domotiques courantes, RAG personnel, notes, agenda délégué.
4. `GUEST` (niveau 10) : Lumières non critiques autorisées, conversation générale, météo ; **blocage strict** sur arrêt PC, lecture emails, désarmement alarme, coffre-fort, fichiers système et webhooks.
5. `SERVICE_AGENT` (niveau 30) : Accès restreint aux tâches déléguées d'un job ou agent, incapable d'élever ses privilèges ou de lire les secrets.

### 4.2 Frontière d'Isolation du Coffre-Fort (`alice_core/security/vault.py`)
- Chiffrement authentifié **AES-256-GCM** avec nonce aléatoire unique de 96 bits (`os.urandom(12)`) par opération et données associées (AAD : `vault_id|version|item_id`).
- Dérivation de clé par **Scrypt** (`cryptography.hazmat.primitives.kdf.scrypt.Scrypt` — résistant aux ASICs) avec sel aléatoire de 16 octets (jamais un hash nu de mot de passe).
- **Exclusion formelle :** Le répertoire et le fichier chiffré du coffre-fort ne sont jamais indexés par `RAG_ENGINE`, jamais transmis au contexte LLM, et jamais journalisés.
