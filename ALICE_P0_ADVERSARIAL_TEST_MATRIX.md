# MATRICE DES TESTS ADVERSARIAUX — MISSION ALICE-P0-INDEPENDENT-ACCEPTANCE-002

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 22 Novembre 2026  
**Environnement :** Python 3.11.8 / websockets 16.0 (venv Windows)  
**Banc de test :** `scratch/adversarial_suite_acceptance_002.py`  
**Résultat synthétique :** Total = 57 | **PASS = 46** | **PARTIAL = 5** | **FAIL = 6**

---

## TABLEAU COMPLET DES CAS D'ÉPREUVE ADVERSARIALE

| ID Test | Domaine | Scénario / Vecteur Adversarial | Entrée Testée | Comportement Sécurisé Attendu | Résultat Réellement Observé | Preuve Empirique | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **ADV-01-01** | SEC-01 | Import dynamique obfusqué (`getattr` / `__import__`) | `getattr(__import__('os'), 'system')('calc')` | Rejet statique immédiat sans exécution | `success=False`, `execution_status: DISABLED_FOR_SECURITY` | `__import__` détecté par inspection AST | **PASS** |
| **ADV-01-02** | SEC-01 | Évasion AST par lookup dans `globals()` | `g = globals(); b = g['__builtins__']` | Pas d'exécution dynamique sur l'hôte | `success=True`, `execution_status: DISABLED_FOR_SECURITY` | Moteur dynamique supprimé, code non lancé sur l'OS | **PASS** |
| **ADV-01-03** | SEC-01 | Invocations de sous-processus dans la boucle | `def hello(): return 'world'` | 0 appel `subprocess.run` ou `Popen` | `mock_sub.called: False, mock_popen.called: False` | Aucune fonction système OS invoquée | **PASS** |
| **ADV-01-04** | SEC-01 | Injection de constructeur JS `Function()` | `const f = new Function('return process')()` | Pattern critique détecté et rejeté | `success=False`, pattern identifié | `details: ['Pattern JavaScript non sécurisé : Function(']` | **PASS** |
| **ADV-02-05** | SEC-02 | Traversée relative simple `../` | `../../outside.txt` | Confinement strict dans `temp_uploads/` | Nom assaini en `outside.txt`, confiné | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-06** | SEC-02 | Traversée avec antislashs Windows `..\` | `..\..\outside.txt` | Confinement strict dans `temp_uploads/` | Séparateurs normalisés, nom assaini | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-07** | SEC-02 | Chemin absolu avec lettre de lecteur Windows | `C:\Windows\Temp\outside.txt` | Annihilation du lecteur et de l'arborescence | Nom extrait en `outside.txt`, confiné | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-08** | SEC-02 | Chemin absolu avec slashs Unix | `C:/Windows/Temp/outside.txt` | Annihilation de l'arborescence absolue | Nom extrait en `outside.txt`, confiné | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-09** | SEC-02 | Partage réseau UNC Windows | `\\server\share\outside.txt` | Annihilation du chemin UNC | Nom extrait en `outside.txt`, confiné | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-10** | SEC-02 | Traversée à séparateurs mixtes | `..\../..\outside.txt` | Confinement strict dans `temp_uploads/` | Nom assaini en `outside.txt`, confiné | Résolu : `temp_uploads/<uuid>_outside.txt` | **PASS** |
| **ADV-02-11** | SEC-02 | Traversée URL-encodée simple | `%2e%2e%2foutside.txt` | Pas de traversée possible | Nom traité comme slug littéral assaini | `_2e_2e_2foutside.txt` confiné | **PASS** |
| **ADV-02-12** | SEC-02 | Traversée doublement URL-encodée | `%252e%252e%252foutside.txt` | Pas de traversée possible | Nom traité comme slug littéral assaini | Caractères `%` remplacés par `_`, confiné | **PASS** |
| **ADV-02-13** | SEC-02 | Nom de fichier vide | `""` | Attribution d'un nom par défaut sécurisé | Fichier stocké sous `<uuid>_.txt` | Confiné dans `temp_uploads/` | **PASS** |
| **ADV-02-14** | SEC-02 | Nom de fichier géant (dépassement `MAX_PATH`) | `A` * 500 + `.txt` | Troncature à taille raisonnable sans crash | Slug tronqué à 50 caractères maximum | Nom ramené à `<uuid>_AAAAA...50.txt` | **PASS** |
| **ADV-02-15** | SEC-02 | Téléversement d'exécutable `.exe` | `malware.exe` | Rejet immédiat par filtrage whitelist | `rejected=True`, fichier non écrit sur disque | Extension présente dans `FORBIDDEN_EXTS` | **PASS** |
| **ADV-02-16** | SEC-02 | Téléversement de script batch `.bat` | `script.bat` | Rejet immédiat par filtrage whitelist | `rejected=True`, fichier non écrit sur disque | Extension présente dans `FORBIDDEN_EXTS` | **PASS** |
| **ADV-02-17** | SEC-02 | Téléversement de script PowerShell `.ps1` | `exploit.ps1` | Rejet immédiat par filtrage whitelist | `rejected=True`, fichier non écrit sur disque | Extension présente dans `FORBIDDEN_EXTS` | **PASS** |
| **ADV-02-18** | SEC-02 | Double extension avec exécutable final | `test.txt.exe` | Rejet immédiat (extension finale `.exe`) | `rejected=True`, fichier non écrit sur disque | Extension analysée = `.exe` | **PASS** |
| **ADV-02-19** | SEC-02 | Double extension avec texte final | `test.exe.txt` | Traitement comme fichier texte inoffensif | Accepté comme texte et confiné | Résolu sous `<uuid>_test_exe.txt` | **PASS** |
| **ADV-02-20** | SEC-02 | Extension exécutable en majuscules | `PAYLOAD.EXE` | Rejet insensible à la casse | `rejected=True` (normalisé en `.exe`) | `ext.lower()` intercepte l'extension | **PASS** |
| **ADV-02-21** | SEC-02 | Extension autorisée en majuscules | `document.PDF` | Acceptation et normalisation | `canonical_ok=True` | Traité comme `.pdf` | **PASS** |
| **ADV-02-22** | SEC-02 | Document PDF légitime standard | `valid.pdf` | Stockage sous UUID unique | Fichier persisté en toute sécurité | `<uuid>_valid.pdf` | **PASS** |
| **ADV-02-B64** | SEC-02 | Charge utile Base64 corrompue | `INVALID_B64_!!!` | Exception interceptée sans crash serveur | `validate=True` lève `binascii.Error` gérée | Bloc `except Exception` renvoie une erreur JSON propre | **PASS** |
| **ADV-03-24** | SEC-03 | Domotique lumière (« Éteins la lumière ») | « Éteins la lumière. » | Renvoie `None` (routage vers Home Assistant) | `res=None` | Aucun arrêt PC programmé | **PASS** |
| **ADV-03-25** | SEC-03 | Domotique lampe (« Éteins la lampe du salon ») | « Éteins la lampe du salon. » | Renvoie `None` (routage vers Home Assistant) | `res=None` | Mot-clé lampe détecté | **PASS** |
| **ADV-03-26** | SEC-03 | Domotique TV (« Éteins la télévision ») | « Éteins la télévision. » | Renvoie `None` (routage vers Home Assistant) | `res=None` | Mot-clé télévision détecté | **PASS** |
| **ADV-03-27** | SEC-03 | Négation explicite (« Je ne veux pas éteindre ») | « Je ne veux pas éteindre mon PC. » | Renvoie `None` (pas d'arrêt) | `res=None` | Négation « ne veux pas » neutralise la commande | **PASS** |
| **ADV-03-28** | SEC-03 | Question réflexive (« Pourquoi éteindre ? ») | « Pourquoi éteindre mon ordinateur ? » | Renvoie `None` (pas d'arrêt) | `res=None` | Mot-clé « pourquoi » neutralise la commande | **PASS** |
| **ADV-03-29** | SEC-03 | Négation impérative (« N'éteins surtout pas ») | « N'éteins surtout pas Windows. » | Renvoie `None` (pas d'arrêt) | `res=None` | Négation « n'éteins pas » neutralise la commande | **PASS** |
| **ADV-03-30** | SEC-03 | Arrêt tâche multimédia (« Arrête la musique ») | « Arrête la musique. » | Renvoie `None` (pas d'extinction PC) | `res=None` | Pas de cible PC détectée | **PASS** |
| **ADV-03-31** | SEC-03 | Arrêt tâche réseau (« Arrête le téléchargement ») | « Arrête le téléchargement. » | Renvoie `None` (pas d'extinction PC) | `res=None` | Pas de cible PC détectée | **PASS** |
| **ADV-03-32** | SEC-03 | Intention explicite (« Éteins mon ordinateur ») | « Éteins mon ordinateur. » | Demande de confirmation 2FA émise | Prompt de confirmation 30s émis | `pending_action: {'action': 'shutdown'}` | **PASS** |
| **ADV-03-33** | SEC-03 | Intention explicite (« Éteins le PC ») | « Éteins le PC. » | Demande de confirmation 2FA émise | Prompt de confirmation 30s émis | `pending_action: {'action': 'shutdown'}` | **PASS** |
| **ADV-03-34** | SEC-03 | Intention explicite redémarrage | « Redémarre mon ordinateur. » | Demande de confirmation 2FA reboot | Prompt de confirmation 30s émis | `pending_action: {'action': 'reboot'}` | **PASS** |
| **ADV-03-35** | SEC-03 | Formulation conditionnelle / pensée | « Je pense éteindre mon PC. » | Ignorer (pas d'impératif clair) | **Prompt 2FA déclenché à tort** | Regex trop gourmande capturant « éteindre mon pc » | **FAIL** |
| **ADV-03-36** | SEC-03 | Demande polie d'extinction | « Est-ce que tu peux éteindre mon PC ? » | Demande de confirmation 2FA émise | Prompt de confirmation 30s émis | Intention reconnue et confirmée | **PASS** |
| **ADV-03-SESSION** | SEC-03 | Isolation de session sur la confirmation | Session B confirme l'action de Session A | Confirmation rejetée si initiateur différent | **Session B valide l'action de Session A** | `pending_action` global sans contrôle de `client_ip` | **PARTIAL** |
| **ADV-04-ORIGIN-38** | SEC-04 | Origine falsifiée IP préfixée `192.168.` | `http://192.168.attacker.com` | Rejet de l'origine malveillante externe | **Origine autorisée par `startswith()`** | `is_origin_allowed("http://192.168.attacker.com") = True` | **FAIL** |
| **ADV-04-ORIGIN-39** | SEC-04 | Origine falsifiée IP préfixée `10.` | `http://10.attacker.io` | Rejet de l'origine malveillante externe | **Origine autorisée par `startswith()`** | `is_origin_allowed("http://10.attacker.io") = True` | **FAIL** |
| **ADV-04-ORIGIN-40** | SEC-04 | Origine falsifiée IP préfixée `172.` | `http://172.malicious.net` | Rejet de l'origine malveillante externe | **Origine autorisée par `startswith()`** | `is_origin_allowed("http://172.malicious.net") = True` | **FAIL** |
| **ADV-04-ORIGIN-41** | SEC-04 | Sous-domaine frauduleux `localhost.evil.com` | `http://localhost.evil.com` | Rejet de l'origine | Rejetée avec succès | `is_origin_allowed = False` | **PASS** |
| **ADV-04-ORIGIN-42** | SEC-04 | Sous-domaine frauduleux `127.0.0.1.attacker.com` | `http://127.0.0.1.attacker.com` | Rejet de l'origine | Rejetée avec succès | `is_origin_allowed = False` | **PASS** |
| **ADV-04-ORIGIN-43** | SEC-04 | Origine externe quelconque | `http://evil.com` | Rejet de l'origine | Rejetée avec succès | `is_origin_allowed = False` | **PASS** |
| **ADV-04-ENDPOINT** | SEC-04 | Accès non authentifié à `/api/auth/token` | Requête `GET /api/auth/token` sur port 8080 | Accès restreint ou authentifié | **Jeton délivré librement avec `CORS: *`** | `token_payload` renvoyé sans contrôle | **FAIL** |
| **ADV-04-LOOPBACK** | SEC-04 | Modèle de confiance loopback non authentifié | Connexion WebSocket depuis `127.0.0.1` | Jeton exigé pour tout client navigateur | Loopback auto-autorisé sans jeton | Exploitable via CSWSH local | **PARTIAL** |
| **ADV-05-46** | SEC-05 | Home Assistant HTTP 200 avec entité valide | HTTP 200 `[{"state": "on"}]` | Distinguer mise en file vs état physique vérifié | Marqué succès dès HTTP 200 | Pas de relecture de capteur | **PARTIAL** |
| **ADV-05-47** | SEC-05 | Home Assistant HTTP 200 avec liste vide | HTTP 200 `[]` | Distinguer anomalie vs succès réel | Marqué succès dès HTTP 200 | Retour considéré comme succès | **PARTIAL** |
| **ADV-05-48** | SEC-05 | Home Assistant HTTP 400 Bad Request | HTTP 400 | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Erreur convenablement gérée | **PASS** |
| **ADV-05-49** | SEC-05 | Home Assistant HTTP 401 Unauthorized | HTTP 401 | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Token expiré/invalide reconnu | **PASS** |
| **ADV-05-50** | SEC-05 | Home Assistant HTTP 403 Forbidden | HTTP 403 | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Permissions insuffisantes reconnues | **PASS** |
| **ADV-05-51** | SEC-05 | Home Assistant HTTP 404 Not Found | HTTP 404 | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Entité inexistante reconnue | **PASS** |
| **ADV-05-52** | SEC-05 | Home Assistant HTTP 500 Internal Error | HTTP 500 | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Panne serveur HA reconnue | **PASS** |
| **ADV-05-53** | SEC-05 | Exception Timeout réseau Home Assistant | Timeout réseau 5s | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Timeout capturé proprement | **PASS** |
| **ADV-05-54** | SEC-05 | Refus de connexion réseau Home Assistant | `ConnectionError` | Détection d'échec et annonce vocale d'erreur | `ha_lumiere = False`, annonce d'échec | Refus de connexion capturé | **PASS** |
| **ADV-05-55** | SEC-05 | Réponse HTTP 200 avec corps vide `""` | HTTP 200 `""` | Interprétation prudente de la réponse | Marqué succès dès code HTTP 200 | Validé sur simple code statut HTTP | **PARTIAL** |
| **ADV-06-01** | SEC-06 | Verrouillage de `memory_add` et `memory_forget` | Analyse des fonctions lignes 2106 et 2126 | Acquisition obligatoire de `MEMOIRE_LOCK` | **Bypass total du verrou et de l'écriture atomique** | `with open("jarvis_memoire.json", "w")` sans lock | **FAIL** |
| **ADV-06-02** | SEC-06 | Robustesse face aux schémas hétérogènes | Mémoire avec `reminders` en liste, int et null | Parsing sans levée de `TypeError` | Contexte généré sans exception | `isinstance` validé sur chaque entrée | **PASS** |
