#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 5 — PILIER 5 ORCHESTRATION & AUTOMATISATION (FEATURES 21 À 25)
Couvre Persistent Jobs, Agent Swarm, Autonomous Web Agent, Webhook HMAC & Briefings.
"""

import os
import sys
import json
import time
import asyncio
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_orchestrator import CommandLifecycleManager, STATE_REQUIRES_CONFIRMATION, STATE_SUCCEEDED, STATE_FAILED
from alice_core.contracts import AliceSecurityError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import RBAC, Role
from alice_core.automation.jobs import PersistentJobManager, JOB_RUNNING, JOB_QUEUED, JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED, JOB_UNKNOWN
from alice_core.automation.agent_swarm import AgentSwarmCoordinator, SwarmBudget
from alice_core.automation.web_agent import AutonomousWebAgent
from alice_core.automation.webhooks import WebhookGateway
from alice_core.automation.daily_briefing import ProactiveDailyBriefing
from alice_google_adapter import GOOGLE_ADAPTER


class TestWave5Automation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.owner = RBAC.register_principal("sw_o", "owner_u", Role.OWNER)
        self.guest = RBAC.register_principal("sw_g", "guest_u", Role.GUEST)

    def tearDown(self):
        FEATURE_FLAGS.set_flag("web_automation", False, persist=False)
        FEATURE_FLAGS.set_flag("webhook_connector", False, persist=False)
        GOOGLE_ADAPTER.disable_mock_mode()
        self.tmp.cleanup()

    def test_01_persistent_jobs_recovery_retry_rbac_and_push(self):
        db = os.path.join(self.tmp.name, "jobs.db")
        jm = PersistentJobManager(db_path=db, max_concurrency=2)
        pushed = []

        async def mock_push(sid, ev):
            pushed.append((sid, ev))

        jm.set_push_notifier(mock_push)

        attempts = {"n": 0}

        async def flaky_task(payload, set_prog):
            attempts["n"] += 1
            set_prog(50)
            if attempts["n"] == 1:
                raise RuntimeError("Transient network blip")
            return {"ok": True, "val": payload["x"]}

        jm.register_handler("flaky", flaky_task)

        # Idempotence sur création
        j1 = jm.enqueue("owner_u", "sw_o", "flaky", {"x": 42}, idempotency_key="key1", max_retries=1)
        j2 = jm.enqueue("owner_u", "sw_o", "flaky", {"x": 42}, idempotency_key="key1", max_retries=1)
        self.assertEqual(j1["job_id"], j2["job_id"])

        # Isolation utilisateur : autre user bloqué
        with self.assertRaises(PermissionError):
            jm.get_job(j1["job_id"], requester_owner_id="guest_u")

        # Exécution avec retry borné + notification push post-confirmation
        res = asyncio.run(jm.execute_job(j1["job_id"]))
        self.assertEqual(res["status"], JOB_SUCCEEDED)
        self.assertEqual(attempts["n"], 2)
        self.assertEqual(len(pushed), 1)
        self.assertEqual(pushed[0][1]["status"], JOB_SUCCEEDED)

        # Simulation redémarrage serveur après crash sur jobs RUNNING
        j_idem = jm.enqueue("owner_u", "sw_o", "flaky", {"x": 1}, idempotent_retryable=True)
        j_nonidem = jm.enqueue("owner_u", "sw_o", "flaky", {"x": 2}, idempotent_retryable=False)
        jm._update_job(j_idem["job_id"], status=JOB_RUNNING)
        jm._update_job(j_nonidem["job_id"], status=JOB_RUNNING)
        rec = jm.recover_interrupted_jobs()
        self.assertEqual(rec["requeued"], 1)
        self.assertEqual(rec["marked_unknown"], 1)
        self.assertEqual(jm.get_job(j_idem["job_id"])["status"], JOB_QUEUED)
        self.assertEqual(jm.get_job(j_nonidem["job_id"])["status"], JOB_UNKNOWN)

        # RBAC refusé à l'exécution (guest tente job require shutdown)
        j_priv = jm.enqueue("guest_u", "sw_g", "flaky", {"x": 9}, required_action="shutdown")
        res_priv = asyncio.run(jm.execute_job(j_priv["job_id"]))
        self.assertEqual(res_priv["status"], JOB_FAILED)
        self.assertIn("RBAC refusé", res_priv["error"])

    def test_02_agent_swarm_budgets_loops_secrets_and_confirmation(self):
        orch = CommandLifecycleManager(log_path=os.path.join(self.tmp.name, "orch.log"))
        swarm = AgentSwarmCoordinator(orchestrator=orch)
        seen_payloads = []

        async def res_runner(ctx):
            seen_payloads.append(ctx["payload"])
            return {"success": True, "summary": "Faits vérifiés."}

        async def slow_runner(ctx):
            await asyncio.sleep(1.5)
            return {"success": True, "summary": "Trop tard"}

        swarm.register_agent_runner("ResearchAgent", res_runner)
        swarm.register_agent_runner("FactCheckerAgent", slow_runner)

        async def run():
            cmd = orch.register_command("analyse multi-agents", "sw_o")
            # 1. Profondeur dépassée
            r_depth = await swarm.delegate_task(cmd.command_id, "sw_o", [{"agent": "ResearchAgent"}], depth=3)
            self.assertEqual(r_depth["status"], STATE_FAILED)

            # 2. Tentative d'élévation de privilège d'un agent
            cmd_esc = orch.register_command("esc", "sw_o")
            with self.assertRaises(AliceSecurityError):
                await swarm.delegate_task(cmd_esc.command_id, "sw_o", [{"agent": "ResearchAgent", "grant_role": "OWNER"}])

            # 3. Boucle + fuite secret filtrée + timeout partiel
            cmd2 = orch.register_command("analyse mixte", "sw_o")
            out = await swarm.delegate_task(
                cmd2.command_id, "sw_o",
                [
                    {"agent": "ResearchAgent", "untrusted_source": True, "payload": {"vault_secret": "TOP_SECRET", "context_data": "info web"}},
                    {"agent": "FactCheckerAgent", "payload": {}},  # timeout 0.35s
                ],
                budget=SwarmBudget(max_depth=2, max_calls=5, max_time_seconds=0.35),
                call_chain=[],
            )
            # Test explicite de boucle de délégation bloquée
            cmd_loop = orch.register_command("boucle", "sw_o")
            out_loop = await swarm.delegate_task(
                cmd_loop.command_id, "sw_o",
                [{"agent": "ResearchAgent", "payload": {}}],
                call_chain=["ResearchAgent"],
            )
            self.assertIn("Boucle de délégation", out_loop["subtasks"][0]["error"])
            # ResearchAgent 1 ok, Secret masqué, untrusted encadré, FactChecker timeout -> partiel !
            self.assertTrue(seen_payloads[0]["vault_secret"].startswith("***BLOCKED"))
            self.assertIn("<untrusted_web_data>", seen_payloads[0]["context_data"])
            self.assertEqual(out["status"], STATE_SUCCEEDED)
            self.assertTrue(out["partial"])

            # 4. Action sensible via AutomationAgent -> exige confirmation centrale
            cmd3 = orch.register_command("action critique", "sw_o")
            out_sens = await swarm.delegate_task(
                cmd3.command_id, "sw_o",
                [{"agent": "AutomationAgent", "requested_action": "ha_lumiere", "payload": {"piece": "salon"}}]
            )
            self.assertEqual(out_sens["status"], STATE_REQUIRES_CONFIRMATION)

        asyncio.run(run())

    def test_03_web_agent_redirect_ssrf_captcha_and_prepared_gate(self):
        FEATURE_FLAGS.set_flag("web_automation", True, persist=False)
        wa = AutonomousWebAgent()

        # Exécutable interdit
        prep_exe = wa.prepare_engaging_action("download", "https://8.8.8.8/malware.exe", {})
        self.assertFalse(prep_exe["success"])

        # Redirection 302 vers localhost (SSRF via redirection) bloquée !
        mock_redir = MagicMock()
        mock_redir.status_code = 302
        mock_redir.headers = {"Location": "http://127.0.0.1:8765/admin"}
        with patch("alice_core.automation.web_agent.requests.get", return_value=mock_redir):
            res_ssrf = wa.fetch_safe("https://8.8.8.8/start")
        self.assertFalse(res_ssrf["success"])
        self.assertEqual(res_ssrf["status"], "BLOCKED_SSRF_OR_UNSAFE")

        # Détection CAPTCHA -> arrêt immédiat sans contournement
        mock_cap = MagicMock()
        mock_cap.status_code = 200
        mock_cap.iter_content.return_value = [b"<html><div>Please verify you are human - reCAPTCHA</div></html>"]
        with patch("alice_core.automation.web_agent.requests.get", return_value=mock_cap):
            res_cap = wa.fetch_safe("https://8.8.8.8/shop")
        self.assertFalse(res_cap["success"])
        self.assertEqual(res_cap["status"], "BLOCKED_CAPTCHA_OR_MFA")

        # Action engageante préparée != exécutée
        res_prep = wa.prepare_engaging_action("hotel_booking", "https://8.8.8.8/book", {"price": 120}, user_confirmed=False)
        self.assertEqual(res_prep["status"], "PREPARED_REQUIRES_CONFIRMATION")
        self.assertFalse(res_prep["executed"])

    def test_04_webhook_gateway_hmac_replay_rotation_and_forbidden_actions(self):
        FEATURE_FLAGS.set_flag("webhook_connector", True, persist=False)
        gw = WebhookGateway(config_file=os.path.join(self.tmp.name, "wh.json"))

        # Interdiction d'enregistrer shutdown/alarme sur webhook
        with self.assertRaises(AliceSecurityError):
            gw.register_connector("n8n_bad", "Bad", "owner_u", {"shutdown"})

        reg = gw.register_connector("n8n_1", "NodeRED", "owner_u", {"ha_lumiere", "meteo"})
        secret1 = reg["secret"]

        ts = str(int(time.time()))
        body = json.dumps({"action": "ha_lumiere", "data": {"piece": "salon"}}).encode("utf-8")
        sig = gw.compute_signature(secret1, ts, "nonce_abc", body)

        # Signature valide -> 200
        ok, code, _ = gw.verify_and_parse_incoming("n8n_1", sig, ts, "nonce_abc", body)
        self.assertTrue(ok)
        self.assertEqual(code, 200)

        # Rejeu avec même nonce -> 409 bloqué
        ok_rep, code_rep, _ = gw.verify_and_parse_incoming("n8n_1", sig, ts, "nonce_abc", body)
        self.assertFalse(ok_rep)
        self.assertEqual(code_rep, 409)

        # Signature falsifiée -> 401 bloqué
        ok_bad, code_bad, _ = gw.verify_and_parse_incoming("n8n_1", "0" * 64, ts, "nonce_xyz", body)
        self.assertFalse(ok_bad)
        self.assertEqual(code_bad, 401)

        # Rotation de secret : l'ancien reste toléré pendant la fenêtre de grâce, le nouveau marche aussi
        secret2 = gw.rotate_secret("n8n_1", "owner_u", grace_seconds=60.0)
        sig_old = gw.compute_signature(secret1, ts, "nonce_grace", body)
        sig_new = gw.compute_signature(secret2, ts, "nonce_new", body)
        self.assertTrue(gw.verify_and_parse_incoming("n8n_1", sig_old, ts, "nonce_grace", body)[0])
        self.assertTrue(gw.verify_and_parse_incoming("n8n_1", sig_new, ts, "nonce_new", body)[0])

    def test_05_daily_briefing_guest_privacy_and_silent_mode(self):
        GOOGLE_ADAPTER.enable_mock_mode({
            "emails": [{"id": "e1", "subject": "Relevé bancaire confidentiel"}],
            "calendar": [{"id": "c1", "summary": "Réunion équipe"}],
        })
        db = ProactiveDailyBriefing()
        # Invités présents à voix haute -> emails masqués strictement !
        br_guest = db.build_morning_briefing(self.owner, guests_present=True, speak_aloud=True)
        self.assertEqual(br_guest["sections"]["urgent_emails"]["status"], "REDACTED_PRIVACY_GUARD")

        # Sans invités -> emails accessibles à l'OWNER
        br_priv = db.build_morning_briefing(self.owner, guests_present=False, speak_aloud=True)
        self.assertIsInstance(br_priv["sections"]["urgent_emails"], list)

        # Mode silencieux -> speak_allowed=False
        db.configure(silent_mode=True)
        br_sil = db.build_morning_briefing(self.owner, guests_present=False, speak_aloud=True)
        self.assertFalse(br_sil["speak_allowed"])


if __name__ == "__main__":
    unittest.main()
