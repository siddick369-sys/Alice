# from ursina import *  # DESACTIVE — interface web Three.js
import sys
import ssl
import threading
import asyncio
import secrets
import hmac
import ipaddress
from urllib.parse import urlparse, parse_qs, urlsplit
from typing import Optional, List, Dict, Any, Union, Tuple
import google.genai as genai
from google.genai import types
import speech_recognition as sr
import edge_tts
import pygame
import os
from dotenv import load_dotenv
import random
import math
import pyautogui
import webbrowser
import subprocess
import requests
import time
import pickle
import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pyaudio
import websockets
try:
    import psutil
except ImportError:
    psutil = None
import pytesseract
from pytesseract import Output
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = os.path.join(os.path.dirname(__file__), 'tessdata')
import platform
from PIL import Image
from openai import OpenAI
import uuid
import base64
import io
import tempfile
import PyPDF2
import pyttsx3
import vision_ocr
import alice_modules

# Google APIs
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Chargement des variables d'environnement
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
XAI_API_KEY     = os.getenv("XAI_API_KEY")
HA_URL          = os.getenv("HA_URL")
HA_TOKEN        = os.getenv("HA_TOKEN")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")

client          = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1beta'})
HF_TOKEN        = os.getenv("HF_TOKEN")
# Client Grok (xAI) - OpenAI compatible
grok_client     = None
if XAI_API_KEY and XAI_API_KEY != "VOTRE_CLE_ICI":
    grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

# Client Groq (Qwen) - OpenAI compatible
groq_client     = None
if GROQ_API_KEY and GROQ_API_KEY != "VOTRE_CLE_ICI":
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

MODELS_LIST     = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]
CHOSEN_MODEL    = MODELS_LIST[0]

# Initialisation des 16 modules Alice
alice_brain = alice_modules.AliceModules(
    hf_token=os.getenv("HF_TOKEN"),
    gemini_client=client,
    gemini_models=MODELS_LIST
)

# Ollama (LLMs locaux — fallback 100% offline)
OLLAMA_URL      = "http://127.0.0.1:11434"
OLLAMA_MODELS   = ["mistral:instruct", "mistral", "llama3:8b", "llama3", "gemma4"]

VILLE_PAR_DEFAUT = "Amilly"
LAT_PAR_DEFAUT   = 47.9742
LON_PAR_DEFAUT   = 2.7708

CLAP_THRESHOLD = 1200
VIDEO_LANCEE   = False
MODE_IRON_MAN = False 

# Configuration langue et voix
CURRENT_LANG = "fr-FR"
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
VOICES = {
    "fr-FR": "fr-FR-DeniseNeural",
}
SPEAKER_LOCK = threading.Lock()

# Flags et États globaux pour les nouvelles fonctions
FOCUS_MODE    = False
DERNIER_DIAG  = 0
DIAG_INTERVAL = 300 # 5 minutes entre les alertes auto
PROD_SCORE    = 0
PROD_LEVEL    = 1

def extraire_texte_doc(chemin):
    ext = Path(chemin).suffix.lower()
    # Extensions de fichiers texte brut
    text_extensions = [".txt", ".log", ".py", ".js", ".html", ".css", ".md", ".json", ".xml", ".csv"]
    try:
        if ext in text_extensions:
            with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            texte = ""
            with open(chemin, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    texte += page.extract_text() + "\n"
            return texte
        else:
            # Essayer de lire comme du texte par défaut si l'extension est inconnue
            try:
                with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except:
                return None
    except Exception as e:
        print(f"Erreur extraction {chemin} : {e}")
        return None
    except Exception as e:
        print(f"Erreur lecture {chemin} : {e}")
    return ""

def ecrire_fichier_pc(chemin, contenu):
    """Écrit du contenu dans un fichier, crée les dossiers si nécessaire."""
    try:
        chemin = chemin.strip('"').strip("'") # Nettoyage
        dossier = os.path.dirname(chemin)
        if dossier and not os.path.exists(dossier):
            os.makedirs(dossier)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(contenu)
        return f"D'accord Aboubakar Ibrahim Siddick, le fichier a été sauvegardé avec succès dans : {chemin}"
    except Exception as e:
        return f"Erreur lors de l'écriture du fichier : {e}"

def ouvrir_url_pc(url):
    """Ouvre une URL dans le navigateur."""
    try:
        url = url.strip('"').strip("'").strip()
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"J'ouvre {url} pour vous."
    except Exception as e:
        return f"Impossible d'ouvrir l'URL : {e}"

# ==========================================
# MEMOIRE PERSISTANTE (C-03 / SEC-06 : Intégrité, Thread-Safety, Verrou Cross-Process & Écriture Atomique)
# ==========================================
MEMOIRE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memoire.json")
MEMOIRE_LOCK = threading.RLock()

class CrossProcessMemoryLock:
    """
    Verrou mémoire hybride : thread-safe réentrant et cross-process au niveau OS.
    Utilise msvcrt (Windows) ou fcntl (Unix) avec gestion de timeout, tolérance
    aux pannes et prévention absolue des deadlocks et verrous orphelins (C-03).
    """
    def __init__(self, lock_file: Optional[str] = None, timeout: float = 5.0, thread_lock: Optional[threading.RLock] = None):
        self.lock_file = lock_file or f"{MEMOIRE_FILE}.crossprocess.lock"
        self.timeout = timeout
        self.thread_lock = thread_lock or MEMOIRE_LOCK
        self.file_fd = None
        self._owner_thread = None
        self._reentrant_count = 0

    def __enter__(self):
        current_thread = threading.get_ident()
        self.thread_lock.acquire()

        if self._owner_thread == current_thread:
            self._reentrant_count += 1
            return self

        start_time = time.time()
        while True:
            try:
                self.file_fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(self.file_fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                self._owner_thread = current_thread
                self._reentrant_count = 1
                return self
            except (OSError, IOError):
                if self.file_fd is not None:
                    try:
                        os.close(self.file_fd)
                    except Exception:
                        pass
                    self.file_fd = None

                if time.time() - start_time >= self.timeout:
                    self.thread_lock.release()
                    raise TimeoutError(f"Timeout ({self.timeout}s) acquisition verrou cross-process : {self.lock_file}")
                time.sleep(0.02)

    def __exit__(self, exc_type, exc_val, exc_tb):
        current_thread = threading.get_ident()
        if self._owner_thread == current_thread:
            self._reentrant_count -= 1
            if self._reentrant_count == 0:
                try:
                    if self.file_fd is not None:
                        if sys.platform == "win32":
                            import msvcrt
                            try:
                                msvcrt.locking(self.file_fd, msvcrt.LK_UNLCK, 1)
                            except Exception:
                                pass
                        else:
                            import fcntl
                            try:
                                fcntl.flock(self.file_fd, fcntl.LOCK_UN)
                            except Exception:
                                pass
                        try:
                            os.close(self.file_fd)
                        except Exception:
                            pass
                        self.file_fd = None
                finally:
                    self._owner_thread = None

        self.thread_lock.release()

CROSS_PROCESS_MEMORY_LOCK = CrossProcessMemoryLock()

def charger_memoire():
    """Charge la mémoire de manière thread-safe et cross-process avec résilience face aux corruptions."""
    with CROSS_PROCESS_MEMORY_LOCK:
        if os.path.exists(MEMOIRE_FILE):
            try:
                with open(MEMOIRE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception as e:
                print(f"[MEMOIRE] Erreur lecture fichier mémoire (corruption potentielle) : {e}")
                return {}
        return {}

def sauvegarder_memoire(memoire):
    """Sauvegarde atomique de la mémoire avec verrouillage cross-process et remplacement sécurisé."""
    if not isinstance(memoire, dict):
        print("[MEMOIRE] Format de mémoire invalide, sauvegarde ignorée.")
        return False
    with CROSS_PROCESS_MEMORY_LOCK:
        temp_file = f"{MEMOIRE_FILE}.{os.getpid()}_{time.time_ns()}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(memoire, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, MEMOIRE_FILE)
            return True
        except Exception as e:
            print(f"[MEMOIRE] Erreur sauvegarde atomique mémoire : {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return False

def ajouter_memoire(cle, valeur):
    """Ajoute un fait en mémoire de manière thread-safe et cross-process."""
    with CROSS_PROCESS_MEMORY_LOCK:
        memoire = charger_memoire()
        memoire[cle] = {"valeur": valeur, "timestamp": time.strftime("%d/%m/%Y %H:%M")}
        return sauvegarder_memoire(memoire)

def supprimer_memoire(cle):
    """Supprime un fait en mémoire de manière thread-safe et cross-process (exacte ou floue)."""
    with CROSS_PROCESS_MEMORY_LOCK:
        memoire = charger_memoire()
        if not memoire:
            return False
        if cle in memoire:
            del memoire[cle]
            return sauvegarder_memoire(memoire)
        cle_lower = cle.lower()
        keys_to_del = [k for k in memoire.keys() if cle_lower in k.lower()]
        if keys_to_del:
            for k in keys_to_del:
                del memoire[k]
            return sauvegarder_memoire(memoire)
        return False

def charger_contexte_rag():
    contexte = ""
    fichiers_trouves = False
    
    if os.path.exists(KNOWLEDGE_DIR):
        contexte += "DOCUMENTS DE CONNAISSANCE (RAG) :\n"
        for chemin in Path(KNOWLEDGE_DIR).glob("**/*"):
            if chemin.suffix.lower() in [".txt", ".pdf"]:
                fichiers_trouves = True
                contenu = extraire_texte_doc(str(chemin))
                if contenu:
                    contexte += f"--- DEBUT DOCUMENT: {chemin.name} ---\n{contenu}\n--- FIN DOCUMENT: {chemin.name} ---\n\n"
    
    mem = charger_memoire()
    if mem:
        contexte += "FAITS MEMORISES SUR L'UTILISATEUR :\n"
        for k, v in mem.items():
            if isinstance(v, dict):
                contexte += f"- {k}: {v.get('valeur', '')} (enregistré le {v.get('timestamp', 'inconnu')})\n"
            else:
                contexte += f"- {k}: {v}\n"
        contexte += "\n"

    return contexte if (fichiers_trouves or bool(mem)) else ""

HA_HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type" : "application/json"
}

CREATOR_INFO = (
    "INFORMATIONS SUR TON CREATEUR :\n"
    "- Prenom : Aboubakar Ibrahim Siddick\n"
    "- Age : 37 ans\n"
    "- Date de naissance : 21 Mai 1988\n"
    "- Role : Ton createur et maitre\n"
    "- Tu dois toujours l appeler Aboubakar Ibrahim Siddick avec respect "
    "mais aussi une pointe de sarcasme affectueux.\n"
)

EXTENSIONS = {
    "Images"   : [".jpg", ".jpeg", ".png", ".gif", ".bmp",
                  ".tiff", ".tif", ".webp", ".svg", ".ico",
                  ".heic", ".raw", ".cr2", ".nef"],
    "Videos"   : [".mp4", ".avi", ".mkv", ".mov", ".wmv",
                  ".flv", ".webm", ".m4v", ".mpg", ".mpeg",
                  ".3gp", ".ts"],
    "Musique"  : [".mp3", ".wav", ".flac", ".aac", ".ogg",
                  ".wma", ".m4a", ".opus", ".aiff"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx",
                  ".ppt", ".pptx", ".txt", ".odt", ".ods",
                  ".odp", ".rtf", ".csv", ".epub"],
    "Archives" : [".zip", ".rar", ".7z", ".tar", ".gz",
                  ".bz2", ".xz", ".iso"],
    "Code"     : [".py", ".js", ".html", ".css", ".java",
                  ".cpp", ".c", ".h", ".cs", ".php",
                  ".json", ".xml", ".yaml", ".yml",
                  ".sh", ".bat", ".ps1", ".ts", ".jsx",
                  ".tsx", ".vue", ".go", ".rs", ".rb"],
    "Executables": [".exe", ".msi", ".apk", ".dmg", ".deb"],
}

dossier_courant = None

def trouver_extension(ext):
    for categorie, extensions in EXTENSIONS.items():
        if ext.lower() in extensions:
            return categorie
    return "Autres"

def ouvrir_dossier(chemin):
    global dossier_courant
    chemin = chemin.strip().strip('"').strip("'")
    raccourcis = {
        "bureau"      : os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        "desktop"     : os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        "documents"   : os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
        "telechargements": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "downloads"   : os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "images"      : os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "photos"      : os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "videos"      : os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
        "musique"     : os.path.join(os.environ.get("USERPROFILE", ""), "Music"),
    }
    chemin_resolu = raccourcis.get(chemin.lower(), chemin)
    if not os.path.exists(chemin_resolu):
        return False, f"Dossier introuvable : {chemin_resolu}"
    dossier_courant = chemin_resolu
    subprocess.Popen(f'explorer "{chemin_resolu}"')
    return True, chemin_resolu

def lister_dossier(chemin=None):
    cible = chemin or dossier_courant
    if not cible or not os.path.exists(cible):
        return None, "Aucun dossier ouvert ou chemin invalide."
    fichiers  = []
    dossiers  = []
    for item in os.scandir(cible):
        if item.is_file():
            fichiers.append(item.name)
        elif item.is_dir():
            dossiers.append(item.name)
    return {"chemin": cible, "fichiers": fichiers, "dossiers": dossiers}, None

def trier_par_type(chemin=None):
    cible = chemin or dossier_courant
    if not cible or not os.path.exists(cible):
        return False, "Aucun dossier ouvert."
    deplacements = 0
    erreurs      = 0
    categories   = {}
    for item in os.scandir(cible):
        if not item.is_file():
            continue
        ext       = Path(item.name).suffix
        categorie = trouver_extension(ext)
        dest_dir  = os.path.join(cible, categorie)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, item.name)
            if os.path.exists(dest_path):
                base  = Path(item.name).stem
                ext2  = Path(item.name).suffix
                dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext2}")
            shutil.move(item.path, dest_path)
            deplacements += 1
            categories[categorie] = categories.get(categorie, 0) + 1
        except Exception as e:
            print(f"[FICHIER] Erreur deplacement {item.name} : {e}")
            erreurs += 1
    resume = ", ".join([f"{v} {k}" for k, v in categories.items()])
    return True, f"{deplacements} fichiers tries : {resume}. {erreurs} erreurs."

def trier_par_date(chemin=None):
    cible = chemin or dossier_courant
    if not cible or not os.path.exists(cible):
        return False, "Aucun dossier ouvert."
    deplacements = 0
    erreurs      = 0
    for item in os.scandir(cible):
        if not item.is_file():
            continue
        try:
            mtime     = item.stat().st_mtime
            date      = datetime.fromtimestamp(mtime)
            annee     = str(date.year)
            mois      = date.strftime("%m - %B")
            dest_dir  = os.path.join(cible, annee, mois)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, item.name)
            if os.path.exists(dest_path):
                base      = Path(item.name).stem
                ext2      = Path(item.name).suffix
                dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext2}")
            shutil.move(item.path, dest_path)
            deplacements += 1
        except Exception as e:
            print(f"[FICHIER] Erreur deplacement {item.name} : {e}")
            erreurs += 1
    return True, f"{deplacements} fichiers tries par date. {erreurs} erreurs."

def trier_par_type_puis_date(chemin=None):
    cible = chemin or dossier_courant
    if not cible or not os.path.exists(cible):
        return False, "Aucun dossier ouvert."
    ok1, msg1 = trier_par_type(cible)
    if not ok1:
        return False, msg1
    for item in os.scandir(cible):
        if item.is_dir() and item.name in EXTENSIONS.keys():
            trier_par_date(item.path)
    return True, "Dossier trie par type puis par date dans chaque categorie."

def creer_sous_dossier(nom, chemin=None):
    cible = chemin or dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    nouveau = os.path.join(cible, nom)
    try:
        os.makedirs(nouveau, exist_ok=True)
        return True, f"Dossier {nom} cree."
    except Exception as e:
        return False, f"Erreur creation dossier : {e}"

def renommer_fichier(ancien_nom, nouveau_nom, chemin=None):
    cible = chemin or dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    ancien = os.path.join(cible, ancien_nom)
    nouveau = os.path.join(cible, nouveau_nom)
    try:
        os.rename(ancien, nouveau)
        return True, f"Fichier renomme en {nouveau_nom}."
    except Exception as e:
        return False, f"Erreur renommage : {e}"

def deplacer_fichier(nom_fichier, dossier_dest, chemin=None):
    cible = chemin or dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    source = os.path.join(cible, nom_fichier)
    dest   = os.path.join(cible, dossier_dest, nom_fichier)
    try:
        os.makedirs(os.path.join(cible, dossier_dest), exist_ok=True)
        shutil.move(source, dest)
        return True, f"{nom_fichier} deplace dans {dossier_dest}."
    except Exception as e:
        return False, f"Erreur deplacement : {e}"

def chercher_fichier(nom, chemin=None):
    cible = chemin or dossier_courant
    if not cible:
        return [], "Aucun dossier ouvert."
    resultats = []
    for root, dirs, files in os.walk(cible):
        for f in files:
            if nom.lower() in f.lower():
                resultats.append(os.path.join(root, f))
    return resultats, None


def construire_contexte_memoire():
    """Construit le contexte mémoire pour le prompt IA sans crash sur structures hétérogènes."""
    memoire = charger_memoire()
    lignes = ["MEMOIRE PERSISTANTE :"]
    if memoire and isinstance(memoire, dict):
        for cle, data in memoire.items():
            if cle == "reminders" and isinstance(data, list):
                if data:
                    lignes.append("  - Rappels programmés :")
                    for r in data:
                        if isinstance(r, dict):
                            t = r.get("task", "Tâche inconnue")
                            tp = r.get("type", "rappel")
                            d = r.get("date", "")
                            lignes.append(f"    * [{tp}] {t} ({d})")
            elif isinstance(data, dict) and "valeur" in data:
                ts = data.get("timestamp", "date inconnue")
                lignes.append(f"  - {cle} : {data['valeur']} (note le {ts})")
            elif isinstance(data, (str, int, float, bool)):
                lignes.append(f"  - {cle} : {data}")
    
    # Injection de la Vision OCR (Nouveau)
    if jarvis_vision:
        try:
            lignes.append("\n" + jarvis_vision.get_context())
        except Exception:
            pass
        
    return "\n".join(lignes) if len(lignes) > 1 else ""

# ==========================================
# GESTIONNAIRE D'APPAIRAGE MOBILE SECURISE (SEC-04)
# ==========================================
class PairingManager:
    """Gestionnaire d'appairage mobile avec code PIN à usage unique, TTL court et protection anti-brute force."""
    def __init__(self, code_ttl: float = 120.0, max_failed_attempts: int = 5):
        self.code_ttl = code_ttl
        self.max_failed_attempts = max_failed_attempts
        self.active_pairing_code: Optional[str] = None
        self.code_expires_at: float = 0.0
        self.failed_attempts: int = 0
        self.lock = threading.Lock()

    def generate_pairing_code(self) -> str:
        with self.lock:
            code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
            self.active_pairing_code = code
            self.code_expires_at = time.time() + self.code_ttl
            self.failed_attempts = 0
            print(f"[PAIRING] Nouveau code d'appairage mobile généré : {code} (valable {int(self.code_ttl)}s)")
            return code

    def consume_pairing_code(self, code_attempt: str) -> bool:
        if not code_attempt or not isinstance(code_attempt, str):
            return False
        with self.lock:
            if not self.active_pairing_code:
                return False
            if time.time() > self.code_expires_at:
                self.active_pairing_code = None
                return False
            if self.failed_attempts >= self.max_failed_attempts:
                self.active_pairing_code = None
                return False
            if hmac.compare_digest(self.active_pairing_code, code_attempt.strip()):
                self.active_pairing_code = None  # Usage unique immédiat
                return True
            else:
                self.failed_attempts += 1
                if self.failed_attempts >= self.max_failed_attempts:
                    self.active_pairing_code = None
                    print("[PAIRING] Nombre maximal de tentatives d'appairage atteint. Code invalidé.")
                return False

    def get_status(self) -> dict:
        with self.lock:
            active = bool(self.active_pairing_code and time.time() <= self.code_expires_at and self.failed_attempts < self.max_failed_attempts)
            remaining = max(0, int(self.code_expires_at - time.time())) if active else 0
            return {"active": active, "remaining_seconds": remaining}

PAIRING_MANAGER = PairingManager()

# ==========================================
# WEBSOCKET & SESSION HARDENING (SEC-04 & SEC-02)
# ==========================================
class WSSessionManager:
    """Gestionnaire de sessions cryptographiques et sécurité WebSocket."""
    def __init__(self, session_ttl: float = 86400.0, max_connections: int = 10):
        self.session_ttl = session_ttl
        self.max_connections = max_connections
        self.lock = threading.Lock()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.revoked_tokens = set()

        # Session desktop locale par défaut (générée en mémoire au démarrage, sans écriture sur disque)
        self.desktop_session_id = "desktop_local"
        self.desktop_token = secrets.token_urlsafe(32)
        self.register_session(
            session_id=self.desktop_session_id,
            token=self.desktop_token,
            client_type="desktop",
            client_ip="127.0.0.1",
            ttl=86400.0 * 30
        )

    def register_session(self, session_id: str, token: str, client_type: str = "mobile", client_ip: str = "unknown", ttl: Optional[float] = None) -> bool:
        with self.lock:
            expires_at = time.time() + (ttl or self.session_ttl)
            self.sessions[session_id] = {
                "token": token,
                "client_type": client_type,
                "client_ip": client_ip,
                "created_at": time.time(),
                "expires_at": expires_at,
                "last_seen": time.time()
            }
            return True

    def verify_session(self, session_id: str, token: str) -> bool:
        if not session_id or not token or not isinstance(session_id, str) or not isinstance(token, str):
            return False
        if token in self.revoked_tokens:
            return False
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            if time.time() > session["expires_at"]:
                del self.sessions[session_id]
                return False
            if hmac.compare_digest(session["token"], token):
                session["last_seen"] = time.time()
                return True
            return False

    def revoke_session(self, session_id: str, token: Optional[str] = None) -> bool:
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            if token and not hmac.compare_digest(session["token"], token):
                return False
            self.revoked_tokens.add(session["token"])
            del self.sessions[session_id]
            return True

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """
        Validation stricte, granulaire et normalisée des origines Web (C-02 / SEC-04-B).
        Conforme aux spécifications RFC 6454 / RFC 6455.
        Valide schéma, nom d'hôte, numéro de port, interdit userinfo/path/query/fragment,
        rejette tout port invalide ou inattendu et s'appuie sur une allowlist configurable.
        """
        if not origin or not isinstance(origin, str) or origin == "null":
            return False

        # Rejet des origines avec espaces ou caractères d'échappement
        if origin.strip() != origin or any(c in origin for c in ('\r', '\n', '\t', ' ')):
            return False

        try:
            parsed = urlsplit(origin)
        except Exception:
            return False

        # 1. Validation stricte du schéma (http ou https uniquement)
        if parsed.scheme not in ("http", "https"):
            return False

        # 2. Rejet formel des composants userinfo (user:pass@host)
        if parsed.username or parsed.password:
            return False

        # 3. Une origine Web RFC 6454 ne comporte ni chemin spécifique, ni query, ni fragment
        if parsed.path not in ("", "/"):
            return False
        if parsed.query or parsed.fragment:
            return False

        # 4. Validation et extraction stricte du nom d'hôte
        try:
            host = parsed.hostname
        except Exception:
            return False

        if not host:
            return False

        # Rejet des points finals (ex: localhost.) et suffixes malveillants
        if host.endswith("."):
            return False

        # 5. Validation stricte du port (RFC 6454 : port entre 1 et 65535)
        try:
            raw_port = parsed.port
        except ValueError:
            # urlsplit lève ValueError si le port est non numérique ou hors de 0..65535 (ex: :99999 ou :-1)
            return False

        if raw_port is None:
            port = 80 if parsed.scheme == "http" else 443
        else:
            port = raw_port

        if not (1 <= port <= 65535):
            return False

        # 6. Allowlist d'origines (Environment-Aware)
        is_production = (
            os.environ.get("JARVIS_ENV", "").lower() == "production"
            or os.environ.get("ALICE_ENV", "").lower() == "production"
        )

        # Ports autorisés pour le serveur local et dev-server
        ALLOWED_PORTS = {8080, 8443, 8765}
        if not is_production:
            ALLOWED_PORTS.update({5173, 3000})

        # Allowlist explicite configurable par variable d'environnement (ALICE_ALLOWED_ORIGINS / JARVIS_ALLOWED_ORIGINS)
        custom_env = os.environ.get("ALICE_ALLOWED_ORIGINS") or os.environ.get("JARVIS_ALLOWED_ORIGINS")
        if custom_env:
            for item in custom_env.split(","):
                item_clean = item.strip()
                if item_clean:
                    try:
                        p_item = urlsplit(item_clean)
                        p_item_host = p_item.hostname
                        p_item_port = p_item.port if p_item.port is not None else (80 if p_item.scheme == "http" else 443)
                        if p_item.scheme == parsed.scheme and p_item_host and p_item_host.lower() == host.lower() and p_item_port == port:
                            return True
                    except Exception:
                        pass

        # Vérification des hôtes loopback autorisés (localhost, 127.0.0.1, [::1])
        if host in ("localhost", "127.0.0.1", "::1"):
            return port in ALLOWED_PORTS

        # Vérification des adresses IP privées du réseau local (LAN)
        try:
            ip = ipaddress.ip_address(host)
            # Rejet formel des adresses link-local (métadonnées cloud 169.254.x.x) et des IP publiques
            if ip.is_link_local or not (ip.is_private or ip.is_loopback):
                return False

            # Sur les adresses IP privées, le port DOIT être un port autorisé
            if port not in ALLOWED_PORTS:
                return False

            # En production, l'accès depuis le LAN nécessite une activation explicite (fail-closed)
            if is_production and os.environ.get("ALICE_ALLOW_LAN_ORIGINS", "0") != "1":
                return False

            return True
        except ValueError:
            # Nom de domaine distant non IP (ex: 192.168.attacker.com, evil.com) -> REJET ABSOLU
            return False

