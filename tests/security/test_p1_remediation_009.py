# -*- coding: utf-8 -*-
"""
ALICE-P1-REMEDIATION-009: TARGETED SECURITY VERIFICATION SUITE
================================================================
Tests ciblés pour :
- FINDING-01 : Révocation active des WebSockets, multi-connexions, TOCTOU, immutabilité d'identité
- FINDING-02 : Routage WSS /ws mobile (via exécution Node réelle de buildWebSocketUrl dans mobile/app.js)
- FINDING-03 : RBAC strictement fail-closed + couverture exhaustive des call sites de main2.py
- FINDING-06 : En-têtes X-Forwarded-For dupliqués/ambigus + suppression verify_token & chemin auth WS
"""

import sys
import os
import re
import json
import time
import asyncio
import subprocess
import unittest
from unittest.mock import patch
import websockets

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Jarvis Final - SITE"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main2
from alice_core.security.rbac import RBAC, Role, UserPrincipal, ACTION_TO_PERMISSION, PUBLIC_CONVERSATIONAL_ACTIONS, PERMISSION_MATRIX


class MultiHeaderMock:
    """Simule un objet headers HTTP/WS supportant get_all() pour tester les en-têtes dupliqués."""
    def __init__(self, pairs):
        self._pairs = list(pairs)

    def get(self, name, default=None):
        nl = name.lower()
        for k, v in self._pairs:
            if k.lower() == nl:
                return v
        return default

    def get_all(self, name):
        nl = name.lower()
        return [v for k, v in self._pairs if k.lower() == nl]


async def _with_ws_server(coro_fn):
    main2.CONNECTED_CLIENTS.clear()
    async with websockets.serve(main2.ws_handler, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        return await coro_fn(port)


class TestFinding01WebSocketRevocation(unittest.TestCase):
    """FINDING-01 : Révocation effective des connexions WebSocket actives et protection TOCTOU."""

    def setUp(self):
        main2.CONNECTED_CLIENTS.clear()

    def test_active_ws_closed_immediately_on_revoke_and_multi_conn_isolated(self):
        sid_a = "f01-sess-a"
        tok_a = "f01-tok-a"
        sid_b = "f01-sess-b"
        tok_b = "f01-tok-b"
        main2.WS_SESSION_MANAGER.register_session(sid_a, tok_a, client_type="mobile", client_ip="203.0.113.10", role="OWNER")
        main2.WS_SESSION_MANAGER.register_session(sid_b, tok_b, client_type="mobile", client_ip="203.0.113.11", role="OWNER")

        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }

        async def scenario(port):
            hdr_a = {"Origin": "https://alice.example.com", "X-Forwarded-For": "203.0.113.10", "Cookie": f"alice_session={sid_a}:{tok_a}"}
            hdr_b = {"Origin": "https://alice.example.com", "X-Forwarded-For": "203.0.113.11", "Cookie": f"alice_session={sid_b}:{tok_b}"}

            # Deux connexions simultanées sur la session A + une connexion sur la session B
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr_a) as ws_a1, \
                       websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr_a) as ws_a2, \
                       websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr_b) as ws_b:
                self.assertEqual(json.loads(await asyncio.wait_for(ws_a1.recv(), 3.0))["type"], "auth_ok")
                self.assertEqual(json.loads(await asyncio.wait_for(ws_a2.recv(), 3.0))["type"], "auth_ok")
                self.assertEqual(json.loads(await asyncio.wait_for(ws_b.recv(), 3.0))["type"], "auth_ok")
                self.assertEqual(len(main2.CONNECTED_CLIENTS), 3)

                # Révocation de la session A depuis un thread externe (comme /api/revoke_session)
                revoked = await asyncio.to_thread(main2.WS_SESSION_MANAGER.revoke_session, sid_a, tok_a)
                self.assertTrue(revoked)

                # Les deux connexions A doivent être fermées (4001) et retirées de CONNECTED_CLIENTS
                for ws_a in (ws_a1, ws_a2):
                    with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx:
                        await asyncio.wait_for(ws_a.recv(), timeout=3.0)
                    self.assertEqual(ctx.exception.rcvd.code, 4001)

                self.assertFalse(any(getattr(w, "session_id", None) == sid_a for w in main2.CONNECTED_CLIENTS))
                # La session B reste active et opérationnelle
                self.assertTrue(any(getattr(w, "session_id", None) == sid_b for w in main2.CONNECTED_CLIENTS))
                await ws_b.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(0.1)
                self.assertTrue(main2.WS_SESSION_MANAGER.is_session_active(sid_b, tok_b))

                # Reconnexion avec l'ancien token A -> rejetée 4001
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr_a) as ws_reconn:
                    with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx_r:
                        await asyncio.wait_for(ws_reconn.recv(), timeout=6.5)
                    self.assertEqual(ctx_r.exception.rcvd.code, 4001)

        try:
            with patch.dict(os.environ, env, clear=True):
                asyncio.run(_with_ws_server(scenario))
        finally:
            main2.WS_SESSION_MANAGER.revoke_session(sid_a, tok_a)
            main2.WS_SESSION_MANAGER.revoke_session(sid_b, tok_b)

    def test_no_privileged_action_or_identity_switch_after_revocation(self):
        sid = "f01-cmd-rev"
        tok = "f01-tok-rev"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, client_type="mobile", client_ip="203.0.113.12", role="OWNER")
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }

        async def scenario(port):
            hdr = {"Origin": "https://alice.example.com", "X-Forwarded-For": "203.0.113.12", "Cookie": f"alice_session={sid}:{tok}"}
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr) as ws:
                self.assertEqual(json.loads(await asyncio.wait_for(ws.recv(), 3.0))["type"], "auth_ok")
                # Tentative de changement d'identité en cours de vie -> rejet 4001
                await ws.send(json.dumps({"type": "auth", "session_id": "desktop_local", "token": main2.WS_SESSION_MANAGER.desktop_token}))
                msg = json.loads(await asyncio.wait_for(ws.recv(), 3.0))
                self.assertEqual(msg["type"], "auth_error")
                with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx:
                    await asyncio.wait_for(ws.recv(), timeout=3.0)
                self.assertEqual(ctx.exception.rcvd.code, 4001)

        try:
            with patch.dict(os.environ, env, clear=True):
                asyncio.run(_with_ws_server(scenario))
        finally:
            main2.WS_SESSION_MANAGER.revoke_session(sid, tok)


