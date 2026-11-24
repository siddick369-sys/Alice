#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS UNITAIRES & D'INTÉGRATION — LOT C : SÉCURITÉ DE L'AGENT WEB & ANTI-SSRF
Valide le blocage des adresses privées, localhost, métadonnées cloud et protocoles non autorisés.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alice_web_guard import (
    WEB_GUARD, AliceWebGuard,
    STATUS_CONFIRMED_INFO, STATUS_SEARCH_PERFORMED
)

class TestWebGuard(unittest.TestCase):

    def test_01_reject_schemes(self):
        """Vérifie le rejet des schémas dangereux (file, javascript, gopher, ftp)."""
        bad_urls = [
            "file:///C:/Windows/System32/drivers/etc/hosts",
            "javascript:alert(1)",
            "ftp://ftp.example.com",
            "gopher://evil.com",
            "data:text/html,<h1>Hello</h1>"
        ]
        for url in bad_urls:
            ok, msg = WEB_GUARD.is_safe_url(url)
            self.assertFalse(ok, f"URL aurait dû être rejetée : {url}")
            self.assertIn("Schéma d'URL interdit", msg)

    def test_02_reject_loopback_and_localhost(self):
        """Vérifie le blocage absolu de la boucle locale (anti-SSRF sur ports locaux)."""
        loopback_urls = [
            "http://localhost:8080",
            "http://127.0.0.1:8765",
            "http://127.0.0.1:80",
            "http://[::1]:8080"
        ]
        for url in loopback_urls:
            ok, msg = WEB_GUARD.is_safe_url(url)
            self.assertFalse(ok, f"Boucle locale aurait dû être rejetée : {url}")

    def test_03_reject_private_subnets(self):
        """Vérifie le blocage des adresses IP des réseaux privés (RFC 1918)."""
        private_urls = [
            "http://192.168.1.1/admin",
            "http://192.168.1.13:8123",  # Home assistant local
            "http://10.0.0.1",
            "http://172.16.0.5"
        ]
        for url in private_urls:
            ok, msg = WEB_GUARD.is_safe_url(url)
            self.assertFalse(ok, f"IP privée aurait dû être rejetée : {url}")

    def test_04_reject_cloud_metadata(self):
        """Vérifie le blocage de l'adresse de métadonnées d'instance cloud (169.254.169.254)."""
        ok, msg = WEB_GUARD.is_safe_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(ok)
        self.assertIn("Accès interdit", msg)

    def test_05_accept_public_https_domains(self):
        """Vérifie que les domaines publics valides sont acceptés."""
        # Test sur des IP publiques directes pour éviter dépendance DNS réseau en test hors ligne
        ok, msg = WEB_GUARD.is_safe_url("https://8.8.8.8")
        self.assertTrue(ok)
        self.assertEqual(msg, "URL vérifiée et sécurisée.")

    def test_06_search_evidence_format(self):
        """Vérifie le contrat de traçabilité des preuves de recherche."""
        ev = AliceWebGuard.format_search_evidence("météo paris", [{"source": "meteofrance.com", "temp": "12°C"}])
        self.assertEqual(ev["query"], "météo paris")
        self.assertEqual(ev["status"], STATUS_CONFIRMED_INFO)
        self.assertEqual(ev["results_count"], 1)
        self.assertTrue(ev["is_verified"])
        self.assertFalse(ev["is_simulated"])


if __name__ == "__main__":
    unittest.main()
