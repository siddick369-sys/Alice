# ALICE_010 — REVUE SSRF & DNS REBINDING (F05)

- **Finding :** `F05` — Risque DNS Rebinding (TOCTOU), port `8080` autorisé et `userinfo` accepté dans `alice_web_guard.py`
- **Statut :** `FIXED_VERIFIED`

## 1. Corrections appliquées
- **`Jarvis Final - SITE/alice_web_guard.py` :**
  - Rejet explicite de `userinfo` (`parsed.username`, `parsed.password`, `@` dans `netloc`).
  - Restriction de `ALLOWED_PORTS` à `{80, 443}` (retrait de `8080`, qui exposait le port HTTP local d'ALICE sans besoin métier pour l'agent Web externe).
  - Déballage `ipv4_mapped` (`::ffff:127.0.0.1`) et rejet des plages multicast/unspecified.
  - Nouvelle méthode `resolve_and_validate_url(url)` retournant `(ok, reason, validated_ips)`.
- **`Jarvis Final - SITE/alice_core/automation/web_agent.py` :**
  - Ajout de `_pin_dns_to_validated_ips()` épinglant `urllib3.util.connection.create_connection` sur l'IP déjà validée pour chaque saut de redirection, éliminant la double résolution DNS (TOCTOU) tout en préservant l'en-tête `Host` et la vérification TLS/SNI.

## 2. Preuves
- `TestF05SSRFHardening` (`2/2 PASS`) dans `tests/security/test_p1_remediation_010_adversarial.py` + `6/6 PASS` dans `test_web_guard.py`.
