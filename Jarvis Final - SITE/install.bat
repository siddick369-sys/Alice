@echo off
SETLOCAL EnableDelayedExpansion
TITLE J.A.R.V.I.S - Installation Automatique (www.techenclair.fr)
COLOR 0A
cd /d "%~dp0"

echo ======================================================
echo           INSTALLATION DE J.A.R.V.I.S
echo           Site : www.techenclair.fr
echo ======================================================
echo.

:: 1. Vérification des droits Administrateur
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [^!] ATTENTION : Ce script n'est pas lance en tant qu'Administrateur.
    echo [^!] Pour une installation sans erreurs, il est VIVEMENT recommande de :
    echo     - Faire un clic droit sur 'install.bat'
    echo     - Choisir 'Executer en tant qu'administrateur'
    echo.
    pause
    exit /b
)

:: 1b. Analyse du système (Détection dynamique)
echo [SYSTEME] Analyse de votre configuration...
echo.

set "PY_STATUS=[A INSTALLER]"
set "NODE_STATUS=[A INSTALLER]"
set "VENV_STATUS=[A CREER]"
set "WEB_STATUS=[A INSTALLER]"
set "ROOT_STATUS=NON"
set "CHROME_STATUS=NON"

:: Vérification Racine (présence de main2.py dans le même dossier que le script)
if exist "%~dp0main2.py" (
    set "ROOT_STATUS=OUI"
) else (
    set "ROOT_STATUS=NON"
)

:: Vérification Chrome (Registre et Chemins)
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1 && set "CHROME_STATUS=OUI"
reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1 && set "CHROME_STATUS=OUI"
if "!CHROME_STATUS!"=="NON" (
    if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_STATUS=OUI"
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_STATUS=OUI"
    if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_STATUS=OUI"
)


:: Détection versions
python --version >nul 2>&1 && set "PY_STATUS=[DEJA PRESENT]"
where npm >nul 2>&1 && set "NODE_STATUS=[DEJA PRESENT]"
if exist "venv" set "VENV_STATUS=[DEJA PRESENT]"
if exist "frontend\node_modules" set "WEB_STATUS=[DEJA PRESENT]"

:: 1c. Récapitulatif et Validation
echo ======================================================
echo           RECAPITULATIF DE L'INSTALLATION
echo ======================================================
echo [CHECK] Fichier a la RACINE du projet : !ROOT_STATUS!
echo [CHECK] Navigateur Chrome installe    : !CHROME_STATUS!
echo.
echo Statut des composants :
echo  - Environnement Python 3.12    : !PY_STATUS!
echo  - Node.js / NPM (Interface)    : !NODE_STATUS!
echo  - Dossier virtuel (venv)       : !VENV_STATUS!
echo  - Modules Web (node_modules)   : !WEB_STATUS!
echo.
if "!ROOT_STATUS!"=="NON" (
    COLOR 0C
    echo.
    echo XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    echo X               ERREUR D'EMPLACEMENT                 X
    echo XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    echo.
    echo [^!] LE FICHIER INSTALL.BAT N'EST PAS AU BON ENDROIT.
    echo.
    echo POUR CORRIGER :
    echo 1. Allez dans votre dossier JARVIS (la ou se trouve main2.py^).
    echo 2. Copiez ce fichier 'install.bat' a l'interieur.
    echo 3. Relancez-le depuis ce dossier.
    echo.
    echo L'installation ne peut pas continuer ici.
    pause
    exit /b
)

if "!CHROME_STATUS!"=="NON" (
    echo [^!] ATTENTION : Chrome est introuvable. JARVIS en a besoin.
    echo [^!] Veuillez l'installer avant de continuer.
    echo.
)
echo [INFO] Seuls les elements [A INSTALLER] seront traites.
echo [INFO] Taille approximative max : ~1.5 Go
echo.
echo ------------------------------------------------------
echo  Soutenir TechEnClair : https://www.paypal.com/paypalme/TechEnClair
echo ------------------------------------------------------
echo ======================================================


echo.
echo.
echo Appuyez sur [ENTREE] pour lancer les etapes manquantes...
pause >nul

echo.
echo [SYSTEME] Debut des operations...
echo.

:: 2. Détection / Installation de Python
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    py --version >nul 2>&1 && set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    echo [SYSTEME] Python est introuvable. Telechargement de Python 3.12...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -OutFile 'python_installer.exe'"
    echo [SYSTEME] Installateur telecharge. Lancement...
    echo [IMPORTANT] COCHEZ BIEN LA CASE 'ADD PYTHON TO PATH' AU DEBUT ^!
    start /wait python_installer.exe
    del python_installer.exe
    echo [SYSTEME] Python doit être installe maintenant. Veuillez RELANCER ce fichier install.bat.
    pause && exit /b
)

echo [SYSTEME] Python detecte : 
%PYTHON_CMD% --version

:: 3. Détection / Installation de Node.js
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [SYSTEME] Node.js est manquant. Telechargement...
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.12.2/node-v20.12.2-x64.msi' -OutFile 'node_installer.msi'"
    echo [SYSTEME] Installation de Node.js en cours...
    start /wait node_installer.msi
    del node_installer.msi
    echo [SYSTEME] Node.js installe (un redemarrage de l'ordinateur peut être requis si npm n'est toujours pas detecte^).
)

:: 4. Création de l'environnement virtuel
if not exist "venv" (
    echo [SYSTEME] Preparation de l'environnement virtuel (venv^)...
    "%PYTHON_CMD%" -m venv venv
    if %errorlevel% neq 0 (
        echo [^!] Erreur lors de la creation du venv. Verifiez vos droits.
        pause && exit /b
    )
)

