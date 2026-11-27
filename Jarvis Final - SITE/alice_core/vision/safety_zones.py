#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 20 — CONTEXTUAL SAFETY ZONES (ALICE-VISION-020, Wave 4).
Zones polygonales virtuelles (piscine, escalier, atelier, zone technique) avec
plages horaires, validation temporelle multi-trames et protection renforcée des données.
Ne constitue JAMAIS un dispositif de sécurité certifié ni un substitut humain.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from alice_core.feature_flags import FEATURE_FLAGS


SAFETY_DISCLAIMER = (
    "AVERTISSEMENT : Cette alerte est une assistance logicielle contextuelle et ne "
    "constitue ni un dispositif de sécurité certifié ni un substitut à la surveillance humaine."
)


class SafetyZoneMonitor:
    """Évaluateur géométrique et temporel de zones de sécurité virtuelles."""

    def __init__(self):
        self._lock = threading.RLock()
        self.zones: Dict[str, Dict[str, Any]] = {}
        self._dwell_counts: Dict[Tuple[str, str], int] = {}

    @staticmethod
    def point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """Algorithme Ray Casting pour test d'appartenance à un polygone quelconque."""
        if len(polygon) < 3:
            return False
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
            if intersect:
                inside = not inside
            j = i
        return inside

    def add_zone(
        self,
        zone_id: str,
        name: str,
        camera_id: str,
        owner_id: str,
        polygon: List[Tuple[float, float]],
        start_hour: int = 0,
        end_hour: int = 23,
        dwell_frames_required: int = 2,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        if len(polygon) < 3:
            raise ValueError("Une zone polygonale requiert au moins 3 sommets.")
        z = {
            "zone_id": zone_id,
            "name": name,
            "camera_id": camera_id,
            "owner_id": owner_id,
            "polygon": [(float(px), float(py)) for px, py in polygon],
            "start_hour": int(start_hour),
            "end_hour": int(end_hour),
            "dwell_frames_required": max(1, int(dwell_frames_required)),
            "enabled": bool(enabled),
            "disclaimer": SAFETY_DISCLAIMER,
        }
        with self._lock:
            self.zones[zone_id] = z
        return z

    @staticmethod
    def _in_schedule(zone: Dict[str, Any], dt: datetime) -> bool:
        s, e = zone["start_hour"], zone["end_hour"]
        h = dt.hour
        if s <= e:
            return s <= h <= e
        return h >= s or h <= e

    def evaluate_detections(
        self,
        camera_id: str,
        detections: List[Dict[str, Any]],
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Vérifie les détections (humain/animal) contre les zones actives de la caméra."""
        FEATURE_FLAGS.require_enabled("video_monitoring")
        dt = now or datetime.now()
        alerts = []

        with self._lock:
            cam_zones = [z for z in self.zones.values() if z["camera_id"] == camera_id and z["enabled"]]
            for z in cam_zones:
                if not self._in_schedule(z, dt):
                    continue
                zid = z["zone_id"]
                intruded = False
                matched_det = None
                for d in detections:
                    bbox = d.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    if self.point_in_polygon(cx, cy, z["polygon"]):
                        intruded = True
                        matched_det = d
                        break

                streak_key = (camera_id, zid)
                if intruded and matched_det:
                    self._dwell_counts[streak_key] = self._dwell_counts.get(streak_key, 0) + 1
                    if self._dwell_counts[streak_key] >= z["dwell_frames_required"]:
                        alerts.append({
                            "zone_id": zid,
                            "zone_name": z["name"],
                            "camera_id": camera_id,
                            "object_class": matched_det.get("class", "mouvement"),
                            "privacy_protected": True,
                            "alert_message": f"Entrée détectée en zone '{z['name']}' ({matched_det.get('class')}).",
                            "disclaimer": SAFETY_DISCLAIMER,
                            "timestamp": time.time(),
                        })
                else:
                    self._dwell_counts[streak_key] = 0

        return alerts


SAFETY_ZONES = SafetyZoneMonitor()
