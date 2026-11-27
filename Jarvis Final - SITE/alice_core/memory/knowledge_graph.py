#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 12 — PERSONAL KNOWLEDGE GRAPH (ALICE-MEM-012, Wave 2).
Graphe relationnel persistant typé avec provenance, confiance, statut explicite
HYPOTHESIS vs VERIFIED, isolation stricte par propriétaire et contrôle CRUD complet.
"""

import os
import json
import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from alice_core.security.rbac import RBAC, UserPrincipal


ALLOWED_ENTITY_TYPES = {
    "person", "contact", "project", "organization",
    "document", "preference", "event", "object"
}

ALLOWED_RELATIONS = {
    "connaît", "travaille_sur", "appartient_a",
    "est_lie_a", "prefere", "a_participe_a"
}


class PersonalKnowledgeGraph:
    """Graphe relationnel persistant isolé par propriétaire."""

    def __init__(self, graph_file: Optional[str] = None):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.graph_file = graph_file or os.path.join(base_dir, "alice_outputs", "knowledge_graph.json")
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relations: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.graph_file):
            try:
                with open(self.graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.entities = data.get("entities", {})
                self.relations = data.get("relations", {})
            except Exception:
                self.entities = {}
                self.relations = {}

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
            tmp = f"{self.graph_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"entities": self.entities, "relations": self.relations}, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.graph_file)

    def upsert_entity(
        self,
        name: str,
        entity_type: str,
        owner_id: str,
        visibility: str = "private",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        etype = entity_type.lower().strip()
        if etype not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"Type d'entité non autorisé : {entity_type}")
        norm_name = name.strip()
        if not norm_name:
            raise ValueError("Nom d'entité vide.")

        with self._lock:
            for eid, ent in self.entities.items():
                if ent["owner_id"] == owner_id and ent["name"].lower() == norm_name.lower() and ent["entity_type"] == etype:
                    if metadata:
                        ent["metadata"].update(metadata)
                    ent["updated_at"] = time.time()
                    self._save()
                    return ent

            eid = f"ent_{uuid.uuid4().hex[:10]}"
            ent = {
                "entity_id": eid,
                "name": norm_name,
                "entity_type": etype,
                "owner_id": owner_id,
                "visibility": visibility,
                "metadata": dict(metadata or {}),
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self.entities[eid] = ent
            self._save()
            return ent

    def add_relation(
        self,
        source_id: str,
        relation: str,
        target_id: str,
        owner_id: str,
        source: str = "user_declaration",
        confidence: float = 0.7,
        visibility: str = "private",
        provenance: str = "",
        explicitly_confirmed: bool = False,
    ) -> Dict[str, Any]:
        rel_clean = relation.strip()
        if rel_clean not in ALLOWED_RELATIONS:
            raise ValueError(f"Type de relation non reconnu : {rel_clean}")
        with self._lock:
            if source_id not in self.entities or target_id not in self.entities:
                raise KeyError("Entité source ou cible introuvable dans le graphe.")
            # Isolation stricte : impossible de lier des entités appartenant à un autre utilisateur privé
            src_ent = self.entities[source_id]
            tgt_ent = self.entities[target_id]
            if (src_ent["visibility"] == "private" and src_ent["owner_id"] != owner_id) or (
                tgt_ent["visibility"] == "private" and tgt_ent["owner_id"] != owner_id
            ):
                raise PermissionError("Isolation graphe violée : entité privée appartenant à un autre utilisateur.")

            conf = max(0.0, min(1.0, float(confidence)))
            # Règle absolue : une inférence/hypothèse n'est JAMAIS promue fait certain automatiquement
            status = "VERIFIED" if (explicitly_confirmed and conf >= 0.85) else "HYPOTHESIS"

            edge_id = f"rel_{uuid.uuid4().hex[:10]}"
            edge = {
                "edge_id": edge_id,
                "source_id": source_id,
                "relation": rel_clean,
                "target_id": target_id,
                "source": source,
                "extracted_at": time.time(),
                "confidence": round(conf, 3),
                "status": status,
                "owner_id": owner_id,
                "visibility": visibility,
                "provenance": provenance,
            }
            self.relations[edge_id] = edge
            self._save()
            return edge

    def confirm_relation(self, principal: UserPrincipal, edge_id: str) -> Dict[str, Any]:
        with self._lock:
            edge = self.relations.get(edge_id)
            if not edge:
                raise KeyError("Relation introuvable.")
            if not RBAC.check_owner_isolation(principal, edge["owner_id"], edge["visibility"]):
                raise PermissionError("Accès refusé à cette relation.")
            edge["status"] = "VERIFIED"
            edge["confidence"] = max(edge["confidence"], 0.95)
            self._save()
            return edge

    def correct_relation(self, principal: UserPrincipal, edge_id: str, new_relation: Optional[str] = None, new_target_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            edge = self.relations.get(edge_id)
            if not edge:
                raise KeyError("Relation introuvable.")
            if not RBAC.check_owner_isolation(principal, edge["owner_id"], edge["visibility"]):
                raise PermissionError("Modification refusée.")
            if new_relation:
                if new_relation not in ALLOWED_RELATIONS:
                    raise ValueError(f"Relation invalide : {new_relation}")
                edge["relation"] = new_relation
            if new_target_id:
                if new_target_id not in self.entities:
                    raise KeyError("Nouvelle entité cible introuvable.")
                edge["target_id"] = new_target_id
            edge["status"] = "VERIFIED"
            self._save()
            return edge

    def delete_relation(self, principal: UserPrincipal, edge_id: str) -> bool:
        with self._lock:
            edge = self.relations.get(edge_id)
            if not edge:
                return False
            if not RBAC.check_owner_isolation(principal, edge["owner_id"], edge["visibility"]):
                raise PermissionError("Suppression refusée.")
            del self.relations[edge_id]
            self._save()
            return True

    def delete_entity(self, principal: UserPrincipal, entity_id: str) -> bool:
        with self._lock:
            ent = self.entities.get(entity_id)
            if not ent:
                return False
            if not RBAC.check_owner_isolation(principal, ent["owner_id"], ent["visibility"]):
                raise PermissionError("Suppression refusée.")
            del self.entities[entity_id]
            # Supprimer toutes les arêtes liées
            orphan_edges = [eid for eid, r in self.relations.items() if r["source_id"] == entity_id or r["target_id"] == entity_id]
            for eid in orphan_edges:
                del self.relations[eid]
            self._save()
            return True

    def query_user_graph(self, principal: UserPrincipal, query_name: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            visible_entities = [
                e for e in self.entities.values()
                if RBAC.check_owner_isolation(principal, e["owner_id"], e["visibility"])
                and (not query_name or query_name.lower() in e["name"].lower())
            ]
            visible_ids = {e["entity_id"] for e in visible_entities}
            visible_relations = [
                r for r in self.relations.values()
                if RBAC.check_owner_isolation(principal, r["owner_id"], r["visibility"])
                and (not query_name or r["source_id"] in visible_ids or r["target_id"] in visible_ids)
            ]
            return {"entities": visible_entities, "relations": visible_relations}


KNOWLEDGE_GRAPH = PersonalKnowledgeGraph()
