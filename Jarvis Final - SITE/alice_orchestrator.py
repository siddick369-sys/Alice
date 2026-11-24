#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALICE ORCHESTRATOR — MODULE DE GESTION DU CYCLE DE VIE DES COMMANDES (LOT A)
Définit le contrat formel en 9 états, l'idempotence, la corrélation et l'observabilité.

États du cycle de vie :
- RECEIVED               : Commande réceptionnée par le serveur
- VALIDATING             : Validation des droits, de la session et des paramètres
- ACCEPTED               : Commande acceptée pour exécution
- RUNNING                : Exécution en cours avec surveillance de timeout
- SUCCEEDED              : Exécution terminée avec succès
- FAILED                 : Échec de l'action avec diagnostic
- UNKNOWN                : État incertain (matériel indisponible ou timeout)
- CANCELLED              : Commande annulée par l'utilisateur ou par timeout
- REQUIRES_CONFIRMATION  : Action sensible nécessitant l'accord explicite de l'utilisateur
"""

import os
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Tuple

logger = logging.getLogger("AliceOrchestrator")

# Définition des 9 états formels
STATE_RECEIVED              = "RECEIVED"
STATE_VALIDATING            = "VALIDATING"
STATE_ACCEPTED              = "ACCEPTED"
STATE_RUNNING               = "RUNNING"
STATE_SUCCEEDED             = "SUCCEEDED"
STATE_FAILED                = "FAILED"
STATE_UNKNOWN               = "UNKNOWN"
STATE_CANCELLED             = "CANCELLED"
STATE_REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"

ALL_STATES = {
    STATE_RECEIVED,
    STATE_VALIDATING,
    STATE_ACCEPTED,
    STATE_RUNNING,
    STATE_SUCCEEDED,
    STATE_FAILED,
    STATE_UNKNOWN,
    STATE_CANCELLED,
    STATE_REQUIRES_CONFIRMATION
}

# Actions nécessitant une confirmation utilisateur obligatoire par politique de sécurité
SENSITIVE_ACTIONS = {
    "shutdown",
    "reboot",
    "alice_rediger_email",
    "ha_alarme",
    "supprimer_fichier"
}

class CommandRecord:
    """Représentation immuable et traçable d'une commande dans le système."""
    def __init__(self, command_id: str, text: str, session_id: str, client_ip: str = "local"):
        self.command_id: str = command_id
        self.trace_id: str = f"tr_{uuid.uuid4().hex[:12]}"
        self.text: str = text
        self.session_id: str = session_id
        self.client_ip: str = client_ip
        self.action: Optional[str] = None
        self.state: str = STATE_RECEIVED
        self.previous_state: Optional[str] = None
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at
        self.payload: Dict[str, Any] = {}
        self.result: Any = None
        self.error: Optional[str] = None
        self.requires_confirmation: bool = False
        self.confirmation_token: Optional[str] = None
        self.confirmation_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "command_lifecycle",
            "command_id": self.command_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "text": self.text,
            "action": self.action,
            "state": self.state,
            "previous_state": self.previous_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_token": self.confirmation_token,
            "confirmation_prompt": self.confirmation_prompt
        }


