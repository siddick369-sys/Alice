#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE FLAGS REGISTRY — Contrôle centralisé et sécuritaire côté backend (Section 8).
Les fonctionnalités sensibles (biométrie, surveillance, automatisation, coffre-fort,
webhooks, web autonome) sont désactivées par défaut jusqu'à configuration explicite.
"""

import os
import json
import threading
from dataclasses import dataclass
from typing import Dict, Any, Optional
from alice_core.contracts import FeatureDisabledError


@dataclass(frozen=True)
class FeatureFlagSpec:
    name: str
    default: bool
    category: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    requires_consent: bool = False


FLAG_SPECS: Dict[str, FeatureFlagSpec] = {
    "barge_in_enabled": FeatureFlagSpec(
        "barge_in_enabled", True, "voice", "LOW",
        "Interruption vocale temps réel pendant la lecture TTS."
    ),
    "whisper_mode_enabled": FeatureFlagSpec(
        "whisper_mode_enabled", True, "voice", "LOW",
        "Détection du chuchotement et profil de sortie nocturne."
    ),
    "followup_listen_enabled": FeatureFlagSpec(
        "followup_listen_enabled", True, "voice", "LOW",
        "Fenêtre d'écoute continue configurable (5s) après réponse."
    ),
    "voice_biometrics": FeatureFlagSpec(
        "voice_biometrics", False, "voice", "CRITICAL",
        "Identification biométrique multi-locuteurs (Voice ID). Désactivée par défaut.",
        requires_consent=True
    ),
    "emotion_context": FeatureFlagSpec(
        "emotion_context", False, "voice", "MEDIUM",
        "Analyse acoustique probabiliste du ton (sans diagnostic médical).",
        requires_consent=True
    ),
    "predictive_automation": FeatureFlagSpec(
        "predictive_automation", False, "iot", "HIGH",
        "Routines domotiques prédictives, délestage et régulation thermique.",
        requires_consent=True
    ),
    "presence_simulation": FeatureFlagSpec(
        "presence_simulation", False, "iot", "HIGH",
        "Simulation de présence dynamique en mode absence explicite.",
        requires_consent=True
    ),
    "video_monitoring": FeatureFlagSpec(
        "video_monitoring", False, "vision", "CRITICAL",
        "Surveillance vidéo RTSP et zones de sécurité virtuelles.",
        requires_consent=True
    ),
    "visual_memory": FeatureFlagSpec(
        "visual_memory", False, "vision", "HIGH",
        "Indexation temporelle d'observations visuelles avec rétention bornée.",
        requires_consent=True
    ),
    "agent_swarm": FeatureFlagSpec(
        "agent_swarm", True, "agents", "MEDIUM",
        "Délégation bornée à des agents spécialisés sur l'orchestrateur 9 états."
    ),
    "web_automation": FeatureFlagSpec(
        "web_automation", False, "agents", "HIGH",
        "Agent web autonome encadré par WebGuard anti-SSRF.",
        requires_consent=True
    ),
    "webhook_connector": FeatureFlagSpec(
        "webhook_connector", False, "automation", "HIGH",
        "Passerelle Webhooks HMAC-SHA256 pour n8n / Node-RED.",
        requires_consent=True
    ),
    "offline_sync": FeatureFlagSpec(
        "offline_sync", True, "mobile", "LOW",
        "Synchronisation PWA hors connexion (données non confidentielles uniquement)."
    ),
    "encrypted_vault": FeatureFlagSpec(
        "encrypted_vault", False, "security", "CRITICAL",
        "Coffre-fort chiffré AES-256-GCM isolé du RAG et du LLM.",
        requires_consent=True
    ),
}


class FeatureFlagManager:
    """Gestionnaire backend centralisé des Feature Flags avec persistance sécurisée."""

    def __init__(self, state_file: Optional[str] = None):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.state_file = state_file or os.path.join(base_dir, "alice_outputs", "feature_flags.json")
        self._overrides: Dict[str, bool] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if k in FLAG_SPECS and isinstance(v, bool):
                            self._overrides[k] = v
            except Exception:
                self._overrides = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = f"{self.state_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._overrides, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.state_file)
        except Exception:
            pass

    def is_enabled(self, flag_name: str) -> bool:
        if flag_name not in FLAG_SPECS:
            raise KeyError(f"Feature flag inconnu : {flag_name}")
        # Variable d'environnement prioritaire (ex: ALICE_FLAG_VOICE_BIOMETRICS=1)
        env_key = f"ALICE_FLAG_{flag_name.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val.strip().lower() in ("1", "true", "yes", "on")

        with self._lock:
            if flag_name in self._overrides:
                return self._overrides[flag_name]
            return FLAG_SPECS[flag_name].default

    def set_flag(self, flag_name: str, enabled: bool, persist: bool = True) -> bool:
        if flag_name not in FLAG_SPECS:
            raise KeyError(f"Feature flag inconnu : {flag_name}")
        if not isinstance(enabled, bool):
            raise ValueError("La valeur d'un feature flag doit être booléenne.")
        with self._lock:
            self._overrides[flag_name] = enabled
            if persist:
                self._save()
        return enabled

    def reset_to_defaults(self, persist: bool = True):
        with self._lock:
            self._overrides.clear()
            if persist:
                self._save()

    def require_enabled(self, flag_name: str):
        """Vérifie strictement côté backend qu'une fonctionnalité est active."""
        if not self.is_enabled(flag_name):
            spec = FLAG_SPECS[flag_name]
            raise FeatureDisabledError(
                f"Fonctionnalité '{flag_name}' désactivée par politique de sécurité backend ({spec.risk_level})."
            )

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        res = {}
        for name, spec in FLAG_SPECS.items():
            res[name] = {
                "enabled": self.is_enabled(name),
                "default": spec.default,
                "category": spec.category,
                "risk_level": spec.risk_level,
                "requires_consent": spec.requires_consent,
                "description": spec.description,
            }
        return res


FEATURE_FLAGS = FeatureFlagManager()
