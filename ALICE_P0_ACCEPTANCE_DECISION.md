# DÉCISION OFFICIELLE D'HOMOLOGATION DE SÉCURITÉ P0

**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Référence de mission :** ALICE-P0-INDEPENDENT-ACCEPTANCE-002  
**Auditeur :** Principal Security Architect & Lead Vulnerability Researcher  
**Date d'émission :** 22 Novembre 2026  
**Décision finale d'acceptation :** **REJETÉE (`REJECTED`)**  

---

## 1. DÉCISION FORMELLE

Après audit contradictoire approfondi, analyse statique du code source, examen de l'infrastructure d'exécution et soumission de l'application à un banc de test adversarial de 57 épreuves, la décision officielle est :

$$\mathbf{STATUT\quad:\quad REJETÉ\quad(REJECTED)}$$

Le système J.A.R.V.I.S / ALICE (SITE-V2) **ne peut pas être homologué en l'état** pour un usage de production ou une exposition réseau, en raison de vulnérabilités critiques non résolues et d'une régression bloquante introduite lors de la remédiation.

Conformément à la clause 14 de l'ordre de mission :
> *« Un seul échec critique suffit à empêcher l'acceptation globale. »*

---

## 2. JUSTIFICATION DOMAINE PAR DOMAINE

| Domaine | Intitulé | Statut | Justification Technique Synthétique |
| :---: | :--- | :---: | :--- |
| **SEC-01** | Neutralisation RCE | **PASS** *(avec réserves)* | L'exécution dynamique de code arbitraire sur l'hôte a été supprimée (`subprocess.run` éliminé). L'analyse statique AST filtre les modules système évidents, bien qu'elle ne constitue pas un sandbox complet si l'exécution venait à être rétablie. |
| **SEC-02** | Uploads & Path Traversal | **PASS** | Confinement strict dans `temp_uploads/`, normalisation par nom de base, préfixe UUID v4 et whitelist d'extensions résistants aux 18 vecteurs de traversée. La réception des frames vidéo est découplée de l'upload. |
| **SEC-03** | Commandes Système PC | **PARTIAL** | La suppression du mot-clé naïf « eteins » élimine les arrêts involontaires. Cependant, `pending_action` est un état global sans isolation de session, permettant à un client réseau de valider ou annuler l'arrêt initié par un autre utilisateur. De plus, la formulation « Je pense éteindre mon PC » déclenche à tort la demande 2FA. |
| **SEC-04** | WebSocket & Auth | **FAIL** *(Bloquant)* | **Vulnérabilité critique majeure :** L'endpoint HTTP `/api/auth/token` est publiquement exposé sur `0.0.0.0:8080` sans authentification avec `Access-Control-Allow-Origin: *`, permettant la fuite totale du jeton de session. De plus, la politique d'origine est contournable via des domaines comme `192.168.attacker.com`. Enfin, le client `mobile/app.js` est devenu inopérant car il ne transmet pas de jeton et se fait rejeter toutes les 5 secondes. |
| **SEC-05** | Vérité Domotique | **PARTIAL** | Les codes d'erreur et timeouts Home Assistant sont convenablement détectés et annoncés. Toutefois, la réception d'un code HTTP 200 est assimilée à une confirmation d'état physique réel (`STATE_VERIFIED`), ce qui constitue une fausse assurance pour les actions de sécurité critiques (alarmes). |
| **SEC-06** | Intégrité Mémoire | **FAIL** *(Bloquant)* | Bien que `sauvegarder_memoire` et `construire_contexte_memoire` aient été protégés, les fonctions `memory_add` et `memory_forget` (L2106 et L2126), activement sollicitées par le routeur IA, écrivent directement sur le fichier mémoire sans acquérir `MEMOIRE_LOCK` et sans écriture atomique, réintroduisant le risque de corruption de données en concurrence. |

---

## 3. IMPACT SUR LE RAPPORT ANTÉRIEUR (ALICE_P0_REMEDIATION_REPORT.md)

Le rapport `ALICE_P0_REMEDIATION_REPORT.md` affirmait :
- *« 100% DES VULNÉRABILITÉS P0 NEUTRALISÉES ET VALIDÉES »*
- *« 25/25 TESTS RÉUSSIS »*

L'audit contradictoire infirme cette conclusion :
1. Les 25 tests du banc précédent comprenaient 10 tests de fonctions isolées ou de manipulation de chaînes (ex. `os.path.basename`) qui n'évaluaient pas les flux réels du serveur WebSocket complet.
2. Le banc de test précédent n'a pas audité l'endpoint de distribution du jeton `/api/auth/token` ni les contournements DNS d'origine (`192.168.attacker.com`).
3. Le banc précédent n'a pas vérifié l'implémentation effective du client mobile, occultant sa rupture opérationnelle complète.
4. Le banc précédent a omis d'auditer les fonctions mémorielles concurrentes `memory_add` et `memory_forget`.

---

## 4. CONDITIONS PRÉALABLES À UNE NOUVELLE COMMISSION D'ACCEPTATION

Pour qu'une nouvelle mission d'homologation puisse conclure à un avis favorable (`ACCEPTED`), les actions correctives suivantes doivent être impérativement menées dans le cadre d'un nouveau chantier contrôlé :

1. **Suppression de la faille de distribution du jeton :** Retirer `/api/auth/token` ou le conditionner à une authentification préalable forte (ex. code d'appairage à usage unique).
2. **Correction de la validation IP/Origine :** Remplacer le test `host.startswith(...)` par `ipaddress.ip_address(host).is_private`.
3. **Mise à niveau du client mobile :** Implémenter le protocole d'authentification dans `mobile/app.js`.
4. **Unification et verrouillage de la mémoire :** Rediriger `memory_add` et `memory_forget` vers les fonctions thread-safe `ajouter_memoire` et `supprimer_memoire` sous `MEMOIRE_LOCK`.
5. **Isolation de session 2FA :** Lier `pending_action` à l'adresse IP et à la session de l'émetteur pour empêcher toute validation croisée non autorisée.

*Fait à Paris, le 22 Novembre 2026.*  
*Pour la Commission d'Audit et de Sécurité Logicielle.*
