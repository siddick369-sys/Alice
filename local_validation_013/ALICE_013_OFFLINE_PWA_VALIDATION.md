# ALICE_013_OFFLINE_PWA_VALIDATION.md
## Audit de l'Architecture Hors-Ligne, PWA et Isolation Mémoire — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  

---

### 1. Service Worker (`Jarvis Final - SITE/mobile/sw.js`)

- **Cycle de vie :** `sw.js` intercepte les requêtes de navigation et statiques (`index.html`, `style.css`, `app.js`, `orb.js`, `manifest.json`).
- **Protection des données sensibles :**  
  Toutes les requêtes vers `/api/*` et le protocole WebSocket sont expressément exclues du cache persistant du Service Worker (`networkOnly` ou bypass direct), garantissant qu'aucune donnée privée d'utilisateur n'est stockée dans le cache du navigateur.

---

### 2. Isolation Multi-Comptes dans IndexedDB (`mobile/app.js` — Finding F01)

L'audit de conformité de la correction F01 (Mission 010) confirme les éléments suivants :
- **Bases de données cloisonnées par compte :**  
  Au lieu d'une base globale unique, chaque compte dispose d'une base IndexedDB dédiée nommée `aliceOfflineDB_${resolvedOwner}`.
- **Gestion des transitions & Purge :**  
  Lors d'une déconnexion ou d'un changement de session, la fonction `transitionAccountContext(newOwner)` incrémente le numéro d'époque (`currentAccountEpoch`), ferme les connexions ouvertes et invalide immédiatement les opérations asynchrones en cours.
- **Validation fonctionnelle :** Aucune fuite croisée inter-utilisateurs n'est possible au niveau du stockage local du navigateur.

---

### 3. Synchronisation Hors-Ligne & Idempotence (`/api/sync/notes`)

- **Traitement par lots (`ops`) :** Le protocole supporte les opérations `upsert` et `delete` horodatées.
- **Résistance aux conflits :** Le serveur compare les timestamps `updated_at` pour appliquer la règle du dernier écrivain (*Last-Write-Wins*).
- **Protection CSRF :** L'endpoint `/api/sync/notes` exige strictement un jeton `X-CSRF-Token` valide lorsque l'appel provient d'un navigateur avec en-tête `Origin`, bloquant toute tentative de synchronisation forcée par un tiers.
