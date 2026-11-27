"""
Exécuteur global et exhaustif de toutes les suites de tests du projet (Mission 014).
Charge directement chaque module de test de manière robuste.
"""
import os
import sys
import time
import unittest
import importlib.util

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(ROOT_DIR, "Jarvis Final - SITE")
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
SITE_TESTS_DIR = os.path.join(SOURCE_DIR, "tests")

# Configuration des chemins système
for p in [ROOT_DIR, SOURCE_DIR, TESTS_DIR, SITE_TESTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

TEST_FILES = [
    # 1. Sécurité & Remédiations P1
    os.path.join(TESTS_DIR, "security", "test_p1_production_exposure_006.py"),
    os.path.join(TESTS_DIR, "security", "test_p1_remediation_007_real_sockets.py"),
    os.path.join(TESTS_DIR, "security", "test_p1_remediation_009.py"),
    os.path.join(TESTS_DIR, "security", "test_p1_remediation_010_adversarial.py"),
    # 2. ALICE Ultimate Suites (Waves)
    os.path.join(TESTS_DIR, "alice_ultimate", "agents", "test_wave5_automation.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "integration", "test_e2e_api_ws_bridge.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "integration", "test_wave1_observability.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "iot", "test_wave3_iot.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "memory", "test_wave2_memory.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "mobile", "test_wave6_mobile_sync.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "performance", "test_benchmarks.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "security", "test_wave0_foundation.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "security", "test_wave1_rbac.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "security", "test_wave6_vault.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "vision", "test_wave4_vision.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "voice", "test_wave1_voice.py"),
    os.path.join(TESTS_DIR, "alice_ultimate", "voice", "test_wave6_biometrics_mood.py"),
    # 3. Mission 007 Site Tests
    os.path.join(SITE_TESTS_DIR, "test_command_lifecycle.py"),
    os.path.join(SITE_TESTS_DIR, "test_rag_engine.py"),
    os.path.join(SITE_TESTS_DIR, "test_web_guard.py"),
    os.path.join(SITE_TESTS_DIR, "test_google_adapter.py"),
    # 4. Mission 014 Remédiations
    os.path.join(TESTS_DIR, "test_remediation_014.py"),
    os.path.join(TESTS_DIR, "test_multimodal_014.py"),
]

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for file_path in TEST_FILES:
    if os.path.exists(file_path):
        mod_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            file_suite = loader.loadTestsFromModule(mod)
            suite.addTests(file_suite)
        except Exception as e:
            print(f"[ERREUR CHARGEMENT] {file_path} : {e}")

print("=" * 80)
print(f"[TEST RUNNER 014] Démarrage de l'exécution globale ({suite.countTestCases()} tests découverts)")
print("=" * 80)

runner = unittest.TextTestRunner(verbosity=2)
start_time = time.time()
result = runner.run(suite)
duration = time.time() - start_time

print("\n" + "=" * 80)
print(f"[TEST RUNNER 014] Exécution terminée en {duration:.2f}s")
print(f"Total tests    : {result.testsRun}")
print(f"Succès (PASS)  : {result.testsRun - len(result.failures) - len(result.errors)}")
print(f"Échecs (FAIL)  : {len(result.failures)}")
print(f"Erreurs (ERR)  : {len(result.errors)}")
print(f"Ignorés (SKIP) : {len(result.skipped)}")
print("=" * 80)

sys.exit(0 if result.wasSuccessful() else 1)
