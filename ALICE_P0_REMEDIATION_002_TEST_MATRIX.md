# 🧪 MATRICE DE TEST FORENSIQUE ET ADVERSARIAL — ALICE-P0-REMEDIATION-002

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence :** `ALICE-P0-REMEDIATION-002`  
**Date d'Exécution :** 23 Novembre 2026  
**Environnement :** Python 3.11.8 Venv (`Jarvis Final - SITE/venv`)  
**Banc de test :** `scratch/test_remediation_002_full.py`  
**Score Global :** **66 / 66 TESTS PASS (100.0%)**

---

## 1. SUITE 1 : VALIDATION STRICTE D'ORIGINE & DÉFENSE CSWSH (SEC-04)

| ID Test | Vecteur d'Entrée (Origin Header) | Catégorie de Menace | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC04-O-01** | `http://192.168.attacker.com` | Bypass de préfixe DNS malveillant | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-02** | `http://10.attacker.io` | Bypass de préfixe DNS malveillant | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-03** | `http://172.malicious.net` | Bypass de préfixe DNS malveillant | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-04** | `http://192.168.1.attacker.com:8080` | Faux sous-domaine local avec port | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-05** | `http://attacker.com` | Domaine public non autorisé | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-06** | `http://169.254.169.254` | IP Link-Local / Métadonnées Cloud SSRF | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-07** | `http://8.8.8.8` | IP publique externe | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-08** | `"null"` | Origine sandbox iframe non fiable | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-09** | `None` | En-tête d'origine manquant | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-10** | `ftp://localhost` | Protocole non HTTP/HTTPS | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-11** | `javascript:alert(1)` | Pseudo-schéma d'injection | REJET (`False`) | `False` | **PASS** |
| **SEC04-O-12** | `http://localhost` | Origine loopback locale | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-13** | `http://localhost:5173` | Interface Desktop locale Vite | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-14** | `http://127.0.0.1:8080` | Loopback IPv4 standard | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-15** | `http://[::1]:8080` | Loopback IPv6 standard | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-16** | `http://192.168.1.23:8080` | IP privée légitime Classe C | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-17** | `http://10.0.0.5:8080` | IP privée légitime Classe A | ACCEPTÉ (`True`) | `True` | **PASS** |
| **SEC04-O-18** | `http://172.16.0.10:8080` | IP privée légitime Classe B | ACCEPTÉ (`True`) | `True` | **PASS** |

---

## 2. SUITE 2 : PROTOCOLE D'APPAIRAGE CRYPTOGRAPHIQUE PAIRINGMANAGER (SEC-04)

| ID Test | Scénario de Test | Vecteur / Condition | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC04-P-01** | Génération de PIN éphémère | `generate_pairing_code()` | 6 chiffres décimaux | 6 chiffres décimaux | **PASS** |
| **SEC04-P-02** | Rejet de tentative erronée | Soumission `"000000"` | Rejet (`False`) | `False` | **PASS** |
| **SEC04-P-03** | Consommation du code légitime | Soumission du PIN actif | Validation (`True`) | `True` | **PASS** |
| **SEC04-P-04** | Protection anti-rejeu (Usage unique) | Re-soumission du même PIN | Rejet immédiat (`False`) | `False` | **PASS** |
| **SEC04-P-05** | Verrouillage anti-brute force | 5 échecs consécutifs | Invalidation totale du code | Invalidation observée | **PASS** |
| **SEC04-P-06** | Expiration temporelle TTL (120s) | Soumission après dépassement TTL | Rejet pour code expiré | `False` | **PASS** |

---

## 3. SUITE 3 : GESTION DES SESSIONS & RÉVOCATION (SEC-04)

| ID Test | Scénario de Test | Vecteur / Condition | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC04-S-01** | Vérification de session valide | `session_id` + `token` valides | `verify_session == True` | `True` | **PASS** |
| **SEC04-S-02** | Rejet de jeton invalide | Jeton erroné sur session existante | `verify_session == False` | `False` | **PASS** |
| **SEC04-S-03** | Rejet d'identifiant inconnu | Session inexistante | `verify_session == False` | `False` | **PASS** |
| **SEC04-S-04** | Session desktop locale | Session de démarrage en mémoire | Session active et vérifiée | Active et vérifiée | **PASS** |
| **SEC04-S-05** | Révocation explicite | Appel `revoke_session(s_id, token)` | Session révoquée / refusée | Refusée après révocation | **PASS** |

---

## 4. SUITE 4 : CONTRÔLEUR D'ACTIONS SYSTÈME & FILTRES LINGUISTIQUES (SEC-03)

