# 🏗️ ALICE — ARCHITECTURE CIBLE & SPÉCIFICATIONS TECHNIQUES
## PHASE C : TARGET ARCHITECTURE & CONTRACT SPECIFICATIONS

**Mission ID :** `ALICE-FUNCTIONAL-PLATFORM-EVOLUTION-007`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  
**Classification :** ARCHITECTURE & SYSTEM DESIGN  

---

## 1. OBJECTIFS ARCHITECTURAUX ET PRINCIPES DIRECTEURS

L'architecture cible a pour mission de transformer l'existant sans déstabiliser les acquis certifiés P0/P1 :
1. **Séparation des responsabilités :** Découpler le parsing de messages, le routage, l'orchestration des commandes et la couche de transport WebSocket/HTTP.
2. **Contrat de cycle de vie d'action (9 états stricts) :** Remplacer le traitement obscur « fire-and-forget » par un protocole événementiel structuré émis vers les clients (Mobile & Web).
3. **Idempotence et Anti-Rejeu :** Chaque commande possède un `command_id` unique généré ou reçu, empêchant les doubles exécutions accidentelles (double tap sur mobile).
4. **Gestion centralisée des erreurs & Observabilité :** Taxonomie standardisée d'erreurs, identifiants de corrélation (`trace_id`), découplage strict entre pannes externes d'IA et indisponibilités internes.
5. **RAG Hybride Autonome et Vérifiable :** Ingestion multi-formats (texte, PDF, tableurs XLSX), découpage en chunks avec métadonnées précises de provenance, indexation vectorielle/lexicale locale sans dépendance réseau bloquante.
6. **Adaptateur d'Intégration Résilient :** Découplage des services Google Workspace via un adaptateur testable gérant l'absence d'authentification sans bloquer le serveur.
7. **Suite de Tests Intégrée au Dépôt :** Création d'un dossier `tests/` dans le projet, pérennisant les tests unitaires, d'intégration et de sécurité.

---

## 2. MODÉLISATION DU CYCLE DE VIE D'UNE COMMANDE (LOT A)

### 2.1 Les 9 États Formels du Contrat d'Exécution

```
                ┌──────────────┐
                │   RECEIVED   │ (Commande réceptionnée, timestamp & ID attribués)
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │  VALIDATING  │ (Vérification des droits, session, schéma des arguments)
                └──────┬───────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌──────────────┐               ┌───────────────────────┐
│   ACCEPTED   │               │ REQUIRES_CONFIRMATION │ (Action sensible : arrêt, email, domotique critique)
└──────┬───────┘               └───────────┬───────────┘
       │                                   │
       │                     ┌─────────────┴─────────────┐
       │                     ▼                           ▼
       │              ┌──────────────┐            ┌──────────────┐
       │              │   ACCEPTED   │            │  CANCELLED   │ (Refus utilisateur ou timeout de confirmation)
       │              └──────┬───────┘            └──────────────┘
       │                     │
       └──────────────┐      │
                      ▼      ▼
               ┌──────────────┐
               │   RUNNING    │ (Exécution active de l'action avec timeout borné)
               └──────┬───────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐
│  SUCCEEDED   ││    FAILED    ││   UNKNOWN    │ (Statut matériel incertain ou indisponible)
└──────────────┘└──────────────┘└──────────────┘
```

### 2.2 Schéma JSON des Événements WebSocket (`command_lifecycle`)

Chaque transition d'état émet un payload typé et standardisé vers le client initiateur et les clients connectés :

```json
{
  "type": "command_lifecycle",
  "command_id": "cmd_1779549012_a8f9",
  "session_id": "mobile_sess_82f1",
  "action": "ha_lumiere",
  "state": "RUNNING",
  "previous_state": "ACCEPTED",
  "timestamp": 1779549012.45,
  "payload": {
    "piece": "salon",
    "etat": "on"
  },
  "result": null,
  "requires_confirmation": false,
  "confirmation_prompt": null,
  "error": null,
  "trace_id": "tr_628a1c90"
}
```

---

## 3. ARCHITECTURE DE LA MÉMOIRE & DU RAG (LOT B)

