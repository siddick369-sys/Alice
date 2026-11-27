"""
Test Suite de Remédiation et de Validation Adversariale — Mission 014
Vérifie F013-01 (Protocole WebSocket et cohérence des états),
F013-02 (Bindings réseau Mode A / Mode B),
et F013-03 (Cycle de vie et arrêt propre).
"""
import os
import sys
import json
import time
import asyncio
import unittest
import socket
from unittest.mock import patch

# Ajout du dossier source au path
SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Jarvis Final - SITE")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

import websockets
import main2

def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

async def _run_ws_server(handler, port, bind_address="127.0.0.1"):
    server = await websockets.serve(handler, bind_address, port, max_size=15 * 1024 * 1024)
    return server

class TestRemediation014NetworkBindings(unittest.TestCase):
    """Validation de F013-02 : Sécurisation et sélection des modes de binding réseau."""

    def test_mode_a_localhost_via_bind_mode(self):
        env = {"ALICE_BIND_MODE": "LOCALHOST"}
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "127.0.0.1")
            self.assertEqual(cfg.ws_host, "127.0.0.1")

    def test_mode_a_localhost_via_bind_address(self):
        env = {"ALICE_BIND_ADDRESS": "127.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "127.0.0.1")
            self.assertEqual(cfg.ws_host, "127.0.0.1")

    def test_mode_b_lan_via_bind_mode(self):
        env = {"ALICE_BIND_MODE": "LAN"}
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "0.0.0.0")
            self.assertEqual(cfg.ws_host, "0.0.0.0")

    def test_mode_b_lan_via_lan_access_flag(self):
        env = {"ALICE_LAN_ACCESS": "1"}
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "0.0.0.0")
            self.assertEqual(cfg.ws_host, "0.0.0.0")

    def test_backward_compatibility_empty_env(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "0.0.0.0")
            self.assertEqual(cfg.ws_host, "0.0.0.0")


class TestRemediation014WebSocketProtocol(unittest.TestCase):
    """Validation de F013-01 : Cohérence du protocole WebSocket, messages auth_ok, RBAC et révocations."""

    def setUp(self):
        main2.CONNECTED_CLIENTS.clear()

    def tearDown(self):
        main2.CONNECTED_CLIENTS.clear()

    def test_ws_desktop_local_receives_explicit_auth_ok(self):
        """Desktop loopback (Vite 5173) reçoit un message auth_ok explicite dès la connexion."""
        port = _get_free_port()

        async def scenario():
            server = await _run_ws_server(main2.ws_handler, port)
            try:
                headers = {"Origin": "http://localhost:5173"}
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    resp = json.loads(raw_resp)
                    self.assertEqual(resp.get("type"), "auth_ok")
                    self.assertEqual(resp.get("session_id"), "desktop_local")
                    self.assertEqual(resp.get("role"), "OWNER")
                    self.assertEqual(resp.get("auth_method"), "desktop_local")
                    self.assertEqual(len(main2.CONNECTED_CLIENTS), 1)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())

    def test_ws_cookie_auth_has_priority_and_emits_auth_ok(self):
        """Une session avec cookie alice_session prime et émet auth_ok avec son identité propre."""
        port = _get_free_port()
        sid = "sess-cookie-014"
        tok = "tok-secret-014"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, client_type="mobile", client_ip="127.0.0.1", role="MEMBER")

        async def scenario():
            server = await _run_ws_server(main2.ws_handler, port)
            try:
                headers = {
                    "Origin": "http://localhost:8080",
                    "Cookie": f"alice_session={sid}:{tok}"
                }
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    resp = json.loads(raw_resp)
                    self.assertEqual(resp.get("type"), "auth_ok")
                    self.assertEqual(resp.get("session_id"), sid)
                    self.assertEqual(resp.get("auth_method"), "cookie")
                    self.assertEqual(resp.get("role"), "MEMBER")
                    self.assertNotEqual(resp.get("session_id"), "desktop_local")
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())

    def test_ws_mobile_loopback_without_cookie_requires_pairing_or_auth(self):
        """Une connexion loopback issue de l'interface mobile (:8080) sans cookie n'est pas promue desktop_local."""
        port = _get_free_port()

        async def scenario():
            server = await _run_ws_server(main2.ws_handler, port)
            try:
                headers = {"Origin": "http://localhost:8080"}
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                    # Ne reçoit pas d'auth_ok automatique
                    # Envoie un token invalide -> doit être rejeté 4001
                    await ws.send(json.dumps({"type": "auth", "session_id": "fake", "token": "wrong"}))
                    err_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                    self.assertEqual(err_resp.get("type"), "auth_error")
                    # La connexion doit se fermer avec le code 4001
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except websockets.exceptions.ConnectionClosed as cc:
                        self.assertEqual(cc.code, 4001)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())

    def test_ws_session_revocation_immediately_terminates_socket(self):
        """La révocation d'une session en cours ferme immédiatement la socket WebSocket."""
        port = _get_free_port()
        sid = "sess-revoc-014"
        tok = "tok-revoc-014"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, client_type="mobile", client_ip="127.0.0.1")

        async def scenario():
            server = await _run_ws_server(main2.ws_handler, port)
            try:
                headers = {"Cookie": f"alice_session={sid}:{tok}"}
                async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                    ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                    self.assertEqual(ack.get("type"), "auth_ok")

                    # Révocation de la session côté serveur
                    main2.WS_SESSION_MANAGER.revoke_session(sid)

                    # Le client tente d'envoyer un message
                    await ws.send(json.dumps({"type": "ping"}))
                    # Doit recevoir auth_error et être déconnecté
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                        self.assertEqual(msg.get("type"), "auth_error")
                    except websockets.exceptions.ConnectionClosed as cc:
                        self.assertEqual(cc.code, 4001)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())

    def test_ws_unauthorized_origin_rejected_4003(self):
        """Une origine non autorisée est immédiatement rejetée avec le code 4003."""
        port = _get_free_port()

        async def scenario():
            server = await _run_ws_server(main2.ws_handler, port)
            try:
                headers = {"Origin": "https://malicious-website.com"}
                try:
                    async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                        await ws.recv()
                    self.fail("Connexion aurait dû être rejetée avec 4003")
                except websockets.exceptions.InvalidStatusCode as e:
                    self.assertEqual(e.status_code, 403)
                except websockets.exceptions.ConnectionClosed as cc:
                    self.assertEqual(cc.code, 4003)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(scenario())


class TestRemediation014ProcessLifecycle(unittest.TestCase):
    """Validation de F013-03 : Mécanisme d'arrêt propre et libération des ports."""

    def test_stop_alice_runtime_idempotent(self):
        """stop_alice_runtime() est idempotent et n'engendre aucune exception si appelé plusieurs fois."""
        try:
            main2.stop_alice_runtime()
            main2.stop_alice_runtime()
        except Exception as e:
            self.fail(f"stop_alice_runtime a levé une exception inattendue : {e}")

    def test_stop_alice_script_port_check_utility(self):
        """L'utilitaire stop_alice vérifie correctement que les ports inoccupés sont libres."""
        import stop_alice
        for p in stop_alice.PORTS:
            free = stop_alice.check_port_free(p)
            self.assertTrue(free, f"Le port {p} devrait être libre avant test")

if __name__ == "__main__":
    unittest.main()