class TestFinding02MobileWssRouting(unittest.TestCase):
    """FINDING-02 : Validation réelle via Node de buildWebSocketUrl() dans mobile/app.js."""

    def _eval_js_url(self, loc_js, cfg_js="{}"):
        app_js_path = os.path.join(PROJECT_ROOT, "mobile", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            src = f.read()
        # Extraire la définition exacte de buildWebSocketUrl depuis mobile/app.js
        m = re.search(r"(function buildWebSocketUrl\b[\s\S]*?\n\})", src)
        self.assertIsNotNone(m, "buildWebSocketUrl introuvable dans mobile/app.js")
        fn_code = m.group(1)
        script = f"""
{fn_code}
try {{
  const url = buildWebSocketUrl({loc_js}, {cfg_js});
  console.log(JSON.stringify({{ok: true, url}}));
}} catch (e) {{
  console.log(JSON.stringify({{ok: false, error: e.message}}));
}}
"""
        res = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        return json.loads(res.stdout.strip())

    def test_production_https_uses_wss_and_ws_path_never_8765(self):
        r = self._eval_js_url("{protocol: 'https:', hostname: 'alice.example.com', host: 'alice.example.com', pathname: '/'}", "{env: 'production'}")
        self.assertTrue(r["ok"])
        self.assertEqual(r["url"], "wss://alice.example.com/ws")
        self.assertNotIn("8765", r["url"])

    def test_production_http_refused_no_ws_fallback(self):
        r = self._eval_js_url("{protocol: 'http:', hostname: 'alice.example.com', host: 'alice.example.com', pathname: '/'}", "{env: 'production'}")
        self.assertFalse(r["ok"])

    def test_local_dev_http_allowed(self):
        r = self._eval_js_url("{protocol: 'http:', hostname: 'localhost', host: 'localhost:8080', pathname: '/'}", "{}")
        self.assertTrue(r["ok"])
        self.assertEqual(r["url"], "ws://localhost:8765")

    def test_https_base_path_and_trailing_slash_no_double_slash(self):
        r1 = self._eval_js_url("{protocol: 'https:', hostname: 'alice.example.com', host: 'alice.example.com', pathname: '/alice'}", "{env: 'production'}")
        r2 = self._eval_js_url("{protocol: 'https:', hostname: 'alice.example.com', host: 'alice.example.com', pathname: '/alice/'}", "{env: 'production'}")
        r3 = self._eval_js_url("{protocol: 'https:', hostname: 'alice.example.com', host: 'alice.example.com', pathname: '/alice/index.html'}", "{env: 'production'}")
        for r in (r1, r2, r3):
            self.assertTrue(r["ok"])
            self.assertEqual(r["url"], "wss://alice.example.com/alice/ws")

    def test_missing_config_fails_explicitly(self):
        r = self._eval_js_url("null", "{}")
        self.assertFalse(r["ok"])

    def test_service_worker_excludes_api_routes(self):
        sw_path = os.path.join(PROJECT_ROOT, "mobile", "sw.js")
        with open(sw_path, "r", encoding="utf-8") as f:
            sw = f.read()
        self.assertIn('url.pathname.startsWith("/api/")', sw)


class TestFinding03RBACStrictFailClosed(unittest.TestCase):
    """FINDING-03 : RBAC strictement fail-closed & couverture complète des call sites."""

    def setUp(self):
        self.sid_owner = "f03-owner"
        self.sid_guest = "f03-guest"
        RBAC.register_principal(self.sid_owner, "u_owner", Role.OWNER)
        RBAC.register_principal(self.sid_guest, "u_guest", Role.GUEST)

    def tearDown(self):
        RBAC.revoke_principal(self.sid_owner)
        RBAC.revoke_principal(self.sid_guest)

    def test_unknown_empty_none_unmapped_actions_denied_even_for_owner(self):
        for bad in ("unknown_action_xyz", "eteindre_pc", "", "   ", None, 123):
            ok_g, _ = RBAC.check_action(self.sid_guest, bad)
            ok_o, _ = RBAC.check_action(self.sid_owner, bad)
            self.assertFalse(ok_g, f"GUEST should be denied for {bad!r}")
            self.assertFalse(ok_o, f"OWNER should be denied for unmapped/invalid {bad!r}")

    def test_case_and_spaces_normalized_safely(self):
        ok_g, _ = RBAC.check_action(self.sid_guest, "  SHUTDOWN ")
        self.assertFalse(ok_g)
        ok_o, _ = RBAC.check_action(self.sid_owner, "  SHUTDOWN ")
        self.assertTrue(ok_o)

    def test_unknown_role_and_unknown_permission_denied(self):
        bad_principal = UserPrincipal(user_id="u_bad", role="SUPER_HACKER", session_id="s_bad")
        ok_role, _ = RBAC.authorize(bad_principal, "system", "shutdown")
        self.assertFalse(ok_role)
        owner_p = RBAC.get_principal(self.sid_owner)
        ok_perm, _ = RBAC.authorize(owner_p, "nonexistent_res", "nonexistent_act")
        self.assertFalse(ok_perm)

    def test_all_main2_actions_covered_by_rbac(self):
        main2_path = os.path.join(PROJECT_ROOT, "main2.py")
        with open(main2_path, "r", encoding="utf-8") as f:
            src = f.read()
        found = set(re.findall(r'\belif action == "([^"]+)"|\bif action == "([^"]+)"', src))
        actions = {a or b for a, b in found if (a or b)}
        covered = set(ACTION_TO_PERMISSION.keys()) | set(PUBLIC_CONVERSATIONAL_ACTIONS)
        missing = actions - covered
        self.assertEqual(missing, set(), f"Actions non couvertes par RBAC dans main2.py : {missing}")


class TestFinding06ProxyHeadersAndVerifyToken(unittest.TestCase):
    """FINDING-06 : Rejet XFF dupliqués/ambigus et correction de verify_token."""

    def test_duplicate_xff_headers_rejected(self):
        env = {"ALICE_TRUSTED_PROXIES": "127.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            hdrs = MultiHeaderMock([
                ("X-Forwarded-For", "203.0.113.10"),
                ("X-Forwarded-For", "198.51.100.20"),
            ])
            ip = main2.get_trusted_client_ip({"headers": hdrs}, ("127.0.0.1", 5000))
            self.assertEqual(ip, "127.0.0.1")

    def test_empty_entry_in_xff_chain_rejected(self):
        env = {"ALICE_TRUSTED_PROXIES": "127.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            ip = main2.get_trusted_client_ip({"headers": {"X-Forwarded-For": "203.0.113.10, "}}, ("127.0.0.1", 5000))
            self.assertEqual(ip, "127.0.0.1")

    def test_ipv4_mapped_ipv6_normalized_in_xff(self):
        env = {"ALICE_TRUSTED_PROXIES": "127.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            ip = main2.get_trusted_client_ip({"headers": {"X-Forwarded-For": "::ffff:203.0.113.44"}}, ("127.0.0.1", 5000))
            self.assertEqual(ip, "203.0.113.44")

    def test_verify_token_removed_and_ws_auth_revalidation_paths(self):
        main2_path = os.path.join(PROJECT_ROOT, "main2.py")
        with open(main2_path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("verify_token", src)

        sid = "f06-auth-sid"
        tok = "f06-auth-tok"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, client_type="mobile", client_ip="203.0.113.10", role="OWNER")
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }

        async def scenario(port):
            hdr = {"Origin": "https://alice.example.com", "X-Forwarded-For": "203.0.113.10"}
            # 1. Auth frame valide puis auth répété valide
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=hdr) as ws:
                await ws.send(json.dumps({"type": "auth", "session_id": sid, "token": tok}))
                self.assertEqual(json.loads(await asyncio.wait_for(ws.recv(), 3.0))["type"], "auth_ok")
                await ws.send(json.dumps({"type": "auth", "session_id": sid, "token": tok}))
                self.assertEqual(json.loads(await asyncio.wait_for(ws.recv(), 3.0))["type"], "auth_ok")
                # Auth répété avec mauvais token -> rejet 4001
                await ws.send(json.dumps({"type": "auth", "session_id": sid, "token": "wrong"}))
                self.assertEqual(json.loads(await asyncio.wait_for(ws.recv(), 3.0))["type"], "auth_error")
                with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx:
                    await asyncio.wait_for(ws.recv(), timeout=3.0)
                self.assertEqual(ctx.exception.rcvd.code, 4001)

        try:
            with patch.dict(os.environ, env, clear=True):
                asyncio.run(_with_ws_server(scenario))
        finally:
            main2.WS_SESSION_MANAGER.revoke_session(sid, tok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