set "V_PY=.\venv\Scripts\python.exe"

:: 5. Mise à jour des outils de base (EVITE LES ERREURS DE COMPILATION)
echo [SYSTEME] Mise a jour des outils d'installation (pip, setuptools, wheel)...
"%V_PY%" -m pip install --upgrade pip setuptools wheel

:: 6. Installation des modules
echo [SYSTEME] Installation des composants IA, Audio et Reseau...

:: Installation par étapes pour isoler les erreurs
echo [1/3] Installation des modules IA (Gemini, Groq, OpenAI, Google APIs)...
"%V_PY%" -m pip install python-dotenv google-genai google-generativeai groq openai flask flask-cors requests websockets colorama tenacity google-auth-oauthlib google-auth-httplib2 google-api-python-client
if %errorlevel% neq 0 (
    echo [^!] Erreur lors de l'installation des modules IA. Verifiez votre connexion internet.
)

echo [2/3] Installation des modules Audio et Vision (Pygame, PyAudio, PyAutoGUI)...
"%V_PY%" -m pip install pygame pyaudio SpeechRecognition edge-tts pyttsx3 pyautogui Pillow screeninfo
if %errorlevel% neq 0 (
    echo.
    echo [AVERTISSEMENT] L'installation de 'pygame' ou 'pyaudio' a peut-être echoue.
    echo [SOLUTION] Si vous voyez une erreur "C++ build tools are required" :
    echo 1. Telechargez : https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo 2. Installez et cochez "Developpement Desktop en C++".
    echo 3. Relancez ensuite ce fichier 'install.bat'.
    echo.
    pause
)

echo [3/3] Finalisation avec le fichier requirements.txt...
if exist "requirements.txt" (
    "%V_PY%" -m pip install -r requirements.txt
)

:: 7. Interface Web
where npm >nul 2>&1
if %errorlevel% equ 0 (
    if exist "frontend\package.json" (
        echo [SYSTEME] Installation de l'interface Web...
        cd frontend && call npm install && cd ..
    )
)

:: 8. Creation du demarreur
echo [SYSTEME] Generation du fichier de lancement 'DEMARRER_JARVIS.bat'...
(
echo @echo off
echo TITLE J.A.R.V.I.S - www.techenclair.fr
echo COLOR 0B
echo cd /d "%%~dp0"
echo ".\venv\Scripts\python.exe" "main2.py"
echo pause
) > "DEMARRER_JARVIS.bat"


:: 9. Création du modèle .env si absent
if not exist ".env" (
    echo [SYSTEME] Creation du fichier de configuration .env...
    (
    echo GEMINI_API_KEY=VOTRE_CLE_ICI
    echo YOUTUBE_API_KEY=VOTRE_CLE_ICI
    echo XAI_API_KEY=VOTRE_CLE_ICI
    echo HA_URL=http://192.168.1.XX:8123
    echo HA_TOKEN=VOTRE_TOKEN_ICI
    echo SERPAPI_API_KEY=VOTRE_CLE_ICI
    echo GROQ_API_KEY=VOTRE_CLE_ICI
    ) > ".env"
)

:: 10. Personnalisation du Prénom
echo.
echo ------------------------------------------------------
echo  PERSONNALISATION DE VOTRE IA
echo ------------------------------------------------------
echo Par defaut, JARVIS est configure pour s'adresser a 'Mickael'.
echo Si vous voulez qu'il utilise VOTRE prenom, ecrivez-le ici :
echo (Ou appuyez simplement sur [ENTREE] pour garder 'Mickael'^)
echo.
set "PN="
set /p "PN=[?] Votre prenom : "

if "%PN%"=="" goto skip_name
if /i "%PN%"=="Mickael" goto skip_name

echo.
echo [SYSTEME] Transformation de JARVIS en cours...
echo Remplacement de 'Mickael' par '%PN%' dans le code source...

echo import sys > temp_rename.py
echo n = sys.argv[1] >> temp_rename.py
echo for p in ['main2.py', 'jarvis_agent.py']: >> temp_rename.py
echo     try: >> temp_rename.py
echo         f = open(p, 'r', encoding='utf-8') >> temp_rename.py
echo         c = f.read() >> temp_rename.py
echo         f.close() >> temp_rename.py
echo         f = open(p, 'w', encoding='utf-8') >> temp_rename.py
echo         f.write(c.replace('Mickael', n).replace('mickael', n.lower())) >> temp_rename.py
echo         f.close() >> temp_rename.py
echo     except: pass >> temp_rename.py

".\venv\Scripts\python.exe" temp_rename.py "%PN%"
del temp_rename.py

echo [OK] Personnalisation terminee.

:skip_name
echo.




echo.
echo ======================================================
echo           INSTALLATION TERMINEE ^!
echo ======================================================
echo.
echo ETAPES SUIVANTES :
echo 1. Ouvre le fichier '.env' et ajoute tes cles API (Gemini, etc.).
echo 2. Si tu as eu des erreurs rouges, installe les "Build Tools C++".
echo 3. Lance 'DEMARRER_JARVIS.bat' pour demarrer ton IA.
echo.
echo ------------------------------------------------------
echo  Soutenir le projet JARVIS :
echo  Si tu aimes mon travail, tu peux m'offrir un cafe ici :
echo  https://www.paypal.com/paypalme/TechEnClair
echo ------------------------------------------------------
echo.
echo Aide et support : www.techenclair.fr
echo ======================================================
pause

