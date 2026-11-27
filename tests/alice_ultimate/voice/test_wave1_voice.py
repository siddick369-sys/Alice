#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 1 — PILIER 1 VOIX (01 BARGE-IN, 04 WHISPER MODE, 05 FOLLOW-UP LISTEN)
Couvre interruptions concurrentes, écho, réponses fantômes, chuchotement vs voix faible et expirations.
"""

import os
import sys
import asyncio
import unittest
import numpy as np
from datetime import datetime

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.voice.pipeline import BargeInAudioManager, AudioState, AcousticSpeechDetector
from alice_core.voice.whisper_mode import WhisperModeManager
from alice_core.voice.followup import FollowUpListenManager


class TestWave1Voice(unittest.TestCase):

    def test_01_barge_in_state_machine_and_phantom_prevention(self):
        async def run():
            mgr = BargeInAudioManager()
            events = []
            stopped_flag = {"called": False}

            async def mock_ws(ev):
                events.append(ev)

            mgr.set_ws_broadcaster(mock_ws)
            mgr.register_stop_callback(lambda: stopped_flag.__setitem__("called", True))

            mgr.transition(AudioState.LISTENING)
            mgr.transition(AudioState.THINKING)
            utt1 = mgr.begin_utterance()
            self.assertEqual(mgr.state, AudioState.SPEAKING)
            self.assertTrue(mgr.enqueue_tts_chunk(utt1, b"chunk1"))

            async def long_tts():
                await asyncio.sleep(2.0)

            mgr.active_tts_task = asyncio.create_task(long_tts())

            # Interruption
            res = await mgr.interrupt("user_voice")
            self.assertTrue(res["interrupted"])
            self.assertEqual(mgr.state, AudioState.LISTENING)
            self.assertTrue(stopped_flag["called"])
            self.assertEqual(len(mgr.tts_buffer), 0)  # Buffers vidés
            self.assertFalse(mgr.enqueue_tts_chunk(utt1, b"phantom"))  # Bloque réponse fantôme
            self.assertFalse(mgr.is_utterance_valid(utt1))
            self.assertGreaterEqual(res["latency_ms"], 0.0)
            self.assertTrue(any(e["action"] == "barge_in_stop" for e in events))

        asyncio.run(run())

    def test_02_repeated_concurrent_barge_in_and_illegal_transition(self):
        mgr = BargeInAudioManager()
        # IDLE -> SPEAKING autorisé, mais LISTENING -> INTERRUPTING interdit directement
        mgr.transition(AudioState.LISTENING)
        with self.assertRaises(ValueError):
            mgr.transition(AudioState.INTERRUPTING)

        async def run_conc():
            mgr2 = BargeInAudioManager()
            mgr2.begin_utterance()
            r1, r2 = await asyncio.gather(mgr2.interrupt("v1"), mgr2.interrupt("v2"))
            # Au moins une interruption réussit et l'état final reste sain (LISTENING)
            self.assertTrue(r1["interrupted"] or r2["interrupted"])
            self.assertEqual(mgr2.state, AudioState.LISTENING)

        asyncio.run(run_conc())

    def test_03_acoustic_echo_and_silence_rejection(self):
        det = AcousticSpeechDetector(sample_rate=16000, base_noise_floor=200.0, echo_margin=2.0)
        # Silence complet
        silence = np.zeros(1600, dtype=np.int16)
        self.assertFalse(det.evaluate_barge_in_frame(silence, is_tts_playing=True, tts_echo_rms=600.0)["triggered"])

        # Écho TTS à 650 RMS (< 600 * 2.0 = 1200) -> rejeté
        t = np.linspace(0, 0.1, 1600, endpoint=False)
        echo_sig = (900 * np.sin(2 * np.pi * 600 * t)).astype(np.int16)
        r_echo = det.evaluate_barge_in_frame(echo_sig, is_tts_playing=True, tts_echo_rms=600.0)
        self.assertFalse(r_echo["triggered"])

        # Voix humaine forte à 2500 RMS dans la bande vocale sur 2 trames -> déclenchée
        human_sig = (3500 * np.sin(2 * np.pi * 550 * t)).astype(np.int16)
        det.evaluate_barge_in_frame(human_sig, is_tts_playing=True, tts_echo_rms=600.0)
        r_human = det.evaluate_barge_in_frame(human_sig, is_tts_playing=True, tts_echo_rms=600.0)
        self.assertTrue(r_human["triggered"])

    def test_04_whisper_detection_vs_quiet_voiced_and_volume_cap(self):
        wm = WhisperModeManager()
        sr = 16000
        t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)

        # Voix faible mais périodique (harmonique pure 150 Hz + 300 Hz)
        quiet_voiced = (350 * np.sin(2 * np.pi * 150 * t) + 180 * np.sin(2 * np.pi * 300 * t)).astype(np.int16)
        res_voiced = wm.detect_whisper_audio(quiet_voiced, sr)
        self.assertFalse(res_voiced["is_whisper"])

        # Chuchotement simulé : bruit blanc filtré hautes fréquences sans périodicité harmonique
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 1, size=t.size)
        # Filtre passe-haut simple (différence d'ordre 1) pour simuler friction aspirée
        whisper_sig = (np.diff(noise, prepend=noise[0]) * 350).astype(np.int16)
        res_whisper = wm.detect_whisper_audio(whisper_sig, sr)
        self.assertTrue(res_whisper["is_whisper"])

        # Profil TTS : en nuit (23h) ou chuchotement, volume plafonné (jamais augmenté)
        prof_night = wm.get_tts_profile(detected_whisper=False, requested_volume=0.9, now=datetime(2026, 11, 24, 23, 15))
        self.assertTrue(prof_night["whisper_active"])
        self.assertLessEqual(prof_night["volume"], wm.max_whisper_volume)

        # Volume demandé très bas (0.1) ne doit JAMAIS être augmenté
        prof_low = wm.get_tts_profile(detected_whisper=True, requested_volume=0.1, now=datetime(2026, 11, 24, 14, 0))
        self.assertEqual(prof_low["volume"], 0.1)

    def test_05_followup_listen_window_expiry_and_noise_rejection(self):
        async def run():
            fm = FollowUpListenManager(default_window_seconds=1.2)
            emitted = []

            async def bcast(sid, ev):
                emitted.append((sid, ev))

            fm.set_broadcaster(bcast)
            st = await fm.open_window("sess_fu", "MEMBER", context_topic="météo")
            self.assertTrue(st["active"])
            self.assertTrue(st["visible_indicator"])

            # Bruit accidentel rejeté
            r_noise = fm.accept_transcript("sess_fu", "euh")
            self.assertFalse(r_noise["accepted"])

            # Question valide acceptée et fenêtre fermée
            r_valid = fm.accept_transcript("sess_fu", "et pour demain matin")
            self.assertTrue(r_valid["accepted"])
            self.assertEqual(r_valid["role"], "MEMBER")

            # Nouvelle fenêtre qui expire naturellement
            await fm.open_window("sess_fu2", "GUEST")
            await asyncio.sleep(1.35)
            r_exp = fm.accept_transcript("sess_fu2", "allume la lumière")
            self.assertFalse(r_exp["accepted"])
            self.assertTrue(any(e[0] == "sess_fu2" and not e[1]["active"] for e in emitted))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
