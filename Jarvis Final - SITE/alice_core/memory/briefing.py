#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 14 — EXECUTIVE BRIEFING (ALICE-MEM-014, Wave 2).
Génère une synthèse structurée en distinguant explicitement :
EXTRACTED (faits extraits), INTERPRETED (analyse), RECOMMENDED (actions), MISSING (absents).
Aucune invention de décisions ; citations rigoureuses conservées.
"""

import re
import time
from typing import Dict, Any, List, Optional
from alice_rag import RAG_ENGINE, AliceRAGEngine


DATE_REGEX = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}\s+(?:janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)(?:\s+\d{4})?)\b",
    re.IGNORECASE,
)


class ExecutiveBriefingGenerator:
    """Générateur de fiches de synthèse documentaire structurées avec provenance stricte."""

    def __init__(self, rag_engine: Optional[AliceRAGEngine] = None):
        self.rag = rag_engine or RAG_ENGINE

    def generate(
        self,
        topic_or_query: str,
        owner_id: Optional[str] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Produit le briefing structuré avec les 9 rubriques réglementaires.
        Si `documents` n'est pas fourni, interroge `self.rag.search()`.
        """
        chunks = documents if documents is not None else self.rag.search(topic_or_query, top_k=top_k, owner_id=owner_id)

        if not chunks:
            return {
                "success": True,
                "status": "NO_DATA",
                "topic": topic_or_query,
                "epistemic_markers": True,
                "sections": {
                    "resume_executif": "[MISSING] Aucune source documentaire trouvée sur ce sujet.",
                    "contexte": {"label": "MISSING", "items": []},
                    "points_cles": {"label": "EXTRACTED", "items": []},
                    "decisions_identifiees": {"label": "EXTRACTED", "items": [], "note": "Aucune décision explicite trouvée."},
                    "dates_importantes": {"label": "EXTRACTED", "items": []},
                    "risques": {"label": "INTERPRETED", "items": []},
                    "actions_a_entreprendre": {"label": "RECOMMENDED", "items": []},
                    "elements_incertains": {"label": "MISSING", "items": ["Aucun document indexé correspondant à la requête."]},
                    "sources_et_references": [],
                },
            }

        key_points: List[Dict[str, str]] = []
        decisions: List[Dict[str, str]] = []
        dates: List[Dict[str, str]] = []
        risks: List[Dict[str, str]] = []
        actions: List[Dict[str, str]] = []
        uncertain: List[str] = []
        sources: List[str] = []

        for ch in chunks:
            cit = ch.get("citation") or f"[Source: {ch.get('source_file', 'doc')} | {ch.get('provenance', 'N/A')}]"
            if cit not in sources:
                sources.append(cit)
            txt = ch.get("text", "")
            sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", txt) if len(s.strip()) > 10]

            for sent in sentences:
                s_low = sent.lower()
                # Points clés factuels extraits
                if len(key_points) < 8:
                    key_points.append({"label": "EXTRACTED", "text": sent, "citation": cit})

                # Décisions explicites UNIQUEMENT (jamais inventées)
                if any(k in s_low for k in ("décidé", "decide", "approuvé", "validé", "adopté", "acté", "résolu")):
                    decisions.append({"label": "EXTRACTED", "text": sent, "citation": cit})

                # Dates importantes
                for m in DATE_REGEX.findall(sent):
                    dates.append({"label": "EXTRACTED", "date": m, "context": sent[:160], "citation": cit})

                # Risques explicitement mentionnés
                if any(k in s_low for k in ("risque", "alerte", "danger", "critique", "blocage", "retard", "pénalité", "échec")):
                    risks.append({"label": "INTERPRETED", "text": sent, "citation": cit})

                # Actions à entreprendre
                if any(k in s_low for k in ("doit", "devra", "action", "prévoir", "planifier", "corriger", "vérifier")):
                    actions.append({"label": "RECOMMENDED", "text": sent, "citation": cit})

        if not decisions:
            uncertain.append("Aucune décision formellement actée n'apparaît dans les extraits disponibles.")
        if not dates:
            uncertain.append("Aucune échéance datée explicite détectée dans les sources.")
        if not risks:
            uncertain.append("Aucun risque explicite mentionné ; une revue complémentaire peut être requise.")

        resume_parts = [f"Synthèse sur '{topic_or_query}' basée sur {len(sources)} référence(s) vérifiée(s)."]
        if key_points:
            resume_parts.append(f"Élément principal [EXTRACTED] : {key_points[0]['text']} {key_points[0]['citation']}")

        return {
            "success": True,
            "status": "OK",
            "topic": topic_or_query,
            "generated_at": time.time(),
            "epistemic_markers": True,
            "sections": {
                "resume_executif": " ".join(resume_parts),
                "contexte": {"label": "EXTRACTED", "items": [f"Corpus analysé : {', '.join(sources)}"]},
                "points_cles": {"label": "EXTRACTED", "items": key_points},
                "decisions_identifiees": {"label": "EXTRACTED", "items": decisions},
                "dates_importantes": {"label": "EXTRACTED", "items": dates},
                "risques": {"label": "INTERPRETED", "items": risks},
                "actions_a_entreprendre": {"label": "RECOMMENDED", "items": actions},
                "elements_incertains": {"label": "MISSING", "items": uncertain},
                "sources_et_references": sources,
            },
        }


BRIEFING_GENERATOR = ExecutiveBriefingGenerator()
