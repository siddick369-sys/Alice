# 🛡️ ALICE — RAPPORT D'AUDIT CONTRADICTOIRE INDÉPENDANT GATE 006
## ÉVALUATION DE SÉCURITÉ P1, ANALYSE FORENSIQUE ET VÉRIFICATION DES PREUVES

**Mission ID :** `ALICE-P1-HARDENING-006-INDEPENDENT-ACCEPTANCE-AND-EVIDENCE-VERIFICATION`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Mission auditée :** `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006`  
**Socle de référence :** `ALICE-P0-FINAL-CERTIFICATION-GATE-005`  
**Classification :** AUDIT CONTRADICTOIRE INDÉPENDANT (STRICT READ-ONLY)  
**Date :** 24 Novembre 2026  
**Auditeur :** Independent Security Auditor  

---

## 1. MANDAT ET INDÉPENDANCE DE L'AUDIT

La mission d'acceptation indépendante `GATE 006` a été diligentée avec une règle formelle : **ne pas considérer les déclarations de la mission précédente comme des faits acquis**, mais chercher activement à réfuter les affirmations techniques à l'aide de preuves forensiques, de re-jeux de tests en boîte blanche et d'analyses de chemins d'exécution.

Le rapport de la mission 006 déclarait notamment :
- 109/109 tests validés (86 P0 + 23 P1) ;
- Décision : `APPROVED_FOR_PRODUCTION_EXPOSURE` ;
- Clôture définitive des risques `RISK-P1-BIND-ALL-INTERFACES-8080` et `RISK-P1-LOCALSTORAGE-TOKEN` ;
- Robustesse face aux déploiements en reverse proxy (Topologies A et B).

L'audit contradictoire révèle que, bien que des améliorations significatives aient été apportées (absence de régression P0, CSP solide, éradication des puits XSS dans l'interface mobile, suppression des tokens dans `localStorage`), **des failles de conception critiques subsistent dès lors que l'application est placée derrière un reverse proxy en production**.

---

## 2. SYNTHÈSE DES CONSTATATIONS CRITIQUES

```
+------------------------------------------------------------------------------------------------+
| SYNTHÈSE DE L'AUDIT INDÉPENDANT GATE 006                                                      |
+------------------------------------------------------------------------------------------------+
| Domaine                              | Statut       | Gravité      | Impact                     |
+--------------------------------------+--------------+--------------+----------------------------+
| Identification du Dépôt              | PASS         | N/A          | Clarifié (dossier interne) |
| Réconciliation Tests P0              | PASS         | INFO         | 86/86 PASS (Timeout réglé) |
| Analyse des Tests P1                 | PARTIAL      | MOYENNE      | 23/23 Unitaires (0 réseau) |
| Cookie HttpOnly & Attribut Secure    | FAIL         | ÉLEVÉE       | Secure omis sous proxy TLS |
| Authentification WebSocket           | FAIL         | CRITIQUE     | Bypass loopback sous proxy |
| Incompatibilité Guide Déploiement    | FAIL         | ÉLEVÉE       | Crash Fail-Closed en prod  |
| En-têtes CSP & Sinks XSS             | PASS         | FAIBLE       | Robuste, 0 sink actif      |
+--------------------------------------+--------------+--------------+----------------------------+
```

### 2.1. Faille Critique : Contournement d'Authentification WebSocket sous Reverse Proxy (Topologie A)
- **Localisation :** `Jarvis Final - SITE/main2.py`, lignes 950-963 (`ws_handler`).
- **Mécanisme :**
  Lorsqu'ALICE est déployée derrière un reverse proxy local (Topologie A : Nginx/Caddy sur port 443 transférant vers `127.0.0.1:8765`), l'adresse socket immédiate vue par le serveur Python est `127.0.0.1`.
  `ws_handler` évalue `client_ip = websocket.remote_address[0]`, fixant `is_loopback = True`.
  Puis le code applique :
  ```python
  if is_loopback and (not origin or WS_SESSION_MANAGER.is_origin_allowed(origin)):
      authenticated = True
      session_id = "desktop_local"
      websocket.session_id = session_id
  ```
  Comme l'en-tête `Origin` transmis par le navigateur légitime est le nom de domaine autorisé du proxy, **tout attaquant externe non authentifié se voit automatiquement attribuer les privilèges `desktop_local` sans jamais fournir de cookie, de session ou de code PIN**.
