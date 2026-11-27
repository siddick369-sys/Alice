#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 4 — PILIER 4 VISION & OCR (FEATURES 16 À 20)
Teste Tesseract 5.5 réel sur ticket généré, prévisualisation/rétention mobile,
anti-faux-positifs vidéo, mémoire visuelle bornée et zones de sécurité polygonales.
"""

import os
import sys
import io
import base64
import time
import tempfile
import unittest
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.contracts import AliceSecurityError, FeatureDisabledError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.vision.analyzer import OnDemandVisualAnalyzer
from alice_core.vision.ocr_receipts import SmartReceiptOCR
from alice_core.vision.video_sentinel import RTSPVideoSentinel
from alice_core.vision.visual_memory import VisualMemoryStore
from alice_core.vision.safety_zones import SafetyZoneMonitor
from alice_rag import AliceRAGEngine


def _make_b64_image(width=320, height=240, color=(200, 200, 200)) -> str:
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    if color != (5, 5, 5):
        draw.rectangle([40, 40, 200, 180], fill=(40, 120, 220))
    buf = io.BytesIO()
    # Ajouter faux EXIF tag 0x010F Make="SecretPhone" pour vérifier suppression
    exif = img.getexif()
    exif[0x010F] = "SecretCameraModel"
    img.save(buf, format="JPEG", exif=exif)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _make_receipt_image(path: str, lines: list):
    img = Image.new("RGB", (700, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    # Utiliser police système Windows Arial/Consolas si dispo pour OCR net
    for candidate in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        if os.path.exists(candidate):
            font = ImageFont.truetype(candidate, 30)
            break
    y = 30
    for line in lines:
        draw.text((35, y), line, fill=(0, 0, 0), font=font)
        y += 45
    img.save(path)


class TestWave4Vision(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        FEATURE_FLAGS.set_flag("video_monitoring", False, persist=False)
        FEATURE_FLAGS.set_flag("visual_memory", False, persist=False)
        self.tmp.cleanup()

    def test_01_visual_analyzer_preview_exif_strip_and_risk_uncertainty(self):
        ana = OnDemandVisualAnalyzer(temp_dir=self.tmp.name, default_retention="ephemeral")
        # Image sombre / uniforme (risque faux positif) avec question sur plaque de cuisson
        dark_b64 = _make_b64_image(color=(10, 10, 10))
        st = ana.stage_preview(dark_b64, owner_id="u1", question="La plaque de cuisson est-elle éteinte ?")
        self.assertTrue(st["success"])
        self.assertTrue(st["exif_stripped"])
        self.assertTrue(st["requires_confirmation"])

        # Vérifier qu'aucun EXIF ne subsiste sur le fichier sauvegardé
        saved_path = ana.staged[st["preview_id"]]["path"]
        with Image.open(saved_path) as im:
            self.assertEqual(len(im.getexif()), 0)

        res = ana.confirm_and_analyze(st["preview_id"], owner_id="u1", confirmed=True)
        self.assertEqual(res["status"], "UNCERTAIN_NEEDS_HUMAN_VERIFICATION")
        self.assertIn("vérifier physiquement", res["analysis"])
        self.assertTrue(res["deleted_after_analysis"])
        self.assertFalse(os.path.exists(saved_path))

    def test_02_smart_ocr_real_tesseract_validation_and_xlsx_export(self):
        ocr = SmartReceiptOCR(storage_file=os.path.join(self.tmp.name, "rcpt.json"))
        good_img = os.path.join(self.tmp.name, "ticket_ok.png")
        _make_receipt_image(good_img, [
            "BOULANGERIE CENTRALE",
            "Date: 24/11/2026",
            "Facture: FAC-2026-08",
            "Total HT: 100.00",
            "TVA: 20.00",
            "Total TTC: 120.00 EUR",
        ])
        res = ocr.process_receipt(good_img, owner_id="u1")
        self.assertEqual(res["validation_status"], "VERIFIED", f"Inconsistencies: {res['inconsistencies']} | Raw: {res['raw_text_excerpt']}")
        self.assertEqual(res["montant_ttc"], 120.0)
        self.assertTrue(res["saved"])

        # Export XLSX vérifié avec AliceRAGEngine
        xlsx_out = os.path.join(self.tmp.name, "tickets.xlsx")
        ocr.export_xlsx("u1", xlsx_out)
        self.assertTrue(os.path.exists(xlsx_out))
        rag = AliceRAGEngine(knowledge_dir=self.tmp.name, index_file=os.path.join(self.tmp.name, "idx.json"))
        extracted = rag.extract_text_from_xlsx(xlsx_out)
        self.assertTrue(any("120.0" in r["text"] for r in extracted))

        # Ticket mathématiquement incohérent -> bloqué sans confirmation explicite
        bad_img = os.path.join(self.tmp.name, "ticket_bad.png")
        _make_receipt_image(bad_img, [
            "CAFE DU COIN",
            "Total HT: 50.00",
            "TVA: 10.00",
            "Total TTC: 99.00 EUR",
        ])
        res_bad = ocr.process_receipt(bad_img, owner_id="u1", confirmed_save=False)
        self.assertEqual(res_bad["validation_status"], "NEEDS_MANUAL_REVIEW")
        self.assertFalse(res_bad["saved"])

    def test_03_video_sentinel_auth_weather_filter_and_no_facerec(self):
        sent = RTSPVideoSentinel(capture_dir=self.tmp.name, cooldown_seconds=5.0)
        FEATURE_FLAGS.set_flag("video_monitoring", False, persist=False)
        with self.assertRaises(FeatureDisabledError):
            sent.register_camera("cam1", "rtsp://user:pass@192.168.1.99:554/h264", "u1")

        FEATURE_FLAGS.set_flag("video_monitoring", True, persist=False)
        sent.register_camera("cam1", "rtsp://user:pass@192.168.1.99:554/h264", "u1", zone="jardin")
        self.assertFalse(sent.face_recognition_enabled)

        # Caméra inconnue rejetée
        base_frame = np.full((240, 320, 3), 60, dtype=np.uint8)
        with self.assertRaises(AliceSecurityError):
            sent.process_authorized_frame("cam_inconnue", base_frame)

        # Fond initial
        sent.process_authorized_frame("cam1", base_frame, min_temporal_frames=2, now_ts=100.0)
        # Variation lumineuse globale (passage de nuage/flash sur >50% image) -> ignorée !
        flash_frame = np.full((240, 320, 3), 180, dtype=np.uint8)
        res_flash = sent.process_authorized_frame("cam1", flash_frame, min_temporal_frames=1, now_ts=101.0)
        self.assertEqual(len(res_flash["emitted_events"]), 0)

        # Réinitialiser sur fond calme puis objet localisé persistant sur 2 trames -> détecté !
        sent.process_authorized_frame("cam1", base_frame, min_temporal_frames=2, now_ts=102.0)
        obj_frame = base_frame.copy()
        cv2.rectangle(obj_frame, (100, 40), (150, 170), (240, 240, 240), -1)
        sent.process_authorized_frame("cam1", obj_frame, min_temporal_frames=2, now_ts=103.0)
        obj_frame2 = base_frame.copy()
        cv2.rectangle(obj_frame2, (105, 42), (155, 172), (240, 240, 240), -1)
        res_obj = sent.process_authorized_frame("cam1", obj_frame2, min_temporal_frames=2, now_ts=104.0)
        self.assertGreater(len(res_obj["emitted_events"]), 0)

    def test_04_visual_memory_privacy_never_invents_and_purge(self):
        vm = VisualMemoryStore(index_file=os.path.join(self.tmp.name, "vm.json"), max_items=5, retention_hours=1.0)
        FEATURE_FLAGS.set_flag("visual_memory", True, persist=False)

        # Aucune observation -> NOT_OBSERVED
        r_none = vm.search_object("u1", "lunettes")
        self.assertFalse(r_none["found"])
        self.assertEqual(r_none["status"], "NOT_OBSERVED")

        # Enregistrement réel d'objet + exclusion profilage personne foyer
        obs = vm.record_observation("u1", "cam1", "table_entree", ["lunettes", "aboubakar"], 0.88)
        self.assertNotIn("aboubakar", obs["objects"])
        self.assertIn("lunettes", obs["objects"])

        r_found = vm.search_object("u1", "lunettes")
        self.assertTrue(r_found["found"])
        self.assertIn("table_entree", r_found["message"])

        # Rétention expirée -> purge automatique
        vm.observations[0]["timestamp"] = time.time() - 7200.0
        purged = vm.purge_expired()
        self.assertEqual(purged, 1)
        self.assertFalse(vm.search_object("u1", "lunettes")["found"])

    def test_05_safety_zones_polygon_dwell_and_disclaimer(self):
        sz = SafetyZoneMonitor()
        FEATURE_FLAGS.set_flag("video_monitoring", True, persist=False)
        sz.add_zone("piscine", "Piscine Extérieure", "cam1", "u1", [(50, 50), (200, 50), (200, 200), (50, 200)], start_hour=0, end_hour=23, dwell_frames_required=2)

        # Hors polygone -> aucune alerte
        out_alerts = sz.evaluate_detections("cam1", [{"class": "humain", "bbox": [10, 10, 30, 30]}])
        self.assertEqual(len(out_alerts), 0)

        # 1ère frame dedans -> attente validation temporelle
        in1 = sz.evaluate_detections("cam1", [{"class": "humain", "bbox": [100, 100, 140, 180]}])
        self.assertEqual(len(in1), 0)

        # 2ème frame dedans -> alerte confirmée avec avertissement légal obligatoire
        in2 = sz.evaluate_detections("cam1", [{"class": "humain", "bbox": [105, 100, 145, 180]}])
        self.assertEqual(len(in2), 1)
        self.assertIn("substitut à la surveillance humaine", in2[0]["disclaimer"])


if __name__ == "__main__":
    unittest.main()
