# ALICE_011 — AUDIT CLÉ BIOMÉTRIQUE (F08)

- **Statut F08 :** **`ACCEPTED_RISK`**
- **Analyse (`Jarvis Final - SITE/alice_core/voice/voice_id.py`) :**
  - En l'absence d'`ALICE_BIOMETRIC_KEY_B64`, `self._key = os.urandom(32)` est conservée uniquement en mémoire vive (jamais écrite sur disque, jamais loggée, absente de `localStorage`/`sessionStorage`/IndexedDB).
  - La perte au redémarrage est un défaut de disponibilité (repli vers `Role.GUEST`) sans affaiblissement de confidentialité.
  - **Réserve P3 :** Si `ALICE_BIOMETRIC_KEY_B64` est fournie, le code la tronque/complète par `ljust(32, b"\x00")` au lieu de rejeter une clé trop courte ; en Python, la clé en RAM n'est pas effaçable physiquement (`bytes` immuables).
