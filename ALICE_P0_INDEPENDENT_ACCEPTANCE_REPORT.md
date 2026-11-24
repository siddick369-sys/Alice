# MISSION ALICE-P0-INDEPENDENT-ACCEPTANCE-002
## AUDIT CONTRADICTOIRE INDÉPENDANT — HOMOLOGATION SÉCURITÉ, TESTS ADVERSARIAUX ET VALIDATION DES SIX REMÉDIATIONS P0

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 22 Novembre 2026  
**Auditeur :** Principal Security Architect, Adversarial Security & Reliability Engineer  
**Mode :** STRICT READ-ONLY / AUDIT ADVERSARIAL CONTRADICTOIRE  
**Décision d'homologation :** **REJETÉE (`REJECTED`)**  
**Nombre de tests adversariaux exécutés :** 57 (46 PASS, 5 PARTIAL, 6 FAIL)  

---

## 1. RÉSUMÉ EXÉCUTIF

Dans le cadre de la mission `ALICE-P0-INDEPENDENT-ACCEPTANCE-002`, un audit de sécurité contradictoire et indépendant a été mené sur les modifications apportées lors de la remédiation `ALICE-REMEDIATION-P0-001`.

L'objectif de cet audit n'était pas de reconduire passivement les conclusions du rapport précédent (qui affirmait une conformité de 100 % sur 25 tests), mais de soumettre le code source réel à des épreuves adversariales rigoureuses, de vérifier le fonctionnement des composants dans leur contexte serveur complet et de détecter d'éventuelles failles ou régressions introduites.

### Conclusions principales :
1. **SEC-01 (Neutralisation RCE) : VALIDÉ AVEC RÉSERVES (`PASS`).** L'exécution dynamique de code arbitraire sur l'hôte via `verifier_code_boucle` a été intégralement supprimée (`subprocess.run` éliminé). Toutefois, l'inspection AST ne constitue pas un sandbox complet, bien que l'exécution demeure désactivée par conception.
2. **SEC-02 (Upload & Path Traversal) : VALIDÉ (`PASS`).** Le confinement des fichiers dans `temp_uploads/`, l'assainissement par nom de base, l'UUID v4 et la whitelist d'extensions résistent aux 18 vecteurs de traversée testés. La désindentation de `screen_frame` est effective.
3. **SEC-03 (System Action Controller) : PARTIELLEMENT VALIDÉ (`PARTIAL`).** Le mot-clé naïf a été supprimé et la désambiguïsation domotique fonctionne. Cependant, le protocole de confirmation (`pending_action`) est un état global unique non lié à une session ou IP cliente, permettant à un tiers de confirmer ou annuler une action initiée par un autre utilisateur.
4. **SEC-04 (WebSocket & Authentification) : ÉCHEC CRITIQUE (`FAIL`).**
   - **Faillite d'authentification :** L'endpoint HTTP `/api/auth/token` délivre le jeton de session à quiconque en fait la demande, sans aucune authentification, avec un en-tête `Access-Control-Allow-Origin: *`.
   - **Bypass de politique d'origine (CSWSH) :** La validation d'origine vérifie `host.startswith("192.168.")`, ce qui autorise n'importe quel domaine malveillant tel que `http://192.168.attacker.com`.
   - **Régression critique de l'interface mobile :** Le client `mobile/app.js` ne récupère jamais le jeton et n'envoie aucun message d'authentification. En conséquence, **tout équipement mobile sur le LAN est déconnecté après 5 secondes** (code 4001).
5. **SEC-05 (Vérité domotique) : PARTIELLEMENT VALIDÉ (`PARTIAL`).** Les erreurs d'API et codes HTTP 500/400 sont correctement répercutés à l'utilisateur. Cependant, le code assimile un code HTTP 200 de Home Assistant à une confirmation d'état physique réel, alors que Home Assistant acquitte seulement la mise en file d'attente du service (`REQUEST_ACCEPTED` != `STATE_VERIFIED`).
6. **SEC-06 (Mémoire persistante) : ÉCHEC CRITIQUE (`FAIL`).** Si `charger_memoire` et `sauvegarder_memoire` ont été durcis, deux autres fonctions de persistance activement appelées par le routeur IA — `memory_add` (ligne 2106) et `memory_forget` (ligne 2126) — écrivent directement dans `jarvis_memoire.json` **sans acquérir le verrou `MEMOIRE_LOCK` et sans écriture atomique**.

