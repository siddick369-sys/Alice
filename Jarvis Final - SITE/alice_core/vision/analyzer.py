#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 16 — ON-DEMAND VISUAL ANALYSIS (ALICE-VISION-016, Wave 4).
Parcours complet : Capture -> Prévisualisation -> Confirmation explicite ->
Analyse (qualité image + OCR/Vision) -> Politique de rétention/suppression.
Protège les métadonnées EXIF et signale toute incertitude sur les situations à risque.
"""

import os
import io
import time
import uuid
import base64
import threading
import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, Optional
from alice_core.ops.observability import OBSERVABILITY


RISK_KEYWORDS = (
    "plaque", "cuisson", "gaz", "four", "fer à repasser", "bougie",
    "éteint", "eteint", "allumé", "allume", "fuite", "feu", "fumée", "sûr"
)


class OnDemandVisualAnalyzer:
    """Gestionnaire sécurisé d'analyses visuelles à la demande avec prévisualisation et rétention."""

    def __init__(self, temp_dir: Optional[str] = None, default_retention: str = "ephemeral"):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.temp_dir = temp_dir or os.path.join(base_dir, "temp_uploads", "vision_staging")
        self.default_retention = default_retention  # "ephemeral" | "keep_24h"
        self.staged: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _strip_exif_and_decode(image_b64: str) -> bytes:
        raw = base64.b64decode(image_b64, validate=True)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        buf = io.BytesIO()
        # Sauvegarde sans métadonnées EXIF (GPS, modèle appareil supprimés)
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()

    @staticmethod
    def assess_image_quality(clean_bytes: bytes) -> Dict[str, Any]:
        arr = np.frombuffer(clean_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return {"valid": False, "reason": "image_decode_failed"}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        h, w = gray.shape
        low_light = brightness < 40.0
        blurry = blur_var < 35.0
        return {
            "valid": True,
            "width": int(w),
            "height": int(h),
            "brightness": round(brightness, 1),
            "sharpness": round(blur_var, 1),
            "low_light": low_light,
            "blurry": blurry,
            "ambiguous": bool(low_light or blurry),
        }

    def stage_preview(self, image_b64: str, owner_id: str, question: str = "", retention_policy: Optional[str] = None) -> Dict[str, Any]:
        """Étape 1-2 : Décode, supprime les EXIF et prépare l'aperçu avant confirmation."""
        try:
            clean_bytes = self._strip_exif_and_decode(image_b64)
            quality = self.assess_image_quality(clean_bytes)
            if not quality["valid"]:
                return {"success": False, "status": "INVALID_IMAGE", "error": quality.get("reason")}
        except Exception as e:
            return {"success": False, "status": "INVALID_IMAGE", "error": str(e)}

        preview_id = f"vis_{uuid.uuid4().hex[:10]}"
        os.makedirs(self.temp_dir, exist_ok=True)
        fpath = os.path.join(self.temp_dir, f"{preview_id}.jpg")
        with open(fpath, "wb") as f:
            f.write(clean_bytes)

        policy = retention_policy or self.default_retention
        with self._lock:
            self.staged[preview_id] = {
                "preview_id": preview_id,
                "owner_id": owner_id,
                "path": fpath,
                "question": question,
                "quality": quality,
                "retention_policy": policy,
                "exif_stripped": True,
                "created_at": time.time(),
                "confirmed": False,
            }

        return {
            "success": True,
            "status": "PREVIEW_READY",
            "preview_id": preview_id,
            "exif_stripped": True,
            "quality": quality,
            "retention_policy": policy,
            "requires_confirmation": True,
        }

    def confirm_and_analyze(
        self,
        preview_id: str,
        owner_id: str,
        confirmed: bool,
        vision_fn=None,
    ) -> Dict[str, Any]:
        """Étape 3-6 : Exige confirmation, analyse et applique la rétention/suppression."""
        with self._lock:
            item = self.staged.get(preview_id)
            if not item:
                return {"success": False, "status": "NOT_FOUND", "error": "Capture introuvable ou expirée."}
            if item["owner_id"] != owner_id and owner_id != "owner_local":
                return {"success": False, "status": "FORBIDDEN", "error": "Capture d'un autre utilisateur."}

        if not confirmed:
            self._delete_capture(preview_id)
            return {"success": True, "status": "CANCELLED_AND_DELETED", "deleted": True}

        t0 = time.perf_counter()
        quality = item["quality"]
        question = item.get("question", "")
        is_safety_check = any(k in question.lower() for k in RISK_KEYWORDS)

        analysis_text = ""
        uncertain = quality["ambiguous"]

        if is_safety_check and quality["ambiguous"]:
            # Règle impérative : ne jamais affirmer qu'un appareil critique est éteint sur image ambiguë
            analysis_text = (
                "Image trop sombre ou floue pour une vérification fiable. "
                "Par sécurité, je ne peux pas confirmer l'état de l'équipement : veuillez vérifier physiquement sur place."
            )
            status = "UNCERTAIN_NEEDS_HUMAN_VERIFICATION"
        else:
            if vision_fn:
                try:
                    analysis_text = str(vision_fn(item["path"], question))
                except Exception as e:
                    analysis_text = f"Analyse IA indisponible ({e})."
                    uncertain = True
            else:
                analysis_text = (
                    f"Image nette ({quality['width']}x{quality['height']}, luminosité {quality['brightness']})."
                )
            if is_safety_check:
                analysis_text += " [Note : une vérification visuelle directe reste recommandée pour les appareils à risque.]"
            status = "UNCERTAIN_NEEDS_HUMAN_VERIFICATION" if uncertain else "ANALYZED"

        lat_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        OBSERVABILITY.record_latency("vision_analysis_ms", lat_ms)

        deleted = False
        if item["retention_policy"] == "ephemeral":
            deleted = self._delete_capture(preview_id)

        return {
            "success": True,
            "status": status,
            "preview_id": preview_id,
            "analysis": analysis_text,
            "quality": quality,
            "uncertain": uncertain,
            "exif_stripped": True,
            "deleted_after_analysis": deleted,
            "latency_ms": lat_ms,
        }

    def _delete_capture(self, preview_id: str) -> bool:
        with self._lock:
            item = self.staged.pop(preview_id, None)
        if item and os.path.exists(item["path"]):
            try:
                os.remove(item["path"])
                return True
            except Exception:
                return False
        return bool(item)


VISUAL_ANALYZER = OnDemandVisualAnalyzer()
