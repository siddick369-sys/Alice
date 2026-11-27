#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 10 — SMART THERMAL COMFORT (ALICE-IOT-010, Wave 3).
Moteur de recommandation et régulation thermique contrôlée prenant en compte
température intérieure/extérieure, météo/ensoleillement et présence,
avec hystérésis anti-oscillations et plancher antigel infranchissable.
"""

import time
import threading
from typing import Dict, Any, Optional
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.iot.ha_client import HomeAssistantClient, HA_CLIENT


ABSOLUTE_FROST_GUARD_MIN_C = 7.0
ABSOLUTE_MAX_SAFETY_C = 28.0


class SmartThermalController:
    """Régulateur de confort thermique avec hystérésis et protection antigel."""

    def __init__(
        self,
        ha_client: Optional[HomeAssistantClient] = None,
        min_comfort_c: float = 16.0,
        max_comfort_c: float = 24.0,
        hysteresis_c: float = 0.5,
        min_cycle_seconds: float = 900.0,
    ):
        self.ha = ha_client or HA_CLIENT
        self._lock = threading.RLock()
        self.enabled: bool = True
        self.min_comfort_c = max(ABSOLUTE_FROST_GUARD_MIN_C, float(min_comfort_c))
        self.max_comfort_c = min(ABSOLUTE_MAX_SAFETY_C, float(max_comfort_c))
        self.hysteresis_c = float(hysteresis_c)
        self.min_cycle_seconds = float(min_cycle_seconds)
        self.last_command_ts: float = 0.0
        self.last_target_c: Optional[float] = None
        self.last_shutter_action: Optional[str] = None

    def set_bounds(self, min_c: float, max_c: float):
        if min_c < ABSOLUTE_FROST_GUARD_MIN_C:
            raise ValueError(
                f"Sécurité antigel : la température minimale ne peut descendre sous {ABSOLUTE_FROST_GUARD_MIN_C}°C."
            )
        if max_c > ABSOLUTE_MAX_SAFETY_C or min_c >= max_c:
            raise ValueError("Plage thermique invalide.")
        with self._lock:
            self.min_comfort_c = float(min_c)
            self.max_comfort_c = float(max_c)

    def recommend(
        self,
        indoor_temp_c: float,
        target_temp_c: float,
        outdoor_temp_c: Optional[float] = None,
        sunny: Optional[bool] = None,
        occupied: bool = True,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calcule la recommandation thermique sans oscillation et protège l'antigel."""
        ts = now_ts if now_ts is not None else time.time()
        safe_target = max(ABSOLUTE_FROST_GUARD_MIN_C, min(self.max_comfort_c, float(target_temp_c)))

        # Mode éco absence mais antigel strict préservé
        if not occupied:
            safe_target = max(ABSOLUTE_FROST_GUARD_MIN_C, min(safe_target, self.min_comfort_c))

        diff = safe_target - float(indoor_temp_c)
        recommended_hvac = "HOLD"
        recommended_shutter = "NO_CHANGE"

        # Hystérésis : aucune bascule dans la bande morte [-hysteresis, +hysteresis]
        if diff >= self.hysteresis_c:
            recommended_hvac = "HEAT"
            if sunny and (outdoor_temp_c is not None and outdoor_temp_c >= 5.0):
                recommended_shutter = "OPEN_FOR_SOLAR_GAIN"
        elif diff <= -self.hysteresis_c:
            recommended_hvac = "COOL_OR_REDUCE"
            if sunny and (outdoor_temp_c is not None and outdoor_temp_c > float(indoor_temp_c)):
                recommended_shutter = "CLOSE_FOR_SHADE"

        cooldown_blocked = (self.last_command_ts > 0) and ((ts - self.last_command_ts) < self.min_cycle_seconds)
        if cooldown_blocked and self.last_target_c == safe_target:
            recommended_hvac = "COOLDOWN_HOLD"

        return {
            "indoor_temp_c": round(float(indoor_temp_c), 2),
            "safe_target_c": round(safe_target, 2),
            "occupied": occupied,
            "recommended_hvac": recommended_hvac,
            "recommended_shutter": recommended_shutter,
            "frost_guard_floor_c": ABSOLUTE_FROST_GUARD_MIN_C,
            "cooldown_active": cooldown_blocked,
        }

    def apply_regulation(
        self,
        thermostat_entity: str,
        indoor_temp_c: float,
        target_temp_c: float,
        outdoor_temp_c: Optional[float] = None,
        sunny: Optional[bool] = None,
        occupied: bool = True,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self.enabled or not FEATURE_FLAGS.is_enabled("predictive_automation"):
            rec = self.recommend(indoor_temp_c, target_temp_c, outdoor_temp_c, sunny, occupied, now_ts)
            rec["applied"] = False
            rec["reason"] = "Régulation automatique désactivée (mode recommandation uniquement)."
            return rec

        ts = now_ts if now_ts is not None else time.time()
        rec = self.recommend(indoor_temp_c, target_temp_c, outdoor_temp_c, sunny, occupied, ts)

        if rec["recommended_hvac"] in ("HOLD", "COOLDOWN_HOLD"):
            rec["applied"] = False
            rec["reason"] = "Bande morte hystérésis ou cooldown anti-oscillation actif."
            return rec

        if not self.ha.is_configured():
            rec["applied"] = False
            rec["status"] = "UNAVAILABLE"
            return rec

        res = self.ha.call_service("climate", "set_temperature", thermostat_entity, {"temperature": rec["safe_target_c"]})
        if res.get("success"):
            with self._lock:
                self.last_command_ts = ts
                self.last_target_c = rec["safe_target_c"]
        rec["applied"] = bool(res.get("success"))
        rec["ha_result"] = res
        return rec


THERMAL_CONTROLLER = SmartThermalController()