En application de la règle stricte de certification (Section 14 : *« Un seul échec critique suffit à empêcher l'acceptation globale »*), **l'homologation globale est formellement REJETÉE (`REJECTED`)**.

---

## 2. BASELINE FORENSIQUE ET ÉTAT INITIAL

Avant toute exécution de tests, l'empreinte exacte du dépôt a été constatée :

- **Répertoire racine :** `c:\Users\USER\Desktop\Jarvis Final - SITE-V2`
- **Branche Git :** `main`
- **HEAD Git :** `f9c319557f4a02d8ddf5957505bde91c87947940`
- **État `git status --short` :**
  - Modifiés (non commités) : `Jarvis Final - SITE/alice_modules.py`, `Jarvis Final - SITE/main2.py`
  - Non suivis : `ALICE_P0_CHANGELOG.md`, `ALICE_P0_REMEDIATION_REPORT.md`, `ALICE_P0_SECURITY_TEST_MATRIX.md`
- **Interpréteur Python :** Python 3.11.8 (`c:\Users\USER\Desktop\Jarvis Final - SITE-V2\Jarvis Final - SITE\venv\Scripts\python.exe`)
- **Version Websockets :** 16.0

### Empreintes cryptographiques SHA-256 des fichiers audités

| Fichier | Empreinte SHA-256 |
| :--- | :--- |
| `Jarvis Final - SITE/alice_modules.py` | `711c697bb5f0c03b3d46fd35b0515229d21cb15370c601a05cb718b88bcaa536` |
| `Jarvis Final - SITE/main2.py` | `42c849e71e32597fa95e71fa626249dd75f2358093147a8d4fc49fe586bbda03` |
| `ALICE_P0_CHANGELOG.md` | `3f56dc63df873620d3f2cb2dc19e3d8eaccbb3701660f9a1ba0845294550aa87` |
| `ALICE_P0_REMEDIATION_REPORT.md` | `8b3cc0534cc689fa47093ea76750ee8f30b6ca775064d6025f9324be68f1cb5b` |
| `ALICE_P0_SECURITY_TEST_MATRIX.md` | `9d13837b9e36ce6254be795d372d684e3b46e25d08805fe90b95469e9f34269b` |
| `Jarvis Final - SITE/frontend/src/main.ts` | `5b986cdd149aac1b2c4cff34ee6d02fdd7af62e341f080ae61fd7ecc7032c162` |
| `Jarvis Final - SITE/mobile/app.js` | `7de1a9ba81e4ff326ef0279804dfe793245ba16f426a101c1b844b59429ac9e0` |

---

## 3. ANALYSE CONTRADICTOIRE DOMAINE PAR DOMAINE

### 3.1. SEC-01 — Analyse Statique et Suppression du RCE
- **Code audité :** `alice_modules.py` L834-950 (`verifier_code_boucle`)
- **Vérification de suppression d'exécution :** Aucune invocation de `subprocess.run`, `subprocess.Popen`, `os.system`, `exec` ou `eval` n'est effectuée sur l'hôte. Les tests d'interception avec mocks confirment que 0 sous-processus ne sont lancés.
- **Résistance adversariale :**
  - Les tentatives d'import direct (`os`, `sys`, `subprocess`) ou de builtins (`eval`, `exec`, `__import__`) sont interceptées par le visiteur AST.
  - L'évasion par `globals()` passe l'AST mais ne donne lieu à **aucune exécution** car le moteur dynamique a été éliminé (`execution_status: "DISABLED_FOR_SECURITY"`).
- **Limite technique identifiée :** L'inspection AST ne constitue pas un sandbox d'exécution. Si l'exécution dynamique venait à être rétablie sans conteneurisation isolée, le filtrage AST serait contournable par métaprogrammation.
- **Statut d'homologation :** **PASS (avec réserve d'absence de sandbox si réactivation future)**.

