#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 22 — AGENT SWARM (ALICE-AUTO-022, Wave 5).
Délégation contrôlée sur le contrat formel à 9 états d'ORCHESTRATOR (Mission 007).
Garantit : limites de profondeur, budget de temps/tokens/appels, détection de boucle,
isolation des secrets, confinement des données Web non fiables, RBAC SERVICE_AGENT
et validation centrale de toute action sensible.
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable
from alice_orchestrator import (
    ORCHESTRATOR, CommandLifecycleManager,
    STATE_VALIDATING, STATE_ACCEPTED, STATE_RUNNING,
    STATE_SUCCEEDED, STATE_FAILED, STATE_REQUIRES_CONFIRMATION
)
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.contracts import AliceSecurityError
from alice_core.security.audit import redact_text, AUDIT_LOGGER
from alice_core.security.rbac import RBAC, Role


ALLOWED_SWARM_AGENTS = {
    "ResearchAgent": {"tools": {"rag_search", "web_search"}, "sensitive": False},
    "FactCheckerAgent": {"tools": {"rag_search", "verify_claims"}, "sensitive": False},
    "DocumentAnalystAgent": {"tools": {"rag_search", "briefing"}, "sensitive": False},
    "WriterAgent": {"tools": {"draft_text"}, "sensitive": False},
    "AutomationAgent": {"tools": {"prepare_iot", "prepare_reminder"}, "sensitive": True},
    "SecurityReviewerAgent": {"tools": {"ast_audit", "policy_check"}, "sensitive": False},
}


@dataclass
class SwarmBudget:
    max_depth: int = 2
    max_calls: int = 6
    max_tokens_chars: int = 12000
    max_time_seconds: float = 15.0
    used_calls: int = 0
    used_chars: int = 0
    started_at: float = field(default_factory=time.time)

    def consume_call(self):
        if self.used_calls >= self.max_calls:
            raise RuntimeError(f"Budget d'appels Agent Swarm dépassé ({self.max_calls}).")
        if (time.time() - self.started_at) > self.max_time_seconds:
            raise TimeoutError(f"Budget temps Agent Swarm dépassé ({self.max_time_seconds}s).")
        self.used_calls += 1

    def consume_chars(self, count: int):
        if self.used_chars + count > self.max_tokens_chars:
            raise RuntimeError(f"Budget tokens/caractères Agent Swarm dépassé ({self.max_tokens_chars}).")
        self.used_chars += count


