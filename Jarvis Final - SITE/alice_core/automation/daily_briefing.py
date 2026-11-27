#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 21 — PROACTIVE MORNING / EVENING BRIEFING (ALICE-AUTO-021, Wave 5).
Génère des synthèses planifiables en heure locale sans données fictives,
avec mode silencieux, traçabilité des sources et protection anti-fuite d'emails
confidentiels en présence d'invités.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from alice_core.security.rbac import Role, UserPrincipal
from alice_core.memory.commitments import COMMITMENT_TRACKER
from alice_core.iot.ha_client import HA_CLIENT
from alice_google_adapter import GOOGLE_ADAPTER


class ProactiveDailyBriefing:
    """Service de génération des briefings matinaux et débriefings du soir."""

    def __init__(self):
        self._lock = threading.RLock()
        self.morning_time: str = "07:30"
        self.evening_time: str = "21:30"
        self.silent_mode: bool = False
        self.allow_confidential_emails_with_guests: bool = False
        self.cancelled_dates: set = set()
        self.weather_provider = None  # Optionnel : branché sur get_meteo_actuelle

    def configure(self, morning_time: str = "07:30", evening_time: str = "21:30", silent_mode: bool = False, allow_emails_with_guests: bool = False):
        with self._lock:
            self.morning_time = morning_time
            self.evening_time = evening_time
            self.silent_mode = bool(silent_mode)
            self.allow_confidential_emails_with_guests = bool(allow_emails_with_guests)

    def cancel_for_today(self):
        self.cancelled_dates.add(datetime.now().strftime("%Y-%m-%d"))

    def build_morning_briefing(
        self,
        principal: UserPrincipal,
        guests_present: bool = False,
        speak_aloud: bool = True,
    ) -> Dict[str, Any]:
        today_key = datetime.now().strftime("%Y-%m-%d")
        if today_key in self.cancelled_dates:
            return {"cancelled": True, "reason": "Annulé pour aujourd'hui."}

        sources: List[str] = []
        sections: Dict[str, Any] = {}

        # 1. Météo réelle si fournisseur branché, sinon état explicite
        if self.weather_provider:
            try:
                sections["weather"] = self.weather_provider()
                sources.append("open-meteo")
            except Exception as e:
                sections["weather"] = f"Météo indisponible ({e})."
        else:
            sections["weather"] = "Météo non consultée (fournisseur hors ligne)."

        # 2. Agenda via adaptateur Google
        cal = GOOGLE_ADAPTER.list_calendar_events(days=1)
        if cal.get("success"):
            sections["calendar"] = cal.get("events", [])
            sources.append("google_calendar")
        else:
            sections["calendar"] = {"status": cal.get("status"), "note": cal.get("message")}

        # 3. Emails urgents : bloqué à voix haute si invités présents OU si non OWNER
        can_include_emails = (
            principal.role == Role.OWNER
            and not (guests_present and speak_aloud and not self.allow_confidential_emails_with_guests)
        )
        if can_include_emails:
            mails = GOOGLE_ADAPTER.read_emails(max_results=3)
            if mails.get("success"):
                sections["urgent_emails"] = mails.get("emails", [])
                sources.append("gmail")
            else:
                sections["urgent_emails"] = {"status": mails.get("status"), "note": mails.get("message")}
        else:
            sections["urgent_emails"] = {
                "status": "REDACTED_PRIVACY_GUARD",
                "note": "Lecture vocale des emails masquée (présence d'invités ou rôle non autorisé).",
            }

        # 4. Engagements en attente / programmés
        cmts = COMMITMENT_TRACKER.list_for_owner(principal.user_id)
        sections["commitments_pending"] = [c["commitment"] for c in cmts if c["status"] != "COMPLETED"]
        if cmts:
            sources.append("commitment_tracker")

        # 5. État réel maison (Home Assistant)
        if HA_CLIENT.is_configured():
            alarm = HA_CLIENT.get_state("alarm_control_panel.home_base_2")
            sections["home_status"] = {"alarm": alarm.get("state"), "status": alarm.get("status")}
            sources.append("home_assistant")
        else:
            sections["home_status"] = {"status": "UNCONFIGURED", "note": "Home Assistant non configuré."}

        return {
            "type": "morning_briefing",
            "date": today_key,
            "silent_mode": self.silent_mode,
            "speak_allowed": (not self.silent_mode) and speak_aloud,
            "guests_present": guests_present,
            "sections": sections,
            "sources": sources,
            "is_simulated": False,
        }

    def build_evening_debrief(self, principal: UserPrincipal, completed_tasks_count: int = 0) -> Dict[str, Any]:
        cmts = COMMITMENT_TRACKER.list_for_owner(principal.user_id)
        pending = [c for c in cmts if c["status"] not in ("COMPLETED", "REJECTED")]
        cal = GOOGLE_ADAPTER.list_calendar_events(days=2)
        return {
            "type": "evening_debrief",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "silent_mode": self.silent_mode,
            "sections": {
                "completed_tasks_today": completed_tasks_count,
                "pending_commitments": [c["commitment"] for c in pending],
                "tomorrow_calendar": cal.get("events", []) if cal.get("success") else cal.get("status"),
                "home_status": "UNCONFIGURED" if not HA_CLIENT.is_configured() else "CONFIGURED",
            },
            "sources": ["commitment_tracker", "google_adapter"],
            "is_simulated": False,
        }


DAILY_BRIEFING = ProactiveDailyBriefing()
