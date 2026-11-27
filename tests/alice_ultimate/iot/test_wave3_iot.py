#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 3 — PILIER 2 DOMOTIQUE PRÉDICTIVE & IoT (FEATURES 06 À 10)
Couvre indisponibilité HA, données périmées, protection équipements critiques,
sécurité simulation d'absence, hystérésis thermique et consentement routines.
"""

import os
import sys
import time
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.contracts import AliceSecurityError, FeatureDisabledError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import RBACPolicyEngine, Role
from alice_core.iot.ha_client import HomeAssistantClient
from alice_core.iot.routines import PredictiveRoutineManager
from alice_core.iot.eco_manager import EcoManager
from alice_core.iot.self_healing import SelfHealingIoT
from alice_core.iot.presence import DynamicPresenceSimulator
from alice_core.iot.thermal import SmartThermalController, ABSOLUTE_FROST_GUARD_MIN_C


class StubHAClient(HomeAssistantClient):
    """Client HA isolé en mémoire pour tester sans action physique réelle."""

    def __init__(self, states=None, configured=True):
        super().__init__(base_url="http://stub-ha.local" if configured else "", token="stub" if configured else "")
        self._configured = configured
        self.states = dict(states or {})
        self.calls = []

    def is_configured(self) -> bool:
        return self._configured

    def get_state(self, entity_id: str):
        if not self._configured:
            return {"success": False, "status": "UNCONFIGURED", "entity_id": entity_id, "state": "unknown", "stale": True}
        if entity_id not in self.states:
            return {"success": False, "status": "STATE_UNKNOWN", "entity_id": entity_id, "state": "unavailable", "stale": True}
        d = self.states[entity_id]
        stale = self._evaluate_staleness(d)
        raw = str(d.get("state", "unknown")).lower()
        if raw in ("unknown", "unavailable"):
            return {"success": False, "status": "STATE_UNKNOWN", "entity_id": entity_id, "state": raw, "stale": True}
        return {"success": True, "status": "STALE" if stale else "OK", "entity_id": entity_id, "state": d["state"], "stale": stale, "latency_ms": 4.2}

    def call_service(self, domain: str, service: str, entity_id: str, data=None):
        if not self._configured:
            return {"success": False, "status": "UNCONFIGURED"}
        self.calls.append((domain, service, entity_id, data))
        return {"success": True, "status": "REQUEST_ACCEPTED"}


class TestWave3IoT(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rbac = RBACPolicyEngine()
        self.owner = self.rbac.register_principal("so", "u_owner", Role.OWNER)
        self.guest = self.rbac.register_principal("sg", "u_guest", Role.GUEST)

    def tearDown(self):
        FEATURE_FLAGS.set_flag("predictive_automation", False, persist=False)
        FEATURE_FLAGS.set_flag("presence_simulation", False, persist=False)
        self.tmp.cleanup()

    def test_01_predictive_routines_learning_consent_and_antirepeat(self):
        rm = PredictiveRoutineManager(state_file=os.path.join(self.tmp.name, "rt.json"))
        base = datetime(2026, 11, 20, 23, 30)
        for day in range(4):
            ts = (base + timedelta(days=day)).timestamp()
            rm.record_event("light.salon", "turn_off", timestamp=ts)

        cands = rm.detect_candidates(min_occurrences=3)
        self.assertEqual(len(cands), 1)
        self.assertIn("23h", cands[0]["prompt"])

        # Flag off -> blocage création sans consentement activé
        with self.assertRaises(FeatureDisabledError):
            rm.accept_routine(self.owner, cands[0])

        FEATURE_FLAGS.set_flag("predictive_automation", True, persist=False)
        # Guest bloqué par RBAC
        with self.assertRaises(PermissionError):
            rm.accept_routine(self.guest, cands[0])

        # Refus anti-répétition
        rm.reject_suggestion(cands[0]["pattern_key"])
        self.assertEqual(len(rm.detect_candidates(min_occurrences=3)), 0)

    def test_02_eco_manager_stale_critical_protection_and_unconfigured_ha(self):
        # HA non configuré -> signalé proprement
        eco_off = EcoManager(ha_client=StubHAClient(configured=False))
        res_off = eco_off.evaluate_consumption()
        self.assertFalse(res_off["success"])
        self.assertEqual(res_off["data_quality"], "UNCONFIGURED")

        # Données périmées + protection stricte des équipements critiques
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        fresh_ts = datetime.now(timezone.utc).isoformat()
        ha = StubHAClient({
            "sensor.lixee_zlinky_tic_puissance_apparente": {"state": "5200", "last_updated": fresh_ts},
            "sensor.old": {"state": "450", "last_updated": old_ts},
        })
        eco = EcoManager(ha_client=ha, peak_threshold_va=4500.0)
        eco.configure_tariffs(peak_eur_kwh=0.25, offpeak_eur_kwh=0.14, offpeak_hours=[22, 23, 0, 1, 2, 3, 4, 5])

        # Refus d'ajouter un congélateur ou une alarme en règle de délestage
        with self.assertRaises(ValueError):
            eco.add_shedding_rule("switch.congelateur", 3000.0, auto_authorized=True)
        with self.assertRaises(ValueError):
            eco.add_shedding_rule("alarm_control_panel.home_base_2", 1000.0, auto_authorized=True)

        FEATURE_FLAGS.set_flag("predictive_automation", True, persist=False)
        eco.add_shedding_rule("switch.prise_salon", 4800.0, auto_authorized=True)
        res = eco.evaluate_consumption(device_sensors={"ancien": "sensor.old"}, current_hour=18)
        self.assertTrue(res["peak_detected"])
        self.assertEqual(res["tariff"]["period"], "PEAK")
        self.assertTrue(res["devices"]["ancien"]["stale"])
        self.assertEqual(res["shedding"][0]["action"], "SHED_EXECUTED")
        self.assertIn(("switch", "turn_off", "switch.prise_salon", None), ha.calls)

    def test_03_self_healing_iot_never_lies_about_failed_recovery(self):
        fresh_ts = datetime.now(timezone.utc).isoformat()
        ha = StubHAClient({
            "light.salon": {"state": "on", "last_updated": fresh_ts},
            "light.couloir": {"state": "unavailable", "last_updated": fresh_ts},
            "sensor.detecteur_1_batterie": {"state": "12", "last_updated": fresh_ts},
        })
        sh = SelfHealingIoT(ha_client=ha, low_battery_threshold=20)
        diag = sh.run_fleet_diagnostic(
            monitored_entities=["light.salon", "light.couloir"],
            battery_entities={"detecteur_cuisine": "sensor.detecteur_1_batterie"},
        )
        self.assertEqual(diag["status"], "DEGRADED")
        self.assertEqual(len(diag["low_battery_devices"]), 1)
        self.assertEqual(diag["offline_devices"][0]["entity_id"], "light.couloir")

        rec = sh.attempt_non_destructive_recovery("light.couloir", max_retries=2, retry_delay=0.01)
        self.assertFalse(rec["repaired"])
        self.assertEqual(rec["status"], "RECOVERY_FAILED_VERIFIED")

    def test_04_presence_simulation_away_gate_and_forbidden_devices(self):
        ha = StubHAClient({"light.salon": {"state": "off"}})
        sim = DynamicPresenceSimulator(ha_client=ha)
        FEATURE_FLAGS.set_flag("presence_simulation", True, persist=False)

        with self.assertRaises(AliceSecurityError):
            sim.activate(away_mode_confirmed=False)

        with self.assertRaises(AliceSecurityError):
            sim.set_allowed_lights(["alarm_control_panel.home_base_2"])

        sim.activate(away_mode_confirmed=True)
        # Nuit -> bloqué pour respecter la quiétude locale
        r_quiet = sim.execute_step("light.salon", "on", now=datetime(2026, 11, 24, 23, 45))
        self.assertFalse(r_quiet["executed"])
        self.assertEqual(r_quiet["reason"], "quiet_hours_enforced")

        # Tentative illégale sur une serrure -> arrêt sécurité immédiat
        with self.assertRaises(AliceSecurityError):
            sim.execute_step("lock.entree", "on")
        self.assertFalse(sim.simulation_active)

    def test_05_thermal_comfort_hysteresis_cooldown_and_frost_guard(self):
        ha = StubHAClient({"climate.thermostat": {"state": "heat"}})
        th = SmartThermalController(ha_client=ha, hysteresis_c=0.5, min_cycle_seconds=900.0)
        FEATURE_FLAGS.set_flag("predictive_automation", True, persist=False)

        # Interdit de descendre sous le plancher antigel 7°C
        with self.assertRaises(ValueError):
            th.set_bounds(4.0, 22.0)

        # Cible demandée 2°C -> remontée automatiquement à 7°C antigel
        rec_frost = th.recommend(indoor_temp_c=10.0, target_temp_c=2.0)
        self.assertEqual(rec_frost["safe_target_c"], ABSOLUTE_FROST_GUARD_MIN_C)

        # Hystérésis : écart 0.2°C -> HOLD (aucune oscillation)
        rec_hold = th.apply_regulation("climate.thermostat", indoor_temp_c=20.8, target_temp_c=21.0, now_ts=1000.0)
        self.assertFalse(rec_hold["applied"])
        self.assertEqual(rec_hold["recommended_hvac"], "HOLD")

        # Écart net 2.0°C -> chauffage appliqué
        rec_heat = th.apply_regulation("climate.thermostat", indoor_temp_c=19.0, target_temp_c=21.0, sunny=True, outdoor_temp_c=10.0, now_ts=1000.0)
        self.assertTrue(rec_heat["applied"])
        self.assertEqual(rec_heat["recommended_shutter"], "OPEN_FOR_SOLAR_GAIN")

        # Cooldown 15 min empêche oscillation immédiate à t+120s pour même cible
        rec_cool = th.apply_regulation("climate.thermostat", indoor_temp_c=19.2, target_temp_c=21.0, now_ts=1120.0)
        self.assertFalse(rec_cool["applied"])


if __name__ == "__main__":
    unittest.main()