---

### 3.2. SEC-02 — Upload de Fichiers et Path Traversal
- **Code audité :** `main2.py` L642-731 (`ws_handler` branche `file_upload`)
- **Résistance aux 18 vecteurs de traversée :**
  - `os.path.basename` neutralise les chemins relatifs (`../../`) et absolus (`C:\Windows\...`, `\\server\share\...`).
  - `re.sub(r'[^a-zA-Z0-9_\.-]', '_', base)[:50]` assainit les caractères et tronque à 50 caractères, protégeant contre les dépassements de chemin Windows (`MAX_PATH`).
  - L'UUID v4 préfixé rend les noms de stockage internes non prévisibles et élimine les écrasements.
  - La vérification canonique `os.path.realpath(file_path).startswith(os.path.realpath(temp_dir) + os.sep)` garantit l'impossibilité d'écrire hors de `temp_uploads/`.
- **Validation de `screen_frame` :** L'instruction `elif msg_type == "screen_frame":` est désormais désindentée au niveau principal (L735), restaurant le traitement des captures sans dépendance à l'upload.
- **Risque résiduel identifié :** Absence de politique de rétention ou nettoyage périodique dans `temp_uploads/` pouvant saturer l'espace disque sur le long terme.
- **Statut d'homologation :** **PASS**.

---

### 3.3. SEC-03 — Contrôle des Commandes Système (Arrêt / Redémarrage PC)
- **Code audité :** `main2.py` L1849-1995 (`SystemActionController` & `executer_action_pc`)
- **Élimination du déclencheur naïf :** La chaîne `if "eteins" in cmd` a bien été retirée.
- **Corpus adversarial :**
  - « Éteins la lumière », « Éteins la télé », « Arrête la musique » renvoient `None` et sont bien routés vers Home Assistant.
  - « Je ne veux pas éteindre mon PC » et « N'éteins surtout pas Windows » sont neutralisés par la détection des négations.
  - « Éteins mon ordinateur » et « Redémarre mon ordinateur » ouvrent bien une fenêtre de confirmation de 30 secondes.
- **Défauts identifiés lors de l'audit adversarial :**
  1. **Faux positif sur formulation réflexive :** « Je pense éteindre mon PC » déclenche la demande de confirmation 2FA au lieu d'être ignoré (`ADV-03-35 FAIL`).
  2. **Absence d'isolation de session (`ADV-03-SESSION PARTIAL`) :** `pending_action` est un attribut d'instance global unique. Si l'utilisateur sur le PC demande l'extinction, un client sur le réseau local ou via WebSocket peut envoyer « confirmer l'extinction » et valider l'action à son insu, car l'adresse IP cliente est consignée dans l'audit log mais n'est pas comparée lors de la confirmation.
- **Statut d'homologation :** **PARTIAL**.

---

### 3.4. SEC-04 — Audit Approfondi du WebSocket et de l'Authentification
- **Code audité :** `main2.py` L479-629 (`WSSessionManager`, `ws_handler`) et L3904-3929 (`start_mobile_http_server`)
- **Vulnérabilités critiques démontrées :**

#### 1. Divulgation publique du jeton via `/api/auth/token` (`ADV-04-ENDPOINT FAIL`)
Dans `start_mobile_http_server` (L3915-3923) :
```python
if self.path == "/api/auth/token":
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    token_payload = json.dumps({"token": get_active_ws_token()})
    self.wfile.write(token_payload.encode("utf-8"))
```
Le serveur écoute sur `0.0.0.0:8080`. N'importe quelle machine du réseau local ou n'importe quel site web malveillant visité dans le navigateur peut exécuter `fetch("http://192.168.1.23:8080/api/auth/token")`. Grâce à `Access-Control-Allow-Origin: *`, le navigateur ne bloque pas la lecture. L'attaquant obtient instantanément le jeton de session WebSocket actif.