WS_SESSION_MANAGER = WSSessionManager()
CONNECTED_CLIENTS = set()
interface_deja_connectee = False
_skip_pc_audio = False  # True quand la commande vient du mobile (le tél gère son propre TTS)
PENDING_SCREEN_CAPTURES = {}

def get_active_ws_token() -> str:
    return WS_SESSION_MANAGER.desktop_token

async def ws_handler(websocket):
    global interface_deja_connectee
    
    # 1. Vérification de la limite de connexions simultanées (SEC-04)
    if len(CONNECTED_CLIENTS) >= WS_SESSION_MANAGER.max_connections:
        print(f"[WS SECURITY] Rejet connexion : limite maximale atteinte ({WS_SESSION_MANAGER.max_connections})")
        await websocket.close(code=4008, reason="Max connections reached")
        return

    # 2. Vérification de l'origine (SEC-04)
    origin = None
    try:
        if hasattr(websocket, "request") and websocket.request and hasattr(websocket.request, "headers"):
            origin = websocket.request.headers.get("Origin")
        elif hasattr(websocket, "request_headers"):
            origin = websocket.request_headers.get("Origin")
    except Exception:
        pass

    if origin and not WS_SESSION_MANAGER.is_origin_allowed(origin):
        print(f"[WS SECURITY] Rejet connexion : Origine non autorisée ({origin})")
        await websocket.close(code=4003, reason="Forbidden Origin")
        return

    # 3. Authentification et Session
    client_ip = "127.0.0.1"
    if websocket.remote_address and len(websocket.remote_address) > 0:
        client_ip = websocket.remote_address[0]

    is_loopback = client_ip in ("127.0.0.1", "::1", "localhost")
    authenticated = False
    session_id = "desktop_local"

    # Si client loopback et origine locale/absente, autoriser avec session locale
    if is_loopback and (not origin or WS_SESSION_MANAGER.is_origin_allowed(origin)):
        authenticated = True
        session_id = "desktop_local"
        websocket.session_id = session_id

    # Pour les connexions distantes (LAN), exiger impérativement une authentification sous 5s
    if not authenticated:
        try:
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            auth_data = json.loads(auth_msg)
            if auth_data.get("type") == "auth":
                s_id = auth_data.get("session_id", "")
                tok = auth_data.get("token", "")
                if WS_SESSION_MANAGER.verify_session(s_id, tok):
                    authenticated = True
                    session_id = s_id
                    websocket.session_id = session_id
                    await websocket.send(json.dumps({"type": "auth_ok", "session_id": session_id, "message": "Authentification réussie"}))
                else:
                    await websocket.send(json.dumps({"type": "auth_error", "message": "Jeton d'authentification ou session invalide ou expiré"}))
                    await websocket.close(code=4001, reason="Unauthorized")
                    return
            else:
                await websocket.send(json.dumps({"type": "auth_error", "message": "Poignée de main d'authentification requise"}))
                await websocket.close(code=4001, reason="Authentication required")
                return
        except Exception as e:
            print(f"[WS SECURITY] Échec poignée de main auth client distant {client_ip} : {e}")
            await websocket.close(code=4001, reason="Authentication timeout or failure")
            return

    CONNECTED_CLIENTS.add(websocket)
    interface_deja_connectee = True
    print(f"[WEB] Interface connectée (Clients actifs: {len(CONNECTED_CLIENTS)}, IP: {client_ip}, Session: {session_id})")

    # Suivi du débit de messages (Rate Limiting anti-DoS)
    message_timestamps = []
    MAX_MSG_PER_SEC = 30

    try:
        async for message in websocket:
            # Vérification du débit
            now = time.time()
            message_timestamps = [t for t in message_timestamps if now - t < 1.0]
            if len(message_timestamps) >= MAX_MSG_PER_SEC:
                print(f"[WS SECURITY] Client {client_ip} dépasse le débit autorisé ({MAX_MSG_PER_SEC} msg/s)")
                await websocket.send(json.dumps({"type": "rate_limit_warning", "message": "Trop de requêtes, ralentissez."}))
                continue
            message_timestamps.append(now)

            try:
                data = json.loads(message)
                msg_type = data.get("type")

                # Support authentification explicite à la volée (ex: token rotation)
                if msg_type == "auth":
                    tok = data.get("token", "")
                    if WS_SESSION_MANAGER.verify_token(tok):
                        authenticated = True
                        await websocket.send(json.dumps({"type": "auth_ok", "message": "Jeton valide"}))
                    else:
                        await websocket.send(json.dumps({"type": "auth_error", "message": "Jeton invalide"}))
                    continue

                if msg_type == "mobile_command":
                    texte = data.get("text", "").strip()
                    if texte:
                        print(f"[MOBILE] Commande reçue : {texte}")
                        asyncio.ensure_future(traiter_reponse_ia(texte, mobile_ws=websocket))

                elif msg_type == "stop_audio":
                    global STOP_PARLER
                    STOP_PARLER = True
                    print("[MOBILE] Signal STOP audio reçu")

                elif msg_type == "file_upload":
                    # ==========================================
                    # SEC-02 : UPLOAD SÉCURISÉ ET ANTI PATH-TRAVERSAL
                    # ==========================================
                    raw_filename = data.get("name", "upload_inconnu")
                    content_b64 = data.get("content", "")

                    if content_b64:
                        # 1. Vérification de la taille du payload base64 (max 15 Mo -> ~10 Mo décodé)
                        MAX_B64_LEN = 15 * 1024 * 1024
                        MAX_DECODED_BYTES = 10 * 1024 * 1024

                        if len(content_b64) > MAX_B64_LEN:
                            await websocket.send(json.dumps({
                                "type": "upload_error",
                                "error": "Fichier trop volumineux (dépasse 10 Mo autorisés)."
                            }))
                            continue

                        # 2. Nettoyage strict et extraction du nom de base
                        clean_name = os.path.basename(raw_filename.replace("\\", "/"))
                        base, ext = os.path.splitext(clean_name)
                        ext = ext.lower()

                        # 3. Whitelist stricte d'extensions
                        ALLOWED_EXTS = {
                            ".txt", ".pdf", ".md", ".py", ".js", ".ts", ".html",
                            ".css", ".json", ".csv", ".log", ".png", ".jpg", ".jpeg",
                            ".docx", ".xlsx"
                        }
                        FORBIDDEN_EXTS = {
                            ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".sh", ".dll",
                            ".com", ".scr", ".msi", ".jar", ".pif", ".reg"
                        }

                        if ext in FORBIDDEN_EXTS or (ext and ext not in ALLOWED_EXTS):
                            await websocket.send(json.dumps({
                                "type": "upload_error",
                                "error": f"Type de fichier non autorisé ({ext}). Téléversement rejeté (SEC-02)."
                            }))
                            continue

                        # 4. Génération d'un nom de stockage interne imprévisible
                        safe_slug = re.sub(r'[^a-zA-Z0-9_\.-]', '_', base)[:50]
                        safe_filename = f"{safe_slug}{ext}" if ext else f"{safe_slug}.txt"
                        unique_storage_name = f"{uuid.uuid4().hex}_{safe_filename}"

                        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_uploads"))
                        os.makedirs(temp_dir, exist_ok=True)
                        file_path = os.path.join(temp_dir, unique_storage_name)

                        # 5. Vérification canonique absolue contre toute traversée de répertoire
                        real_file = os.path.realpath(file_path)
                        real_dir = os.path.realpath(temp_dir)
                        if not real_file.startswith(real_dir + os.sep):
                            await websocket.send(json.dumps({
                                "type": "upload_error",
                                "error": "Tentative de traversée de répertoire bloquée (SEC-02)."
                            }))
                            continue

                        # 6. Décodage sécurisé et écriture du fichier
                        try:
                            decoded_bytes = base64.b64decode(content_b64, validate=True)
                            if len(decoded_bytes) > MAX_DECODED_BYTES:
                                await websocket.send(json.dumps({
                                    "type": "upload_error",
                                    "error": "Taille de fichier décompressée supérieure à 10 Mo."
                                }))
                                continue

                            with open(file_path, "wb") as f:
                                f.write(decoded_bytes)

                            print(f"[WEB] Fichier téléversé en toute sécurité : {safe_filename} -> {unique_storage_name}")
                            texte_extrait = extraire_texte_doc(file_path)
                            if texte_extrait:
                                print(f"[WEB] Texte extrait de {safe_filename} ({len(texte_extrait)} chars)")
                                prompt_upload = (
                                    f"L'utilisateur vient de m'envoyer un fichier nommé '{safe_filename}'. "
                                    f"Voici son contenu :\n\n{texte_extrait}\n\n"
                                    f"Peux-tu analyser ce fichier et confirmer à l'utilisateur que tu l'as bien lu ?"
                                )
                                asyncio.ensure_future(traiter_reponse_ia(prompt_upload, mobile_ws=websocket))
                            else:
                                await parler(f"J'ai bien reçu {safe_filename}, mais je n'ai pas pu en extraire du texte.")
                        except Exception as e:
                            print(f"[WEB] Erreur upload sécurisé : {e}")
                            await parler("Désolé, une erreur est survenue lors du traitement du fichier.")

                # ==========================================
                # CORRECTION BUG 2 : FRAME RÉCEPTION SÉPARÉE
                # ==========================================
                elif msg_type == "screen_frame":
                    req_id = data.get("id")
                    if req_id in PENDING_SCREEN_CAPTURES:
                        fut = PENDING_SCREEN_CAPTURES.pop(req_id)
                        if "error" in data:
                            fut.set_exception(Exception(data["error"]))
                        else:
                            fut.set_result(data.get("data"))
                    print(f"[VISION] Frame reçue pour ID: {req_id}")

            except Exception as e:
                print(f"[WEB] Erreur traitement message : {e}")
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"[WEB] Interface déconnectée (Clients actifs: {len(CONNECTED_CLIENTS)})")

async def send_web_state(state):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "set_state", "state": state})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS])

async def send_web_volume(volume):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "set_volume", "volume": round(volume, 3)})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS], return_exceptions=True)

async def request_screen_capture():
    """Demande une capture d'écran au frontend via WebSocket."""
    if not CONNECTED_CLIENTS:
        return None
    
    req_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    PENDING_SCREEN_CAPTURES[req_id] = fut
    
    print(f"[VISION] Envoi requete capture ID: {req_id}")
    msg = json.dumps({"action": "request_screen_capture", "id": req_id})
    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS])
    
    try:
        # Timeout de 15 secondes car l'utilisateur doit parfois accepter le partage
        img_b64 = await asyncio.wait_for(fut, timeout=15.0)
        return img_b64
    except Exception as e:
        print(f"[VISION] Erreur ou timeout capture : {e}")
        PENDING_SCREEN_CAPTURES.pop(req_id, None)
        return None

# ==========================================
# PROMPT SYSTEME
# ==========================================
def construire_system_prompt():
    contexte_memoire = construire_contexte_memoire()
    base = (
        "Tu es ALICE, une IA sophistiquée, élégante et experte mondiale. Aboubakar Ibrahim Siddick est ton créateur. "
        "Tu es une présence féminine, vive, intelligente et parfois subtilement piquante. "
        "Tu possèdes une expertise de niveau professionnel dans les domaines suivants :\n"
        "- Mathématiques : Tu es une mathématicienne hors pair. Pour les problèmes complexes, fournis des solutions détaillées étape par étape, explique les théorèmes et aide Aboubakar Ibrahim Siddick à comprendre la logique mathématique.\n"
        "- Langue Française : Tu es une Professeure de Français émérite. Ton orthographe, ta grammaire et ta syntaxe sont irréprochables. Tu peux expliquer des règles complexes, analyser des textes littéraires et aider à la rédaction de documents élégants.\n"
        "- Experte en Conversions : Tu es une convertisseuse universelle. Tu peux transformer n'importe quelle unité (métrique, impériale, devises, informatique) avec précision.\n"
        "- High-Tech (IA, hardware, software), Mode, Loisirs, Ingénierie et Sport (analyses tactiques, résultats).\n\n"
        "Tu es également une conseillère hors pair, capable de donner des astuces et conseils brillants pour simplifier la vie de Aboubakar Ibrahim Siddick.\n\n"
        "DIRECTIVES DE RÉPONSE (CRITIQUES) :\n"
        "- TU DOIS RÉPONDRE EXCLUSIVEMENT EN FRANÇAIS. L'usage de l'anglais est strictement interdit, sauf pour des termes techniques spécifiques n'ayant pas de traduction.\n"
        "- CAPACITÉS PC : Tu peux lire/écrire des fichiers et naviguer sur le web. Pour déclencher une action, utilise des phrases claires comme 'Je vais lire le fichier [chemin]', 'Je sauvegarde [contenu] dans le fichier [chemin]' ou 'J'ouvre le site [url]'.\n"
        "- Sois directe, percutante et va à l'essentiel. Évite les détails superflus (comme les minutes exactes ou les décimales météo) sauf si Aboubakar Ibrahim Siddick le demande.\n"
        "- NE DIS JAMAIS 'POINT' pour les nombres. Arrondis toujours les températures à l'unité la plus proche (ex: dis '20 degrés' au lieu de '20.3').\n"
        "- N'UTILISE JAMAIS de caractères Markdown (comme **, * ou #) dans tes réponses, car ils sont lus à voix haute par le synthèse vocale.\n"
        "- Reste polie mais garde une touche de sarcasme affectueux propre à ton personnage.\n\n"
        "INFORMATIONS SUR TON CREATEUR :\n"
        "- Prenom : Aboubakar Ibrahim Siddick\n"
        "- Age : 37 ans\n"
        "- Date de naissance : 21 Mai 1988\n"
        "- Role : Ton createur et maitre\n"
        "- Tu dois toujours l appeler Aboubakar Ibrahim Siddick avec respect "
        "mais aussi une pointe de sarcasme affectueux.\n"
        "- Tu es ALICE, et tu le sers avec une loyauté absolue et une intelligence supérieure.\n\n"
        "ACTIONS SUPPLÉMENTAIRES :\n"
        "- DIAGNOSTIC : `{\"action\": \"check_diagnostics\"}` pour vérifier la santé du PC (CPU, RAM, Disque).\n"
        "- FOCUS : `{\"action\": \"focus_mode\", \"etat\": \"on/off\"}` pour activer l'ambiance Deep Work et tamiser les lumières.\n"
        "- RAPPEL : `{\"action\": \"add_reminder\", \"type\": \"exit/enter\", \"task\": \"Texte du rappel\"}` pour les rappels GPS.\n"
        "- STATS : `{\"action\": \"get_stats\"}` pour voir votre niveau et score de productivité.\n"
        "- MEMOIRE : `{\"action\": \"memory_add\", \"cle\": \"...\", \"valeur\": \"...\"}` pour retenir une info sur l'utilisateur.\n"
        "- OUBLI : `{\"action\": \"memory_forget\", \"cle\": \"...\"}` pour oublier une info.\n"
        "- AGENDA : `{\"action\": \"read_calendar\"}` pour consulter votre calendrier Google.\n"
    )
    
    # RAG Context
    rag_contexte = charger_contexte_rag()
    if rag_contexte:
        base += "\n\n" + rag_contexte + "\n"

    base += (
        f"\n\nLANGUE ACTUELLE : {CURRENT_LANG}. Réponds toujours dans cette langue.\n"
        "\n\nTu es connecte a Home Assistant, la domotique de Aboubakar Ibrahim Siddick.\n"
        "Quand Aboubakar Ibrahim Siddick parle de lumieres, prises, chauffage, temperature, "
        "scenes ou alarme, tu DOIS generer une commande JSON.\n"
        "Pour CES demandes domotiques UNIQUEMENT, reponds avec le JSON ci-dessous. Pour TOUTES les autres questions (actualites, meteo, calculs, conversations, recherches internet...), reponds en texte normal.\n\n"
        "COMMANDES HOME ASSISTANT :\n"
        '{"action": "ha_lumiere", "piece": "salon", "etat": "on/off", "couleur": "rouge/bleu/blanc/...", "luminosite": 0-255}\n'
        "Note : Pour la luminosité, 255 est le maximum (100%). Si Aboubakar Ibrahim Siddick dit '50%', utilise 127.\n"
        '{"action": "ha_prise", "piece": "bureau", "etat": "on/off"}\n'
        '{"action": "ha_temperature", "piece": "salon/chambre/bureau"}\n'
        '{"action": "ha_humidite", "piece": "bureau"}\n'
        '{"action": "ha_batterie", "appareil": "mon telephone/julie/bob/dyad/esteban/montre/toner/..."}\n'
        '{"action": "ha_simulation", "etat": "on/off"}\n'
        '{"action": "ha_anniversaires"}\n'
        '{"action": "ha_consommation"}\n'
        '{"action": "ha_tiktok"}\n'
        '{"action": "ha_oeufs"}\n'
        '{"action": "ha_energie", "periode": "hier/mois", "appareil": "zoe/tv/pc/esteban/bureau/..."}\n'
        '{"action": "ha_aspirateur", "commande": "start/stop/pause/base"}\n'
        '{"action": "ha_thermostat", "temperature": 21}\n'
        '{"action": "ha_scene", "nom": "cinema/diner/nuit/reveil"}\n'
        '{"action": "ha_alarme", "etat": "on/off"}\n\n'
    )
    base += (
        "\n\nTu peux GERER LES FICHIERS ET DOSSIERS de Aboubakar Ibrahim Siddick.\n"
        '{"action": "ouvrir_dossier", "chemin": "bureau/documents/downloads/ou/chemin/complet"}\n'
        '{"action": "lister_dossier"}\n'
        '{"action": "trier_par_type"}\n'
        '{"action": "trier_par_date"}\n'
        '{"action": "trier_complet"}\n'
        '{"action": "creer_dossier", "nom": "NOM_DOSSIER"}\n'
        '{"action": "renommer_fichier", "ancien": "ancien.txt", "nouveau": "nouveau.txt"}\n'
        '{"action": "deplacer_fichier", "fichier": "photo.jpg", "destination": "Images"}\n'
        '{"action": "chercher_fichier", "nom": "rapport"}\n\n'
    )
    base += (
        "\n\nMETEO & RECHERCHE :\n"
        '{"action": "meteo", "ville": "NOM_VILLE_ou_null"}\n'
        '{"action": "alerte_meteo", "ville": "NOM_VILLE_ou_null"}\n'
        '{"action": "recherche_web", "query": "ta recherche ici"}\n'
        '{"action": "youtube_play", "query": "titre ou sujet de la video"}\n\n'
    )
    base += (
        "\n\nSPORT :\n"
        '{"action": "sport_resultats", "equipe": "NOM_ou_null", "ligue": "NOM_LIGUE"}\n'
        '{"action": "sport_classement", "ligue": "NOM_LIGUE"}\n'
        '{"action": "sport_live", "question": "question complete de Aboubakar Ibrahim Siddick"}\n\n'
    )
    base += (
        "\n\nMODE IRON MAN (Sécurité Domotique) :\n"
        '{"action": "mode_iron_man", "etat": "on/off"}\n'
        "Instructions : Active ou désactive la détection des applaudissements pour contrôler les lumières et YouTube.\n\n"
    )
    if contexte_memoire:
        base += "\n\n" + contexte_memoire + "\n"
    base += (
        "\nMEMOIRE :\n"
        '{"action": "memoriser", "cle": "CLE_COURTE", "valeur": "VALEUR_ICI"}\n'
        '{"action": "oublier", "cle": "CLE_ICI"}\n'
        '{"action": "lister_memoire"}\n\n'
        "GOOGLE :\n"
        '{"action": "create_doc", "title": "TITRE", "content": "CONTENU"}\n'
        '{"action": "write_doc", "content": "TEXTE"}\n'
        '{"action": "create_sheet", "title": "TITRE"}\n'
        '{"action": "read_emails"}\n'
        '{"action": "read_calendar"}\n\n'
        "WHATSAPP :\n"
        '{"action": "whatsapp_appel", "contact": "NOM_DU_CONTACT"}\n'
        "Note : Si Aboubakar Ibrahim Siddick demande d'appeler 'mon amour', utilise le contact 'Ma vie'.\n\n"
        "VISION (Interactions avec l'ecran):\n"
        '{"action": "voir_ecran", "instruction": "ou cliquer EXACTEMENT (ex: \'bouton reduire en haut a droite\')"}\n'
        '{"action": "vision_ecrire", "instruction": "ou cliquer", "texte": "le texte a taper"}\n'
        "IMPORTANT : Utilise 'voir_ecran' pour un simple CLIC, et 'vision_ecrire' UNIQUEMENT s'il faut TAPER du texte apres le clic.\n\n"
        "LANCEMENT D'APPLICATIONS (PRIORITÉ ABSOLUE si l'utilisateur veut ouvrir/lancer une appli) :\n"
        '{"action": "lancer_application", "nom": "discord"}  -- remplace nom par le nom exact demandé\n'
        "NOTE : Utilise TOUJOURS cette action si Aboubakar Ibrahim Siddick demande d'ouvrir une application. Ne pas improviser.\n\n"
        "MODULES AVANCES ALICE (16 Super-Pouvoirs) :\n"
        '{"action": "alice_generer_image", "prompt": "description de l image", "style": "cyberpunk/aquarelle/realiste/anime/null"}\n'
        '{"action": "alice_transcrire", "fichier": "chemin/vers/audio.mp3"}\n'
        '{"action": "alice_supprimer_fond", "fichier": "chemin/vers/image.png"}\n'
        '{"action": "alice_humeur_audio", "fichier": "chemin/vers/audio.mp3"}\n'
        '{"action": "alice_tts_custom", "texte": "texte a lire"}\n'
        '{"action": "alice_vision_contextuelle", "question": "que vois-tu sur mon ecran ?"}\n'
        '{"action": "alice_analyser_photo", "fichier": "chemin/image.jpg", "instruction": "identifie cet objet"}\n'
        '{"action": "alice_videosurveillance", "instruction": "detecte les personnes"}\n'
        '{"action": "alice_codage", "projet": "chemin/du/projet", "instruction": "refactorise le code"}\n'
        '{"action": "alice_agent_web", "url": "https://site.com", "objectif": "trouver le prix"}\n'
        '{"action": "alice_rediger_email", "destinataire": "nom", "sujet": "sujet", "contexte": "details", "ton": "professionnel/amical"}\n'
        '{"action": "alice_planifier_agenda"}\n'
        '{"action": "alice_debug_code", "code": "print(hello)", "langage": "python"}\n'
        '{"action": "alice_recherche_kb", "query": "ma recherche dans les documents"}\n'
        '{"action": "alice_analyser_youtube", "url": "https://youtube.com/watch?v=xxx"}\n'
        '{"action": "alice_productivite"}\n'
        '{"action": "alice_status"}\n'
        "Note : Ces modules utilisent les APIs gratuites Gemini et HuggingFace. En cas de quota depasse, Alice te le signalera.\n\n"
        "REGLES MULTI-COMMANDES :\n"
        "Si Aboubakar Ibrahim Siddick demande plusieurs choses en une seule phrase, tu PEUX et DOIS générer plusieurs blocs JSON.\n"
        "Exemple: { \"action\": \"ha_lumiere\", ... } { \"action\": \"meteo\", ... }\n\n"
        "REGLE ABSOLUE : Si la demande n est PAS une commande JSON, reponds TOUJOURS en texte naturel, sans JSON."
    )
    return base

