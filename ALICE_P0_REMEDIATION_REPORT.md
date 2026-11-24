# MISSION ALICE-REMEDIATION-P0-001
## RAPPORT D'EXÉCUTION — NEUTRALISATION DES VULNÉRABILITÉS CRITIQUES P0 ET DURCISSEMENT SYSTÈME

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 22 Novembre 2026  
**Référence d'audit :** ALICE-FORENSIC-AUDIT-001  
**Statut :** RÉUSSI (100% DES VULNÉRABILITÉS P0 NEUTRALISÉES ET VALIDÉES)  
**Mode d'intervention :** STRICT SÉCURITÉ — READ/WRITE CONTRÔLÉ SANS DÉPLOIEMENT NI COMMIT  
**Intervenant :** Senior Software Architect, Principal Security & DevSecOps Engineer  

---

## 1. SYNTHÈSE MANAGÉRIALE & ANALYSE DE POSTURE

À la suite du rapport d'audit contradictoire `ALICE-FORENSIC-AUDIT-001`, la mission prioritaire `ALICE-REMEDIATION-P0-001` a été déclenchée pour neutraliser l'intégralité des vecteurs de compromission critique (P0) identifiés dans le système J.A.R.V.I.S / ALICE.

Avant cette remédiation, le système exposait la machine hôte Windows et l'infrastructure locale à des risques inacceptables :
1. **Exécution de code arbitraire (RCE)** sur l'OS hôte via la boucle d'auto-debug Python/Node sans aucun cloisonnement ni sandbox.
2. **Traversée de répertoires (Path Traversal)** et téléversement non filtré via le canal WebSocket permettant l'écriture arbitraire sur le système de fichiers.
3. **Extinction intempestive du PC hôte Windows** déclenchée sur de simples sous-chaînes de texte (ex. « éteins la lumière »), sans confirmation ni journalisation.
4. **Exposition non authentifiée du serveur WebSocket** sur `0.0.0.0:8765`, vulnérable au détournement distant et aux attaques Cross-Site WebSocket Hijacking (CSWSH).
5. **Confirmations vocales mensongères** lors des interactions domotiques Home Assistant en ignorant les codes d'erreur réseau et API.
6. **Corruption fatale de la mémoire persistante** due à l'absence de synchronisation multi-thread et à l'incompatibilité de type sur la structure des rappels.

### Résultats de la mission :
- **6 frontières de sécurité durcies** avec succès dans le code source (`alice_modules.py` et `main2.py`).
- **25 tests de sécurité automatisés exécutés** avec un taux de réussite de **100.0% (25/25 PASS)**.
- **Sauvegarde intégrale pré-remédiation conservée** hors du projet (`brain/backups/pre_remediation_p0`).
- **Aucune dépendance externe altérée**, aucun fichier d'environnement compromis, aucun commit Git déclenché.
- **Rétrocompatibilité préservée** avec les interfaces existantes (Frontend Three.js et Mobile).

---

## 2. DÉTAIL DES VULNÉRABILITÉS TRAITÉES & REMÉDIATIONS TECHNIQUES

### 2.1. SEC-01 — Neutralisation de l'Exécution Python Arbitraire sur l'Hôte

#### Contexte et Vulnérabilité
Dans `Jarvis Final - SITE/alice_modules.py`, la méthode `verifier_code_boucle` générait un script temporaire sur disque et exécutait directement `subprocess.run(["python", temp_file])` ou `["node", temp_file]` avec les privilèges complets de l'utilisateur Windows. Tout code généré par l'IA ou injecté par un utilisateur pouvait effacer des données, exfiltrer des variables d'environnement ou compromettre le poste de travail.

#### Solution Implémentée
- **Suppression intégrale de l'exécution dynamique sur l'OS hôte** (`subprocess.run` éliminé).
- **Implémentation d'une analyse statique AST (Abstract Syntax Tree)** pour Python :
  - Parsing syntaxique strict sans exécution.
  - Inspection AST des modules dangereux interdits : `os`, `sys`, `subprocess`, `shutil`, `socket`, `pty`, `commands`, `winreg`.
  - Détection des builtins d'exécution dynamique : `eval`, `exec`, `__import__`, `compile`, `breakpoint`.