### 3.1 Pipeline d'Ingestion Documentaire et Extraction
Le nouveau moteur RAG (`AliceRAGEngine`) prend en charge :
- **Documents Textuels :** `.txt`, `.md`, `.log`, `.csv`, `.json`, `.py`, `.js`.
- **Documents PDF :** Extraction de texte via `PyPDF2` page par page.
- **Tableurs Excel (`.xlsx`) :** Extraction structurée via `openpyxl` (présent dans le venv), convertissant feuilles et lignes en tableaux textuels exploitables.
- **Normalisation & Nettoyage :** Découpage en blocs sémantiques de 400 caractères avec chevauchement de 50 caractères, préservation de l'origine (`source_file`, `sheet_name`/`page_num`, `chunk_id`).

### 3.2 Indexation et Scoring Hybride Local
- **Persistance locale :** Enregistrement de l'index dans `knowledge/rag_index.json` avec hachage SHA-256 des fichiers sources pour indexation incrémentale.
- **Moteur de recherche lexicale & TF-IDF pondéré :** Calcul de pertinence basé sur la fréquence inverse des termes (TF-IDF local) avec pondération des n-grammes (bigrammes/trigrammes).
- **Citations de provenance :** Tout contexte injecté à l'IA inclut des étiquettes formelles de citation : `[Source: Classeur1.xlsx | Feuille: Donnees | Ligne: 12]`.
- **Immunité aux injections promptes RAG :** Le contenu ingéré est encadré par des balises strictes de données non fiables (`<untrusted_document_data>`) avec instruction explicite à l'IA de ne jamais exécuter de commandes contenues dans les documents.

---

## 4. ARCHITECTURE DE SÉCURITÉ DE L'AGENT WEB (LOT C)

```
Requête Web (URL) ──> [ URL Validator & SSRF Guard ]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
      [ REJET IMMÉDIAT ]              [ ACCÈS AUTORISÉ ]
  - Schémas non-HTTP(S)               - Schémas http:// ou https://
  - IPs privées (10.0.0.0/8,          - Domaines résolus publics
    172.16.0.0/12, 192.168.0.0/16,    - Timeout strict (10s)
    127.0.0.0/8, ::1)                 - Taille max téléchargement (5 Mo)
  - Métadonnées cloud                 - Headers isolés
    (169.254.169.254)
```

---

## 5. ARCHITECTURE DU CLIENT MOBILE MULTIMODAL (LOT E)

### 5.1 Composants UI Réactifs
- **Badge d'état d'exécution en temps réel :**
  Un composant UI dédié (`#command-status-bar`) affiche dynamiquement l'état courant de l'action :
  - `VALIDATING` : Témoin clignotant bleu
  - `RUNNING` : Spinner d'activité avec libellé de l'action en cours
  - `REQUIRES_CONFIRMATION` : Boîte de dialogue modale d'autorisation explicite
  - `SUCCEEDED` : Badge vert avec message de confirmation matérielle
  - `FAILED` : Badge rouge avec diagnostic d'erreur non bloquant
- **Modale de Confirmation Interactive (`#action-confirm-modal`) :**
  Pour toute commande système ou action domotique sensible, le client affiche les paramètres de l'action et propose deux boutons : `[Confirmer l'action]` et `[Annuler]`. L'envoi du retour transmet le jeton de confirmation rattaché à la session WebSocket courante.
- **Résilience Réseau & Tampon Hors-Ligne :**
  En cas de coupure de communication WebSocket, la reconnexion automatique réémet les abonnements d'état et affiche un état d'avertissement jaune non bloquant.

---

## 6. ADAPTATEUR GOOGLE WORKSPACE (LOT D)

```python
class GoogleWorkspaceAdapter:
    """Adaptateur découplé pour l'écosystème Google Workspace."""
    def __init__(self, credentials_path: str, token_path: str):
        self.is_authenticated: bool
        self.scopes: list
    def check_availability(self) -> dict: ...
    def create_document(self, title: str, content: str) -> CommandResult: ...
    def read_emails(self, max_results: int) -> CommandResult: ...
    def list_calendar_events(self, days: int) -> CommandResult: ...
```
- Si `token.pickle` est absent, l'adaptateur retourne `status: UNAVAILABLE` avec un message clair : *"Le compte Google n'est pas encore associé. Veuillez exécuter la procédure d'authentification initiale."* Aucune tentative d'ouverture de socket bloquant en arrière-plan n'est effectuée.
- Les actions de modification ou suppression exigent formellement le statut `REQUIRES_CONFIRMATION`.
