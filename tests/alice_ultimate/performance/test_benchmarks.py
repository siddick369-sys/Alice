#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BENCHMARKS RÉELS DE PERFORMANCE — MISSION 008 (Section 6)
Mesure les latences réelles (médiane p50, p95, p99) sur le matériel hôte actuel
et enregistre les résultats bruts dans benchmark_results.json.
"""

import os
import sys
import json
import time
import math
import platform
import tempfile
import asyncio
import unittest
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Jarvis Final - SITE"))
if ROOT_SITE not in sys.path:
    sys.path.insert(0, ROOT_SITE)

from alice_core.ops.observability import OBSERVABILITY
from alice_core.voice.pipeline import BargeInAudioManager, AudioState
from alice_rag import AliceRAGEngine
from alice_orchestrator import CommandLifecycleManager, STATE_VALIDATING, STATE_ACCEPTED, STATE_RUNNING, STATE_SUCCEEDED
from alice_core.vision.ocr_receipts import SmartReceiptOCR
from alice_core.vision.video_sentinel import LocalLightweightDetector
from alice_core.mobile_sync.offline_sync import MobileSyncAndShortcutsManager
from alice_core.security.rbac import RBACPolicyEngine, Role


def _stats(samples_ms):
    s = sorted(samples_ms)
    n = len(s)
    def pct(p):
        idx = min(n - 1, max(0, int(math.ceil((p / 100.0) * n)) - 1))
        return round(s[idx], 3)
    return {
        "samples": n,
        "min_ms": round(s[0], 3),
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "max_ms": round(s[-1], 3),
    }


class TestPerformanceBenchmarks(unittest.TestCase):

    def test_01_run_and_record_all_benchmarks(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            sys_before = OBSERVABILITY.telemetry.sample()

            # 1. Latence Barge-In (N=30)
            barge_samples = []
            async def bench_barge():
                mgr = BargeInAudioManager()
                for _ in range(30):
                    mgr.transition(AudioState.IDLE)
                    mgr.begin_utterance()
                    res = await mgr.interrupt("bench")
                    barge_samples.append(res["latency_ms"])
            asyncio.run(bench_barge())

            # 2. Latence Indexation & Recherche Hybrid RAG (N=10 / N=30)
            kb = os.path.join(tmp.name, "kb")
            os.makedirs(kb, exist_ok=True)
            for i in range(10):
                with open(os.path.join(kb, f"doc_{i}.md"), "w", encoding="utf-8") as f:
                    f.write(f"# Document {i}\nServeur TLS port 8765 équipement SN-{1000+i}.\n" * 8)

            rag_idx_samples = []
            for _ in range(10):
                rag = AliceRAGEngine(knowledge_dir=kb, index_file=os.path.join(tmp.name, "idx.json"))
                t0 = time.perf_counter()
                rag.index_knowledge_directory(force=True)
                rag_idx_samples.append((time.perf_counter() - t0) * 1000.0)

            rag_search_samples = []
            for i in range(30):
                t0 = time.perf_counter()
                rag.search(f"serveur TLS SN-{1000 + (i % 10)}", top_k=3)
                rag_search_samples.append((time.perf_counter() - t0) * 1000.0)

            # 3. Latence Tesseract 5.5 OCR Receipt (N=5)
            rcpt_img = os.path.join(tmp.name, "rcpt.png")
            im = Image.new("RGB", (650, 320), (255, 255, 255))
            d = ImageDraw.Draw(im)
            font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28) if os.path.exists(r"C:\Windows\Fonts\arial.ttf") else ImageFont.load_default()
            d.text((30, 30), "MAGASIN TEST\nTotal HT: 100.00\nTVA: 20.00\nTotal TTC: 120.00 EUR", fill=(0, 0, 0), font=font)
            im.save(rcpt_img)
            ocr = SmartReceiptOCR(storage_file=os.path.join(tmp.name, "rcpt.json"))
            ocr_samples = []
            for _ in range(5):
                res_ocr = ocr.process_receipt(rcpt_img, "bench_u")
                ocr_samples.append(res_ocr["ocr_latency_ms"])

            # 4. Latence Détection Vidéo OpenCV HOG+Motion (N=20, 320x240)
            det = LocalLightweightDetector()
            frame = np.full((240, 320, 3), 80, dtype=np.uint8)
            vis_samples = []
            for i in range(20):
                f2 = frame.copy()
                f2[40:140, 60 + i:110 + i] = 220
                t0 = time.perf_counter()
                det.detect_frame(f2)
                vis_samples.append((time.perf_counter() - t0) * 1000.0)

            # 5. Latence Orchestrateur 9 états (N=30)
            orch_samples = []
            async def bench_orch():
                orch = CommandLifecycleManager(log_path=os.path.join(tmp.name, "orch.log"))
                for i in range(30):
                    t0 = time.perf_counter()
                    c = orch.register_command(f"cmd {i}", "s_bench")
                    await orch.transition(c.command_id, STATE_VALIDATING)
                    await orch.transition(c.command_id, STATE_ACCEPTED)
                    await orch.transition(c.command_id, STATE_RUNNING)
                    await orch.transition(c.command_id, STATE_SUCCEEDED, result="ok")
                    orch_samples.append((time.perf_counter() - t0) * 1000.0)
            asyncio.run(bench_orch())

            # 6. Latence Sync Mobile (N=30)
            rbac = RBACPolicyEngine()
            u = rbac.register_principal("sb", "u_bench", Role.OWNER)
            ms = MobileSyncAndShortcutsManager(state_file=os.path.join(tmp.name, "sync.json"))
            sync_samples = []
            for i in range(30):
                res_s = ms.apply_sync_batch(u, [{"op_id": f"b_{i}", "item_id": f"n_{i}", "item_type": "note", "title": "T", "content": "C", "base_version": 0}])
                sync_samples.append(res_s["sync_latency_ms"])

            sys_after = OBSERVABILITY.telemetry.sample()
            report = {
                "environment": {
                    "os": platform.platform(),
                    "python": platform.python_version(),
                    "cpu_cores": os.cpu_count(),
                    "ram_total_gb": sys_after["ram_total_gb"],
                    "ram_available_gb": sys_after["ram_available_gb"],
                    "cpu_percent_during_bench": sys_after["cpu_percent"],
                },
                "benchmarks": {
                    "barge_in_abort": _stats(barge_samples),
                    "rag_index_10_docs": _stats(rag_idx_samples),
                    "rag_hybrid_search": _stats(rag_search_samples),
                    "ocr_tesseract_receipt": _stats(ocr_samples),
                    "video_sentinel_frame_320x240": _stats(vis_samples),
                    "orchestrator_full_lifecycle": _stats(orch_samples),
                    "mobile_offline_sync_op": _stats(sync_samples),
                },
            }
            out_file = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.assertTrue(os.path.exists(out_file))
            self.assertLess(report["benchmarks"]["barge_in_abort"]["p95_ms"], 50.0)
            self.assertLess(report["benchmarks"]["rag_hybrid_search"]["p95_ms"], 200.0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
