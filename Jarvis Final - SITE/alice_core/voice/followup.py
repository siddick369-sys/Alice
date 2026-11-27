#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 05 — FOLLOW-UP LISTEN (ALICE-VOICE-005, Wave 1).
Fenêtre d'écoute continue configurable (défaut 5s) après une réponse d'ALICE,
avec état visible côté WebSocket/UI, annulation immédiate, expiration fiable,
aucune écoute cachée et protection contre les déclenchements accidentels.
"""

import time
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, Awaitable, List
from alice_core.feature_flags import FEATURE_FLAGS


ACCIDENTAL_NOISE_PATTERNS = {
    "", "euh", "hum", "hm", "ah", "oh", "ok", "oui", "bonjour"
}


class FollowUpListenManager:
    """Gestionnaire contrôlé de la fenêtre d'écoute de suivi post-réponse."""

    def __init__(self, default_window_seconds: float = 5.0):
        self._lock = threading.RLock()
        self.window_seconds: float = max(1.0, min(30.0, float(default_window_seconds)))
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.disabled_sessions: set = set()
        self._timers: Dict[str, asyncio.Task] = {}
        self._broadcaster: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None

    def set_broadcaster(self, fn: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        self._broadcaster = fn

    def set_window_seconds(self, seconds: float):
        if not (1.0 <= seconds <= 30.0):
            raise ValueError("La fenêtre Follow-Up doit être comprise entre 1s et 30s.")
        self.window_seconds = float(seconds)

    def set_session_enabled(self, session_id: str, enabled: bool):
        with self._lock:
            if enabled:
                self.disabled_sessions.discard(session_id)
            else:
                self.disabled_sessions.add(session_id)
                self.cancel(session_id, reason="user_disabled")

    def is_enabled_for(self, session_id: str) -> bool:
        return FEATURE_FLAGS.is_enabled("followup_listen_enabled") and (session_id not in self.disabled_sessions)

    async def _emit(self, session_id: str, payload: Dict[str, Any]):
        if self._broadcaster:
            try:
                await self._broadcaster(session_id, payload)
            except Exception:
                pass

    async def open_window(self, session_id: str, role: str, context_topic: str = "") -> Dict[str, Any]:
        """Ouvre une fenêtre d'écoute visible à l'issue d'une réponse vocale."""
        if not self.is_enabled_for(session_id):
            return {"active": False, "reason": "disabled_for_session_or_flag"}

        now = time.time()
        expires_at = now + self.window_seconds

        # Annuler tout minuteur précédent proprement
        old_timer = self._timers.pop(session_id, None)
        if old_timer and not old_timer.done():
            old_timer.cancel()

        state = {
            "type": "followup_state",
            "active": True,
            "session_id": session_id,
            "role": role,
            "window_seconds": self.window_seconds,
            "opened_at": now,
            "expires_at": expires_at,
            "context_topic": context_topic[:100],
            "visible_indicator": True,
        }
        with self._lock:
            self.active_sessions[session_id] = state

        await self._emit(session_id, state)

        async def _expire_task():
            try:
                await asyncio.sleep(self.window_seconds)
                await self.expire(session_id)
            except asyncio.CancelledError:
                pass

        try:
            loop = asyncio.get_running_loop()
            self._timers[session_id] = loop.create_task(_expire_task())
        except RuntimeError:
            pass

        return state

    async def expire(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            had = self.active_sessions.pop(session_id, None)
            self._timers.pop(session_id, None)
        if had:
            ev = {
                "type": "followup_state",
                "active": False,
                "session_id": session_id,
                "reason": "timeout_expired",
                "visible_indicator": False,
            }
            await self._emit(session_id, ev)
            return ev
        return {"active": False, "reason": "not_active"}

    def cancel(self, session_id: str, reason: str = "manual_cancel") -> Dict[str, Any]:
        with self._lock:
            had = self.active_sessions.pop(session_id, None)
            timer = self._timers.pop(session_id, None)
        if timer and not timer.done():
            timer.cancel()
        return {
            "type": "followup_state",
            "active": False,
            "session_id": session_id,
            "cancelled": bool(had),
            "reason": reason,
            "visible_indicator": False,
        }

    def accept_transcript(self, session_id: str, transcript: str) -> Dict[str, Any]:
        """
        Valide qu'une question de suivi est légitime, non expirée et non accidentelle.
        """
        clean = (transcript or "").strip().lower()
        with self._lock:
            sess = self.active_sessions.get(session_id)
            if not sess:
                return {"accepted": False, "reason": "window_closed"}
            if time.time() > sess["expires_at"]:
                self.active_sessions.pop(session_id, None)
                return {"accepted": False, "reason": "window_expired"}

        # Filtrage anti-bruit / déclenchement accidentel
        words = [w for w in clean.split() if len(w) > 0]
        if clean in ACCIDENTAL_NOISE_PATTERNS or len(words) < 2 and len(clean) < 5:
            return {"accepted": False, "reason": "accidental_short_noise"}

        # Fenêtre consommée et fermée après capture valide
        self.cancel(session_id, reason="consumed_by_followup")
        return {
            "accepted": True,
            "session_id": session_id,
            "role": sess["role"],
            "context_topic": sess.get("context_topic", ""),
            "transcript": transcript.strip(),
        }


FOLLOWUP_MANAGER = FollowUpListenManager()
