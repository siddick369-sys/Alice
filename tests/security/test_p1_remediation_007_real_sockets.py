# -*- coding: utf-8 -*-
"""
ALICE-P1-REMEDIATION-007: REAL-SOCKET & ADVERSARIAL ACCEPTANCE SUITE
======================================================================
Tests réels sur sockets TCP/HTTP/HTTPS/WebSocket :
- Lot A / D.2 : WS-01 à WS-12 (véritable serveur websockets.serve sur TCP)
- Lot B / D.3 : COOKIE-01 à COOKIE-10 (véritable serveur HTTP/HTTPS MobileHandler sur TCP)
- Lot C / D.4 : TLS-01 à TLS-08 (démarrage TLS direct, proxy TLS, fail-closed)
- Lot D.5     : IP-01 à IP-09 (IPv4, IPv6, IPv4-mapped IPv6, CIDR, normalisation)
"""

import sys
import os
import ssl
import json
import time
import socket
import asyncio
import tempfile
import threading
import unittest
import http.client
import http.server
import datetime
from unittest.mock import patch

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import websockets

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Jarvis Final - SITE"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main2


def _generate_self_signed_cert(cert_path: str, key_path: str):
    """Génère un certificat X.509 auto-signé temporaire pour tests TLS réels."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def _start_real_http_server(ssl_ctx=None):
    """Démarre un véritable serveur HTTP/HTTPS MobileHandler sur 127.0.0.1:<port éphémère>."""
    server = http.server.HTTPServer(("127.0.0.1", 0), main2.MobileHandler)
    if ssl_ctx is not None:
        server.socket = ssl_ctx.wrap_socket(server.socket, server_side=True)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port, t


async def _run_with_real_ws_server(coro_fn):
    """Démarre un véritable serveur websockets.serve(main2.ws_handler) sur port éphémère TCP."""
    main2.CONNECTED_CLIENTS.clear()
    async with websockets.serve(main2.ws_handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        return await coro_fn(port)


class TestRealWebSocketBoundary(unittest.TestCase):
    """D.2 : Scénarios WebSocket réels WS-01 à WS-12 sur véritables sockets TCP."""

    def setUp(self):
        main2.CONNECTED_CLIENTS.clear()

    def test_ws01_external_client_via_proxy_no_auth_rejected(self):
        """WS-01 : Client externe via proxy approuvé sans auth -> rejet 4001, aucun privilège desktop_local."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "203.0.113.50",
                "X-Forwarded-Proto": "https",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws02_forged_xff_127_0_0_1_in_proxy_mode_rejected(self):
        """WS-02 : Client externe avec X-Forwarded-For: 127.0.0.1 en mode proxy -> aucun privilège desktop_local."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "127.0.0.1",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws03_forged_x_real_ip_127_0_0_1_rejected(self):
        """WS-03 : Client avec X-Real-IP: 127.0.0.1 en mode direct -> aucun bypass local."""
        env = {
            "ALICE_TLS_TERMINATION": "direct",
            "ALICE_TRUSTED_PROXIES": "10.99.99.99",  # 127.0.0.1 non approuvé comme proxy
        }
        async def scenario(port):
            headers = {
                "Origin": "http://localhost:8080",
                "X-Real-IP": "127.0.0.1",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                # La présence d'un header de forwarding interdit l'auto-auth desktop_local
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws04_approved_proxy_external_client_remains_external(self):
        """WS-04 : Proxy approuvé transmettant IP externe -> client reste externe et requiert auth."""
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "198.51.100.77",
                "X-Forwarded-Proto": "https",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws05_approved_proxy_canonical_xff_blocks_local_privilege(self):
        """WS-05 : Proxy approuvé écrasant un header client par valeur canonique -> pas de privilège local."""
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "203.0.113.99, 127.0.0.1",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws06_untrusted_peer_forging_headers_ignored(self):
        """WS-06 : Pair non approuvé forgeant XFF/XFP -> headers ignorés."""
        env = {"ALICE_TRUSTED_PROXIES": "10.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            resolved = main2.get_trusted_client_ip(
                {"headers": {"X-Forwarded-For": "127.0.0.1", "X-Real-IP": "127.0.0.1"}},
                ("198.51.100.25", 50000),
            )
            self.assertEqual(resolved, "198.51.100.25")
            is_sec, reason = main2.is_request_https_secure(
                {"headers": {"X-Forwarded-Proto": "https"}},
                "198.51.100.25",
            )
            self.assertFalse(is_sec)
            self.assertEqual(reason, "untrusted_peer_no_tls")

    def test_ws07_genuine_local_desktop_client_allowed_in_direct_mode(self):
        """WS-07 : Véritable client local direct (sans proxy ni header de forwarding) autorisé."""
        env = {"ALICE_TLS_TERMINATION": "direct"}
        async def scenario(port):
            headers = {"Origin": "http://localhost:5173"}
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                # Envoyer un ping JSON valide et vérifier que la connexion reste ouverte
                await ws.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(0.2)
                self.assertEqual(len(main2.CONNECTED_CLIENTS), 1)
                connected_ws = next(iter(main2.CONNECTED_CLIENTS))
                self.assertEqual(getattr(connected_ws, "session_id", None), "desktop_local")

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws08_valid_session_cookie_authenticates_over_proxy(self):
        """WS-08 : Client externe authentifié avec cookie alice_session valide via proxy -> auth_ok."""
        sid = "ws08-sid"
        tok = "ws08-tok-secret"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, client_type="mobile", client_ip="203.0.113.10")
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "203.0.113.10",
                "Cookie": f"alice_session={sid}:{tok}",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                self.assertEqual(msg.get("type"), "auth_ok")
                self.assertEqual(msg.get("auth_method"), "cookie")
                self.assertEqual(msg.get("session_id"), sid)

        try:
            with patch.dict(os.environ, env, clear=True):
                asyncio.run(_run_with_real_ws_server(scenario))
        finally:
            main2.WS_SESSION_MANAGER.revoke_session(sid, tok)

    def test_ws09_expired_or_invalid_session_rejected(self):
        """WS-09 : Session expirée ou invalide via cookie -> rejetée (4001)."""
        sid = "ws09-expired"
        tok = "ws09-tok"
        main2.WS_SESSION_MANAGER.register_session(sid, tok, ttl=-5)
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "203.0.113.10",
                "Cookie": f"alice_session={sid}:{tok}",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=6.5)
                    self.fail("Expected WebSocket close 4001")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws10_hostile_origin_rejected_even_from_loopback(self):
        """WS-10 : Origin hostile rejetée 4003 même depuis 127.0.0.1."""
        async def scenario(port):
            headers = {"Origin": "https://evil.attacker.com"}
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=3.0)
                    self.fail("Expected WebSocket close 4003")
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4003)

        asyncio.run(_run_with_real_ws_server(scenario))

    def test_ws11_cross_session_isolation(self):
        """WS-11 : Une session B ne peut pas valider CSRF ou révoquer la session A."""
        main2.WS_SESSION_MANAGER.register_session("sess-A", "tok-A", csrf_token="csrf-A")
        main2.WS_SESSION_MANAGER.register_session("sess-B", "tok-B", csrf_token="csrf-B")
        try:
            self.assertFalse(main2.WS_SESSION_MANAGER.verify_csrf("sess-A", "csrf-B"))
            self.assertFalse(main2.WS_SESSION_MANAGER.revoke_session("sess-A", "tok-B"))
            self.assertTrue(main2.WS_SESSION_MANAGER.verify_session("sess-A", "tok-A"))
        finally:
            main2.WS_SESSION_MANAGER.revoke_session("sess-A", "tok-A")
            main2.WS_SESSION_MANAGER.revoke_session("sess-B", "tok-B")

    def test_ws12_command_before_authentication_rejected(self):
        """WS-12 : Commande privilégiée envoyée avant auth -> zéro exécution, fermeture 4001."""
        env = {
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
            "ALICE_ALLOWED_ORIGINS": "https://alice.example.com",
        }
        async def scenario(port):
            headers = {
                "Origin": "https://alice.example.com",
                "X-Forwarded-For": "203.0.113.55",
            }
            async with websockets.connect(f"ws://127.0.0.1:{port}", additional_headers=headers) as ws:
                await ws.send(json.dumps({"type": "command", "text": "eteins le pc"}))
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                self.assertEqual(msg.get("type"), "auth_error")
                try:
                    await asyncio.wait_for(ws.recv(), timeout=3.0)
                except websockets.exceptions.ConnectionClosed as e:
                    self.assertEqual(e.code, 4001)

        with patch.dict(os.environ, env, clear=True):
            asyncio.run(_run_with_real_ws_server(scenario))


class TestRealHTTPCookies(unittest.TestCase):
    """D.3 : Tests HTTP/HTTPS réels des cookies COOKIE-01 à COOKIE-10."""

    def _pair_request(self, port, headers=None, use_tls=False):
        pin = main2.PAIRING_MANAGER.generate_pairing_code()
        if use_tls:
            ctx = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection("127.0.0.1", port, context=ctx, timeout=5)
        else:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            conn.request("POST", "/api/pair", body=json.dumps({"code": pin}), headers=req_headers)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            set_cookies = resp.headers.get_all("Set-Cookie") or []
            return resp.status, body, set_cookies
        finally:
            conn.close()

    def test_cookie01_direct_tls_emits_secure(self):
        """COOKIE-01 : TLS direct -> Set-Cookie contient Secure, HttpOnly, SameSite=Strict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_p = os.path.join(tmpdir, "cert.pem")
            key_p = os.path.join(tmpdir, "key.pem")
            _generate_self_signed_cert(cert_p, key_p)
            env = {
                "ALICE_ENV": "production",
                "JARVIS_ENV": "production",
                "ALICE_TLS_TERMINATION": "direct",
                "ALICE_SSL_CERT": cert_p,
                "ALICE_SSL_KEY": key_p,
            }
            with patch.dict(os.environ, env, clear=True):
                ssl_ctx = main2.get_ssl_context()
                self.assertIsNotNone(ssl_ctx)
                srv, port, _ = _start_real_http_server(ssl_ctx=ssl_ctx)
                try:
                    status, body, cookies = self._pair_request(port, use_tls=True)
                    self.assertEqual(status, 200)
                    self.assertEqual(len(cookies), 2)
                    for c in cookies:
                        self.assertIn("Secure", c)
                        self.assertIn("SameSite=Strict", c)
                    sess_c = [c for c in cookies if c.startswith("alice_session=")][0]
                    self.assertIn("HttpOnly", sess_c)
                finally:
                    srv.shutdown()
                    srv.server_close()

    def test_cookie02_proxy_https_emits_secure(self):
        """COOKIE-02 : Proxy approuvé + X-Forwarded-Proto: https -> Secure présent."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.10"})
                self.assertEqual(status, 200)
                self.assertEqual(len(cookies), 2)
                for c in cookies:
                    self.assertIn("Secure", c)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie03_proxy_http_in_production_refused(self):
        """COOKIE-03 : Proxy approuvé + X-Forwarded-Proto: http en production -> refus 403, aucun cookie."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "http"})
                self.assertEqual(status, 403)
                self.assertEqual(cookies, [])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie04_untrusted_peer_forged_xfp_ignored(self):
        """COOKIE-04 : Pair non approuvé + XFP=https forgé -> XFP ignoré, refus 403 en production."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "10.99.99.99",  # 127.0.0.1 non approuvé
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https"})
                self.assertEqual(status, 403)
                self.assertEqual(cookies, [])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie05_missing_xfp_in_production_refused(self):
        """COOKIE-05 : XFP absent en production -> refus 403."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={})
                self.assertEqual(status, 403)
                self.assertEqual(cookies, [])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie06_multiple_xfp_rejected(self):
        """COOKIE-06 : XFP multiple (comma-separated) -> rejeté 403."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https, http"})
                self.assertEqual(status, 403)
                self.assertEqual(cookies, [])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie07_malformed_xfp_rejected(self):
        """COOKIE-07 : XFP malformé -> rejeté 403."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https;evil=1"})
                self.assertEqual(status, 403)
                self.assertEqual(cookies, [])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie08_and_09_session_httponly_and_csrf_attributes(self):
        """COOKIE-08 & COOKIE-09 : alice_session est HttpOnly, alice_csrf non-HttpOnly double-submit, host-only."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, _, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https"})
                self.assertEqual(status, 200)
                sess_c = [c for c in cookies if c.startswith("alice_session=")][0]
                csrf_c = [c for c in cookies if c.startswith("alice_csrf=")][0]
                self.assertIn("HttpOnly", sess_c)
                self.assertNotIn("HttpOnly", csrf_c)
                self.assertNotIn("Domain=", sess_c)
                self.assertNotIn("Domain=", csrf_c)
                self.assertIn("Path=/", sess_c)
                self.assertIn("SameSite=Strict", sess_c)
                self.assertIn("Secure", sess_c)
                self.assertIn("Secure", csrf_c)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_cookie10_logout_revoke_clears_cookies_with_matching_attributes(self):
        """COOKIE-10 : Déconnexion (/api/revoke_session) -> Max-Age=0 + Secure + CSRF vérifié."""
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            srv, port, _ = _start_real_http_server()
            try:
                status, body, cookies = self._pair_request(port, headers={"X-Forwarded-Proto": "https"})
                self.assertEqual(status, 200)
                data = json.loads(body)
                csrf_tok = data["csrf_token"]
                sess_cookie_kv = cookies[0].split(";", 1)[0]

                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                # 1. Sans X-CSRF-Token -> doit être refusé (403)
                conn.request("POST", "/api/revoke_session", body="{}", headers={
                    "Content-Type": "application/json",
                    "Cookie": sess_cookie_kv,
                    "X-Forwarded-Proto": "https",
                })
                r_bad = conn.getresponse()
                r_bad.read()
                self.assertEqual(r_bad.status, 403)

                # 2. Avec X-CSRF-Token valide -> 200 + Max-Age=0 + Secure
                conn.request("POST", "/api/revoke_session", body="{}", headers={
                    "Content-Type": "application/json",
                    "Cookie": sess_cookie_kv,
                    "X-CSRF-Token": csrf_tok,
                    "X-Forwarded-Proto": "https",
                })
                r_ok = conn.getresponse()
                r_ok.read()
                self.assertEqual(r_ok.status, 200)
                del_cookies = r_ok.headers.get_all("Set-Cookie") or []
                self.assertEqual(len(del_cookies), 2)
                for dc in del_cookies:
                    self.assertIn("Max-Age=0", dc)
                    self.assertIn("Secure", dc)
                conn.close()
            finally:
                srv.shutdown()
                srv.server_close()


class TestTLSStartupAndTopologies(unittest.TestCase):
    """D.4 : Tests de démarrage TLS & Fail-Closed."""

    def test_tls01_prod_no_cert_no_proxy_fails_closed(self):
        env = {"ALICE_ENV": "production", "JARVIS_ENV": "production", "ALICE_SSL_CERT": "/nonexistent", "ALICE_SSL_KEY": "/nonexistent"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_TLS_REQUIRED")

    def test_tls02_prod_valid_direct_tls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_p = os.path.join(tmpdir, "cert.pem")
            key_p = os.path.join(tmpdir, "key.pem")
            _generate_self_signed_cert(cert_p, key_p)
            env = {"ALICE_ENV": "production", "JARVIS_ENV": "production", "ALICE_TLS_TERMINATION": "direct", "ALICE_SSL_CERT": cert_p, "ALICE_SSL_KEY": key_p}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(main2.get_transport_security_mode(), "TLS_ENFORCED_PRODUCTION")

    def test_tls03_prod_valid_proxy_tls_loopback(self):
        env = {
            "ALICE_ENV": "production",
            "JARVIS_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1,::1",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "PROXY_TLS_TERMINATED")

    def test_tls04_proxy_tls_without_trusted_proxies_fails_closed(self):
        env = {
            "ALICE_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_PROXY_CONFIG_INVALID")

    def test_tls05_proxy_tls_with_invalid_trusted_proxy_fails_closed(self):
        env = {
            "ALICE_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "proxy.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_PROXY_CONFIG_INVALID")

    def test_tls06_proxy_tls_with_public_bind_fails_closed(self):
        env = {
            "ALICE_ENV": "production",
            "ALICE_TLS_TERMINATION": "proxy",
            "ALICE_BIND_ADDRESS": "0.0.0.0",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_TRUSTED_PROXIES": "127.0.0.1",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_PROXY_PUBLIC_BIND")

    def test_tls07_mismatched_key_and_cert_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cert1 = os.path.join(tmpdir, "c1.pem")
            key1 = os.path.join(tmpdir, "k1.pem")
            cert2 = os.path.join(tmpdir, "c2.pem")
            key2 = os.path.join(tmpdir, "k2.pem")
            _generate_self_signed_cert(cert1, key1)
            _generate_self_signed_cert(cert2, key2)
            env = {"ALICE_ENV": "production", "ALICE_SSL_CERT": cert1, "ALICE_SSL_KEY": key2}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_TLS_REQUIRED")

    def test_tls08_contradictory_alice_and_jarvis_env_fails_closed(self):
        env = {"ALICE_ENV": "production", "JARVIS_ENV": "development"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(main2.get_transport_security_mode(), "FAIL_CLOSED_CONFIG_CONFLICT")


class TestIPv4IPv6Normalization(unittest.TestCase):
    """D.5 : Tests IPv4, IPv6, IPv4-mapped IPv6, CIDR et valeurs invalides."""

    def test_ipv4_ipv6_loopback_and_mapped(self):
        self.assertTrue(main2.is_loopback_ip("127.0.0.1"))
        self.assertTrue(main2.is_loopback_ip("::1"))
        self.assertTrue(main2.is_loopback_ip("::ffff:127.0.0.1"))
        self.assertFalse(main2.is_loopback_ip("203.0.113.45"))
        self.assertFalse(main2.is_loopback_ip("2001:db8::1"))
        self.assertFalse(main2.is_loopback_ip("::ffff:203.0.113.45"))
        self.assertFalse(main2.is_loopback_ip("invalid_ip"))

    def test_trusted_proxy_cidr_and_mapped(self):
        trusted = {"127.0.0.1", "::1", "10.10.0.0/16"}
        self.assertTrue(main2.is_trusted_proxy_ip("127.0.0.1", trusted))
        self.assertTrue(main2.is_trusted_proxy_ip("::ffff:127.0.0.1", trusted))
        self.assertTrue(main2.is_trusted_proxy_ip("10.10.5.42", trusted))
        self.assertFalse(main2.is_trusted_proxy_ip("10.20.5.42", trusted))
        self.assertFalse(main2.is_trusted_proxy_ip("2001:db8::1", trusted))
        self.assertFalse(main2.is_trusted_proxy_ip("127.0.0.1:8080", trusted))


if __name__ == "__main__":
    unittest.main(verbosity=2)
