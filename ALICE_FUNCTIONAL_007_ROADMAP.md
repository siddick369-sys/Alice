# 🗺️ ALICE — FEUILLE DE ROUTE D'ÉVOLUTION FONCTIONNELLE
## ROADMAP OPÉRATIONNELLE PAR LOTS INDÉPENDANTS

**Mission ID :** `ALICE-FUNCTIONAL-PLATFORM-EVOLUTION-007`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  
**Classification :** STRATÉGIE PRODUIT & PLAN D'EXÉCUTION  

---

## 1. MATRICE D'ÉVALUATION ET DE PRIORISATION DES LOTS

| Lot | Domaine Fonctionnel | Valeur Utilisateur | Impact Produit | Risque Technique | Dépendances Externes | Complexité | Score Priorité | Sélection & Ordonnancement |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LOT A** | **Assistant Central & Orchestration** | Maximale (5/5) | Majeur (5/5) | Faible (1/5) | Aucune | Modérée (3/5) | **19 / 20** | **LOT PRIORITAIRE N°1 (Socle)** |
| **LOT E** | **Application Mobile & Multimodal** | Maximale (5/5) | Majeur (5/5) | Faible (2/5) | Backend Lot A | Modérée (3/5) | **18 / 20** | **LOT N°1B (Front Mobile)** |
| **LOT B** | **Mémoire Persistante & RAG Hybride**| Élevée (4/5) | Élevé (4/5) | Faible (1/5) | Fichiers locaux | Moyenne (3/5) | **17 / 20** | **LOT N°2 (Intelligence & Contexte)** |
| **LOT C** | **Agent Web & Recherche Sécurisée** | Élevée (4/5) | Élevé (4/5) | Modéré (3/5) | Réseau Web / SerpAPI| Moyenne (3/5) | **15 / 20** | **LOT N°3 (Recherche & Anti-SSRF)** |
| **LOT D** | **Google Workspace & Intégrations** | Moyenne (3/5) | Modéré (3/5) | Élevé (4/5) | OAuth2 Google | Élevée (4/5) | **12 / 20** | **LOT N°4 (Adaptateur Découplé)** |
| **LOT F** | **OCR & Compréhension Documents** | Moyenne (3/5) | Modéré (3/5) | Faible (2/5) | Tesseract local | Moyenne (3/5) | **14 / 20** | **LOT N°5 (Vision & Extraction)** |
| **LOT G** | **Automatisation & Workflows** | Moyenne (3/5) | Modéré (3/5) | Modéré (3/5) | Scheduler local | Élevée (4/5) | **12 / 20** | **LOT N°6 (Moteur d'automatisation)** |
| **LOT H** | **Vidéosurveillance & Domotique** | Faible (2/5) | Faible (2/5) | Élevé (5/5) | Matériel physique | Élevée (4/5) | **8 / 20** | **LOT N°7 (Stabilisé en lecture seule)** |
| **LOT I** | **Fiabilité & Observabilité** | Élevée (4/5) | Majeur (5/5) | Faible (1/5) | Logs / Métriques | Faible (2/5) | **18 / 20** | **TRANSVERSAL (Intégré aux lots)** |

---

## 2. ARBITRAGE DU PREMIER LOT D'IMPLÉMENTATION

> ### 🎯 CHOIX FORMEL : **LOT A (Assistant Central & Orchestration) + LOT E (Application Mobile Multimodale)**
> 
> **Justification méthodologique :**  
> L'audit forensique a établi sans équivoque que le backend exécute les commandes sans aucun accusé de réception ou statut d'étape vers les interfaces utilisateurs. Implémenter le contrat de cycle de vie en 9 états sur le backend (Lot A) et l'interfacer immédiatement avec l'application mobile (Lot E) offre la valeur utilisateur et la fiabilité produit les plus élevées, tout en présentant un risque de régression minime vis-à-vis des contrôles P0 existants.
> 
> De surcroît, le **LOT B (Mémoire & RAG)** sera immédiatement enchaîné pour doter l'assistant d'un moteur documentaire local robuste et autonome, sans dépendre de clés tierces ou de chargements en mémoire volatils.

---

## 3. PHASAGE DÉTAILLÉ DE L'EXÉCUTION

### Phase 1 — Socle d'Orchestration et Contrat de Commande (Lot A + Transversal I)
1. **Création du module `alice_orchestrator.py` :**
   - Classe `CommandLifecycleManager` gérant les 9 états formels (`RECEIVED`, `VALIDATING`, `ACCEPTED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `CANCELLED`, `REQUIRES_CONFIRMATION`).
   - Génération d'identifiants de corrélation (`trace_id`, `command_id`).
   - Détection et rejet des commandes dupliquées (fenêtre d'idempotence de 10 secondes).
   - Enregistrement des transitions d'états dans un journal d'événements structuré.
2. **Intégration dans `main2.py` :**
   - Raccordement du gestionnaire de cycle de vie dans `ws_handler` et `traiter_reponse_ia`.
   - Émission continue des messages WebSocket `command_lifecycle` vers les clients connectés.
   - Gestion stricte des timeouts par action avec bascule en état `FAILED` ou `UNKNOWN` sans freeze du serveur.

### Phase 2 — Expérience Mobile Réactive et Multimodale (Lot E)
1. **Mise à niveau de `mobile/app.js` & `mobile/index.html` :**
   - Ajout d'une barre de statut d'action dynamique (`#action-status-pill`) reflétant les 9 états en temps réel.
   - Ajout d'une modale de confirmation interactive (`#confirm-action-modal`) avec boutons valider/annuler pour les actions sensibles.
   - Ajout d'une gestion anti-double clic / anti-rebond sur le microphone et la saisie de commande.
   - Affichage visuel des erreurs avec messages explicatifs non anxiogènes.

### Phase 3 — Rénovation de la Mémoire et du RAG Local (Lot B)
1. **Création du module `alice_rag.py` :**
   - Ingestion multi-formats : texte brut, PDF (`PyPDF2`), et tableurs Excel (`openpyxl` pour `knowledge/Classeur1.xlsx`).
   - Moteur TF-IDF et N-grammes local sans dépendance externe obligatoire.
   - Index persistant sur disque (`knowledge/rag_index.json`).
   - Étiquetage de provenance et citations strictes dans les réponses IA.
   - Isolation de session et neutralisation des prompts malveillants présents dans les documents.

### Phase 4 — Adaptateur Sécurisé Web & Google Workspace (Lot C & Lot D)
1. **Module de sécurité Web (`alice_web_guard.py`) :**
   - Validation stricte des URL (schéma HTTP/HTTPS, rejet des adresses privées/boucle locale/métadonnées cloud).
   - Traçabilité des sources trouvées.
2. **Adaptateur Google Workspace (`alice_google_adapter.py`) :**
   - Adaptateur découplé indiquant clairement l'indisponibilité si `token.pickle` est absent, sans bloquer le serveur.
   - Politique d'action exigeant une confirmation utilisateur explicite pour toute création/modification.

### Phase 5 — Validation, Non-Régression & Certification
1. **Création de la suite de tests interne (`tests/`) :**
   - `tests/test_command_lifecycle.py` : Validation des 9 états, idempotence et timeouts.
   - `tests/test_rag_engine.py` : Validation de l'ingestion XLSX/PDF, scoring et provenance.
   - `tests/test_web_guard.py` : Validation anti-SSRF et filtrage des URL.
   - `tests/test_google_adapter.py` : Validation de l'adaptateur sans blocage.
   - `tests/test_regression_p0_gate005.py` : Rapatriement et exécution de la suite de non-régression des 86 tests P0 certifiés.