- **Contrôles statiques pour JavaScript** (détection de patterns critiques : `child_process`, `eval`, `fs`).
- **Mode d'auto-correction statique sécurisé** : en cas d'erreur de syntaxe ou de détection de pattern dangereux, l'IA Gemini est sollicitée pour assainir et corriger le code statiquement sans JAMAIS le lancer sur le système hôte.
- **Statut d'exécution explicite** : `execution_status = "DISABLED_FOR_SECURITY"`, `safety_status = "SECURE_STATIC_VERIFIED"`.

```python
# Extrait de la remédiation SEC-01 dans alice_modules.py :
tree = ast.parse(code_actuel)
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name.split('.')[0] in DANGEROUS_MODULES:
                dangers_iteration.append(f"Import interdit détecté : {alias.name}")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
            dangers_iteration.append(f"Appel interdit à builtin dangereux : {node.func.id}()")
```

---

### 2.2. SEC-02 — Protection des Téléversements et Neutralisation du Path Traversal

#### Contexte et Vulnérabilité
Dans `Jarvis Final - SITE/main2.py`, le gestionnaire de messages WebSocket `file_upload` utilisait directement le nom fourni par le client (`os.path.join(temp_dir, filename)`). Un attaquant pouvait injecter `../../` ou des chemins absolus Windows (`C:\...`) pour écraser des fichiers système ou exécutables. De plus, la réception des frames vidéo pour la vision (`screen_frame`) était accidentellement indentée dans le bloc `file_upload`, bloquant les captures d'écran.

#### Solution Implémentée
- **Neutralisation de Path Traversal :**
  - Extraction stricte du nom de base via `os.path.basename(raw_filename.replace("\\", "/"))`.
  - Assainissement regex du nom (`re.sub(r'[^a-zA-Z0-9_\.-]', '_', base)`).
  - Préfixage imprévisible par UUID v4 : `f"{uuid.uuid4().hex}_{safe_filename}"`.
  - Vérification canonique absolue via `os.path.realpath` : rejet si le chemin résolu ne réside pas strictement dans le sous-dossier autorisé `temp_uploads/`.
- **Contrôle strict des extensions :**
  - Whitelist stricte : `.txt`, `.pdf`, `.md`, `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.csv`, `.log`, `.png`, `.jpg`, `.jpeg`, `.docx`, `.xlsx`.
  - Blacklist immédiate de tout exécutable ou script système : `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.sh`, `.dll`, `.com`, `.scr`, `.msi`, `.jar`, `.reg`.
- **Limitation de taille (Anti-DoS) :**
  - Plafond de charge utile base64 : 15 Mo.
  - Plafond de fichier décompressé en mémoire : 10 Mo.
- **Correction architecturale de la Vision :**
  - Désindentation de la branche `screen_frame` pour la traiter de façon autonome au niveau de la boucle de messages principale, résolvant immédiatement le blocage des captures d'écran.

---

### 2.3. SEC-03 — Contrôleur d'Actions Système Sécurisées (Arrêt / Redémarrage PC)

#### Contexte et Vulnérabilité
Dans `Jarvis Final - SITE/main2.py`, la condition `if "eteins" in cmd or "shutdown" in cmd:` déclenchait immédiatement `os.system("shutdown /s /t 5")`. Une simple commande comme « Jarvis, éteins la lumière du salon » ou « Je ne veux pas éteindre » éteignait l'ordinateur de l'utilisateur en 5 secondes.

