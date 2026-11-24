# 📖 ALICE — GUIDE UTILISATEUR & MANUEL D'EXPLOITATION
## MISSION 007 : GUIDE OPÉRATIONNEL DE LA PLATEFORME J.A.R.V.I.S / ALICE

**Mission ID :** `ALICE-FUNCTIONAL-PLATFORM-EVOLUTION-007`  
**Projet :** J.A.R.V.I.S / ALICE — SITE-V2  
**Date :** 24 Novembre 2026  
**Version :** 2.1 — Functional Release  

---

## 1. DÉMARRAGE ET CONNEXION AU SYSTÈME

### 1.1 Démarrage du Serveur Central
Pour lancer le serveur Alice sur la machine hôte :
1. Exécuter le script batch situé dans le dossier du projet :
   ```cmd
   cd "Jarvis Final - SITE"
   DEMARRER_JARVIS.bat
   ```
2. Ou démarrer directement via l'interpréteur Python :
   ```cmd
   venv\Scripts\python.exe main2.py
   ```
3. Le serveur initialise les 16 modules experts, charge la mémoire sécurisée et démarre :
   - Le serveur HTTP mobile sur le port **8080**
   - Le serveur WebSocket sécurisé sur le port **8765**

---

### 1.2 Connexion depuis un Smartphone ou Tablette (Application Mobile)
1. Ouvrez le navigateur de votre smartphone (Chrome, Safari, Firefox).
2. Saisissez l'adresse réseau de la machine hôte :
   `http://<IP_DU_PC>:8080` (en mode développement) ou `https://<IP_DU_PC>:8080` (en production).
3. **Procédure d'appairage sécurisé (première connexion) :**
   - Une boîte de dialogue modale vous demande un code PIN à 6 chiffres.
   - Le code PIN temporaire est affiché dans la console du serveur lors du démarrage.
   - Saisissez le code et appuyez sur **« Associer l'appareil »**.
   - Votre session est désormais chiffrée et enregistrée.

---

## 2. COMPRENDRE LE CYCLE DE VIE DES COMMANDES

Grâce au contrat événementiel en 9 états de la Mission 007, l'application mobile affiche en temps réel la progression de votre demande via la barre de statut supérieure :

| État Affiché | Couleur & Animation | Signification pour l'Utilisateur |
| :---: | :---: | :--- |
| **`RECEIVED`** | Bleu clair fixe | La commande vocale ou textuelle a été bien reçue par le serveur. |
| **`VALIDATING`** | Bleu clair pulsant | Alice vérifie vos permissions de session et la validité des paramètres. |
| **`ACCEPTED`** | Cyan fixe | La commande est validée et programmée dans la file d'exécution. |
| **`RUNNING`** | Bleu vif animé | L'action est en cours d'exécution (recherche, domotique, vision). |
| **`REQUIRES_CONFIRMATION`** | Or / Jaune clignotant | **Action sensible !** Une boîte de dialogue vous demande confirmation avant d'agir. |
| **`SUCCEEDED`** | Vert émeraude | L'action a réussi avec succès et a été vérifiée matériellement. |
| **`FAILED`** | Rouge vif | L'action n'a pas pu aboutir. Un message d'explication vous est fourni. |
| **`UNKNOWN`** | Ambre / Orange | L'ordre a été transmis mais l'équipement physique ne répond pas (ex: ampoule éteinte à l'interrupteur mural). |
| **`CANCELLED`** | Gris neutre | Vous avez annulé l'action ou le délai de confirmation a expiré. |

---

## 3. MODALE DE CONFIRMATION INTERACTIVE

Pour les actions ayant un impact critique (extinction ou redémarrage de l'ordinateur, envoi d'un email, armement de l'alarme, suppression de fichiers) :
1. Alice ne procède pas immédiatement.
2. Une modale surgit sur votre écran mobile : **« Confirmation Requise »** avec le descriptif précis de l'action.
3. Deux boutons s'offrent à vous :
   - **`[Confirmer]`** (Vert) : L'action est exécutée sur-le-champ avec transmission de votre jeton de session.
   - **`[Annuler]`** (Rouge) : L'action est rejetée sans aucune conséquence sur vos données ou vos équipements.
4. Si vous ne répondez pas sous **60 secondes**, l'action expire automatiquement et est annulée par sécurité.

---

## 4. BASE DE CONNAISSANCES ET RAG (DOCUMENTS & TABLEURS)

Alice intègre désormais un moteur documentaire hybride capable d'analyser vos fichiers sans envoyer vos données à des tiers non autorisés :

### 4.1 Documents Pris en Charge
- **Tableurs Excel (`.xlsx`) :** Vos tableaux de données (ex: `Classeur1.xlsx`) sont automatiquement indexés ligne par ligne.
- **Documents PDF (`.pdf`) :** Vos rapports et notices sont analysés page par page.
- **Fichiers Texte & Code :** `.txt`, `.md`, `.py`, `.js`, `.json`, `.csv`.

### 4.2 Poser une Question sur vos Documents
Dites simplement :
- *"Alice, recherche dans mes documents les informations sur le matricule 24MEB01IU."*
- *"Alice, que contient le classeur de données ?"*
- *"Alice, résume le rapport de sécurité."*

Alice vous répondra en citant rigoureusement la source de chaque information :  
`[Source: Classeur1.xlsx | Feuille: sheet1 | Lignes: 1-10]`

---

## 5. CONTRÔLE DOMOTIQUE & VÉRICICATION PHYSIQUE

Lorsque vous pilotez votre maison via Alice :
- *"Alice, allume la lumière du salon en bleu à 50%."*
- *"Alice, éteins la prise du bureau."*

Alice ne se contente pas d'envoyer l'ordre à Home Assistant :
- Elle interroge le capteur réel de l'appareil pendant 1,2 seconde.
- Si l'ampoule s'allume effectivement, elle confirme : *"C'est fait, lumière salon allumée en bleu à 50%. État matériel vérifié."* (Statut `SUCCEEDED`).
- Si l'interrupteur physique au mur a été coupé, elle vous prévient honnêtement : *"Attention : l'ordre a été envoyé, mais l'appareil salon signale toujours l'état : off."* (Statut `UNKNOWN`).

---

## 6. DÉPANNAGE ET BONNES PRATIQUES

1. **Microphone bloqué sur mobile en HTTP :**
   - Si vous accédez au serveur en `http://` sur un smartphone Android avec Chrome, le microphone peut être restreint par le navigateur.
   - Cliquez sur l'avertissement rouge en haut de l'écran et suivez les instructions : tapez `chrome://flags` dans Chrome, cherchez *« Insecure origins treated as secure »*, ajoutez l'URL de votre serveur (ex: `http://192.168.1.23:8080`) et relancez Chrome.
   - En production avec certificat HTTPS/WSS, cette manipulation est inutile.
2. **Double clic involontaire :**
   - Le système dispose d'une protection anti-rebond automatique. Les clics rapprochés de moins de 800 ms sont ignorés pour éviter toute double exécution accidentelle.
3. **Session expirée :**
   - Si la modale d'appairage réapparaît, saisissez simplement un nouveau code PIN généré sur la console du serveur.
