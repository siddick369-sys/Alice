#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS UNITAIRES & D'INTÉGRATION — LOT D : ADAPTATEUR GOOGLE WORKSPACE
Valide la non-bloquance en cas de token absent, le découpage read/write
et la politique de confirmation sur les actions engageantes.
"""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alice_google_adapter import (
    GoogleWorkspaceAdapter,
    GW_STATUS_AVAILABLE, GW_STATUS_UNAVAILABLE,
    GW_STATUS_AUTH_REQUIRED, GW_STATUS_CONFIRMATION
)

class TestGoogleAdapter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.adapter = GoogleWorkspaceAdapter(base_dir=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_missing_credentials_fails_gracefully(self):
        """Vérifie le repli immédiat sans blocage si credentials.json est absent."""
        avail = self.adapter.check_availability()
        self.assertEqual(avail["status"], GW_STATUS_UNAVAILABLE)
        self.assertFalse(avail["authenticated"])
        self.assertIn("credentials.json absent", avail["message"])

    def test_02_missing_token_returns_auth_required_without_hanging(self):
        """Vérifie que l'absence de token.pickle ne tente pas d'ouvrir de socket local bloquant."""
        # Créer credentials.json factice
        creds_file = os.path.join(self.tmp_dir.name, "credentials.json")
        with open(creds_file, "w", encoding="utf-8") as f:
            f.write('{"installed": {"client_id": "dummy"}}')

        avail = self.adapter.check_availability()
        self.assertEqual(avail["status"], GW_STATUS_AUTH_REQUIRED)
        self.assertFalse(avail["authenticated"])
        self.assertIn("Jeton OAuth (token.pickle) absent", avail["message"])

    def test_03_read_operations_fail_cleanly_when_unauthenticated(self):
        """Vérifie que la lecture d'emails ou du calendrier retourne une structure d'échec propre."""
        res_cal = self.adapter.list_calendar_events(days=7)
        self.assertFalse(res_cal["success"])
        self.assertEqual(res_cal["events"], [])

        res_mail = self.adapter.read_emails(max_results=3)
        self.assertFalse(res_mail["success"])
        self.assertEqual(res_mail["emails"], [])

    def test_04_mock_mode_enables_isolated_testing(self):
        """Vérifie le fonctionnement du mode mocké pour les tests automatisés."""
        self.adapter.enable_mock_mode({
            "emails": [{"id": "1", "subject": "Test"}],
            "calendar": [{"id": "c1", "summary": "Meeting"}]
        })
        
        cal = self.adapter.list_calendar_events()
        self.assertTrue(cal["success"])
        self.assertEqual(len(cal["events"]), 1)

        mail = self.adapter.read_emails()
        self.assertTrue(mail["success"])
        self.assertEqual(len(mail["emails"]), 1)

    def test_05_mutating_actions_require_confirmation(self):
        """Vérifie que la création de document ou l'envoi d'email exige une confirmation explicite."""
        self.adapter.enable_mock_mode()

        doc_prep = self.adapter.prepare_create_doc("Rapport Annuel", "Contenu")
        self.assertTrue(doc_prep["success"])
        self.assertEqual(doc_prep["status"], GW_STATUS_CONFIRMATION)
        self.assertIn("Confirmez-vous", doc_prep["confirmation_prompt"])

        mail_prep = self.adapter.prepare_send_email("boss@enterprise.com", "Démission", "Adieu")
        self.assertTrue(mail_prep["success"])
        self.assertEqual(mail_prep["status"], GW_STATUS_CONFIRMATION)
        self.assertIn("Confirmez-vous", mail_prep["confirmation_prompt"])


if __name__ == "__main__":
    unittest.main()
