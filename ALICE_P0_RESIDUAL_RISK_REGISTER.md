# REGISTRE DES RISQUES RÉSIDUELS ET VULNÉRABILITÉS — ALICE / J.A.R.V.I.S

**Mission :** ALICE-P0-INDEPENDENT-ACCEPTANCE-002  
**Date d'établissement :** 22 Novembre 2026  
**Référence d'audit :** ALICE-FORENSIC-AUDIT-001  
**Statut global du système :** RISQUES CRITIQUES RÉMANENTS — NON HOMOLOGUÉ POUR PRODUCTION  

---

## 1. TABLEAU DE SYNTHÈSE DES RISQUES RÉSIDUELS

| ID Risque | Domaine | Intitulé de la Vulnérabilité Résiduelle | Sévérité (CVSS v3.1) | Probabilité | Impact | Priorité |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **RISK-01** | SEC-04 | Fuite totale du jeton WebSocket via `/api/auth/token` (CORS wildcard) | **CRITIQUE (9.1)** | Élevée | Critique | **P0 (Bloquant)** |
| **RISK-02** | SEC-04 | Contournement de la politique d'origine WebSocket via préfixe IP | **ÉLEVÉE (8.3)** | Moyenne | Élevé | **P0 (Bloquant)** |
| **RISK-03** | SEC-04 | Rupture fonctionnelle et déconnexion en boucle du client mobile | **MOYENNE (5.3)** | Certaine | Modéré | **P0 (Bloquant)** |
| **RISK-04** | SEC-06 | Concurrence non synchronisée dans `memory_add` et `memory_forget` | **ÉLEVÉE (7.4)** | Élevée | Élevé | **P0 (Bloquant)** |
| **RISK-05** | SEC-03 | Absence d'isolation de session sur la confirmation d'extinction PC | **MOYENNE (6.5)** | Faible | Élevé | **P1** |
| **RISK-06** | SEC-05 | Fausse assurance d'état physique réel sur les services Home Assistant | **MOYENNE (5.5)** | Moyenne | Moyen | **P1** |
| **RISK-07** | SEC-01 | Algorithmique DoS par grands exposants dans le solveur mathématique | **FAIBLE (4.3)** | Faible | Modéré | **P2** |
| **RISK-08** | SEC-02 | Saturation de stockage par accumulation indéfinie de `temp_uploads` | **FAIBLE (3.3)** | Moyenne | Faible | **P2** |

---

## 2. FICHES DE RISQUE DÉTAILLÉES

### RISK-01 — Fuite totale du jeton WebSocket via `/api/auth/token`
- **Composant affecté :** `main2.py` L3915-3923 (`start_mobile_http_server`)
- **Sévérité :** **CRITIQUE (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N - 9.1)**
- **Description :** Le serveur HTTP écoute sur `0.0.0.0:8080`. L'endpoint `/api/auth/token` renvoie le jeton de session WebSocket actif en clair, sans exiger aucune authentification ni clé API, et attache l'en-tête `Access-Control-Allow-Origin: *`.
- **Exploitabilité :** Tout équipement connecté au réseau local (LAN/Wi-Fi) ou toute page web consultée dans un navigateur sur la même machine peut exécuter une simple requête HTTP GET pour récupérer le jeton et prendre le contrôle du WebSocket.
- **Conditions de reproduction sûres :**
  ```python
  import requests
  r = requests.get("http://localhost:8080/api/auth/token")
  assert "token" in r.json()
  ```
- **Mesure corrective recommandée :**
  Supprimer l'en-tête `Access-Control-Allow-Origin: *`. Exiger un secret partagé d'infrastructure (défini dans `.env`) ou générer un code d'appairage à usage unique (OTP) affiché sur la console PC avant de distribuer un jeton de session à un équipement distant.
- **Priorité :** **P0 (Bloquant pour toute mise en service)**.

---

### RISK-02 — Contournement de la politique d'origine WebSocket via préfixe IP
- **Composant affecté :** `main2.py` L534 (`WSSessionManager.is_origin_allowed`)
- **Sévérité :** **ÉLEVÉE (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N - 8.3)**
- **Description :** La fonction `is_origin_allowed` valide les origines via la condition `host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.")`. Cette comparaison textuelle valide n'importe quel domaine Internet contrôlé par un attaquant et commençant par ces sous-chaînes (ex. `http://192.168.attacker.com`).
- **Exploitabilité :** Un attaquant exploitant Cross-Site WebSocket Hijacking (CSWSH) peut contourner le filtre d'origine et initier une connexion vers `ws://localhost:8765`.
- **Conditions de reproduction sûres :**
  ```python
  from main2 import WS_SESSION_MANAGER
  assert WS_SESSION_MANAGER.is_origin_allowed("http://192.168.attacker.com") is True
  ```
- **Mesure corrective recommandée :**
  Remplacer la validation textuelle par le module standard `ipaddress` :
  ```python
  import ipaddress
  try:
      ip = ipaddress.ip_address(host)
      return ip.is_private or ip.is_loopback
  except ValueError:
      return host in ("localhost", "127.0.0.1", "::1")
  ```
- **Priorité :** **P0 (Bloquant)**.

---