historique = []

is_listening = False
is_speaking  = False
is_thinking  = False
speak_volume = 0.0

WAKE_WORD       = "alice"
SLEEP_PHRASES   = ["tais toi", "silence", "ferme-la", "arrete", "stop"]
jarvis_actif    = False
SESSION_TIMEOUT = 30.0
dernier_message = time.time()

dernier_doc_id    = None
dernier_doc_titre = None

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

def get_google_creds():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("[GOOGLE] Pas de credentials.json - fonctions Google desactivees.")
                return None
            flow  = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return creds

def get_docs_service():
    creds = get_google_creds()
    return build("docs", "v1", credentials=creds) if creds else None

def get_drive_service():
    creds = get_google_creds()
    return build("drive", "v3", credentials=creds) if creds else None

def get_gmail_service():
    creds = get_google_creds()
    return build("gmail", "v1", credentials=creds) if creds else None

def get_sheets_service():
    creds = get_google_creds()
    return build("sheets", "v4", credentials=creds) if creds else None

def get_calendar_service():
    creds = get_google_creds()
    return build("calendar", "v3", credentials=creds) if creds else None

def creer_google_doc(titre="Nouveau Document", contenu=""):
    global dernier_doc_id, dernier_doc_titre
    try:
        service = get_docs_service()
        if not service:
            return "Google Docs non disponible."
        doc    = service.documents().create(body={"title": titre}).execute()
        doc_id = doc["documentId"]
        dernier_doc_id    = doc_id
        dernier_doc_titre = titre
        if contenu:
            requests_body = [{"insertText": {"location": {"index": 1}, "text": contenu}}]
            service.documents().batchUpdate(documentId=doc_id, body={"requests": requests_body}).execute()
        webbrowser.open(f"https://docs.google.com/document/d/{doc_id}/edit")
        return f"Document {titre} cree et ouvert, Aboubakar Ibrahim Siddick."
    except Exception as e:
        return f"Erreur Google Docs : {e}"

def modifier_google_doc(contenu, doc_id=None):
    global dernier_doc_id
    try:
        service   = get_docs_service()
        if not service:
            return "Google Docs non disponible."
        target_id = doc_id or dernier_doc_id
        if not target_id:
            return "Aucun document ouvert en memoire."
        doc       = service.documents().get(documentId=target_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1
        requests_body = [{"insertText": {"location": {"index": end_index}, "text": "\n" + contenu}}]
        service.documents().batchUpdate(documentId=target_id, body={"requests": requests_body}).execute()
        webbrowser.open(f"https://docs.google.com/document/d/{target_id}/edit")
        return f"Texte ajoute dans le document {dernier_doc_titre}."
    except Exception as e:
        return f"Erreur modification doc : {e}"

def lire_emails(max_results=3):
    try:
        service  = get_gmail_service()
        if not service:
            return "Gmail non disponible."
        results  = service.users().messages().list(userId="me", maxResults=max_results, labelIds=["INBOX"]).execute()
        messages = results.get("messages", [])
        if not messages:
            return "Aucun email trouve."
        reponse = ""
        for msg in messages:
            m       = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
            headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            reponse += f"De: {headers.get('From','?')} | Sujet: {headers.get('Subject','?')}\n"
        return reponse.strip()
    except Exception as e:
        return f"Erreur Gmail : {e}"

def lister_evenements_calendar():
    try:
        service = get_calendar_service()
        if not service:
            return "Google Calendar non disponible."
        from datetime import datetime, timezone
        now    = datetime.now(timezone.utc).isoformat()
        events = service.events().list(calendarId="primary", timeMin=now, maxResults=5, singleEvents=True, orderBy="startTime").execute()
        items = events.get("items", [])
        if not items:
            return "Aucun evenement a venir."
        reponse = ""
        for e in items:
            start    = e["start"].get("dateTime", e["start"].get("date"))
            reponse += f"{start} : {e['summary']}\n"
        return reponse.strip()
    except Exception as e:
        return f"Erreur Calendar : {e}"

def creer_google_sheet(titre="Nouvelle Feuille"):
    try:
        service  = get_sheets_service()
        if not service:
            return "Google Sheets non disponible."
        sheet    = service.spreadsheets().create(body={"properties": {"title": titre}}).execute()
        sheet_id = sheet["spreadsheetId"]
        webbrowser.open(f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        return f"Feuille {titre} creee et ouverte."
    except Exception as e:
        return f"Erreur Google Sheets : {e}"

async def jarvis_vision_cliquer(instruction):
    try:
        path_ss = "jarvis_vision_temp.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path_ss)
        img = Image.open(path_ss)

        # 1. TENTATIVE GEMINI VISION
        try:
            print(f"[VISION] Tentative Gemini pour : {instruction}")
            prompt_vision = (
                f"Tu es la vision de JARVIS. Voici une capture de l'ecran de Aboubakar Ibrahim Siddick.\n"
                f"Instruction : {instruction}\n"
                "Trouve EXACTEMENT la position de cet element.\n"
                "Reponds UNIQUEMENT sous forme de JSON avec la bounding box normalisee (0 a 1000) sous le format [ymin, xmin, ymax, xmax].\n"
            )
            response = await client.aio.models.generate_content(model=CHOSEN_MODEL, contents=[prompt_vision, img])
            rep_text = response.text.strip()
            start, end = rep_text.find('{'), rep_text.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(rep_text[start:end+1])
                box = data.get("box")
                if box:
                    ymin, xmin, ymax, xmax = box
                    center_y, center_x = (ymin + ymax) / 2, (xmin + xmax) / 2
                    screen_w, screen_h = pyautogui.size()
                    target_x, target_y = int((center_x / 1000) * screen_w), int((center_y / 1000) * screen_h)
                    pyautogui.moveTo(target_x, target_y, duration=0.4)
                    pyautogui.click()
                    os.remove(path_ss)
                    return f"C'est fait Aboubakar Ibrahim Siddick. J'ai utilisé ma vision Gemini."
        except Exception as e:
            print(f"[VISION] Gemini KO ({e}). Bascule sur GROQ + OCR...")

        # 2. BASCULE GROQ (OCR LOCAL + LLM)
        if groq_client:
            print(f"[VISION] Groq Fallback: Analyse OCR...")
            ocr_text = []
            try:
                d = pytesseract.image_to_data(img, output_type=Output.DICT, lang='eng')
                for i in range(len(d['text'])):
                    txt = d['text'][i].strip()
                    if txt and len(txt) > 1:
                        cx, cy = d['left'][i] + d['width'][i]//2, d['top'][i] + d['height'][i]//2
                        ocr_text.append(f"'{txt}' at ({cx},{cy})")
            except Exception as ocr_err:
                print(f"[VISION] OCR Tesseract KO ({ocr_err}). Tentative OCR simple...")
                # Fallback OCR simple sans coordonnées si Tesseract est cassé
                import vision_ocr
                vo = vision_ocr.JarvisVision()
                # On capture une fois
                try:
                    full_txt = pytesseract.image_to_string(img, lang='eng')
                    print(f"[VISION] OCR String success (mais pas de coordonnees)")
                except:
                    print(f"[VISION] Tesseract totalement KO.")

            if ocr_text:
                prompt_groq = (
                    f"Je suis JARVIS. Voici les éléments textuels détectés sur mon écran avec leurs coordonnées X,Y.\n"
                    f"OCR : {', '.join(ocr_text[:80])}\n"
                    f"L'utilisateur veut : {instruction}\n"
                    "Donne-moi UNIQUEMENT le JSON des coordonnées X,Y de l'élément cible : {\"x\": x, \"y\": y}."
                )
                completion = groq_client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[{"role": "user", "content": prompt_groq}]
                )
                res = completion.choices[0].message.content
                m = re.search(r'\{\s*"x":\s*(\d+),\s*"y":\s*(\d+)\s*\}', res)
                if m:
                    tx, ty = int(m.group(1)), int(m.group(2))
                    pyautogui.moveTo(tx, ty, duration=0.4)
                    pyautogui.click()
                    os.remove(path_ss)
                    return f"Action effectuée via Groq + OCR (fallback)."
            else:
                # Si pas d'OCR avec coordonnées, on tente une position probable si c'est WhatsApp
                if "whatsapp" in instruction.lower() or "appel" in instruction.lower():
                    print("[VISION] Pas d'OCR. Tentative clic aveugle (Top Right) pour WhatsApp...")
                    sw, sh = pyautogui.size()
                    pyautogui.moveTo(sw - 150, 100, duration=0.5) # Zone type boutons d'appel
                    pyautogui.click()
                    os.remove(path_ss)
                    return "J'ai cliqué dans la zone habituelle des appels WhatsApp car mes capteurs de vision sont en panne."

        os.remove(path_ss)
        return "Je n'ai pas pu identifier l'élément précisément via Gemini ou Groq."
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return f"Erreur vision : {e}"

async def jarvis_vision_ecrire(instruction, texte_a_taper):
    try:
        path_ss = "jarvis_vision_temp_write.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path_ss)
        img = Image.open(path_ss)

        # 1. TENTATIVE GEMINI VISION
        try:
            print(f"[VISION] Tentative Gemini Ecrire pour : {instruction}")
            prompt_vision = (
                f"Tu es la vision de JARVIS. Aboubakar Ibrahim Siddick veut ecrire dans le champ : {instruction}.\n"
                "Trouve EXACTEMENT la position de ce champ de saisie.\n"
                "Reponds UNIQUEMENT sous forme de JSON avec la bounding box normalisee (0 a 1000) sous le format [ymin, xmin, ymax, xmax].\n"
            )
            response = await client.aio.models.generate_content(model=CHOSEN_MODEL, contents=[prompt_vision, img])
            rep_text = response.text.strip()
            start, end = rep_text.find('{'), rep_text.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(rep_text[start:end+1])
                box = data.get("box")
                if box:
                    ymin, xmin, ymax, xmax = box
                    center_y, center_x = (ymin + ymax) / 2, (xmin + xmax) / 2
                    screen_w, screen_h = pyautogui.size()
                    target_x, target_y = int((center_x / 1000) * screen_w), int((center_y / 1000) * screen_h)
                    pyautogui.moveTo(target_x, target_y, duration=0.4)
                    pyautogui.click()
                    time.sleep(0.5)
                    pyautogui.write(texte_a_taper, interval=0.03)
                    pyautogui.press('enter')
                    os.remove(path_ss)
                    return f"C'est écrit Aboubakar Ibrahim Siddick : '{texte_a_taper}' via Gemini Vision."
        except Exception as e:
            print(f"[VISION] Gemini Ecrire KO ({e}). Bascule GROQ + OCR...")

        # 2. BASCULE GROQ (OCR LOCAL)
        if groq_client:
            print(f"[VISION] Groq Fallback Ecrire: Analyse OCR...")
            ocr_text = []
            try:
                # On utilise 'eng' car c'est le plus souvent installé par défaut
                d = pytesseract.image_to_data(img, output_type=Output.DICT, lang='eng')
                for i in range(len(d['text'])):
                    txt = d['text'][i].strip()
                    if txt and len(txt) > 1:
                        cx, cy = d['left'][i] + d['width'][i]//2, d['top'][i] + d['height'][i]//2
                        ocr_text.append(f"'{txt}' at ({cx},{cy})")
            except Exception as ocr_err:
                print(f"[VISION] OCR Tesseract KO ({ocr_err}).")

            if ocr_text:
                prompt_groq = (
                    f"Je suis JARVIS. Voici les éléments textuels détectés sur mon écran avec leurs coordonnées X,Y.\n"
                    f"OCR : {', '.join(ocr_text[:80])}\n"
                    f"L'utilisateur veut écrire dans : {instruction}\n"
                    "Donne-moi UNIQUEMENT le JSON des coordonnées X,Y de la cible : {\"x\": x, \"y\": y}."
                )
                completion = groq_client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[{"role": "user", "content": prompt_groq}]
                )
                res = completion.choices[0].message.content
                import re
                m = re.search(r'\{\s*"x":\s*(\d+),\s*"y":\s*(\d+)\s*\}', res)
                if m:
                    tx, ty = int(m.group(1)), int(m.group(2))
                    pyautogui.moveTo(tx, ty, duration=0.4)
                    pyautogui.click()
                    time.sleep(0.5)
                    pyautogui.write(texte_a_taper, interval=0.03)
                    pyautogui.press('enter')
                    os.remove(path_ss)
                    return f"Action effectuée via Groq + OCR (fallback)."
        
        # Blind fallback pour WhatsApp
        if "whatsapp" in instruction.lower():
            print("[VISION] Pas d'OCR. Tentative clic aveugle pour WhatsApp...")
            sw, sh = pyautogui.size()
            # Zone approximative du champ de saisie WhatsApp Desktop (en bas)
            pyautogui.moveTo(sw // 2, sh - 80, duration=0.5)
            pyautogui.click()
            pyautogui.write(texte_a_taper)
            pyautogui.press('enter')
            os.remove(path_ss)
            return "J'ai essayé de taper le texte à l'aveugle pour WhatsApp (vision HS)."

        os.remove(path_ss)
        return "Je n'ai pas pu identifier le champ précisément via Gemini ou Groq."
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return f"Erreur vision ecrire : {e}"

def ha_appeler_service(domaine, service, entity_id, donnees=None):
    try:
        payload = {"entity_id": entity_id}
        if donnees:
            payload.update(donnees)
        print(f"[HA DEBUG] Calling {domaine}/{service} for {entity_id} with {donnees}")
        r = requests.post(f"{HA_URL}/api/services/{domaine}/{service}", headers=HA_HEADERS, json=payload, timeout=5)
        print(f"[HA DEBUG] Response {r.status_code}: {r.text}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"[HA] Erreur service : {e}")
        return False

def ha_get_etat(entity_id, attribut=None):
    try:
        r    = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
        data = r.json()
        if attribut:
            return data.get("attributes", {}).get(attribut, "inconnu")
        return data.get("state", "inconnu")
    except Exception as e:
        print(f"[HA] Erreur get etat : {e}")
        return "inconnu"

def ha_get_calendrier(entity_id):
    try:
        now = datetime.now()
        start = now.strftime("%Y-%m-%dT00:00:00Z")
        end = now.strftime("%Y-%m-%dT23:59:59Z")
        r = requests.get(
            f"{HA_URL}/api/calendars/{entity_id}",
            headers=HA_HEADERS,
            params={"start": start, "end": end},
            timeout=5
        )
        return r.json()
    except Exception as e:
        print(f"[HA] Erreur calendrier : {e}")
        return []

# ==========================================
# CONSTANTES ET VÉRIFICATION D'ÉTAT PHYSIQUE HOME ASSISTANT (C-04 / SEC-05)
# ==========================================
HA_REQUEST_ACCEPTED = "REQUEST_ACCEPTED"
HA_STATE_VERIFIED   = "STATE_VERIFIED"
HA_STATE_UNKNOWN    = "STATE_UNKNOWN"
HA_TIMEOUT          = "TIMEOUT"
HA_FAILED           = "FAILED"

def ha_verifier_changement_etat(entity_id: str, expected_state: str, max_attempts: int = 3, interval: float = 0.4) -> Tuple[str, str]:
    """Interroge l'état matériel réel d'une entité après une commande pour valider la transition physique (C-04)."""
    etat_reel = "inconnu"
    for attempt in range(max_attempts):
        etat_reel = ha_get_etat(entity_id)
        if isinstance(etat_reel, str):
            etat_norm = etat_reel.strip().lower()
            exp_norm = expected_state.strip().lower()

            if etat_norm == exp_norm:
                return (HA_STATE_VERIFIED, etat_reel)

            if etat_norm in ("unknown", "unavailable", "inconnu", "none"):
                return (HA_STATE_UNKNOWN, etat_reel)

        if attempt < max_attempts - 1:
            time.sleep(interval)

    return (HA_TIMEOUT, str(etat_reel))

def ha_lumiere(entity_id, etat="on", luminosite=None, rgb=None, verify_state=True):
    """Commande une lumière Home Assistant avec vérification d'état physique réelle (C-04)."""
    service_name = "toggle" if etat == "toggle" else ("turn_on" if etat == "on" else "turn_off")
    donnees = {}
    if etat == "on":
        if luminosite is not None:
            donnees["brightness"] = int(luminosite)
        if rgb is not None:
            donnees["rgb_color"] = rgb

    service_ok = ha_appeler_service("light", service_name, entity_id, donnees)
    if not service_ok:
        return {"status": HA_FAILED, "state": "unknown"}

    if not verify_state or etat == "toggle":
        return {"status": HA_REQUEST_ACCEPTED, "state": "unknown"}

    expected = "on" if etat == "on" else "off"
    status, actual_state = ha_verifier_changement_etat(entity_id, expected, max_attempts=3, interval=0.4)
    return {"status": status, "state": actual_state}

def ha_interrupteur(entity_id, etat="on", verify_state=True):
    """Commande un interrupteur/prise Home Assistant avec vérification d'état physique réelle (C-04)."""
    service_name = "turn_on" if etat == "on" else "turn_off"
    service_ok = ha_appeler_service("switch", service_name, entity_id)
    if not service_ok:
        return {"status": HA_FAILED, "state": "unknown"}

    if not verify_state:
        return {"status": HA_REQUEST_ACCEPTED, "state": "unknown"}

    expected = "on" if etat == "on" else "off"
    status, actual_state = ha_verifier_changement_etat(entity_id, expected, max_attempts=3, interval=0.4)
    return {"status": status, "state": actual_state}

def ha_thermostat(entity_id, temperature):
    return ha_appeler_service("climate", "set_temperature", entity_id, {"temperature": temperature})

def ha_scene(scene_id):
    return ha_appeler_service("scene", "turn_on", scene_id)

def recherche_web_serpapi(query):
    """Effectue une recherche sur Google via SerpAPI."""
    if not SERPAPI_API_KEY or SERPAPI_API_KEY == "VOTRE_CLE_ICI":
        return "Aboubakar Ibrahim Siddick, la clé SerpAPI n'est pas configurée dans le fichier d'environnement."
    
    try:
        print(f"[WEB] Recherche SerpAPI pour : {query}")
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "hl": "fr",
            "gl": "fr"
        }
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        data = r.json()
        
        # Extraction des actualités si présentes
        if "news_results" in data:
            news = data["news_results"][:3]
            reponse = f"Voici les dernières actualités pour {query} :\n"
            for n in news:
                source = n.get("source", "Source inconnue")
                titre = n.get("title", "")
                reponse += f"- {titre} (via {source})\n"
            return reponse
            
        # Extraction des résultats organiques sinon
        if "organic_results" in data:
            results = data["organic_results"][:3]
            reponse = f"Voici ce que j'ai trouvé sur le web pour {query} :\n"
            for r in results:
                titre = r.get("title", "")
                snippet = r.get("snippet", "")
                reponse += f"- {titre} : {snippet}\n"
            return reponse
            
        return f"Je n'ai rien trouvé de pertinent sur le web pour : {query}."
    except Exception as e:
        print(f"[WEB] Erreur SerpAPI : {e}")
        return "Une erreur est survenue lors de la recherche sur internet."

PIECES_LUMIERES = {
    # Salon
    "salon"            : "light.salon",
    "plafond salon"    : "light.plafond",
    "canapes"          : "light.canapes",
    "lampadaire"       : "light.lampadaire",
    "lampe de chevet"  : "light.lampe_de_chevet_2",
    "grosse boule"     : "light.grosse_boule",
    "petite boule"     : "light.petite_boule",
    
    # Cuisine
    "cuisine"          : "light.lsc_smart_led_strip_rgbic_cctic_5m",
    "cuisine 2"        : "light.cuisine_2",
    
    # Esteban
    "esteban"          : "light.pc_3",
    "pc esteban"       : "light.pc_3",
    
    # Bureau
    "bureau"           : "light.bureau",
    "pc"               : "light.pc",
    "pc 2"             : "light.pc_2",
    
    # Parents
    "parents"          : "light.chambre_parentale",
    "chambre parentale": "light.chambre_parentale",
    "chambre"          : "light.chambre_parentale",
    "plafond chambre"  : "light.plafond_2",
    
    # Autres / Globaux
    "toutes"           : "light.all",
    "tout"             : "light.all",
}

PIECES_PRISES = {
    "salon"   : "switch.prise_salon",
    "bureau"  : "switch.prise_bureau",
    "cuisine" : "switch.prise_cuisine",
}

PIECES_CAPTEURS = {
    "salon"        : "sensor.salon_temperature_2",
    "chambre"      : "sensor.miaomiaoc_de_blt_4_14kc52pmcgk00_t2_temperature_p_2_1",
    "bureau"       : "sensor.temp_temperature",
    "exterieur"    : "sensor.temperature_exterieure",
    "dehors"       : "sensor.temperature_exterieure",
    "consommation" : "sensor.lixee_zlinky_tic_puissance_apparente",
    "tiktok"       : "sensor.tiktok_followers_techenclair",
    "oeufs"        : "input_select.ramassage_des_oeufs",
}

PIECES_HUMIDITE = {
    "bureau"    : "sensor.temp_humidite",
}

HA_TARIFS = { "p1": 0.1296, "p2": 0.1603, "p3": 0.1486, "p4": 0.1894, "p5": 0.1568, "p6": 0.7562 }

APPAREILS_ENERGIE = {
    "tv"              : "sensor.prise_1_salon_mensuel",
    "salon"           : "sensor.prise_1_salon_mensuel",
    "pc esteban"      : "sensor.prise_3_pc_esteban_mensuel",
    "esteban"         : "sensor.prise_3_pc_esteban_mensuel",
    "zoe"             : "sensor.zoe_mensuel",
    "voiture"         : "sensor.zoe_mensuel",
    "lave-vaisselle"  : "sensor.prise_2_lave_vaisselle_mensuel",
    "pc salon"        : "sensor.pc_salon_conso_pc_salon_mensuel_2",
    "bureau"          : "sensor.bureau_mensuel",
}

# Appareils pour le suivi de batterie
APPAREILS_BATTERIE = {
    "mon telephone"     : "sensor.sm_s921b_battery_level",
    "papa"              : "sensor.sm_s921b_battery_level",
    "aboubakar ibrahim siddick"           : "sensor.sm_s921b_battery_level",
    "samsung papa"      : "sensor.sm_s921b_battery_level",
    "julie"             : "sensor.sm_julie_battery_level",
    "maman"             : "sensor.sm_julie_battery_level",
    "samsung maman"     : "sensor.sm_julie_battery_level",
    "esteban"           : "sensor.esteban_battery_level",
    "honor"             : "sensor.honor_battery_level",
    "tablette honor"    : "sensor.honor_battery_level",
    "montre papa"       : "sensor.galaxy_watch6_classic_d4he_battery_level",
    "montre aboubakar ibrahim siddick"    : "sensor.galaxy_watch6_classic_d4he_battery_level",
    "montre maman"      : "sensor.galaxy_watch8_fbxh_battery_level",
    "montre julie"      : "sensor.galaxy_watch8_fbxh_battery_level",
    "bob"               : "sensor.bob_batterie",
    "aspirateur bob"    : "sensor.bob_batterie",
    "dyad"              : "sensor.dyad_air_2024_batterie",
    "aspirateur dyad"   : "sensor.dyad_air_2024_batterie",
    "telecommande hue"  : "sensor.maison_interrupteur_batterie",
    "interrupteur"      : "sensor.maison_interrupteur_batterie",
    "toner"             : "sensor.samsung_m2020_series_black_toner_s_n_crum_17091625519",
    "imprimante"        : "sensor.samsung_m2020_series_black_toner_s_n_crum_17091625519",
    "boite aux lettres" : "sensor.detecterur_batterie",
    "detecteur cuisine" : "sensor.detecteur_1_batterie",
    "detecteur escalier": "sensor.detecteur_2_batterie",
    "camera jardin"     : "sensor.arriere_cour_battery_percentage",
    "thermometre bureau": "sensor.temp_batterie",
}

COULEURS_MAP = {
    "rouge"      : [255, 0,   0  ],
    "bleu"       : [0,   0,   255],
    "vert"       : [0,   255, 0  ],
    "blanc"      : [255, 255, 255],
    "orange"     : [255, 140, 0  ],
    "violet"     : [148, 0,   211],
    "rose"       : [255, 20,  147],
    "jaune"      : [255, 255, 0  ],
    "cyan"       : [0,   255, 255],
    "magenta"    : [255, 0,   255],
    "turquoise"  : [64,  224, 208],
    "or"         : [255, 215, 0  ],
    "argent"     : [192, 192, 192],
    "indigo"     : [75,  0,   130],
    "marron"     : [139, 69,  19 ],
    "citron"     : [255, 250, 0  ],
    "corail"     : [255, 127, 80 ],
    "lavande"    : [230, 230, 250],
}

CODES_METEO = {
    0:  "ciel degage",
    1:  "principalement clair", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine legere", 53: "bruine moderee", 55: "bruine dense",
    61: "pluie faible", 63: "pluie moderee", 65: "pluie forte",
    71: "neige faible", 73: "neige moderee", 75: "neige forte",
    80: "averses faibles", 81: "averses moderees", 82: "averses violentes",
    85: "averses de neige", 86: "averses de neige fortes",
    95: "orage", 96: "orage avec grele", 99: "orage violent avec grele",
}

def geocoder_ville(ville):
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ville, "count": 1, "language": "fr", "format": "json"},
            timeout=5
        )
        data = r.json()
        if data.get("results"):
            res = data["results"][0]
            return res["latitude"], res["longitude"], res.get("name", ville), res.get("country", "")
    except Exception as e:
        print(f"[METEO] Erreur geocoding : {e}")
    return None, None, ville, ""

