# ALICE_010 — RAPPORT D'ISOLATION MULTI-COMPTE INDEXEDDB (F01)

- **Finding :** `F01` — Fuite et synchronisation croisée inter-comptes dans IndexedDB (`aliceOfflineDB`)
- **Statut :** `FIXED_VERIFIED`

## 1. Corrections appliquées (`Jarvis Final - SITE/mobile/app.js` & `main2.py`)
- **`main2.py` (`/api/pair`) :** Inclusion de `user_id` et `role` résolus côté serveur dans la réponse JSON d'appairage.
- **`mobile/app.js` :**
  - Cloisonnement par base dédiée par compte (`aliceOfflineDB_<ownerId>`, schéma v2 avec index `by_owner`) ET filtrage strict `record.owner_id === expectedOwner` à chaque lecture/écriture (`idbPut`, `idbGetAll`).
  - Gestionnaire de transition `transitionAccountContext(newOwnerId)` avec verrou `accountTransitionLock` et compteur d'époque `accountEpoch` : purge `notes`, `pending_ops` et supprime la base précédente et l'ancienne base v1 `aliceOfflineDB` lors du logout, `auth_error`, fermeture WS `4001`/`4003` ou changement de compte.
  - Protection anti-race : tout callback tardif (`expectedEpoch !== accountEpoch || activeAccountId !== expectedOwner`) est rejeté avant toute écriture IndexedDB ou DOM.
  - `syncOfflineNotes()` filtre les opérations sur `op.owner_id === myOwner` et annule l'écriture si `accountEpoch` change pendant `apiFetch`.

## 2. Preuves (`tests/security/test_p1_remediation_010_adversarial.py`)
- `TestF01MultiAccountIndexedDBIsolation.test_01_node_real_account_switch_and_late_callback_isolation` (**PASS** sous Node.js v24.11.0 sur le code réel de `mobile/app.js`) : démontre le cloisonnement A→B (`0` note et `0` op héritées par B) et le rejet d'un callback tardif issu de l'époque de A.
