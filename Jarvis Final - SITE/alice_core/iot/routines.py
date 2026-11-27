#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 06 — PREDICTIVE ROUTINES (ALICE-IOT-006, Wave 3).
Apprend les habitudes domotiques récurrentes, calcule un score de confiance,
suggère sans répéter, et exige un consentement explicite (Accepter/Refuser/Modifier/Suspendre/Supprimer).
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import RBAC, UserPrincipal


class PredictiveRoutineManager:
    """Moteur d'apprentissage de routines avec cycle de consentement utilisateur."""

    def __init__(self, state_file: Optional[str] = None, cooldown_seconds: float = 86400.0 * 14):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.state_file = state_file or os.path.join(base_dir, "alice_outputs", "iot_routines.json")
        self.cooldown_seconds = cooldown_seconds
        self.events: List[Dict[str, Any]] = []
        self.routines: Dict[str, Dict[str, Any]] = {}
        self.dismissed_patterns: Dict[str, float] = {}  # pattern_key -> last_dismissed_ts
        self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.events = d.get("events", [])
                self.routines = d.get("routines", {})
                self.dismissed_patterns = d.get("dismissed_patterns", {})
            except Exception:
                pass

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = f"{self.state_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "events": self.events[-1000:],
                    "routines": self.routines,
                    "dismissed_patterns": self.dismissed_patterns,
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.state_file)

    def record_event(self, entity_id: str, action: str, timestamp: Optional[float] = None, presence: str = "home"):
        """Enregistre un événement domotique autorisé."""
        ts = timestamp or time.time()
        dt = datetime.fromtimestamp(ts)
        with self._lock:
            self.events.append({
                "entity_id": entity_id,
                "action": action,
                "timestamp": ts,
                "minute_of_day": dt.hour * 60 + dt.minute,
                "day_key": dt.strftime("%Y-%m-%d"),
                "presence": presence,
            })
            self._save()

    def detect_candidates(self, min_occurrences: int = 3, tolerance_minutes: int = 30) -> List[Dict[str, Any]]:
        """Détecte les récurrences temporelles sans proposer les motifs récemment refusés."""
        now = time.time()
        with self._lock:
            # Grouper par (entity_id, action, presence)
            groups: Dict[tuple, List[Dict[str, Any]]] = {}
            for ev in self.events:
                k = (ev["entity_id"], ev["action"], ev["presence"])
                groups.setdefault(k, []).append(ev)

            suggestions = []
            for (entity_id, action, presence), ev_list in groups.items():
                if len(ev_list) < min_occurrences:
                    continue
                # Regroupement autour du temps médian
                minutes = sorted(e["minute_of_day"] for e in ev_list)
                median_min = minutes[len(minutes) // 2]
                cluster = [e for e in ev_list if abs(e["minute_of_day"] - median_min) <= tolerance_minutes]
                unique_days = {e["day_key"] for e in cluster}
                if len(unique_days) < min_occurrences:
                    continue

                avg_min = int(sum(e["minute_of_day"] for e in cluster) / len(cluster))
                hh, mm = divmod(avg_min, 60)
                pattern_key = f"{entity_id}:{action}:{hh:02d}:{mm // 15 * 15:02d}"

                # Anti-répétition des suggestions déjà refusées ou déjà existantes
                if pattern_key in self.dismissed_patterns and (now - self.dismissed_patterns[pattern_key]) < self.cooldown_seconds:
                    continue
                if any(r.get("pattern_key") == pattern_key and r.get("status") != "DELETED" for r in self.routines.values()):
                    continue

                confidence = round(min(0.98, 0.55 + 0.1 * len(unique_days)), 2)
                suggestions.append({
                    "pattern_key": pattern_key,
                    "entity_id": entity_id,
                    "action": action,
                    "suggested_time": f"{hh:02d}:{mm:02d}",
                    "presence": presence,
                    "occurrences_days": len(unique_days),
                    "confidence": confidence,
                    "prompt": (
                        f"Tu exécutes régulièrement '{action}' sur {entity_id} vers {hh:02d}h{mm:02d}. "
                        f"Veux-tu créer cette routine ?"
                    ),
                })
            return suggestions

    def accept_routine(self, principal: UserPrincipal, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("predictive_automation")
        ok, reason = RBAC.authorize(principal, "iot", "routine_manage")
        if not ok:
            raise PermissionError(reason)
        rid = f"rt_{uuid.uuid4().hex[:8]}"
        with self._lock:
            routine = {
                "routine_id": rid,
                "pattern_key": suggestion["pattern_key"],
                "entity_id": suggestion["entity_id"],
                "action": suggestion["action"],
                "scheduled_time": suggestion["suggested_time"],
                "status": "ACTIVE",
                "owner_id": principal.user_id,
                "created_at": time.time(),
            }
            self.routines[rid] = routine
            self._save()
            return routine

    def reject_suggestion(self, pattern_key: str):
        with self._lock:
            self.dismissed_patterns[pattern_key] = time.time()
            self._save()

    def update_routine(self, principal: UserPrincipal, routine_id: str, new_status: Optional[str] = None, new_time: Optional[str] = None) -> Dict[str, Any]:
        ok, reason = RBAC.authorize(principal, "iot", "routine_manage")
        if not ok:
            raise PermissionError(reason)
        with self._lock:
            r = self.routines.get(routine_id)
            if not r:
                raise KeyError("Routine introuvable.")
            if new_status in ("ACTIVE", "PAUSED", "DELETED"):
                r["status"] = new_status
            if new_time:
                r["scheduled_time"] = new_time
            self._save()
            return r


PREDICTIVE_ROUTINES = PredictiveRoutineManager()