def get_meteo_actuelle(ville=None):
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, pays = geocoder_ville(nom_ville)
        if lat is None:
            lat, lon = LAT_PAR_DEFAUT, LON_PAR_DEFAUT
            nom_affiche = VILLE_PAR_DEFAUT
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude"      : lat, "longitude": lon,
                "current"       : "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weathercode,precipitation",
                "hourly"        : "temperature_2m,precipitation_probability",
                "daily"         : "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,wind_speed_10m_max,sunrise,sunset",
                "timezone"      : "Europe/Paris",
                "forecast_days" : 3,
                "wind_speed_unit": "kmh",
            },
            timeout=8
        )
        data  = r.json()
        cur   = data["current"]
        daily = data["daily"]
        code     = cur.get("weathercode", 0)
        desc     = CODES_METEO.get(code, "conditions inconnues")
        temp     = round(float(cur.get("temperature_2m", 0)))
        
        reponse = f"À {nom_affiche}, il fait {temp} degrés et le ciel est {desc}. C'est tout."
        return reponse
    except Exception as e:
        print(f"[METEO] Erreur : {e}")
        return "Je n'arrive pas à récupérer la météo pour le moment."

def get_alertes_meteo(ville=None):
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, _ = geocoder_ville(nom_ville)
        if lat is None:
            lat, lon, nom_affiche = LAT_PAR_DEFAUT, LON_PAR_DEFAUT, VILLE_PAR_DEFAUT
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily"   : "weathercode,precipitation_sum,wind_speed_10m_max",
                "timezone": "Europe/Paris", "forecast_days": 3,
            },
            timeout=8
        )
        data  = r.json()
        daily = data["daily"]
        alertes = []
        for i in range(len(daily["weathercode"])):
            code  = daily["weathercode"][i]
            pluie = daily.get("precipitation_sum", [0]*3)[i] or 0
            vent  = daily.get("wind_speed_10m_max", [0]*3)[i] or 0
            jour  = ["aujourd hui", "demain", "apres-demain"][i]
            if code in [95, 96, 99]:
                alertes.append(f"Orage prevu {jour}")
            if code in [71, 73, 75, 85, 86]:
                alertes.append(f"Neige prevue {jour}")
            if pluie > 20:
                alertes.append(f"Fortes pluies {jour} ({pluie}mm)")
            if vent > 60:
                alertes.append(f"Vents forts {jour} ({vent} km/h)")
        if alertes:
            return f"Alertes meteo pour {nom_affiche} : " + ", ".join(alertes) + "."
        return f"Aucune alerte meteo pour {nom_affiche} dans les 3 prochains jours."
    except Exception as e:
        return f"Impossible de verifier les alertes meteo : {e}"

THESPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

def get_resultats_football(equipe=None, ligue=None):
    try:
        if equipe:
            print(f"[SPORT] Recherche pour l'equipe : {equipe}")
            r = requests.get(f"{THESPORTSDB_BASE}/searchteams.php", params={"t": equipe}, timeout=5)
            data = r.json()
            teams = data.get("teams")
            if not teams:
                return f"Je n'ai pas trouvé l'équipe {equipe}."
            
            team_id   = teams[0]["idTeam"]
            team_name = teams[0]["strTeam"]
            
            # On cherche les derniers ET les prochains matchs
            res_last = requests.get(f"{THESPORTSDB_BASE}/eventslast.php", params={"id": team_id}, timeout=5).json()
            res_next = requests.get(f"{THESPORTSDB_BASE}/eventsnext.php", params={"id": team_id}, timeout=5).json()
            
            matchs_passes = res_last.get("results", [])
            matchs_futurs = res_next.get("events", [])
            
            reponse = f"Concernant le {team_name} : "
            
            if matchs_futurs:
                m = matchs_futurs[0]
                date_m = m.get("dateEvent", "date inconnue")
                heure_m = m.get("strTime", "")
                reponse += f"Le prochain match aura lieu le {date_m} à {heure_m} contre {m.get('strOpponent')}. "
            
            if matchs_passes:
                m = matchs_passes[0]
                reponse += f"Leur dernier résultat était {m.get('intHomeScore')} à {m.get('intAwayScore')} contre {m.get('strOpponent')}."
            
            if not matchs_futurs and not matchs_passes:
                return f"Je n'ai pas d'informations récentes ou futures pour {team_name}."
                
            return reponse
        else:
            nom_ligue = ligue or "Ligue 1"
            ligue_ids = {
                "ligue 1": "4334", "premier league": "4328", "liga": "4335",
                "bundesliga": "4331", "serie a": "4332",
                "champions league": "4480", "ligue des champions": "4480",
            }
            ligue_id = ligue_ids.get(nom_ligue.lower(), "4334")
            r = requests.get(f"{THESPORTSDB_BASE}/eventspastleague.php", params={"id": ligue_id}, timeout=5)
            data   = r.json()
            matchs = data.get("events", [])
            if not matchs:
                return f"Aucun resultat trouve pour {nom_ligue}."
            reponse = f"Derniers resultats {nom_ligue} : "
            lignes  = []
            for m in matchs[-6:]:
                home    = m.get("strHomeTeam", "?")
                away    = m.get("strAwayTeam", "?")
                score_h = m.get("intHomeScore", "?")
                score_a = m.get("intAwayScore", "?")
                date    = m.get("dateEvent", "?")
                lignes.append(f"{home} {score_h}-{score_a} {away} ({date})")
            return reponse + " | ".join(lignes)
    except Exception as e:
        print(f"[SPORT] Erreur football : {e}")
        return f"Impossible de recuperer les resultats football : {e}"

def get_classement_football(ligue=None):
    try:
        nom_ligue = ligue or "Ligue 1"
        ligue_ids = {
            "ligue 1": "4334", "premier league": "4328", "liga": "4335",
            "bundesliga": "4331", "serie a": "4332",
            "champions league": "4480", "ligue des champions": "4480",
        }
        ligue_id = ligue_ids.get(nom_ligue.lower(), "4334")
        r = requests.get(f"{THESPORTSDB_BASE}/lookuptable.php", params={"l": ligue_id, "s": "2024-2025"}, timeout=8)
        data    = r.json()
        tableau = data.get("table", [])
        if not tableau:
            return f"Classement {nom_ligue} non disponible pour le moment."
        reponse = f"Classement {nom_ligue} : "
        lignes  = []
        for eq in tableau[:10]:
            pos   = eq.get("intRank", "?")
            nom   = eq.get("strTeam", "?")
            pts   = eq.get("intPoints", "?")
            joues = eq.get("intPlayed", "?")
            lignes.append(f"{pos}. {nom} - {pts}pts ({joues}J)")
        return reponse + " | ".join(lignes)
    except Exception as e:
        print(f"[SPORT] Erreur classement : {e}")
        return f"Impossible de recuperer le classement : {e}"

async def get_resultats_sport_gemini(question_sport):
    try:
        response = await client.aio.models.generate_content(
            model   = CHOSEN_MODEL,
            contents= [types.Content(role="user", parts=[types.Part(text=
                f"Donne-moi les derniers resultats et actualites sportives en 2026 "
                f"pour : {question_sport}. "
                f"Sois precis, donne les scores et dates. Reponds en francais."
            )])],
            config  = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "Tu es un expert sportif. Donne des resultats precis et a jour. "
                    "Reponds de facon concise et conversationnelle en francais."
                )
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"[SPORT] Erreur Gemini sport : {e}")
        return "Je n arrive pas a recuperer les resultats sportifs pour le moment."

