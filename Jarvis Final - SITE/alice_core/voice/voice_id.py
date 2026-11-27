#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 02 — VOICE ID / MULTI-SPEAKER (ALICE-VOICE-002, Wave 6).
Identification probabiliste des locuteurs par empreintes acoustiques spectrales locales (NumPy),
stockées chiffrées AES-256-GCM, avec consentement explicite, rétention configurable,
suppression/révocation effective, anti-rejeu audio et isolation RBAC stricte :
- Un locuteur inconnu reçoit le rôle GUEST par défaut (zéro usurpation d'identité).
- L'identification vocale ne suffit JAMAIS seule à autoriser une action critique.
"""

import os
import json
import time
import base64
import hashlib
import threading
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Dict, Any, Optional, List
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.contracts import AliceSecurityError
from alice_core.security.rbac import Role
from alice_core.security.audit import AUDIT_LOGGER


class VoiceIDManager:
    """Gestionnaire biométrique vocal local chiffré avec anti-rejeu."""

    EMBEDDING_DIM = 36

    def __init__(
        self,
        store_file: Optional[str] = None,
        similarity_threshold: float = 0.84,
        retention_days: float = 90.0,
    ):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.store_file = store_file or os.path.join(base_dir, "alice_outputs", "secure_vault", "voice_templates.enc")
        self.similarity_threshold = similarity_threshold
        self.retention_days = retention_days
        # Clé AES-256 éphémère de session / fournie via env ; jamais loggée ni écrite en clair dans le dépôt
        env_key_b64 = os.environ.get("ALICE_BIOMETRIC_KEY_B64")
        if env_key_b64:
            self._key = base64.b64decode(env_key_b64)[:32].ljust(32, b"\x00")
        else:
            self._key = os.urandom(32)
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.revoked_speakers: set = set()
        self._recent_audio_hashes: Dict[str, float] = {}  # Anti-rejeu audio exact
        self._load()

    def _encrypt_profiles(self, obj: Dict[str, Any]) -> Dict[str, str]:
        nonce = os.urandom(12)
        aes = AESGCM(self._key)
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        ct = aes.encrypt(nonce, raw, b"alice_voice_templates_v1")
        return {"nonce": base64.b64encode(nonce).decode("ascii"), "ct": base64.b64encode(ct).decode("ascii")}

    def _decrypt_profiles(self, blob: Dict[str, str]) -> Dict[str, Any]:
        aes = AESGCM(self._key)
        nonce = base64.b64decode(blob["nonce"])
        ct = base64.b64decode(blob["ct"])
        raw = aes.decrypt(nonce, ct, b"alice_voice_templates_v1")
        return json.loads(raw.decode("utf-8"))

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
            blob = self._encrypt_profiles({"profiles": self.profiles, "revoked": sorted(self.revoked_speakers)})
            tmp = f"{self.store_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(blob, f)
            os.replace(tmp, self.store_file)

    def _load(self):
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    blob = json.load(f)
                data = self._decrypt_profiles(blob)
                self.profiles = data.get("profiles", {})
                self.revoked_speakers = set(data.get("revoked", []))
            except Exception:
                self.profiles = {}

    @classmethod
    def extract_embedding(cls, pcm_int16: np.ndarray, sample_rate: int = 16000) -> List[float]:
        """Calcule un vecteur spectral local logarithmique (36 bandes Mel-approximées normalisées L2)."""
        if pcm_int16.size < 400:
            raise ValueError("Échantillon vocal trop court pour extraction.")
        arr = pcm_int16.astype(np.float64)
        arr = arr - np.mean(arr)
        rms = float(np.sqrt(np.mean(arr ** 2)))
        if rms < 40.0:
            raise ValueError("Signal vocal trop faible ou silencieux.")
        arr = arr / (rms + 1e-9)

        win = arr * np.hanning(arr.size)
        spec = np.abs(np.fft.rfft(win)) + 1e-9
        freqs = np.fft.rfftfreq(arr.size, d=1.0 / sample_rate)

        # 36 bandes réparties logarithmiquement entre 80 Hz et 7500 Hz
        edges = np.geomspace(80.0, min(7500.0, sample_rate / 2.0 - 10), cls.EMBEDDING_DIM + 1)
        vec = np.zeros(cls.EMBEDDING_DIM, dtype=np.float32)
        for i in range(cls.EMBEDDING_DIM):
            mask = (freqs >= edges[i]) & (freqs < edges[i + 1])
            band_energy = float(np.mean(spec[mask])) if np.any(mask) else 1e-9
            vec[i] = np.log1p(band_energy)

        # Centrage et normalisation L2 pour invariance de gain/micro
        vec = vec - np.mean(vec)
        norm = float(np.linalg.norm(vec))
        if norm > 1e-9:
            vec = vec / norm
        return [round(float(x), 6) for x in vec]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        va = np.asarray(a, dtype=np.float32)
        vb = np.asarray(b, dtype=np.float32)
        na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
        if na < 1e-9 or nb < 1e-9:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))

    def enroll_speaker(
        self,
        speaker_id: str,
        display_name: str,
        role: Role,
        pcm_int16: np.ndarray,
        sample_rate: int = 16000,
        consent_granted: bool = False,
    ) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("voice_biometrics")
        if not consent_granted:
            raise AliceSecurityError("Enrôlement vocal refusé : consentement biométrique explicite requis.")
        emb = self.extract_embedding(pcm_int16, sample_rate)
        now = time.time()
        with self._lock:
            self.revoked_speakers.discard(speaker_id)
            self.profiles[speaker_id] = {
                "speaker_id": speaker_id,
                "display_name": display_name,
                "role": role.value,
                "embedding": emb,
                "consent_timestamp": now,
                "expires_at": now + (self.retention_days * 86400.0),
            }
            self._save()
        # Audit sans AUCUNE empreinte vocale brute !
        AUDIT_LOGGER.log("VOICE_ID", "speaker_enrolled", actor_id=speaker_id, role=role.value, outcome="OK")
        return {"enrolled": True, "speaker_id": speaker_id, "role": role.value, "encrypted_at_rest": True}

    def delete_or_revoke(self, speaker_id: str) -> bool:
        with self._lock:
            existed = speaker_id in self.profiles
            self.profiles.pop(speaker_id, None)
            self.revoked_speakers.add(speaker_id)
            self._save()
        AUDIT_LOGGER.log("VOICE_ID", "speaker_revoked_deleted", actor_id=speaker_id, outcome="OK")
        return existed

    def purge_expired_profiles(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            expired = [sid for sid, p in self.profiles.items() if now > p.get("expires_at", 0)]
            for sid in expired:
                del self.profiles[sid]
                removed += 1
            if removed:
                self._save()
        return removed

    def identify_speaker(self, pcm_int16: np.ndarray, sample_rate: int = 16000, allow_replay_check: bool = True) -> Dict[str, Any]:
        """
        Identifie un locuteur probabilistement.
        - En cas d'audio rejoué identique -> bloque pour anti-rejeu.
        - En cas de confiance insuffisante -> retourne speaker_id='unknown', role=GUEST.
        - L'identification vocale retourne sufficient_for_sensitive_actions=False.
        """
        FEATURE_FLAGS.require_enabled("voice_biometrics")
        self.purge_expired_profiles()

        # Anti-rejeu audio exact (même buffer PCM exact soumis à répétition)
        audio_digest = hashlib.sha256(pcm_int16.tobytes()).hexdigest()
        now = time.time()
        with self._lock:
            self._recent_audio_hashes = {k: ts for k, ts in self._recent_audio_hashes.items() if now - ts < 300.0}
            if allow_replay_check and audio_digest in self._recent_audio_hashes:
                AUDIT_LOGGER.log("VOICE_ID", "audio_replay_detected", outcome="DENIED")
                return {
                    "identified": False,
                    "speaker_id": "unknown",
                    "role": Role.GUEST.value,
                    "confidence": 0.0,
                    "replay_blocked": True,
                    "sufficient_for_sensitive_actions": False,
                }
            self._recent_audio_hashes[audio_digest] = now

        try:
            probe_emb = self.extract_embedding(pcm_int16, sample_rate)
        except ValueError as e:
            return {
                "identified": False,
                "speaker_id": "unknown",
                "role": Role.GUEST.value,
                "confidence": 0.0,
                "reason": str(e),
                "sufficient_for_sensitive_actions": False,
            }

        best_sid = None
        best_prof = None
        best_sim = -1.0
        with self._lock:
            for sid, prof in self.profiles.items():
                if sid in self.revoked_speakers:
                    continue
                sim = self._cosine(probe_emb, prof["embedding"])
                if sim > best_sim:
                    best_sim = sim
                    best_sid = sid
                    best_prof = prof

        if not best_prof or best_sim < self.similarity_threshold:
            return {
                "identified": False,
                "speaker_id": "unknown",
                "role": Role.GUEST.value,  # Locuteur inconnu -> permissions GUEST par défaut
                "confidence": round(max(0.0, best_sim), 3),
                "sufficient_for_sensitive_actions": False,
            }

        return {
            "identified": True,
            "speaker_id": best_sid,
            "display_name": best_prof["display_name"],
            "role": best_prof["role"],
            "confidence": round(best_sim, 3),
            # Invariant impératif : Voice ID ne suffit JAMAIS seul aux actions sensibles !
            "sufficient_for_sensitive_actions": False,
        }


VOICE_ID_MANAGER = VoiceIDManager()
