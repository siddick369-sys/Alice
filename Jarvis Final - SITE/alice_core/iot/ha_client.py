#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLIENT HOME ASSISTANT DÉCOUPLÉ & RÉSILIENCE MATÉRIELLE (Wave 3).
Respecte strictement l'invariant C-04 (vérification physique réelle) et signale
explicitement les états UNAVAILABLE, STALE ou UNCONFIGURED sans fausse réussite.
"""

import os
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from alice_core.ops.observability import OBSERVABILITY


class HomeAssistantClient:
    """Client REST Home Assistant sûr et testable avec détection de données périmées."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, stale_after_seconds: float = 600.0):
        self.base_url = base_url if base_url is not None else os.getenv("HA_URL", "")
        self.token = token if token is not None else os.getenv("HA_TOKEN", "")
        self.stale_after_seconds = stale_after_seconds

    def is_configured(self) -> bool:
        return bool(
            self.base_url
            and self.token
            and "VOTRE" not in self.token
            and "URL-Home" not in self.base_url
            and self.base_url.startswith(("http://", "https://"))
        )

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _evaluate_staleness(self, state_data: Dict[str, Any]) -> bool:
        ts_str = state_data.get("last_updated") or state_data.get("last_changed")
        if not ts_str:
            return False
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            return age > self.stale_after_seconds
        except Exception:
            return False

    def get_state(self, entity_id: str) -> Dict[str, Any]:
        if not self.is_configured():
            OBSERVABILITY.set_integration_health("home_assistant", "UNCONFIGURED", "HA_URL/HA_TOKEN non configurés")
            return {"success": False, "status": "UNCONFIGURED", "entity_id": entity_id, "state": "unknown", "stale": True}
        try:
            t0 = time.perf_counter()
            r = requests.get(f"{self.base_url.rstrip('/')}/api/states/{entity_id}", headers=self._headers(), timeout=5)
            lat = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                OBSERVABILITY.set_integration_health("home_assistant", "DEGRADED", f"HTTP {r.status_code}")
                return {"success": False, "status": "HTTP_ERROR", "code": r.status_code, "entity_id": entity_id, "state": "unknown", "stale": True}
            data = r.json()
            raw_state = str(data.get("state", "unknown")).lower()
            stale = self._evaluate_staleness(data)
            OBSERVABILITY.set_integration_health("home_assistant", "HEALTHY", f"Latence {lat:.1f}ms")
            if raw_state in ("unknown", "unavailable", "none"):
                return {"success": False, "status": "STATE_UNKNOWN", "entity_id": entity_id, "state": raw_state, "attributes": data.get("attributes", {}), "stale": True}
            return {
                "success": True,
                "status": "STALE" if stale else "OK",
                "entity_id": entity_id,
                "state": data.get("state"),
                "attributes": data.get("attributes", {}),
                "last_updated": data.get("last_updated"),
                "stale": stale,
                "latency_ms": round(lat, 2),
            }
        except Exception as e:
            OBSERVABILITY.set_integration_health("home_assistant", "UNAVAILABLE", str(e))
            return {"success": False, "status": "UNAVAILABLE", "entity_id": entity_id, "state": "unknown", "stale": True, "error": str(e)}

    def call_service(self, domain: str, service: str, entity_id: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"success": False, "status": "UNCONFIGURED", "message": "Home Assistant non configuré."}
        payload = {"entity_id": entity_id}
        if data:
            payload.update(data)
        try:
            r = requests.post(
                f"{self.base_url.rstrip('/')}/api/services/{domain}/{service}",
                headers=self._headers(),
                json=payload,
                timeout=5,
            )
            ok = r.status_code in (200, 201)
            return {"success": ok, "status": "REQUEST_ACCEPTED" if ok else "FAILED", "code": r.status_code}
        except Exception as e:
            OBSERVABILITY.set_integration_health("home_assistant", "UNAVAILABLE", str(e))
            return {"success": False, "status": "UNAVAILABLE", "error": str(e)}

    def list_states(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            r = requests.get(f"{self.base_url.rstrip('/')}/api/states", headers=self._headers(), timeout=5)
            return r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
        except Exception:
            return []


HA_CLIENT = HomeAssistantClient()
