# 🛡️ ALICE — PLAN DE RETOUR ARRIÈRE (ROLLBACK PLAN) P1
## PROCÉDURES DE REPLI D'URGENCE ET RESTAURATION DU SOCLE HOMOLOGUÉ (MISSION 006)

**Mission ID :** `ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Classification :** PROCÉDURE DE CONTINUITÉ D'ACTIVITÉ & RESTAURATION  
**Date :** 24 Novembre 2026  

---

## 1. DÉCLENCHEURS DE RETOUR ARRIÈRE (ROLLBACK TRIGGERS)

Une procédure de retour arrière immédiate doit être engagée si l'un des incidents critiques suivants est constaté en production :
1. **Échec d'appairage mobile systématique :** Impossibilité d'émettre ou de valider le cookie `alice_session` sur les terminaux clients autorisés.
2. **Rejet inattendu d'adresses IP légitimes :** Défaillance dans la chaîne de confiance du reverse proxy provoquant le blocage d'utilisateurs autorisés.
3. **Régression fonctionnelle critique :** Défaillance de l'interaction vocale, du frontend Three.js, ou de la synchronisation Home Assistant.
4. **Crash au démarrage :** Échec de liaison socket ou incompatibilité sur le système hôte.

---

## 2. PROCÉDURES DE REPLI

### 2.1. Option A : Repli par Configuration d'Environnement (Sans Modification de Code)

Avant toute modification de code source, le comportement par défaut de l'application peut être immédiatement rétabli via les variables d'environnement dans le fichier `.env` :

```ini
# Rétablissement immédiat de la liaison directe multi-interfaces (Topologie C)
ALICE_BIND_ADDRESS=0.0.0.0
ALICE_HTTP_PORT=8080
ALICE_WS_BIND_ADDRESS=0.0.0.0
ALICE_WS_PORT=8765

# Rétablissement de la confiance loopback par défaut
ALICE_TRUSTED_PROXIES=127.0.0.1,::1

# Mode de compatibilité transitoire
JARVIS_ENV=development
ALICE_REQUIRE_TLS=0
```

Redémarrer le service backend ALICE :
```powershell
Stop-Process -Name python -Force
& "venv\Scripts\python.exe" main2.py
```

### 2.2. Option B : Restauration Forensique de l'Arbre de Travail Git

Si une corruption de code ou une instabilité imprévue impose de restaurer l'état exact certifié lors de la mission précédente `ALICE-P0-FINAL-CERTIFICATION-GATE-005` (commit `b1f67aa2003deb6abbaa06f1e50827812a513de6`) :

```powershell
# 1. Vérification du statut Git
git status

# 2. Sauvegarde horodatée des modifications actuelles dans une branche locale de diagnostic
git checkout -b rescue/p1-hardening-backup-$(Get-Date -Format "yyyyMMdd-HHmmss")

# 3. Retour sur la branche main et restauration exacte du commit certifié P0
git checkout main
git reset --hard b1f67aa2003deb6abbaa06f1e50827812a513de6

# 4. Nettoyage des fichiers temporaires ou non suivis
git clean -fd
```

---

## 3. TABLEAU DES SOMMES DE CONTRÔLE (RÉFÉRENCE SOCLE P0)

En cas de restauration manuelle fichier par fichier, les sommes de contrôle SHA-256 de référence (état initial certifié) sont :

| Fichier | SHA-256 de Référence Socle P0 (`b1f67aa`) |
| :--- | :--- |
| `Jarvis Final - SITE/main2.py` | `E1EA29C4A994E4FB2C3260C4B9C1B343B18AC4734C9217A5C30F8255DE5844D4` |
| `Jarvis Final - SITE/mobile/app.js` | `A07E4A749DD30C07ADCBEEE7D8C776EBF2B26181CEC28CC73AD130760720426A` |
| `Jarvis Final - SITE/mobile/index.html` | `4C7976C853282B7A3AD0DC318BE440A39DBCD6603FC52946B0D6942AB9B2C33C` |
| `Jarvis Final - SITE/alice_modules.py` | `FC879F59E07B9E4FD931C08EC6D53C1B204BDF6A2643656C1265C48BE5B3E308` |
| `Jarvis Final - SITE/jarvis_agent.py` | `EA7DD54D58FDC886F9CF71F14F254F7B1B3CCD4CE2C003EB76BC659E2B8948B5` |

---

## 4. PROTOCOLE DE POST-VÉRIFICATION APRÈS ROLLBACK

Après application d'une procédure de repli :
1. **Contrôle d'intégrité :** Recalculer les hachages SHA-256 des fichiers restaurés à l'aide de `Get-FileHash`.
2. **Exécution des tests de recette :** Lancer immédiatement la suite maître de tests :
   ```powershell
   & "venv\Scripts\python.exe" "C:\Users\USER\.gemini\antigravity\brain\9f43747e-d272-4f9c-bf13-f2fb641773ea\scratch\test_acceptance_004_master.py"
   ```
3. **Validation de non-régression :** Confirmer le passage des 86 tests P0 (100% PASS).
4. **Validation de service :** Vérifier que l'interface mobile et le Three.js orb répondent correctement.
