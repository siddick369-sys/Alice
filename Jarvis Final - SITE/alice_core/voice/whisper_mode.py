#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 04 — WHISPER MODE (ALICE-VOICE-004, Wave 1).
Distingue le chuchotement (énergie non voisée aspirée, faible harmonicité périodique,
ZCR haute fréquence) d'une voix normale distante/faible, gère le planning nocturne
sur l'heure locale et adapte les profils de sortie TTS avec plafond sonore strict.
"""

import threading
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from alice_core.feature_flags import FEATURE_FLAGS


class WhisperModeManager:
    """Gestionnaire de détection du chuchotement et de profil vocal doux."""

    def __init__(self):
        self._lock = threading.RLock()
        self.mode: str = "auto"  # "auto" | "manual_on" | "manual_off"
        self.night_schedule_enabled: bool = True
        self.night_start_hour: int = 22
        self.night_end_hour: int = 7
        self.max_whisper_volume: float = 0.35  # Plafond matériel jamais dépassé
        self.last_detection: Dict[str, Any] = {"is_whisper": False, "reason": "none"}

    def set_mode(self, mode: str):
        if mode not in ("auto", "manual_on", "manual_off"):
            raise ValueError("Mode whisper invalide (attendu : auto, manual_on, manual_off)")
        with self._lock:
            self.mode = mode

    def configure_night_schedule(self, enabled: bool, start_hour: int = 22, end_hour: int = 7):
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            raise ValueError("Les heures nocturnes doivent être comprises entre 0 et 23.")
        with self._lock:
            self.night_schedule_enabled = bool(enabled)
            self.night_start_hour = int(start_hour)
            self.night_end_hour = int(end_hour)

    def is_night_time(self, now: Optional[datetime] = None) -> bool:
        if not self.night_schedule_enabled:
            return False
        dt = now or datetime.now()
        h = dt.hour
        if self.night_start_hour > self.night_end_hour:
            return h >= self.night_start_hour or h < self.night_end_hour
        return self.night_start_hour <= h < self.night_end_hour

    def detect_whisper_audio(self, pcm_int16: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Différencie un murmure aspiré d'une parole normale parlée doucement/loin :
        - Un murmure présente un fort taux de friction/non-périodicité (spectral flatness
          élevée dans les fréquences moyennes/hautes, ZCR élevé, faible pic d'autocorrélation
          fondamentale) et une amplitude modérée (pas un cri ni le silence).
        - Une voix douce/distante conserve une périodicité harmonique marquée (autocorrélation F0 haute).
        """
        if not FEATURE_FLAGS.is_enabled("whisper_mode_enabled"):
            return {"is_whisper": False, "confidence": 0.0, "reason": "feature_disabled"}

        if pcm_int16.size < int(sample_rate * 0.05):
            return {"is_whisper": False, "confidence": 0.0, "reason": "frame_too_short"}

        arr = pcm_int16.astype(np.float64)
        rms = float(np.sqrt(np.mean(arr ** 2)))

        # Trop silencieux (bruit ambiant) ou trop fort (voix pleine/cri)
        if rms < 45.0:
            return {"is_whisper": False, "confidence": 0.0, "reason": "silence", "rms": round(rms, 1)}
        if rms > 3500.0:
            return {"is_whisper": False, "confidence": 0.05, "reason": "loud_speech", "rms": round(rms, 1)}

        # Autocorrélation normalisée dans la plage de pitch humain (80Hz - 350Hz)
        centered = arr - np.mean(arr)
        energy = float(np.sum(centered ** 2)) + 1e-9
        min_lag = max(1, int(sample_rate / 350))
        max_lag = min(centered.size // 2, int(sample_rate / 80))

        peak_periodicity = 0.0
        if max_lag > min_lag:
            ac = np.correlate(centered, centered, mode="full")[centered.size - 1:]
            seg = ac[min_lag:max_lag] / energy
            if seg.size > 0:
                peak_periodicity = float(np.max(seg))

        # Ratio haute fréquence (> 1.8 kHz) vs basse fréquence (< 800 Hz)
        spec = np.abs(np.fft.rfft(centered * np.hanning(centered.size))) ** 2
        freqs = np.fft.rfftfreq(centered.size, d=1.0 / sample_rate)
        low_e = float(np.sum(spec[(freqs >= 80) & (freqs <= 800)])) + 1e-9
        high_e = float(np.sum(spec[(freqs >= 1800) & (freqs <= 6000)])) + 1e-9
        hf_lf_ratio = high_e / low_e

        signs = np.sign(centered)
        zcr = float(np.mean(np.abs(np.diff(signs)) > 0))

        # Chuchotement : faible harmonicité (< 0.42) + friction HF notable + ZCR élevé
        is_unvoiced = peak_periodicity < 0.42
        has_friction = hf_lf_ratio > 0.35 or zcr > 0.14
        is_whisper = bool(is_unvoiced and has_friction)

        score = 0.0
        if is_unvoiced:
            score += min(0.5, (0.5 - peak_periodicity))
        if hf_lf_ratio > 0.35:
            score += min(0.3, hf_lf_ratio * 0.25)
        if zcr > 0.14:
            score += 0.2
        conf = round(min(1.0, max(0.0, score)), 2)

        res = {
            "is_whisper": is_whisper,
            "confidence": conf,
            "rms": round(rms, 1),
            "periodicity": round(peak_periodicity, 3),
            "hf_lf_ratio": round(hf_lf_ratio, 3),
            "zcr": round(zcr, 3),
            "reason": "whisper_detected" if is_whisper else "low_volume_voiced_speech",
        }
        with self._lock:
            self.last_detection = res
        return res

    def get_tts_profile(
        self,
        detected_whisper: bool = False,
        requested_volume: float = 0.85,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Retourne le profil TTS et garantit que le volume n'est jamais augmenté automatiquement."""
        with self._lock:
            if not FEATURE_FLAGS.is_enabled("whisper_mode_enabled") or self.mode == "manual_off":
                return {
                    "whisper_active": False,
                    "volume": round(min(1.0, max(0.0, requested_volume)), 2),
                    "edge_rate": "+0%",
                    "edge_volume": "+0%",
                    "pyttsx3_rate": 160,
                    "voice_style": "standard",
                }

            night = self.is_night_time(now)
            active = (self.mode == "manual_on") or detected_whisper or night

            if not active:
                return {
                    "whisper_active": False,
                    "volume": round(min(1.0, max(0.0, requested_volume)), 2),
                    "edge_rate": "+0%",
                    "edge_volume": "+0%",
                    "pyttsx3_rate": 160,
                    "voice_style": "standard",
                }

            # En mode chuchotement/nuit : on ne peut QUE baisser le volume (jamais augmenter)
            capped_vol = round(min(requested_volume, self.max_whisper_volume), 2)
            return {
                "whisper_active": True,
                "night_mode": night,
                "manual_override": (self.mode == "manual_on"),
                "volume": capped_vol,
                "edge_rate": "-12%",
                "edge_volume": "-45%",
                "edge_pitch": "-4Hz",
                "pyttsx3_rate": 135,
                "voice_style": "soft_whisper_compatible",
            }


WHISPER_MANAGER = WhisperModeManager()
