# ALICE_010 — RAPPORT DE CONTAINMENT SECRET (F03)

- **Finding :** `F03` — GitHub Personal Access Token exposé en clair dans `.git/config`
- **Statut :** `LOCAL_REFERENCE_REMOVED` | `EXTERNAL_REVOCATION_PENDING` *(ne peut être marqué `EXTERNAL_REVOCATION_CONFIRMED` sans confirmation réelle du fournisseur par l'utilisateur)*

## 1. Exposition détectée (sans divulgation)
- `.git/config` (`remote.origin.url`) : `SECRET_DETECTED` (PAT intégré à l'URL HTTPS du remote `origin`).
- Scan de propagation hors `.git` :
  - `C:\Users\USER\Desktop\Jarvis Final - SITE-V2\.env` (ligne 1) : présence d'un motif PAT GitHub (fichier d'environnement local non suivi).
  - `C:\Users\USER\Desktop\Jarvis Final - SITE-V2\Jarvis Final - SITE\.env` (ligne 9) : présence d'un motif PAT GitHub (fichier d'environnement local non suivi).
  - `tests/alice_ultimate/security/test_wave0_foundation.py` (ligne 63) : chaîne de test synthétique pour `redact_text` (non secret).

## 2. Remédiation locale effectuée
- `git remote set-url origin https://github.com/siddick369-sys/Alice.git`
- Vérification : `PAT_IN_GIT_CONFIG_AFTER=False`, `git remote -v` affiche uniquement `https://github.com/siddick369-sys/Alice.git` sans jeton intégré.

## 3. Action externe obligatoire pour l'utilisateur
La révocation d'un PAT GitHub est une opération externe impossible depuis le dépôt local. L'utilisateur doit immédiatement :
1. Se connecter sur GitHub → **Settings** → **Developer settings** → **Personal access tokens** (**Tokens (classic)** et/ou **Fine-grained tokens**).
2. Révoquer (**Revoke** / **Delete**) le jeton précédemment présent dans `.git/config` (et remplacer l'entrée dans `.env` / `Jarvis Final - SITE/.env` si identique).
3. Utiliser **Git Credential Manager** (ou un helper sécurisé) plutôt qu'un PAT dans l'URL du remote.
