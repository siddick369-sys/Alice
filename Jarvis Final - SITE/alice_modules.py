# ============================================================
# ALICE MODULES — 16 Super-Pouvoirs via Gemini + HuggingFace
# Mode GRATUIT avec gestion stricte des quotas et fallbacks
# ============================================================

import os
import io
import re
import ast
import json
import time
import base64
import asyncio
import threading
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Imports conditionnels (graceful degradation)
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import psutil
except ImportError:
    psutil = None

# ============================================================
# RATE LIMITER — Protection anti-quota pour APIs gratuites
# ============================================================
class RateLimiter:
    """Limiteur de débit simple pour les APIs gratuites."""
    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = []
        self._lock = threading.Lock()

    def can_call(self) -> bool:
        with self._lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            return len(self.calls) < self.max_calls

    def record_call(self):
        with self._lock:
            self.calls.append(time.time())

    def wait_time(self) -> float:
        with self._lock:
            if not self.calls:
                return 0
            oldest = min(self.calls)
            return max(0, self.period - (time.time() - oldest))


# ============================================================
# CLASSE PRINCIPALE — AliceModules
# ============================================================
class AliceModules:
    """
    Regroupe les 16 super-pouvoirs d'Alice.
    Conçu pour le mode GRATUIT : chaque appel API est rate-limité
    et dispose de fallbacks en cas de quota épuisé.
    """

    def __init__(self, hf_token: str = None, gemini_client=None, gemini_models: list = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.gemini_client = gemini_client
        self.gemini_models = gemini_models or ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]

        # Client HuggingFace
        self.hf_client = None
        if self.hf_token and InferenceClient:
            try:
                self.hf_client = InferenceClient(
                    provider="hf-inference",
                    api_key=self.hf_token,
                )
                print("[ALICE MODULES] Client HuggingFace initialisé.")
            except Exception as e:
                print(f"[ALICE MODULES] Erreur init HuggingFace : {e}")

        # Rate limiters (quotas gratuits)
        # HuggingFace free : ~30 req/heure environ
        self.hf_limiter = RateLimiter(max_calls=25, period_seconds=3600)
        # Gemini free : ~15 RPM pour flash, ~2 RPM pour pro
        self.gemini_limiter = RateLimiter(max_calls=12, period_seconds=60)

        # Dossiers de travail
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice_outputs")
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # Base vectorielle en mémoire (feature 14)
        self._vector_store = {}
        self._embeddings_cache = {}

        # Suivi productivité (feature 16)
        self._window_tracker = {}
        self._tracking_active = False

        print("[ALICE MODULES] 16 modules chargés et prêts.")

    # ========================================================
    # 1. GÉNÉRATION D'IMAGES (FLUX / SDXL via HuggingFace)
    # ========================================================
    async def generer_image(self, prompt: str, style: str = None) -> dict:
        """
        Génère une image via FLUX.1-schnell ou SDXL (fallback).
        Retourne {"success": bool, "path": str, "message": str}
        """
        if not self.hf_client:
            return {"success": False, "path": None, "message": "Client HuggingFace non disponible. Vérifiez HF_TOKEN."}

        if not self.hf_limiter.can_call():
            wait = self.hf_limiter.wait_time()
            return {"success": False, "path": None, "message": f"Quota HuggingFace atteint. Réessayez dans {int(wait//60)} minutes."}

        # Enrichissement du prompt si style spécifié
        full_prompt = prompt
        if style:
            full_prompt = f"{prompt}, {style} style, high quality, detailed"

        timestamp = int(time.time())
        filename = f"alice_image_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)

        models = [
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-xl-base-1.0",
        ]

        for model_name in models:
            try:
                print(f"[IMAGE] Génération avec {model_name}...")
                self.hf_limiter.record_call()
                image = await asyncio.to_thread(
                    self.hf_client.text_to_image,
                    prompt=full_prompt,
                    model=model_name,
                )
                image.save(filepath)
                print(f"[IMAGE] Sauvegardée : {filepath}")
                return {
                    "success": True,
                    "path": filepath,
                    "message": f"Image générée avec {model_name.split('/')[-1]} et sauvegardée dans {filepath}"
                }
            except Exception as e:
                print(f"[IMAGE] Échec {model_name} : {e}")
                continue

        return {"success": False, "path": None, "message": "Tous les modèles de génération d'images ont échoué."}

    # ========================================================
    # 2. TRANSCRIPTION WHISPER PRO (HuggingFace)
    # ========================================================
    async def transcrire_audio(self, audio_path: str) -> dict:
        """
        Transcription audio via Whisper large-v3 de HuggingFace.
        Retourne {"success": bool, "text": str, "message": str}
        """
        if not self.hf_client:
            return {"success": False, "text": "", "message": "Client HuggingFace non disponible."}

        if not os.path.exists(audio_path):
            return {"success": False, "text": "", "message": f"Fichier audio introuvable : {audio_path}"}

        if not self.hf_limiter.can_call():
            return {"success": False, "text": "", "message": "Quota HuggingFace atteint."}

        models = [
            "openai/whisper-large-v3-turbo",
            "openai/whisper-large-v3",
            "openai/whisper-small",
        ]

        for model_name in models:
            try:
                print(f"[WHISPER] Transcription avec {model_name}...")
                self.hf_limiter.record_call()
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()

                result = await asyncio.to_thread(
                    self.hf_client.automatic_speech_recognition,
                    audio=audio_bytes,
                    model=model_name,
                )
                texte = result.text if hasattr(result, 'text') else str(result)
                print(f"[WHISPER] Transcription réussie ({len(texte)} chars)")
                return {
                    "success": True,
                    "text": texte,
                    "message": f"Transcription réussie via {model_name.split('/')[-1]}"
                }
            except Exception as e:
                print(f"[WHISPER] Échec {model_name} : {e}")
                continue

        return {"success": False, "text": "", "message": "Échec de la transcription avec tous les modèles Whisper."}

    # ========================================================
    # 3. SUPPRESSION DE FOND (RemBG via HuggingFace)
    # ========================================================
    async def supprimer_fond(self, image_path: str) -> dict:
        """
        Supprime le fond d'une image via BRIA RemBG.
        Retourne {"success": bool, "path": str, "message": str}
        """
        if not self.hf_client or not Image:
            return {"success": False, "path": None, "message": "Client HF ou PIL non disponible."}

        if not os.path.exists(image_path):
            return {"success": False, "path": None, "message": f"Image introuvable : {image_path}"}

        if not self.hf_limiter.can_call():
            return {"success": False, "path": None, "message": "Quota HuggingFace atteint."}

        timestamp = int(time.time())
        out_filename = f"alice_nobg_{timestamp}.png"
        out_path = os.path.join(self.output_dir, out_filename)

        models = [
            "briaai/RMBG-1.4",
            "Xenova/rmbg-1.4",
        ]

        for model_name in models:
            try:
                print(f"[REMBG] Suppression de fond avec {model_name}...")
                self.hf_limiter.record_call()

                img = Image.open(image_path)
                # Convertir en bytes
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                result = await asyncio.to_thread(
                    self.hf_client.image_segmentation,
                    image=buf.getvalue(),
                    model=model_name,
                )

                # Le résultat est une liste de masques, on prend le premier
                if result and hasattr(result[0], 'mask'):
                    mask = result[0].mask
                    if isinstance(mask, Image.Image):
                        # Appliquer le masque comme alpha
                        img_rgba = img.convert("RGBA")
                        mask_resized = mask.resize(img_rgba.size)
                        img_rgba.putalpha(mask_resized.convert("L"))
                        img_rgba.save(out_path)
                    else:
                        # Sauvegarder directement si c'est déjà l'image finale
                        mask.save(out_path)
                elif isinstance(result, Image.Image):
                    result.save(out_path)
                else:
                    # Fallback : sauvegarder brut
                    with open(out_path, "wb") as f:
                        f.write(result if isinstance(result, bytes) else str(result).encode())

                return {
                    "success": True,
                    "path": out_path,
                    "message": f"Fond supprimé. Image sauvegardée : {out_path}"
                }
            except Exception as e:
                print(f"[REMBG] Échec {model_name} : {e}")
                continue

        return {"success": False, "path": None, "message": "Échec de la suppression de fond."}

    # ========================================================
    # 4. AUDIO MOOD DETECTION (Analyse émotionnelle)
    # ========================================================
    async def detecter_humeur_audio(self, audio_path: str) -> dict:
        """
        Analyse le ton émotionnel d'un enregistrement audio.
        Retourne {"success": bool, "mood": str, "confidence": float, "message": str}
        """
        if not self.hf_client:
            return {"success": False, "mood": "neutre", "confidence": 0, "message": "Client HF non disponible."}

        if not os.path.exists(audio_path):
            return {"success": False, "mood": "neutre", "confidence": 0, "message": "Fichier audio introuvable."}

        if not self.hf_limiter.can_call():
            return {"success": False, "mood": "neutre", "confidence": 0, "message": "Quota HF atteint."}

        try:
            print("[MOOD] Analyse émotionnelle du ton de voix...")
            self.hf_limiter.record_call()

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            result = await asyncio.to_thread(
                self.hf_client.audio_classification,
                audio=audio_bytes,
                model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
            )

            if result and len(result) > 0:
                top = result[0]
                label = top.label if hasattr(top, 'label') else str(top.get('label', 'neutre'))
                score = top.score if hasattr(top, 'score') else float(top.get('score', 0))

                # Mapping anglais -> français
                mood_map = {
                    "angry": "en colère", "happy": "joyeux", "sad": "triste",
                    "neutral": "neutre", "fear": "inquiet", "disgust": "dégoûté",
                    "surprise": "surpris", "calm": "calme"
                }
                mood_fr = mood_map.get(label.lower(), label)

                return {
                    "success": True,
                    "mood": mood_fr,
                    "confidence": round(score, 2),
                    "message": f"Humeur détectée : {mood_fr} (confiance : {round(score*100)}%)"
                }
        except Exception as e:
            print(f"[MOOD] Erreur : {e}")

        return {"success": False, "mood": "neutre", "confidence": 0, "message": "Impossible d'analyser l'humeur."}

    # ========================================================
    # 5. SYNTHÈSE VOCALE CUSTOM (TTS via HuggingFace)
    # ========================================================
    async def synthese_vocale_custom(self, texte: str, voix: str = "feminine") -> dict:
        """
        Synthèse vocale via des modèles HuggingFace (Bark / MMS-TTS).
        Retourne {"success": bool, "path": str, "message": str}
        """
        if not self.hf_client:
            return {"success": False, "path": None, "message": "Client HF non disponible."}

        if not self.hf_limiter.can_call():
            return {"success": False, "path": None, "message": "Quota HF atteint."}

        timestamp = int(time.time())
        out_path = os.path.join(self.output_dir, f"alice_tts_{timestamp}.wav")

        models = [
            "facebook/mms-tts-fra",  # TTS français
            "espnet/kan-bayashi_ljspeech_vits",
        ]

        for model_name in models:
            try:
                print(f"[TTS CUSTOM] Synthèse avec {model_name}...")
                self.hf_limiter.record_call()

                audio = await asyncio.to_thread(
                    self.hf_client.text_to_speech,
                    text=texte,
                    model=model_name,
                )

                # Audio peut être bytes ou un objet avec .audio
                audio_bytes = audio if isinstance(audio, bytes) else getattr(audio, 'audio', audio)
                if isinstance(audio_bytes, bytes):
                    with open(out_path, "wb") as f:
                        f.write(audio_bytes)
                    return {
                        "success": True,
                        "path": out_path,
                        "message": f"Audio généré via {model_name.split('/')[-1]} : {out_path}"
                    }
            except Exception as e:
                print(f"[TTS CUSTOM] Échec {model_name} : {e}")
                continue

        return {"success": False, "path": None, "message": "Échec de la synthèse vocale custom."}

    # ========================================================
    # 6. ANALYSE VISUELLE CONTEXTUELLE (Gemini Multimodal)
    # ========================================================
    async def analyser_ecran_contextuel(self, image_path_or_b64: str, question: str = None) -> dict:
        """
        Analyse visuelle complète d'un écran (au-delà de l'OCR).
        Comprend les icônes, graphiques, dispositions d'interface.
        """
        if not self.gemini_client or not types:
            return {"success": False, "analysis": "", "message": "Client Gemini non disponible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "analysis": "", "message": "Quota Gemini atteint. Patientez 1 minute."}

        try:
            # Charger l'image
            if os.path.exists(str(image_path_or_b64)):
                img = Image.open(image_path_or_b64)
            else:
                # C'est du base64
                img_bytes = base64.b64decode(image_path_or_b64)
                img = Image.open(io.BytesIO(img_bytes))

            prompt = (
                "Tu es ALICE, une IA de vision avancée. Analyse cette capture d'écran EN PROFONDEUR.\n"
                "NE fais PAS un simple OCR. Décris :\n"
                "1. L'application ou le site web affiché (nom, type)\n"
                "2. Les éléments d'interface visibles (boutons, menus, icônes)\n"
                "3. L'état actuel (erreurs, notifications, progression)\n"
                "4. Ce que l'utilisateur semble faire\n"
                "5. Des suggestions d'actions pertinentes\n"
            )
            if question:
                prompt += f"\nQuestion spécifique de l'utilisateur : {question}\n"
            prompt += "\nRéponds en français, de façon claire et concise."

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt, img]
                    )
                    return {
                        "success": True,
                        "analysis": response.text,
                        "message": f"Analyse visuelle complète via {model}"
                    }
                except Exception as e:
                    print(f"[VISION CTX] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[VISION CTX] Erreur : {e}")

        return {"success": False, "analysis": "", "message": "Échec de l'analyse visuelle."}

    # ========================================================
    # 7. LECTURE DE PHOTOS (Identification d'objets Gemini)
    # ========================================================
    async def analyser_photo(self, image_path: str, instruction: str = None) -> dict:
        """
        Analyse une photo pour identifier objets, pièces cassées, animaux, etc.
        """
        if not self.gemini_client or not Image:
            return {"success": False, "analysis": "", "message": "Client Gemini ou PIL non disponible."}

        if not os.path.exists(image_path):
            return {"success": False, "analysis": "", "message": f"Image introuvable : {image_path}"}

        if not self.gemini_limiter.can_call():
            return {"success": False, "analysis": "", "message": "Quota Gemini atteint."}

        try:
            img = Image.open(image_path)

            prompt = (
                "Tu es ALICE, experte en identification visuelle.\n"
                "Analyse cette photo et fournis :\n"
                "1. Identification précise de tous les objets visibles\n"
                "2. État des objets (neuf, usé, cassé, etc.)\n"
                "3. Marque et modèle si identifiable\n"
                "4. Suggestions (réparation, remplacement, prix estimé)\n"
            )
            if instruction:
                prompt += f"\nInstruction spécifique : {instruction}\n"
            prompt += "\nRéponds en français."

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt, img]
                    )
                    return {
                        "success": True,
                        "analysis": response.text,
                        "message": f"Photo analysée avec {model}"
                    }
                except Exception as e:
                    print(f"[PHOTO] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[PHOTO] Erreur : {e}")

        return {"success": False, "analysis": "", "message": "Échec de l'analyse photo."}

    # ========================================================
    # 8. VIDÉOSURVEILLANCE INTELLIGENTE (Analyse de frames)
    # ========================================================
    async def analyser_video_surveillance(self, frames_b64: list = None, instruction: str = "Détecte tout mouvement ou personne suspecte") -> dict:
        """
        Analyse des frames vidéo pour la détection d'objets/personnes.
        Accepte une liste d'images base64 (frames extraites).
        """
        if not self.gemini_client:
            return {"success": False, "analysis": "", "message": "Client Gemini non disponible."}

        if not frames_b64 or len(frames_b64) == 0:
            # Fallback : capture d'écran locale
            try:
                import pyautogui
                screenshot = pyautogui.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format="PNG")
                buf.seek(0)
                frames_b64 = [base64.b64encode(buf.getvalue()).decode()]
            except:
                return {"success": False, "analysis": "", "message": "Aucune frame fournie et capture impossible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "analysis": "", "message": "Quota Gemini atteint."}

        try:
            # Prendre la première frame
            img_bytes = base64.b64decode(frames_b64[0])
            img = Image.open(io.BytesIO(img_bytes))

            prompt = (
                f"Tu es ALICE en mode vidéosurveillance.\n"
                f"Instruction : {instruction}\n"
                f"Analyse cette image et signale :\n"
                "1. Présence de personnes (nombre, position, comportement)\n"
                "2. Véhicules ou animaux détectés\n"
                "3. Objets inhabituels ou suspects\n"
                "4. Niveau de risque (faible/moyen/élevé)\n"
                "Réponds en français, sois concis."
            )

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt, img]
                    )
                    return {
                        "success": True,
                        "analysis": response.text,
                        "message": "Analyse vidéosurveillance terminée."
                    }
                except Exception as e:
                    print(f"[VIDEO] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[VIDEO] Erreur : {e}")

        return {"success": False, "analysis": "", "message": "Échec de l'analyse vidéo."}

    # ========================================================
    # 9. ASSISTANT DE CODAGE FULL-CONTEXT (Gemini 1.5 Pro)
    # ========================================================
    async def assistant_codage(self, chemin_projet: str, instruction: str) -> dict:
        """
        Lit le projet complet et propose un refactor ou une solution.
        Utilise la fenêtre de contexte géante de Gemini 1.5 Pro.
        """
        if not self.gemini_client:
            return {"success": False, "code": "", "message": "Client Gemini non disponible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "code": "", "message": "Quota Gemini atteint."}

        try:
            # Collecter les fichiers du projet
            code_extensions = [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml", ".md", ".txt"]
            fichiers_contenu = []
            total_chars = 0
            max_chars = 500_000  # Limite pour ne pas exploser le contexte gratuit

            projet = Path(chemin_projet)
            if not projet.exists():
                return {"success": False, "code": "", "message": f"Projet introuvable : {chemin_projet}"}

            for f in sorted(projet.rglob("*")):
                if f.is_file() and f.suffix.lower() in code_extensions:
                    if any(skip in str(f) for skip in ["node_modules", "venv", ".git", "__pycache__", "dist"]):
                        continue
                    try:
                        contenu = f.read_text(encoding="utf-8", errors="ignore")
                        if total_chars + len(contenu) > max_chars:
                            break
                        fichiers_contenu.append(f"--- {f.relative_to(projet)} ---\n{contenu}")
                        total_chars += len(contenu)
                    except:
                        continue

            if not fichiers_contenu:
                return {"success": False, "code": "", "message": "Aucun fichier de code trouvé dans le projet."}

            code_complet = "\n\n".join(fichiers_contenu)

            prompt = (
                "Tu es ALICE, une ingénieure logicielle de classe mondiale.\n"
                f"Voici le code COMPLET d'un projet ({len(fichiers_contenu)} fichiers, {total_chars} caractères) :\n\n"
                f"{code_complet}\n\n"
                f"INSTRUCTION DE L'UTILISATEUR : {instruction}\n\n"
                "Analyse le code, identifie les problèmes, et propose une solution complète.\n"
                "Fournis le code corrigé si nécessaire. Réponds en français."
            )

            self.gemini_limiter.record_call()
            # Priorité à gemini-2.5-pro pour le grand contexte
            models_prio = ["gemini-2.5-pro"] + [m for m in self.gemini_models if m != "gemini-2.5-pro"]

            for model in models_prio:
                try:
                    response = await asyncio.wait_for(
                        self.gemini_client.aio.models.generate_content(
                            model=model,
                            contents=[prompt]
                        ),
                        timeout=60.0
                    )
                    return {
                        "success": True,
                        "code": response.text,
                        "message": f"Analyse de {len(fichiers_contenu)} fichiers via {model}"
                    }
                except Exception as e:
                    print(f"[CODE] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[CODE] Erreur : {e}")

        return {"success": False, "code": "", "message": "Échec de l'assistant de codage."}

    # ========================================================
    # 10. AGENT WEB AUTONOME (Navigation visuelle Gemini)
    # ========================================================
    async def agent_web_action(self, url: str, objectif: str) -> dict:
        """
        Navigue sur un site web de manière autonome en analysant
        visuellement les pages et en simulant des clics.
        """
        # Validation d'URL et prévention SSRF (LOT C)
        try:
            import alice_web_guard
            safe, reason = alice_web_guard.WEB_GUARD.is_safe_url(url)
            if not safe:
                return {
                    "success": False,
                    "result": "",
                    "message": f"Accès refusé par Alice Web Guard : {reason}",
                    "security_block": True
                }
        except ImportError:
            pass

        if not self.gemini_client:
            return {"success": False, "result": "", "message": "Client Gemini non disponible."}

        try:
            import webbrowser
            import pyautogui

            # Étape 1 : Ouvrir l'URL
            webbrowser.open(url)
            await asyncio.sleep(5)  # Attendre le chargement

            # Étape 2 : Capturer l'écran
            screenshot = pyautogui.screenshot()
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            buf.seek(0)
            img = Image.open(buf)

            if not self.gemini_limiter.can_call():
                return {"success": False, "result": "", "message": "Quota Gemini atteint."}

            # Étape 3 : Demander à Gemini quoi faire
            prompt = (
                "Tu es ALICE, un agent web autonome.\n"
                f"J'ai ouvert le site : {url}\n"
                f"Objectif : {objectif}\n\n"
                "Voici une capture de la page. Analyse-la et dis-moi :\n"
                "1. Ce que tu vois sur la page\n"
                "2. Les étapes à suivre pour atteindre l'objectif\n"
                "3. Sur quel élément cliquer en premier (avec coordonnées approximatives)\n"
                "Réponds en JSON : {\"description\": \"...\", \"action\": \"clic/scroll/saisie\", \"cible\": \"...\", \"box\": [ymin, xmin, ymax, xmax]}\n"
            )

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt, img]
                    )
                    return {
                        "success": True,
                        "result": response.text,
                        "message": f"Page analysée. Objectif : {objectif}"
                    }
                except Exception as e:
                    print(f"[WEB AGENT] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[WEB AGENT] Erreur : {e}")

        return {"success": False, "result": "", "message": "Échec de l'agent web."}

    # ========================================================
    # 11. RÉDACTION D'EMAILS INTELLIGENTE (Gmail + Gemini)
    # ========================================================
    async def rediger_email(self, destinataire: str, sujet: str, contexte: str,
                            anciens_emails: str = None, ton: str = "professionnel") -> dict:
        """
        Rédige un email en imitant le style de l'utilisateur.
        """
        if not self.gemini_client:
            return {"success": False, "email": "", "message": "Client Gemini non disponible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "email": "", "message": "Quota Gemini atteint."}

        try:
            prompt = (
                "Tu es ALICE, l'assistante de Aboubakar Ibrahim Siddick.\n"
                f"Rédige un email {ton} pour : {destinataire}\n"
                f"Sujet : {sujet}\n"
                f"Contexte : {contexte}\n"
            )
            if anciens_emails:
                prompt += f"\nVoici des exemples d'emails précédents pour imiter le style :\n{anciens_emails}\n"

            prompt += (
                "\nRègles :\n"
                "- Utilise un ton naturel et français impeccable\n"
                "- Pas de formules creuses ou trop génériques\n"
                "- L'email doit être prêt à envoyer tel quel\n"
                "- Commence par la formule de politesse et termine par la signature\n"
                "- Signe avec : Aboubakar Ibrahim Siddick\n"
            )

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt]
                    )
                    return {
                        "success": True,
                        "email": response.text,
                        "message": "Email rédigé avec succès."
                    }
                except Exception as e:
                    continue

        except Exception as e:
            print(f"[EMAIL] Erreur : {e}")

        return {"success": False, "email": "", "message": "Échec de la rédaction de l'email."}

    # ========================================================
    # 12. PLANIFICATEUR D'AGENDA PRÉDICTIF
    # ========================================================
    async def planifier_agenda(self, evenements: list, habitudes: dict = None) -> dict:
        """
        Analyse le calendrier et les habitudes pour proposer
        des créneaux de travail optimaux.
        """
        if not self.gemini_client:
            return {"success": False, "plan": "", "message": "Client Gemini non disponible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "plan": "", "message": "Quota Gemini atteint."}

        try:
            # Construire le contexte
            events_text = ""
            if evenements:
                for ev in evenements:
                    start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date', '?'))
                    summary = ev.get('summary', 'Sans titre')
                    events_text += f"- {start} : {summary}\n"
            else:
                events_text = "Aucun événement prévu."

            habits_text = ""
            if habitudes:
                for k, v in habitudes.items():
                    habits_text += f"- {k} : {v}\n"

            prompt = (
                "Tu es ALICE, planificatrice intelligente.\n"
                f"Voici l'agenda actuel de Aboubakar Ibrahim Siddick :\n{events_text}\n"
            )
            if habits_text:
                prompt += f"Ses habitudes connues :\n{habits_text}\n"

            prompt += (
                "\nPropose :\n"
                "1. Les meilleurs créneaux de travail profond (Deep Work)\n"
                "2. Des pauses stratégiques (technique Pomodoro)\n"
                "3. Le moment idéal pour les tâches créatives vs administratives\n"
                "4. Des alertes de conflit ou surcharge\n"
                "Réponds en français, de façon structurée."
            )

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt]
                    )
                    return {
                        "success": True,
                        "plan": response.text,
                        "message": "Planning prédictif généré."
                    }
                except Exception as e:
                    continue

        except Exception as e:
            print(f"[AGENDA] Erreur : {e}")

        return {"success": False, "plan": "", "message": "Échec de la planification."}

    # ========================================================
    # 13. VÉRIFICATION DE CODE STATIQUE ET SÉCURISÉE (SEC-01)
    # Exécution dynamique sur hôte désactivée par mesure de sécurité
    # ========================================================
    async def verifier_code_boucle(self, code: str, langage: str = "python", max_iterations: int = 3) -> dict:
        """
        Analyse statiquement le code (syntaxe AST, détection de patterns dangereux),
        et demande à l'IA de le corriger en boucle sans JAMAIS l'exécuter sur le système hôte.
        L'exécution arbitraire est strictement neutralisée (SEC-01).
        """
        code_actuel = code
        historique_erreurs = []
        dangers_detectes = []

        # Mots-clés / modules critiques à interdire en mode non-sandboxé
        DANGEROUS_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "pty", "commands", "winreg"}
        DANGEROUS_BUILTINS = {"exec", "eval", "__import__", "compile", "breakpoint", "open", "input"}

        for iteration in range(max_iterations):
            erreurs_iteration = []
            dangers_iteration = []

            # Analyse statique selon le langage
            if langage == "python":
                try:
                    tree = ast.parse(code_actuel)
                    # Inspection AST pour détecter les appels et imports dangereux
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name.split('.')[0] in DANGEROUS_MODULES:
                                    dangers_iteration.append(f"Import interdit détecté : {alias.name}")
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.module.split('.')[0] in DANGEROUS_MODULES:
                                dangers_iteration.append(f"Import interdit depuis module : {node.module}")
                        elif isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
                                dangers_iteration.append(f"Appel interdit à builtin dangereux : {node.func.id}()")
                            elif isinstance(node.func, ast.Attribute):
                                if node.func.attr in ("system", "popen", "spawn", "exec", "eval"):
                                    dangers_iteration.append(f"Appel de méthode système potentiellement dangereuse : .{node.func.attr}()")
                except SyntaxError as syn_err:
                    erreurs_iteration.append(f"SyntaxError: {syn_err.msg} (ligne {syn_err.lineno})")
                except Exception as parse_err:
                    erreurs_iteration.append(f"ParseError: {parse_err}")
            elif langage == "javascript":
                js_dangerous = ["eval(", "Function(", "child_process", "require('fs')", "require(\"fs\")", "process.exit"]
                for pat in js_dangerous:
                    if pat in code_actuel:
                        dangers_iteration.append(f"Pattern JavaScript non sécurisé : {pat}")
                if code_actuel.count("{") != code_actuel.count("}"):
                    erreurs_iteration.append("Erreur de syntaxe : accolades asymétriques")
                if code_actuel.count("(") != code_actuel.count(")"):
                    erreurs_iteration.append("Erreur de syntaxe : parenthèses asymétriques")

            if not erreurs_iteration and not dangers_iteration:
                return {
                    "success": True,
                    "code_final": code_actuel,
                    "iterations": iteration + 1,
                    "message": (
                        f"Code validé avec succès par analyse statique et vérification de sécurité "
                        f"après {iteration + 1} itération(s). Aucune exécution arbitraire sur le système hôte (SEC-01)."
                    ),
                    "execution_status": "DISABLED_FOR_SECURITY",
                    "safety_status": "SECURE_STATIC_VERIFIED",
                    "details": []
                }

            rapport_problemes = []
            if erreurs_iteration:
                rapport_problemes.extend(erreurs_iteration)
            if dangers_iteration:
                rapport_problemes.extend([f"Alerte sécurité : {d}" for d in dangers_iteration])

            derniers_problemes = " ; ".join(rapport_problemes)
            historique_erreurs.append(derniers_problemes)
            dangers_detectes.extend(dangers_iteration)

            if not self.gemini_client:
                return {
                    "success": False,
                    "code_final": code_actuel,
                    "iterations": iteration + 1,
                    "message": f"Échec de validation statique : {derniers_problemes}. Client Gemini indisponible pour auto-correction.",
                    "execution_status": "DISABLED_FOR_SECURITY",
                    "safety_status": "REJECTED_UNSAFE_OR_INVALID",
                    "details": rapport_problemes
                }

            if not self.gemini_limiter.can_call():
                return {
                    "success": False,
                    "code_final": code_actuel,
                    "iterations": iteration + 1,
                    "message": f"Quota Gemini atteint pendant la correction statique. Problèmes : {derniers_problemes}",
                    "execution_status": "DISABLED_FOR_SECURITY",
                    "safety_status": "REJECTED_UNSAFE_OR_INVALID",
                    "details": rapport_problemes
                }

            prompt = (
                f"Tu es ALICE, analyste et correctrice experte en sécurité de code ({langage}).\n"
                f"Le code suivant a échoué aux vérifications statiques et de sécurité :\n```{langage}\n{code_actuel}\n```\n"
                f"Problèmes détectés :\n```\n{derniers_problemes}\n```\n"
                f"Consignes absolues :\n"
                f"1. Corrige la syntaxe et assure-toi que le code est propre et valide.\n"
                f"2. Supprime TOUT appel dangereux, import système (os, sys, subprocess), ou mécanisme d'évaluation dynamique (eval, exec).\n"
                f"3. Renvoie UNIQUEMENT le code corrigé sans aucune explication, encadré par des balises ```{langage}.\n"
            )

            self.gemini_limiter.record_call()
            correction_reussie = False
            for model in self.gemini_models:
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=model,
                        contents=[prompt]
                    )
                    match = re.search(r'```(?:\w+)?\n(.*?)```', response.text, re.DOTALL)
                    if match:
                        code_actuel = match.group(1).strip()
                    else:
                        code_actuel = response.text.strip()
                    correction_reussie = True
                    break
                except Exception:
                    continue

            if not correction_reussie:
                break

        return {
            "success": False,
            "code_final": code_actuel,
            "iterations": max_iterations,
            "message": (
                f"Échec de la validation statique après {max_iterations} tentative(s). "
                f"Derniers problèmes : {historique_erreurs[-1] if historique_erreurs else 'inconnus'}"
            ),
            "execution_status": "DISABLED_FOR_SECURITY",
            "safety_status": "REJECTED_UNSAFE_OR_INVALID",
            "details": historique_erreurs
        }

    # ========================================================
    # 14. BASE DE CONNAISSANCES VECTORIELLE (Recherche sémantique)
    # ========================================================
    async def indexer_knowledge_base(self, knowledge_dir: str) -> dict:
        """
        Indexe tous les documents du dossier knowledge/ pour la recherche sémantique
        en utilisant le moteur local AliceRAGEngine (TXT, MD, PDF, XLSX).
        """
        try:
            import alice_rag
            res = alice_rag.RAG_ENGINE.index_knowledge_directory()
            self._vector_store = {
                c["chunk_id"]: {
                    "file": c["source_file"],
                    "text": c["text"],
                    "chunk_id": c.get("chunk_id", ""),
                    "citation": c.get("provenance", "")
                }
                for c in alice_rag.RAG_ENGINE.chunks
            }
            return {
                "success": True,
                "count": len(self._vector_store),
                "message": f"{len(self._vector_store)} chunks indexés depuis {knowledge_dir} (moteur AliceRAGEngine)."
            }
        except Exception as e:
            print(f"[KB] Erreur indexation AliceRAGEngine : {e}")

        # Fallback local autonome
        count = 0
        kb_path = Path(knowledge_dir)
        if not kb_path.exists():
            return {"success": False, "count": 0, "message": f"Dossier inexistant : {knowledge_dir}"}

        text_extensions = [".txt", ".pdf", ".md", ".py", ".js", ".html"]

        for f in kb_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in text_extensions:
                try:
                    contenu = f.read_text(encoding="utf-8", errors="ignore")
                    if not contenu.strip():
                        continue

                    # Découper en chunks de 500 chars
                    chunks = [contenu[i:i+500] for i in range(0, len(contenu), 450)]

                    for i, chunk in enumerate(chunks[:10]):  # Max 10 chunks par fichier
                        key = f"{f.name}_chunk_{i}"
                        self._vector_store[key] = {
                            "file": str(f),
                            "text": chunk,
                            "chunk_id": i
                        }
                        count += 1
                except Exception as e:
                    print(f"[KB] Erreur indexation {f.name} : {e}")

        return {"success": True, "count": count, "message": f"{count} chunks indexés depuis {knowledge_dir}"}

    async def recherche_semantique(self, query: str, top_k: int = 3) -> dict:
        """
        Recherche sémantique dans la base de connaissances.
        Priorité au moteur AliceRAGEngine avec scoring TF-IDF / N-grammes et citations.
        """
        try:
            import alice_rag
            results = alice_rag.RAG_ENGINE.search(query, top_k=top_k)
            if results:
                return {
                    "success": True,
                    "results": [
                        {
                            "file": r["source_file"],
                            "text": r["text"][:300],
                            "score": r["score"],
                            "citation": r["citation"]
                        }
                        for r in results
                    ],
                    "message": f"{len(results)} résultat(s) trouvé(s) pour '{query}'"
                }
        except Exception as e:
            print(f"[RAG] Fallback recherche semantique : {e}")

        if not self._vector_store:
            return {"success": False, "results": [], "message": "Base de connaissances vide. Lancez d'abord l'indexation."}

        # Recherche par mots-clés (fallback si pas d'embeddings disponibles)
        query_words = set(query.lower().split())
        scored = []

        for key, doc in self._vector_store.items():
            text = doc["text"].lower()
            # Score basé sur le nombre de mots de la requête présents dans le chunk
            score = sum(1 for w in query_words if w in text)
            # Bonus pour les mots adjacents
            for i in range(len(query.split()) - 1):
                bigram = f"{query.split()[i]} {query.split()[i+1]}".lower()
                if bigram in text:
                    score += 2
            if score > 0:
                scored.append((score, key, doc))

        scored.sort(reverse=True, key=lambda x: x[0])
        results = []
        for score, key, doc in scored[:top_k]:
            results.append({
                "file": doc["file"],
                "text": doc["text"][:300],
                "score": score,
                "chunk_id": doc.get("chunk_id", 0)
            })

        if results:
            return {
                "success": True,
                "results": results,
                "message": f"{len(results)} résultat(s) trouvé(s) pour '{query}'"
            }
        return {"success": False, "results": [], "message": f"Aucun résultat pour '{query}'"}

    # ========================================================
    # 15. ANALYSE DE VIDÉOS YOUTUBE (Résumé via Gemini)
    # ========================================================
    async def analyser_video_youtube(self, url_ou_sujet: str) -> dict:
        """
        Analyse/résume une vidéo YouTube en utilisant Gemini.
        Gemini peut lire les vidéos YouTube directement.
        """
        if not self.gemini_client:
            return {"success": False, "summary": "", "message": "Client Gemini non disponible."}

        if not self.gemini_limiter.can_call():
            return {"success": False, "summary": "", "message": "Quota Gemini atteint."}

        try:
            # Si c'est une URL YouTube, on l'envoie directement à Gemini
            is_youtube_url = "youtube.com" in url_ou_sujet or "youtu.be" in url_ou_sujet

            prompt = (
                "Tu es ALICE, analyste de contenu vidéo.\n"
            )

            if is_youtube_url:
                prompt += (
                    f"Voici une vidéo YouTube : {url_ou_sujet}\n"
                    "Fournis un résumé complet de cette vidéo :\n"
                )
            else:
                prompt += (
                    f"L'utilisateur veut un résumé du contenu vidéo sur le sujet : {url_ou_sujet}\n"
                    "Utilise ta recherche Google pour trouver et analyser les meilleures vidéos sur ce sujet.\n"
                )

            prompt += (
                "1. Résumé en 5-10 points clés\n"
                "2. Les informations les plus importantes\n"
                "3. Les recommandations ou conclusions de la vidéo\n"
                "4. Un verdict en une phrase\n"
                "Réponds en français."
            )

            self.gemini_limiter.record_call()
            for model in self.gemini_models:
                try:
                    config = None
                    if types:
                        config = types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                        )
                    response = await asyncio.wait_for(
                        self.gemini_client.aio.models.generate_content(
                            model=model,
                            contents=[prompt],
                            config=config,
                        ),
                        timeout=30.0
                    )
                    return {
                        "success": True,
                        "summary": response.text,
                        "message": "Analyse vidéo terminée."
                    }
                except Exception as e:
                    print(f"[YT ANALYSE] Échec {model} : {e}")
                    continue

        except Exception as e:
            print(f"[YT ANALYSE] Erreur : {e}")

        return {"success": False, "summary": "", "message": "Échec de l'analyse vidéo."}

    # ========================================================
    # 16. CALCULATEUR DE PRODUCTIVITÉ AVANCÉ
    # ========================================================
    async def suivi_productivite(self) -> dict:
        """
        Effectue un snapshot des fenêtres actives et calcule
        un score de productivité basé sur les applications utilisées.
        """
        if not psutil:
            return {"success": False, "stats": {}, "message": "Module psutil non disponible."}

        try:
            # Applications productives vs distractions
            apps_productives = {
                "code", "vscode", "visual studio", "pycharm", "intellij",
                "word", "excel", "powerpoint", "notion", "obsidian",
                "terminal", "cmd", "powershell", "bash",
                "figma", "photoshop", "illustrator", "blender",
                "chrome - docs", "chrome - github", "chrome - stack",
            }
            apps_distractions = {
                "youtube", "netflix", "twitch", "discord", "twitter",
                "tiktok", "instagram", "facebook", "reddit",
                "steam", "epic games", "league of legends",
            }

            # Scanner les processus actifs
            processes = {}
            for proc in psutil.process_iter(['name', 'cpu_percent']):
                try:
                    name = proc.info['name'].lower()
                    if name not in processes:
                        processes[name] = proc.info.get('cpu_percent', 0) or 0
                except:
                    continue

            productif_count = 0
            distraction_count = 0
            active_apps = []

            for pname in processes:
                for p in apps_productives:
                    if p in pname:
                        productif_count += 1
                        active_apps.append(f"✅ {pname}")
                        break
                for d in apps_distractions:
                    if d in pname:
                        distraction_count += 1
                        active_apps.append(f"❌ {pname}")
                        break

            total = productif_count + distraction_count
            score = (productif_count / max(total, 1)) * 100

            # CPU et RAM
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent

            stats = {
                "score_productivite": round(score),
                "apps_productives": productif_count,
                "apps_distractions": distraction_count,
                "cpu_usage": cpu,
                "ram_usage": ram,
                "active_apps": active_apps[:10],
                "conseil": self._conseil_productivite(score, cpu, ram)
            }

            return {
                "success": True,
                "stats": stats,
                "message": f"Score de productivité : {round(score)}%. {stats['conseil']}"
            }

        except Exception as e:
            print(f"[PRODUCTIVITE] Erreur : {e}")
            return {"success": False, "stats": {}, "message": f"Erreur suivi : {e}"}

    def _conseil_productivite(self, score: float, cpu: float, ram: float) -> str:
        """Génère un conseil personnalisé basé sur les stats."""
        if score >= 80:
            conseil = "Excellente concentration ! Continuez sur cette lancée."
        elif score >= 50:
            conseil = "Pas mal, mais quelques distractions détectées. Activez le Mode Focus ?"
        elif score >= 20:
            conseil = "Beaucoup de distractions actives. Fermez les applications non essentielles."
        else:
            conseil = "Hmm, on dirait que c'est jour de repos. Pas de jugement !"

        if cpu > 80:
            conseil += " Attention, le processeur est très sollicité."
        if ram > 85:
            conseil += " La mémoire est presque pleine, fermez des onglets."

        return conseil

    # ========================================================
    # UTILITAIRE : Status de tous les modules
    # ========================================================
    def get_status(self) -> dict:
        """Retourne l'état de tous les modules Alice."""
        return {
            "huggingface": "[OK] Actif" if self.hf_client else "[X] Inactif (pas de HF_TOKEN)",
            "gemini": "[OK] Actif" if self.gemini_client else "[X] Inactif",
            "hf_quota": f"{self.hf_limiter.max_calls - len([t for t in self.hf_limiter.calls if time.time() - t < self.hf_limiter.period])}/{self.hf_limiter.max_calls} appels restants",
            "gemini_quota": f"{self.gemini_limiter.max_calls - len([t for t in self.gemini_limiter.calls if time.time() - t < self.gemini_limiter.period])}/{self.gemini_limiter.max_calls} appels restants",
            "knowledge_base": f"{len(self._vector_store)} chunks indexés",
            "output_dir": self.output_dir,
            "modules": [
                "1. Génération d'images (FLUX/SDXL)",
                "2. Transcription Whisper Pro",
                "3. Suppression de fond (RemBG)",
                "4. Détection d'humeur audio",
                "5. Synthèse vocale custom",
                "6. Analyse visuelle contextuelle",
                "7. Lecture de photos",
                "8. Vidéosurveillance intelligente",
                "9. Assistant de codage full-context",
                "10. Agent web autonome",
                "11. Rédaction d'emails intelligente",
                "12. Planificateur d'agenda prédictif",
                "13. Vérification de code en boucle",
                "14. Base de connaissances vectorielle",
                "15. Analyse de vidéos YouTube",
                "16. Calculateur de productivité avancé",
            ]
        }
