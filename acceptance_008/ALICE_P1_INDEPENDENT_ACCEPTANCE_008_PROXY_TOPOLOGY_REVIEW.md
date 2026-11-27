# 🛡️ ALICE-P1-INDEPENDENT-ACCEPTANCE-008 — REVUE TOPOLOGIE PROXY & GUIDE

**Mission ID :** `ALICE-P1-INDEPENDENT-ACCEPTANCE-008`  
**Date :** 25 Novembre 2026  

---

## 1. INVENTAIRE DES CONFIGURATIONS RÉSEAU DANS LE DÉPÔT

- Recherche récursive (`*nginx*`, `*caddy*`, `*docker*`, `*.bat`, `*.sh`, `*.ps1`) dans `C:\Users\USER\Desktop\Jarvis Final - SITE-V2` :
  - **Fichiers Nginx / Caddy / Docker / Firewall :** **0 fichier trouvé**.
  - **Scripts présents :** Uniquement des scripts locaux Windows (`DEMARRER_JARVIS.bat`, `install.bat`).
- **Conséquence :** L'écrasement réel des en-têtes `X-Forwarded-For` et `X-Forwarded-Proto` par un proxy de production et les règles pare-feu de la machine cible sont **`NOT_VERIFIED`**.

## 2. VALIDATION LOCALE PAR FIXTURE PROXY TCP INDÉPENDANTE

Une fixture TCP locale (`CLIENT TCP → PROXY TCP → BACKEND TCP`) a été exécutée dans `scratch/test_acceptance_008_independent.py` :
- Lorsque le proxy écrase les headers clients forgés (`XFF: 127.0.0.1`, `X-Real-IP: ::1`, `XFP: https`), le backend Python rejette correctement les clients non authentifiés (`4001` WS, `403` HTTP si `XFP=http`) et accepte les sessions valides (`auth_ok` WS, `200 + Secure` HTTP si `XFP=https`).

## 3. CONTRADICTIONS IDENTIFIÉES DANS `ALICE_P1_REMEDIATION_007_DEPLOYMENT_GUIDE.md`

1. **Port WebSocket (`443 /ws` vs `:8765`) :** Le bloc Nginx du guide expose WebSocket sur `https://<host>/ws` (port 443) et ferme le port `8765`, mais `mobile/app.js:12` se connecte en dur sur `:8765`.
2. **HSTS côté Nginx :** Le bloc Nginx d'exemple omet `add_header Strict-Transport-Security`, bien que `MobileHandler` émette cet en-tête lorsque `X-Forwarded-Proto: https` est transmis.
3. **Header `X-Forwarded-For` dupliqué :** `get_trusted_client_ip` (`main2.py:4725`) utilise `headers.get("X-Forwarded-For")` sans vérifier `headers.get_all("X-Forwarded-For")` pour rejeter d'éventuels en-têtes dupliqués si un proxy intermédiaire ne les fusionne pas.
