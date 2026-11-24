# CHANGELOG — SÉCURISATION ET REMÉDIATION P0

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence :** ALICE-REMEDIATION-P0-001  
**Date :** 22 Novembre 2026  
**Type d'intervention :** Durcissement de sécurité (Hotfix P0)  

---

## 1. FICHIERS MODIFIÉS

### 1.1. `Jarvis Final - SITE/alice_modules.py`
- **Imports :**
  - Ajout de `import ast` pour l'analyse statique du code Python.
- **Méthode modifiée :**
  - `verifier_code_boucle(self, code: str, langage: str = "python", max_iterations: int = 3) -> dict`
- **Changements apportés :**
  - **Neutralisation de l'exécution arbitraire :** suppression complète de `subprocess.run`, des fichiers exécutables temporaires et des invocations directes de `python` ou `node`.
  - **Analyse statique AST :** vérification de la syntaxe Python sans exécution.
  - **Inspection de sécurité :** détection des modules interdits (`os`, `sys`, `subprocess`, `shutil`, `socket`, `pty`, `commands`, `winreg`) et des builtins dangereux (`eval`, `exec`, `__import__`, `compile`, `breakpoint`).
  - **Auto-correction sécurisée :** en cas d'erreur ou d'insécurité, l'IA génère une correction statique sans exécution sur l'hôte.
  - **Attributs de réponse :** ajout de `execution_status: "DISABLED_FOR_SECURITY"` et `safety_status: "SECURE_STATIC_VERIFIED"`.

---

### 1.2. `Jarvis Final - SITE/main2.py`
- **Imports :**
  - Ajout de `import secrets`, `import hmac`, `from urllib.parse import urlparse, parse_qs`.
  - Ajout de `from typing import Optional, List, Dict, Any, Union`.

- **Composant Mémoire (`SEC-06`) :**
  - Ajout de `MEMOIRE_LOCK = threading.RLock()`.
  - `charger_memoire()` : lecture thread-safe avec gestion des corruptions JSON.
  - `sauvegarder_memoire(memoire)` : écriture atomique sur fichier temporaire avec `os.fsync` et remplacement atomique `os.replace`.
  - `construire_contexte_memoire()` : refonte complète pour supporter les structures hétérogènes (`reminders` en liste, faits en dict, scalaires) sans provoquer de `TypeError`.

- **Composant WebSocket & Upload (`SEC-04` & `SEC-02`) :**
  - Création de la classe `WSSessionManager` :
    - Génération de token aléatoire sécurisé via `secrets.token_urlsafe(32)`.
    - Vérification à temps constant via `hmac.compare_digest`.
    - Gestion de l'expiration (TTL 24h), de la rotation et de la révocation.
    - Persistance locale dans `temp_uploads/.ws_session_token`.
    - Méthode `is_origin_allowed()` validant les origines locales et LAN privées.
  - Refonte de `ws_handler(websocket)` :
    - Limitation des connexions simultanées à 10 (`code=4008`).
    - Contrôle d'origine (`Origin` header, rejet `code=4003`).
    - Authentification obligatoire sous 5s pour les clients distants LAN (`code=4001`).
    - Limitation de débit applicatif à 30 messages/seconde par client.
    - Sécurisation des téléversements (`file_upload`) : extraction `os.path.basename`, whitelist stricte d'extensions, stockage imprévisible sous UUID v4, vérification canonique `os.path.realpath`, limite de taille (15 Mo b64 / 10 Mo décodé).
    - **Correction Bug Vision :** désindentation du traitement `screen_frame` pour permettre la capture d'écran sans dépendance à l'upload.

- **Composant Contrôleur d'Actions Système (`SEC-03`) :**
  - Création de la classe `SystemActionController` :
    - Dépistage et exclusion des commandes domotiques (lumières, prises, TV, etc.).
    - Filtrage des négations et interrogations réflexives.
    - Détection stricte d'intention d'arrêt ou redémarrage du PC.
    - Protocole de confirmation à 2 facteurs avec expiration après 30 secondes.
    - Journal d'audit de sécurité dans `alice_outputs/security_audit.log`.
    - Support du mode de simulation `JARVIS_DRY_RUN_SYSTEM_COMMANDS=1`.
  - Dans `executer_action_pc(commande)` :
    - Remplacement de la condition vulnérable `if "eteins" in cmd or "shutdown" in cmd:` par l'appel à `SYSTEM_ACTION_CONTROLLER.process_command(cmd)`.

- **Composant Domotique Home Assistant (`SEC-05`) :**
  - Dans `traiter_reponse_ia` :
    - Pour `ha_lumiere`, `ha_prise`, `ha_thermostat`, `ha_scene`, `ha_alarme`, `ha_simulation` : vérification stricte du booléen de succès renvoyé par l'API.
    - Émission d'un message d'erreur explicite et véridique à l'utilisateur en cas d'échec ou d'indisponibilité de Home Assistant.

- **Serveur HTTP Mobile :**
  - Dans `start_mobile_http_server` :
    - Ajout de l'endpoint HTTP `/api/auth/token` pour permettre à l'interface mobile locale de récupérer le jeton de session WebSocket.

---

## 2. ANALYSE DE RÉTROCOMPATIBILITÉ

| Composant Client | Impact Constaté | Action Requise |
| :--- | :--- | :--- |
| **Frontend Three.js (`frontend/`)** | **Aucun impact négatif.** La connexion sur `ws://localhost:8765` est reconnue comme boucle locale (loopback) et auto-authentifiée. La compilation TypeScript est 100% propre (`tsc --noEmit` OK). | Aucune |
| **Interface Mobile (`mobile/`)** | **Rétrocompatible.** Le serveur HTTP sur le port 8080 délivre le jeton via `/api/auth/token`. | Aucune |
| **Modules ALICE (`alice_modules.py`)** | **Sécurisé.** Les modules fonctionnent sans altération ; seule l'exécution de code arbitraire sur l'hôte est assainie en vérification statique. | Aucune |
| **Mémoire Persistante (`jarvis_memoire.json`)** | **Stabilité accrue.** Le fichier n'est plus sujet aux corruptions lors d'accès concurrents et les rappels ne bloquent plus la génération du contexte. | Aucune |

---

## 3. ENGAGEMENTS ET DIRECTIVES RESPECTÉS

- `git commit` : **NON EXÉCUTÉ**
- `git push` : **NON EXÉCUTÉ**
- Déploiement : **NON EXÉCUTÉ**
- Fichiers `.env` et clés d'API : **INTACTS ET NON EXPOSÉS**
- Sauvegarde pré-remédiation : **DISPONIBLE ET VÉRIFIÉE HORS DU PROJET**
