# ALICE_013_OCR_VISION_VALIDATION.md
## Audit et Validation Réelle du Sous-Système Vision & OCR — Mission 013

**Mission ID :** `ALICE-LOCAL-RUNTIME-ACCEPTANCE-013`  
**Date :** 2026-11-27  

---

### 1. Vérification des Prérequis Locaux

- **Binaire Exécutable Tesseract :** Détecté sur l'hôte à l'emplacement standard `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **Fichiers de Modèles Linguistiques (`tessdata`) :**
  - Dossier : `Jarvis Final - SITE/tessdata/`
  - Fichiers présents : `eng.traineddata` (3.9 Mo), `fra.traineddata` (4.4 Mo).
- **Variable d'Environnement :** `main2.py:40` initialise formellement `os.environ['TESSDATA_PREFIX']` vers `Jarvis Final - SITE/tessdata`.

---

### 2. Test Réel d'Extraction Textuelle OCR (Image Synthétique de Contrôle)

Un fichier image de contrôle a été généré dans `local_validation_013/test_data/ocr_sample.png` avec le contenu suivant :
```
ALICE VALIDATION 013
TOTAL FACTURE: 42.50 EUR
```

**Exécution du pipeline OCR (`JarvisVision.extract_text_tesseract`) :**
- Prétraitement d'image (redimensionnement bicubique x2, flou gaussien, binarisation adaptative Otsu).
- Appel Tesseract via `pytesseract`.
- **Texte extrait et nettoyé :**
  ```
  ALICE VALIDATION 013

  TOTAL FACTURE: 42.50 EUR
  ```
- **Concordance :** **100% de conformité** sur les caractères, chiffres et symboles monétaires.

---

### 3. Gestion des Cas Limites et Capture d'Écran GDI (BitBlt)

1. **Image vide / unicolore (noire) :**  
   Traitée sans exception ni plantage ; renvoie une chaîne vide propre (`''`).
2. **Capture d'écran Windows GDI (`mss.grab`) en session non interactive :**  
   - En environnement headless ou de service Windows où le contexte de bureau GDI est déconnecté, la fonction Win32 `BitBlt` échoue avec `ScreenShotError`.
   - **Comportement constaté :** L'exception est interceptée par la boucle `_vision_loop()` et le rate-limiting (1 log / 30s) empêche la saturation du disque.
   - **Conclusion de rigueur forensique :** Le moteur OCR Tesseract est pleinement fonctionnel en local pour tout flux d'images ou reçus téléversés. En revanche, la capture automatisée d'écran du bureau hôte nécessite une session de bureau Windows interactive active pour que l'appel `BitBlt` aboutisse.
