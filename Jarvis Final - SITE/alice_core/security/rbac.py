#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 28 — MULTI-USER RBAC & GUEST MODE (ALICE-SEC-028, Wave 1).
Cloisonnement strict côté backend par rôle, ressource, action, délégation
et vérification secondaire (step-up) pour les opérations critiques.
"""

import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Tuple, Any
from alice_core.contracts import AliceSecurityError
from alice_core.security.audit import AUDIT_LOGGER


class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    GUEST = "GUEST"
    SERVICE_AGENT = "SERVICE_AGENT"


ROLE_LEVELS: Dict[Role, int] = {
    Role.OWNER: 100,
    Role.ADMIN: 80,
    Role.MEMBER: 50,
    Role.SERVICE_AGENT: 30,
    Role.GUEST: 10,
}


# Politique canonique RBAC : (ressource, action) -> {Role: policy}
# "ALLOW"         : autorisé par défaut
# "STEP_UP"       : autorisé uniquement avec authentification secondaire active
# "DELEGATED"     : autorisé uniquement si une délégation explicite est accordée
# "DENY"          : strictement interdit
PERMISSION_MATRIX: Dict[Tuple[str, str], Dict[Role, str]] = {
    # Conversation & Assistant général
    ("assistant", "chat"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "ALLOW", Role.SERVICE_AGENT: "ALLOW",
    },
    ("voice", "followup"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "ALLOW", Role.SERVICE_AGENT: "DENY",
    },
    # Domotique
    ("iot", "light_control"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DELEGATED_OR_PUBLIC_ROOM", Role.SERVICE_AGENT: "DELEGATED",
    },
    ("iot", "switch_control"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DELEGATED",
    },
    ("iot", "sensor_read"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "ALLOW", Role.SERVICE_AGENT: "ALLOW",
    },
    ("iot", "alarm_arm"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("iot", "alarm_disarm"): {
        Role.OWNER: "STEP_UP", Role.ADMIN: "DENY", Role.MEMBER: "DELEGATED_STEP_UP",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("iot", "routine_manage"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    # Système hôte
    ("system", "shutdown"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "DELEGATED", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("system", "reboot"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "DELEGATED", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("system", "app_launch"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("files", "read"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("files", "write"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("files", "delete"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    # Navigation Web autonome / Recherche
    ("web", "browse"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DELEGATED",
    },
    # Communications & Workspace
    ("emails", "read"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "DELEGATED", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("emails", "send"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "DENY", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("calendar", "read"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DELEGATED",
    },
    # Mémoire, RAG & Graphe
    ("memory", "read"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DELEGATED",
    },
    ("memory", "write"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "ALLOW",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DELEGATED",
    },
    # Coffre-fort chiffré
    ("vault", "read"): {
        Role.OWNER: "STEP_UP", Role.ADMIN: "DENY", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("vault", "write"): {
        Role.OWNER: "STEP_UP", Role.ADMIN: "DENY", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    # Observabilité & Administration
    ("ops", "dashboard"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("ops", "export"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("flags", "manage"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("webhooks", "manage"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("vision", "monitor"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DELEGATED",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("voice_id", "manage"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "ALLOW", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
    ("rbac", "manage"): {
        Role.OWNER: "ALLOW", Role.ADMIN: "DENY", Role.MEMBER: "DENY",
        Role.GUEST: "DENY", Role.SERVICE_AGENT: "DENY",
    },
}

# Mapping exhaustif des commandes d'actions IA -> (ressource, action)
ACTION_TO_PERMISSION: Dict[str, Tuple[str, str]] = {
    "shutdown": ("system", "shutdown"),
    "reboot": ("system", "reboot"),
    "system_control": ("system", "shutdown"),
    "lancer_application": ("system", "app_launch"),
    "focus_mode": ("system", "app_launch"),
    "youtube_play": ("system", "app_launch"),
    "alice_analyser_youtube": ("system", "app_launch"),
    "ouvrir_dossier": ("files", "write"),
    "lister_dossier": ("files", "read"),
    "chercher_fichier": ("files", "read"),
    "trier_par_type": ("files", "write"),
    "trier_par_date": ("files", "write"),
    "trier_complet": ("files", "write"),
    "creer_dossier": ("files", "write"),
    "renommer_fichier": ("files", "write"),
    "deplacer_fichier": ("files", "delete"),
    "supprimer_fichier": ("files", "delete"),
    "create_doc": ("files", "write"),
    "write_doc": ("files", "write"),
    "create_sheet": ("files", "write"),
    "alice_generer_image": ("files", "write"),
    "alice_transcrire": ("files", "write"),
    "alice_supprimer_fond": ("files", "write"),
    "ha_lumiere": ("iot", "light_control"),
    "ha_prise": ("iot", "switch_control"),
    "ha_aspirateur": ("iot", "switch_control"),
    "ha_temperature": ("iot", "sensor_read"),
    "ha_humidite": ("iot", "sensor_read"),
    "ha_consommation": ("iot", "sensor_read"),
    "ha_energie": ("iot", "sensor_read"),
    "ha_batterie": ("iot", "sensor_read"),
    "ha_tiktok": ("iot", "sensor_read"),
    "ha_alarme": ("iot", "alarm_disarm"),
    "ha_simulation": ("iot", "routine_manage"),
    "ha_thermostat": ("iot", "routine_manage"),
    "ha_scene": ("iot", "routine_manage"),
    "mode_iron_man": ("iot", "routine_manage"),
    "iot_eco": ("iot", "routine_manage"),
    "iot_health": ("iot", "routine_manage"),
    "read_emails": ("emails", "read"),
    "alice_rediger_email": ("emails", "send"),
    "send_gmail": ("emails", "send"),
    "whatsapp_appel": ("emails", "send"),
    "read_calendar": ("calendar", "read"),
    "google_calendar_check": ("calendar", "read"),
    "add_reminder": ("memory", "write"),
    "alice_planifier_agenda": ("memory", "write"),
    "memoriser": ("memory", "write"),
    "oublier": ("memory", "write"),
    "lister_memoire": ("memory", "read"),
    "memory_add": ("memory", "write"),
    "memory_forget": ("memory", "write"),
    "alice_recherche_kb": ("memory", "read"),
    "knowledge_graph_add": ("memory", "write"),
    "knowledge_graph_query": ("memory", "read"),
    "daily_briefing": ("memory", "read"),
    "executive_briefing": ("memory", "read"),
    "alice_videosurveillance": ("vision", "monitor"),
    "voir_ecran": ("vision", "monitor"),
    "vision_ecrire": ("vision", "monitor"),
    "alice_vision_contextuelle": ("vision", "monitor"),
    "alice_analyser_photo": ("vision", "monitor"),
    "visual_memory_search": ("vision", "monitor"),
    "recherche_web": ("web", "browse"),
    "alice_agent_web": ("web", "browse"),
    "web_agent_check": ("web", "browse"),
    "alice_codage": ("files", "write"),
    "alice_debug_code": ("files", "write"),
    "check_diagnostics": ("ops", "dashboard"),
    "get_stats": ("ops", "dashboard"),
    "vault_read": ("vault", "read"),
    "vault_write": ("vault", "write"),
    "alice_humeur_audio": ("assistant", "chat"),
    "alice_tts_custom": ("assistant", "chat"),
    "alice_productivite": ("assistant", "chat"),
}

# Liste blanche explicite d'actions conversationnelles publiques (jamais de default-allow)
PUBLIC_CONVERSATIONAL_ACTIONS: Set[str] = {
    "meteo",
    "alerte_meteo",
    "sport_resultats",
    "sport_classement",
    "sport_live",
    "alice_status",
    "ha_anniversaires",
    "ha_oeufs",
}

PUBLIC_GUEST_ROOMS = {"salon", "cuisine", "couloir"}


@dataclass
class UserPrincipal:
    """Identité authentifiée rattachée à une session backend."""
    user_id: str
    role: Role
    session_id: str
    delegations: Set[str] = field(default_factory=set)  # ex: {"emails:read", "iot:alarm_arm"}
    step_up_until: float = 0.0
    public_rooms_allowed: bool = True

    def has_step_up(self) -> bool:
        return time.time() < self.step_up_until

    def grant_step_up(self, duration_seconds: float = 300.0):
        self.step_up_until = time.time() + duration_seconds


class RBACPolicyEngine:
    """Moteur d'autorisation RBAC centralisé côté backend."""

    def __init__(self):
        self._lock = threading.RLock()
        self._principals: Dict[str, UserPrincipal] = {}  # session_id -> UserPrincipal
        self._owner_step_up_pins: Dict[str, str] = {}    # optionnel pour vérif secondaire

    def register_principal(
        self,
        session_id: str,
        user_id: str,
        role: Role,
        delegations: Optional[Set[str]] = None,
        step_up_seconds: float = 0.0,
    ) -> UserPrincipal:
        if not isinstance(role, Role):
            role = Role(str(role).upper())
        with self._lock:
            p = UserPrincipal(
                user_id=user_id,
                role=role,
                session_id=session_id,
                delegations=set(delegations or ()),
                step_up_until=(time.time() + step_up_seconds) if step_up_seconds > 0 else 0.0,
            )
            self._principals[session_id] = p
            return p

    def get_principal(self, session_id: str) -> UserPrincipal:
        with self._lock:
            if session_id in self._principals:
                return self._principals[session_id]
            # Fail-closed : une session inconnue ou non enregistrée reçoit le rôle minimal GUEST
            if session_id == "desktop_local":
                p = UserPrincipal(user_id="owner_local", role=Role.OWNER, session_id="desktop_local")
                self._principals[session_id] = p
                return p
            return UserPrincipal(user_id="anonymous_guest", role=Role.GUEST, session_id=session_id)

    def revoke_principal(self, session_id: str):
        with self._lock:
            self._principals.pop(session_id, None)

    def grant_delegation(self, actor: UserPrincipal, target_session_id: str, perm_key: str) -> bool:
        """Seul OWNER (ou ADMIN pour délégations non critiques) peut accorder une délégation."""
        if actor.role != Role.OWNER and not (actor.role == Role.ADMIN and not perm_key.startswith("vault:")):
            AUDIT_LOGGER.log(
                "RBAC", "delegation_denied", actor.user_id, actor.role.value, actor.session_id,
                "DENIED", {"target": target_session_id, "perm": perm_key}
            )
            raise AliceSecurityError("Élévation de privilèges interdite : vous ne pouvez pas déléguer ce droit.")
        with self._lock:
            target = self.get_principal(target_session_id)
            target.delegations.add(perm_key)
            AUDIT_LOGGER.log(
                "RBAC", "delegation_granted", actor.user_id, actor.role.value, actor.session_id,
                "OK", {"target_user": target.user_id, "perm": perm_key}
            )
            return True

    def change_role(self, actor: UserPrincipal, target_session_id: str, new_role: Role) -> bool:
        """Empêche toute élévation horizontale ou verticale de rôle par un non-OWNER."""
        if actor.role != Role.OWNER:
            AUDIT_LOGGER.log(
                "RBAC", "role_escalation_blocked", actor.user_id, actor.role.value, actor.session_id,
                "DENIED", {"target": target_session_id, "requested_role": new_role.value}
            )
            raise AliceSecurityError("Seul le propriétaire (OWNER) peut modifier les rôles RBAC.")
        with self._lock:
            target = self.get_principal(target_session_id)
            target.role = new_role
            self._principals[target_session_id] = target
            AUDIT_LOGGER.log(
                "RBAC", "role_changed", actor.user_id, actor.role.value, actor.session_id,
                "OK", {"target_user": target.user_id, "new_role": new_role.value}
            )
            return True

    def authorize(
        self,
        principal: UserPrincipal,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Évalue l'autorisation côté backend et journalise tout refus."""
        context = context or {}
        if principal is None or not isinstance(getattr(principal, "role", None), Role):
            AUDIT_LOGGER.log("RBAC", "unknown_role_denied", outcome="DENIED", details={"role": repr(getattr(principal, "role", None))})
            return False, "Accès refusé : rôle inconnu ou invalide."

        # Cas spécial alarme : armer vs désarmer
        if resource == "iot" and action == "alarm_disarm" and context.get("etat") == "on":
            action = "alarm_arm"

        perm_key = f"{resource}:{action}"
        policies = PERMISSION_MATRIX.get((resource, action))
        if not policies:
            AUDIT_LOGGER.log(
                "RBAC", "unknown_permission_denied", principal.user_id, principal.role.value,
                principal.session_id, "DENIED", {"perm": perm_key}
            )
            return False, f"Accès refusé : permission inconnue '{perm_key}'."

        policy = policies.get(principal.role, "DENY")

        allowed = False
        reason = f"Accès refusé pour le rôle {principal.role.value} sur '{perm_key}'."

        if policy == "ALLOW":
            allowed = True
            reason = "Autorisé."
        elif policy == "STEP_UP":
            if principal.has_step_up() or context.get("step_up_verified") is True:
                allowed = True
                reason = "Autorisé après vérification renforcée."
            else:
                allowed = False
                reason = f"Vérification renforcée requise (step-up auth) pour '{perm_key}'."
        elif policy == "DELEGATED":
            if perm_key in principal.delegations:
                allowed = True
                reason = "Autorisé par délégation explicite."
            else:
                reason = f"Délégation explicite requise pour '{perm_key}' (rôle {principal.role.value})."
        elif policy == "DELEGATED_STEP_UP":
            if perm_key in principal.delegations and (principal.has_step_up() or context.get("step_up_verified") is True):
                allowed = True
                reason = "Autorisé par délégation et vérification renforcée."
            else:
                reason = f"Délégation + vérification renforcée requises pour '{perm_key}'."
        elif policy == "DELEGATED_OR_PUBLIC_ROOM":
            room = str(context.get("piece", "")).lower().strip()
            if perm_key in principal.delegations or (principal.public_rooms_allowed and (not room or room in PUBLIC_GUEST_ROOMS)):
                allowed = True
                reason = "Autorisé (zone commune invité)."
            else:
                reason = f"Accès invité refusé pour la pièce privée '{room}'."

        if not allowed:
            AUDIT_LOGGER.log(
                "RBAC", "access_denied", principal.user_id, principal.role.value,
                principal.session_id, "DENIED", {"perm": perm_key, "reason": reason}
            )
        return allowed, reason

    def check_action(
        self,
        session_id: str,
        action_name: Optional[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Vérifie si une action JSON de l'orchestrateur est autorisée (strictement fail-closed)."""
        try:
            if not session_id or not isinstance(session_id, str):
                return False, "Accès refusé : session absente ou invalide."
            principal = self.get_principal(session_id)
            if principal is None or not isinstance(principal.role, Role):
                return False, "Accès refusé : principal RBAC invalide."
            if not action_name or not isinstance(action_name, str):
                AUDIT_LOGGER.log(
                    "RBAC", "invalid_action_denied", principal.user_id, principal.role.value,
                    principal.session_id, "DENIED", {"action": repr(action_name)}
                )
                return False, "Accès refusé : action vide ou invalide."
            act_norm = action_name.strip().lower()
            if not act_norm:
                return False, "Accès refusé : action vide."
            if act_norm in PUBLIC_CONVERSATIONAL_ACTIONS:
                return self.authorize(principal, "assistant", "chat", context=context)
            if act_norm not in ACTION_TO_PERMISSION:
                AUDIT_LOGGER.log(
                    "RBAC", "unmapped_action_denied", principal.user_id, principal.role.value,
                    principal.session_id, "DENIED", {"action": act_norm}
                )
                return False, f"Accès refusé : action inconnue ou non autorisée '{act_norm}'."
            res, act = ACTION_TO_PERMISSION[act_norm]
            return self.authorize(principal, res, act, context=context)
        except Exception as e:
            AUDIT_LOGGER.log("RBAC", "decision_error_fail_closed", outcome="DENIED", details={"error": str(e)})
            return False, "Accès refusé : erreur interne lors du contrôle d'autorisation."

    def check_owner_isolation(self, requester: UserPrincipal, resource_owner_id: str, visibility: str = "private") -> bool:
        """Empêche la fuite horizontale des ressources privées entre utilisateurs."""
        if visibility == "shared":
            return requester.role != Role.GUEST
        if requester.user_id == resource_owner_id:
            return True
        if requester.role == Role.OWNER and resource_owner_id != "vault_locked":
            return True
        AUDIT_LOGGER.log(
            "RBAC", "horizontal_isolation_blocked", requester.user_id, requester.role.value,
            requester.session_id, "DENIED", {"resource_owner": resource_owner_id}
        )
        return False


RBAC = RBACPolicyEngine()