#### 2. Contournement de validation d'origine (`ADV-04-ORIGIN FAIL`)
Dans `WSSessionManager.is_origin_allowed` (L534) :
```python
if host and (host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.")):
    return True
```
Cette vérification utilise un simple préfixe de chaîne au lieu de valider une adresse IP IPv4/CIDR. Un nom de domaine comme `http://192.168.attacker.com` ou `http://10.malicious.net` est évalué comme légitime (`True`).

#### 3. Détournement local combiné (CSWSH -> Loopback Auto-Auth)
Les connexions provenant de `127.0.0.1` sont marquées `authenticated = True` sans exiger de jeton. Combiné avec le contournement d'origine ci-dessus, une page web malveillante ouverte par la victime peut établir une connexion WebSocket directe sur `ws://localhost:8765`, être validée par le filtre d'origine trompeur et bénéficier de l'auto-authentification loopback.

#### 4. Rupture de fonctionnement du client mobile (`mobile/app.js`)
L'analyse de `mobile/app.js` démontre qu'aucun appel à `/api/auth/token` n'a été implémenté dans le client mobile. Le client tente une connexion WebSocket brute sans jeton. Le backend attendant un message d'authentification sous 5 secondes pour tout client distant, **le client mobile est déconnecté systématiquement avec l'erreur 4001 toutes les 5 secondes**.
- **Statut d'homologation :** **FAIL (Inacceptable en l'état)**.

---

### 3.5. SEC-05 — Vérité Opérationnelle Home Assistant
- **Code audité :** `main2.py` L1265-1325 et L3056-3142
- **Gestion des erreurs API :** L'interception des codes HTTP 400, 401, 403, 404, 500, des timeouts et des refus de connexion a été vérifiée avec succès. ALICE n'annonce plus de fausse réussite lorsque l'API Home Assistant échoue.
- **Limite conceptuelle (`REQUEST_ACCEPTED` vs `STATE_VERIFIED`) :**
  Dans l'API REST de Home Assistant, l'appel de service `POST /api/services/{domain}/{service}` renvoie HTTP 200 dès que l'ordre est pris en charge par le bus d'événements. Il ne garantit pas que l'appareil physique (lampe Zigbee éteinte à l'interrupteur, volet déconnecté, alarme en défaut matériel) a effectivement changé d'état. Pour des commandes critiques comme l'armement/désarmement d'alarme (`ha_alarme`), la confirmation vocale devrait être asservie à une interrogation d'état ultérieure (`ha_get_etat`).
- **Statut d'homologation :** **PARTIAL**.

---

### 3.6. SEC-06 — Mémoire Persistante et Écritures Concurrentes
- **Code audité :** `main2.py` L389-435 et L2106-2144
- **Concurrence sur `charger_memoire` / `sauvegarder_memoire` :** Le verrou `MEMOIRE_LOCK` et l'écriture atomique via `.tmp` et `os.replace` protègent efficacement les fonctions principales. Le parsing de `construire_contexte_memoire` ne lève plus d'exception `TypeError` sur les rappels (`reminders`).
- **Vulnérabilité critique découverte (`ADV-06-01 FAIL`) :**
  L'audit a identifié que le routeur IA (L3293 et L3301) appelle les fonctions `memory_add(cle, valeur)` et `memory_forget(cle)` définies à la ligne 2106 :
  ```python
  def memory_add(cle, valeur):
      with open("jarvis_memoire.json", "r", encoding="utf-8") as f:
          data = json.load(f)
      ...
      with open("jarvis_memoire.json", "w", encoding="utf-8") as f:
          json.dump(data, f, indent=2, ensure_ascii=False)
  ```
  Ces deux fonctions :
  1. N'acquièrent pas `MEMOIRE_LOCK`.
  2. N'utilisent pas d'écriture atomique (`os.replace`).
  3. Utilisent un chemin relatif `"jarvis_memoire.json"` dépendant du répertoire courant d'exécution.
  Toute action mémorielle déclenchée par l'IA lors d'un traitement vocal concurrent peut donc corrompre ou tronquer le fichier mémoire, contournant totalement les sécurités de `sauvegarder_memoire`.
