#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 6 — FEATURES 02 (VOICE ID) & 03 (ACOUSTIC CONTEXT)
Couvre consentement, chiffrement templates, détection inconnus -> GUEST,
anti-rejeu audio, révocation/suppression et absence de diagnostic médical.
"""

import os
import sys
import tempfile
import unittest
import numpy as np

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.contracts import AliceSecurityError, FeatureDisabledError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import Role
from alice_core.voice.voice_id import VoiceIDManager
from alice_core.voice.acoustic_context import AcousticContextAnalyzer


def _synth_voice(f0: float, harmonics: list, duration: float = 0.4, sr: int = 16000, amp: float = 1200.0, seed: int = 0) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sig = np.zeros_like(t)
    for k, w in enumerate(harmonics, 1):
        sig += w * np.sin(2 * np.pi * (f0 * k) * t)
    rng = np.random.default_rng(seed)
    sig += 0.05 * rng.normal(0, 1, size=t.size)
    return (sig * amp).astype(np.int16)


class TestWave6VoiceIDAndMood(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.tmp.name, "vt.enc")

    def tearDown(self):
        FEATURE_FLAGS.set_flag("voice_biometrics", False, persist=False)
        FEATURE_FLAGS.set_flag("emotion_context", False, persist=False)
        self.tmp.cleanup()

    def test_01_voice_id_consent_encryption_unknown_guest_and_antireplay(self):
        vid = VoiceIDManager(store_file=self.store, similarity_threshold=0.82)

        sig_owner = _synth_voice(125.0, [1.0, 0.7, 0.4, 0.2], seed=1)
        sig_owner_probe = _synth_voice(126.0, [0.98, 0.72, 0.39, 0.21], duration=0.42, seed=2)
        sig_stranger = _synth_voice(295.0, [0.3, 0.2, 0.9, 0.85, 0.7], seed=3)

        # Désactivé par défaut
        with self.assertRaises(FeatureDisabledError):
            vid.enroll_speaker("abou", "Aboubakar", Role.OWNER, sig_owner, consent_granted=True)

        FEATURE_FLAGS.set_flag("voice_biometrics", True, persist=False)

        # Refus sans consentement
        with self.assertRaises(AliceSecurityError):
            vid.enroll_speaker("abou", "Aboubakar", Role.OWNER, sig_owner, consent_granted=False)

        # Enrôlement consenti -> stocké chiffré
        vid.enroll_speaker("abou", "Aboubakar", Role.OWNER, sig_owner, consent_granted=True)
        with open(self.store, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("Aboubakar", raw)
        self.assertNotIn("embedding", raw)

        # Identification légitime (échantillon différent mais même timbre spectral)
        id_ok = vid.identify_speaker(sig_owner_probe)
        self.assertTrue(id_ok["identified"])
        self.assertEqual(id_ok["speaker_id"], "abou")
        # Invariant : jamais suffisant seul pour les actions critiques
        self.assertFalse(id_ok["sufficient_for_sensitive_actions"])

        # Rejeu exact du même buffer audio -> bloqué !
        id_replay = vid.identify_speaker(sig_owner_probe)
        self.assertFalse(id_replay["identified"])
        self.assertTrue(id_replay.get("replay_blocked"))

        # Locuteur inconnu -> GUEST par défaut, jamais d'identité inventée
        id_stranger = vid.identify_speaker(sig_stranger)
        self.assertFalse(id_stranger["identified"])
        self.assertEqual(id_stranger["speaker_id"], "unknown")
        self.assertEqual(id_stranger["role"], Role.GUEST.value)

        # Révocation / suppression effective
        self.assertTrue(vid.delete_or_revoke("abou"))
        sig_owner_probe2 = _synth_voice(125.5, [1.0, 0.7, 0.4, 0.2], duration=0.45, seed=9)
        id_after_rev = vid.identify_speaker(sig_owner_probe2)
        self.assertFalse(id_after_rev["identified"])

    def test_02_acoustic_context_patterns_optout_and_no_medical_claims(self):
        ac = AcousticContextAnalyzer()
        sig_loud = _synth_voice(200.0, [1.0, 0.5], duration=0.5, amp=4500.0, seed=4)
        # Moduler fortement l'enveloppe pour simuler haute intensité / urgence
        mod = np.tile(np.concatenate([np.ones(400), np.full(400, 0.1)]), 10)[:sig_loud.size]
        sig_intense = (sig_loud * mod).astype(np.int16)

        # Opt-in requis
        res_off = ac.analyze(sig_intense)
        self.assertFalse(res_off["enabled"])
        self.assertEqual(res_off["pattern"], "UNKNOWN")

        FEATURE_FLAGS.set_flag("emotion_context", True, persist=False)
        res_on = ac.analyze(sig_intense, user_id="u1")
        self.assertTrue(res_on["enabled"])
        self.assertFalse(res_on["medical_or_psychological_diagnosis"])
        self.assertFalse(res_on["permissions_modified"])
        self.assertIn(res_on["pattern"], ("HIGH_VOCAL_INTENSITY", "URGENT_SPEECH_PATTERN", "CALM"))

        # Opt-out utilisateur
        ac.set_user_opt_out("u1", True)
        self.assertFalse(ac.analyze(sig_intense, user_id="u1")["enabled"])


if __name__ == "__main__":
    unittest.main()
