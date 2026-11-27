#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 6 — FEATURES 26 & 27 : OFFLINE PWA SYNC & QUICK ACTIONS
Couvre idempotence, résolution de conflits, exclusion absolue des secrets du cache,
et filtrage RBAC sur les raccourcis d'écran d'accueil.
"""

import os
import sys
import tempfile
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.security.rbac import RBACPolicyEngine, Role
from alice_core.mobile_sync.offline_sync import MobileSyncAndShortcutsManager


class TestWave6MobileSync(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rbac = RBACPolicyEngine()
        self.owner = self.rbac.register_principal("sm_o", "owner1", Role.OWNER)
        self.guest = self.rbac.register_principal("sm_g", "guest1", Role.GUEST)

    def tearDown(self):
        self.tmp.cleanup()

    def test_01_idempotent_sync_conflict_detection_and_secret_exclusion(self):
        ms = MobileSyncAndShortcutsManager(state_file=os.path.join(self.tmp.name, "sync.json"))

        # 1. Création note + tentative de synchro d'un secret vault (doit être rejetée!)
        res1 = ms.apply_sync_batch(self.owner, [
            {"op_id": "op_1", "item_id": "note_1", "item_type": "note", "title": "Courses", "content": "Lait", "base_version": 0},
            {"op_id": "op_sec", "item_id": "sec_1", "item_type": "vault", "title": "PIN", "content": "1234", "base_version": 0},
            {"op_id": "op_conf", "item_id": "doc_1", "item_type": "note", "confidential": True, "content": "Secret", "base_version": 0},
        ])
        self.assertEqual(len(res1["accepted"]), 1)
        self.assertEqual(res1["accepted"][0]["version"], 1)
        self.assertEqual(len(res1["rejected"]), 2)

        # 2. Réenvoi idempotent de op_1 -> ignoré sans doublon
        res_dup = ms.apply_sync_batch(self.owner, [
            {"op_id": "op_1", "item_id": "note_1", "item_type": "note", "title": "Courses", "content": "Lait", "base_version": 0},
        ])
        self.assertEqual(res_dup["skipped_idempotent"], ["op_1"])

        # 3. Édition avec base_version périmée (0 alors que serveur est 1) -> conflit remonté !
        res_conf = ms.apply_sync_batch(self.owner, [
            {"op_id": "op_2", "item_id": "note_1", "item_type": "note", "title": "Courses", "content": "Pain", "base_version": 0},
        ])
        self.assertEqual(len(res_conf["conflicts"]), 1)
        self.assertEqual(res_conf["conflicts"][0]["server_version"], 1)

        # 4. Résolution explicite avec résolution client forcée ou version à jour
        res_ok = ms.apply_sync_batch(self.owner, [
            {"op_id": "op_3", "item_id": "note_1", "item_type": "note", "title": "Courses", "content": "Lait + Pain", "base_version": 1},
        ])
        self.assertEqual(res_ok["accepted"][0]["version"], 2)

    def test_02_quick_actions_respect_rbac(self):
        ms = MobileSyncAndShortcutsManager(state_file=os.path.join(self.tmp.name, "sync2.json"))
        qa_owner = ms.get_quick_actions(self.owner)
        qa_guest = ms.get_quick_actions(self.guest)
        # Pour GUEST, l'action ha_alarme doit être marquée non autorisée (allowed=False)
        alarm_guest = [a for a in qa_guest if a["id"] == "qa_secure_home"][0]
        self.assertFalse(alarm_guest["allowed"])
        # Note rapide / Cinema reste accessible
        self.assertTrue(len(qa_owner) >= 5)


if __name__ == "__main__":
    unittest.main()
