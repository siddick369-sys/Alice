# ALICE_011 — AUDIT SSRF & DNS PINNING (F05)

- **Statut F05 :** **`FIXED_VERIFIED`**
- **Inspection (`alice_web_guard.py` & `alice_core/automation/web_agent.py`) :**
  - Rejet de `userinfo` (`username`/`password`/`@` dans `netloc`), retrait du port `8080` (`ALLOWED_PORTS = {80, 443}`), déballage `ipv4_mapped`, rejet multicast/unspecified/loopback/private/link-local/169.254.169.254.
  - `_pin_dns_to_validated_ips()` force `urllib3.util.connection.create_connection` vers l'IP déjà validée pour chaque saut de redirection, en conservant `Host` et SNI/TLS intacts et en bloquant tout hôte inattendu.
- **Preuves (`independent_probe.py` + `TestF05SSRFHardening`) :**
  - 12/12 URLs adversariales rejetées (`localhost`, `127.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]`, `169.254.169.254`, `10.0.0.1`, `user:pass@`, `user%40evil@`, `:8080`, `:8765`, `file:///`, `javascript:`), blocage d'hôte inattendu dans `_pin_dns_to_validated_ips` vérifié.