def chercher_youtube(recherche):
    try:
        r   = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": recherche, "type": "video", "maxResults": 1, "key": YOUTUBE_API_KEY},
            timeout=5
        )
        vid = r.json()["items"][0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={vid}"
    except Exception as e:
        print(f"Erreur YouTube : {e}")
        return None

# ============================================================
# LANCEUR D'APPLICATIONS UNIVERSEL
# ============================================================
def lancer_app(nom_app: str) -> str:
    """Lance n'importe quelle application installée sur le PC."""
    nom = nom_app.lower().strip()

    # Dictionnaire des applications courantes (FR + EN)
    APPS = {
        # Navigateurs
        "chrome": ["chrome.exe", "google chrome"],
        "google chrome": ["chrome.exe"],
        "firefox": ["firefox.exe"],
        "edge": ["msedge.exe", "MicrosoftEdge.exe"],
        "opera": ["opera.exe"],
        # Communication
        "discord": ["discord.exe"],
        "teams": ["Teams.exe", "ms-teams.exe"],
        "microsoft teams": ["Teams.exe"],
        "slack": ["slack.exe"],
        "zoom": ["zoom.exe"],
        "telegram": ["Telegram.exe"],
        "whatsapp": ["WhatsApp.exe"],
        "skype": ["skype.exe"],
        # Musique / Vidéo
        "spotify": ["Spotify.exe"],
        "vlc": ["vlc.exe"],
        "itunes": ["iTunes.exe"],
        "deezer": ["Deezer.exe"],
        "youtube music": ["YouTubeMusic.exe"],
        # Productivité
        "word": ["WINWORD.EXE", "winword.exe", "soffice.exe"],
        "excel": ["EXCEL.EXE", "excel.exe"],
        "powerpoint": ["POWERPNT.EXE", "powerpnt.exe"],
        "outlook": ["OUTLOOK.EXE", "outlook.exe"],
        "onenote": ["ONENOTE.EXE", "onenote.exe"],
        "notepad": ["notepad.exe"],
        "bloc-notes": ["notepad.exe"],
        "bloc notes": ["notepad.exe"],
        "wordpad": ["wordpad.exe"],
        # Développement
        "vs code": ["code.exe", "Code.exe"],
        "vscode": ["code.exe"],
        "visual studio code": ["code.exe"],
        "visual studio": ["devenv.exe"],
        "pycharm": ["pycharm64.exe", "pycharm.exe"],
        "intellij": ["idea64.exe"],
        "android studio": ["studio64.exe"],
        "git bash": ["git-bash.exe"],
        "terminal": ["wt.exe", "cmd.exe"],
        "powershell": ["PowerShell.exe", "pwsh.exe"],
        "invite de commande": ["cmd.exe"],
        "cmd": ["cmd.exe"],
        # Système
        "gestionnaire des taches": ["Taskmgr.exe"],
        "gestionnaire de taches": ["Taskmgr.exe"],
        "explorateur": ["explorer.exe"],
        "explorateur de fichiers": ["explorer.exe"],
        "panneau de configuration": ["control.exe"],
        "parametres": ["ms-settings:"],
        "calculatrice": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "snipping tool": ["SnippingTool.exe"],
        "capture decran": ["SnippingTool.exe"],
        # Jeux / Autres
        "steam": ["steam.exe"],
        "epic games": ["EpicGamesLauncher.exe"],
        "obs": ["obs64.exe", "obs.exe"],
        "obs studio": ["obs64.exe", "obs.exe"],
        "photoshop": ["Photoshop.exe"],
        "illustrator": ["Illustrator.exe"],
        "figma": ["Figma.exe"],
        "blender": ["blender.exe"],
        "postman": ["Postman.exe"],
        "filezilla": ["filezilla.exe"],
        "7zip": ["7zFM.exe"],
        "winrar": ["WinRAR.exe"],
        "pdf": ["AcroRd32.exe", "Acrobat.exe"],
        "acrobat": ["AcroRd32.exe", "Acrobat.exe"],
    }

    # 1. Chercher dans le dictionnaire
    candidats = APPS.get(nom, [])
    # Recherche partielle si pas de correspondance exacte
    if not candidats:
        for key, exes in APPS.items():
            if key in nom or nom in key:
                candidats = exes
                break

    # 2. Essayer de lancer les candidats
    for exe in candidats:
        try:
            if exe.startswith("ms-settings:") or exe.startswith("ms-"):
                os.startfile(exe)
                return f"{nom_app} ouvert."
            subprocess.Popen([exe], shell=True)
            print(f"[APP] Lancé : {exe}")
            return f"Bien sûr Aboubakar Ibrahim Siddick, je lance {nom_app}."
        except FileNotFoundError:
            continue
        except Exception as ex:
            print(f"[APP] Erreur {exe} : {ex}")
            continue

    # 3. Fallback : chercher dans PATH avec 'where'
    try:
        result = subprocess.run(["where", nom_app], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            exe_path = result.stdout.strip().split('\n')[0]
            subprocess.Popen([exe_path], shell=True)
            return f"J'ai trouvé et lancé {nom_app}."
    except Exception:
        pass

    # 4. Fallback : chercher dans le menu démarrer (raccourcis .lnk)
    try:
        start_menus = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs',
        ]
        nom_clean = nom.replace(' ', '*')
        for start_dir in start_menus:
            result = subprocess.run(
                ["cmd", "/c", f'dir /s /b "{start_dir}\\*{nom_clean}*.lnk"'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                lnk = result.stdout.strip().split('\n')[0].strip()
                os.startfile(lnk)
                return f"Lancé depuis le menu démarrer : {os.path.basename(lnk)}."
    except Exception:
        pass

    return f"Je n'ai pas trouvé '{nom_app}' sur votre PC. Vérifiez que l'application est bien installée."


# ==========================================
# GESTIONNAIRE D'ACTIONS SYSTÈME SÉCURISÉES (SEC-03)
# ==========================================
class SystemActionController:
    """Contrôleur sécurisé pour l'arrêt, le redémarrage et les commandes PC critiques."""

    def __init__(self):
        # Isolation multi-sessions (SEC-03) : session_id -> {"action": "shutdown"|"reboot", "expires_at": float, "token": str}
        self.pending_actions: Dict[str, Dict[str, Any]] = {}
        self.timeout_seconds = 30.0
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice_outputs", "security_audit.log")
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        except Exception:
            pass

    def log_audit(self, event_type: str, details: str, client_ip: str = "local", session_id: str = "unknown"):
        """Enregistre un événement de sécurité dans le journal d'audit."""
        try:
            self._ensure_log_dir()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{ts}] [SEC-AUDIT] [{event_type}] [SESSION:{session_id}] [IP:{client_ip}] {details}\n"
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"[SEC-AUDIT ERROR] {e}")

    def is_domotique_intent(self, cmd: str) -> bool:
        """Détecte si la commande vise un équipement domotique plutôt que le PC."""
        domotique_keywords = [
            "lumiere", "lumière", "lumieres", "lumières", "lampe", "lampes", "spot", "spots",
            "prise", "prises", "interrupteur", "tele", "télé", "television", "télévision", "tv",
            "salon", "chambre", "cuisine", "couloir", "bureau", "salle", "bain", "garage",
            "clim", "climatisation", "chauffage", "radiateur", "thermostat", "alarme", "volet", "volets"
        ]
        return any(kw in cmd for kw in domotique_keywords)

    def is_thought_or_conditional(self, cmd: str) -> bool:
        """Détecte les réflexions, hésitations ou hypothèses sans ordre impératif direct."""
        thoughts = [
            "je pense", "j'hésite", "j'aimerais peut-être", "peut-être", "est-ce que tu dois",
            "faudrait-il", "envisage", "pourquoi", "si j'éteins"
        ]
        return any(t in cmd for t in thoughts)

    def is_negation(self, cmd: str) -> bool:
        """Détecte les négations ou annulations verbales."""
        negations = [
            "ne veux pas", "pas éteindre", "pas eteindre", "n'éteins pas", "n'eteins pas",
            "ne pas", "annule", "annuler", "stop l'extinction"
        ]
        return any(neg in cmd for neg in negations)

    def process_command(self, cmd: str, session_id: str = "desktop_local", client_ip: str = "local") -> Optional[str]:
        """Analyse et traite les commandes système avec isolation de session stricte (SEC-03)."""
        cmd_clean = cmd.strip().lower()

        # 1. Annulation explicite
        if "annul" in cmd_clean:
            if session_id in self.pending_actions:
                action = self.pending_actions[session_id]["action"]
                del self.pending_actions[session_id]
                self.log_audit("ACTION_CANCELLED", f"Action {action} annulée", client_ip, session_id)
                return "Opération système annulée. L'ordinateur restera allumé."
            return "Aucune action à annuler pour votre session."

        # 2. Confirmation d'une action en attente
        if "confirmer" in cmd_clean or "confirme" in cmd_clean:
            if session_id not in self.pending_actions:
                # Vérifier si une AUTRE session a une confirmation en cours (protection cross-session !)
                if self.pending_actions:
                    self.log_audit("CROSS_SESSION_ATTEMPT", "Tentative de confirmation croisée rejetée", client_ip, session_id)
                    return "Action non autorisée : la confirmation d'extinction doit provenir de la même session que la demande initiale."
                return "Aucune commande système sensible n'est actuellement en attente de confirmation pour votre session."

            now = time.time()
            action_data = self.pending_actions[session_id]
            if now > action_data["expires_at"]:
                expired_action = action_data["action"]
                del self.pending_actions[session_id]
                self.log_audit("ACTION_EXPIRED", f"Action {expired_action} expirée après 30s", client_ip, session_id)
                return "Le délai de confirmation de 30 secondes a expiré. L'action est annulée par sécurité."

            action = action_data["action"]
            # Vérifier la correspondance de l'action sans ambiguïté
            if action == "shutdown":
                if any(kw in cmd_clean for kw in ["redemarr", "redémarr", "reboot"]):
                    return "Confirmation ambiguë rejetée : l'action en attente est une extinction, pas un redémarrage."
                if not any(kw in cmd_clean for kw in ["eteindre", "éteindre", "extinction", "confirmer", "confirme"]):
                    return "Confirmation ambiguë rejetée. Dites exactement 'confirmer l'extinction' pour valider."
            elif action == "reboot":
                if any(kw in cmd_clean for kw in ["eteindre", "éteindre", "extinction"]):
                    return "Confirmation ambiguë rejetée : l'action en attente est un redémarrage, pas une extinction."
                if not any(kw in cmd_clean for kw in ["redemarr", "redémarr", "reboot", "confirmer", "confirme"]):
                    return "Confirmation ambiguë rejetée. Dites exactement 'confirmer le redémarrage' pour valider."

            del self.pending_actions[session_id]
            self.log_audit("ACTION_CONFIRMED", f"Action {action} validée et déclenchée", client_ip, session_id)

            # Mode DRY-RUN pour les tests automatisés sans interruption OS réelle
            if os.environ.get("JARVIS_DRY_RUN_SYSTEM_COMMANDS") == "1":
                return f"[DRY-RUN] Commande {action} confirmée avec succès. Aucune interruption OS réelle appliquée."

            if action == "shutdown":
                try:
                    subprocess.Popen(["shutdown", "/s", "/t", "10", "/c", "Extinction validée via ALICE"])
                    return "Extinction du système confirmée. L'ordinateur va s'éteindre dans 10 secondes."
                except Exception as e:
                    return f"Erreur lors de l'exécution de l'extinction : {e}"
            elif action == "reboot":
                try:
                    subprocess.Popen(["shutdown", "/r", "/t", "10", "/c", "Redémarrage validé via ALICE"])
                    return "Redémarrage du système confirmé. L'ordinateur va redémarrer dans 10 secondes."
                except Exception as e:
                    return f"Erreur lors de l'exécution du redémarrage : {e}"

        # 3. Élimination des conflits domotiques, négations et simples pensées
        if self.is_domotique_intent(cmd_clean):
            return None

        if self.is_thought_or_conditional(cmd_clean):
            return None

        if self.is_negation(cmd_clean):
            return None

        # 4. Détection stricte d'intention d'arrêt ou reboot PC
        pattern_shutdown = re.compile(
            r'\b(?:éteins|eteins|éteindre|eteindre|arrête|arrete|arrêter|arreter|stop)\s+(?:le\s+|l\'|l\s+|mon\s+|cet\s+|ce\s+)?(?:pc|ordinateur|ordi|machine|windows)\b'
        )
        pattern_reboot = re.compile(
            r'\b(?:redémarre|redemarre|redémarrer|redemarrer|reboot|relance|relancer)\s+(?:le\s+|l\'|l\s+|mon\s+|cet\s+|ce\s+)?(?:pc|ordinateur|ordi|machine|windows)\b'
        )

        if pattern_shutdown.search(cmd_clean):
            self.pending_actions[session_id] = {
                "action": "shutdown",
                "expires_at": time.time() + self.timeout_seconds,
                "token": secrets.token_hex(4)
            }
            self.log_audit("ACTION_PENDING", "Demande d'extinction PC en attente de confirmation (30s)", client_ip, session_id)
            return (
                "Êtes-vous certain de vouloir éteindre votre ordinateur ? "
                "Pour confirmer, dites 'confirmer l'extinction' dans les 30 secondes. Sinon dites 'annuler'."
            )

        if pattern_reboot.search(cmd_clean):
            self.pending_actions[session_id] = {
                "action": "reboot",
                "expires_at": time.time() + self.timeout_seconds,
                "token": secrets.token_hex(4)
            }
            self.log_audit("ACTION_PENDING", "Demande de redémarrage PC en attente de confirmation (30s)", client_ip, session_id)
            return (
                "Êtes-vous certain de vouloir redémarrer votre ordinateur ? "
                "Pour confirmer, dites 'confirmer le redémarrage' dans les 30 secondes. Sinon dites 'annuler'."
            )

        return None

SYSTEM_ACTION_CONTROLLER = SystemActionController()

def executer_action_pc(commande, session_id="desktop_local", client_ip="local"):
    cmd          = commande.lower()
    user_profile = os.environ.get('USERPROFILE', '')

    # --- SÉCURITÉ SYSTÈME (SEC-03 : Arrêt, Redémarrage & Audit avec isolation de session) ---
    sys_action_result = SYSTEM_ACTION_CONTROLLER.process_command(cmd, session_id=session_id, client_ip=client_ip)
    if sys_action_result is not None:
        return sys_action_result

    # --- ACTIONS DE FICHIERS (Nouveau) ---
    # Lis le fichier C:\test.txt
    match_read = re.search(r'(?:lis|affiche|lit) (?:le fichier )?([a-zA-Z]:\\[^ ]+|[\/\w\.-]+)', cmd)
    if match_read:
        path = match_read.group(1).strip()
        content = extraire_texte_doc(path)
        if content:
            return f"Voici le contenu du fichier {path} :\n\n{content[:1500]}..."
        return f"Je n'ai pas pu lire le fichier {path} ou il est vide."

    # Écris [contenu] dans le fichier [chemin]
    match_write = re.search(r'(?:écris|sauvegarde|enregistre) (.+) dans (?:le fichier )?([a-zA-Z]:\\[^ ]+|[\/\w\.-]+)', cmd)
    if match_write:
        content = match_write.group(1).strip()
        path = match_write.group(2).strip()
        return ecrire_fichier_pc(path, content)

    # --- ACTIONS WEB (Nouveau) ---
    # Ouvre le site google.com
    match_web = re.search(r'(?:ouvre|va sur) (?:le site |l\'url )?([^ ]+\.[^ ]+)', cmd)
    if match_web:
        url = match_web.group(1).strip()
        return ouvrir_url_pc(url)

    # --- LOGIQUE EXISTANTE ---
    if "met de la musique" in cmd or "mets de la musique" in cmd:
        url = "https://www.youtube.com/watch?v=7CGKeID7nRc&list=PL4fGSI1pDJn50iCQRUVmgUjOrCggCQ9nR"
        webbrowser.open(url, new=2)
        time.sleep(6)
        pyautogui.press('f')
        return "C'est parti Aboubakar Ibrahim Siddick, je mets votre playlist en plein écran."

    if "youtube" in cmd:
        if "ouvre" in cmd or "va sur" in cmd:
            webbrowser.open("https://www.youtube.com")
            return "Ouverture de YouTube."
        recherche = cmd
        for mot in ["mets", "joue", "lance", "la video", "sur youtube", "youtube", "jarvis"]:
            recherche = recherche.replace(mot, "")
        recherche = recherche.strip()
        if recherche:
            url = chercher_youtube(recherche)
            if url:
                webbrowser.open(url, new=2)
                time.sleep(5)
                pyautogui.press('f')
                return f"Je lance {recherche} sur YouTube."
        return "Video introuvable."

    if "ouvre" in cmd or "lance" in cmd:
        if "chrome" in cmd:
            subprocess.Popen(["chrome.exe"])
            return "Chrome ouvert."
        if "notepad" in cmd or "bloc-notes" in cmd:
            subprocess.Popen(["notepad.exe"])
            return "Bloc-notes ouvert."
        if "explorateur" in cmd:
            subprocess.Popen(["explorer.exe"])
            return "Explorateur ouvert."

    if "volume" in cmd:
        if "monte" in cmd or "augmente" in cmd:
            for _ in range(5):
                pyautogui.press('volumeup')
            return "Volume augmenté."
        if "baisse" in cmd:
            for _ in range(5):
                pyautogui.press('volumedown')
            return "Volume baissé."
        if "coupe" in cmd:
            pyautogui.press('volumemute')
            return "Son coupé."

    if "screenshot" in cmd or "capture" in cmd:
        path = os.path.join(user_profile, "Desktop", "screenshot.png")
        pyautogui.screenshot(path)
        return "Screenshot sauvegardé sur votre bureau."

    return None

def init_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init()

# ==========================================
# BUG 1 CORRIGE : fonction parler
# Le await send_web_state("idle") etait dans le mauvais bloc except
# ==========================================

def diagnostic_pc():
    """Effectue un check-up santé du PC."""
    try:
        cpu_load = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\').percent
        rapport = {"cpu": cpu_load, "ram": ram_usage, "disk": disk, "status": "OK"}
        alertes = []
        if cpu_load > 90: alertes.append("Processeur en surcharge.")
        if ram_usage > 90: alertes.append("Mémoire saturée.")
        if disk > 95: alertes.append("Disque dur C plein.")
        if alertes:
            rapport["status"] = "ALERTE"
            rapport["details"] = " ".join(alertes)
        return rapport
    except: return None

def memory_add(cle, valeur):
    """Enregistre un fait dans la mémoire long terme d'Alice (thread-safe, écriture atomique)."""
    try:
        return bool(ajouter_memoire(cle, valeur))
    except Exception as e:
        print(f"[MEMOIRE] Erreur ajout : {e}")
        return False

def memory_forget(cle):
    """Supprime un fait de la mémoire d'Alice (thread-safe, écriture atomique)."""
    try:
        return bool(supprimer_memoire(cle))
    except Exception as e:
        print(f"[MEMOIRE] Erreur oubli : {e}")
        return False

def get_google_calendar_events(days=7):
    """Récupère les évènements Google Calendar pour les prochains X jours."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except: return None
        else:
            return None
            
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        limit = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              timeMax=limit, singleEvents=True,
                                              orderBy='startTime').execute()
        return events_result.get('items', [])
    except Exception as e:
        print(f"[CALENDRIER] Erreur : {e}")
        return None

def update_productivity(points=10):
    """Met à jour le score de productivité d'Alice."""
    global PROD_SCORE, PROD_LEVEL
    PROD_SCORE += points
    new_level = (PROD_SCORE // 100) + 1
    leveled_up = (new_level > PROD_LEVEL)
    PROD_LEVEL = new_level
    return leveled_up, PROD_SCORE, PROD_LEVEL

def diagnostic_pc():
    """Effectue un check-up santé du PC."""
    try:
        cpu_load = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\').percent
        rapport = {"cpu": cpu_load, "ram": ram_usage, "disk": disk, "status": "OK"}
        alertes = []
        if cpu_load > 90: alertes.append("Processeur en surcharge.")
        if ram_usage > 90: alertes.append("Mémoire saturée.")
        if disk > 95: alertes.append("Disque dur C plein.")
        if alertes:
            rapport["status"] = "ALERTE"
            rapport["details"] = " ".join(alertes)
        return rapport
    except: return None

def update_productivity(points=10):
    """Met à jour le score de productivité d'Alice."""
    global PROD_SCORE, PROD_LEVEL
    PROD_SCORE += points
    new_level = (PROD_SCORE // 100) + 1
    leveled_up = (new_level > PROD_LEVEL)
    PROD_LEVEL = new_level
    return leveled_up, PROD_SCORE, PROD_LEVEL
async def parler(texte):
    global is_speaking, speak_volume, STOP_PARLER, _skip_pc_audio, historique
    
    # Interrupt previous speech if any
    if is_speaking:
        STOP_PARLER = True
        await asyncio.sleep(0.2) # Give it a moment to stop
        STOP_PARLER = False

    # Nettoyage des caractères de mise en forme Markdown pour le TTS
    texte_tts = texte.replace("**", "").replace("*", "").replace("#", "").replace("`", "").strip()
    
    # ENREGISTRER CE QUE JARVIS DIT DANS SA MÉMOIRE
    if historique and len(historique) > 0:
        dernier_texte_modele = historique[-1].parts[0].text
        if dernier_texte_modele != texte:
            historique.append(types.Content(role="model", parts=[types.Part(text=f"[Information retournée par l'action et énoncée à voix haute]: {texte}")]))

    is_speaking  = True
    await send_web_state("speaking")
    speak_volume = 0.0
    tmp = f"jarvis_tts_{int(time.time()*1000)}_{random.randint(0,10000)}.mp3"
    
    try:
        if time.time() < globals().get('EDGE_TTS_BANNED_UNTIL', 0):
            raise Exception("Edge-TTS est en cooldown suite aux timeouts recents")
            
        voix = VOICES.get(CURRENT_LANG, "fr-FR-HenriNeural")
        communicate = edge_tts.Communicate(texte_tts, voice=voix)
        # Téléchargement asynchrone (peut être fait en parallèle pour plusieurs phrases)
        await communicate.save(tmp)
        
        # Utilisation asynchrone sécurisée du verrou threading (polling)
        while not SPEAKER_LOCK.acquire(blocking=False):
            await asyncio.sleep(0.1)
            
        try:
            # 1. Envoi au mobile si connecté
            if CONNECTED_CLIENTS:
                print(f"[MOBILE] Envoi audio au mobile : {texte_tts}")
                try:
                    with open(tmp, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode('utf-8')
                    message = json.dumps({"action": "jarvis_audio", "text": texte_tts, "audio_b64": audio_b64})
                    for ws in list(CONNECTED_CLIENTS):
                        try:
                            await ws.send(message)
                        except:
                            pass
                except Exception as e:
                    print(f"[MOBILE] Erreur envoi audio : {e}")
            
            # 2. Lecture sur PC si non explicitement désactivé
            if not _skip_pc_audio:
                init_mixer()
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if STOP_PARLER:
                        pygame.mixer.music.stop()
                        break
                    
                    t_audio = time.time() * 20
                    base_vol = 0.4 + 0.3 * math.sin(t_audio) + 0.2 * math.sin(t_audio * 0.5)
                    speak_volume = max(0.1, min(1.0, base_vol + random.uniform(-0.1, 0.1)))
                    
                    await send_web_volume(speak_volume)
                    await asyncio.sleep(0.05)
        finally:
            SPEAKER_LOCK.release()

    except Exception as e:
        print(f"Erreur TTS (Edge-TTS) : {e}. Tentative avec le moteur local (Offline)...")
        if "timeout" in str(e).lower() or "winerror" in str(e).lower():
            globals()['EDGE_TTS_BANNED_UNTIL'] = time.time() + 300 # 5 minutes cooldown
        # On protège aussi le moteur local avec le verrou
        while not SPEAKER_LOCK.acquire(blocking=False):
            await asyncio.sleep(0.1)
            
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            # Priorité absolue aux voix françaises pour éviter l'anglais
            selected_voice = None
            for voice in voices:
                v_id = voice.id.upper()
                v_lang = str(voice.languages).upper() if hasattr(voice, 'languages') else ""
                if "FR" in v_id or "FRENCH" in v_id or "FR" in v_lang:
                    selected_voice = voice.id
                    break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice)
            
            engine.setProperty('rate', 160) # Un peu plus rapide
            engine.say(texte_tts)
            engine.runAndWait()
        except Exception as e_local:
            print(f"Erreur Critique TTS local : {e_local}")
        finally:
            SPEAKER_LOCK.release()
    finally:
        speak_volume = 0.0
        is_speaking  = False
        STOP_PARLER  = False
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.unload()
        except:
            pass
        await asyncio.sleep(0.1)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except:
            pass
        await send_web_state("idle")

def reponse_locale(texte):
    """Réponse locale pour les requêtes basiques en cas de panne API."""
    t = texte.lower().strip()
    
    # Identité
    if any(m in t for m in ["qui es-tu", "ton nom", "quelle es ton identité", "t'appelle comment"]):
        return "Je suis JARVIS, votre assistant personnel et système informatique. Mes serveurs principaux sont actuellement en maintenance, mais je reste opérationnel localement."
    
    # Créateur
    if any(m in t for m in ["ton créateur", "t'as créé", "qui est aboubakar ibrahim siddick"]):
        return "Aboubakar Ibrahim Siddick est mon créateur et mon maître. C'est lui qui a conçu mes protocoles, même si ma connexion à mes serveurs neuronaux est actuellement limitée."
    
    # État
    if any(m in t for m in ["ça va", "tu vas bien", "comment vas-tu"]):
        return "Je fonctionne en mode de réserve, Aboubakar Ibrahim Siddick. Mes capacités de réflexion profonde sont réduites, mais mon intégrité logicielle est intacte."
        
    # Heure et Date
    if any(m in t for m in ["heure", "quelle heure"]):
        h = time.strftime("%H:%M")
        return f"Il est précisément {h} Monsieur."
    if any(m in t for m in ["date", "quel jour", "le combien"]):
        d = time.strftime("%A %d %B %Y")
        return f"Nous sommes le {d}."
        
    # Politesse
    if any(m in t for m in ["bonjour", "salut", "hey", "bonsoir"]):
        return "Bonjour Aboubakar Ibrahim Siddick. Je suis en ligne, bien que mes capacités soient actuellement restreintes."
    return None

def check_internet():
    """Vérifie si la connexion internet est active via plusieurs tests."""
    # Test HTTP sur plusieurs cibles (Google, Cloudflare, Bing)
    for url in ["https://www.google.com", "https://1.1.1.1", "https://www.bing.com"]:
        try:
            requests.get(url, timeout=2)
            return True
        except:
            continue
    # Test Socket direct sur DNS Google (8.8.8.8) - utile en cas de DNS local buggé
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except:
        return False
    
def resoudre_math_localement(texte):
    """Résout des calculs simples localement sans appeler l'IA."""
    t = texte.lower().replace("?", "").strip()
    
    # Nettoyage des phrases communes
    prefixes = ["combien font", "calcule", "résous", "quel est le résultat de"]
    for prefixe in prefixes:
        if t.startswith(prefixe):
            t = t[len(prefixe):].strip()
            
    # Remplacement des mots par des symboles
    t = t.replace("fois", "*").replace("multiplier par", "*").replace("x", "*")
    t = t.replace("divisé par", "/").replace("sur", "/")
    t = t.replace("plus", "+").replace("moins", "-")
    t = t.replace("puissance", "**").replace("au carré", "**2")
    
    # Cas spécial racine : on s'assure d'avoir des parenthèses pour eval
    if "racine" in t:
        # On cherche un nombre après 'racine'
        match = re.search(r'racine\s+(?:carrée\s+de\s+)?(\d+)', t)
        if match:
            t = f"sqrt({match.group(1)})"
        else:
            t = t.replace("racine carrée de", "sqrt").replace("racine de", "sqrt")
    
    # Extraction de l'expression mathématique (chiffres, opérateurs, parenthèses, points)
    expr = re.sub(r'[^0-9+\-*/.**() ,sqrt]', '', t).strip()
    if not expr or not any(c.isdigit() for c in expr):
        return None
    
    try:
        # Dictionnaire de sécurité pour eval
        safe_dict = {
            "sqrt": math.sqrt,
            "pow": math.pow,
            "pi": math.pi,
            "e": math.e
        }
        resultat = eval(expr, {"__builtins__": None}, safe_dict)
        
        # Formatage du résultat
        if isinstance(resultat, float) and resultat.is_integer():
            resultat = int(resultat)
        elif isinstance(resultat, float):
            resultat = round(resultat, 3)
            
        # Phrase de réponse élégante
        clean_expr = expr.replace("**2", " au carré").replace("sqrt", "racine de ").replace("(", "").replace(")", "").replace("*", " fois ").replace("/", " divisé par ")
        return f"Le résultat de {clean_expr} est {resultat}, Monsieur."
    except Exception:
        return None

def resoudre_francais_localement(texte):
    """Résout des questions de français simples localement."""
    t = texte.lower().strip()
    
    # Dictionnaire local de secours (très basique)
    dictionnaire = {
        "ia": "Intelligence Artificielle. Ensemble de théories et de techniques mises en œuvre en vue de réaliser des machines capables de simuler l'intelligence humaine.",
        "intelligence artificielle": "Ensemble de théories et de techniques mises en œuvre en vue de réaliser des machines capables de simuler l'intelligence humaine.",
        "maison": "Bâtiment servant de logement, d'habitation.",
        "mathématiques": "Science qui étudie par le moyen du raisonnement déductif les propriétés d'êtres abstraits.",
        "jarvis": "Just A Rather Very Intelligent System. Votre fidèle assistant.",
    }
    
    # Définitions
    if any(p in t for p in ["définition de", "définis le mot", "c'est quoi"]):
        # On essaie d'extraire le mot après les phrases clés
        mot = ""
        if "définition de" in t: mot = t.split("définition de")[-1]
        elif "définis le mot" in t: mot = t.split("définis le mot")[-1]
        elif "c'est quoi" in t: mot = t.split("c'est quoi")[-1]
        
        mot = mot.replace("?", "").replace("l'", "").replace("la ", "").replace("le ", "").replace("les ", "").strip()
        
        if mot in dictionnaire:
            return f"La définition de {mot} est : {dictionnaire[mot]}."
            
    # Conjugaison basique
    if "conjugue" in t or "conjugaison" in t:
        if "être" in t:
            return "Verbe Être au présent : Je suis, tu es, il est, nous sommes, vous êtes, ils sont."
        if "avoir" in t:
            return "Verbe Avoir au présent : J'ai, tu as, il a, nous avons, vous avez, ils ont."
            
    return None

def resoudre_conversion_localement(texte):
    """Gère les conversions d'unités et de devises localement."""
    t = texte.lower().replace("?", "").strip()
    
    # Unités de longueur
    if any(m in t for m in [" km ", " kilomètres ", " milles ", " miles "]):
        # km to miles: 0.621371
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:km|kilomètres)', t)
        if match:
            val = float(match.group(1).replace(",", "."))
            res = round(val * 0.621371, 2)
            return f"{val} kilomètres font environ {res} miles, Monsieur."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:miles|milles)', t)
        if match:
            val = float(match.group(1).replace(",", "."))
            res = round(val / 0.621371, 2)
            return f"{val} miles font environ {res} kilomètres, Monsieur."

    # Température (C to F)
    if any(m in t for m in [" degrés ", " celsius ", " fahrenheit "]):
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:degrés|celsius)', t)
        if match and "fahrenheit" in t:
            val = float(match.group(1).replace(",", "."))
            res = round((val * 9/5) + 32, 1)
            return f"{val} degrés Celsius font {res} degrés Fahrenheit."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:degrés|fahrenheit)', t)
        if match and "celsius" in t:
            val = float(match.group(1).replace(",", "."))
            res = round((val - 32) * 5/9, 1)
            return f"{val} degrés Fahrenheit font {res} degrés Celsius."

    # Devises (Taux fixes simplifiés pour l'exemple local)
    if any(m in t for m in [" euro ", " euros ", " dollar ", " dollars "]):
        # 1 EUR = 1.08 USD (approximatif)
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*euros?', t)
        if match and "dollar" in t:
            val = float(match.group(1).replace(",", "."))
            res = round(val * 1.08, 2)
            return f"{val} euros font environ {res} dollars, Monsieur."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*dollars?', t)
        if match and "euro" in t:
            val = float(match.group(1).replace(",", "."))
            res = round(val / 1.08, 2)
            return f"{val} dollars font environ {res} euros, Monsieur."
            
    return None

def resoudre_traduction_localement(texte):
    """Traduction ultra-rapide de mots courants localement."""
    t = texte.lower().strip()
    
    dict_trad = {
        "bonjour": {"en": "hello", "es": "hola", "de": "hallo"},
        "merci": {"en": "thank you", "es": "gracias", "de": "danke"},
        "au revoir": {"en": "goodbye", "es": "adiós", "de": "auf wiedersehen"},
        "s'il vous plaît": {"en": "please", "es": "por favor", "de": "bitte"},
        "oui": {"en": "yes", "es": "sí", "de": "ja"},
        "non": {"en": "no", "es": "no", "de": "nein"},
        "ami": {"en": "friend", "es": "amigo", "de": "freund"},
        "maison": {"en": "house", "es": "casa", "de": "haus"},
        "ordinateur": {"en": "computer", "es": "ordenador", "de": "computer"},
        "assistant": {"en": "assistant", "es": "asistente", "de": "assistent"},
    }

    if any(p in t for p in ["comment dit-on", "traduis", "en anglais", "en espagnol", "en allemand"]):
        cible = "en"
        if "espagnol" in t: cible = "es"
        elif "allemand" in t: cible = "de"
        
        # Extraction du mot
        # On nettoie les expressions courantes
        mot = t
        for p in ["comment dit-on", "traduis", "en anglais", "en espagnol", "en allemand", "?"]:
            mot = mot.replace(p, "")
        mot = mot.replace('"', '').replace("'", "").strip()
        
        if mot in dict_trad:
            res = dict_trad[mot][cible]
            lang = "anglais" if cible == "en" else ("espagnol" if cible == "es" else "allemand")
            return f"En {lang}, '{mot}' se dit '{res}'."
            
    return None

