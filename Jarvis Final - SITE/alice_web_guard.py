#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALICE WEB GUARD — FILTRAGE D'URL, PRÉVENTION SSRF ET TRAÇABILITÉ DES SOURCES (LOT C)
Garantit qu'aucune requête externe arbitraire ne peut cibler le réseau local,
la boucle locale ou les points de terminaison de métadonnées de cloud.
"""

import socket
import ipaddress
import urllib.parse
from typing import Tuple, Optional, Dict, Any

# Statuts formels de l'agent web
STATUS_SEARCH_PERFORMED   = "SEARCH_PERFORMED"
STATUS_PAGE_INACCESSIBLE   = "PAGE_INACCESSIBLE"
STATUS_INCOMPLETE_RESULT  = "INCOMPLETE_RESULT"
STATUS_UNVERIFIED_INFO    = "UNVERIFIED_INFO"
STATUS_CONFIRMED_INFO     = "CONFIRMED_INFO"
STATUS_BLOCKED_SSRF       = "BLOCKED_SSRF_OR_UNSAFE_URL"

class AliceWebGuard:
    """Garde-fou contre les requêtes SSRF et les URL non fiables."""

    ALLOWED_SCHEMES = {"http", "https"}
    ALLOWED_PORTS = {80, 443}

    @classmethod
    def resolve_and_validate_url(cls, url: str) -> Tuple[bool, str, list]:
        """
        Analyse une URL, rejette userinfo et ports non autorisés, résout le DNS
        et retourne (ok, reason, validated_ips) pour permettre le pinning IP.
        """
        if not url or not isinstance(url, str):
            return False, "URL vide ou invalide.", []

        url_clean = url.strip()
        try:
            parsed = urllib.parse.urlparse(url_clean)
        except Exception as e:
            return False, f"Format d'URL invalide : {e}", []

        # 1. Validation du schéma
        if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            return False, f"Schéma d'URL interdit : {parsed.scheme} (seuls http et https sont autorisés)", []

        # 1b. Rejet explicite de userinfo (user:pass@host)
        if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
            return False, "Identifiants userinfo interdits dans l'URL.", []

        # 2. Validation du nom d'hôte
        hostname = parsed.hostname
        if not hostname:
            return False, "Nom d'hôte manquant dans l'URL.", []

        # Rejet explicite de localhost et noms de machines locales
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False, "Accès interdit à la boucle locale (localhost/127.0.0.1).", []

        # 3. Résolution DNS et inspection de l'adresse IP cible (anti-DNS rebinding et anti-SSRF)
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if port not in cls.ALLOWED_PORTS:
            return False, f"Port interdit : {port}.", []

        try:
            # Résolution de toutes les adresses IP associées
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            resolved_ips = sorted({item[4][0] for item in addr_info})
        except socket.gaierror:
            # En mode test ou hors ligne, si le domaine ne résout pas, vérifier si c'est un format IP brut
            try:
                ip_obj = ipaddress.ip_address(hostname)
                resolved_ips = [str(ip_obj)]
            except ValueError:
                return False, f"Nom de domaine introuvable ou injoignable : {hostname}", []

        if not resolved_ips:
            return False, f"Aucune adresse IP résolue pour {hostname}.", []

        for ip_str in resolved_ips:
            try:
                ip = ipaddress.ip_address(ip_str)
                if getattr(ip, "ipv4_mapped", None) is not None:
                    ip = ip.ipv4_mapped
                # Vérification des sous-réseaux privés, réservés, loopback et métadonnées
                if ip.is_private:
                    return False, f"Accès interdit au réseau privé interne ({ip_str}).", []
                if ip.is_loopback:
                    return False, f"Accès interdit à l'adresse de bouclage ({ip_str}).", []
                if ip.is_link_local:
                    return False, f"Accès interdit à l'adresse lien-local ({ip_str}).", []
                if ip.is_reserved:
                    return False, f"Accès interdit à une adresse réservée ({ip_str}).", []
                if ip.is_multicast or ip.is_unspecified:
                    return False, f"Accès interdit à une adresse non routable ({ip_str}).", []
                # Blocage spécifique métadonnées Cloud AWS/GCP/Azure (169.254.169.254)
                if str(ip) == "169.254.169.254":
                    return False, "Accès interdit au service de métadonnées d'instance cloud.", []
            except ValueError:
                return False, f"Adresse IP résolue invalide : {ip_str}", []

        return True, "URL vérifiée et sécurisée.", resolved_ips

    @classmethod
    def is_safe_url(cls, url: str) -> Tuple[bool, str]:
        """Vérifie formellement qu'une URL ne cible pas une IP privée, loopback ou interne."""
        ok, reason, _ = cls.resolve_and_validate_url(url)
        return ok, reason

    @classmethod
    def format_search_evidence(cls, query: str, results: list, status: str = STATUS_CONFIRMED_INFO) -> Dict[str, Any]:
        """Formate une preuve de recherche traçable avec statut d'exactitude."""
        return {
            "query": query,
            "status": status,
            "results_count": len(results),
            "sources": results,
            "is_verified": (status == STATUS_CONFIRMED_INFO),
            "is_simulated": False  # Invariant : aucune simulation présentée comme réelle
        }


WEB_GUARD = AliceWebGuard()
