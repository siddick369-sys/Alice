# -*- coding: utf-8 -*-
"""
ALICE-P1-PRODUCTION-EXPOSURE-HARDENING-006: ADVERSARIAL TEST SUITE
==================================================================
Comprehensive test suite verifying P1 security remediations:
- B1: Network binding configurations (IPv4/IPv6, port ranges, collision detection)
- B2: Reverse proxy header spoofing & IP extraction (XFF, X-Real-IP, CF, RFC 7239)
- B3: Frontend XSS sink audit & CSP header validation
- B4: Session cookie architecture (HttpOnly, SameSite, CSRF protection, WS cookie auth)
- B5: Session revocation & lifetime management
- B6: Dynamic origin port validation
"""

import sys
import os
import unittest
import json
import ipaddress
import http.client
from unittest.mock import MagicMock, patch

# Add main project path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Jarvis Final - SITE"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main2


class MockReqHandler:
    def __init__(self, headers):
        self.headers = headers


class TestNetworkBindingConfig(unittest.TestCase):
    """B1: Tests for NetworkConfig and binding environment parsing."""

    def test_default_network_config(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "0.0.0.0")
            self.assertEqual(cfg.http_port, 8080)
            self.assertEqual(cfg.ws_host, "0.0.0.0")
            self.assertEqual(cfg.ws_port, 8765)
            self.assertIn("127.0.0.1", cfg.trusted_proxies)

    def test_custom_valid_ipv4_config(self):
        env = {
            "ALICE_BIND_ADDRESS": "127.0.0.1",
            "ALICE_HTTP_PORT": "8088",
            "ALICE_WS_BIND_ADDRESS": "127.0.0.1",
            "ALICE_WS_PORT": "8766",
            "ALICE_TRUSTED_PROXIES": "10.0.0.1,192.168.1.0/24"
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "127.0.0.1")
            self.assertEqual(cfg.http_port, 8088)
            self.assertEqual(cfg.ws_host, "127.0.0.1")
            self.assertEqual(cfg.ws_port, 8766)
            self.assertIn("10.0.0.1", cfg.trusted_proxies)
            self.assertIn("192.168.1.0/24", cfg.trusted_proxies)

    def test_ipv6_loopback_config(self):
        env = {
            "ALICE_BIND_ADDRESS": "::1",
            "ALICE_WS_BIND_ADDRESS": "::1",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_host, "::1")
            self.assertEqual(cfg.ws_host, "::1")

    def test_invalid_ip_fallback(self):
        env = {
            "ALICE_BIND_ADDRESS": "999.999.999.999; rm -rf /",
            "ALICE_WS_BIND_ADDRESS": "invalid_host_name_injection",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            # Should safely fallback to safe defaults or loopback
            self.assertIn(cfg.http_host, ["127.0.0.1", "0.0.0.0"])
            self.assertIn(cfg.ws_host, ["127.0.0.1", "0.0.0.0"])

    def test_invalid_port_fallback(self):
        env = {
            "ALICE_HTTP_PORT": "999999",  # out of bounds
            "ALICE_WS_PORT": "not_a_number",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            self.assertEqual(cfg.http_port, 8080)
            self.assertEqual(cfg.ws_port, 8765)

    def test_port_collision_resolution(self):
        env = {
            "ALICE_HTTP_PORT": "8080",
            "ALICE_WS_PORT": "8080",  # collision with HTTP
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = main2.get_network_config()
            # Collision must be prevented: WS port should adjust or fallback
            self.assertNotEqual(cfg.http_port, cfg.ws_port)


class TestReverseProxyAndClientIP(unittest.TestCase):
    """B2: Tests for get_trusted_client_ip spoofing resistance and header parsing."""

    def setUp(self):
        self.trusted_env = {
            "ALICE_TRUSTED_PROXIES": "127.0.0.1,10.0.0.1,172.16.0.0/12"
        }

    def test_untrusted_peer_xff_spoof_rejected(self):
        # Peer is 192.168.1.50 (NOT trusted proxy)
        # Peer sends X-Forwarded-For: 8.8.8.8
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Forwarded-For": "8.8.8.8"})
            client_ip = main2.get_trusted_client_ip(handler, ("192.168.1.50", 54321))
            # Must strictly return the socket peer IP, ignoring the spoofed header
            self.assertEqual(client_ip, "192.168.1.50")

    def test_untrusted_peer_cf_spoof_rejected(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"CF-Connecting-IP": "1.1.1.1"})
            client_ip = main2.get_trusted_client_ip(handler, ("192.168.1.100", 54321))
            self.assertEqual(client_ip, "192.168.1.100")

    def test_trusted_proxy_single_xff(self):
        # Peer is trusted 127.0.0.1
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Forwarded-For": "203.0.113.195"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "203.0.113.195")

    def test_trusted_proxy_multiple_xff_leftmost(self):
        # Multiple proxies in chain: leftmost is originating client
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "203.0.113.195")

    def test_trusted_proxy_xff_with_port(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Forwarded-For": "203.0.113.195:54321"})
            client_ip = main2.get_trusted_client_ip(handler, ("10.0.0.1", 54321))
            self.assertEqual(client_ip, "203.0.113.195")

    def test_trusted_proxy_x_real_ip(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Real-IP": "198.51.100.42"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "198.51.100.42")

    def test_trusted_proxy_cf_connecting_ip(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"CF-Connecting-IP": "198.51.100.99"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "198.51.100.99")

    def test_trusted_proxy_rfc7239_forwarded(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"Forwarded": "for=198.51.100.77;proto=https;by=203.0.113.43"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "198.51.100.77")

    def test_trusted_proxy_malformed_header_fallback(self):
        with patch.dict(os.environ, self.trusted_env, clear=True):
            handler = MockReqHandler({"X-Forwarded-For": "not_an_ip; SELECT * FROM users"})
            client_ip = main2.get_trusted_client_ip(handler, ("127.0.0.1", 54321))
            self.assertEqual(client_ip, "127.0.0.1")


class TestFrontendSecurityAndHeaders(unittest.TestCase):
    """B3: Tests for CSP and Security Headers on MobileHandler and static files."""

    def test_security_headers_generation(self):
        handler_mock = MagicMock()
        headers_set = {}
        def mock_send_header(name, val):
            headers_set[name.lower()] = val
        handler_mock.send_header = mock_send_header

        main2.MobileHandler._set_security_headers(handler_mock)

        self.assertIn("content-security-policy", headers_set)
        csp = headers_set["content-security-policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self' https://cdnjs.cloudflare.com", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

        self.assertEqual(headers_set.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers_set.get("x-frame-options"), "DENY")
        self.assertIn("strict-origin-when-cross-origin", headers_set.get("referrer-policy", ""))
        self.assertIn("microphone=(self)", headers_set.get("permissions-policy", ""))

    def test_mobile_index_no_hardcoded_private_ip(self):
        index_path = os.path.join(PROJECT_ROOT, "mobile", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("192.168.1.23", content, "Hardcoded private LAN IP must not be present in index.html")

    def test_mobile_app_no_unsafe_sinks(self):
        app_path = os.path.join(PROJECT_ROOT, "mobile", "app.js")
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn(".innerHTML", content)
        self.assertNotIn(".outerHTML", content)
        self.assertNotIn("document.write", content)
        self.assertNotIn("eval(", content)

    def test_mobile_app_no_token_stored_in_localstorage(self):
        app_path = os.path.join(PROJECT_ROOT, "mobile", "app.js")
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Must not store auth token in localStorage
        self.assertNotIn('localStorage.setItem("alice_token"', content)
        self.assertNotIn("localStorage.setItem('alice_token'", content)


class TestSessionCookieAndAuthentication(unittest.TestCase):
    """B4 & B5: Tests for Session cookies, CSRF protection, and WebSocket auth."""

    def setUp(self):
        self.session_mgr = main2.WSSessionManager()

    def test_session_registration_with_csrf(self):
        session_id = "test-session-123"
        token = "test-token-456"
        csrf = "csrf-secret-123"
        registered = self.session_mgr.register_session(session_id, token, csrf_token=csrf)
        self.assertTrue(registered)
        self.assertTrue(self.session_mgr.verify_csrf(session_id, csrf))
        self.assertFalse(self.session_mgr.verify_csrf(session_id, "wrong-csrf"))
        self.assertFalse(self.session_mgr.verify_csrf("non-existent", csrf))

    def test_session_revocation(self):
        session_id = "test-session-234"
        token = "test-token-789"
        self.session_mgr.register_session(session_id, token)
        self.assertTrue(self.session_mgr.validate_session(session_id, token))
        self.session_mgr.revoke_session(session_id, token)
        self.assertFalse(self.session_mgr.validate_session(session_id, token))

    def test_expired_session_invalidation(self):
        session_id = "test-session-expired"
        token = "test-token-exp"
        # Register session with ttl = -1 (immediately expired)
        self.session_mgr.register_session(session_id, token, ttl=-1)
        self.assertFalse(self.session_mgr.validate_session(session_id, token))

    def test_dynamic_origin_port_validation(self):
        # Configure custom port
        env = {"ALICE_HTTP_PORT": "8443", "ALICE_WS_PORT": "8444"}
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(main2.is_origin_allowed("http://localhost:8443"))
            self.assertTrue(main2.is_origin_allowed("http://127.0.0.1:8443"))
            self.assertFalse(main2.is_origin_allowed("http://malicious-site.com:8443"))
            self.assertFalse(main2.is_origin_allowed("http://localhost:9999"))


if __name__ == "__main__":
    unittest.main()
