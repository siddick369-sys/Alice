#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 1 — FEATURE 28 : MULTI-USER RBAC & GUEST MODE
Tests unitaires, escalades verticales/horizontales et révocation de privilèges.
"""

import os
import sys
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.contracts import AliceSecurityError
from alice_core.security.rbac import RBACPolicyEngine, Role


class TestWave1RBAC(unittest.TestCase):

    def setUp(self):
        self.rbac = RBACPolicyEngine()
        self.owner = self.rbac.register_principal("sess_owner", "u_owner", Role.OWNER)
        self.admin = self.rbac.register_principal("sess_admin", "u_admin", Role.ADMIN)
        self.member = self.rbac.register_principal("sess_member", "u_member", Role.MEMBER)
        self.guest = self.rbac.register_principal("sess_guest", "u_guest", Role.GUEST)
        self.agent = self.rbac.register_principal("sess_agent", "svc_agent", Role.SERVICE_AGENT)

    def test_01_guest_strictly_blocked_from_sensitive_actions(self):
        for act, ctx in [
            ("shutdown", {}),
            ("reboot", {}),
            ("read_emails", {}),
            ("alice_rediger_email", {}),
            ("ha_alarme", {"etat": "off"}),
            ("vault_read", {}),
            ("check_diagnostics", {}),
        ]:
            ok, _ = self.rbac.check_action("sess_guest", act, context=ctx)
            self.assertFalse(ok, f"GUEST aurait dû être bloqué pour {act}")

        # Lumière publique salon autorisée pour GUEST, mais pas chambre parentale
        ok_salon, _ = self.rbac.check_action("sess_guest", "ha_lumiere", context={"piece": "salon"})
        self.assertTrue(ok_salon)
        ok_chambre, _ = self.rbac.check_action("sess_guest", "ha_lumiere", context={"piece": "chambre"})
        self.assertFalse(ok_chambre)

    def test_02_vertical_privilege_escalation_blocked(self):
        with self.assertRaises(AliceSecurityError):
            self.rbac.change_role(self.guest, "sess_guest", Role.OWNER)
        with self.assertRaises(AliceSecurityError):
            self.rbac.change_role(self.admin, "sess_admin", Role.OWNER)
        with self.assertRaises(AliceSecurityError):
            self.rbac.grant_delegation(self.member, "sess_member", "system:shutdown")

    def test_03_owner_step_up_required_for_vault_and_alarm_disarm(self):
        ok_disarm_no_stepup, _ = self.rbac.check_action("sess_owner", "ha_alarme", context={"etat": "off"})
        self.assertFalse(ok_disarm_no_stepup)

        ok_vault_no_stepup, _ = self.rbac.authorize(self.owner, "vault", "read")
        self.assertFalse(ok_vault_no_stepup)

        self.owner.grant_step_up(60.0)
        ok_disarm_ok, _ = self.rbac.check_action("sess_owner", "ha_alarme", context={"etat": "off"})
        self.assertTrue(ok_disarm_ok)
        ok_vault_ok, _ = self.rbac.authorize(self.owner, "vault", "read")
        self.assertTrue(ok_vault_ok)

    def test_04_horizontal_isolation_and_delegation(self):
        # Membre A ne peut pas accéder aux ressources privées de Membre B
        other_member = self.rbac.register_principal("sess_m2", "u_member_2", Role.MEMBER)
        self.assertFalse(self.rbac.check_owner_isolation(self.member, other_member.user_id, visibility="private"))
        self.assertTrue(self.rbac.check_owner_isolation(self.member, "u_member", visibility="private"))

        # Délégation email par OWNER à MEMBER
        ok_before, _ = self.rbac.check_action("sess_member", "read_emails")
        self.assertFalse(ok_before)
        self.rbac.grant_delegation(self.owner, "sess_member", "emails:read")
        ok_after, _ = self.rbac.check_action("sess_member", "read_emails")
        self.assertTrue(ok_after)


if __name__ == "__main__":
    unittest.main()