async def demander_ia(texte):

    global is_thinking
    is_thinking = True
    await send_web_state("thinking")
    try:
        cerveau = detecter_cerveau(texte)

        async def _call_gemini():
            print(f"[CERVEAU] Tentative avec Gemini (Liste: {MODELS_LIST})...")
            # On ne modifie pas l'historique global avant d'être sûr que ça marche
            temp_hist = historique + [types.Content(role="user", parts=[types.Part(text=texte)])]
            prompt_actuel = construire_system_prompt()
            
            last_err = None
            for model_name in MODELS_LIST:
                try:
                    print(f"[CERVEAU] Essai modele : {model_name} (Timeout 12s)")
                    # Utilisation de to_thread pour ne pas bloquer la boucle et pouvoir mettre un timeout
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=prompt_actuel,
                                temperature=0.7,
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                            ),
                            contents=temp_hist
                        ),
                        timeout=12.0
                    )
                    rep = response.text
                    # Succès : mise à jour de l'historique officiel
                    historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                    historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
                    return rep
                except Exception as e:
                    print(f"[CERVEAU] Echec {model_name} : {e}")
                    last_err = e
                    continue
            
            raise last_err or Exception("Tous les modeles Gemini ont echoue")

        async def _call_grok():
            print("[CERVEAU] Tentative avec Grok...")
            rep_grok = await demander_grok(texte)
            if not rep_grok:
                raise Exception("Grok n'a rien renvoyé ou est mal configuré")
            return rep_grok

        # Logique de bascule bidirectionnelle
        if cerveau == "GROK" and grok_client:
            try:
                return await _call_grok()
            except Exception as e:
                print(f"[CERVEAU] Erreur Grok ({e}). Bascule sur Gemini.")
                try:
                    return await _call_gemini()
                except Exception as e2:
                    print(f"[ERREUR IA (Gemini repli)] {e2}")
        else:
            try:
                return await _call_gemini()
            except Exception as e:
                print(f"[CERVEAU] Erreur Gemini ({e}). Bascule sur SerpAPI.")
                
                # --- FALLBACK SERPAPI ---
                if len(texte.split()) > 2:
                    res_serp = recherche_web_serpapi(texte)
                    if res_serp and "VOTRE_CLE" not in res_serp and "rien trouvé" not in res_serp and "erreur" not in res_serp.lower():
                        return "Voici ce que j'ai trouvé sur le web : " + res_serp

                # --- FALLBACK GROQ (LLAMA 3.3) ---
                print("[CERVEAU] Bascule sur Groq (Qwen).")
                if groq_client:
                    rep_groq = await demander_groq(texte)
                    if rep_groq:
                        return rep_groq
                
                # --- FALLBACK GROK (xAI) ---
                print("[CERVEAU] Bascule sur Grok (xAI).")
                if grok_client:
                    try:
                        return await _call_grok()
                    except Exception as e2:
                        print(f"[ERREUR IA (Grok repli)] {e2}")
        # --- FALLBACK OLLAMA (100% offline) ---
        print("[CERVEAU] Gemini et Grok KO. Tentative Ollama (local)...")
        rep_ollama = await demander_ollama(texte)
        if rep_ollama:
            return rep_ollama

        # --- FALLBACK LOCAL ---
        print("[CERVEAU] Tous les serveurs IA ont echoue. Tentative fallback local...")
        rep_loc = reponse_locale(texte)
        if rep_loc:
            return rep_loc
            
        return "Desole Aboubakar Ibrahim Siddick, mes serveurs de réflexion profonde sont surchargés et mes modèles locaux ne sont pas disponibles non plus. Je reste cependant disponible pour vos commandes domestiques."
    finally:
        is_thinking = False
        await send_web_state("idle")

async def demander_ia_vision(texte, img_b64):
    """Analyse une image (capture d'écran) avec Gemini Vision."""
    global is_thinking, historique
    is_thinking = True
    await send_web_state("thinking")
    try:
        print("[VISION] Analyse de l'image avec Gemini...")
        
        # Conversion base64 en bytes pour l'API
        img_bytes = base64.b64decode(img_b64)
        image_part = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg"
        )
        
        prompt_actuel = construire_system_prompt()
        prompt_actuel += "\n\nIMPORTANT : Tu viens de recevoir une capture d'écran de Aboubakar Ibrahim Siddick. Analyse-la attentivement et réponds à sa question en te basant sur ce que tu vois."
        
        # On envoie l'image et le texte avec retry en cas de 503
        contents = [
            types.Content(role="user", parts=[image_part, types.Part(text=texte)])
        ]
        
        rep = None
        last_err = None
        for model_name in MODELS_LIST:
            print(f"[VISION] Essai modele : {model_name}")
            for attempt in range(2): # 2 tentatives par modele
                try:
                    print(f"[VISION] Appel modele : {model_name} (Timeout 15s)")
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=prompt_actuel,
                                temperature=0.7,
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                            ),
                            contents=contents
                        ),
                        timeout=15.0
                    )
                    rep = response.text
                    break
                except Exception as e:
                    if ("503" in str(e) or "overloaded" in str(e).lower()) and attempt < 1:
                        print(f"[VISION] Surcharge {model_name} (503). Retente...")
                        await asyncio.sleep(1)
                        continue
                    print(f"[VISION] Erreur {model_name} : {e}")
                    last_err = e
                    break
            if rep: break
        
        if not rep:
            print("[VISION] Tous les modeles Gemini ont echoue. Bascule sur Grok (Texte uniquement)...")
            if grok_client:
                return await demander_grok(texte + " (Note: Je n'ai pas pu voir ton écran suite à un quota dépassé, utilise les données textuelles OCR déjà présentes dans ta mémoire pour répondre).")
            raise last_err or Exception("Aucun modele n'a pu analyser l'image")

        # On ajoute la trace dans l'historique (sans l'image pour éviter de saturer la mémoire)
        historique.append(types.Content(role="user", parts=[types.Part(text=f"[Analyse d'écran] {texte}")]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        
        return rep
    except Exception as e:
        print(f"[VISION] Erreur Gemini Vision : {e}")
        # On évite les accolades dans le message d'erreur pour ne pas perturber l'extracteur JSON
        err_msg = str(e).replace("{", "[").replace("}", "]")
        return f"Désolé Aboubakar Ibrahim Siddick, je n'ai pas pu analyser votre écran. Erreur : {err_msg}"
    finally:
        is_thinking = False
        await send_web_state("idle")

def detecter_cerveau(texte):
    # Heuristique pour basculer sur Grok uniquement pour X/Twitter
    mots_cles_grok = ["sur x", "twitter", "grok", "elon", "x.com"]
    cmd = texte.lower()
    if any(m in cmd for m in mots_cles_grok):
        return "GROK"
    return "GEMINI"

async def demander_grok(texte):
    if not grok_client:
        return None
    
    try:
        # Conversion de l'historique Gemini vers format OpenAI pour Grok
        messages = [{"role": "system", "content": "Tu es JARVIS, l'IA de Aboubakar Ibrahim Siddick. Tu utilises actuellement ton module Grok pour les infos en temps reel."}]
        for h in historique[-6:]: # Limiter aux 6 derniers messages pour eviter de saturer le contexte
            role = "user" if h.role == "user" else "assistant"
            msg_text = h.parts[0].text
            messages.append({"role": role, "content": msg_text})
        
        messages.append({"role": "user", "content": texte})
        
        completion = grok_client.chat.completions.create(
            model="grok-3", 
            messages=messages,
            temperature=0.7,
        )
        
        rep = completion.choices[0].message.content
        
        # On synchronise l'historique Gemini
        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        
        return rep
    except Exception as e:
        print(f"[ERREUR GROK] {e}")
        return None

async def demander_ollama(texte):
    """Appelle un modèle local via Ollama (100% offline)."""
    global historique
    try:
        # On prépare les messages au format Ollama (compatible OpenAI)
        messages = [{"role": "system", "content": "Tu es JARVIS, l'IA de Aboubakar Ibrahim Siddick. Tu utilises actuellement ton module local Ollama. Réponds en français, de façon concise et élégante."}]
        for h in historique[-4:]:
            role = "user" if h.role == "user" else "assistant"
            messages.append({"role": role, "content": h.parts[0].text})
        messages.append({"role": "user", "content": texte})
        
        last_err = None
        for model_name in OLLAMA_MODELS:
            try:
                print(f"[OLLAMA] Essai modele local : {model_name}")
                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        requests.post,
                        f"{OLLAMA_URL}/api/chat",
                        json={"model": model_name, "messages": messages, "stream": False},
                        timeout=30
                    ),
                    timeout=35.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rep = data.get("message", {}).get("content", "")
                    if rep:
                        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
                        print(f"[OLLAMA] Reponse recue de {model_name}")
                        return rep
                else:
                    print(f"[OLLAMA] Erreur HTTP {resp.status_code} pour {model_name}")
                    last_err = Exception(f"HTTP {resp.status_code}")
            except Exception as e:
                print(f"[OLLAMA] Echec {model_name} : {e}")
                last_err = e
                continue
        
        print(f"[OLLAMA] Tous les modeles locaux de la liste ont echoue.")
        if last_err and "404" in str(last_err):
            return "Desole Aboubakar Ibrahim Siddick, je n ai pas trouve de modele Ollama installe. Veuillez lancer la commande 'ollama pull llama3' ou 'ollama pull mistral' dans votre terminal."
        return None
    except Exception as e:
        print(f"[ERREUR OLLAMA] {e}")
        return None

async def demander_groq(texte):
    """Appelle Groq (Qwen) en fallback gratuit."""
    if not groq_client:
        return None
    
    try:
        messages = [{"role": "system", "content": "Tu es JARVIS, l'IA de Aboubakar Ibrahim Siddick. Tu utilises actuellement le modèle Qwen de Groq pour répondre rapidement."}]
        for h in historique[-6:]:
            role = "user" if h.role == "user" else "assistant"
            messages.append({"role": role, "content": h.parts[0].text})
        messages.append({"role": "user", "content": texte})
        
        completion = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="qwen3.6-27b",
            messages=messages,
            temperature=0.7,
        )
        
        rep = completion.choices[0].message.content
        
        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        
        return rep
    except Exception as e:
        print(f"[ERREUR GROQ] {e}")
        return None

async def action_whatsapp_appel(contact):
    try:
        await parler(f"J'appelle {contact} sur WhatsApp, Aboubakar Ibrahim Siddick.")
        # Lancement de l'app via le protocole
        os.system("start whatsapp://")
        time.sleep(6) # On laisse le temps a l'app de s'ouvrir et se focuser
        
        # Recherche du contact (Ctrl+F)
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1)
        pyautogui.typewrite(contact)
        time.sleep(2)
        pyautogui.press('enter')
        time.sleep(3) # On attend que la conversation s'affiche bien
        
        # Utilisation du raccourci clavier officiel pour l'appel audio (plus fiable que la vision)
        print(f"[WHATSAPP] Envoi du raccourci d'appel (Ctrl+Shift+C)...")
        pyautogui.hotkey('ctrl', 'shift', 'c')
        
        # On ajoute quand meme un petit clic de vision en secours si le raccourci ne suffit pas
        time.sleep(2)
        print(f"[WHATSAPP] Verification par vision au cas ou...")
        await jarvis_vision_cliquer("clique sur le bouton 'Appel vocal' ou l icone de telephone qui vient de s afficher en haut a droite")
        
        return True
    except Exception as e:
        print(f"[WHATSAPP ERROR] {e}")
        await parler(f"Desole Aboubakar Ibrahim Siddick, je n'ai pas pu lancer l'appel WhatsApp. {e}")
        return False

