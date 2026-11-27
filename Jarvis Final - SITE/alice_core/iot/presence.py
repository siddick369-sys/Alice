#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 09 — DYNAMIC PRESENCE SIMULATION (ALICE-IOT-009, Wave 3).
Simule une présence réaliste UNIQUEMENT lorsque le mode absence est explicitement activé.
Invariants de sécurité absolus :
- Ne touche JAMAIS aux alarmes, serrures, portes de garage ou caméras.
- Respecte les horaires de calme nocturne.
- Arrêt immédiat et retour à un état sûr en cas d'erreur.
"""

import time
import random
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.contracts import AliceSecurityError
from alice_core.iot.ha_client import HomeAssistantClient, HA_CLIENT
from alice_core.security.audit import AUDIT_LOGGER


FORBIDDEN_PRESENCE_DOMAINS = ("alarm_control_panel.", "lock.", "camera.", "cover.garage")


class DynamicPresenceSimulator:
    """Simulateur de présence sécurisé en mode absence explicite."""

    def __init__(self, ha_client: Optional[HomeAssistantClient] = None):
        self.ha = ha_client or HA_CLIENT
        self._lock = threading.RLock()
        self.away_mode_active: bool = False
        self.simulation_active: bool = False
        self.allowed_lights: List[str] = ["light.salon", "light.cuisine_2", "light.chambre_parentale"]
        self.quiet_start_hour: int = 23
        self.quiet_end_hour: int = 7
        self.activated_lights: set = set()
        self.last_schedule: List[Dict[str, Any]] = []

    def set_allowed_lights(self, entities: List[str]):
        for e in entities:
            if not e.startswith("light.") or e.startswith(FORBIDDEN_PRESENCE_DOMAINS):
                raise AliceSecurityError(
                    f"Violation sécurité simulation présence : entité '{e}' interdite (seules les lumières non critiques sont autorisées)."
                )
        with self._lock:
            self.allowed_lights = list(entities)

    def activate(self, away_mode_confirmed: bool) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("presence_simulation")
        if not away_mode_confirmed:
            raise AliceSecurityError(
                "La simulation de présence ne peut démarrer que si le mode absence est explicitement activé."
            )
        with self._lock:
            self.away_mode_active = True
            self.simulation_active = True
            AUDIT_LOGGER.log("IOT", "presence_simulation_started", details={"lights": self.allowed_lights})
            return {"active": True, "lights": self.allowed_lights}

    def deactivate(self) -> Dict[str, Any]:
        """Arrêt immédiat et mise en sécurité (extinction des lampes allumées par la simulation)."""
        with self._lock:
            self.simulation_active = False
            self.away_mode_active = False
            lights_to_turn_off = list(self.activated_lights)
            self.activated_lights.clear()
        for l_ent in lights_to_turn_off:
            if self.ha.is_configured():
                self.ha.call_service("light", "turn_off", l_ent)
        AUDIT_LOGGER.log("IOT", "presence_simulation_stopped", details={"restored_off": lights_to_turn_off})
        return {"active": False, "restored_off": lights_to_turn_off}

    def generate_daily_schedule(self, seed: Optional[int] = None) -> List[Dict[str, Any]]:
        rng = random.Random(seed)
        slots = []
        # Créneau soirée réaliste (18h30..23h15 max)
        for light in self.allowed_lights:
            start_min = rng.randint(18 * 60 + 30, 22 * 60)
            dur = rng.randint(25, 75)
            end_min = min(self.quiet_start_hour * 60 - 5, start_min + dur)
            slots.append({
                "entity_id": light,
                "on_time": f"{start_min // 60:02d}:{start_min % 60:02d}",
                "off_time": f"{end_min // 60:02d}:{end_min % 60:02d}",
            })
        self.last_schedule = slots
        return slots

    def execute_step(self, entity_id: str, action: str, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Exécute un pas de simulation en appliquant les invariants stricts de sécurité."""
        if entity_id.startswith(FORBIDDEN_PRESENCE_DOMAINS) or not entity_id.startswith("light."):
            self.deactivate()
            raise AliceSecurityError(
                f"Invariant sécurité violé : tentative d'accès simulation sur '{entity_id}' refusée et simulation stoppée."
            )

        with self._lock:
            if not (self.away_mode_active and self.simulation_active):
                return {"executed": False, "reason": "simulation_not_active"}

        dt = now or datetime.now()
        is_quiet = (dt.hour >= self.quiet_start_hour) or (dt.hour < self.quiet_end_hour)
        if action == "on" and is_quiet:
            return {"executed": False, "reason": "quiet_hours_enforced"}

        if not self.ha.is_configured():
            # Échec contrôlé : retour à l'état sûr sans prétendre avoir allumé la lampe
            return {"executed": False, "status": "UNAVAILABLE", "reason": "Home Assistant indisponible"}

        service = "turn_on" if action == "on" else "turn_off"
        res = self.ha.call_service("light", service, entity_id, {"brightness": 140} if action == "on" else None)
        if not res.get("success"):
            # En cas de défaillance matérielle, repli sûr
            self.deactivate()
            return {"executed": False, "status": "FAILED_SAFE_STOP", "error": res}

        with self._lock:
            if action == "on":
                self.activated_lights.add(entity_id)
            else:
                self.activated_lights.discard(entity_id)

        return {"executed": True, "entity_id": entity_id, "action": action}


PRESENCE_SIMULATOR = DynamicPresenceSimulator()