class AgentSwarmCoordinator:
    """Coordonnateur d'agents spécialisés connecté à ORCHESTRATOR (9 états)."""

    def __init__(self, orchestrator: Optional[CommandLifecycleManager] = None):
        self.orchestrator = orchestrator or ORCHESTRATOR
        self._agent_runners: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}

    def register_agent_runner(self, agent_name: str, fn: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        if agent_name not in ALLOWED_SWARM_AGENTS:
            raise ValueError(f"Agent non répertorié : {agent_name}")
        self._agent_runners[agent_name] = fn

    @staticmethod
    def _strip_secrets(task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Empêche toute propagation de secrets d'un agent à un autre."""
        blocked_keys = ("vault", "secret", "password", "token", "api_key", "private_key", "voiceprint")
        cleaned = {}
        for k, v in task_payload.items():
            if any(bk in k.lower() for bk in blocked_keys):
                cleaned[k] = "***BLOCKED_SECRET_PASSTHROUGH***"
            elif isinstance(v, str):
                cleaned[k] = redact_text(v)
            else:
                cleaned[k] = v
        return cleaned

    async def delegate_task(
        self,
        parent_command_id: str,
        session_id: str,
        subtasks: List[Dict[str, Any]],
        budget: Optional[SwarmBudget] = None,
        depth: int = 0,
        call_chain: Optional[List[str]] = None,
        websocket: Any = None,
    ) -> Dict[str, Any]:
        """
        Orchestre plusieurs sous-tâches spécialisées avec budgets stricts,
        anti-boucle, confinement des données non fiables et agrégation finale.
        """
        FEATURE_FLAGS.require_enabled("agent_swarm")
        b = budget or SwarmBudget()
        chain = list(call_chain or [])

        if depth > b.max_depth:
            await self.orchestrator.transition(
                parent_command_id, STATE_FAILED, action="agent_swarm",
                error=f"Profondeur de délégation dépassée ({depth} > {b.max_depth})",
                websocket=websocket
            )
            return {"success": False, "status": "FAILED", "error": "Max delegation depth exceeded"}

        await self.orchestrator.transition(parent_command_id, STATE_VALIDATING, action="agent_swarm", websocket=websocket)
        await self.orchestrator.transition(parent_command_id, STATE_ACCEPTED, action="agent_swarm", websocket=websocket)
        await self.orchestrator.transition(parent_command_id, STATE_RUNNING, action="agent_swarm", websocket=websocket)

        results: List[Dict[str, Any]] = []
        requires_central_confirm = False

        for st in subtasks:
            agent_name = st.get("agent", "")
            if agent_name not in ALLOWED_SWARM_AGENTS:
                results.append({"agent": agent_name, "success": False, "error": "Agent non autorisé"})
                continue

            # Détection de boucle de délégation
            if agent_name in chain and st.get("allow_repeat") is not True:
                results.append({"agent": agent_name, "success": False, "error": "Boucle de délégation détectée et bloquée."})
                AUDIT_LOGGER.log("SWARM", "delegation_loop_blocked", session_id=session_id, outcome="DENIED", details={"chain": chain + [agent_name]})
                continue

            # Vérifier interdiction d'auto-élévation de privilège
            if st.get("grant_role") or st.get("override_permissions"):
                raise AliceSecurityError("Un agent spécialisé ne peut pas modifier ses propres permissions.")

            # Vérification budget d'appels et de temps
            try:
                b.consume_call()
            except Exception as eb:
                results.append({"agent": agent_name, "success": False, "error": str(eb)})
                break

            # Si l'agent ou la sous-tâche porte une action sensible -> validation centrale requise
            action_req = st.get("requested_action")
            if action_req:
                ok_rbac, r_msg = RBAC.check_action(session_id, action_req, context=st.get("payload", {}))
                if not ok_rbac:
                    results.append({"agent": agent_name, "success": False, "error": f"RBAC refusé : {r_msg}"})
                    continue
                if st.get("sensitive", False) or ALLOWED_SWARM_AGENTS[agent_name]["sensitive"]:
                    requires_central_confirm = True
                    results.append({
                        "agent": agent_name,
                        "success": False,
                        "status": STATE_REQUIRES_CONFIRMATION,
                        "message": f"Action sensible '{action_req}' soumise à validation centrale."
                    })
                    continue

            safe_payload = self._strip_secrets(st.get("payload", {}))
            if st.get("untrusted_source"):
                # Encadrement strict des instructions web/externes non fiables
                safe_payload["context_data"] = f"<untrusted_web_data>{safe_payload.get('context_data', '')}</untrusted_web_data>"

            runner = self._agent_runners.get(agent_name)
            try:
                remaining_time = max(0.1, b.max_time_seconds - (time.time() - b.started_at))
                if runner:
                    out = await asyncio.wait_for(runner({"payload": safe_payload, "depth": depth + 1, "chain": chain + [agent_name]}), timeout=remaining_time)
                else:
                    out = {"success": True, "summary": f"[{agent_name}] Tâche traitée en mode local sûr."}
                out_str = str(out.get("summary", ""))
                b.consume_chars(len(out_str))
                results.append({"agent": agent_name, "success": bool(out.get("success", True)), "output": out})
            except asyncio.TimeoutError:
                results.append({"agent": agent_name, "success": False, "error": "Timeout sous-agent dépassé"})
            except Exception as e_sub:
                results.append({"agent": agent_name, "success": False, "error": str(e_sub)})

        if requires_central_confirm:
            await self.orchestrator.transition(
                parent_command_id, STATE_REQUIRES_CONFIRMATION, action="agent_swarm",
                confirmation_prompt="Un sous-agent demande une action sensible : confirmez-vous ?",
                websocket=websocket
            )
            return {"success": False, "status": STATE_REQUIRES_CONFIRMATION, "subtasks": results}

        success_count = sum(1 for r in results if r.get("success"))
        partial = (0 < success_count < len(results))
        final_state = STATE_SUCCEEDED if success_count > 0 else STATE_FAILED
        await self.orchestrator.transition(
            parent_command_id, final_state, action="agent_swarm",
            result={"subtasks_ok": success_count, "total": len(results), "partial": partial},
            error=None if success_count > 0 else "Tous les sous-agents ont échoué.",
            websocket=websocket
        )
        return {
            "success": success_count > 0,
            "status": final_state,
            "partial": partial,
            "budget_used": {"calls": b.used_calls, "chars": b.used_chars},
            "subtasks": results,
        }


SWARM_COORDINATOR = AgentSwarmCoordinator()