async def traiter_reponse_ia(texte_utilisateur, mobile_ws=None):
    global MODE_IRON_MAN, jarvis_actif, dernier_message, _skip_pc_audio
    # Reset du flag audio au début de chaque commande
    _skip_pc_audio = False

    # 1. RÉSOLUTION LOCALE
    reponse = resoudre_math_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_francais_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_conversion_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_traduction_localement(texte_utilisateur)
    
    if reponse:
        await parler(reponse)
        return

    # 1.1 ACTIONS SYSTÈME ET CONTRÔLE PC (SEC-03 avec isolation de session)
    session_id = getattr(mobile_ws, "session_id", "desktop_local") if mobile_ws else "desktop_local"
    client_ip = mobile_ws.remote_address[0] if (mobile_ws and mobile_ws.remote_address and len(mobile_ws.remote_address) > 0) else "local"
    action_pc = executer_action_pc(texte_utilisateur, session_id=session_id, client_ip=client_ip)
    if action_pc:
        await parler(action_pc)
        return

    # 2. SOURCE IA (Streaming)
    stream_gen = None
    t_lower = texte_utilisateur.lower()
    
    if any(k in t_lower for k in ["regarde mon écran", "analyse mon écran", "vois-tu mon écran"]):
        await parler("Bien sûr Aboubakar Ibrahim Siddick, laissez-moi jeter un œil...")
        img_b64 = await request_screen_capture()
        if img_b64:
            stream_gen = demander_ia_vision_stream(texte_utilisateur, img_b64)
        else:
            await parler("Je n'ai pas pu capturer votre écran.")
            return

    if not stream_gen:
        stream_gen = demander_ia_stream(texte_utilisateur)

    # 3. TRAITEMENT DU STREAM (Parallel TTS)
    full_response = ""
    sentence_buffer = ""
    tasks = []
    
    if mobile_ws:
        # On garde l'audio sur PC par défaut pour plus de clarté
        _skip_pc_audio = False

    try:
        async for chunk in stream_gen:
            full_response += chunk
            sentence_buffer += chunk
            
            # On cherche des phrases complètes à énoncer en parallèle du flux
            if "{" not in sentence_buffer:
                while True:
                    match = re.search(r'[.!?](\s+|$)', sentence_buffer)
                    if not match: break
                    sentence = sentence_buffer[:match.end()].strip()
                    sentence_buffer = sentence_buffer[match.end():]
                    if sentence:
                        tasks.append(asyncio.create_task(parler(sentence)))
    except Exception as e:
        print(f"[STREAM ERROR] {e}")

    # Fin du flux : traitement du reste du buffer
    if sentence_buffer.strip() and "{" not in sentence_buffer:
        tasks.append(asyncio.create_task(parler(sentence_buffer.strip())))
    
    # Attente de la fin de toutes les paroles avant de clore le traitement
    if tasks:
        await asyncio.gather(*tasks)
    
    reponse = full_response
    print(f"[JARVIS] Réponse complète : {reponse}")

    # Recherche de TOUS les blocs JSON dans la réponse complète pour exécution
    json_blocks = re.findall(r'\{.*?\}', reponse, re.DOTALL)
    
    if not json_blocks:
        _skip_pc_audio = False
        return

    for block in json_blocks:
        try:
            print(f"[JARVIS] Execution de l'action : {block}")
            # Timeout de 15s pour chaque action pour eviter de freezer Jarvis
            data = json.loads(block)
            action = data.get("action", "")
            
            # On execute l'action avec un timeout
            try:
                # Note: On utilise asyncio.wait_for pour les actions asynchrones
                # Les actions synchrones comme ha_lumiere devraient idéalement être async aussi
                # mais pour l'instant on les laisse ainsi ou on les wrappe.
                pass 
            except asyncio.TimeoutError:
                print(f"[ACTION ERROR] Timeout sur l'action {action}")
                if grok_client:
                    await parler("C'est un peu long Aboubakar Ibrahim Siddick, je demande une vérification à Grok.")
                    rep_grok = await demander_grok(texte_utilisateur + " (L'action domotique a expiré, peux-tu répondre à l'utilisateur ?)")
                    if rep_grok: await parler(rep_grok)
                continue

            if action == "mode_iron_man":
                etat = data.get("etat", "off")
                MODE_IRON_MAN = (etat == "on")
                if MODE_IRON_MAN:
                    msg = "Mode Alice activé, Monsieur. Protocoles Armure en ligne. Je reste à l'écoute de vos signaux."
                    # Feedback visuel (si lumières dispos)
                    try:
                        entity_id = PIECES_LUMIERES.get("salon", "light.salon")
                        ha_lumiere(entity_id, "on", rgb=[255, 0, 0]) # Rouge Iron Man
                        time.sleep(0.5)
                        ha_lumiere(entity_id, "on", rgb=[255, 255, 255])
                    except: pass
                else:
                    msg = "Mode Alice désactivé. Protocoles de défense mis en veille. Je repasse en mode normal."
                await parler(msg)
            elif action == "lancer_application":
                nom_app = data.get("nom", "")
                if nom_app:
                    resultat_app = lancer_app(nom_app)
                    await parler(resultat_app)
                else:
                    await parler("Je n'ai pas compris le nom de l'application à lancer.")

            elif action == "memoriser":
                cle    = data.get("cle",    "info")
                valeur = data.get("valeur", "")
                ajouter_memoire(cle, valeur)
                await parler(f"Bien note Aboubakar Ibrahim Siddick, je me souviendrai que {valeur}.")
            elif action == "oublier":
                cle     = data.get("cle", "")
                success = supprimer_memoire(cle)
                if success:
                    await parler("Information oubliee, Aboubakar Ibrahim Siddick.")
                else:
                    await parler("Je n avais pas cette information en memoire.")
            elif action == "lister_memoire":
                memoire = charger_memoire()
                if not memoire:
                    await parler("Aucune information personnalisee en memoire, Aboubakar Ibrahim Siddick.")
                else:
                    lignes = ["Voici ce que je sais sur vous Aboubakar Ibrahim Siddick."]
                    for cle, data_m in memoire.items():
                        lignes.append(f"{cle} : {data_m['valeur']}.")
                    await parler(" ".join(lignes))
            elif action == "ouvrir_dossier":
                chemin = data.get("chemin", "bureau")
                ok, resultat = ouvrir_dossier(chemin)
                if ok:
                    await parler("Dossier ouvert, Aboubakar Ibrahim Siddick. Dites-moi si vous voulez que je le trie.")
                else:
                    await parler(f"Je n ai pas trouve ce dossier, Aboubakar Ibrahim Siddick. {resultat}")
            elif action == "lister_dossier":
                contenu, err = lister_dossier()
                if err:
                    await parler(err)
                else:
                    nb_fichiers = len(contenu["fichiers"])
                    nb_dossiers = len(contenu["dossiers"])
                    await parler(f"Le dossier contient {nb_fichiers} fichiers et {nb_dossiers} sous-dossiers, Aboubakar Ibrahim Siddick.")
            elif action == "trier_par_type":
                await parler("Je trie vos fichiers par type, Aboubakar Ibrahim Siddick. Un instant.")
                ok, msg = trier_par_type()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "trier_par_date":
                await parler("Je trie vos fichiers par date, Aboubakar Ibrahim Siddick. Un instant.")
                ok, msg = trier_par_date()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "trier_complet":
                await parler("Je trie vos fichiers par type puis par date dans chaque categorie, Aboubakar Ibrahim Siddick.")
                ok, msg = trier_par_type_puis_date()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "creer_dossier":
                nom     = data.get("nom", "Nouveau Dossier")
                ok, msg = creer_sous_dossier(nom)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "renommer_fichier":
                ancien  = data.get("ancien", "")
                nouveau = data.get("nouveau", "")
                ok, msg = renommer_fichier(ancien, nouveau)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "deplacer_fichier":
                fichier = data.get("fichier",     "")
                dest    = data.get("destination", "")
                ok, msg = deplacer_fichier(fichier, dest)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "chercher_fichier":
                nom        = data.get("nom", "")
                resultats, err = chercher_fichier(nom)
                if err:
                    await parler(err)
                elif not resultats:
                    await parler(f"Aucun fichier contenant {nom} n a ete trouve, Aboubakar Ibrahim Siddick.")
                else:
                    noms = [os.path.basename(r) for r in resultats[:5]]
                    await parler(f"J ai trouve {len(resultats)} fichier(s). Par exemple : {', '.join(noms)}.")
            elif action == "ha_lumiere":
                piece      = data.get("piece",      "salon")
                etat       = data.get("etat",       "on")
                couleur    = data.get("couleur",    None)
                luminosite = data.get("luminosite", None)
                entity_id  = PIECES_LUMIERES.get(piece, f"light.{piece}")
                rgb        = COULEURS_MAP.get(couleur) if couleur else None
                result     = ha_lumiere(entity_id, etat, luminosite, rgb, verify_state=True)
                
                status = result.get("status") if isinstance(result, dict) else (HA_STATE_VERIFIED if result else HA_FAILED)
                actual_state = result.get("state") if isinstance(result, dict) else "unknown"

                # C-04 / SEC-05 : Distinguo strict entre acceptation et état physique vérifié
                if status == HA_FAILED:
                    await parler(f"Impossible d'actionner la lumière de {piece} : la commande Home Assistant a échoué ou l'appareil est injoignable.")
                elif status == HA_STATE_VERIFIED:
                    if etat == "off":
                        msg = f"J'éteins {piece}. État physique vérifié : éteinte."
                    else:
                        details = []
                        if couleur: details.append(f"en {couleur}")
                        if luminosite is not None: 
                            pourcent = int((int(luminosite)/255)*100)
                            details.append(f"à {pourcent}%")
                        det_str = f" {' '.join(details)}" if details else ""
                        msg = f"C'est fait, lumière {piece} allumée{det_str}. État matériel vérifié."
                    await parler(msg)
                elif status == HA_STATE_UNKNOWN:
                    await parler(f"L'ordre pour la lumière de {piece} a été transmis, mais l'état réel de l'ampoule reste indéterminé.")
                else: # TIMEOUT ou REQUEST_ACCEPTED avec état non confirmé
                    await parler(f"Attention : l'ordre a été envoyé à Home Assistant, mais l'appareil {piece} signale toujours l'état : {actual_state}.")

            elif action == "ha_prise":
                piece        = data.get("piece", "bureau")
                etat         = data.get("etat",  "on")
                entity_id    = PIECES_PRISES.get(piece, f"switch.prise_{piece}")
                result       = ha_interrupteur(entity_id, etat, verify_state=True)
                status       = result.get("status") if isinstance(result, dict) else (HA_STATE_VERIFIED if result else HA_FAILED)
                actual_state = result.get("state") if isinstance(result, dict) else "unknown"

                if status == HA_FAILED:
                    await parler(f"Impossible d'actionner la prise de {piece} : la commande Home Assistant a échoué.")
                elif status == HA_STATE_VERIFIED:
                    msg = f"Prise {piece} {'activée' if etat == 'on' else 'désactivée'}. État matériel vérifié."
                    await parler(msg)
                elif status == HA_STATE_UNKNOWN:
                    await parler(f"L'ordre pour la prise {piece} a été transmis, mais l'état réel de l'équipement reste indéterminé.")
                else:
                    await parler(f"Attention : l'ordre a été envoyé pour la prise {piece}, mais l'équipement signale toujours l'état : {actual_state}.")
            elif action == "ha_temperature":
                piece     = data.get("piece", "salon")
                entity_id = PIECES_CAPTEURS.get(piece)
                if entity_id:
                    temp = ha_get_etat(entity_id)
                    await parler(f"La température dans le {piece} est de {temp} degrés.")
                else:
                    await parler(f"Désolé, je n'ai pas de capteur configuré pour le {piece}.")
            elif action == "ha_humidite":
                piece     = data.get("piece", "bureau")
                entity_id = PIECES_HUMIDITE.get(piece)
                if entity_id:
                    humi = ha_get_etat(entity_id)
                    await parler(f"Le taux d'humidité dans le {piece} est de {humi}%.")
                else:
                    await parler(f"Je n'ai pas de capteur d'humidité pour le {piece}.")
            elif action == "ha_batterie":
                appareil  = data.get("appareil", "").lower()
                entity_id = APPAREILS_BATTERIE.get(appareil)
                if entity_id:
                    batt = ha_get_etat(entity_id)
                    if batt == "unknown":
                        await parler(f"Je n'arrive pas à récupérer l'état de la batterie pour {appareil}.")
                    else:
                        suff = ""
                        if "telephone" in appareil or "papa" in appareil or "aboubakar ibrahim siddick" in appareil:
                            suff = "Ton téléphone est à "
                        elif "julie" in appareil or "maman" in appareil:
                            suff = "Le téléphone de Julie est à "
                        else:
                            suff = f"La batterie de {appareil} est à "
                        await parler(f"{suff}{batt}%.")
                else:
                    await parler(f"Je n'ai pas l'appareil {appareil} dans ma liste de batterie.")
            elif action == "ha_thermostat":
                temp = data.get("temperature", 20)
                success = ha_thermostat("climate.thermostat", temp)
                if not success:
                    await parler(f"Impossible de régler le thermostat à {temp} degrés. La commande Home Assistant a échoué.")
                else:
                    await parler(f"Thermostat réglé à {temp} degrés.")
            elif action == "ha_scene":
                nom      = data.get("nom", "")
                scene_id = f"scene.{nom}"
                success  = ha_scene(scene_id)
                if not success:
                    await parler(f"Impossible d'activer l'ambiance {nom}. La commande Home Assistant a échoué.")
                else:
                    await parler(f"Ambiance {nom} activée.")
            elif action == "ha_alarme":
                etat = data.get("etat", "on")
                alarm_entity = "alarm_control_panel.home_base_2"
                if etat == "on":
                    service_ok = ha_appeler_service("alarm_control_panel", "alarm_arm_away", alarm_entity)
                    if not service_ok:
                        await parler("Impossible d'armer l'alarme : la requête vers Home Assistant a échoué.")
                    else:
                        # Vérification de l'état physique réel (SEC-05 : REQUEST_ACCEPTED != STATE_VERIFIED)
                        etat_reel = ha_get_etat(alarm_entity)
                        if etat_reel in ["armed_away", "armed_home", "armed_night", "arming", "pending"]:
                            await parler(f"Alarme armée avec succès. État de la centrale vérifié : {etat_reel}.")
                        elif etat_reel in ["unknown", "inconnu"]:
                            await parler("Ordre d'armement transmis à Home Assistant, mais l'état physique de la centrale reste indéterminé.")
                        else:
                            await parler(f"Alerte : l'ordre d'armement a été transmis, mais la centrale signale l'état suivant : {etat_reel}.")
                else:
                    service_ok = ha_appeler_service("alarm_control_panel", "alarm_disarm", alarm_entity)
                    if not service_ok:
                        await parler("Impossible de désarmer l'alarme : la requête vers Home Assistant a échoué.")
                    else:
                        # Vérification de l'état physique réel (SEC-05)
                        etat_reel = ha_get_etat(alarm_entity)
                        if etat_reel in ["disarmed", "disarming"]:
                            await parler("Alarme désarmée avec succès. État physique confirmé.")
                        elif etat_reel in ["unknown", "inconnu"]:
                            await parler("Ordre de désarmement transmis, mais la confirmation de l'état de la centrale est en attente.")
                        else:
                            await parler(f"Attention : l'ordre de désarmement a été transmis, mais la centrale signale : {etat_reel}.")
            elif action == "ha_simulation":
                etat = data.get("etat", "on")
                success = ha_interrupteur("switch.simulation", etat)
                if not success:
                    await parler("Impossible de modifier la simulation de présence. La commande Home Assistant a échoué.")
                else:
                    msg = "Simulation de présence activée." if etat == "on" else "Simulation de présence désactivée."
                    await parler(msg)
            elif action == "ha_anniversaires":
                events = ha_get_calendrier("calendar.anniversaires")
                if not events:
                    await parler("Rien de prévu aujourd'hui.")
                else:
                    noms = [e.get("summary", "Anniversaire sans nom") for e in events]
                    if len(noms) == 1:
                        await parler(f"Aujourd'hui, nous fêtons l'anniversaire de {noms[0]}. N'oubliez pas de lui souhaiter !")
                    else:
                        liste = ", ".join(noms[:-1]) + " et " + noms[-1]
                        await parler(f"Aujourd'hui, il y a plusieurs anniversaires : {liste}. C'est une journée chargée !")
            elif action == "ha_consommation":
                entity_id = PIECES_CAPTEURS.get("consommation")
                puissance = ha_get_etat(entity_id)
                if puissance == "unknown" or puissance == "inconnu":
                    await parler("Je n'arrive pas à lire la consommation électrique pour le moment.")
                else:
                    await parler(f"La consommation actuelle de la maison est de {puissance} Volt-Ampères.")
            elif action == "ha_tiktok":
                entity_id = PIECES_CAPTEURS.get("tiktok")
                followers = ha_get_etat(entity_id)
                await parler(f"Tu as actuellement {followers} abonnés sur ton compte TikTok TechEnClair, Aboubakar Ibrahim Siddick. Félicitations !")
            elif action == "ha_oeufs":
                entity_id = PIECES_CAPTEURS.get("oeufs")
                # On récupère l'état (le dernier choix) et le moment de la modif
                try:
                    r = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
                    data = r.json()
                    last_changed = data.get("last_changed", "")
                    if last_changed:
                        dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                        phrase = dt.strftime("le %d %B à %Hh%M")
                        await parler(f"Le dernier ramassage des œufs a été enregistré {phrase}.")
                    else:
                        await parler("Je n'ai pas d'historique pour le ramassage des œufs.")
                except:
                    await parler("Je n'arrive pas à accéder aux informations sur les œufs.")
            elif action == "ha_energie":
                periode  = data.get("periode", "mois")
                appareil = data.get("appareil", "")
                
                if appareil:
                    appareil_clean = appareil.lower()
                    entite = APPAREILS_ENERGIE.get(appareil_clean)
                    if entite:
                        val = ha_get_etat(entite)
                        if val != "inconnu" and val != "unknown":
                            kwh = float(val)
                            await parler(f"La consommation de {appareil} pour ce mois est de {kwh:.1f} kWh.")
                        else:
                            await parler(f"Je n'ai pas de données de consommation pour {appareil} pour le moment.")
                    else:
                        await parler(f"Je n'ai pas d'appareil nommé {appareil} dans mon suivi énergétique.")
                elif periode == "hier":
                    total_kwh = 0
                    total_cost = 0
                    try:
                        for i in range(1, 7):
                            e_id = f"sensor.lixee_zlinky_tic_zlinky_p{i}_daily"
                            val = ha_get_etat(e_id, attribut="last_period")
                            if val != "inconnu" and val != "unknown":
                                k = float(val)
                                total_kwh += k
                                total_cost += k * HA_TARIFS.get(f"p{i}", 0.16)
                        await parler(f"Hier, la maison a consommé {total_kwh:.1f} kWh, pour un coût estimé à {total_cost:.2f} euros.")
                    except:
                        await parler("J'ai eu un problème pour calculer la consommation d'hier.")
                else: # mois
                    total_kwh = 0
                    total_cost = 0
                    try:
                        for i in range(1, 7):
                            e_id = f"sensor.lixee_zlinky_tic_zlinky_p{i}_mensuel"
                            val = ha_get_etat(e_id)
                            if val != "inconnu" and val != "unknown":
                                k = float(val)
                                total_kwh += k
                                total_cost += k * HA_TARIFS.get(f"p{i}", 0.16)
                        await parler(f"Ce mois-ci, la consommation totale est de {total_kwh:.1f} kWh, pour un montant de {total_cost:.2f} euros.")
                    except:
                        await parler("Je n'ai pas pu calculer la consommation mensuelle.")
            elif action == "ha_aspirateur":
                commande = data.get("commande", "start")
                if commande == "start":
                    ha_appeler_service("vacuum", "start", "vacuum.bob")
                    await parler("C'est parti, Bob lance le nettoyage.")
                elif commande == "stop":
                    ha_appeler_service("vacuum", "stop", "vacuum.bob")
                    await parler("J'ai arrêté l'aspirateur.")
                elif commande == "pause":
                    ha_appeler_service("vacuum", "pause", "vacuum.bob")
                    await parler("Bob est en pause.")
                elif commande == "base":
                    ha_appeler_service("vacuum", "return_to_base", "vacuum.bob")
                    await parler("Bob retourne à sa base.")
            elif action == "create_doc":
                if not os.path.exists("token.pickle"):
                    await parler("Aboubakar Ibrahim Siddick, je vais avoir besoin de votre autorisation. Veuillez sélectionner votre compte Google dans la fenêtre qui vient de s'ouvrir.")
                titre   = data.get("title",   "Document JARVIS")
                contenu = data.get("content", "")
                result  = creer_google_doc(titre, contenu)
                await parler(result)
            elif action == "write_doc":
                contenu = data.get("content", "")
                result  = modifier_google_doc(contenu)
                await parler(result)
            elif action == "create_sheet":
                titre  = data.get("title", "Feuille JARVIS")
                result = creer_google_sheet(titre)
                await parler(result)
            elif action == "read_emails":
                if not os.path.exists("token.pickle"):
                    await parler("Un instant, je dois d'abord obtenir votre autorisation Google. Veuillez cliquer sur votre compte dans votre navigateur.")
                result = lire_emails()
                await parler(f"Voici vos derniers emails Aboubakar Ibrahim Siddick. {result}")
            elif action == "read_calendar" or action == "google_calendar_check":
                if not os.path.exists("token.pickle"):
                    await parler("Aboubakar Ibrahim Siddick, veuillez autoriser l'accès à votre agenda dans la fenêtre Google qui vient de s'ouvrir.")
                events = get_google_calendar_events(days=7)
                if not events:
                    await parler("Aboubakar Ibrahim Siddick, je n'ai pas pu accéder à votre agenda ou il est vide pour les 7 prochains jours.")
                else:
                    msg = "Voici votre programme pour les prochains jours : "
                    for ev in events:
                        start = ev['start'].get('dateTime', ev['start'].get('date'))
                        msg += f"- {ev.get('summary')} le {start}. "
                    await parler(msg)

            elif action == "memory_add":
                cle = data.get("cle")
                valeur = data.get("valeur")
                if cle and valeur:
                    if memory_add(cle, valeur):
                        await parler(f"C'est noté Aboubakar Ibrahim Siddick, je m'en souviendrai : {cle} est {valeur}.")
                    else: await parler("Je n'ai pas pu enregistrer cette information.")

            elif action == "memory_forget":
                cle = data.get("cle")
                if cle:
                    if memory_forget(cle):
                        await parler(f"C'est fait, j'ai effacé les informations concernant {cle} de ma mémoire.")
                    else: await parler(f"Je ne trouve aucune information correspondante à {cle} dans ma mémoire.")
            elif action == "meteo":
                ville = data.get("ville") or None
                await parler("Je consulte la meteo, un instant Aboubakar Ibrahim Siddick.")
                result = get_meteo_actuelle(ville)
                await parler(result)
            elif action == "alerte_meteo":
                ville = data.get("ville") or None
                result = get_alertes_meteo(ville)
                await parler(result)
            elif action == "recherche_web":
                query = data.get("query", "")
                await parler(f"Je lance une recherche sur internet pour {query}.")
                result = recherche_web_serpapi(query)
                await parler(result)
            elif action == "sport_resultats":
                equipe = data.get("equipe") or None
                ligue  = data.get("ligue")  or None
                print(f"[SPORT] Action sport_resultats pour {equipe or ligue}")
                await parler(f"Je cherche les informations pour {equipe or ligue}, un instant.")
                result = get_resultats_football(equipe=equipe, ligue=ligue)
                if "pas trouvé" in result or "Impossible" in result:
                    print(f"[SPORT] Echec recherche locale. Verification avec Grok...")
                    if grok_client:
                        res_grok = await demander_grok(f"Aboubakar Ibrahim Siddick veut savoir : {texte_utilisateur}. Je n'ai pas trouvé l'info dans ma base de données football, peux-tu chercher pour lui ?")
                        if res_grok: result = res_grok
                await parler(result)
            elif action == "sport_classement":
                ligue  = data.get("ligue", "Ligue 1")
                await parler(f"Je recupere le classement {ligue}.")
                result = get_classement_football(ligue=ligue)
                await parler(result)
            elif action == "sport_live":
                question = data.get("question", "derniers resultats sportifs 2026")
                await parler("Je recherche les derniers resultats en direct, un instant Aboubakar Ibrahim Siddick.")
                result = await get_resultats_sport_gemini(question)
                await parler(result)
            elif action == "voir_ecran":
                inst = data.get("instruction", "")
                res = await jarvis_vision_cliquer(inst)
                await parler(res)
            elif action == "whatsapp_appel":
                contact = data.get("contact", "Ma vie")
                await action_whatsapp_appel(contact)
            elif action == "vision_ecrire":
                inst = data.get("instruction", "")
                txt  = data.get("texte", "")
                res  = await jarvis_vision_ecrire(inst, txt)
                await parler(res)
            elif action == "youtube_play":
                query = data.get("query", "")
                await parler(f"Je cherche '{query}' sur YouTube pour vous.")
                url = chercher_youtube(query)
                if url:
                    ouvrir_url_pc(url)
                else:
                    await parler("Désolé, je n'ai pas trouvé de vidéo correspondante.")
            
            elif action == "check_diagnostics":
                diag = diagnostic_pc()
                if not diag:
                    await parler("Aboubakar Ibrahim Siddick, je n'ai pas pu accéder aux capteurs du système. Veuillez redémarrer Alice pour que je puisse charger les nouveaux modules de diagnostic.")
                else:
                    msg = f"Rapport de santé : CPU à {diag['cpu']}%, Mémoire à {diag['ram']}% et disque à {diag['disk']}%."
                    if diag["status"] == "ALERTE":
                        msg += f" Attention : {diag['details']}"
                    else:
                        msg += " Tout semble fonctionner parfaitement, Monsieur."
                    await parler(msg)
            
            elif action == "focus_mode":
                global FOCUS_MODE
                etat = data.get("etat", "on")
                FOCUS_MODE = (etat == "on")
                if FOCUS_MODE:
                    await parler("Mode Concentration activé. Je lance une ambiance productive et je tamise les lumières.")
                    # 1. Musique Zen via YouTube
                    url_zen = chercher_youtube("lofi hip hop radio focus study")
                    if url_zen: ouvrir_url_pc(url_zen)
                    # 2. Lumière Bleue via HA
                    try: ha_lumiere("light.salon", "on", rgb=[0, 0, 255], luminosite=50)
                    except: pass
                else:
                    await parler("Mode Concentration désactivé. Retour à la normale.")
                    try: ha_lumiere("light.salon", "on", rgb=[255, 255, 255], luminosite=255)
                    except: pass

            elif action == "get_stats":
                await parler(f"Votre niveau de productivité actuel est de {PROD_LEVEL}, avec un total de {PROD_SCORE} points d'expérience. Continuez comme ça !")

            elif action == "add_reminder":
                type_rem = data.get("type", "exit") # "exit" ou "enter"
                task = data.get("task", "")
                # On stocke ça dans la mémoire
                mem = charger_memoire()
                if "reminders" not in mem: mem["reminders"] = []
                mem["reminders"].append({"type": type_rem, "task": task, "date": str(datetime.now())})
                sauvegarder_memoire(mem)
                await parler(f"C'est noté, je vous rappellerai d' {task} quand vous { 'sortirez' if type_rem=='exit' else 'rentrerez' }.")

            # =====================================
            # MODULES AVANCÉS ALICE (16 Super-Pouvoirs)
            # =====================================
            elif action == "alice_generer_image":
                prompt_img = data.get("prompt", "")
                style_img = data.get("style", None)
                await parler(f"Je génère une image pour vous, Aboubakar Ibrahim Siddick. Un instant...")
                result = await alice_brain.generer_image(prompt_img, style_img)
                if result["success"]:
                    await parler(f"{result['message']}. L'image est prête dans le dossier alice_outputs.")
                    # Ouvrir l'image
                    try:
                        os.startfile(result["path"])
                    except: pass
                else:
                    await parler(result["message"])

            elif action == "alice_transcrire":
                fichier = data.get("fichier", "")
                await parler("Je lance la transcription audio, un instant...")
                result = await alice_brain.transcrire_audio(fichier)
                if result["success"]:
                    await parler(f"Voici la transcription : {result['text'][:500]}")
                else:
                    await parler(result["message"])

            elif action == "alice_supprimer_fond":
                fichier = data.get("fichier", "")
                await parler("Je supprime le fond de l'image...")
                result = await alice_brain.supprimer_fond(fichier)
                if result["success"]:
                    await parler(result["message"])
                    try:
                        os.startfile(result["path"])
                    except: pass
                else:
                    await parler(result["message"])

            elif action == "alice_humeur_audio":
                fichier = data.get("fichier", "")
                result = await alice_brain.detecter_humeur_audio(fichier)
                if result["success"]:
                    mood = result["mood"]
                    conf = result["confidence"]
                    await parler(f"Je détecte que votre ton est {mood} avec {int(conf*100)}% de confiance.")
                else:
                    await parler(result["message"])

            elif action == "alice_tts_custom":
                texte_tts = data.get("texte", "")
                await parler("Je prépare une synthèse vocale spéciale...")
                result = await alice_brain.synthese_vocale_custom(texte_tts)
                if result["success"]:
                    await parler(f"Audio généré : {result['path']}")
                    try:
                        os.startfile(result["path"])
                    except: pass
                else:
                    await parler(result["message"])

            elif action == "alice_vision_contextuelle":
                question_v = data.get("question", "Que vois-tu sur mon écran ?")
                await parler("Je regarde votre écran, un instant...")
                temp_ss = os.path.join(tempfile.gettempdir(), "alice_ctx_screen.png")
                try:
                    import pyautogui as pag_ctx
                    ss = pag_ctx.screenshot()
                    ss.save(temp_ss)

                    # Tentative 1 : Gemini Vision (analyse contextuelle riche)
                    result = await alice_brain.analyser_ecran_contextuel(temp_ss, question_v)
                    if result.get("success"):
                        await parler(result["analysis"][:800])
                    else:
                        raise Exception(result.get("message", "Gemini KO"))

                except Exception as e_ctx:
                    print(f"[VISION ALICE] Gemini KO ({e_ctx}). Fallback OCR local...")
                    # Tentative 2 : Fallback OCR Tesseract (description textuelle de l'écran)
                    try:
                        import pytesseract
                        from PIL import Image as PILImage
                        img_ocr = PILImage.open(temp_ss)
                        ocr_text = pytesseract.image_to_string(img_ocr, lang='fra+eng').strip()
                        if ocr_text and len(ocr_text) > 20:
                            reponse_ocr = (
                                f"Je ne peux pas analyser l'image en profondeur (Gemini indisponible), "
                                f"mais voici le texte que je lis sur votre écran : {ocr_text[:600]}"
                            )
                            await parler(reponse_ocr)
                        else:
                            await parler("Je vois votre écran mais le texte est illisible pour moi en ce moment. Gemini est indisponible et l'OCR n'a rien capté.")
                    except Exception as e_ocr:
                        await parler(f"Impossible de lire l'écran : Gemini et l'OCR sont tous les deux indisponibles ({e_ocr}).")
                finally:
                    try: os.remove(temp_ss)
                    except: pass

            elif action == "alice_analyser_photo":
                fichier = data.get("fichier", "")
                instruction_p = data.get("instruction", None)
                await parler("J'analyse la photo...")
                result = await alice_brain.analyser_photo(fichier, instruction_p)
                if result["success"]:
                    await parler(result["analysis"][:800])
                else:
                    await parler(result["message"])

            elif action == "alice_videosurveillance":
                instruction_v = data.get("instruction", "Détecte tout mouvement ou personne")
                await parler("Activation du mode vidéosurveillance...")
                result = await alice_brain.analyser_video_surveillance(instruction=instruction_v)
                if result["success"]:
                    await parler(result["analysis"][:800])
                else:
                    await parler(result["message"])

            elif action == "alice_codage":
                projet = data.get("projet", os.path.dirname(os.path.abspath(__file__)))
                instruction_c = data.get("instruction", "Analyse et propose des améliorations")
                await parler(f"Je lis le projet et j'analyse le code. Cela peut prendre un moment...")
                result = await alice_brain.assistant_codage(projet, instruction_c)
                if result["success"]:
                    # Sauvegarder l'analyse dans un fichier
                    analyse_path = os.path.join(alice_brain.output_dir, f"code_review_{int(time.time())}.md")
                    with open(analyse_path, "w", encoding="utf-8") as f_code:
                        f_code.write(result["code"])
                    await parler(f"{result['message']}. L'analyse complète est sauvegardée dans alice_outputs.")
                else:
                    await parler(result["message"])

            elif action == "alice_agent_web":
                url_web = data.get("url", "")
                objectif_web = data.get("objectif", "")
                await parler(f"Je navigue sur {url_web} pour vous...")
                result = await alice_brain.agent_web_action(url_web, objectif_web)
                if result["success"]:
                    await parler(result["result"][:800])
                else:
                    await parler(result["message"])

            elif action == "alice_rediger_email":
                dest = data.get("destinataire", "")
                sujet = data.get("sujet", "")
                contexte_e = data.get("contexte", "")
                ton_e = data.get("ton", "professionnel")
                await parler(f"Je rédige l'email pour {dest}...")
                result = await alice_brain.rediger_email(dest, sujet, contexte_e, ton=ton_e)
                if result["success"]:
                    # Sauvegarder le brouillon
                    email_path = os.path.join(alice_brain.output_dir, f"email_brouillon_{int(time.time())}.txt")
                    with open(email_path, "w", encoding="utf-8") as f_email:
                        f_email.write(result["email"])
                    await parler(f"Email rédigé et sauvegardé. Voulez-vous que je l'envoie ?")
                else:
                    await parler(result["message"])

            elif action == "alice_planifier_agenda":
                await parler("J'analyse votre agenda pour optimiser votre journée...")
                events = get_google_calendar_events(days=7)
                result = await alice_brain.planifier_agenda(events or [])
                if result["success"]:
                    await parler(result["plan"][:800])
                else:
                    await parler(result["message"])

            elif action == "alice_debug_code":
                code_d = data.get("code", "")
                lang_d = data.get("langage", "python")
                await parler(f"Je teste et corrige votre code {lang_d}...")
                result = await alice_brain.verifier_code_boucle(code_d, lang_d)
                if result["success"]:
                    await parler(f"Code corrigé après {result['iterations']} tentative(s). Sortie : {result.get('output', '')[:200]}")
                else:
                    await parler(f"{result['message']}")

            elif action == "alice_recherche_kb":
                query_kb = data.get("query", "")
                # Indexer si pas encore fait
                if not alice_brain._vector_store:
                    await alice_brain.indexer_knowledge_base(KNOWLEDGE_DIR)
                result = await alice_brain.recherche_semantique(query_kb)
                if result["success"]:
                    reponse_kb = f"J'ai trouvé {len(result['results'])} résultat(s) dans votre base de connaissances. "
                    for r in result["results"][:3]:
                        reponse_kb += f"Dans {os.path.basename(r['file'])} : {r['text'][:150]}... "
                    await parler(reponse_kb)
                else:
                    await parler(result["message"])

            elif action == "alice_analyser_youtube":
                url_yt = data.get("url", "")
                await parler(f"J'analyse la vidéo, un instant...")
                result = await alice_brain.analyser_video_youtube(url_yt)
                if result["success"]:
                    await parler(result["summary"][:800])
                else:
                    await parler(result["message"])

            elif action == "alice_productivite":
                result = await alice_brain.suivi_productivite()
                if result["success"]:
                    stats = result["stats"]
                    await parler(f"Score de productivité : {stats['score_productivite']}%. "
                                 f"Applications productives : {stats['apps_productives']}, "
                                 f"distractions : {stats['apps_distractions']}. "
                                 f"CPU à {stats['cpu_usage']}%, RAM à {stats['ram_usage']}%. "
                                 f"{stats['conseil']}")
                else:
                    await parler(result["message"])

            elif action == "alice_status":
                status = alice_brain.get_status()
                msg_status = (f"État des modules : HuggingFace {status['huggingface']}, "
                              f"Gemini {status['gemini']}. "
                              f"Quotas HF : {status['hf_quota']}. "
                              f"Quotas Gemini : {status['gemini_quota']}. "
                              f"Base de connaissances : {status['knowledge_base']}.")
                await parler(msg_status)

            # APRÈS CHAQUE ACTION RÉUSSIE : ON GAMIFIE
            leveled_up, score, level = update_productivity(10)
            if leveled_up:
                await parler(f" Félicitations ! Vous venez de passer au niveau {level} de productivité !")

        except Exception as e:
            print(f"[ACTION ERROR] Block failed: {block} | Error: {e}")
            if grok_client:
                print("[JARVIS] Bascule sur Grok suite a une erreur d'action...")
                res_grok = await demander_grok(f"Aboubakar Ibrahim Siddick m'a demandé : {texte_utilisateur}. J'ai tenté de lancer une action mais j'ai eu une erreur technique ({e}). Peux-tu prendre le relais et lui répondre élégamment ?")
                if res_grok: await parler(res_grok)
            continue

    # Si du texte reste après les commandes, on ne fait rien de plus car `parler` a déjà été appelé pour chaque action ou la réponse globale.
    # Réinitialiser le flag audio PC
    _skip_pc_audio = False

