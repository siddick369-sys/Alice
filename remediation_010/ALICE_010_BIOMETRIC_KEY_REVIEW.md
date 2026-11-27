# ALICE_010 — REVUE DE LA CLÉ BIOMÉTRIQUE ÉPHÉMÈRE (F08)

- **Finding :** `F08` — Clé AES-256 éphémère dans `alice_core/voice/voice_id.py` lorsque `ALICE_BIOMETRIC_KEY_B64` est absente
- **Statut :** `ACCEPTED_RISK` *(défaut de disponibilité documenté, comportement fail-safe)*

## Analyse du cycle de vie
- Si `ALICE_BIOMETRIC_KEY_B64` est fournie, les empreintes spectrales chiffrées AES-256-GCM persistent entre redémarrages.
- Si elle est absente, `VoiceIDManager` génère `os.urandom(32)` en mémoire vive uniquement : aucune clé en clair n'est écrite sur disque, et les anciens profils deviennent illisibles au redémarrage (repli vers `GUEST`).
- **Recommandation :** Ne jamais écrire la clé en clair sur disque ; en production, injecter `ALICE_BIOMETRIC_KEY_B64` (32 octets encodés Base64) via le gestionnaire de secrets de l'OS ou le coffre-fort matériel, et rejeter les clés de longueur inférieure à 32 octets plutôt que de les compléter par zéros.
