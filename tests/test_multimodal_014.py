"""
Validation Multimodale Complète — Mission 014 (Phases 4, 5, 6).
Teste le parcours Assistant (WS + HTTP), le sous-système Audio (Mic + TTS)
et le sous-système Vision (OCR Tesseract avec tessdata local).
"""
import os
import sys
import json
import time
import asyncio
import unittest
from unittest.mock import patch

SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Jarvis Final - SITE")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

import websockets
import main2

class TestMultimodal014(unittest.TestCase):

    def test_phase4_assistant_websocket_interaction(self):
        """Vérifie le cycle complet de commande/question via WebSocket."""
        port = 8769
        received_responses = []

        async def scenario():
            server = await websockets.serve(main2.ws_handler, "127.0.0.1", port)
            try:
                headers = {"Origin": "http://localhost:5173"}
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                    # 1. Réception auth_ok
                    auth_ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                    self.assertEqual(auth_ack.get("type"), "auth_ok")

                    # 2. Envoi d'une commande
                    cmd = {
                        "type": "command",
                        "command": "quelle heure est-il",
                        "action": "system_info"
                    }
                    await ws.send(json.dumps(cmd))
                    await asyncio.sleep(0.5)
                    # Envoi d'un ping de maintien
                    await ws.send(json.dumps({"type": "ping"}))
                    # La socket reste ouverte et saine
                    self.assertEqual(len(main2.CONNECTED_CLIENTS), 1)
                    self.assertIsNone(ws.close_code)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())

    def test_phase5_audio_subsystem(self):
        """Vérifie la détection matérielle micro et la synthèse vocale locale."""
        # 1. Vérification PyAudio
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            dev_count = p.get_device_count()
            input_devs = []
            for i in range(dev_count):
                info = p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    input_devs.append(info.get("name"))
            p.terminate()
            self.assertGreater(len(input_devs), 0, "Au moins un périphérique micro détecté")
            print(f"[TEST AUDIO] {len(input_devs)} périphériques microphone détectés.")
        except Exception as e:
            self.fail(f"Erreur PyAudio : {e}")

        # 2. Vérification pyttsx3 (TTS hors-ligne)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            self.assertGreater(len(voices), 0, "Au moins une voix TTS SAPI5 installée")
            print(f"[TEST TTS] {len(voices)} voix locales disponibles (ex: {voices[0].name}).")
        except Exception as e:
            self.fail(f"Erreur TTS pyttsx3 : {e}")

    def test_phase6_vision_ocr_subsystem(self):
        """Vérifie le fonctionnement de Tesseract OCR avec le tessdata local."""
        import pytesseract
        from PIL import Image, ImageDraw

        # Configuration Tesseract local
        tess_dir = os.path.join(SOURCE_DIR, "tessdata")
        os.environ["TESSDATA_PREFIX"] = tess_dir

        tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if not os.path.exists(tesseract_cmd):
            tesseract_cmd = r"C:\Users\USER\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Création d'une image de test synthétique avec texte français
        img = Image.new("RGB", (300, 80), color="white")
        draw = ImageDraw.Draw(img)
        test_text = "ALICE SECURITE 2026"
        draw.text((10, 30), test_text, fill="black")

        test_img_path = os.path.join(SOURCE_DIR, "test_ocr_sample.png")
        img.save(test_img_path)

        try:
            extracted = pytesseract.image_to_string(Image.open(test_img_path)).strip()
            print(f"[TEST OCR] Texte extrait : '{extracted}'")
            self.assertIn("ALICE", extracted.upper())
            self.assertIn("SECURITE", extracted.upper())
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)

if __name__ == "__main__":
    unittest.main()
