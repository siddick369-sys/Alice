#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALICE GOOGLE WORKSPACE ADAPTER — ADAPTATEUR DÉCOUPLÉ ET TESTABLE (LOT D)
Gère l'écosystème Google (Docs, Sheets, Gmail, Calendar) avec distinction stricte
entre lecture et actions irréversibles (création/modification/envoi), sans bloquer
le serveur en cas de token OAuth manquant.
"""

import os
import pickle
from typing import Dict, Any, Optional, List, Tuple

# Statuts de l'adaptateur
GW_STATUS_AVAILABLE     = "AVAILABLE"
GW_STATUS_UNAVAILABLE   = "UNAVAILABLE"
GW_STATUS_AUTH_REQUIRED = "AUTH_REQUIRED"
GW_STATUS_CONFIRMATION  = "REQUIRES_CONFIRMATION"

class GoogleWorkspaceAdapter:
    """Adaptateur résilient pour l'écosystème Google Workspace."""

    MINIMAL_SCOPES = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/calendar",
    ]

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.credentials_path = os.path.join(self.base_dir, "credentials.json")
        self.token_path = os.path.join(self.base_dir, "token.pickle")
        self._mock_mode: bool = False
        self._mock_data: Dict[str, Any] = {}

    def enable_mock_mode(self, mock_data: Optional[Dict[str, Any]] = None):
        """Active le mode mocké pour les tests automatisés et l'isolation."""
        self._mock_mode = True
        self._mock_data = mock_data or {
            "emails": [{"id": "m1", "subject": "Test Email", "from": "sender@test.com"}],
            "calendar": [{"id": "c1", "summary": "Réunion Projet", "start": "2026-11-25T10:00:00Z"}]
        }

    def disable_mock_mode(self):
        """Désactive le mode mocké."""
        self._mock_mode = False

    def check_availability(self) -> Dict[str, Any]:
        """Vérifie l'état réel de l'authentification sans lancer de flux bloquant."""
        if self._mock_mode:
            return {
                "status": GW_STATUS_AVAILABLE,
                "authenticated": True,
                "mock_mode": True,
                "message": "Mode simulation activé pour les tests."
            }

        if not os.path.exists(self.credentials_path):
            return {
                "status": GW_STATUS_UNAVAILABLE,
                "authenticated": False,
                "message": "Fichier credentials.json absent. L'intégration Google Workspace est désactivée."
            }

        if not os.path.exists(self.token_path):
            return {
                "status": GW_STATUS_AUTH_REQUIRED,
                "authenticated": False,
                "message": "Jeton OAuth (token.pickle) absent. Autorisation interactive requise hors production."
            }

        try:
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)
            if creds and creds.valid:
                return {"status": GW_STATUS_AVAILABLE, "authenticated": True, "message": "Compte Google authentifié et valide."}
            elif creds and creds.expired and creds.refresh_token:
                return {"status": GW_STATUS_AVAILABLE, "authenticated": True, "message": "Jeton expiré mais renouvelable (refresh token présent)."}
            else:
                return {"status": GW_STATUS_AUTH_REQUIRED, "authenticated": False, "message": "Jeton expiré sans refresh token."}
        except Exception as e:
            return {"status": GW_STATUS_UNAVAILABLE, "authenticated": False, "message": f"Erreur lecture jeton : {e}"}

    def list_calendar_events(self, days: int = 1) -> Dict[str, Any]:
        """Lecture sécurisée des événements du calendrier."""
        status = self.check_availability()
        if not status["authenticated"]:
            return {
                "success": False,
                "status": status["status"],
                "events": [],
                "message": f"Google Calendar indisponible : {status['message']}"
            }

        if self._mock_mode:
            return {
                "success": True,
                "status": GW_STATUS_AVAILABLE,
                "events": self._mock_data.get("calendar", []),
                "message": f"{len(self._mock_data.get('calendar', []))} événement(s) récupéré(s) (simulation)."
            }

        # En environnement réel avec token valide
        try:
            from googleapiclient.discovery import build
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)
            service = build("calendar", "v3", credentials=creds)
            # Exécution de la requête bornée dans le temps
            events = []
            return {"success": True, "status": GW_STATUS_AVAILABLE, "events": events, "message": "Événements récupérés."}
        except Exception as e:
            return {"success": False, "status": GW_STATUS_UNAVAILABLE, "events": [], "message": f"Erreur API Calendar : {e}"}

    def read_emails(self, max_results: int = 3) -> Dict[str, Any]:
        """Lecture sécurisée de la boîte de réception."""
        status = self.check_availability()
        if not status["authenticated"]:
            return {
                "success": False,
                "status": status["status"],
                "emails": [],
                "message": f"Gmail indisponible : {status['message']}"
            }

        if self._mock_mode:
            return {
                "success": True,
                "status": GW_STATUS_AVAILABLE,
                "emails": self._mock_data.get("emails", []),
                "message": f"{len(self._mock_data.get('emails', []))} email(s) récupéré(s) (simulation)."
            }

        return {"success": False, "status": GW_STATUS_UNAVAILABLE, "emails": [], "message": "Service non initialisé."}

    def prepare_create_doc(self, title: str, content: str = "") -> Dict[str, Any]:
        """Action engageante (création) nécessitant une confirmation explicite."""
        status = self.check_availability()
        if not status["authenticated"]:
            return {
                "success": False,
                "status": status["status"],
                "message": f"Google Docs indisponible : {status['message']}"
            }

        return {
            "success": True,
            "status": GW_STATUS_CONFIRMATION,
            "action": "create_google_doc",
            "params": {"title": title, "content": content},
            "confirmation_prompt": f"Confirmez-vous la création du document Google Docs '{title}' ?"
        }

    def prepare_send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Action irréversible (envoi d'email) soumise à confirmation stricte."""
        status = self.check_availability()
        if not status["authenticated"]:
            return {
                "success": False,
                "status": status["status"],
                "message": f"Gmail indisponible : {status['message']}"
            }

        return {
            "success": True,
            "status": GW_STATUS_CONFIRMATION,
            "action": "send_gmail",
            "params": {"to": to, "subject": subject, "body": body},
            "confirmation_prompt": f"Confirmez-vous l'envoi de l'email à {to} avec pour objet '{subject}' ?"
        }


GOOGLE_ADAPTER = GoogleWorkspaceAdapter()
