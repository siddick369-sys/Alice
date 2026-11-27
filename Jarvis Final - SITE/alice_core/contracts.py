#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONTRATS TRANSVERSES — Modèles de résultats et exceptions normalisées (Wave 0).
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class AliceSecurityError(PermissionError):
    """Erreur levée lors d'un refus RBAC, d'un flag désactivé ou d'une violation de sécurité."""


class FeatureDisabledError(AliceSecurityError):
    """Erreur levée lorsqu'une fonctionnalité protégée par feature flag est désactivée."""


class AliceDegradedError(RuntimeError):
    """Erreur contrôlée lors d'une panne ou indisponibilité d'un service tiers."""


@dataclass
class ServiceResult:
    """Contrat de réponse standardisé entre tous les modules d'ALICE."""
    success: bool
    status: str  # OK, DEGRADED, UNAVAILABLE, AUTH_REQUIRED, DENIED, UNKNOWN, FAILED
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    degraded: bool = False
    fallback_used: Optional[str] = None
    provenance: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    trace_id: str = field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
