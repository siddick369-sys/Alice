#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 03 — ACOUSTIC MOOD AND CONTEXT (ALICE-VOICE-003, Wave 6).
Analyse acoustique probabiliste non identifiante (débit, intensité, énergie, pauses)
produisant uniquement : CALM, URGENT_SPEECH_PATTERN, HIGH_VOCAL_INTENSITY,
LOW_ENERGY_SPEECH, UNKNOWN.
Ne produit aucun diagnostic psychologique/médical et ne modifie aucune permission.
"""

import numpy as np
from typing import Dict, Any, Optional
from alice_core.feature_flags import FEATURE_FLAGS


ACOUSTIC_CONTEXT_LABELS = {
    "CALM",
    "URGENT_SPEECH_PATTERN",
    "HIGH_VOCAL_INTENSITY",
    "LOW_ENERGY_SPEECH",
    "UNKNOWN",
}


class AcousticContextAnalyzer:
    """Analyseur de contexte acoustique conversationnel avec opt-out strict."""

    def __init__(self):
        self.opted_out_users: set = set()

    def set_user_opt_out(self, user_id: str, opted_out: bool):
        if opted_out:
            self.opted_out_users.add(user_id)
        else:
            self.opted_out_users.discard(user_id)

    def analyze(self, pcm_int16: np.ndarray, sample_rate: int = 16000, user_id: str = "owner") -> Dict[str, Any]:
        if not FEATURE_FLAGS.is_enabled("emotion_context") or user_id in self.opted_out_users:
            return {
                "enabled": False,
                "pattern": "UNKNOWN",
                "confidence": 0.0,
                "communication_style": "standard",
                "medical_or_psychological_diagnosis": False,
                "permissions_modified": False,
            }

        if pcm_int16.size < int(sample_rate * 0.2):
            return {
                "enabled": True,
                "pattern": "UNKNOWN",
                "confidence": 0.0,
                "communication_style": "standard",
                "medical_or_psychological_diagnosis": False,
                "permissions_modified": False,
            }

        arr = pcm_int16.astype(np.float64)
        rms = float(np.sqrt(np.mean(arr ** 2)))

        # Découpage en fenêtres de 20ms pour mesurer pauses et variations d'enveloppe (débit)
        win_len = max(1, int(sample_rate * 0.02))
        n_wins = arr.size // win_len
        frames = arr[:n_wins * win_len].reshape(n_wins, win_len)
        frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
        pause_ratio = float(np.mean(frame_rms < max(50.0, rms * 0.22)))
        flux = float(np.mean(np.abs(np.diff(frame_rms)))) / (rms + 1e-9)

        if rms < 60.0:
            pattern = "UNKNOWN"
            conf = 0.2
            style = "standard"
        elif rms > 4200.0 and flux > 0.35:
            pattern = "HIGH_VOCAL_INTENSITY"
            conf = 0.78
            style = "calm_reassuring_concise"
        elif pause_ratio < 0.12 and flux > 0.28 and rms >= 800.0:
            pattern = "URGENT_SPEECH_PATTERN"
            conf = 0.74
            style = "concise_priority_info"
        elif rms < 450.0 and pause_ratio > 0.45:
            pattern = "LOW_ENERGY_SPEECH"
            conf = 0.68
            style = "calm_helpful"
        else:
            pattern = "CALM"
            conf = 0.76
            style = "standard"

        return {
            "enabled": True,
            "pattern": pattern,
            "confidence": round(conf, 2),
            "metrics": {
                "rms": round(rms, 1),
                "pause_ratio": round(pause_ratio, 3),
                "envelope_flux": round(flux, 3),
            },
            "communication_style": style,
            "medical_or_psychological_diagnosis": False,
            "permissions_modified": False,
        }


ACOUSTIC_CONTEXT = AcousticContextAnalyzer()
