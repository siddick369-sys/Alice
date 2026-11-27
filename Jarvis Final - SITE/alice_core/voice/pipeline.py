#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 01 — REAL-TIME BARGE-IN & AUTOMATE AUDIO (ALICE-VOICE-001, Wave 1).
Gère l'automate formel : IDLE -> LISTENING -> THINKING -> SPEAKING -> INTERRUPTING -> LISTENING,
le filtrage anti-écho / bruit, le vidage des buffers audio obsolètes et l'annulation asynchrone.
"""

import time
import uuid
import asyncio
import threading
import numpy as np
from collections import deque
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
from alice_core.ops.observability import OBSERVABILITY
from alice_core.feature_flags import FEATURE_FLAGS


class AudioState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTING = "INTERRUPTING"


VALID_AUDIO_TRANSITIONS: Dict[AudioState, set] = {
    AudioState.IDLE: {AudioState.LISTENING, AudioState.THINKING, AudioState.SPEAKING, AudioState.IDLE},
    AudioState.LISTENING: {AudioState.THINKING, AudioState.IDLE, AudioState.SPEAKING},
    AudioState.THINKING: {AudioState.SPEAKING, AudioState.IDLE, AudioState.INTERRUPTING, AudioState.LISTENING},
    AudioState.SPEAKING: {AudioState.INTERRUPTING, AudioState.IDLE},
    AudioState.INTERRUPTING: {AudioState.LISTENING, AudioState.IDLE},
}


class AcousticSpeechDetector:
    """
    Détecte la parole humaine vs bruit impulsionnel ou écho TTS actif
    à partir de trames PCM int16 (bande vocale 300-3400 Hz + cohérence énergétique).
    """

    def __init__(self, sample_rate: int = 16000, base_noise_floor: float = 250.0, echo_margin: float = 1.85):
        self.sample_rate = sample_rate
        self.noise_floor = base_noise_floor
        self.echo_margin = echo_margin
        self._consecutive_voice = 0

    @staticmethod
    def _analyze_frame(pcm_int16: np.ndarray, sample_rate: int) -> Dict[str, float]:
        if pcm_int16.size == 0:
            return {"rms": 0.0, "voice_ratio": 0.0, "zcr": 0.0}
        arr = pcm_int16.astype(np.float64)
        rms = float(np.sqrt(np.mean(arr ** 2)))
        # Taux de passage par zéro (ZCR)
        signs = np.sign(arr)
        zcr = float(np.mean(np.abs(np.diff(signs)) > 0)) if arr.size > 1 else 0.0

        # Énergie dans la bande vocale 300-3400 Hz vs spectre total
        win = arr * np.hanning(arr.size)
        spec = np.abs(np.fft.rfft(win)) ** 2
        freqs = np.fft.rfftfreq(arr.size, d=1.0 / sample_rate)
        total_energy = float(np.sum(spec)) + 1e-9
        voice_mask = (freqs >= 300.0) & (freqs <= 3400.0)
        voice_energy = float(np.sum(spec[voice_mask]))
        voice_ratio = voice_energy / total_energy
        return {"rms": rms, "voice_ratio": voice_ratio, "zcr": zcr}

    def evaluate_barge_in_frame(
        self,
        pcm_int16: np.ndarray,
        is_tts_playing: bool = False,
        tts_echo_rms: float = 0.0,
    ) -> Dict[str, Any]:
        """Détermine si la trame contient une prise de parole humaine légitime."""
        metrics = self._analyze_frame(pcm_int16, self.sample_rate)
        rms = metrics["rms"]
        voice_ratio = metrics["voice_ratio"]

        # Seuil adapté : si TTS joue, exige un dépassement net de l'écho TTS + prédominance bande vocale
        effective_threshold = self.noise_floor
        if is_tts_playing:
            effective_threshold = max(self.noise_floor * 1.4, tts_echo_rms * self.echo_margin)

        is_human_band = (voice_ratio >= 0.45) and (0.01 <= metrics["zcr"] <= 0.45)
        above_threshold = rms > effective_threshold

        if above_threshold and is_human_band:
            self._consecutive_voice += 1
        else:
            self._consecutive_voice = 0
            # Mise à jour lente du bruit de fond hors parole
            if not is_tts_playing and rms < self.noise_floor * 1.5 and rms > 10.0:
                self.noise_floor = 0.9 * self.noise_floor + 0.1 * rms

        triggered = self._consecutive_voice >= 2
        return {
            "triggered": triggered,
            "consecutive_frames": self._consecutive_voice,
            "rms": round(rms, 2),
            "threshold": round(effective_threshold, 2),
            "voice_ratio": round(voice_ratio, 3),
        }

    def reset(self):
        self._consecutive_voice = 0


class BargeInAudioManager:
    """
    Gestionnaire d'état audio et d'interruption asynchrone temps réel.
    Garantit qu'une réponse TTS interrompue est immédiatement stoppée, que ses buffers
    sont vidés et qu'aucun fragment audio obsolète (réponse fantôme) n'est émis.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.state: AudioState = AudioState.IDLE
        self.previous_state: Optional[AudioState] = None
        self.current_utterance_id: int = 0
        self.active_tts_task: Optional[asyncio.Task] = None
        self.tts_buffer: deque = deque()
        self.stt_buffer: deque = deque()
        self.history: deque = deque(maxlen=100)
        self.detector = AcousticSpeechDetector()
        self._tts_stop_callbacks: List[Callable[[], Any]] = []
        self._ws_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self.last_barge_in_latency_ms: Optional[float] = None
        self.stop_signal: bool = False

    def set_ws_broadcaster(self, fn: Callable[[Dict[str, Any]], Awaitable[None]]):
        self._ws_broadcaster = fn

    def register_stop_callback(self, fn: Callable[[], Any]):
        self._tts_stop_callbacks.append(fn)

    def transition(self, new_state: AudioState, reason: str = "") -> AudioState:
        with self._lock:
            allowed = VALID_AUDIO_TRANSITIONS.get(self.state, set())
            if new_state not in allowed and new_state != self.state:
                raise ValueError(
                    f"Transition d'état audio illégale : {self.state.value} -> {new_state.value}"
                )
            self.previous_state = self.state
            self.state = new_state
            self.history.append({
                "ts": time.time(),
                "from": self.previous_state.value,
                "to": new_state.value,
                "utterance_id": self.current_utterance_id,
                "reason": reason,
            })
            return self.state

    def begin_utterance(self) -> int:
        """Démarre une nouvelle réponse TTS et retourne son identifiant d'époque."""
        with self._lock:
            self.stop_signal = False
            self.current_utterance_id += 1
            if self.state != AudioState.SPEAKING:
                self.transition(AudioState.SPEAKING, reason="begin_tts")
            return self.current_utterance_id

    def is_utterance_valid(self, utterance_id: int) -> bool:
        """Empêche les réponses audio fantômes après interruption."""
        with self._lock:
            return (not self.stop_signal) and (utterance_id == self.current_utterance_id) and (
                self.state in (AudioState.SPEAKING, AudioState.THINKING)
            )

    def enqueue_tts_chunk(self, utterance_id: int, chunk: bytes) -> bool:
        """Ajoute un fragment TTS uniquement si son époque est toujours active."""
        with self._lock:
            if not self.is_utterance_valid(utterance_id):
                return False
            self.tts_buffer.append((utterance_id, chunk))
            return True

    def flush_obsolete_buffers(self):
        with self._lock:
            self.tts_buffer.clear()

    async def interrupt(self, source: str = "user_voice") -> Dict[str, Any]:
        """
        Déclenche le barge-in : annule la tâche TTS, vide les buffers, émet stop_audio
        aux clients WebSocket et bascule vers LISTENING.
        Mesure la latence réelle entre déclenchement et arrêt complet.
        """
        FEATURE_FLAGS.require_enabled("barge_in_enabled")
        t_start = time.perf_counter()

        with self._lock:
            if self.state == AudioState.INTERRUPTING:
                # Anti-double interruption concurrente
                return {"interrupted": False, "reason": "already_interrupting", "state": self.state.value}

            self.stop_signal = True
            self.current_utterance_id += 1
            prev = self.state
            if prev in (AudioState.SPEAKING, AudioState.THINKING):
                self.transition(AudioState.INTERRUPTING, reason=source)
            self.flush_obsolete_buffers()
            task = self.active_tts_task
            self.active_tts_task = None

        # Annulation propre de la tâche asyncio TTS active
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=0.15)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass

        # Callbacks matériels (ex: pygame.mixer.music.stop)
        for cb in list(self._tts_stop_callbacks):
            try:
                res = cb()
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

        with self._lock:
            self.detector.reset()
            self.stt_buffer.clear()
            if self.state == AudioState.INTERRUPTING:
                self.transition(AudioState.LISTENING, reason="barge_in_resume_stt")
            elif self.state == AudioState.IDLE:
                self.transition(AudioState.LISTENING, reason="start_listen")

        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 3)
        self.last_barge_in_latency_ms = latency_ms
        OBSERVABILITY.record_latency("barge_in_latency_ms", latency_ms)

        if self._ws_broadcaster:
            try:
                await self._ws_broadcaster({
                    "action": "barge_in_stop",
                    "utterance_id": self.current_utterance_id,
                    "state": "listening",
                    "audio_state": self.state.value,
                    "latency_ms": latency_ms,
                })
            except Exception:
                pass

        return {
            "interrupted": True,
            "previous_state": prev.value,
            "state": self.state.value,
            "utterance_id": self.current_utterance_id,
            "latency_ms": latency_ms,
        }


BARGE_IN_MANAGER = BargeInAudioManager()