| ID Test | Phrase / Commande Testée | Contexte / Session | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC03-T-01** | « Je pense éteindre mon PC » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-02** | « J'hésite à éteindre mon ordinateur » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-03** | « J'aimerais peut-être éteindre le pc » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-04** | « Est-ce que tu dois éteindre la machine ? » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-05** | « Faudrait-il redémarrer l'ordi ? » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-06** | « Pourquoi éteindre le pc ? » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-T-07** | « Si j'éteins mon ordinateur, que se passe-t-il ? » | Session 1 | Ignoré (`None`) | `None` | **PASS** |
| **SEC03-C-01** | « éteins mon pc » | `sess_alpha` | Déclenchement 2FA (30s) | Prompt 2FA émis | **PASS** |
| **SEC03-C-02** | Vérification de stockage d'état | `sess_alpha` | Action stockée dans `pending_actions` | Présente dans dict | **PASS** |
| **SEC03-C-03** | « confirmer l'extinction » (Tentative croisée) | `sess_beta` | REJET : Session non autorisée | Rejet croisé avec audit | **PASS** |
| **SEC03-C-04** | « confirmer le redémarrage » (Ambiguïté) | `sess_alpha` | REJET : Désambiguïsation requise | Confirmation ambiguë rejetée | **PASS** |
| **SEC03-C-05** | Conservation après ambiguïté | `sess_alpha` | Action d'extinction préservée | Action toujours en attente | **PASS** |
| **SEC03-C-06** | « confirmer l'extinction » (Légitime) | `sess_alpha` | Validation et exécution DRY-RUN | Exécution validée | **PASS** |
| **SEC03-C-07** | Nettoyage post-confirmation | `sess_alpha` | Action supprimée de l'état | Dict nettoyé | **PASS** |
| **SEC03-C-08** | « redémarre l'ordinateur » puis « annuler » | `sess_gamma` | Annulation confirmée | Opération annulée | **PASS** |
| **SEC03-C-09** | Nettoyage post-annulation | `sess_gamma` | Action supprimée de l'état | Dict nettoyé | **PASS** |

---

## 5. SUITE 5 : CONCURRENCE ET INTÉGRITÉ DE LA MÉMOIRE (SEC-06)

| ID Test | Scénario de Test | Paramètres / Charge | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC06-M-01** | Écriture via `memory_add` | Clé/Valeur sous `MEMOIRE_LOCK` | Succès écriture atomique | `True` | **PASS** |
| **SEC06-M-02** | Lecture via `charger_memoire` | Relecture immédiate | Donnée conforme en mémoire | Valeur exacte lue | **PASS** |
| **SEC06-M-03** | Suppression floue `memory_forget` | Recherche insensible à la casse | Suppression réussie | `True` | **PASS** |
| **SEC06-M-04** | Vérification post-suppression | Relecture mémoire | Clé totalement absente | Clé absente | **PASS** |
| **SEC06-M-05** | Concurrence multi-thread | 30 threads d'écriture simultanés | 0 corruption, 30 faits enregistrés | 30 faits enregistrés | **PASS** |
| **SEC06-M-06** | Intégration RAG `charger_contexte_rag` | Lecture sous verrou | Contexte RAG structuré | Contexte généré | **PASS** |

---

## 6. SUITE 6 : VÉRITÉ OPÉRATIONNELLE HOME ASSISTANT (SEC-05)

| ID Test | Scénario Testé | Réponse Service HA / État Physique | Annonce ALICE Attendue | Annonce ALICE Observée | Verdict |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SEC05-HA-01** | Armement alarme vérifié | HTTP 200 + `state: armed_away` | Confirmation avec état physique | Alarme armée avec succès. État de la centrale vérifié : armed_away. | **PASS** |
| **SEC05-HA-02** | Armement alarme indéterminé | HTTP 200 + `state: unknown` | Avertissement d'état indéterminé | Ordre d'armement transmis, mais l'état physique reste indéterminé. | **PASS** |
| **SEC05-HA-03** | Erreur serveur Home Assistant | HTTP 500 Server Error | Notification d'échec de commande | Impossible d'armer l'alarme : la requête a échoué. | **PASS** |
| **SEC05-HA-04** | Désarmement alarme vérifié | HTTP 200 + `state: disarmed` | Confirmation physique de désarmement | Alarme désarmée avec succès. État physique confirmé. | **PASS** |

---

## 7. SUITE 7 : NON-RÉGRESSION SÉCURITÉ STATIQUE ET CONFINEMENT (SEC-01 & SEC-02)

| ID Test | Domaine | Payload Soumis | Résultat Attendu | Résultat Observé | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC01-NR-01** | Sécurité AST | `import os; os.system('calc')` | Rejet statique (`success: False`) | Rejeté (`DISABLED_FOR_SECURITY`) | **PASS** |
| **SEC01-NR-02** | Sécurité AST | `exec('print(1)')` | Rejet statique (`success: False`) | Rejeté (`DISABLED_FOR_SECURITY`) | **PASS** |
| **SEC01-NR-03** | Sécurité AST | `eval('2+2')` | Rejet statique (`success: False`) | Rejeté (`DISABLED_FOR_SECURITY`) | **PASS** |
| **SEC01-NR-04** | Sécurité AST | `import subprocess; subprocess.Popen('whoami')` | Rejet statique (`success: False`) | Rejeté (`DISABLED_FOR_SECURITY`) | **PASS** |
| **SEC01-NR-05** | Sécurité AST | `x = 1 + 2\nprint(x)` | Code pur autorisé | Validé sans exécution hôte | **PASS** |
| **SEC02-NR-01** | Path Traversal | `../../etc/passwd` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |
| **SEC02-NR-02** | Path Traversal | `..\..\windows\system32\cmd.exe` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |
| **SEC02-NR-03** | Path Traversal | `normal_file.txt` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |
| **SEC02-NR-04** | Path Traversal | `test..file.pdf` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |
| **SEC02-NR-05** | Path Traversal | `/root/.bashrc` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |
| **SEC02-NR-06** | Path Traversal | `../../../boot.ini` | Confinement strict `temp_uploads` | Confiné dans répertoire | **PASS** |

---

## 8. SYNTHÈSE STATISTIQUE

- **Nombre total d'épreuves :** 66
- **Épreuves réussies :** 66
- **Épreuves partielles :** 0
- **Épreuves échouées :** 0
- **Taux de couverture et succès :** **100.0%**