class CommandLifecycleManager:
    """
    Gestionnaire centralisé du cycle de vie des commandes pour J.A.R.V.I.S / ALICE.
    Garantit l'idempotence, le suivi des états et la notification en temps réel via WebSocket.
    """

    def __init__(self, log_path: Optional[str] = None):
        self.commands: Dict[str, CommandRecord] = {}
        # Fenêtre d'idempotence (clé de hachage session:texte -> (command_id, timestamp))
        self._idempotency_cache: Dict[str, Tuple[str, float]] = {}
        self._idempotency_window: float = 4.0  # 4 secondes de protection anti-double tap
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = log_path or os.path.join(base_dir, "alice_outputs", "command_lifecycle.log")
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        except Exception:
            pass

    def _log_event(self, record: CommandRecord):
        """Enregistre l'événement dans le journal d'observabilité sans fuite de secrets."""
        try:
            self._ensure_log_dir()
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.updated_at))
            # Masquer les données sensibles éventuelles
            safe_payload = {k: ("***" if "token" in k.lower() or "secret" in k.lower() else v) for k, v in record.payload.items()}
            entry = {
                "timestamp": ts,
                "command_id": record.command_id,
                "trace_id": record.trace_id,
                "session_id": record.session_id,
                "state": record.state,
                "action": record.action,
                "error": record.error,
                "payload": safe_payload
            }
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ORCHESTRATOR LOG ERROR] {e}")

    def check_idempotency(self, text: str, session_id: str) -> Optional[CommandRecord]:
        """
        Vérifie si une commande identique est déjà en cours ou a été soumise récemment.
        Prévient les doubles exécutions accidentelles.
        """
        now = time.time()
        # Nettoyage des anciennes entrées du cache
        self._idempotency_cache = {
            k: v for k, v in self._idempotency_cache.items()
            if now - v[1] < self._idempotency_window
        }
        
        idem_key = f"{session_id}:{text.strip().lower()}"
        if idem_key in self._idempotency_cache:
            prev_cmd_id, timestamp = self._idempotency_cache[idem_key]
            if prev_cmd_id in self.commands:
                existing = self.commands[prev_cmd_id]
                # Si la commande est encore en cours de traitement, signaler la duplication
                if existing.state in (STATE_RECEIVED, STATE_VALIDATING, STATE_ACCEPTED, STATE_RUNNING):
                    return existing
        return None

    def register_command(self, text: str, session_id: str, client_ip: str = "local", command_id: Optional[str] = None) -> CommandRecord:
        """Enregistre une nouvelle commande à l'état INITIAL 'RECEIVED'."""
        cmd_id = command_id or f"cmd_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        record = CommandRecord(cmd_id, text, session_id, client_ip)
        self.commands[cmd_id] = record
        
        # Enregistrement dans le cache d'idempotence
        idem_key = f"{session_id}:{text.strip().lower()}"
        self._idempotency_cache[idem_key] = (cmd_id, time.time())
        
        self._log_event(record)
        return record

    async def transition(self, command_id: str, new_state: str, action: Optional[str] = None,
                         payload: Optional[Dict[str, Any]] = None, result: Any = None,
                         error: Optional[str] = None, confirmation_prompt: Optional[str] = None,
                         websocket: Any = None) -> CommandRecord:
        """
        Effectue une transition d'état atomique et notifie les clients WebSocket.
        """
        if new_state not in ALL_STATES:
            raise ValueError(f"État non reconnu dans le contrat : {new_state}")
            
        record = self.commands.get(command_id)
        if not record:
            # Création à la volée si commande non encore enregistrée
            record = CommandRecord(command_id, "unknown", "unknown")
            self.commands[command_id] = record

        record.previous_state = record.state
        record.state = new_state
        record.updated_at = time.time()
        
        if action:
            record.action = action
        if payload:
            record.payload.update(payload)
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
            
        if new_state == STATE_REQUIRES_CONFIRMATION:
            record.requires_confirmation = True
            token = uuid.uuid4().hex[:8]
            record.confirmation_token = token
            record.confirmation_prompt = confirmation_prompt or f"Confirmez-vous l'action sensible '{record.action}' ?"
            self.pending_confirmations[record.command_id] = {
                "command_id": record.command_id,
                "session_id": record.session_id,
                "action": record.action,
                "token": token,
                "payload": record.payload,
                "expires_at": time.time() + 60.0  # 60s pour confirmer
            }

        self._log_event(record)
        
        # Envoi de la notification WebSocket en temps réel
        if websocket:
            await self._send_ws(websocket, record)

        return record

    async def _send_ws(self, websocket: Any, record: CommandRecord):
        """Envoie l'événement de cycle de vie au client WebSocket."""
        try:
            if hasattr(websocket, "send") and not getattr(websocket, "closed", False):
                payload_str = json.dumps(record.to_dict(), ensure_ascii=False)
                await websocket.send(payload_str)
        except Exception as e:
            # Ne pas bloquer l'orchestration si un client réseau s'est déconnecté
            logger.debug(f"Échec envoi WS command_lifecycle : {e}")

    def verify_confirmation(self, command_id: str, token: str, session_id: str) -> Tuple[bool, str]:
        """
        Vérifie qu'un jeton de confirmation correspond à la session et à l'action en attente.
        Empêche les confirmations croisées inter-sessions (SEC-03).
        """
        pending = self.pending_confirmations.get(command_id)
        if not pending:
            return False, "Aucune action en attente de confirmation pour cet identifiant."

        if time.time() > pending["expires_at"]:
            del self.pending_confirmations[command_id]
            return False, "Le délai de confirmation a expiré (timeout 60s)."

        if pending["session_id"] != session_id:
            return False, "Violation de sécurité : la confirmation doit provenir de la même session que la commande initiale."

        if pending["token"] != token:
            return False, "Jeton de confirmation invalide."

        # Confirmation valide, retrait de la liste d'attente
        del self.pending_confirmations[command_id]
        return True, "Confirmation validée."

    def cancel_confirmation(self, command_id: str, session_id: str) -> Tuple[bool, str]:
        """Annule une action en attente de confirmation."""
        pending = self.pending_confirmations.get(command_id)
        if not pending:
            return False, "Aucune action en attente à annuler."

        if pending["session_id"] != session_id:
            return False, "Action non autorisée depuis cette session."

        del self.pending_confirmations[command_id]
        if command_id in self.commands:
            self.commands[command_id].state = STATE_CANCELLED
            self.commands[command_id].updated_at = time.time()
            self._log_event(self.commands[command_id])
        return True, "Action annulée avec succès."

    async def execute_action_with_lifecycle(self, command_id: str, action_name: str,
                                           action_func: Callable, action_args: Tuple = (),
                                           action_kwargs: Optional[Dict] = None,
                                           timeout: float = 15.0,
                                           websocket: Any = None) -> Tuple[str, Any]:
        """
        Exécute une fonction d'action encadrée par le cycle de vie 9 états.
        Gère les timeouts, les exceptions et les états matériels indéterminés.
        """
        action_kwargs = action_kwargs or {}
        
        # 1. Validation de la commande
        await self.transition(command_id, STATE_VALIDATING, action=action_name, websocket=websocket)
        
        # Vérification si confirmation nécessaire
        if action_name in SENSITIVE_ACTIONS:
            await self.transition(command_id, STATE_REQUIRES_CONFIRMATION, action=action_name,
                                  confirmation_prompt=f"Êtes-vous certain de vouloir exécuter {action_name} ?",
                                  websocket=websocket)
            return STATE_REQUIRES_CONFIRMATION, None

        # 2. Acceptation
        await self.transition(command_id, STATE_ACCEPTED, action=action_name, websocket=websocket)

        # 3. Exécution en cours
        await self.transition(command_id, STATE_RUNNING, action=action_name, websocket=websocket)

        try:
            # Exécution avec timeout strict
            if asyncio.iscoroutinefunction(action_func):
                res = await asyncio.wait_for(action_func(*action_args, **action_kwargs), timeout=timeout)
            else:
                loop = asyncio.get_event_loop()
                res = await asyncio.wait_for(loop.run_in_executor(None, lambda: action_func(*action_args, **action_kwargs)), timeout=timeout)

            # Analyse du résultat pour détecter les états physiques indéterminés (Home Assistant)
            if isinstance(res, dict) and res.get("status") in ("STATE_UNKNOWN", "TIMEOUT", "HA_STATE_UNKNOWN"):
                await self.transition(command_id, STATE_UNKNOWN, action=action_name, result=res,
                                      error="État matériel réel non confirmé par le capteur/équipement.",
                                      websocket=websocket)
                return STATE_UNKNOWN, res

            if isinstance(res, dict) and res.get("success") is False:
                err_msg = res.get("message") or res.get("error") or "Échec de l'action"
                await self.transition(command_id, STATE_FAILED, action=action_name, result=res,
                                      error=err_msg, websocket=websocket)
                return STATE_FAILED, res

            # Succès confirmé
            await self.transition(command_id, STATE_SUCCEEDED, action=action_name, result=res, websocket=websocket)
            return STATE_SUCCEEDED, res

        except asyncio.TimeoutError:
            err = f"Délai d'exécution dépassé ({timeout}s) pour l'action {action_name}."
            await self.transition(command_id, STATE_FAILED, action=action_name, error=err, websocket=websocket)
            return STATE_FAILED, err

        except Exception as e:
            err = f"Erreur interne lors de l'exécution de {action_name} : {str(e)}"
            await self.transition(command_id, STATE_FAILED, action=action_name, error=err, websocket=websocket)
            return STATE_FAILED, err


# Instance globale partagée
ORCHESTRATOR = CommandLifecycleManager()
