#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JOURNAL D'AUDIT SÉCURISÉ ET EXPURGATION DE SECRETS (Wave 0).
Garantit qu'aucune clé API, jeton, mot de passe, empreinte vocale brute ou donnée
du coffre-fort n'est jamais écrit en clair dans les logs.
"""

import os
import re
import json
import time
import hashlib
import threading
from typing import Any, Dict, Optional, List


SECRET_KEY_PATTERNS = (
    "token", "secret", "password", "passwd", "api_key", "apikey",
    "private_key", "master_key", "aes_key", "voiceprint", "embedding",
    "biometric", "credential", "authorization", "cookie", "csrf",
    "pin", "rtsp_url", "passphrase", "vault_data"
)

SECRET_VALUE_REGEXES = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{15,}"),
    re.compile(r"sk-[A-Za-z0-9\-_]{16,}"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    re.compile(r"(rtsp://)([^:@/\s]+):([^@/\s]+)@", re.IGNORECASE),
]


def redact_text(text: str) -> str:
    """Expurge les motifs de secrets connus dans une chaîne libre."""
    if not isinstance(text, str):
        return str(text)
    cleaned = text
    for pat in SECRET_VALUE_REGEXES:
        if "rtsp://" in pat.pattern:
            cleaned = pat.sub(r"\1***:***@", cleaned)
        elif "Bearer" in pat.pattern:
            cleaned = pat.sub(r"\1***REDACTED***", cleaned)
        else:
            cleaned = pat.sub("***REDACTED***", cleaned)
    return cleaned


def sanitize_for_log(obj: Any, depth: int = 0) -> Any:
    """Nettoie récursivement dicts/listes/chaînes avant journalisation."""
    if depth > 6:
        return "***TRUNCATED***"
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_low = str(k).lower()
            if any(sk in k_low for sk in SECRET_KEY_PATTERNS):
                sanitized[str(k)] = "***REDACTED***"
            else:
                sanitized[str(k)] = sanitize_for_log(v, depth + 1)
        return sanitized
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_log(x, depth + 1) for x in obj[:50]]
    if isinstance(obj, str):
        return redact_text(obj[:1000])
    if isinstance(obj, bytes):
        return f"<bytes:{len(obj)}>"
    return obj


class AuditLogger:
    """Journal d'audit append-only chaîné par hachage SHA-256."""

    def __init__(self, log_file: Optional[str] = None):
        self._lock = threading.Lock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.log_file = log_file or os.path.join(base_dir, "alice_outputs", "alice_audit.jsonl")
        self._last_hash = "0" * 64
        self._init_last_hash()

    def _init_last_hash(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "rb") as f:
                    lines = f.read().splitlines()
                if lines:
                    last = json.loads(lines[-1].decode("utf-8"))
                    self._last_hash = last.get("entry_hash", self._last_hash)
            except Exception:
                pass

    def log(
        self,
        category: str,
        action: str,
        actor_id: str = "system",
        role: str = "SYSTEM",
        session_id: str = "local",
        outcome: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        safe_details = sanitize_for_log(details or {})
        with self._lock:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            entry_core = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "ts_epoch": round(time.time(), 4),
                "category": str(category),
                "action": redact_text(str(action)),
                "actor_id": str(actor_id),
                "role": str(role),
                "session_id": str(session_id),
                "outcome": str(outcome),
                "details": safe_details,
                "prev_hash": self._last_hash,
            }
            payload_bytes = json.dumps(entry_core, sort_keys=True, ensure_ascii=False).encode("utf-8")
            entry_hash = hashlib.sha256(payload_bytes).hexdigest()
            entry_core["entry_hash"] = entry_hash
            self._last_hash = entry_hash

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_core, ensure_ascii=False) + "\n")
            return entry_core

    def read_recent(self, limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_file):
            return []
        with self._lock:
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                entries = []
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        if category and rec.get("category") != category:
                            continue
                        entries.append(rec)
                        if len(entries) >= limit:
                            break
                    except Exception:
                        continue
                return entries
            except Exception:
                return []


AUDIT_LOGGER = AuditLogger()
