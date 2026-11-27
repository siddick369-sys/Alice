# 🛡️ ALICE — REVUE TECHNIQUE DE L'EXPOSITION RÉSEAU ET DES PROXIES
## ANALYSE DES BINDINGS, DÉTECTION DES LISTENERS ET EXAMEN DES REVERSE PROXIES

**Mission ID :** `ALICE-P1-HARDENING-006-INDEPENDENT-ACCEPTANCE-AND-EVIDENCE-VERIFICATION`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Document :** `ALICE_P1_GATE006_NETWORK_EXPOSURE_REVIEW.md`  
**Date :** 24 Novembre 2026  
**Auditeur :** Independent Security Auditor  

---

## 1. REVUE TECHNIQUE DE LA CONFIGURATION DES LIAISONS RÉSEAU

### 1.1. Architecture `NetworkConfig` (`main2.py`)
La centralisation des liaisons réseau via `get_network_config()` (lignes 624-700 de `main2.py`) introduit un paramétrage dynamique des adresses et des ports :

```python
raw_bind = os.environ.get("ALICE_BIND_ADDRESS") or os.environ.get("JARVIS_BIND_ADDRESS") or "0.0.0.0"
raw_http_port = os.environ.get("ALICE_HTTP_PORT") or os.environ.get("JARVIS_HTTP_PORT") or "8080"
raw_ws_bind = os.environ.get("ALICE_WS_BIND_ADDRESS") or os.environ.get("JARVIS_WS_BIND_ADDRESS") or bind_address
raw_ws_port = os.environ.get("ALICE_WS_PORT") or os.environ.get("JARVIS_WS_PORT") or "8765"
raw_proxies = os.environ.get("ALICE_TRUSTED_PROXIES") or "127.0.0.1,::1"
```

### 1.2. Propriétés et Comportements Évalués
1. **Liaison locale de bouclage (`127.0.0.1` / `::1`) :**  
   Prise en charge nativement. Si `ALICE_BIND_ADDRESS=127.0.0.1`, les sockets s'ouvrent uniquement sur l'interface locale de la machine hôte.
2. **Support IPv6 :**  
   Pris en charge via `DualStackHTTPServer` (`address_family = socket.AF_INET6 if ":" in net_cfg.bind_address else socket.AF_INET`).
3. **Résolution de collision de ports :**  
   Si `http_port == ws_port`, le port WebSocket est automatiquement décalé pour éviter l'échec de liaison `EADDRINUSE`.
