#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUITE MAÎTRESSE DE TESTS ALICE ULTIMATE — MISSION 008
Exécute toutes les suites de tests (Voix, IoT, Mémoire, Vision, Agents, Mobile, Sécurité, Intégration, Performance).
"""

import os
import sys
import time
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def run_all():
    print("=" * 80)
    print("ALICE MISSION 008 — SUITE COMPLÈTE DES 30 FONCTIONNALITÉS (TESTS & BENCHMARKS)")
    print("=" * 80)
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.dirname(__file__), top_level_dir=ROOT_DIR)
    runner = unittest.TextTestRunner(verbosity=2)
    t0 = time.time()
    result = runner.run(suite)
    dur = time.time() - t0
    print("\n" + "=" * 80)
    print(f"RÉSUMÉ ALICE ULTIMATE : {result.testsRun} tests exécutés en {dur:.2f}s")
    print(f"SUCCÈS : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"ÉCHECS : {len(result.failures)}")
    print(f"ERREURS : {len(result.errors)}")
    print("=" * 80)
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
