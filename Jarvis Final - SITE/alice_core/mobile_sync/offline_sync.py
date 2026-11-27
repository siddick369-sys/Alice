#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURES 26 & 27 — RESILIENT OFFLINE PWA SYNC & QUICK ACTIONS (ALICE-MOBILE-026/027, Wave 6).
- Synchronisation idempotente des notes et tâches autorisées (ZÉRO secret, token ou donnée vault).
- Détection explicite des conflits (ne détruit pas silencieusement une édition).
- Raccourcis d'actions rapides configurables soumis au RBAC et confirmations.
"""

import os
import json
import time
import threading
from typing import Dict, Any, List, Optional
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.security.rbac import RBAC, UserPrincipal


EXCLUDED_SYNC_TYPES = {"vault", "secret", "voiceprint", "token", "password", "private_key"}

DEFAULT_QUICK_ACTIONS = [
    {"id": "qa_cinema", "label": "Mode Cinéma", "command": "active la scène cinéma", "action": "ha_scene", "sensitive": False, "icon": "🎬", "order": 1},
    {"id": "qa_briefing", "label": "Briefing", "command": "donne mon briefing du jour", "action": "daily_briefing", "sensitive": False, "icon": "☀️", "order": 2},
    {"id": "qa_home_state", "label": "État Maison", "command": "état des équipements maison", "action": "ha_temperature", "sensitive": False, "icon": "🏠", "order": 3},
    {"id": "qa_quick_note", "label": "Note Rapide", "command": "nouvelle note rapide", "action": "memoriser", "sensitive": False, "icon": "📝", "order": 4},
    {"id": "qa_secure_home", "label": "Sécuriser Maison", "command": "active l'alarme et vérifie la maison", "action": "ha_alarme", "sensitive": True, "icon": "🛡️", "order": 5},
]


class MobileSyncAndShortcutsManager:
    """Gestionnaire backend de synchronisation PWA hors-ligne et raccourcis."""

    def __init__(self, state_file: Optional[str] = None, max_cache_ttl_seconds: float = 86400.0 * 7):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.state_file = state_file or os.path.join(base_dir, "alice_outputs", "mobile_sync_state.json")
        self.max_cache_ttl_seconds = max_cache_ttl_seconds
        # user_id -> {item_id -> item_dict}
        self.notes_tasks: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.applied_op_ids: set = set()
        # user_id -> list of quick action dicts
        self.quick_actions: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.notes_tasks = d.get("notes_tasks", {})
                self.applied_op_ids = set(d.get("applied_op_ids", []))
                self.quick_actions = d.get("quick_actions", {})
            except Exception:
                pass

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = f"{self.state_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "notes_tasks": self.notes_tasks,
                    "applied_op_ids": list(self.applied_op_ids)[-2000:],
                    "quick_actions": self.quick_actions,
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.state_file)

    def apply_sync_batch(self, principal: UserPrincipal, client_ops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronise un lot d'opérations hors ligne de manière idempotente :
        - Rejette toute tentative de mise en cache/sync de secrets ou données coffre-fort.
        - Détecte et remonte les conflits de version sans écraser silencieusement.
        """
        FEATURE_FLAGS.require_enabled("offline_sync")
        ok, reason = RBAC.authorize(principal, "assistant", "chat")
        if not ok:
            raise PermissionError(reason)

        t0 = time.perf_counter()
        uid = principal.user_id
        accepted = []
        conflicts = []
        skipped_idempotent = []
        rejected = []

        with self._lock:
            user_store = self.notes_tasks.setdefault(uid, {})

            for op in client_ops:
                op_id = str(op.get("op_id", "")).strip()
                item_id = str(op.get("item_id", "")).strip()
                item_type = str(op.get("item_type", "note")).lower().strip()
                if not item_id or not op_id:
                    rejected.append({"op_id": op_id, "reason": "missing_ids"})
                    continue

                if item_type in EXCLUDED_SYNC_TYPES or op.get("confidential") is True:
                    rejected.append({"op_id": op_id, "reason": "secrets_and_confidential_excluded_from_offline_cache"})
                    continue

                if op_id in self.applied_op_ids:
                    skipped_idempotent.append(op_id)
                    continue

                base_version = int(op.get("base_version", 0))
                existing = user_store.get(item_id)
                if existing and existing["version"] != base_version and op.get("resolution") != "force_client":
                    conflicts.append({
                        "item_id": item_id,
                        "op_id": op_id,
                        "client_title": op.get("title", ""),
                        "client_content": op.get("content", ""),
                        "client_base_version": base_version,
                        "server_version": existing["version"],
                        "server_content": existing["content"],
                        "server_updated_at": existing["updated_at"],
                    })
                    continue

                new_ver = (existing["version"] + 1) if existing else 1
                user_store[item_id] = {
                    "item_id": item_id,
                    "item_type": item_type,
                    "title": str(op.get("title", ""))[:120],
                    "content": str(op.get("content", ""))[:5000],
                    "done": bool(op.get("done", False)),
                    "deleted": bool(op.get("deleted", False)),
                    "version": new_ver,
                    "updated_at": time.time(),
                    "expires_at": time.time() + self.max_cache_ttl_seconds,
                }
                self.applied_op_ids.add(op_id)
                accepted.append({"op_id": op_id, "item_id": item_id, "version": new_ver})

            self._save()

        return {
            "success": True,
            "accepted": accepted,
            "conflicts": conflicts,
            "skipped_idempotent": skipped_idempotent,
            "rejected": rejected,
            "items": [i for i in self.notes_tasks.get(uid, {}).values() if not i.get("deleted")],
            "sync_latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # --- FEATURE 27 : Quick Actions / Shortcuts ---

    def get_quick_actions(self, principal: UserPrincipal) -> List[Dict[str, Any]]:
        uid = principal.user_id
        with self._lock:
            actions = self.quick_actions.get(uid)
            if actions is None:
                actions = [dict(a) for a in DEFAULT_QUICK_ACTIONS]
                self.quick_actions[uid] = actions
                self._save()
        # Filtrer ou marquer selon RBAC réel de l'utilisateur
        visible = []
        for a in sorted(actions, key=lambda x: x.get("order", 99)):
            allowed, _ = RBAC.check_action(principal.session_id, a.get("action", ""))
            entry = dict(a)
            entry["allowed"] = allowed
            visible.append(entry)
        return visible

    def save_quick_actions(self, principal: UserPrincipal, actions_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clean = []
        for idx, a in enumerate(actions_list[:12]):
            clean.append({
                "id": str(a.get("id") or f"qa_{idx}"),
                "label": str(a.get("label", "Action"))[:40],
                "command": str(a.get("command", ""))[:200],
                "action": str(a.get("action", "chat")),
                "sensitive": bool(a.get("sensitive", False)),
                "icon": str(a.get("icon", "⚡"))[:4],
                "order": int(a.get("order", idx + 1)),
            })
        with self._lock:
            self.quick_actions[principal.user_id] = clean
            self._save()
        return self.get_quick_actions(principal)


MOBILE_SYNC = MobileSyncAndShortcutsManager()
