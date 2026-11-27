#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 19 — VISUAL MEMORY (ALICE-VISION-019, Wave 4).
Indexe uniquement des observations d'objets réellement détectés avec horodatage,
caméra, zone et référence de capture soumise à rétention bornée et purge.
Interdit l'invention d'emplacements et le profilage permanent des personnes du foyer.
"""

import os
import json
import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from alice_core.feature_flags import FEATURE_FLAGS


FORBIDDEN_HOUSEHOLD_PROFILING = ("aboubakar", "julie", "esteban", "membre_foyer")


class VisualMemoryStore:
    """Mémoire visuelle temporelle bornée et respectueuse de la vie privée."""

    def __init__(self, index_file: Optional[str] = None, max_items: int = 200, retention_hours: float = 24.0):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.index_file = index_file or os.path.join(base_dir, "alice_outputs", "visual_memory.json")
        self.max_items = max_items
        self.retention_hours = retention_hours
        self.observations: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.observations = json.load(f)
            except Exception:
                self.observations = []

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
            tmp = f"{self.index_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.observations, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.index_file)

    def record_observation(
        self,
        owner_id: str,
        camera_id: str,
        zone: str,
        objects: List[str],
        confidence: float,
        capture_ref: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("visual_memory")
        ts = timestamp or time.time()
        # Ne pas construire d'historique identifiant les personnes du foyer
        filtered_objs = [o.strip() for o in objects if o.strip() and o.lower() not in FORBIDDEN_HOUSEHOLD_PROFILING]
        obs = {
            "obs_id": f"vmem_{uuid.uuid4().hex[:10]}",
            "owner_id": owner_id,
            "timestamp": ts,
            "camera_id": camera_id,
            "zone": zone,
            "objects": filtered_objs,
            "confidence": round(float(confidence), 2),
            "capture_ref": capture_ref,
        }
        with self._lock:
            self.observations.append(obs)
            self.purge_expired(now_ts=ts)
            self._save()
        return obs

    def purge_expired(self, now_ts: Optional[float] = None) -> int:
        ts = now_ts or time.time()
        cutoff = ts - (self.retention_hours * 3600.0)
        removed = 0
        with self._lock:
            kept = []
            for o in self.observations:
                if o["timestamp"] < cutoff:
                    removed += 1
                    p = o.get("capture_ref")
                    if p and os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                else:
                    kept.append(o)
            while len(kept) > self.max_items:
                old = kept.pop(0)
                removed += 1
                p = old.get("capture_ref")
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            self.observations = kept
            self._save()
        return removed

    def search_object(self, owner_id: str, object_query: str, since_hours: float = 24.0) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("visual_memory")
        q = object_query.strip().lower()
        cutoff = time.time() - (since_hours * 3600.0)
        matches = []
        with self._lock:
            for o in reversed(self.observations):
                if o["owner_id"] != owner_id and owner_id != "owner_local":
                    continue
                if o["timestamp"] < cutoff:
                    continue
                if any(q in obj.lower() for obj in o.get("objects", [])):
                    matches.append(o)

        if not matches:
            return {
                "found": False,
                "status": "NOT_OBSERVED",
                "matches": [],
                "message": f"Aucune observation visuelle exploitée pour '{object_query}' sur les dernières {since_hours:.0f}h.",
            }
        latest = matches[0]
        return {
            "found": True,
            "status": "FOUND",
            "matches": matches[:5],
            "latest": latest,
            "message": (
                f"Dernière observation de '{object_query}' en zone '{latest['zone']}' "
                f"(caméra {latest['camera_id']}, confiance {int(latest['confidence']*100)}%)."
            ),
        }


VISUAL_MEMORY = VisualMemoryStore()
