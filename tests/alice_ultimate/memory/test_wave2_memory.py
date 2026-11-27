#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS WAVE 2 — PILIER 3 MÉMOIRE & INTELLIGENCE DOCUMENTAIRE (FEATURES 11 À 15)
Couvre Hybrid RAG (BM25 + Dense + RRF), Knowledge Graph, Hot-Folder Watchdog
(.docx/.epub/.pdf/.txt), Executive Briefing et Commitment Tracker.
"""

import os
import sys
import zipfile
import tempfile
import unittest

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_rag import AliceRAGEngine
from alice_core.memory.knowledge_graph import PersonalKnowledgeGraph
from alice_core.memory.watchdog import HotFolderWatchdog
from alice_core.memory.briefing import ExecutiveBriefingGenerator
from alice_core.memory.commitments import CommitmentTracker, CommitmentState
from alice_core.security.rbac import RBACPolicyEngine, Role


def _create_sample_docx(path: str, paragraphs: list):
    xml_paras = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{xml_paras}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", doc_xml)


def _create_sample_epub(path: str, html_body: str):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/chap1.xhtml", f"<html><body>{html_body}</body></html>")


class TestWave2Memory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb_dir = os.path.join(self.tmp.name, "kb")
        os.makedirs(self.kb_dir, exist_ok=True)
        self.idx_file = os.path.join(self.tmp.name, "rag_index.json")
        self.rag = AliceRAGEngine(knowledge_dir=self.kb_dir, index_file=self.idx_file)
        self.rbac = RBACPolicyEngine()
        self.owner = self.rbac.register_principal("s_o", "owner1", Role.OWNER)
        self.m1 = self.rbac.register_principal("s_m1", "alice_u1", Role.MEMBER)
        self.m2 = self.rbac.register_principal("s_m2", "bob_u2", Role.MEMBER)

    def tearDown(self):
        self.tmp.cleanup()

    def test_01_hybrid_rag_exact_code_isolation_and_corruption_recovery(self):
        with open(os.path.join(self.kb_dir, "inventaire.txt"), "w", encoding="utf-8") as f:
            f.write("Équipement critique : Onduleur APC numéro de série SN-9942-XR installé au garage.\n")
        with open(os.path.join(self.kb_dir, "securite.md"), "w", encoding="utf-8") as f:
            f.write("# Protocole TLS\nLes certificats doivent être renouvelés tous les 90 jours.\n")

        self.rag.index_knowledge_directory(force=True)
        # Recherche exacte de numéro de série
        res_sn = self.rag.search("SN-9942-XR", top_k=2, owner_id="alice_u1")
        self.assertGreater(len(res_sn), 0)
        self.assertEqual(res_sn[0]["source_file"], "inventaire.txt")

        # Document privé pour bob_u2
        priv_file = os.path.join(self.tmp.name, "note_bob.txt")
        with open(priv_file, "w", encoding="utf-8") as f:
            f.write("Code confidentiel projet Orion : ZETA-771.")
        self.rag.ingest_file(priv_file, owner_id="bob_u2", visibility="private")

        # Isolation : alice_u1 ne doit PAS voir note_bob
        res_alice = self.rag.search("ZETA-771", top_k=3, owner_id="alice_u1")
        self.assertEqual(len(res_alice), 0)
        res_bob = self.rag.search("ZETA-771", top_k=3, owner_id="bob_u2")
        self.assertEqual(len(res_bob), 1)

        # Évaluation comparative Precision/Recall
        eval_rep = self.rag.evaluate_retrieval([
            ("SN-9942-XR onduleur", ["inventaire.txt"]),
            ("protocole certificats TLS", ["securite.md"]),
        ])
        self.assertGreaterEqual(eval_rep["hybrid"]["recall_at_k"], 1.0)

        # Corruption de l'index JSON -> récupération propre sans crash
        with open(self.idx_file, "w", encoding="utf-8") as f:
            f.write("{CORRUPTED_JSON!!!")
        rag_rec = AliceRAGEngine(knowledge_dir=self.kb_dir, index_file=self.idx_file)
        self.assertTrue(rag_rec.index_corrupted_recovered)
        res_after = rag_rec.search("certificats", top_k=1)
        self.assertEqual(len(res_after), 1)

    def test_02_knowledge_graph_hypothesis_vs_verified_and_isolation(self):
        kg = PersonalKnowledgeGraph(graph_file=os.path.join(self.tmp.name, "kg.json"))
        e1 = kg.upsert_entity("Marc", "person", owner_id="alice_u1", visibility="private")
        e2 = kg.upsert_entity("Projet Helios", "project", owner_id="alice_u1", visibility="private")

        # Une confiance 0.72 ou non confirmée reste HYPOTHESIS
        rel = kg.add_relation(e1["entity_id"], "travaille_sur", e2["entity_id"], owner_id="alice_u1", confidence=0.72)
        self.assertEqual(rel["status"], "HYPOTHESIS")

        # Confirmation utilisateur -> VERIFIED
        kg.confirm_relation(self.m1, rel["edge_id"])
        q_m1 = kg.query_user_graph(self.m1, "Marc")
        self.assertEqual(q_m1["relations"][0]["status"], "VERIFIED")

        # Isolation : bob_u2 ne voit rien du graphe privé de alice_u1
        q_m2 = kg.query_user_graph(self.m2, "Marc")
        self.assertEqual(len(q_m2["entities"]), 0)
        with self.assertRaises(PermissionError):
            kg.delete_entity(self.m2, e1["entity_id"])

    def test_03_hot_folder_watchdog_docx_epub_large_queue_and_cleanup(self):
        docx_path = os.path.join(self.kb_dir, "contrat.docx")
        epub_path = os.path.join(self.kb_dir, "manuel.epub")
        _create_sample_docx(docx_path, ["Décision validée : livraison serveur prévue le 12/12/2026."])
        _create_sample_epub(epub_path, "<h1>Chapitre Architecture</h1><p>Guide domotique KNX et Zigbee.</p>")

        wd = HotFolderWatchdog(watch_dir=self.kb_dir, rag_engine=self.rag, large_file_bytes=200 * 1024, stability_delay=0.02)
        stats1 = wd.scan_once()
        self.assertEqual(stats1["processed"], 2)

        # Deuxième passe sans modification -> déduplication SHA-256
        stats2 = wd.scan_once()
        self.assertEqual(stats2["processed"], 0)
        self.assertEqual(stats2["skipped_dedup"], 2)

        # Recherche sur DOCX et EPUB
        self.assertEqual(self.rag.search("livraison serveur", top_k=1)[0]["source_file"], "contrat.docx")
        self.assertEqual(self.rag.search("Zigbee domotique", top_k=1)[0]["source_file"], "manuel.epub")

        # Fichier volumineux -> file asynchrone
        big_path = os.path.join(self.kb_dir, "gros_log.txt")
        with open(big_path, "w", encoding="utf-8") as f:
            f.write(("Ligne journal système archive audit alpha.\n" * 6000))
        stats3 = wd.scan_once()
        self.assertEqual(stats3["queued_large"], 1)
        res_big = wd.process_large_queue_step()
        self.assertEqual(res_big["status"], "INDEXED_LARGE")

        # Suppression fichier -> nettoyage cohérent de l'index
        os.remove(docx_path)
        stats4 = wd.scan_once()
        self.assertEqual(stats4["removed"], 1)
        self.assertEqual(len(self.rag.search("12/12/2026 contrat", top_k=1)), 0)

    def test_04_executive_briefing_epistemic_labels(self):
        with open(os.path.join(self.kb_dir, "audit_projet.md"), "w", encoding="utf-8") as f:
            f.write(
                "Le comité a validé le déploiement de la phase 2 pour le 15 janvier 2027.\n"
                "Risque critique identifié sur l'alimentation électrique du garage.\n"
                "Il faudra planifier une maintenance préventive avant l'hiver.\n"
            )
        self.rag.index_knowledge_directory(force=True)
        gen = ExecutiveBriefingGenerator(rag_engine=self.rag)
        rep = gen.generate("phase 2 garage maintenance")
        secs = rep["sections"]
        self.assertEqual(rep["status"], "OK")
        self.assertGreater(len(secs["decisions_identifiees"]["items"]), 0)
        self.assertGreater(len(secs["dates_importantes"]["items"]), 0)
        self.assertGreater(len(secs["risques"]["items"]), 0)
        self.assertGreater(len(secs["actions_a_entreprendre"]["items"]), 0)
        self.assertEqual(secs["risques"]["label"], "INTERPRETED")
        self.assertEqual(secs["actions_a_entreprendre"]["label"], "RECOMMENDED")
        self.assertIn("[Source: audit_projet.md", secs["sources_et_references"][0])

    def test_05_commitment_tracker_filtering_and_states(self):
        ct = CommitmentTracker(storage_file=os.path.join(self.tmp.name, "cmt.json"))
        # Hypothèse et citation doivent être rejetées
        bad_text = (
            'Si je gagne au loto, je vais acheter une île. '
            'Il a dit que "je t\'envoie le devis demain". '
            '> Je termine le rapport vendredi.'
        )
        res_bad = ct.analyze_text(bad_text, author="Alice", owner_id="alice_u1")
        self.assertEqual(len(res_bad), 0)

        # Engagement authentique
        good_text = "Je t'envoie le contrat signé demain matin avant midi."
        res_good = ct.analyze_text(good_text, author="Aboubakar", recipient="Client", owner_id="alice_u1")
        self.assertEqual(len(res_good), 1)
        cid = res_good[0]["commitment_id"]
        self.assertEqual(res_good[0]["status"], CommitmentState.REVIEW_REQUIRED.value)
        self.assertEqual(res_good[0]["deadline"], "demain")

        ct.transition(cid, CommitmentState.CONFIRMED, owner_id="alice_u1")
        item = ct.transition(cid, CommitmentState.SCHEDULED, owner_id="alice_u1")
        self.assertEqual(item["status"], CommitmentState.SCHEDULED.value)


if __name__ == "__main__":
    unittest.main()
