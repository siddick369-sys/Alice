# 🛡️ ALICE — GUIDE DE DÉPLOIEMENT EN PRODUCTION P1
## ARCHITECTURES DE DÉPLOIEMENT, REVERSE PROXIES ET CONFIGURATION TLS (MISSION 006)

**Mission ID :** `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Classification :** GUIDE OPÉRATIONNEL DE PRODUCTION  
**Date :** 24 Novembre 2026  

---

## 1. VUE D'ENSEMBLE DES TOPOLOGIES SUPPORTÉES

ALICE prend en charge trois architectures de déploiement en fonction des besoins de sécurité et d'infrastructure de l'utilisateur :

```
[ TOPOLOGIE A : REVERSE PROXY LOCAL (RECOMMANDÉ PRODUCTION) ]
  Internet / LAN ---> [ Nginx / Caddy (Port 443 / TLS) ] 
                             |
                             |-- HTTP Proxy (127.0.0.1:8080)
                             +-- WSS Proxy  (127.0.0.1:8765)
                                     |
                             [ Backend ALICE ]

[ TOPOLOGIE B : REVERSE PROXY DISTANT / DMZ ]
  Client ---> [ Passerelle Reverse Proxy (ex: 192.168.1.1) ] ---> [ ALICE (192.168.1.50) ]

[ TOPOLOGIE C : ACCÈS DIRECT LAN (USAGE PRIVÉ ISOLÉ) ]
  Smartphone (WiFi) ---------------------------------------------> [ ALICE (0.0.0.0:8080/8765) ]
```

---

## 2. VARIABLES D'ENVIRONNEMENT DE PRODUCTION

Créez ou mettez à jour votre fichier `.env` ou configurez les variables d'environnement système :

```ini
# --- Environnement et Sécurité ---
JARVIS_ENV=production
ALICE_ENV=production
ALICE_REQUIRE_TLS=1

# --- Topologie Réseau (Exemple Topologie A : isolation locale) ---
ALICE_BIND_ADDRESS=127.0.0.1
ALICE_HTTP_PORT=8080
ALICE_WS_BIND_ADDRESS=127.0.0.1
ALICE_WS_PORT=8765

# --- Proxies de confiance autorisés à transmettre l'IP cliente ---
ALICE_TRUSTED_PROXIES=127.0.0.1,::1

# --- Origines autorisées en production (C-02) ---
ALICE_ALLOWED_ORIGINS=https://alice.mon-domaine.local,https://127.0.0.1:8443
ALICE_ALLOW_LAN_ORIGINS=0
```

---

## 3. CONFIGURATION DES REVERSE PROXIES

### 3.1. Option 1 : Configuration Nginx (Recommandé)

Placez la configuration dans `/etc/nginx/sites-available/alice` (Linux) ou dans `conf/nginx.conf` (Windows) :

```nginx
# Redirection automatique HTTP vers HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name alice.mon-domaine.local;
    return 301 https://$host$request_uri;
}

# Serveur principal HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name alice.mon-domaine.local;

    # Certificats SSL/TLS
    ssl_certificate /etc/letsencrypt/live/alice.mon-domaine.local/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alice.mon-domaine.local/privkey.pem;

    # Protocoles et suites de chiffrement durcies
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # En-têtes de transmission IP cliente (exploités par get_trusted_client_ip)
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 1. Interface Web et API HTTP Mobile
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_buffering off;
        proxy_read_timeout 90s;
    }

    # 2. Flux WebSocket (Upgrade RFC 6455)
    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

### 3.2. Option 2 : Configuration Caddy (Configuration Moderne & Automatique)

Fichier `Caddyfile` :

```caddy
alice.mon-domaine.local {
    # TLS automatique géré par Caddy
    tls admin@mon-domaine.local

    # Proxy WebSocket
    @websockets {
        header Connection *Upgrade*
        header Upgrade    websocket
    }
    reverse_proxy @websockets 127.0.0.1:8765 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Real-IP {remote_host}
    }

    # Proxy HTTP Backend & Frontend
    reverse_proxy 127.0.0.1:8080 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

---

## 4. DÉMARRAGE ET SUPERVISION SOUS WINDOWS

Pour garantir la résilience et le redémarrage automatique d'ALICE sous Windows en production :

### Création du script de lancement durci (`start_alice_production.bat`)

```bat
@echo off
title ALICE - PRODUCTION BACKEND
cd /d "c:\Users\USER\Desktop\Jarvis Final - SITE-V2\Jarvis Final - SITE"

:: Chargement des variables durcies
set JARVIS_ENV=production
set ALICE_ENV=production
set ALICE_REQUIRE_TLS=1
set ALICE_BIND_ADDRESS=127.0.0.1
set ALICE_HTTP_PORT=8080
set ALICE_WS_BIND_ADDRESS=127.0.0.1
set ALICE_WS_PORT=8765
set ALICE_TRUSTED_PROXIES=127.0.0.1,::1

:: Lancement avec l'environnement virtuel Python
venv\Scripts\python.exe main2.py
pause
```

### Intégration Windows Task Scheduler (Tâche Planifiée)
1. Ouvrez le **Planificateur de tâches** (`taskschd.msc`).
2. Créez une tâche : **"ALICE Production Agent"**.
3. Déclencheur : **Au démarrage du système** ou **À l'ouverture de session**.
4. Action : Démarrer un programme `start_alice_production.bat`.
5. Paramètres : Cocher "Redémarrer en cas d'échec toutes les 1 minute".

---

## 5. CHECKLIST DE CONTRÔLE PRÉ-EXPOSITION

Avant d'ouvrir les flux à l'application mobile ou aux utilisateurs :
- [ ] Le reverse proxy écoute en HTTPS/WSS avec un certificat TLS valide.
- [ ] Les variables `ALICE_BIND_ADDRESS=127.0.0.1` et `ALICE_WS_BIND_ADDRESS=127.0.0.1` sont appliquées.
- [ ] La commande `netstat -ano | findstr 8080` confirme l'écoute sur `127.0.0.1:8080` et **non** sur `0.0.0.0:8080`.
- [ ] La commande `netstat -ano | findstr 8765` confirme l'écoute sur `127.0.0.1:8765`.
- [ ] L'accès direct via IP publique ou externe sur le port 8080 est bloqué par le pare-feu hôte (Windows Defender Firewall).
- [ ] Le code PIN d'appairage à usage unique s'affiche et s'associe avec succès.
