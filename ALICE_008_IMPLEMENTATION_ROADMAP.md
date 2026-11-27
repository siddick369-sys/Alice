# 🗺️ ALICE — FEUILLE DE ROUTE D'IMPLÉMENTATION PAR VAGUES (MISSION 008)

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Date :** 24 Novembre 2026  

---

## STRATÉGIE D'EXÉCUTION PAR LOTS (WAVES 0 → 6)

| Vague | Périmètre (Features & Socle) | Objectif d'Ingénierie | Porte de Validation (Tests) |
| :--- | :--- | :--- | :--- |
| **Wave 0** | Socle `alice_core/`, `feature_flags.py`, `audit.py`, arborescence `tests/alice_ultimate/` | Poser les invariants transverses de flags, journalisation sans secrets et contrats de résultats | Smoke tests Wave 0 + 132 tests baseline P0/P1/007 |
| **Wave 1** | **28** RBAC, **30** Observability, **01** Barge-In, **04** Whisper Mode, **05** Follow-Up Listen | Sécuriser les permissions multi-utilisateurs, l'observabilité temps réel et la robustesse conversationnelle audio | Suites `security/rbac`, `ops/`, `voice/` (interruptions, timeouts, isolation) |
| **Wave 2** | **11** Hybrid RAG (Dense+BM25+RRF), **12** Knowledge Graph, **13** Watchdog, **14** Executive Briefing, **15** Commitment Tracker | Transformer la mémoire documentaire en intelligence structurée, multi-format (.docx/.epub/.xlsx/.pdf/.md) et relationnelle | Suite `memory/` (précision/rappel, corruption, concurrence, prompt injection) |
| **Wave 3** | **06** Predictive Routines, **07** Eco-Manager, **08** Self-Healing IoT, **09** Presence Simulation, **10** Thermal Comfort | Doter Home Assistant de moteurs intelligents avec garde-fous physiques et mode dégradé vérifiable | Suite `iot/` (pannes HA, états inconnus, protection critiques, anti-oscillation) |
| **Wave 4** | **16** Visual Analysis Mobile, **17** Smart OCR Receipts (Tesseract+XLSX), **18** RTSP Sentinel, **19** Visual Memory, **20** Safety Zones | Ajouter la vision multimodale, l'extraction comptable vérifiée et l'analyse flux/zones avec respect vie privée | Suite `vision/` (Tesseract réel sur tickets, ROI géométrie, anti-faux-positifs, purge) |
| **Wave 5** | **24** Long-Running Jobs, **22** Agent Swarm, **23** Web Agent, **25** Webhook HMAC Gateway, **21** Proactive Briefings | Automatiser et déléguer de manière bornée, persistante, traçable et protégée contre SSRF/rejeu | Suite `agents/` & `integration/` (budgets, boucles, rejeu HMAC, reprise crash) |
| **Wave 6** | **29** Encrypted AES-256-GCM Vault, **02** Voice ID, **03** Acoustic Context, **26** Offline PWA, **27** Quick Actions | Clôturer les capacités biométriques chiffrées, le coffre-fort isolé et l'expérience mobile PWA hors-ligne | Suite `mobile/`, `security/vault`, `performance/` (benchmarks réels p50/p95) + Régression totale |
