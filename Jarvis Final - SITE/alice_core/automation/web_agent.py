#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 23 — AUTONOMOUS WEB AGENT (ALICE-AUTO-023, Wave 5).
Automatise les suivis Web autorisés (surveillance prix, disponibilité, suivi colis)
avec contrôle strict SSRF à chaque saut de redirection, blocage CAPTCHA/MFA sans contournement,
limite de téléchargement et distinction stricte entre action préparée et exécutée.
"""

import re
import time
import socket
import urllib.parse
import requests
import urllib3.util.connection as urllib3_conn
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from alice_web_guard import WEB_GUARD, STATUS_PAGE_INACCESSIBLE, STATUS_SEARCH_PERFORMED
from alice_core.feature_flags import FEATURE_FLAGS


@contextmanager
def _pin_dns_to_validated_ips(expected_host: str, pinned_ips: List[str]):
    """
    Empêche tout DNS rebinding (TOCTOU) entre resolve_and_validate_url() et requests.get()
    en forçant urllib3 à se connecter uniquement aux IP déjà validées, tout en conservant
    Host et SNI/TLS intacts.
    """
    orig_create = urllib3_conn.create_connection
    pinned_ip = pinned_ips[0]

    def _pinned_create_connection(address, *args, **kwargs):
        host, port = address
        if str(host).lower() == expected_host.lower():
            return orig_create((pinned_ip, port), *args, **kwargs)
        raise RuntimeError(f"Connexion vers hôte inattendu bloquée : {host}")

    urllib3_conn.create_connection = _pinned_create_connection
    try:
        yield
    finally:
        urllib3_conn.create_connection = orig_create


FORBIDDEN_DOWNLOAD_EXTS = (".exe", ".msi", ".bat", ".ps1", ".cmd", ".vbs", ".sh", ".dll", ".scr")
CAPTCHA_MFA_MARKERS = (
    "recaptcha", "hcaptcha", "cf-turnstile", "verify you are human",
    "vérifier que vous êtes humain", "two-factor", "one-time password", "mfa", "captcha"
)


class AutonomousWebAgent:
    """Agent Web autonome sécurisé (zéro contournement CAPTCHA/MFA, zéro transaction automatique)."""

    MAX_REDIRECTS = 4
    MAX_BYTES = 2 * 1024 * 1024  # 2 Mo
    REQUEST_TIMEOUT = 8.0

    @staticmethod
    def _validate_target(url: str):
        safe, reason = WEB_GUARD.is_safe_url(url)
        if not safe:
            return False, reason
        parsed = urllib.parse.urlparse(url)
        if parsed.path.lower().endswith(FORBIDDEN_DOWNLOAD_EXTS):
            return False, f"Téléchargement potentiellement malveillant interdit ({parsed.path})."
        return True, "OK"

    def fetch_safe(self, url: str, session_cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Récupère une page en validant chaque saut de redirection via WEB_GUARD."""
        FEATURE_FLAGS.require_enabled("web_automation")
        current_url = url.strip()
        visited_hops: List[str] = []

        for hop in range(self.MAX_REDIRECTS + 1):
            ok, reason, validated_ips = WEB_GUARD.resolve_and_validate_url(current_url)
            if not ok:
                return {"success": False, "status": "BLOCKED_SSRF_OR_UNSAFE", "error": reason, "hops": visited_hops}
            parsed_hop = urllib.parse.urlparse(current_url)
            if parsed_hop.path.lower().endswith(FORBIDDEN_DOWNLOAD_EXTS):
                return {"success": False, "status": "BLOCKED_SSRF_OR_UNSAFE", "error": f"Téléchargement potentiellement malveillant interdit ({parsed_hop.path}).", "hops": visited_hops}
            visited_hops.append(current_url)

            try:
                with _pin_dns_to_validated_ips(parsed_hop.hostname or "", validated_ips):
                    resp = requests.get(
                        current_url,
                        timeout=self.REQUEST_TIMEOUT,
                        allow_redirects=False,
                        headers={"User-Agent": "ALICE-SafeWebAgent/1.0"},
                        stream=True,
                    )
            except Exception as e:
                return {"success": False, "status": STATUS_PAGE_INACCESSIBLE, "error": str(e), "hops": visited_hops}

            # Validation des redirections saut par saut
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                resp.close()
                if not loc:
                    return {"success": False, "status": STATUS_PAGE_INACCESSIBLE, "error": "Redirection vide."}
                current_url = urllib.parse.urljoin(current_url, loc)
                continue

            if resp.status_code in (401, 403):
                resp.close()
                return {
                    "success": False,
                    "status": "BLOCKED_ACCESS_CONTROL",
                    "http_code": resp.status_code,
                    "message": "Accès refusé par le site (authentification ou restriction). Aucun contournement tenté.",
                }

            # Limite stricte de taille
            chunks = []
            total = 0
            for ch in resp.iter_content(chunk_size=16384):
                total += len(ch)
                if total > self.MAX_BYTES:
                    resp.close()
                    return {"success": False, "status": "ABORTED_SIZE_LIMIT", "error": "Réponse > 2 Mo."}
                chunks.append(ch)
            body = b"".join(chunks).decode("utf-8", errors="ignore")
            resp.close()

            body_low = body.lower()
            if any(m in body_low for m in CAPTCHA_MFA_MARKERS):
                return {
                    "success": False,
                    "status": "BLOCKED_CAPTCHA_OR_MFA",
                    "url": current_url,
                    "message": "Protection anti-bot (CAPTCHA) ou MFA détectée. Intervention humaine requise (zéro contournement).",
                }

            return {
                "success": True,
                "status": STATUS_SEARCH_PERFORMED,
                "url": current_url,
                "http_code": resp.status_code,
                "hops": visited_hops,
                "content": f"<untrusted_web_content>{body[:15000]}</untrusted_web_content>",
                "raw_excerpt": re.sub(r"<[^>]+>", " ", body)[:1500].strip(),
            }

        return {"success": False, "status": "ABORTED_TOO_MANY_REDIRECTS", "hops": visited_hops}

    def prepare_engaging_action(self, action_type: str, target_url: str, details: Dict[str, Any], user_confirmed: bool = False) -> Dict[str, Any]:
        """Distingue formellement la préparation d'une réservation/achat de son exécution confirmée."""
        FEATURE_FLAGS.require_enabled("web_automation")
        ok, reason = self._validate_target(target_url)
        if not ok:
            return {"success": False, "status": "BLOCKED_UNSAFE_URL", "error": reason}

        if not user_confirmed:
            return {
                "success": True,
                "status": "PREPARED_REQUIRES_CONFIRMATION",
                "executed": False,
                "action_type": action_type,
                "target_url": target_url,
                "details": details,
                "message": f"Action '{action_type}' préparée uniquement. Confirmation explicite requise avant validation.",
            }

        return {
            "success": True,
            "status": "CONFIRMED_READY_FOR_USER_HANDOFF",
            "executed": False,
            "action_type": action_type,
            "target_url": target_url,
            "message": "Préparation validée ; finalisation bancaire/compte remise à l'utilisateur dans son navigateur.",
        }


WEB_AGENT = AutonomousWebAgent()
