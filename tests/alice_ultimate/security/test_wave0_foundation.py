#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 0 — SOCLE FONDATION (FEATURE FLAGS, AUDIT REDACTION, CONTRATS)
"""

import os
import sys
import tempfile
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.feature_flags import FeatureFlagManager, FeatureDisabledError
from alice_core.security.audit import AuditLogger, sanitize_for_log, redact_text
from alice_core.contracts import ServiceResult


class TestWave0Foundation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flag_file = os.path.join(self.tmp.name, "flags.json")
        self.audit_file = os.path.join(self.tmp.name, "audit.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_01_sensitive_flags_default_disabled(self):
        mgr = FeatureFlagManager(state_file=self.flag_file)
        for sensitive in (
            "voice_biometrics", "video_monitoring", "encrypted_vault",
            "predictive_automation", "webhook_connector", "web_automation", "visual_memory"
        ):
            self.assertFalse(mgr.is_enabled(sensitive), f"{sensitive} doit être désactivé par défaut")
            with self.assertRaises(FeatureDisabledError):
                mgr.require_enabled(sensitive)

    def test_02_flag_persistence_and_env_override(self):
        mgr = FeatureFlagManager(state_file=self.flag_file)
        mgr.set_flag("encrypted_vault", True)
        self.assertTrue(mgr.is_enabled("encrypted_vault"))

        mgr2 = FeatureFlagManager(state_file=self.flag_file)
        self.assertTrue(mgr2.is_enabled("encrypted_vault"))

        os.environ["ALICE_FLAG_ENCRYPTED_VAULT"] = "0"
        try:
            self.assertFalse(mgr2.is_enabled("encrypted_vault"))
        finally:
            os.environ.pop("ALICE_FLAG_ENCRYPTED_VAULT", None)

    def test_03_audit_secret_redaction_and_chain(self):
        logger = AuditLogger(log_file=self.audit_file)
        e1 = logger.log(
            category="SECURITY",
            action="test_connect",
            details={
                "api_key": "AIzaSyDummyKeyShouldBeRedacted123456",
                "rtsp_url": "rtsp://admin:SuperSecretPass@192.168.1.50:554/stream1",
                "raw_msg": "Token ghp_abcdefghijklmnopqrstuvwxyz123456 détecté",
                "safe_field": "ok"
            }
        )
        self.assertEqual(e1["details"]["api_key"], "***REDACTED***")
        self.assertEqual(e1["details"]["rtsp_url"], "***REDACTED***")
        self.assertIn("***REDACTED***", e1["details"]["raw_msg"])
        self.assertNotIn("ghp_abcdef", e1["details"]["raw_msg"])
        self.assertEqual(e1["details"]["safe_field"], "ok")

        e2 = logger.log(category="SECURITY", action="second_event")
        self.assertEqual(e2["prev_hash"], e1["entry_hash"])

        with open(self.audit_file, encoding="utf-8") as f:
            raw_file = f.read()
        self.assertNotIn("SuperSecretPass", raw_file)
        self.assertNotIn("AIzaSyDummyKey", raw_file)

    def test_04_service_result_contract(self):
        res = ServiceResult(success=True, status="OK", message="Done", data={"x": 1})
        d = res.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["status"], "OK")
        self.assertTrue(d["trace_id"].startswith("tr_"))


if __name__ == "__main__":
    unittest.main()
