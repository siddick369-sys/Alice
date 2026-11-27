#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALICE API BRIDGE — PASSERELLE UNIFIÉE HTTP / WEBSOCKET / ACTIONS IA (MISSION 008).
Connecte les 6 piliers d'alice_core avec main2.py, mobile/ et frontend/,
en appliquant uniformément RBAC, FeatureFlags, AuditLogger et cycle de vie 9 états.
"""

import os
import json
import time
import asyncio
import http.cookies
from urllib.parse import urlsplit, parse_qs
from typing import Dict, Any, Optional, Tuple, Callable

from alice_core.contracts import AliceSecurityError, FeatureDisabledError
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.audit import AUDIT_LOGGER, sanitize_for_log
from alice_core.security.rbac import RBAC, Role, UserPrincipal
from alice_core.security.vault import VAULT_MANAGER
from alice_core.ops.observability import OBSERVABILITY
from alice_core.voice.pipeline import BARGE_IN_MANAGER, AudioState
from alice_core.voice.whisper_mode import WHISPER_MANAGER
from alice_core.voice.followup import FOLLOWUP_MANAGER
from alice_core.voice.voice_id import VOICE_ID_MANAGER
from alice_core.voice.acoustic_context import ACOUSTIC_CONTEXT
from alice_core.memory.knowledge_graph import KNOWLEDGE_GRAPH
from alice_core.memory.watchdog import HOT_FOLDER_WATCHDOG
from alice_core.memory.briefing import BRIEFING_GENERATOR
from alice_core.memory.commitments import COMMITMENT_TRACKER, CommitmentState
from alice_core.iot.ha_client import HA_CLIENT
from alice_core.iot.routines import PREDICTIVE_ROUTINES
from alice_core.iot.eco_manager import ECO_MANAGER
from alice_core.iot.self_healing import SELF_HEALING_IOT
from alice_core.iot.presence import PRESENCE_SIMULATOR
from alice_core.iot.thermal import THERMAL_CONTROLLER
from alice_core.vision.analyzer import VISUAL_ANALYZER
from alice_core.vision.ocr_receipts import RECEIPT_OCR
from alice_core.vision.video_sentinel import VIDEO_SENTINEL
from alice_core.vision.visual_memory import VISUAL_MEMORY
from alice_core.vision.safety_zones import SAFETY_ZONES
from alice_core.automation.jobs import JOB_MANAGER
from alice_core.automation.agent_swarm import SWARM_COORDINATOR
from alice_core.automation.web_agent import WEB_AGENT
from alice_core.automation.webhooks import WEBHOOK_GATEWAY
from alice_core.automation.daily_briefing import DAILY_BRIEFING
from alice_core.mobile_sync.offline_sync import MOBILE_SYNC
from alice_rag import RAG_ENGINE


class AliceAPIBridge:
    """Façade unique connectant routes HTTP REST, WebSocket et dispatch IA."""

    @staticmethod
    def extract_session_from_headers(headers: Any, session_verifier: Callable[[str, str], bool]) -> Optional[Tuple[str, UserPrincipal]]:
        cookie_hdr = headers.get("Cookie") if headers else None
        if not cookie_hdr:
            return None
        try:
            cookies = http.cookies.SimpleCookie(cookie_hdr)
            if "alice_session" in cookies:
                raw_val = cookies["alice_session"].value
                if ":" in raw_val:
                    sid, tok = raw_val.split(":", 1)
                    if session_verifier(sid, tok):
                        return sid, RBAC.get_principal(sid)
        except Exception:
            pass
        return None

    @staticmethod
    def _verify_csrf(headers: Any, sid: str, csrf_verifier: Callable[[str, str], bool], client_ip: str) -> bool:
        csrf_hdr = headers.get("X-CSRF-Token") if headers else None
        if csrf_hdr and csrf_verifier(sid, csrf_hdr):
            return True
        if client_ip in ("127.0.0.1", "::1") and not (headers.get("Origin") if headers else None):
            return True
        return False

    def handle_http_get(
        self,
        raw_path: str,
        headers: Any,
        client_ip: str,
        session_verifier: Callable[[str, str], bool],
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """Traite les routes GET /api/*. Retourne None si la route ne relève pas d'alice_core."""
        parsed = urlsplit(raw_path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if not path.startswith("/api/"):
            return None

        # Laisser main2 gérer /api/auth/token et /api/pair/status
        if path in ("/api/auth/token", "/api/pair/status"):
            return None

        # Toutes les routes /api/* Mission 008 exigent une session authentifiée valide
        auth = self.extract_session_from_headers(headers, session_verifier)
        if not auth:
            return 401, {"error": "Authentification requise."}
        sid, principal = auth

        try:
            if path == "/api/me":
                return 200, {
                    "session_id": sid,
                    "user_id": principal.user_id,
                    "role": principal.role.value,
                    "step_up_active": principal.has_step_up(),
                }

            if path == "/api/ops/metrics":
                svc_filter = qs.get("service", [None])[0]
                res = OBSERVABILITY.get_authorized_dashboard(principal, service_filter=svc_filter)
                return (200 if res.get("authorized") else 403), res

            if path == "/api/ops/export":
                res = OBSERVABILITY.export_authorized(principal, fmt="json")
                return (200 if res.get("authorized") else 403), res

            if path == "/api/flags":
                ok, reason = RBAC.authorize(principal, "flags", "manage")
                if not ok:
                    return 403, {"error": reason}
                return 200, {"flags": FEATURE_FLAGS.list_all()}

            if path == "/api/quick_actions":
                return 200, {"actions": MOBILE_SYNC.get_quick_actions(principal)}

            if path == "/api/sync/notes":
                res = MOBILE_SYNC.apply_sync_batch(principal, [])
                return 200, res

            if path == "/api/kg":
                ok, reason = RBAC.authorize(principal, "memory", "read")
                if not ok:
                    return 403, {"error": reason}
                q = qs.get("q", [None])[0]
                return 200, KNOWLEDGE_GRAPH.query_user_graph(principal, query_name=q)

            if path == "/api/commitments":
                ok, reason = RBAC.authorize(principal, "memory", "read")
                if not ok:
                    return 403, {"error": reason}
                return 200, {"commitments": COMMITMENT_TRACKER.list_for_owner(principal.user_id)}

            if path == "/api/briefing":
                mode = qs.get("mode", ["morning"])[0]
                guests = qs.get("guests", ["0"])[0] == "1"
                if mode == "evening":
                    return 200, DAILY_BRIEFING.build_evening_debrief(principal)
                return 200, DAILY_BRIEFING.build_morning_briefing(principal, guests_present=guests)

            if path == "/api/jobs/stats":
                ok, reason = RBAC.authorize(principal, "ops", "dashboard")
                if not ok:
                    return 403, {"error": reason}
                return 200, {"queue": JOB_MANAGER.get_queue_stats()}

            if path == "/api/iot/routines":
                ok, reason = RBAC.authorize(principal, "iot", "routine_manage")
                if not ok:
                    return 403, {"error": reason}
                return 200, {
                    "suggestions": PREDICTIVE_ROUTINES.detect_candidates(),
                    "routines": list(PREDICTIVE_ROUTINES.routines.values()),
                }

            return 404, {"error": "Endpoint API inconnu."}
        except FeatureDisabledError as fde:
            return 403, {"error": str(fde), "feature_disabled": True}
        except AliceSecurityError as ase:
            return 403, {"error": str(ase)}
        except PermissionError as pe:
            return 403, {"error": str(pe)}
        except Exception as e:
            return 500, {"error": f"Erreur interne : {e}"}

    def handle_http_post(
        self,
        raw_path: str,
        raw_body: bytes,
        headers: Any,
        client_ip: str,
        session_verifier: Callable[[str, str], bool],
        csrf_verifier: Callable[[str, str], bool],
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """Traite les routes POST /api/*. Retourne None pour /api/pair et /api/revoke_session."""
        path = urlsplit(raw_path).path
        if not path.startswith("/api/"):
            return None
        if path in ("/api/pair", "/api/revoke_session"):
            return None

        # 1. Passerelle Webhook HMAC entrante (auth par HMAC + anti-rejeu, pas par cookie)
        if path.startswith("/api/webhooks/"):
            connector_id = path[len("/api/webhooks/"):].strip("/")
            sig = headers.get("X-Alice-Signature") if headers else None
            ts_str = headers.get("X-Alice-Timestamp") if headers else None
            nonce = headers.get("X-Alice-Nonce") if headers else None
            ok, code, res = WEBHOOK_GATEWAY.verify_and_parse_incoming(connector_id, sig, ts_str, nonce, raw_body)
            return code, res

        # 2. Toutes les autres mutations exigent session + CSRF valide
        auth = self.extract_session_from_headers(headers, session_verifier)
        if not auth:
            return 401, {"error": "Authentification requise."}
        sid, principal = auth

        if not self._verify_csrf(headers, sid, csrf_verifier, client_ip):
            return 403, {"error": "Échec de validation du jeton CSRF."}

        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            return 400, {"error": "JSON invalide."}

        try:
            if path == "/api/flags":
                ok, reason = RBAC.authorize(principal, "flags", "manage")
                if not ok:
                    return 403, {"error": reason}
                flag_name = str(data.get("flag", ""))
                enabled = bool(data.get("enabled", False))
                FEATURE_FLAGS.set_flag(flag_name, enabled)
                AUDIT_LOGGER.log("FLAGS", "flag_toggled", principal.user_id, principal.role.value, sid, "OK", {"flag": flag_name, "enabled": enabled})
                return 200, {"success": True, "flag": flag_name, "enabled": enabled}

            if path == "/api/sync/notes":
                ops = data.get("ops", [])
                return 200, MOBILE_SYNC.apply_sync_batch(principal, ops)

            if path == "/api/quick_actions":
                acts = data.get("actions", [])
                return 200, {"success": True, "actions": MOBILE_SYNC.save_quick_actions(principal, acts)}

            if path == "/api/vision/stage":
                ok, reason = RBAC.authorize(principal, "vision", "monitor")
                if not ok:
                    return 403, {"error": reason}
                res = VISUAL_ANALYZER.stage_preview(
                    image_b64=data.get("image_b64", ""),
                    owner_id=principal.user_id,
                    question=data.get("question", ""),
                    retention_policy=data.get("retention_policy"),
                )
                return (200 if res.get("success") else 400), res

            if path == "/api/vision/confirm":
                ok, reason = RBAC.authorize(principal, "vision", "monitor")
                if not ok:
                    return 403, {"error": reason}
                res = VISUAL_ANALYZER.confirm_and_analyze(
                    preview_id=data.get("preview_id", ""),
                    owner_id=principal.user_id,
                    confirmed=bool(data.get("confirmed", False)),
                )
                if not res.get("success") and res.get("status") == "FORBIDDEN":
                    return 403, res
                return 200, res

            if path == "/api/vision/receipt":
                ok, reason = RBAC.authorize(principal, "vision", "monitor")
                if not ok:
                    return 403, {"error": reason}
                stage = VISUAL_ANALYZER.stage_preview(data.get("image_b64", ""), principal.user_id, "receipt_ocr", "keep_24h")
                if not stage.get("success"):
                    return 400, stage
                img_path = VISUAL_ANALYZER.staged[stage["preview_id"]]["path"]
                res = RECEIPT_OCR.process_receipt(img_path, owner_id=principal.user_id, confirmed_save=bool(data.get("confirmed", False)))
                return 200, res

            if path == "/api/kg":
                ok, reason = RBAC.authorize(principal, "memory", "write")
                if not ok:
                    return 403, {"error": reason}
                e1 = KNOWLEDGE_GRAPH.upsert_entity(data["source"], data.get("source_type", "person"), principal.user_id)
                e2 = KNOWLEDGE_GRAPH.upsert_entity(data["target"], data.get("target_type", "project"), principal.user_id)
                rel = KNOWLEDGE_GRAPH.add_relation(
                    e1["entity_id"], data.get("relation", "est_lie_a"), e2["entity_id"],
                    owner_id=principal.user_id, confidence=float(data.get("confidence", 0.9)),
                    explicitly_confirmed=bool(data.get("confirmed", True)),
                )
                return 200, {"success": True, "relation": rel}

            if path == "/api/commitments/confirm":
                ok, reason = RBAC.authorize(principal, "memory", "write")
                if not ok:
                    return 403, {"error": reason}
                st = CommitmentState(data.get("state", "CONFIRMED"))
                item = COMMITMENT_TRACKER.transition(data["commitment_id"], st, owner_id=principal.user_id, deadline=data.get("deadline"))
                return 200, {"success": True, "commitment": item}

            if path == "/api/vault/unlock":
                # Exige strictement un principal OWNER disposant déjà d'une vérification step-up serveur valide
                ok = VAULT_MANAGER.unlock(principal, data.get("passphrase", ""))
                return 200, {"unlocked": ok}

            if path == "/api/vault/lock":
                VAULT_MANAGER.lock()
                return 200, {"locked": True}

            return 404, {"error": "Endpoint POST inconnu."}
        except FeatureDisabledError as fde:
            return 403, {"error": str(fde), "feature_disabled": True}
        except AliceSecurityError as ase:
            return 403, {"error": str(ase)}
        except PermissionError as pe:
            return 403, {"error": str(pe)}
        except Exception as e:
            return 400, {"error": str(e)}

    async def handle_ws_message(self, websocket: Any, data: Dict[str, Any], session_id: str) -> bool:
        """Gère les nouveaux types de trames WebSocket Mission 008 avec contrôle RBAC strict."""
        msg_type = data.get("type")
        principal = RBAC.get_principal(session_id)

        if msg_type == "barge_in":
            ok, reason = RBAC.authorize(principal, "voice", "followup")
            if not ok:
                await websocket.send(json.dumps({"type": "error", "message": reason}, ensure_ascii=False))
                return True
            res = await BARGE_IN_MANAGER.interrupt(source="ws_mobile")
            await websocket.send(json.dumps({"type": "barge_in_ack", **res}, ensure_ascii=False))
            return True

        if msg_type == "whisper_mode":
            ok, reason = RBAC.authorize(principal, "flags", "manage")
            if not ok:
                await websocket.send(json.dumps({"type": "error", "message": reason}, ensure_ascii=False))
                return True
            mode = str(data.get("mode", "auto"))
            try:
                WHISPER_MANAGER.set_mode(mode)
                await websocket.send(json.dumps({"type": "whisper_state", "mode": mode}))
            except Exception as e:
                await websocket.send(json.dumps({"type": "error", "message": str(e)}))
            return True

        if msg_type == "followup_cancel":
            ok, reason = RBAC.authorize(principal, "voice", "followup")
            if not ok:
                await websocket.send(json.dumps({"type": "error", "message": reason}, ensure_ascii=False))
                return True
            res = FOLLOWUP_MANAGER.cancel(session_id, reason="ws_cancel")
            await websocket.send(json.dumps(res, ensure_ascii=False))
            return True

        if msg_type == "followup_toggle":
            ok, reason = RBAC.authorize(principal, "voice", "followup")
            if not ok:
                await websocket.send(json.dumps({"type": "error", "message": reason}, ensure_ascii=False))
                return True
            enabled = bool(data.get("enabled", True))
            FOLLOWUP_MANAGER.set_session_enabled(session_id, enabled)
            await websocket.send(json.dumps({"type": "followup_config", "enabled": enabled}))
            return True

        if msg_type == "sync_notes":
            try:
                res = MOBILE_SYNC.apply_sync_batch(principal, data.get("ops", []))
                await websocket.send(json.dumps({"type": "sync_result", **res}, ensure_ascii=False))
            except Exception as e:
                await websocket.send(json.dumps({"type": "sync_error", "error": str(e)}))
            return True

        return False

    async def dispatch_extended_action(self, action: str, data: Dict[str, Any], session_id: str, weather_fn=None) -> Optional[str]:
        """Exécute les nouvelles actions IA des Piliers 1 à 6 avec contrôle RBAC et FeatureFlags."""
        ok_rbac, rbac_msg = RBAC.check_action(session_id, action, context=data)
        if not ok_rbac:
            return rbac_msg
        principal = RBAC.get_principal(session_id)

        if action == "daily_briefing":
            if weather_fn:
                DAILY_BRIEFING.weather_provider = weather_fn
            mode = data.get("mode", "morning")
            guests = bool(data.get("guests_present", False))
            if mode == "evening":
                res = DAILY_BRIEFING.build_evening_debrief(principal)
                return f"Débriefing du soir : {len(res['sections']['pending_commitments'])} engagement(s) en attente."
            res = DAILY_BRIEFING.build_morning_briefing(principal, guests_present=guests)
            sec = res.get("sections", {})
            return f"Briefing du matin : {sec.get('weather', '')} Engagements en attente : {len(sec.get('commitments_pending', []))}."

        if action == "executive_briefing":
            query = data.get("topic", "general")
            res = BRIEFING_GENERATOR.generate(query, owner_id=principal.user_id)
            return res["sections"]["resume_executif"]

        if action == "knowledge_graph_add":
            ok, reason = RBAC.authorize(principal, "memory", "write")
            if not ok:
                return reason
            e1 = KNOWLEDGE_GRAPH.upsert_entity(data.get("source", ""), data.get("source_type", "person"), principal.user_id)
            e2 = KNOWLEDGE_GRAPH.upsert_entity(data.get("target", ""), data.get("target_type", "project"), principal.user_id)
            KNOWLEDGE_GRAPH.add_relation(e1["entity_id"], data.get("relation", "est_lie_a"), e2["entity_id"], principal.user_id, explicitly_confirmed=True)
            return f"Relation enregistrée dans votre graphe de connaissances : {e1['name']} -> {e2['name']}."

        if action == "knowledge_graph_query":
            ok, reason = RBAC.authorize(principal, "memory", "read")
            if not ok:
                return reason
            res = KNOWLEDGE_GRAPH.query_user_graph(principal, data.get("query"))
            return f"{len(res['entities'])} entité(s) et {len(res['relations'])} relation(s) trouvées."

        if action == "iot_eco":
            res = ECO_MANAGER.evaluate_consumption()
            if not res.get("success"):
                return f"Suivi énergétique indisponible : {res.get('data_quality')}."
            return f"Puissance actuelle : {res['power_va']} VA. " + (" ".join(res["recommendations"]) or "Consommation normale.")

        if action == "iot_health":
            diag = SELF_HEALING_IOT.run_fleet_diagnostic(data.get("entities", ["light.salon"]))
            return diag["summary"]

        if action == "visual_memory_search":
            res = VISUAL_MEMORY.search_object(principal.user_id, data.get("object", ""))
            return res["message"]

        if action == "web_agent_check":
            res = WEB_AGENT.fetch_safe(data.get("url", ""))
            if not res.get("success"):
                return res.get("message") or res.get("error") or "Page inaccessible."
            return f"Page consultée ({res['http_code']}) : {res['raw_excerpt'][:300]}"

        return None


API_BRIDGE = AliceAPIBridge()