#### Solution Implémentée
- **Suppression du déclenchement naïf par sous-chaîne.**
- **Création de la classe `SystemActionController` :**
  - **Désambiguïsation domotique :** détection des mots-clés liés à la maison (`lumière`, `lampe`, `prise`, `télévision`, `tv`, `salon`, `chambre`, `clim`, `chauffage`, `volet`, `alarme`). Si détecté, la commande est transmise intacte au routeur Home Assistant.
  - **Filtrage des négations et interrogations :** détection des motifs tels que « ne veux pas », « pas éteindre », « pourquoi éteindre », évitant tout faux positif.
  - **Détection stricte d'intention PC :** regex explicite `\b(?:éteins|arrête|stop)\s+(?:le\s+|l\'|mon\s+)?(?:pc|ordinateur|ordi|windows)\b`.
  - **Protocole de confirmation à deux facteurs avec TTL de 30 secondes :**
    1. Demande d'extinction reçue -> Mise en attente (`pending_action`), génération d'un jeton aléatoire, réponse vocale demandant explicitement : *« Êtes-vous certain de vouloir éteindre votre ordinateur ? Dites 'confirmer l'extinction' dans les 30 secondes pour valider, ou 'annuler'. »*
    2. Confirmation reçue -> Vérification de non-expiration (TTL 30s) et de non-ambiguïté.
    3. Annulation -> Effacement immédiat de l'action en attente.
  - **Support du mode DRY-RUN :** activation via `JARVIS_DRY_RUN_SYSTEM_COMMANDS=1` pour les tests sans perturbation de la machine hôte.
  - **Journalisation d'audit de sécurité :** consignation horodatée de toutes les demandes, confirmations, expirations et annulations dans `alice_outputs/security_audit.log`.

---

### 2.4. SEC-04 — Durcissement du Serveur WebSocket (Port 8765)

#### Contexte et Vulnérabilité
Le serveur WebSocket écoutait sur `0.0.0.0:8765` sans aucune authentification, sans vérification de l'origine (Origin header), sans limitation du nombre de connexions ni limitation de débit de messages. N'importe quel équipement sur le LAN (ou une page web malveillante ouverte dans le navigateur via CSWSH) pouvait envoyer des commandes arbitraires à ALICE.

#### Solution Implémentée
- **Gestionnaire cryptographique `WSSessionManager` :**
  - Jeton de session aléatoire de haute entropie généré via `secrets.token_urlsafe(32)`.
  - Validation à temps constant via `hmac.compare_digest` (protection anti-timing attack).
  - Mécanismes intégrés d'expiration (24h), de rotation et de révocation.
  - Persistance locale du jeton dans `temp_uploads/.ws_session_token`.
- **Politique d'accès par origine et réseau :**
  - Connexions de bouclage local (`127.0.0.1`, `::1`, `localhost`) autorisées directement pour l'interface de bureau.
  - Connexions distantes (LAN / mobile) : obligation de fournir un jeton valide dans les 5 secondes via une poignée de main `{"type": "auth", "token": "..."}`, faute de quoi la connexion est fermée avec code `4001 Unauthorized`.
  - Filtrage d'origine : validation des origines autorisées (`localhost`, `127.0.0.1`, sous-réseaux privés LAN RFC1918) ; rejet immédiat des origines suspectes avec code `4003 Forbidden Origin`.
- **Protection anti-déni de service (Anti-DoS) :**
  - Plafond strict de 10 connexions simultanées (rejet avec code `4008 Policy Violation`).
  - Limitation de débit applicatif par client (max 30 messages/seconde).
  - Taille maximale de trame configurée à 15 Mo dans `websockets.serve(..., max_size=15*1024*1024)`.
- **Distribution sécurisée du jeton :**
  - Endpoint HTTP local dédié `/api/auth/token` sur le serveur mobile (port 8080) permettant aux clients légitimes de récupérer le jeton sans configuration manuelle.

---

### 2.5. SEC-05 — Élimination des Confirmations Vocales Mensongères

#### Contexte et Vulnérabilité
Dans `Jarvis Final - SITE/main2.py` (`traiter_reponse_ia`), les actions domotiques Home Assistant (`ha_lumiere`, `ha_prise`, `ha_thermostat`, `ha_scene`, `ha_alarme`, `ha_simulation`) appelaient l'API mais ignoraient totalement la valeur de retour booléenne. ALICE annonçait systématiquement un succès vocal (« J'éteins le salon », « Alarme activée ») même si Home Assistant était hors ligne, injoignable ou renvoyait une erreur HTTP 500.

