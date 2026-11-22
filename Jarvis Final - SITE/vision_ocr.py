import os
import time
import threading
import cv2
import numpy as np
import mss
import pytesseract
import re
from typing import Optional, List

# CONFIGURATION TESSERACT WINDOWS
# Téléchargement : https://github.com/UB-Mannheim/tesseract/wiki
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class JarvisVision:
    """
    Module de Vision OCR Temps Réel pour l'assistant Jarvis.
    Permet de capturer et d'analyser l'écran en continu de manière non bloquante.
    """
    
    def __init__(self, use_easyocr: bool = False, scan_interval: float = 3.0):
        self.scan_interval = scan_interval
        self.is_running = False
        self.last_text = ""
        self.monitor = mss.mss()
        self.easy_reader = None
        
        if use_easyocr:
            self._init_easyocr()

        # Thread de surveillance
        self._thread = None

    def _init_easyocr(self):
        """Initialisation paresseuse d'EasyOCR car le chargement est lourd."""
        try:
            import easyocr
            print("[VISION] Chargement d'EasyOCR (IA)...")
            self.easy_reader = easyocr.Reader(['fr', 'en'])
            print("[VISION] EasyOCR prêt.")
        except ImportError:
            print("[VISION] EasyOCR non installé. Utilisation de Tesseract uniquement.")

    def preprocess_image(self, img_np):
        """
        Optimise l'image pour l'OCR : niveaux de gris, binarisation et suppression du bruit.
        """
        # Conversion en niveaux de gris
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
        
        # Redimensionnement (x2) pour mieux lire les petits textes/code
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Flou léger pour réduire le bruit
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Binarisation adaptative (Otsu)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh

    def capture_screen(self, region: Optional[dict] = None):
        """
        Capture l'écran ou une zone spécifique via mss.
        """
        # Si aucune région n'est spécifiée, capture l'écran principal
        sct_img = self.monitor.grab(region or self.monitor.monitors[1])
        return np.array(sct_img)

    def extract_text_tesseract(self, img):
        """Extraction via Tesseract (Rapide)."""
        try:
            # Vérification des langues disponibles pour éviter l'erreur "unable to load languages"
            langs = "fra+eng"
            try:
                avail_langs = pytesseract.get_languages()
                if 'fra' not in avail_langs:
                    langs = "eng"
            except:
                langs = "eng"
                
            return pytesseract.image_to_string(img, lang=langs, config='--psm 3')
        except Exception as e:
            return f"Erreur Tesseract : {e}"

    def extract_text_easyocr(self, img_np):
        """Extraction via EasyOCR (Précis, IA)."""
        if not self.easy_reader:
            return self.extract_text_tesseract(img_np)
        
        results = self.easy_reader.readtext(img_np, detail=0)
        return "\n".join(results)

    def clean_text(self, text: str) -> str:
        """
        Nettoie et formate le texte extrait pour le contexte de l'IA.
        """
        # Supprime les caractères non imprimables bizarres
        text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")
        
        # Regroupe les sauts de ligne multiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Supprime les espaces en fin de ligne
        text = "\n".join(line.strip() for line in text.split("\n"))
        
        return text.strip()

    def _vision_loop(self):
        """Boucle d'analyse en arrière-plan."""
        print(f"[VISION] Surveillance active (Intervalle: {self.scan_interval}s)")
        while self.is_running:
            try:
                # 1. Capture
                raw_img = self.capture_screen()
                
                # 2. Prétraitement
                processed_img = self.preprocess_image(raw_img)
                
                # 3. OCR (choix par défaut Tesseract pour la vitesse)
                if self.easy_reader:
                    raw_text = self.extract_text_easyocr(raw_img) # EasyOCR prefere l'original ou preprocess specifique
                else:
                    raw_text = self.extract_text_tesseract(processed_img)
                
                # 4. Nettoyage
                self.last_text = self.clean_text(raw_text)
                
                # Optionnel : Log si texte trouvé
                # if len(self.last_text) > 10:
                #     print(f"[VISION] {len(self.last_text)} caractères extraits.")
                
            except Exception as e:
                print(f"[VISION ERROR] {e}")
            
            time.sleep(self.scan_interval)

    def start(self):
        """Lance la surveillance en arrière-plan."""
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._vision_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Arrête la surveillance."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def get_context(self) -> str:
        """Retourne le contenu actuel de l'écran pour injection dans Jarvis."""
        if not self.last_text:
            return "Aucun texte détecté à l'écran actuellement."
        return f"CONTENU ACTUEL DE L'ÉCRAN :\n---\n{self.last_text}\n---"

# EXEMPLE D'UTILISATION
if __name__ == "__main__":
    vision = JarvisVision(use_easyocr=False, scan_interval=2.0)
    vision.start()
    
    try:
        while True:
            print("\n" + "="*30)
            print("APERÇU VISION JARVIS :")
            # On n'affiche que les 200 premiers caractères pour le test
            print(vision.get_context()[:200] + "...")
            time.sleep(5)
    except KeyboardInterrupt:
        vision.stop()
        print("Vision arrêtée.")

"""
INSTRUCTIONS D'INSTALLATION (WINDOWS) :

1. INSTALLER TESSERACT OCR :
   - Téléchargez l'installeur (.exe) ici : https://github.com/UB-Mannheim/tesseract/wiki
   - Installez-le dans le dossier par défaut (C:\Program Files\Tesseract-OCR).
   - (Optionnel) Ajoutez 'C:\Program Files\Tesseract-OCR' à votre variable d'environnement PATH.

2. INSTALLER LES PAQUETS PIP :
   Copiez et collez cette commande dans votre terminal :
   pip install mss opencv-python pytesseract easyocr numpy

3. DÉPENDANCES SUPPLÉMENTAIRES POUR EASYOCR (Optionnel) :
   - EasyOCR utilise PyTorch. Si vous avez une carte graphique NVIDIA, installez une version 
     compatible CUDA pour plus de rapidité : https://pytorch.org/get-started/locally/
"""
