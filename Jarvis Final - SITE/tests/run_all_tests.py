#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUITE MAÎTRESSE DE TESTS FONCTIONNELS ET DE NON-RÉGRESSION — MISSION 007
Exécute l'intégralité des tests unitaires, d'intégration, de sécurité et la suite P0.
"""

import sys
import os
import unittest
import time

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_DIR)

def run_suite():
    print("=" * 80)
    print("ALICE MISSION 007 : SUITE DE QUALITÉ LOGICIELLE & TESTS FONCTIONNELS")
    print("=" * 80)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import et ajout des suites
    import test_command_lifecycle
    import test_rag_engine
    import test_web_guard
    import test_google_adapter
    
    suite.addTests(loader.loadTestsFromModule(test_command_lifecycle))
    suite.addTests(loader.loadTestsFromModule(test_rag_engine))
    suite.addTests(loader.loadTestsFromModule(test_web_guard))
    suite.addTests(loader.loadTestsFromModule(test_google_adapter))
    
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time
    
    print("\n" + "=" * 80)
    print(f"RÉSUMÉ MISSION 007 : {result.testsRun} tests exécutés en {duration:.2f}s")
    print(f"SUCCÈS : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"ÉCHECS : {len(result.failures)}")
    print(f"ERREURS : {len(result.errors)}")
    print("=" * 80)
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