- **Statut d'homologation :** **FAIL**.

---

## 4. AUDIT CONTRADICTOIRE DES 25 TESTS ANNONCÉS

Le rapport précédent affirmait un score parfait de 25/25 tests réussis. L'examen minutieux du banc de test `test_alice_p0_comprehensive.py` et des scripts de scratch révèle une disparité méthodologique majeure :

| Catégorie | Tests Concernés | Ce qui était réellement testé | Ce qui manquait pour une preuve de sécurité |
| :--- | :--- | :--- | :--- |
| **Upload (SEC-02)** | SEC02-01 à SEC02-03 | Manipulations de chaînes isolées (`os.path.basename`, regex) | Le handler complet `ws_handler` et la réception de paquets réels n'étaient pas sollicités. |
| **Vision (SEC-02)** | SEC02-04 | Création et résolution manuelle d'une Future dans un dictionnaire local | Aucun message WebSocket réel n'était injecté pour prouver le découplage dans la boucle d'événements. |
| **WebSocket (SEC-04)** | SEC04-03 | Méthode `is_origin_allowed` testée uniquement avec des entrées bienveillantes | Aucune entrée adversariale (ex. `192.168.attacker.com`) n'a été soumise ; l'endpoint `/api/auth/token` n'a pas été audité. |
| **Domotique (SEC-05)** | SEC05-01, SEC05-02 | Appel direct de la fonction `ha_lumiere` avec mock HTTP | Le routeur `traiter_reponse_ia` et la restitution vocale réelle n'étaient pas inclus dans l'assertion. |

**Bilan :** Sur les 25 tests présentés, seuls 15 constituaient des tests d'intégration portant sur le code réellement actif. 10 tests étaient des vérifications unitaires de logique partielle ou isolée.

---

## 5. BILAN GLOBAL DES TESTS ADVERSARIAUX

L'exécution du banc de test contradictoire exhaustif (`scratch/adversarial_suite_acceptance_002.py`) produit le bilan suivant :

```text
=======================================================
ADVERSARIAL RESULTS: Total=57 | PASS=46 | PARTIAL=5 | FAIL=6
=======================================================
```

- **Taux d'échec / non-conformité :** 19.3 % (11 tests en échec ou partiels sur 57).
- **Failles critiques avérées :** 3 (Endpoint token public, Bypass d'origine DNS, Fonctions mémoire non verrouillées).
- **Régression fonctionnelle bloquante :** 1 (Client mobile LAN déconnecté en boucle).

---

## 6. CONDITIONS IMPÉRATIVES DE RÉ-HOMOLOGATION

Pour prétendre à l'homologation lors d'une future mission de remédiation, les actions correctives suivantes devront être apportées :

1. **Suppression ou sécurisation stricte de `/api/auth/token` :** Éliminer l'en-tête CORS wildcard et exiger une clé d'authentification partagée ou un mécanisme d'appairage initial sécurisé pour les clients LAN.
2. **Correction du parseur d'origine WebSocket :** Remplacer le test `host.startswith(...)` par une validation d'adresse IP stricte via le module standard `ipaddress.ip_address(host).is_private`.
3. **Mise à jour du client mobile :** Implémenter dans `mobile/app.js` la poignée de main d'authentification requise dès l'ouverture du WebSocket (`{"type": "auth", "token": "..."}`).
4. **Verrouillage intégral de la mémoire :** Remplacer le contenu des fonctions `memory_add` et `memory_forget` par des appels aux fonctions thread-safe `ajouter_memoire` et `supprimer_memoire` sous le verrou `MEMOIRE_LOCK`.
5. **Isolation de session sur les actions système :** Lier l'objet `pending_action` à l'identifiant de session ou à l'adresse IP cliente pour interdire la confirmation croisée d'extinction.
