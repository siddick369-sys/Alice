# ALICE_013_BROWSER_FUNCTIONAL_TESTS.md
## Validation Fonctionnelle Détaillée en Navigateur Réel — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  

---

### 1. Parcours Testés sur l'Interface Mobile PWA (`http://127.0.0.1:8080/index.html`)

- **Chargement initial & Assets :**
  - Requêtes HTTP pour `index.html`, `style.css`, `orb.js`, `app.js`, `manifest.json` : Toutes retournent `200 OK`.
  - Console JavaScript : `0` erreur non gérée après application du fallback `orb.js` de la Mission 012.
- **Boutons & Tiroirs Modaux :**
  - **Tiroir Notes Hors-Ligne (`📝`) :** Ouverture fluide, affichage du statut `Prêt`, champs de saisie titre/contenu et boutons de synchronisation.
  - **Modale Observabilité (`⚙️`) :** Requête vers `GET /api/ops/metrics`. Avant appairage, renvoie `401 Unauthorized` et affiche correctement le message `"Authentification requise."`.
  - **Modale d'Appairage (`#pairing-modal`) :** Saisie d'un code PIN à 6 chiffres, gestion des messages d'erreur si code invalide, et fermeture sur succès.

---

### 2. Parcours Testés sur l'Interface Desktop WebGL (`http://localhost:5173/`)

- **Rendu WebGL Three.js :**  
  - Le canvas 3D initialise le shader et le système de particules avec succès.
  - L'état de connexion affiche `A.L.I.C.E · connecte`.
- **Commandes & Interactivité :**  
  - Envoi de texte via le champ de commande (`#command-input`) transmis sur WebSocket sous le format `{"type": "mobile_command", "text": "..."}`.
  - Bouton Mute (`#mute-button`) envoyant le signal `{"type": "barge_in"}`.
  - Téléversement de fichier document/image (`#file-upload`) encodé en Base64 et transmis sous `{"type": "file_upload", ...}`.

---

### 3. Comportement Face aux Fournisseurs IA Externes Dégradés / Hors-Ligne

- Lorsque les API externes (Gemini, Groq, Bing Edge-TTS) sont inaccessibles en environnement réseau restreint :
  - Le serveur affiche un avertissement au démarrage sans interrompre les services locaux.
  - Edge-TTS bascule automatiquement sur le moteur local SAPI5 `pyttsx3`.
  - L'interface ne se fige pas et maintient les boucles de synchronisation et de diagnostic actives.
