#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 08 — SELF-HEALING IoT (ALICE-IOT-008, Wave 3).
Diagnostique l'état de la flotte d'équipements connectés (disponibilité, batterie faible,
latence, hors-ligne) avec actions non destructives et zéro fausse déclaration de réparation.
"""

import time
from typing import Dict, Any, List, Optional
from alice_core.iot.ha_client import HomeAssistantClient, HA_CLIENT


class SelfHealingIoT:
    """Diagnostiqueur et moteur d'auto-guérison non destructive pour Home Assistant."""

    def __init__(self, ha_client: Optional[HomeAssistantClient] = None, low_battery_threshold: int = 20):
        self.ha = ha_client or HA_CLIENT
        self.low_battery_threshold = low_battery_threshold

    def run_fleet_diagnostic(
        self,
        monitored_entities: List[str],
        battery_entities: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not self.ha.is_configured():
            return {
                "success": False,
                "status": "UNAVAILABLE",
                "offline_devices": [],
                "low_battery_devices": [],
                "summary": "Home Assistant non configuré : diagnostic matériel impossible.",
            }

        offline_devices = []
        low_battery = []
        healthy_count = 0
        latencies = []

        for ent_id in monitored_entities:
            res = self.ha.get_state(ent_id)
            if "latency_ms" in res:
                latencies.append(res["latency_ms"])
            if not res.get("success"):
                offline_devices.append({
                    "entity_id": ent_id,
                    "status": res.get("status", "UNKNOWN"),
                    "raw_state": res.get("state", "unknown"),
                })
            else:
                healthy_count += 1

        for label, batt_ent in (battery_entities or {}).items():
            b_res = self.ha.get_state(batt_ent)
            if not b_res.get("success"):
                offline_devices.append({"entity_id": batt_ent, "label": label, "status": b_res.get("status", "UNKNOWN")})
                continue
            try:
                pct = float(b_res["state"])
                if pct <= self.low_battery_threshold:
                    low_battery.append({"label": label, "entity_id": batt_ent, "level": pct})
            except Exception:
                pass

        parts = []
        if low_battery:
            desc = ", ".join(f"{b['label']} ({b['level']:.0f}%)" for b in low_battery)
            parts.append(f"{len(low_battery)} capteur(s) présentent une batterie faible : {desc}.")
        if offline_devices:
            desc_off = ", ".join(o["entity_id"] for o in offline_devices)
            parts.append(f"{len(offline_devices)} équipement(s) ne répond(ent) plus : {desc_off}.")
        if not parts:
            parts.append(f"Tous les {healthy_count} équipements surveillés sont en ligne et sains.")

        return {
            "success": True,
            "status": "DEGRADED" if (offline_devices or low_battery) else "HEALTHY",
            "healthy_count": healthy_count,
            "offline_devices": offline_devices,
            "low_battery_devices": low_battery,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "summary": " ".join(parts),
        }

    def attempt_non_destructive_recovery(
        self,
        entity_id: str,
        max_retries: int = 2,
        retry_delay: float = 0.2,
        allow_reconnect_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Tente uniquement des relectures bornées et un rafraîchissement autorisé.
        Ne redémarre jamais l'équipement et vérifie l'état réel avant de conclure.
        """
        attempts = []
        for i in range(max_retries):
            st = self.ha.get_state(entity_id)
            attempts.append({"attempt": i + 1, "status": st.get("status"), "state": st.get("state")})
            if st.get("success") and st.get("status") == "OK":
                return {
                    "repaired": True,
                    "status": "RECOVERED_VERIFIED",
                    "entity_id": entity_id,
                    "attempts": attempts,
                    "message": f"L'équipement {entity_id} répond de nouveau (état vérifié : {st.get('state')}).",
                }
            if i == 0 and allow_reconnect_refresh and self.ha.is_configured():
                self.ha.call_service("homeassistant", "update_entity", entity_id)
            if i < max_retries - 1:
                time.sleep(retry_delay)

        return {
            "repaired": False,
            "status": "RECOVERY_FAILED_VERIFIED",
            "entity_id": entity_id,
            "attempts": attempts,
            "recommendation": f"Vérifiez l'alimentation ou la portée Zigbee/Wi-Fi de {entity_id}.",
            "message": f"Impossible de rétablir {entity_id} après {max_retries} tentatives non destructives.",
        }


SELF_HEALING_IOT = SelfHealingIoT()
