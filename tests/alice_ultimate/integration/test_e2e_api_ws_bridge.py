#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS D'INTÉGRATION END-TO-END — PARCOURS RÉEL HTTP / COOKIES / RBAC / WS / WEBHOOKS
Démarre un serveur HTTP réel MobileHandler sur port éphémère (127.0.0.1:0) et valide
les parcours complets client -> API -> service -> résultat.
"""

import os
import sys
import io
import json
import time
import base64
import asyncio
import threading
import http.server
import http.client
import unittest
from PIL import Image

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

import main2
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.automation.webhooks import WEBHOOK_GATEWAY


class TestE2EIntegrationBridge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), main2.MobileHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def tearDown(self):
        FEATURE_FLAGS.set_flag("webhook_connector", False, persist=False)

    def _pair_and_get_cookies(self, role="OWNER"):
        code = main2.PAIRING_MANAGER.generate_pairing_code(role=role)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/pair", body=json.dumps({"code": code}), headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        cookies = resp.getheader("Set-Cookie") or ""
        # Extraire alice_session=...;
        all_set = resp.headers.get_all("Set-Cookie") or []
        cookie_pairs = []
        for c in all_set:
            cookie_pairs.append(c.split(";", 1)[0])
        conn.close()
        return resp.status, "; ".join(cookie_pairs), body.get("csrf_token", "")

    def test_01_http_ops_metrics_rbac_owner_vs_guest_and_unauth(self):
        # 1. Non authentifié -> 401
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/ops/metrics")
        r_unauth = conn.getresponse()
        r_unauth.read()
        conn.close()
        self.assertEqual(r_unauth.status, 401)

        # 2. GUEST -> 403 Forbidden
        st_g, cookie_g, _ = self._pair_and_get_cookies(role="GUEST")
        self.assertEqual(st_g, 200)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/ops/metrics", headers={"Cookie": cookie_g})
        r_guest = conn.getresponse()
        r_guest.read()
        conn.close()
        self.assertEqual(r_guest.status, 403)

        # 3. OWNER -> 200 OK avec télémétrie CPU/RAM réelle
        st_o, cookie_o, csrf_o = self._pair_and_get_cookies(role="OWNER")
        self.assertEqual(st_o, 200)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/ops/metrics", headers={"Cookie": cookie_o})
        r_owner = conn.getresponse()
        data = json.loads(r_owner.read().decode("utf-8"))
        conn.close()
        self.assertEqual(r_owner.status, 200)
        self.assertTrue(data["authorized"])
        self.assertIn("cpu_percent", data["system"])

        # 4. Sync notes mobile + Vision stage/confirm via HTTP avec CSRF
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        uniq = f"{int(time.time() * 1000)}"
        sync_body = json.dumps({"ops": [{"op_id": f"e2e_{uniq}", "item_id": f"n_e2e_{uniq}", "item_type": "note", "title": "E2E", "content": "OK", "base_version": 0}]})
        conn.request("POST", "/api/sync/notes", body=sync_body, headers={
            "Content-Type": "application/json", "Cookie": cookie_o, "X-CSRF-Token": csrf_o
        })
        r_sync = conn.getresponse()
        sync_data = json.loads(r_sync.read().decode("utf-8"))
        conn.close()
        self.assertEqual(r_sync.status, 200)
        self.assertEqual(len(sync_data["accepted"]), 1)

        # Vision stage -> confirm
        img = Image.new("RGB", (160, 120), (140, 160, 180))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/vision/stage", body=json.dumps({"image_b64": b64, "question": "test", "retention_policy": "ephemeral"}), headers={
            "Content-Type": "application/json", "Cookie": cookie_o, "X-CSRF-Token": csrf_o
        })
        r_st = conn.getresponse()
        st_data = json.loads(r_st.read().decode("utf-8"))
        conn.close()
        self.assertEqual(r_st.status, 200)
        self.assertEqual(st_data["status"], "PREVIEW_READY")

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/vision/confirm", body=json.dumps({"preview_id": st_data["preview_id"], "confirmed": True}), headers={
            "Content-Type": "application/json", "Cookie": cookie_o, "X-CSRF-Token": csrf_o
        })
        r_cf = conn.getresponse()
        cf_data = json.loads(r_cf.read().decode("utf-8"))
        conn.close()
        self.assertEqual(r_cf.status, 200)
        self.assertTrue(cf_data["deleted_after_analysis"])

    def test_02_http_webhook_hmac_and_replay_e2e(self):
        FEATURE_FLAGS.set_flag("webhook_connector", True, persist=False)
        reg = WEBHOOK_GATEWAY.register_connector("e2e_n8n", "E2E", "owner_local", {"meteo"})
        secret = reg["secret"]

        ts = str(int(time.time()))
        nonce = "e2e_nonce_1"
        body = json.dumps({"action": "meteo", "data": {"ville": "Paris"}}).encode("utf-8")
        sig = WEBHOOK_GATEWAY.compute_signature(secret, ts, nonce, body)

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/webhooks/e2e_n8n", body=body, headers={
            "Content-Type": "application/json",
            "X-Alice-Timestamp": ts,
            "X-Alice-Nonce": nonce,
            "X-Alice-Signature": sig,
        })
        r1 = conn.getresponse()
        r1.read()
        conn.close()
        self.assertEqual(r1.status, 200)

        # Rejeu HTTP -> 409
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/webhooks/e2e_n8n", body=body, headers={
            "Content-Type": "application/json",
            "X-Alice-Timestamp": ts,
            "X-Alice-Nonce": nonce,
            "X-Alice-Signature": sig,
        })
        r2 = conn.getresponse()
        r2.read()
        conn.close()
        self.assertEqual(r2.status, 409)

    def test_03_guest_ws_session_blocked_from_sensitive_json_action(self):
        # Vérifie que traiter_reponse_ia bloque un GUEST exécutant read_emails ou shutdown
        orig_stream = main2.demander_ia_stream
        orig_parler = main2.parler
        spoken = []

        async def mock_parler(msg, **kw):
            spoken.append(msg)

        async def mock_stream(t):
            yield '{"action": "read_emails"}'

        class FakeGuestWS:
            session_id = "e2e_guest_ws"
            remote_address = ("192.168.1.90", 12345)
            closed = False
            async def send(self, msg):
                pass

        main2.RBAC.register_principal("e2e_guest_ws", "guest_e2e", main2.Role.GUEST)
        main2.parler = mock_parler
        main2.demander_ia_stream = mock_stream
        try:
            asyncio.run(main2.traiter_reponse_ia("lis mes emails", mobile_ws=FakeGuestWS()))
            self.assertTrue(any("Accès refusé" in s for s in spoken), f"Expected RBAC refusal, got: {spoken}")
        finally:
            main2.demander_ia_stream = orig_stream
            main2.parler = orig_parler
            main2.RBAC.revoke_principal("e2e_guest_ws")


if __name__ == "__main__":
    unittest.main()