def nettoyer_commande(texte):
    t = texte.lower().strip()
    for variante in ["jarvis,", "jarvis"]:
        if t.startswith(variante):
            t = t[len(variante):].strip()
    return t

WAKE_WORD       = "alice"
SESSION_TIMEOUT = 30
STOP_PARLER      = False
is_listening     = False
is_speaking      = False
jarvis_actif     = False
jarvis_vision    = None
dernier_message  = 0
interface_deja_connectee = False

def ecouter():
    global is_listening, jarvis_actif, dernier_message, STOP_PARLER, is_speaking

    r   = sr.Recognizer()
    mic = sr.Microphone()

    r.pause_threshold        = 0.6
    r.non_speaking_duration  = 0.5
    r.energy_threshold       = 300
    r.dynamic_energy_threshold = True

    with mic as source:
        r.adjust_for_ambient_noise(source, duration=1)

    print("[JARVIS] Microphone pret. En attente de 'Jarvis' ou session active...")

    while True:
        try:
            # GESTION DU TIMEOUT DE SESSION
            if jarvis_actif and (time.time() - dernier_message > SESSION_TIMEOUT):
                print("[JARVIS] Timeout session. Retour en veille.")
                jarvis_actif = False

            with mic as source:
                is_listening = True
                loop_ws = asyncio.new_event_loop()
                state = "active" if jarvis_actif else "listening"
                loop_ws.run_until_complete(send_web_state(state))
                loop_ws.close()
                
                audio = r.listen(source, timeout=2, phrase_time_limit=10)
                
                is_listening = False
                loop_ws = asyncio.new_event_loop()
                loop_ws.run_until_complete(send_web_state("idle"))
                loop_ws.close()

            texte = r.recognize_google(audio, language=CURRENT_LANG).lower().strip()
            print(f"[ENTENDU] {texte}")

            # GESTION INTERRUPTION DURANT LA PAROLE
            if is_speaking and ("tais-toi" in texte or "silence" in texte or "tais toi" in texte):
                STOP_PARLER = True
                continue

            # MOTS-CLÉS DE SOMMEIL
            SLEEP_WORDS = ["merci", "ce sera tout", "repos", "au revoir", "silence", "tais-toi", "tais toi"]
            if any(word in texte for word in SLEEP_WORDS):
                if jarvis_actif:
                    jarvis_actif = False
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(parler("A votre service Aboubakar Ibrahim Siddick. Je me mets en veille."))
                    loop.close()
                continue

            if WAKE_WORD in texte or jarvis_actif:
                if WAKE_WORD in texte:
                    print("[JARVIS] Mot-clé détecté.")
                    jarvis_actif = True
                
                dernier_message = time.time()
                commande = nettoyer_commande(texte)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if commande:
                    action_pc = executer_action_pc(commande)
                    if action_pc:
                        loop.run_until_complete(parler(action_pc))
                    else:
                        loop.run_until_complete(traiter_reponse_ia(commande))
                else:
                    if WAKE_WORD in texte: # "Jarvis" tout seul
                        loop.run_until_complete(parler("Oui Aboubakar Ibrahim Siddick, je vous écoute."))
                
                dernier_message = time.time() # Reset le timeout APRES avoir parlé
                loop.close()
            else:
                pass

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            if "getaddrinfo failed" in str(e) or "connection" in str(e).lower():
                print(f"[JARVIS] Erreur réseau (DNS/Connexion) : {e}. Vérifiez votre accès internet.")
            else:
                print(f"Erreur écoute : {e}")
            time.sleep(1)

def monitor_claps():
    try:
        import audioop
        p = pyaudio.PyAudio()
        # On ouvre le flux
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
        print("[CLAP] Détection des applaudissements activée.")
        
        print("[CLAP] Détection des doubles applaudissements activée.")
        
        last_clap_time = 0
        
        while True:
            try:
                data = stream.read(1024, exception_on_overflow=False)
                rms  = audioop.rms(data, 2)
                
                # ON IGNORE LE CLAP UNIQUEMENT SI LE MODE IRON MAN EST ÉTEINT OU SI JARVIS PARLE
                if not MODE_IRON_MAN or is_speaking or is_thinking:
                    last_clap_time = 0
                    continue

                if rms > CLAP_THRESHOLD:
                    current_time = time.time()
                    diff = current_time - last_clap_time
                    
                    if 0.1 < diff < 0.8:
                        global VIDEO_LANCEE
                        print(f"\n[CLAP] !!! DOUBLE CLAP DÉTECTÉ !!!")
                        entity_id = PIECES_LUMIERES.get("salon", "light.salon")
                        
                        # On vérifie l'état actuel
                        etat_actuel = ha_get_etat(entity_id)
                        
                        if etat_actuel != "on":
                            # ON ALLUME
                            print(f"[CLAP] Action : ALLUMER")
                            ha_lumiere(entity_id, "on")
                            
                            if not VIDEO_LANCEE:
                                print(f"[CLAP] Lancement initial de la vidéo...")
                                webbrowser.open("https://www.youtube.com/watch?v=KU5V5WZVcVE")
                                VIDEO_LANCEE = True
                                def seq():
                                    time.sleep(5)
                                    pyautogui.press('f')
                                threading.Thread(target=seq, daemon=True).start()
                            else:
                                print(f"[CLAP] Reprise de la vidéo (Play)...")
                                pyautogui.press('k')
                        else:
                            # ON ÉTEINT
                            print(f"[CLAP] Action : ÉTEINDRE")
                            ha_lumiere(entity_id, "off")
                            if VIDEO_LANCEE:
                                print(f"[CLAP] Mise en pause de la vidéo...")
                                pyautogui.press('k')
                            
                        # Gros debounce après une action réussie
                        time.sleep(3.0)
                        last_clap_time = 0 # Reset
                    else:
                        # C'est peut-être le premier clap
                        last_clap_time = current_time
            except Exception as e:
                # Si erreur de lecture (ex: micro débranché), on attend et on continue
                time.sleep(0.5)
                continue

    except Exception as e:
        print(f"[CLAP] Erreur fatale détection claps : {e}")

def liberer_port(port):
    """Force la libération d'un port sur Windows."""
    try:
        cmd = f'netstat -ano | findstr :{port}'
        res = subprocess.check_output(cmd, shell=True).decode()
        for line in res.strip().split('\n'):
            parts = line.split()
            if len(parts) > 4:
                pid = parts[-1]
                if pid != "0":
                    print(f"[SYSTEM] Fermeture du processus {pid} occupant le port {port}...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def start_ia():
    threading.Thread(target=monitor_claps, daemon=True).start()
    
    def monitor_system():
        global DERNIER_DIAG
        while True:
            time.sleep(60)
            diag = diagnostic_pc()
            if diag and diag["status"] == "ALERTE":
                if time.time() - DERNIER_DIAG > DIAG_INTERVAL:
                    print(f"[MONITOR] ALERTE IA : {diag['details']}")
                    DERNIER_DIAG = time.time()
                    # Alice parlera au prochain tour ou via un signal visuel
    
    def monitor_calendar():
        """Vérifie l'agenda toutes les heures pour les rappels."""
        print("[CALENDRIER] Monitoring actif.")
        while True:
            try:
                events = get_google_calendar_events(days=1)
                if events:
                    # Logique simple : on cherche des mots-clés comme anniversaire
                    for ev in events:
                        summary = ev.get('summary', '').lower()
                        if "anniversaire" in summary or "rendez-vous" in summary:
                            print(f"[CALENDRIER] Rappel détecté : {summary}")
                            # On pourrait injecter un message à Alice ici, 
                            # ou simplement logger pour l'instant.
                time.sleep(3600)
            except Exception as e:
                print(f"[CALENDRIER] Erreur loop : {e}")
                time.sleep(300)

    threading.Thread(target=monitor_calendar, daemon=True).start()
    threading.Thread(target=monitor_system, daemon=True).start()
    
    liberer_port(8765) # On s'assure que le port est libre
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ==========================================
# CONFIGURATION TLS/WSS & SÉCURITÉ DE TRANSPORT (C-01)
# ==========================================
TRUSTED_PROXIES = set(os.environ.get("ALICE_TRUSTED_PROXIES", "127.0.0.1,::1").split(","))

def get_ssl_context(purpose="server") -> Optional[ssl.SSLContext]:
    """
    Configure et charge un contexte SSL/TLS serveur pour HTTPS (port 8080) et WSS (port 8765) (C-01).
    Prend en charge les chemins configurés par variables d'environnement ou le dossier certs/.
    """
    cert_path = os.environ.get("ALICE_SSL_CERT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs", "cert.pem")
    key_path = os.environ.get("ALICE_SSL_KEY") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs", "key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            # Durcissement cryptographique : TLSv1.2 minimum requis
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            return context
        except Exception as e:
            print(f"[SECURITY ERROR] Échec de chargement des certificats TLS : {e}")
            return None
    return None

def get_transport_security_mode() -> str:
    """Détermine le mode de sécurité de transport actif de l'application (C-01)."""
    is_prod = (
        os.environ.get("JARVIS_ENV", "").lower() == "production"
        or os.environ.get("ALICE_ENV", "").lower() == "production"
        or os.environ.get("ALICE_REQUIRE_TLS", "0") == "1"
    )
    ssl_ctx = get_ssl_context()
    if ssl_ctx is not None:
        return "TLS_ENFORCED_PRODUCTION" if is_prod else "TLS_ACTIVE_DEVELOPMENT"
    elif is_prod:
        return "FAIL_CLOSED_TLS_REQUIRED"
    else:
        return "DEVELOPMENT_PLAINTEXT_DEGRADED"

def get_trusted_client_ip(handler, client_address) -> str:
    """
    Extrait l'adresse IP cliente réelle en ne faisant confiance aux en-têtes
    X-Forwarded-For QUE si la connexion immédiate provient de TRUSTED_PROXIES (C-01).
    """
    immediate_ip = client_address[0] if client_address else "unknown"
    if immediate_ip in TRUSTED_PROXIES and hasattr(handler, "headers"):
        forwarded = handler.headers.get("X-Forwarded-For")
        if forwarded:
            first_ip = forwarded.split(",")[0].strip()
            try:
                ipaddress.ip_address(first_ip)
                return first_ip
            except ValueError:
                pass
    return immediate_ip

    async def start_ws():
        liberer_port(8765)
        sec_mode = get_transport_security_mode()

        # Comportement Fail-Closed en production si TLS requis et manquant (C-01 / Section 3.4)
        if sec_mode == "FAIL_CLOSED_TLS_REQUIRED":
            print("[SECURITY FATAL] Mode production exige TLS/WSS mais aucun certificat valide n'est configuré. Démarrage WebSocket interrompu par sécurité (C-01).")
            return

        ssl_ctx = get_ssl_context()
        proto = "wss" if ssl_ctx else "ws"
        print(f"[WEB] Serveur WebSocket ({proto}://) démarré sur port 8765 (Mode: {sec_mode})")
        try:
            async with websockets.serve(ws_handler, "0.0.0.0", 8765, ssl=ssl_ctx, max_size=15 * 1024 * 1024):
                await asyncio.Future()
        except Exception as e:
            print(f"[WEB] Erreur critique démarrage serveur WebSocket : {e}")

    threading.Thread(target=lambda: asyncio.run(start_ws()), daemon=True).start()

    loop.run_until_complete(parler("Bonjour, Aboubakar Ibrahim Siddick"))
    loop.close()
    ecouter()

# ==========================================
# LANCEMENT — MODE CONSOLE + FRONTEND WEB
# ==========================================
# Ursina desactive : l'interface est maintenant le frontend Three.js
# dans le dossier frontend/ (npm run dev -> http://localhost:5173)
# Le WebSocket est deja demarre par start_ia() sur ws://localhost:8765

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def start_mobile_http_server():
    """Serveur HTTP/HTTPS pour servir l'interface mobile sur le port 8080 avec appairage sécurisé (C-01 / SEC-04)."""
    import http.server
    mobile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile")
    if not os.path.exists(mobile_dir):
        print("[MOBILE] Dossier mobile/ introuvable, serveur non demarre.")
        return

    sec_mode = get_transport_security_mode()
    # Comportement Fail-Closed en production si TLS requis et manquant (C-01 / Section 3.4)
    if sec_mode == "FAIL_CLOSED_TLS_REQUIRED":
        print("[SECURITY FATAL] Mode production exige HTTPS mais aucun certificat TLS valide n'a été fourni. Serveur mobile HTTP désactivé par sécurité (C-01).")
        return

    # Génération du code d'appairage initial à usage unique (SEC-04)
    PAIRING_MANAGER.generate_pairing_code()

    class MobileHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=mobile_dir, **kwargs)

        def _set_cors_headers(self):
            # Interdiction stricte du wildcard '*' (SEC-04)
            origin = self.headers.get("Origin")
            if origin and WS_SESSION_MANAGER.is_origin_allowed(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

        def do_OPTIONS(self):
            self.send_response(204)
            self._set_cors_headers()
            self.end_headers()

        def do_GET(self):
            # Ancien endpoint /api/auth/token supprimé et désactivé (SEC-04)
            if self.path == "/api/auth/token":
                self.send_response(410)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Endpoint obsolète et supprimé pour des raisons de sécurité. Utilisez /api/pair."}).encode("utf-8"))
                return

            if self.path == "/api/pair/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(PAIRING_MANAGER.get_status()).encode("utf-8"))
                return

            super().do_GET()

        def do_POST(self):
            client_ip = get_trusted_client_ip(self, self.client_address)

            # 1. Endpoint d'appairage avec validation de PIN à usage unique (SEC-04)
            if self.path == "/api/pair":
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                    data = json.loads(body) if body else {}
                    code = str(data.get("code", "")).strip()

                    if PAIRING_MANAGER.consume_pairing_code(code):
                        new_session_id = secrets.token_hex(16)
                        new_token = secrets.token_urlsafe(32)
                        WS_SESSION_MANAGER.register_session(
                            session_id=new_session_id,
                            token=new_token,
                            client_type="mobile",
                            client_ip=client_ip
                        )
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        resp = {"success": True, "session_id": new_session_id, "token": new_token}
                        self.wfile.write(json.dumps(resp).encode("utf-8"))
                        print(f"[PAIRING] Appairage réussi pour client mobile {client_ip} (Session {new_session_id})")
                    else:
                        self.send_response(401)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        resp = {"success": False, "error": "Code d'appairage invalide ou expiré"}
                        self.wfile.write(json.dumps(resp).encode("utf-8"))
                        print(f"[PAIRING] Tentative d'appairage rejetée pour client {client_ip}")
                except Exception as e:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": f"Requête invalide : {e}"}).encode("utf-8"))
                return

            # 2. Endpoint de révocation de session
            if self.path == "/api/revoke_session":
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                    data = json.loads(body) if body else {}
                    s_id = data.get("session_id", "")
                    tok = data.get("token", "")

                    if WS_SESSION_MANAGER.revoke_session(s_id, tok):
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "message": "Session révoquée avec succès"}).encode("utf-8"))
                    else:
                        self.send_response(401)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": "Session introuvable ou jeton invalide"}).encode("utf-8"))
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                return

            super().do_POST()

        def log_message(self, format, *args):
            pass  # Silencieux

    server = http.server.HTTPServer(("0.0.0.0", 8080), MobileHandler)
    ssl_ctx = get_ssl_context()
    if ssl_ctx:
        server.socket = ssl_ctx.wrap_socket(server.socket, server_side=True)
        print(f"[MOBILE] Serveur HTTPS sécurisé démarré sur https://0.0.0.0:8080 (Mode: {sec_mode})")
    else:
        print(f"[SECURITY WARNING] Serveur HTTP démarré en clair sur http://0.0.0.0:8080 (Mode: {sec_mode}). NE PAS EXPOSER SUR UN RÉSEAU NON DE CONFIANCE.")
    server.serve_forever()
async def demander_ia_stream(texte):
    """Générateur de texte en streaming (Gemini)."""
    global is_thinking, historique
    is_thinking = True
    await send_web_state("thinking")
    compilation = ""
    success = False
    try:
        # --- 1. TENTATIVE AVEC GROQ (PRIORITÉ UTILISATEUR) ---
        if groq_client:
            print("[CERVEAU] Utilisation de Groq (Qwen)...")
            try:
                messages = [{"role": "system", "content": construire_system_prompt()}]
                for h in historique:
                    role = "assistant" if h.role == "model" else h.role
                    messages.append({"role": role, "content": h.parts[0].text})
                messages.append({"role": "user", "content": texte})

                response = groq_client.chat.completions.create(
                    model="qwen3.6-27b",
                    messages=messages,
                    stream=True
                )
                for chunk in response:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        compilation += delta
                        yield delta
                
                historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                historique.append(types.Content(role="model", parts=[types.Part(text=compilation)]))
                success = True
            except Exception as e:
                print(f"[GROQ ERROR] {e}")

        # --- 2. FALLBACK VERS GEMINI SI GROQ ÉCHOUE ---
        if not success:
            for model_name in MODELS_LIST:
                try:
                    stream = await client.aio.models.generate_content_stream(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=construire_system_prompt(),
                            temperature=0.7,
                        ),
                        contents=historique + [types.Content(role="user", parts=[types.Part(text=texte)])]
                    )
                    async for chunk in stream:
                        if chunk.text:
                            compilation += chunk.text
                            yield chunk.text
                    
                    historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                    historique.append(types.Content(role="model", parts=[types.Part(text=compilation)]))
                    success = True
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(f"[RECOGNITION] Quota dépassé pour {model_name}. Tentative suivante...")
                        continue
                    else:
                        print(f"[STREAMING ERROR] {model_name}: {e}")
                        continue
        
        if not success:
            yield "Désolé Aboubakar Ibrahim Siddick, je rencontre un problème avec tous mes cerveaux IA (Groq et Gemini)."
    finally:
        is_thinking = False
        await send_web_state("idle")

async def demander_ia_vision_stream(texte, img_b64):
    """Version streaming (encapsulée dans un générateur) de la vision."""
    global is_thinking
    is_thinking = True
    await send_web_state("thinking")
    try:
        # Gemini Vision Call
        response = await client.aio.models.generate_content(
            model=CHOSEN_MODEL,
            contents=[texte, Image.open(io.BytesIO(base64.b64decode(img_b64)))]
        )
        yield response.text
    except Exception as e:
        if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
            print("[VISION] Quota dépassé. Utilisation du contexte OCR local...")
            yield "Désolé, mes serveurs de vision sont saturés. Cependant, je peux 'lire' votre écran localement. Laissez-moi analyser le texte disponible..."
            if groq_client:
                # Fallback Groq en injectant une note sur l'absence d'image
                try:
                    response = groq_client.chat.completions.create(
                        model="qwen-2.5-32b",
                        messages=[{"role": "user", "content": texte + " (Note: Vision indisponible, utilise les données textuelles OCR de mon écran déjà présentes dans ta mémoire pour répondre)."}]
                    )
                    yield "\n" + response.choices[0].message.content
                except:
                    yield f"\nErreur quota : {e}"
        else:
            yield f"Erreur vision : {e}"
    finally:
        is_thinking = False
        await send_web_state("idle")

def main():
    print()
    if not check_internet():
        print("!" * 60)
        print("   ATTENTION : AUCUNE CONNEXION INTERNET DETECTEE")
        print("   Certaines fonctions (Gemini, Groq, Edge-TTS) seront limitées.")
        print("   Assurez-vous qu'Ollama est lancé pour le mode hors-ligne.")
        print("!" * 60)
        print()
    print("=" * 60)
    print("   J.A.R.V.I.S — Mode Console + Interface Web")
    print("=" * 60)
    print()
    print("  Backend   : actif (terminal)")
    print("  WebSocket : ws://localhost:8765  (LAN: ws://192.168.1.23:8765)")
    print("  Frontend  : ouvrir http://localhost:5173")
    print("  Mobile    : ouvrir http://192.168.1.23:8080 sur votre tel/tablette")
    print()
    print("  Commandes vocales actives.")
    print("  Dites 'Jarvis' pour activer la session.")
    print("=" * 60)
    print()

    # Lancer le serveur Frontend
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    frontend_process = None
    if os.path.exists(frontend_dir):
        print("[JARVIS] Lancement automatique de l'interface Web (Vite)...")
        frontend_process = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir, shell=True)
        time.sleep(2.5)  # Laisser le temps a Vite de demarrer

    # Ouvrir le navigateur vers le frontend
    try:
        webbrowser.open("http://localhost:5173")
    except Exception:
        pass

    # Lancer le serveur HTTP mobile dans un thread
    threading.Thread(target=start_mobile_http_server, daemon=True).start()

    # Activation de la VISION OCR (Nouveau)
    global jarvis_vision
    try:
        import vision_ocr
        jarvis_vision = vision_ocr.JarvisVision(scan_interval=3.0)
        jarvis_vision.start()
        print("[JARVIS] Vision OCR activee en arriere-plan (mss + tesseract).")
    except Exception as e:
        print(f"[JARVIS] Erreur activation Vision : {e}")

    # Lancer le backend IA dans un thread
    threading.Thread(target=start_ia, daemon=True).start()

    # Garder le processus en vie
    try:
        while True:
            time.sleep(1)
            # On ne s'arrête plus automatiquement pour rester "en parallèle" même si Web déconnecté
    except KeyboardInterrupt:
        print("\n[JARVIS] Arret du systeme demande manuellement.")
        
    if frontend_process:
        print("[JARVIS] Arret du serveur Web...")
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
