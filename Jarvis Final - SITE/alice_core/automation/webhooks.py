#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 25 — UNIVERSAL AUTOMATION CONNECTOR (ALICE-AUTO-025, Wave 5).
Passerelle Webhooks bidirectionnelle (n8n, Node-RED) avec signatures HMAC-SHA256
en temps constant, horodatage borné, anti-rejeu (nonce), rotation de secrets,
validation stricte du schéma, rate limiting et cloisonnement RBAC.
"""

import os
import json
import hmac
import time
import uuid
import hashlib
import secrets
import threading
import requests
from typing import Dict, Any, Optional, Set, Tuple
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.contracts import AliceSecurityError
from alice_core.security.audit import AUDIT_LOGGER
from alice_web_guard import WEB_GUARD


# Actions interdites via webhooks entrants automatisés sans intervention OWNER directe
FORBIDDEN_WEBHOOK_ACTIONS = {
    "shutdown", "reboot", "system_control", "ha_alarme",
    "vault_read", "vault_write", "supprimer_fichier", "alice_rediger_email"
}


class WebhookGateway:
    """Gestionnaire sécurisé de connecteurs Webhooks HMAC pour n8n / Node-RED."""

    def __init__(self, config_file: Optional[str] = None, replay_ttl_seconds: float = 300.0):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_file = config_file or os.path.join(base_dir, "alice_outputs", "webhook_connectors.json")
        self.replay_ttl_seconds = replay_ttl_seconds
        self.connectors: Dict[str, Dict[str, Any]] = {}
        self._seen_nonces: Dict[str, float] = {}  # f"{connector_id}:{nonce}" -> expires_at
        self._rate_counters: Dict[str, list] = {}  # connector_id -> [ts]
        self._load()

    def _load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.connectors = json.load(f)
            except Exception:
                self.connectors = {}

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            tmp = f"{self.config_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.connectors, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.config_file)

    def register_connector(
        self,
        connector_id: str,
        name: str,
        owner_id: str,
        allowed_actions: Set[str],
        rate_limit_per_min: int = 30,
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        FEATURE_FLAGS.require_enabled("webhook_connector")
        blocked = set(allowed_actions) & FORBIDDEN_WEBHOOK_ACTIONS
        if blocked:
            raise AliceSecurityError(
                f"Sécurité webhook : les actions critiques {sorted(blocked)} ne peuvent être déclenchées par webhook."
            )
        secret = secrets.token_hex(32)
        with self._lock:
            self.connectors[connector_id] = {
                "connector_id": connector_id,
                "name": name,
                "owner_id": owner_id,
                "secret": secret,
                "previous_secret": None,
                "secret_grace_until": 0.0,
                "allowed_actions": sorted(allowed_actions),
                "rate_limit_per_min": int(rate_limit_per_min),
                "target_url": target_url,
                "enabled": True,
                "created_at": time.time(),
            }
            self._save()
        AUDIT_LOGGER.log("WEBHOOK", "connector_registered", actor_id=owner_id, details={"connector_id": connector_id, "name": name})
        return {"connector_id": connector_id, "secret": secret, "allowed_actions": sorted(allowed_actions)}

    def rotate_secret(self, connector_id: str, owner_id: str, grace_seconds: float = 300.0) -> str:
        with self._lock:
            c = self.connectors.get(connector_id)
            if not c or c["owner_id"] != owner_id:
                raise AliceSecurityError("Connecteur introuvable ou accès refusé.")
            new_secret = secrets.token_hex(32)
            c["previous_secret"] = c["secret"]
            c["secret_grace_until"] = time.time() + grace_seconds
            c["secret"] = new_secret
            self._save()
        AUDIT_LOGGER.log("WEBHOOK", "secret_rotated", actor_id=owner_id, details={"connector_id": connector_id})
        return new_secret

    @staticmethod
    def compute_signature(secret: str, timestamp_str: str, nonce: str, raw_body: bytes) -> str:
        msg = f"{timestamp_str}.{nonce}.".encode("utf-8") + raw_body
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def verify_and_parse_incoming(
        self,
        connector_id: str,
        signature_hex: Optional[str],
        timestamp_str: Optional[str],
        nonce: Optional[str],
        raw_body: bytes,
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Valide strictement un webhook entrant :
        FeatureFlag + Signature HMAC temps constant + Horodatage + Nonce anti-rejeu + Rate Limit + Schéma + RBAC.
        """
        if not FEATURE_FLAGS.is_enabled("webhook_connector"):
            return False, 403, {"error": "Connecteur Webhook désactivé."}

        if not connector_id or not signature_hex or not timestamp_str or not nonce:
            return False, 401, {"error": "En-têtes d'authentification HMAC manquants."}

        with self._lock:
            conn = self.connectors.get(connector_id)
            if not conn or not conn.get("enabled"):
                return False, 401, {"error": "Connecteur inconnu ou désactivé."}

            # 1. Validation fenêtre temporelle (anti-rejeu ancien)
            try:
                req_ts = float(timestamp_str)
            except ValueError:
                return False, 400, {"error": "Horodatage invalide."}
            now = time.time()
            if abs(now - req_ts) > self.replay_ttl_seconds:
                return False, 401, {"error": "Horodatage expiré ou trop éloigné."}

            # 2. Validation signature HMAC en temps constant (avec secret actif ou période de grâce rotation)
            expected_cur = self.compute_signature(conn["secret"], timestamp_str, nonce, raw_body)
            sig_ok = hmac.compare_digest(expected_cur, signature_hex.strip().lower())
            if not sig_ok and conn.get("previous_secret") and now <= conn.get("secret_grace_until", 0.0):
                expected_prev = self.compute_signature(conn["previous_secret"], timestamp_str, nonce, raw_body)
                sig_ok = hmac.compare_digest(expected_prev, signature_hex.strip().lower())

            if not sig_ok:
                AUDIT_LOGGER.log("WEBHOOK", "invalid_hmac_rejected", outcome="DENIED", details={"connector_id": connector_id})
                return False, 401, {"error": "Signature HMAC invalide."}

            # 3. Anti-rejeu Nonce
            self._seen_nonces = {k: exp for k, exp in self._seen_nonces.items() if exp > now}
            nonce_key = f"{connector_id}:{nonce}"
            if nonce_key in self._seen_nonces:
                AUDIT_LOGGER.log("WEBHOOK", "replay_attack_blocked", outcome="DENIED", details={"connector_id": connector_id, "nonce": nonce})
                return False, 409, {"error": "Rejeu détecté (nonce déjà consommé)."}
            self._seen_nonces[nonce_key] = now + self.replay_ttl_seconds

            # 4. Rate Limiting par connecteur
            hits = [t for t in self._rate_counters.get(connector_id, []) if now - t < 60.0]
            if len(hits) >= conn.get("rate_limit_per_min", 30):
                return False, 429, {"error": "Limite de débit Webhook dépassée."}
            hits.append(now)
            self._rate_counters[connector_id] = hits

            # 5. Validation stricte du schéma JSON
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                return False, 400, {"error": "Corps JSON malformé."}

            if not isinstance(payload, dict) or not isinstance(payload.get("action"), str):
                return False, 400, {"error": "Schéma invalide : champ 'action' requis."}

            action = payload["action"].strip()
            if action in FORBIDDEN_WEBHOOK_ACTIONS or action not in conn.get("allowed_actions", []):
                AUDIT_LOGGER.log("WEBHOOK", "action_scope_denied", outcome="DENIED", details={"connector_id": connector_id, "action": action})
                return False, 403, {"error": f"Action '{action}' non autorisée pour ce connecteur."}

            AUDIT_LOGGER.log("WEBHOOK", "incoming_accepted", actor_id=connector_id, outcome="OK", details={"action": action})
            return True, 200, {"success": True, "connector_id": connector_id, "action": action, "data": payload.get("data", {})}

    def emit_outgoing(self, connector_id: str, event_name: str, data: Dict[str, Any], allow_lan_override: bool = False) -> Dict[str, Any]:
        """Émet un webhook signé HMAC vers un service externe validé par WebGuard."""
        FEATURE_FLAGS.require_enabled("webhook_connector")
        with self._lock:
            conn = self.connectors.get(connector_id)
        if not conn or not conn.get("target_url"):
            return {"success": False, "error": "Connecteur ou URL cible non configuré."}

        url = conn["target_url"]
        if not allow_lan_override:
            safe, reason = WEB_GUARD.is_safe_url(url)
            if not safe:
                return {"success": False, "error": f"URL webhook refusée par WebGuard : {reason}"}

        body_bytes = json.dumps({"event": event_name, "data": data}, ensure_ascii=False).encode("utf-8")
        ts_str = str(int(time.time()))
        nonce = uuid.uuid4().hex[:12]
        sig = self.compute_signature(conn["secret"], ts_str, nonce, body_bytes)

        try:
            r = requests.post(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Alice-Timestamp": ts_str,
                    "X-Alice-Nonce": nonce,
                    "X-Alice-Signature": sig,
                },
                timeout=5.0,
            )
            return {"success": r.status_code < 400, "http_code": r.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}


WEBHOOK_GATEWAY = WebhookGateway()