### RISK-03 — Rupture fonctionnelle et déconnexion en boucle du client mobile
- **Composant affecté :** `mobile/app.js` L127-170
- **Sévérité :** **MOYENNE (CVSS:3.1/AV:A/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L - 5.3)**
- **Description :** Le backend exige désormais un message `{ "type": "auth", "token": "..." }` sous 5 secondes pour tout client distant. Or, le code de `mobile/app.js` n'a pas été mis à jour et n'envoie aucun message d'authentification.
- **Impact :** Tout téléphone ou tablette accédant à l'interface mobile via l'adresse LAN `http://192.168.1.23:8080` est déconnecté du WebSocket toutes les 5 secondes (code 4001), rendant l'interface mobile 100 % inopérante.
- **Conditions de reproduction sûres :**
  Ouvrir l'application mobile depuis une adresse IP non loopback ; constater la déconnexion et la tentative de reconnexion cyclique dans la console navigateur (`code 4001`).
- **Mesure corrective recommandée :**
  Mettre à jour `mobile/app.js` pour qu'il interroge le jeton localement et émette la poignée de main `auth` dès l'ouverture de la socket.
- **Priorité :** **P0 (Bloquant opérationnel)**.

---

### RISK-04 — Concurrence non synchronisée dans `memory_add` et `memory_forget`
- **Composant affecté :** `main2.py` L2106-2144 et L3293-3304
- **Sévérité :** **ÉLEVÉE (CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H - 7.4)**
- **Description :** Le routeur IA appelle directement `memory_add` et `memory_forget`. Ces deux fonctions effectuent des lectures et écritures directes sur `"jarvis_memoire.json"` sans acquérir `MEMOIRE_LOCK` et sans écriture atomique (`os.replace`), anéantissant les garanties apportées à `sauvegarder_memoire`.
- **Impact :** Risque de corruption de la mémoire persistante ou de troncature du fichier JSON lors de requêtes vocales ou d'accès concurrents.
- **Conditions de reproduction sûres :**
  Exécuter des écritures concurrentes via `memory_add` pendant qu'une écriture threadée a lieu via `sauvegarder_memoire`.
- **Mesure corrective recommandée :**
  Réécrire `memory_add` et `memory_forget` pour déléguer directement aux fonctions sécurisées `ajouter_memoire` et `supprimer_memoire` sous la protection de `MEMOIRE_LOCK`.
- **Priorité :** **P0 (Bloquant pour l'intégrité des données)**.

---

### RISK-05 — Absence d'isolation de session sur la confirmation d'extinction PC
- **Composant affecté :** `main2.py` L1849-1995 (`SystemActionController`)
- **Sévérité :** **MOYENNE (CVSS:3.1/AV:A/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H - 6.5)**
- **Description :** L'attribut `self.pending_action` est un état unique partagé au niveau du singleton de l'application. Lors de la réception de la commande « confirmer l'extinction », le contrôleur ne vérifie pas si le client confirmant est le même (même IP / même session) que celui ayant initié la demande.
- **Impact :** Un équipement distinct sur le réseau local peut valider l'arrêt du PC à l'insu de l'utilisateur local.
- **Mesure corrective recommandée :**
  Associer chaque action en attente à l'identifiant de socket ou à l'adresse IP source :
  `self.pending_action = {"action": "shutdown", "expires_at": ..., "client_ip": client_ip}` et vérifier `client_ip == self.pending_action["client_ip"]` lors de la confirmation.
- **Priorité :** **P1**.

---

### RISK-06 — Fausse assurance d'état physique réel sur les services Home Assistant
- **Composant affecté :** `main2.py` L1265-1325 et L3056-3142
- **Sévérité :** **MOYENNE (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:L/A:L - 5.5)**
- **Description :** `ha_appeler_service` renvoie `True` dès que le code HTTP retourné est 200 ou 201. Pour Home Assistant, cela signifie que la requête a été acceptée par le bus logiciel, mais pas que le périphérique physique (lampe, prise, alarme) a atteint l'état demandé.
- **Impact :** Pour les actions sensibles (notamment `ha_alarme`), l'utilisateur peut recevoir une fausse confirmation vocale alors que le système d'alarme a échoué à s'armer physiquement.
- **Mesure corrective recommandée :**
  Pour les entités de sécurité (alarmes, serrures), effectuer un appel ultérieur à `ha_get_etat` après 1 seconde pour vérifier le changement d'état effectif avant de vocaliser la confirmation.
- **Priorité :** **P1**.

---

### RISK-07 — Algorithmique DoS dans le solveur mathématique local
- **Composant affecté :** `main2.py` L2373-2423 (`resoudre_math_localement`)
- **Sévérité :** **FAIBLE (CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L - 4.3)**
- **Description :** L'évaluation par `eval()` filtre les caractères non mathématiques mais autorise des expressions exponentielles arbitraires comme `9**9**9` ou `2**10000000`, susceptibles de saturer un cœur CPU et de bloquer l'event loop asyncio.
- **Mesure corrective recommandée :**
  Remplacer `eval` par un parseur AST arithmétique dédié restreignant la valeur des exposants (`**` limité à un exposant $\le 10$).
- **Priorité :** **P2**.

---

### RISK-08 — Saturation de stockage par accumulation indéfinie de `temp_uploads`
- **Composant affecté :** `main2.py` L689-725
- **Sévérité :** **FAIBLE (CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L - 3.3)**
- **Description :** Les fichiers téléversés dans `temp_uploads/` reçoivent un préfixe UUID v4 et sont conservés indéfiniment sur le disque.
- **Impact :** Risque de saturation progressive de la partition système lors d'un usage intensif ou d'envois répétés de fichiers volumineux (10 Mo).
- **Mesure corrective recommandée :**
  Ajouter une tâche de nettoyage périodique supprimant les fichiers temporaires âgés de plus de 24 heures.
- **Priorité :** **P2**.
