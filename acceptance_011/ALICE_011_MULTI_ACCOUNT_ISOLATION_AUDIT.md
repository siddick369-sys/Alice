# ALICE_011 — AUDIT ISOLATION MULTI-COMPTES INDEXEDDB (F01)

- **Statut F01 :** **`FIXED_VERIFIED`**
- **Inspection statique (`Jarvis Final - SITE/mobile/app.js` & `main2.py`) :**
  - `main2.py` (`/api/pair`) renvoie `user_id` et `role` issus de `RBAC.get_principal(new_session_id)`.
  - `app.js` isole chaque compte dans une base dédiée `aliceOfflineDB_<ownerId>` (v2, index `by_owner`) et filtre chaque `idbGetAll`/`idbPut` par `owner_id === expectedOwner`.
  - `transitionAccountContext()` incrémente `accountEpoch`, active `accountTransitionLock`, purge `notes`/`pending_ops`, supprime la base précédente et `aliceOfflineDB` v1 lors du logout, `auth_error`, WS `4001`/`4003` ou changement de compte.
  - `sw.js` exclut `/api/*` et toute méthode non-`GET` du cache.
- **Preuve adversariale (`test_p1_remediation_010_adversarial.py`, Node.js v24.11.0) :**
  - Scénario A→B : `0` note et `0` opération en attente accessibles à B.
  - Callback tardif de l'époque A après transition vers B : rejeté par `expectedEpoch !== accountEpoch`.
