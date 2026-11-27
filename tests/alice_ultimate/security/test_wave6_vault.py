#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 6 — FEATURE 29 : ENCRYPTED SENSITIVE DATA VAULT (AES-256-GCM + SCRYPT)
Couvre chiffrement authentifié, rotation, auto-lock, RBAC strict (OWNER + step-up),
isolement RAG et absence de fuite dans les journaux d'audit.
"""

import os
import sys
import time
import tempfile
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.contracts import AliceSecurityError, FeatureDisabledError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import RBACPolicyEngine, Role
from alice_core.security.vault import EncryptedDataVault
from alice_core.security.audit import AUDIT_LOGGER
from alice_rag import AliceRAGEngine


class TestWave6Vault(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rbac = RBACPolicyEngine()
        self.owner = self.rbac.register_principal("sv_o", "owner1", Role.OWNER)
        self.admin = self.rbac.register_principal("sv_a", "admin1", Role.ADMIN, step_up_seconds=300.0)
        self.guest = self.rbac.register_principal("sv_g", "guest1", Role.GUEST)

    def tearDown(self):
        FEATURE_FLAGS.set_flag("encrypted_vault", False, persist=False)
        self.tmp.cleanup()

    def test_01_vault_flag_rbac_and_step_up_isolation(self):
        v = EncryptedDataVault(vault_dir=self.tmp.name, auto_lock_seconds=2.0)

        # Flag off -> rejeté
        with self.assertRaises(FeatureDisabledError):
            v.initialize(self.owner, "MonMotDePasseFort123!")

        FEATURE_FLAGS.set_flag("encrypted_vault", True, persist=False)

        # OWNER sans step-up -> rejeté
        with self.assertRaises(AliceSecurityError):
            v.initialize(self.owner, "MonMotDePasseFort123!")

        # ADMIN et GUEST strictement rejetés même avec step-up
        with self.assertRaises(AliceSecurityError):
            v.initialize(self.admin, "MonMotDePasseFort123!")
        with self.assertRaises(AliceSecurityError):
            v.initialize(self.guest, "MonMotDePasseFort123!")

        # OWNER + step-up -> succès
        self.owner.grant_step_up(120.0)
        init_res = v.initialize(self.owner, "MonMotDePasseFort123!")
        self.assertTrue(init_res["initialized"])

    def test_02_aes_gcm_encryption_rotation_autolock_and_rag_isolation(self):
        FEATURE_FLAGS.set_flag("encrypted_vault", True, persist=False)
        self.owner.grant_step_up(120.0)
        v = EncryptedDataVault(vault_dir=self.tmp.name, auto_lock_seconds=0.4)
        v.initialize(self.owner, "PhraseMaitreAlpha99!")

        secret_val = "ULTRA_SECRET_BANK_PIN_998877"
        sid = v.store_secret(self.owner, "Code Banque", secret_val, category="finance")

        # Le fichier sur disque ne doit JAMAIS contenir le secret ni le mot de passe maître en clair
        with open(v.vault_file, "r", encoding="utf-8") as f:
            raw_vault = f.read()
        self.assertNotIn(secret_val, raw_vault)
        self.assertNotIn("PhraseMaitreAlpha99", raw_vault)

        # Relecture OK
        got = v.read_secret(self.owner, sid)
        self.assertEqual(got["value"], secret_val)

        # Rotation de clé
        new_ep = v.rotate_master_key(self.owner, "PhraseMaitreAlpha99!", "NouveauMotDePasseBeta77!")
        self.assertEqual(new_ep, 2)
        v.lock()

        # L'ancien mot de passe ne déverrouille plus
        with self.assertRaises(AliceSecurityError):
            v.unlock(self.owner, "PhraseMaitreAlpha99!")

        # Le nouveau déverrouille et lit bien le secret ré-chiffré
        self.assertTrue(v.unlock(self.owner, "NouveauMotDePasseBeta77!"))
        self.assertEqual(v.read_secret(self.owner, sid)["value"], secret_val)

        # Verrouillage automatique après expiration
        time.sleep(0.5)
        self.assertFalse(v.is_unlocked())
        with self.assertRaises(AliceSecurityError):
            v.read_secret(self.owner, sid)

        # Aucune trace du secret dans le RAG ni dans les journaux d'audit
        rag = AliceRAGEngine(knowledge_dir=self.tmp.name, index_file=os.path.join(self.tmp.name, "idx.json"))
        rag.index_knowledge_directory(force=True)
        self.assertEqual(len(rag.search(secret_val)), 0)

        recent_logs = str(AUDIT_LOGGER.read_recent(limit=20))
        self.assertNotIn(secret_val, recent_logs)
        self.assertNotIn("PhraseMaitreAlpha99", recent_logs)


if __name__ == "__main__":
    unittest.main()
