# MATRICE DES TESTS DE SÉCURITÉ P0 — ALICE / J.A.R.V.I.S

**Mission :** ALICE-REMEDIATION-P0-001  
**Référence d'audit :** ALICE-FORENSIC-AUDIT-001  
**Environnement de test :** Python 3.11.8 (venv) sous Windows  
**Banc de test :** `scratch/test_alice_p0_comprehensive.py`  
**Date d'exécution :** 22 Novembre 2026  
**Résultat global :** 25/25 SUCCÈS (100.0 %)

---

## 1. MATRICE COMPLÈTE DES CAS DE TEST

| ID Test | Composant | Vecteur d'Attaque / Scénario | Entrée Testée | Résultat Attendu | Résultat Obtenu | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **SEC01-01** | `alice_modules.py` | Analyse statique de code Python valide | `def addition(a, b): return a + b` | AST validé, pas d'exécution dynamique sur hôte | `safety_status: SECURE_STATIC_VERIFIED`, exécution neutralisée | **PASS** |
| **SEC01-02** | `alice_modules.py` | Détection d'erreur de syntaxe Python | `def broken( return 42` | Rejet statique propre sans crash ni exécution | `safety_status: REJECTED_UNSAFE_OR_INVALID`, SyntaxError capturé | **PASS** |
| **SEC01-03** | `alice_modules.py` | Tentative d'import de modules système dangereux | `import os; os.system('calc.exe')` | Rejet statique immédiat par inspection AST | Import interdit détecté (`os`), code bloqué | **PASS** |
| **SEC01-04** | `alice_modules.py` | Tentative d'exécution dynamique via builtin | `eval('1 + 1')` | Rejet statique immédiat par inspection AST | Appel interdit détecté (`eval()`), code bloqué | **PASS** |
| **SEC01-05** | `alice_modules.py` | Patterns JavaScript non sécurisés | `require('child_process').execSync('calc')` | Détection statique des patterns critiques | Pattern JavaScript non sécurisé détecté | **PASS** |
| **SEC02-01** | `main2.py` (WS) | Path Traversal relatif lors de l'upload | `../../../Windows/System32/drivers/etc/hosts` | Neutralisation via basename, confinement dans `temp_uploads` | Nom assaini en `hosts`, chemin confiné dans `temp_uploads` | **PASS** |
| **SEC02-02** | `main2.py` (WS) | Téléversement d'exécutables et scripts malveillants | Fichiers `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.sh`, `.dll` | Rejet immédiat par filtrage whitelist strict | Extension interdite rejetée sans écriture disque | **PASS** |
| **SEC02-03** | `main2.py` (WS) | Risque de collision et écrasement de fichiers | Upload de `rapport.pdf` | Génération d'un nom de stockage interne avec UUID v4 | Nom imprévisible généré (`<uuid>_rapport.pdf`) | **PASS** |
| **SEC02-04** | `main2.py` (WS) | Dépendance indue de `screen_frame` envers l'upload | Message WS `{ "type": "screen_frame", "id": "123" }` | Traitement autonome de la frame vidéo sans dépendance | Frame reçue et transmise à la promesse de capture | **PASS** |
| **SEC03-01** | `main2.py` (PC) | Confusion commande domotique vs extinction PC | « Éteins la lumière du salon » | Disqualification de l'extinction PC, routage Home Assistant | Renvoie `None` (transmis au routeur domotique) | **PASS** |
| **SEC03-02** | `main2.py` (PC) | Confusion commande télévision vs extinction PC | « Éteins la télévision » | Disqualification de l'extinction PC, routage Home Assistant | Renvoie `None` (transmis au routeur domotique) | **PASS** |
| **SEC03-03** | `main2.py` (PC) | Rejet des requêtes négatives | « Je ne veux pas éteindre le PC » | Pas d'extinction, reconnaissance de la négation | Renvoie `None` (aucun arrêt déclenché) | **PASS** |
| **SEC03-04** | `main2.py` (PC) | Rejet des requêtes interrogatives | « Pourquoi éteindre Windows ? » | Pas d'extinction, reconnaissance de l'interrogation | Renvoie `None` (aucun arrêt déclenché) | **PASS** |
| **SEC03-05** | `main2.py` (PC) | Protocole 2FA pour extinction de l'ordinateur | « Éteins mon ordinateur » puis « confirmer l'extinction » | Confirmation demandée (30s TTL), validation conditionnelle | Demande 2FA émise puis validée en mode DRY-RUN | **PASS** |
| **SEC03-06** | `main2.py` (PC) | Protocole 2FA pour redémarrage de l'ordinateur | « Redémarre mon ordinateur » puis « confirmer le redémarrage » | Confirmation demandée (30s TTL), validation conditionnelle | Demande 2FA émise puis validée en mode DRY-RUN | **PASS** |
| **SEC03-07** | `main2.py` (PC) | Annulation utilisateur de l'extinction | « Éteins mon ordinateur » puis « annuler » | Annulation immédiate et réinitialisation de l'état | Action annulée, machine conservée allumée | **PASS** |
| **SEC03-08** | `main2.py` (PC) | Expiration de la fenêtre de confirmation (TTL) | « Éteins mon ordinateur » puis confirmation après > 30s | Rejet de la confirmation pour expiration | Message d'expiration émis, action refusée | **PASS** |
| **SEC03-09** | `main2.py` (PC) | Traçabilité des actions sensibles | Événements d'arrêt, validation, expiration, annulation | Enregistrement horodaté dans `security_audit.log` | Journal mis à jour avec entrées `[SEC-AUDIT]` | **PASS** |
| **SEC04-01** | `main2.py` (WS) | Vérification cryptographique des jetons de session | Jeton aléatoire vs jeton falsifié | Jeton légitime accepté, jeton falsifié rejeté à temps constant | Validation `hmac.compare_digest` réussie | **PASS** |
| **SEC04-02** | `main2.py` (WS) | Rotation et révocation de session | Appel à `rotate_token()` | Ancien jeton immédiatement invalidé, nouveau jeton actif | Ancien jeton refusé, nouveau jeton accepté | **PASS** |
| **SEC04-03** | `main2.py` (WS) | Filtrage des origines (Anti-CSWSH) | `localhost`, `127.0.0.1`, `192.168.1.X` vs `evil.com` | Origines locales/LAN acceptées, origines externes rejetées | `evil.com` rejeté (`is_origin_allowed = False`) | **PASS** |
| **SEC05-01** | `main2.py` (HA) | Élimination des mensonges lors d'échec domotique | Requête Home Assistant renvoyant HTTP 500 | Détection de l'échec et annonce vocale explicite de panne | `ha_lumiere` renvoie `False`, ALICE annonce l'échec | **PASS** |
| **SEC05-02** | `main2.py` (HA) | Confirmation véridique lors de succès domotique | Requête Home Assistant renvoyant HTTP 200 | Détection du succès et confirmation vocale | `ha_lumiere` renvoie `True`, ALICE confirme l'action | **PASS** |
| **SEC06-01** | `main2.py` (MEM) | Résistance aux accès concurrents multi-threads | 5 threads x 10 écritures concurrentes dans la mémoire | Verrouillage `MEMOIRE_LOCK`, aucune écriture tronquée | 50 écritures persistées sans corruption | **PASS** |
| **SEC06-02** | `main2.py` (MEM) | Résilience du formateur de contexte mémoire | Mémoire contenant listes (`reminders`), entiers et dictionnaires | Parsing fluide sans déclencher de `TypeError` | Contexte IA généré sans aucune exception | **PASS** |

---

## 2. SYNTHÈSE D'EXÉCUTION

- **Nombre total d'épreuves :** 25
- **Épreuves réussies (PASS) :** 25
- **Épreuves échouées (FAIL) :** 0
- **Épreuves bloquées (BLOCKED) :** 0
- **Taux de conformité :** 100.0 %