- **Cause racine :** `ws_handler` omet d'appeler `get_trusted_client_ip` pour démasquer l'IP cliente réelle avant d'accorder l'exemption de confiance de bouclage.

### 2.2. Faille Élevée : Absence de l'attribut `Secure` sur les cookies derrière Reverse Proxy
- **Localisation :** `Jarvis Final - SITE/main2.py`, ligne 4695.
- **Mécanisme :**
  L'attribut `Secure` n'est injecté que si `is_secure` est vrai :
  ```python
  is_secure = (get_transport_security_mode() in ("TLS_ENFORCED_PRODUCTION", "TLS_ACTIVE_DEVELOPMENT"))
  secure_flag = "; Secure" if is_secure else ""
  ```
  Or, sous reverse proxy terminating TLS, la liaison backend est en clair (`http://127.0.0.1:8080`), donc `get_transport_security_mode()` renvoie `DEVELOPMENT_PLAINTEXT_DEGRADED`. Le backend ne vérifie pas `X-Forwarded-Proto: https`. En conséquence, le cookie `alice_session` est émis sans le drapeau `; Secure`, permettant son transit en clair sur des réseaux non chiffrés si le proxy ne réécrit pas les en-têtes Set-Cookie.

### 2.3. Faille Élevée : Crash Fail-Closed lors de l'application du Guide de Déploiement
- **Localisation :** `ALICE_P1_HARDENING_006_DEPLOYMENT_GUIDE.md` vs `main2.py` (ligne 4817).
- **Mécanisme :**
  Le guide de déploiement préconise de positionner `JARVIS_ENV=production` et `ALICE_REQUIRE_TLS=1` pour la Topologie A avec reverse proxy Nginx. Or, dans `main2.py`, la fonction `get_transport_security_mode()` exige des fichiers de certificats locaux (`cert.pem`, `key.pem`) sous peine de basculer en `FAIL_CLOSED_TLS_REQUIRED`.
  Lorsque `FAIL_CLOSED_TLS_REQUIRED` est actif, `start_mobile_http_server()` et `start_ws()` refusent catégoriquement de démarrer et coupent les serveurs par sécurité. Une installation suivant strictement le guide de déploiement ne peut pas démarrer.

---

## 3. TABLEAU RÉCAPITULATIF DES DOMAINES DE VÉRIFICATION

| Domaine d'Audit | Statut | Justification Forensique |
| :--- | :---: | :--- |
| **Dépôt & Chemins** | **PASS** | `Jarvis Final - SITE` est un sous-dossier du dépôt `Jarvis Final - SITE-V2`. Aucun dépôt fantôme. |
| **Non-régression P0** | **PASS** | 86/86 tests PASS reproduits avec succès en boîte blanche (Exit Code 0). |
| **Tests P1** | **PARTIAL** | 23/23 tests unitaires PASS, mais 0 test réseau en conditions réelles d'écoute socket. |
| **Cookies de Session** | **FAIL** | Host-only et HttpOnly respectés, mais drapeau `Secure` conditionné de manière défaillante sous proxy. |
| **WebSocket Auth** | **FAIL** | Vulnérabilité de bypass d'authentification sur boucle locale induite par proxy. |
| **Isolation Réseau** | **PARTIAL** | Liaison `127.0.0.1` fonctionnelle en code, mais non testée avec pare-feu système ou proxy réel. |
| **CSP & XSS** | **PASS** | CSP conforme et stricte ; 0 puits XSS non assaini détecté dans le frontend mobile. |

---

## 4. DÉCISION DE L'AUDIT INDÉPENDANT

En raison des deux failles de conception affectant directement l'exposition derrière reverse proxy (Topologies A et B) :

$$\mathbf{VERDICT : CONDITIONALLY\_APPROVED \quad (\text{USAGE LOCAL / STAGING SEULEMENT})}$$

$$\mathbf{STATUT POUR EXPOSITION PRODUCTION PUBLIQUE : REJECTED}$$

Une homologation pour exposition directe sur un réseau public (`APPROVED_FOR_PRODUCTION_EXPOSURE`) **ne peut pas être accordée** tant que le bypass d'authentification WebSocket et la gestion de `X-Forwarded-Proto` ne sont pas corrigés et testés avec un proxy réel.