#### Solution Implémentée
- Vérification systématique du booléen de succès renvoyé par chaque méthode Home Assistant.
- En cas d'échec ou d'erreur réseau, ALICE annonce désormais la vérité à l'utilisateur :  
  *« Impossible d'actionner la lumière de salon. La commande Home Assistant a échoué ou l'appareil est injoignable. »*
- Garantie d'intégrité opérationnelle : l'utilisateur n'est plus trompé sur l'état physique de sa domotique et de ses alarmes.

---

### 2.6. SEC-06 — Intégrité Mémoire, Concurrence Thread-Safe et Résilience Contextuelle

#### Contexte et Vulnérabilité
Dans `Jarvis Final - SITE/main2.py`, la mémoire persistante `jarvis_memoire.json` présentait deux failles critiques :
1. Écritures concurrentes sans verrouillage provoquant des corruptions de fichier JSON ou des troncatures à 0 octet.
2. L'action `add_reminder` ajoutait une liste dans `memoire["reminders"]`. Or, `construire_contexte_memoire` itérait sur toutes les clés en attendant un dictionnaire avec la clé `valeur` (`data['valeur']`). Cela déclenchait un `TypeError: list indices must be integers or slices, not str`, rendant ALICE définitivement muette et indisponible au démarrage.

#### Solution Implémentée
- **Verrouillage multi-thread :** introduction de `MEMOIRE_LOCK = threading.RLock()` sur l'ensemble des opérations de lecture, écriture et modification.
- **Écriture atomique sur disque :** sauvegarde dans un fichier temporaire avec vidage physique des tampons OS (`f.flush()`, `os.fsync()`), suivi d'un remplacement atomique via `os.replace()`.
- **Parsing tolérant aux schémas hétérogènes :** restructuration complète de `construire_contexte_memoire` pour traiter avec élégance :
  - Les rappels structurés sous forme de listes (`reminders`).
  - Les faits mémorisés sous forme de dictionnaires (`valeur`, `timestamp`).
  - Les types primitifs (entiers, chaînes, booléens).

---

## 3. BILAN DE VALIDATION ET ESSAIS AUTOMATISÉS

Le banc de test exhaustif `scratch/test_alice_p0_comprehensive.py` a été exécuté dans l'environnement virtuel Python du projet.

| Domaine de Sécurité | Référence | Tests Définis | Tests Validés | Taux de Succès |
| :--- | :---: | :---: | :---: | :---: |
| **Exécution de code arbitraire** | SEC-01 | 5 | 5 | **100 %** |
| **Téléversement & Path Traversal** | SEC-02 | 4 | 4 | **100 %** |
| **Commandes système & Extinction** | SEC-03 | 9 | 9 | **100 %** |
| **Sécurité WebSocket & Sessions** | SEC-04 | 3 | 3 | **100 %** |
| **Vérité opérationnelle domotique** | SEC-05 | 2 | 2 | **100 %** |
| **Intégrité mémoire persistante** | SEC-06 | 2 | 2 | **100 %** |
| **TOTAL** | — | **25** | **25** | **100.0 %** |

Compilations vérifiées :
- `alice_modules.py` : `py_compile` **OK**
- `main2.py` : `py_compile` **OK**
- Frontend Web Three.js : `npx tsc --noEmit` **0 erreur**

---

## 4. LIMITES RÉSIDUELLES ET RECOMMANDATIONS P1 / P2

Bien que l'ensemble des vulnérabilités critiques P0 soient intégralement neutralisées, l'architecture bénéficiera des améliorations de niveau P1 / P2 suivantes lors des phases ultérieures :

1. **Environnement Sandbox Isolé (P1) :** Si l'exécution dynamique de code Python par ALICE doit être réactivée à terme, intégrer un conteneur éphémère Docker rootless ou un microVM gVisor avec isolation réseau et mémoire stricte.
2. **Migration Groq Model (P1) :** Mettre à jour dans la configuration les identifiants de modèles Groq dépréciés (`qwen3.6-27b`) vers les modèles actifs supportés par l'API (`qwen/qwen3.8-27b`).
3. **Mise à niveau des dépendances venv (P2) :** Installer les paquets optionnels de vision et OCR (`easyocr`, `rembg`, `openpyxl`) pour exploiter l'ensemble des 16 modules ALICE.
