#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 15 — COMMITMENT TRACKER (ALICE-MEM-015, Wave 2).
Détecte les engagements formulés dans les conversations et emails autorisés.
Cycle d'états : DETECTED -> REVIEW_REQUIRED -> CONFIRMED -> SCHEDULED -> COMPLETED (ou REJECTED).
Filtre strictement les hypothèses et les citations rapportées.
"""

import os
import re
import json
import time
import uuid
import threading
from enum import Enum
from typing import Dict, Any, List, Optional


class CommitmentState(str, Enum):
    DETECTED = "DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


COMMITMENT_PATTERNS = [
    re.compile(
        r"\b(?:je\s+(?:vais|t['’]envoie|t['’]appellerai|te\s+rappelle|rappelle|termine|finis|envoie|prépare|fais|livrerai|enverrai)|"
        r"on\s+se\s+voit|n['’]oublie\s+pas\s+de)\s+([^.!?]+)",
        re.IGNORECASE,
    )
]

HYPOTHETICAL_MARKERS = (
    "si je", "peut-être", "peut etre", "au cas où", "éventuellement",
    "j'hésite", "pourrait", "serait-il possible", "imaginer", "supposons"
)

DEADLINE_PATTERN = re.compile(
    r"\b(demain|aujourd['’]hui|ce soir|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|"
    r"la semaine prochaine|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}h\d{0,2})\b",
    re.IGNORECASE,
)


class CommitmentTracker:
    """Gestionnaire d'engagements et rappels contextuels avec validation humaine."""

    def __init__(self, storage_file: Optional[str] = None):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.storage_file = storage_file or os.path.join(base_dir, "alice_outputs", "commitments.json")
        self.commitments: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.commitments = json.load(f)
            except Exception:
                self.commitments = {}

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            tmp = f"{self.storage_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.commitments, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.storage_file)

    @staticmethod
    def _is_quoted_or_hypothetical(sentence: str) -> bool:
        s = sentence.strip()
        s_low = s.lower()
        if s.startswith(">") or ('"' in s and s.count('"') >= 2) or ("«" in s and "»" in s):
            return True
        if any(h in s_low for h in ("il a dit que", "elle m'a écrit", "dans l'article", "selon le rapport")):
            return True
        if any(h in s_low for h in HYPOTHETICAL_MARKERS):
            return True
        return False

    def analyze_text(
        self,
        text: str,
        author: str,
        recipient: str = "self",
        owner_id: str = "owner_local",
        source: str = "conversation",
    ) -> List[Dict[str, Any]]:
        """Extrait des engagements authentiques en rejetant citations et hypothèses."""
        if not text or not text.strip():
            return []

        created = []
        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if s.strip()]
        for sent in sentences:
            if self._is_quoted_or_hypothetical(sent):
                continue

            for pat in COMMITMENT_PATTERNS:
                m = pat.search(sent)
                if m:
                    dl_match = DEADLINE_PATTERN.search(sent)
                    deadline = dl_match.group(1) if dl_match else None
                    conf = 0.85 if deadline else 0.68
                    item = {
                        "commitment_id": f"cmt_{uuid.uuid4().hex[:10]}",
                        "owner_id": owner_id,
                        "author": author,
                        "recipient": recipient,
                        "commitment": sent,
                        "deadline": deadline,
                        "context": text[:200],
                        "source": source,
                        "confidence": conf,
                        "status": CommitmentState.REVIEW_REQUIRED.value,
                        "created_at": time.time(),
                        "scheduled_for": None,
                    }
                    with self._lock:
                        self.commitments[item["commitment_id"]] = item
                        self._save()
                    created.append(item)
                    break
        return created

    def transition(self, commitment_id: str, new_state: CommitmentState, owner_id: str, deadline: Optional[str] = None, commitment_text: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            item = self.commitments.get(commitment_id)
            if not item:
                raise KeyError("Engagement introuvable.")
            if item["owner_id"] != owner_id and owner_id != "owner_local":
                raise PermissionError("Isolation utilisateur : engagement d'un autre utilisateur.")
            if deadline is not None:
                item["deadline"] = deadline
            if commitment_text is not None:
                item["commitment"] = commitment_text
            item["status"] = new_state.value
            if new_state == CommitmentState.SCHEDULED:
                item["scheduled_for"] = item.get("deadline") or "unscheduled_reminder"
            self._save()
            return item

    def list_for_owner(self, owner_id: str, include_rejected: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                c for c in self.commitments.values()
                if (c["owner_id"] == owner_id or owner_id == "owner_local")
                and (include_rejected or c["status"] != CommitmentState.REJECTED.value)
            ]


COMMITMENT_TRACKER = CommitmentTracker()
