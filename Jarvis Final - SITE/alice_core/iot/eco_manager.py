#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 07 — ECO-MANAGER (ALICE-IOT-007, Wave 3).
Surveille la consommation via Home Assistant, détecte les pics et appareils énergivores,
signale explicitement les données manquantes/périmées, protège les appareils critiques
et n'applique le délestage qu'avec autorisation explicite.
"""

import time
import threading
from typing import Dict, Any, List, Optional, Set
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.iot.ha_client import HomeAssistantClient, HA_CLIENT


DEFAULT_CRITICAL_PREFIXES = (
    "alarm_control_panel.", "lock.", "climate.frost",
    "switch.frigo", "switch.congelateur", "switch.medical", "switch.serveur", "switch.routeur"
)


class EcoManager:
    """Superviseur énergétique et moteur de règles de délestage sécurisé."""

    def __init__(self, ha_client: Optional[HomeAssistantClient] = None, peak_threshold_va: float = 4500.0):
        self.ha = ha_client or HA_CLIENT
        self.peak_threshold_va = peak_threshold_va
        self._lock = threading.RLock()
        self.history: List[Dict[str, Any]] = []
        self.critical_entities: Set[str] = {
            "alarm_control_panel.home_base_2",
            "switch.congelateur",
            "switch.frigo",
            "switch.routeur",
        }
        self.tariffs: Optional[Dict[str, float]] = None  # Off-peak / Peak configurés uniquement si fournis
        self.shedding_rules: List[Dict[str, Any]] = []

    def configure_tariffs(self, peak_eur_kwh: float, offpeak_eur_kwh: float, offpeak_hours: List[int]):
        self.tariffs = {
            "peak_eur_kwh": float(peak_eur_kwh),
            "offpeak_eur_kwh": float(offpeak_eur_kwh),
            "offpeak_hours": [int(h) for h in offpeak_hours],
        }

    def add_critical_device(self, entity_id: str):
        self.critical_entities.add(entity_id)

    def is_critical_device(self, entity_id: str) -> bool:
        if entity_id in self.critical_entities:
            return True
        return entity_id.startswith(DEFAULT_CRITICAL_PREFIXES)

    def add_shedding_rule(self, entity_id: str, max_power_va: float, auto_authorized: bool = False):
        if self.is_critical_device(entity_id):
            raise ValueError(f"Interdiction absolue : l'équipement critique '{entity_id}' ne peut être inclus dans le délestage.")
        with self._lock:
            self.shedding_rules.append({
                "entity_id": entity_id,
                "max_power_va": float(max_power_va),
                "auto_authorized": bool(auto_authorized),
            })

    def evaluate_consumption(
        self,
        total_sensor_id: str = "sensor.lixee_zlinky_tic_puissance_apparente",
        device_sensors: Optional[Dict[str, str]] = None,
        current_hour: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Collecte la puissance, détecte les pics, gère les données manquantes/périmées et propose des économies."""
        total_res = self.ha.get_state(total_sensor_id)
        data_quality = "LIVE"
        power_va = None

        if not total_res.get("success") and total_res.get("status") != "STALE":
            data_quality = total_res.get("status", "UNAVAILABLE")
        else:
            if total_res.get("stale"):
                data_quality = "STALE"
            try:
                power_va = float(total_res["state"])
            except Exception:
                data_quality = "INVALID_READING"

        devices_report = {}
        top_consumers = []
        for label, ent_id in (device_sensors or {}).items():
            d_res = self.ha.get_state(ent_id)
            if not d_res.get("success") and d_res.get("status") != "STALE":
                devices_report[label] = {"entity_id": ent_id, "value": None, "status": d_res.get("status", "MISSING"), "stale": True}
                continue
            try:
                val = float(d_res["state"])
                devices_report[label] = {
                    "entity_id": ent_id,
                    "value": val,
                    "status": "STALE" if d_res.get("stale") else "OK",
                    "stale": bool(d_res.get("stale")),
                }
                top_consumers.append((val, label, ent_id))
            except Exception:
                devices_report[label] = {"entity_id": ent_id, "value": None, "status": "INVALID", "stale": True}

        top_consumers.sort(reverse=True)
        peak_detected = (power_va is not None and power_va > self.peak_threshold_va)

        tariff_info: Dict[str, Any] = {"configured": False, "note": "Tarifs heures pleines/creuses non configurés."}
        if self.tariffs:
            hr = current_hour if current_hour is not None else time.localtime().tm_hour
            is_offpeak = hr in self.tariffs["offpeak_hours"]
            tariff_info = {
                "configured": True,
                "period": "OFF_PEAK" if is_offpeak else "PEAK",
                "rate_eur_kwh": self.tariffs["offpeak_eur_kwh"] if is_offpeak else self.tariffs["peak_eur_kwh"],
            }

        recommendations = []
        shed_actions = []
        if peak_detected:
            recommendations.append(
                f"Pic de puissance détecté ({power_va:.0f} VA > seuil {self.peak_threshold_va:.0f} VA)."
            )
            if top_consumers:
                recommendations.append(f"Appareil le plus énergivore : {top_consumers[0][1]} ({top_consumers[0][0]:.1f}).")
            if tariff_info.get("period") == "PEAK":
                recommendations.append("Vous êtes en heures pleines ; décalez les appareils non essentiels en heures creuses.")

            # Règles de délestage
            for rule in self.shedding_rules:
                target = rule["entity_id"]
                if self.is_critical_device(target):
                    shed_actions.append({"entity_id": target, "action": "BLOCKED_CRITICAL"})
                    continue
                if power_va >= rule["max_power_va"]:
                    if rule["auto_authorized"] and FEATURE_FLAGS.is_enabled("predictive_automation") and data_quality == "LIVE":
                        call = self.ha.call_service("switch", "turn_off", target)
                        shed_actions.append({"entity_id": target, "action": "SHED_EXECUTED", "result": call})
                    else:
                        shed_actions.append({
                            "entity_id": target,
                            "action": "RECOMMENDED_SHED_NEEDS_CONSENT",
                            "reason": "Autorisation explicite ou mesure temps réel requise.",
                        })

        with self._lock:
            self.history.append({"ts": time.time(), "power_va": power_va, "quality": data_quality, "peak": peak_detected})

        return {
            "success": (power_va is not None),
            "data_quality": data_quality,
            "power_va": power_va,
            "peak_detected": peak_detected,
            "tariff": tariff_info,
            "devices": devices_report,
            "recommendations": recommendations,
            "shedding": shed_actions,
        }


ECO_MANAGER = EcoManager()
