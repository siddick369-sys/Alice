#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 1 — FEATURE 30 : OBSERVABILITY & SELF-DIAGNOSTICS DASHBOARD
Valide les métriques réelles sans psutil, les percentiles, la sécurité RBAC et l'export.
"""

import os
import sys
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.ops.observability import ObservabilityRegistry
from alice_core.security.rbac import RBACPolicyEngine, Role


class TestWave1Observability(unittest.TestCase):

    def setUp(self):
        self.obs = ObservabilityRegistry()
        self.rbac = RBACPolicyEngine()
        self.admin = self.rbac.register_principal("s_adm", "admin1", Role.ADMIN)
        self.guest = self.rbac.register_principal("s_gst", "guest1", Role.GUEST)

    def test_01_real_system_telemetry_without_psutil(self):
        diag = self.obs.run_self_diagnostic()
        self.assertIn("cpu", diag)
        self.assertIn("ram", diag)
        self.assertIn("disk", diag)
        self.assertGreaterEqual(diag["ram"], 0.0)
        self.assertLessEqual(diag["ram"], 100.0)
        self.assertIn(diag["status"], ("OK", "ALERTE"))

    def test_02_latency_percentiles_and_command_rates(self):
        for v in [10, 20, 30, 40, 100]:
            self.obs.record_latency("rag_search_ms", v)
        for _ in range(8):
            self.obs.record_command_outcome("SUCCEEDED")
        for _ in range(2):
            self.obs.record_command_outcome("FAILED")

        snap = self.obs.get_snapshot()
        self.assertEqual(snap["latencies"]["rag_search_ms"]["count"], 5)
        self.assertEqual(snap["latencies"]["rag_search_ms"]["p50"], 30.0)
        self.assertEqual(snap["latencies"]["rag_search_ms"]["p95"], 100.0)
        self.assertEqual(snap["commands"]["success_rate_percent"], 80.0)
        self.assertEqual(snap["commands"]["failure_rate_percent"], 20.0)

    def test_03_rbac_enforced_on_dashboard_and_export(self):
        res_guest = self.obs.get_authorized_dashboard(self.guest)
        self.assertFalse(res_guest["authorized"])
        self.assertEqual(res_guest["status"], "FORBIDDEN")

        res_admin = self.obs.get_authorized_dashboard(self.admin)
        self.assertTrue(res_admin["authorized"])
        self.assertIn("system", res_admin)

        exp_guest = self.obs.export_authorized(self.guest)
        self.assertFalse(exp_guest["authorized"])
        exp_admin = self.obs.export_authorized(self.admin, fmt="json")
        self.assertTrue(exp_admin["authorized"])


if __name__ == "__main__":
    unittest.main()
