# ⚡ ALICE — BENCHMARKS RÉELS DE PERFORMANCE (MISSION 008)

**Mission ID :** `ALICE-ULTIMATE-INTELLIGENCE-AND-AUTONOMY-IMPLEMENTATION-008`  
**Date :** 25 Novembre 2026  
**Source brute vérifiable :** `tests/alice_ultimate/performance/benchmark_results.json`  

---

## 1. ENVIRONNEMENT DE MESURE RÉEL

- **OS :** Windows 10 (`Windows-10-10.0.26200-SP0`)
- **Python :** `3.11.8`
- **Processeur :** 8 cœurs logiques (charge mesurée pendant benchmark : `35.4%`)
- **Mémoire :** `15.78 Go` total (`4.09 Go` disponibles pendant le run)

---

## 2. RÉSULTATS MESURÉS (MÉDIANE p50, p95, p99)

| Opération mesurée | Échantillons (N) | Min (ms) | Médiane p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Interruption Barge-In (`BargeInAudioManager.interrupt`)** | 30 | 0.004 | **0.004** | **0.009** | 0.011 | 0.011 |
| **Indexation Hybrid RAG (10 documents Markdown)** | 10 | 20.829 | **24.510** | **38.131** | 38.131 | 38.131 |
| **Recherche Hybrid RAG (BM25 + Dense NumPy + RRF)** | 30 | 1.287 | **1.922** | **2.805** | 2.947 | 2.947 |
| **OCR Ticket réel (Tesseract 5.5 + OpenCV + Parser)** | 5 | 360.510 | **387.130** | **405.880** | 405.880 | 405.880 |
| **Détection Vidéo Sentinelle (OpenCV HOG+Motion 320x240)** | 20 | 10.727 | **13.336** | **17.329** | 18.394 | 18.394 |
| **Cycle de vie complet Orchestrateur (5 transitions + log)** | 30 | 2.454 | **2.750** | **3.882** | 3.950 | 3.950 |
| **Synchronisation Mobile Offline (1 opération idempotente)** | 30 | 1.420 | **2.090** | **3.340** | 3.350 | 3.350 |

---

## 3. ANALYSE DES SLO ET LATENCES NON MESURÉES EN LOCAL

- Les latences **IA cloud** (`Gemini`, `Groq`) et **TTS cloud** (`Edge-TTS`) dépendent des API tierces et du réseau ; elles sont mesurées en production par `OBSERVABILITY.record_latency("ia_latency_ms" / "tts_latency_ms")` mais non simulées comme locales.
- Sur le matériel actuel, la recherche hybride RAG (`p95 = 2.81 ms`), le cycle complet de l'orchestrateur (`p95 = 3.88 ms`) et l'OCR Tesseract réel (`p95 = 405.88 ms`) respectent largement des SLO interactifs réalistes.
