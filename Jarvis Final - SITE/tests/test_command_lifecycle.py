#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS UNITAIRES & D'INTÉGRATION — LOT A : CYCLE DE VIE DES COMMANDES & ORCHESTRATION
Valide les 9 états, l'idempotence, la détection anti-rejeu, les confirmations et les timeouts.
"""

import sys
import os
import time
import asyncio
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alice_orchestrator import (
    ORCHESTRATOR, CommandLifecycleManager,
    STATE_RECEIVED, STATE_VALIDATING, STATE_ACCEPTED,
    STATE_RUNNING, STATE_SUCCEEDED, STATE_FAILED, STATE_UNKNOWN,
    STATE_CANCELLED, STATE_REQUIRES_CONFIRMATION
)

class TestCommandLifecycle(unittest.TestCase):

    def setUp(self):
        self.mgr = CommandLifecycleManager()

    def test_01_all_nine_states_defined(self):
        """Vérifie que les 9 états formels sont distincts et valides."""
        states = {
            STATE_RECEIVED, STATE_VALIDATING, STATE_ACCEPTED,
            STATE_RUNNING, STATE_SUCCEEDED, STATE_FAILED,
            STATE_UNKNOWN, STATE_CANCELLED, STATE_REQUIRES_CONFIRMATION
        }
        self.assertEqual(len(states), 9)

    def test_02_register_command_initial_state(self):
        """Vérifie que toute commande démarre strictement à l'état RECEIVED avec un identifiant."""
        cmd = self.mgr.register_command("allume la cuisine", "sess_001")
        self.assertEqual(cmd.state, STATE_RECEIVED)
        self.assertTrue(cmd.command_id.startswith("cmd_"))
        self.assertTrue(cmd.trace_id.startswith("tr_"))
        self.assertEqual(cmd.session_id, "sess_001")

    def test_03_idempotency_anti_double_tap(self):
        """Vérifie que deux commandes identiques consécutives sont détectées et dédupliquées."""
        cmd1 = self.mgr.register_command("ferme les volets", "sess_002")
        dup = self.mgr.check_idempotency("ferme les volets", "sess_002")
        self.assertIsNotNone(dup)
        self.assertEqual(dup.command_id, cmd1.command_id)

        # Une commande différente ne doit pas être bloquée
        diff = self.mgr.check_idempotency("ouvre les volets", "sess_002")
        self.assertIsNone(diff)

    def test_04_state_transitions(self):
        """Vérifie les transitions d'états atomiques."""
        async def run_transitions():
            cmd = self.mgr.register_command("test transitions", "sess_003")
            
            await self.mgr.transition(cmd.command_id, STATE_VALIDATING, action="test_act")
            self.assertEqual(cmd.state, STATE_VALIDATING)
            self.assertEqual(cmd.previous_state, STATE_RECEIVED)
            
            await self.mgr.transition(cmd.command_id, STATE_ACCEPTED)
            self.assertEqual(cmd.state, STATE_ACCEPTED)
            
            await self.mgr.transition(cmd.command_id, STATE_RUNNING)
            self.assertEqual(cmd.state, STATE_RUNNING)
            
            await self.mgr.transition(cmd.command_id, STATE_SUCCEEDED, result="OK")
            self.assertEqual(cmd.state, STATE_SUCCEEDED)
            self.assertEqual(cmd.result, "OK")

        asyncio.run(run_transitions())

    def test_05_confirmation_security_isolation(self):
        """Vérifie le blocage des confirmations croisées inter-sessions (SEC-03)."""
        async def run_conf():
            cmd = self.mgr.register_command("éteindre l'ordinateur", "sess_legit")
            await self.mgr.transition(cmd.command_id, STATE_REQUIRES_CONFIRMATION, action="shutdown")
            self.assertEqual(cmd.state, STATE_REQUIRES_CONFIRMATION)
            self.assertIsNotNone(cmd.confirmation_token)

            # Tentative d'usurpation depuis une session tierce
            ok_hack, msg_hack = self.mgr.verify_confirmation(cmd.command_id, cmd.confirmation_token, "sess_attacker")
            self.assertFalse(ok_hack)
            self.assertIn("Violation de sécurité", msg_hack)

            # Confirmation légitime
            ok_legit, msg_legit = self.mgr.verify_confirmation(cmd.command_id, cmd.confirmation_token, "sess_legit")
            self.assertTrue(ok_legit)

        asyncio.run(run_conf())

    def test_06_execution_wrapper_timeout(self):
        """Vérifie que les actions qui dépassent le timeout basculent en état FAILED sans bloquer."""
        async def run_to():
            cmd = self.mgr.register_command("action lente", "sess_to")
            
            async def slow_func():
                await asyncio.sleep(0.5)
                return "done"
                
            st, err = await self.mgr.execute_action_with_lifecycle(
                cmd.command_id, "slow_action", slow_func, timeout=0.1
            )
            self.assertEqual(st, STATE_FAILED)
            self.assertIn("Délai d'exécution dépassé", str(err))

        asyncio.run(run_to())

    def test_07_execution_wrapper_unknown_state(self):
        """Vérifie que les équipements en état non vérifié basculent en UNKNOWN."""
        async def run_unk():
            cmd = self.mgr.register_command("action physique incertaine", "sess_unk")
            
            def ha_mock():
                return {"status": "STATE_UNKNOWN", "state": "unavailable"}
                
            st, res = await self.mgr.execute_action_with_lifecycle(
                cmd.command_id, "ha_lumiere", ha_mock
            )
            self.assertEqual(st, STATE_UNKNOWN)

        asyncio.run(run_unk())


if __name__ == "__main__":
    unittest.main()