4. **Filtrage des proxies de confiance :**  
   Parse les adresses IP individuelles et les sous-réseaux CIDR (ex: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.1.0/24`).

### 1.3. Inventaire Exhaustif des Sockets et Listeners
L'audit statique de l'ensemble de l'application confirme que **seuls deux serveurs réseau sont instanciés** :
1. `websockets.serve(ws_handler, net_cfg.ws_bind_address, net_cfg.ws_port, ...)` (ligne 4589).
2. `DualStackHTTPServer((net_cfg.bind_address, net_cfg.http_port), MobileHandler)` (ligne 4828).

Aucun autre listener caché ou service tiers non documenté n'a été identifié. Au repos, `netstat -ano` confirme qu'aucun socket orphelin n'écoute sur les ports 8080 ou 8765.

---

## 2. INCOMPATIBILITÉ CRITIQUE DU GUIDE DE DÉPLOIEMENT PRODUCTION

L'examen contradictoire du document [ALICE_P1_HARDENING_006_DEPLOYMENT_GUIDE.md](file:///c:/Users/USER/Desktop/Jarvis%20Final%20-%20SITE-V2/ALICE_P1_HARDENING_006_DEPLOYMENT_GUIDE.md) révèle une anomalie opérationnelle majeure empêchant le démarrage d'ALICE en Topologie A (Reverse Proxy Local) :

### 2.1. Instructions du Guide de Déploiement
Le guide recommande d'exécuter `start_alice_production.bat` avec la configuration suivante :
```bat
set JARVIS_ENV=production
set ALICE_ENV=production
set ALICE_REQUIRE_TLS=1
set ALICE_BIND_ADDRESS=127.0.0.1
set ALICE_HTTP_PORT=8080
set ALICE_WS_BIND_ADDRESS=127.0.0.1
set ALICE_WS_PORT=8765
set ALICE_TRUSTED_PROXIES=127.0.0.1,::1
```

### 2.2. Réaction du Code Source (`main2.py`)
Au lancement, le backend exécute `get_transport_security_mode()` :
1. `JARVIS_ENV=production` et `ALICE_REQUIRE_TLS=1` indiquent que le mode production est actif.
2. Le backend recherche des certificats locaux dans `certs/cert.pem` et `certs/key.pem`.
3. Dans la Topologie A recommandée, **les certificats TLS sont installés sur Nginx, et non dans le dossier d'ALICE**.
4. En l'absence de certificat local, `get_ssl_context()` renvoie `None`.
5. `get_transport_security_mode()` évalue alors :
   ```python
   elif is_prod:
       return "FAIL_CLOSED_TLS_REQUIRED"
   ```
6. Lors de l'initialisation du serveur mobile et du WebSocket :
   ```python
   if sec_mode == "FAIL_CLOSED_TLS_REQUIRED":
       print("[SECURITY FATAL] Mode production exige HTTPS mais aucun certificat TLS valide n'a été fourni. Serveur mobile HTTP désactivé par sécurité (C-01).")
       return
   ```
7. **RÉSULTAT :** Les deux serveurs se désactivent immédiatement. L'application crash en mode fail-closed.

### 2.3. Conclusion de l'Analyse
La politique C-01 Fail-Closed implémentée dans le code n'a pas été adaptée pour reconnaître qu'une liaison de bouclage (`127.0.0.1`) en aval d'un reverse proxy de confiance constitue un mode de transport sécurisé délégué.
Le guide de déploiement n'a manifestement pas été validé de bout en bout en conditions réelles avec `JARVIS_ENV=production`.

---

## 3. AUDIT DES CONFIGURATIONS REVERSE PROXY PROPOSÉES

### 3.1. Évaluation de la Configuration Nginx
- **Points forts :**
  - Redirection automatique HTTP vers HTTPS (port 80 vers 443).
  - Protocoles stricts `TLSv1.2 TLSv1.3` avec suites de chiffrement modernes.
  - Transmission correcte de `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Proto`.
  - Gestion de l'upgrade WebSocket (`Upgrade` et `Connection "Upgrade"`).
- **Lacunes identifiées :**
  - Absence de directive `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;` dans le bloc serveur Nginx. Comme le backend ALICE n'émet HSTS que si `isinstance(self.server.socket, ssl.SSLSocket)`, aucun en-tête HSTS n'est délivré au client final.
  - Absence de directive `proxy_cookie_flags ~ secure;` pour forcer l'attribut `Secure` sur les cookies émis par le backend.

### 3.2. Évaluation de la Configuration Caddy
- Configuration simple et concise. La terminaison TLS automatique est prise en charge. Les en-têtes `X-Forwarded-Proto` et `X-Forwarded-For` sont transmis par défaut par Caddy.

---

## 4. STATUT DES CONTRÔLES RÉSEAU

| Contrôle | Type de Test | Statut | Justification |
| :--- | :--- | :---: | :--- |
| Parsing des adresses IPv4/IPv6 | Unitaire | **PASS** | Validé par `test_p1_production_exposure_006.py`. |
| Résolution collisions ports | Unitaire | **PASS** | Décalage automatique validé. |
| Rejet XFF non approuvé | Unitaire (Mock) | **PASS** | Validé en mémoire avec faux objets requête. |
| Isolation réseau par pare-feu | Système / Hôte | **NOT_VERIFIED** | Aucun test de règle Windows Firewall ou iptables n'a été conduit. |
| Test réel sous reverse proxy Nginx | Intégration Réseau | **FAIL** | Incompatibilité Fail-Closed + Faille de bypass loopback WebSocket. |
