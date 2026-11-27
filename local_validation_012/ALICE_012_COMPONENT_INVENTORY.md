# ALICE_012_COMPONENT_INVENTORY.md
## Inventaire Complet des Composants, Modules et Points d'Entrée ALICE

**Mission ID :** `ALICE-LOCAL-END-TO-END-VALIDATION-012`  
**Date :** 2026-11-26  
**Répertoire source :** `Jarvis Final - SITE/`  

---

### 1. Architecture Générale & Points d'Entrée

ALICE repose sur une architecture hybride Python / TypeScript / Web Standard :
1. **Point d'entrée principal Backend :** `Jarvis Final - SITE/main2.py`
   - Démarre le serveur HTTP Mobile (`start_mobile_http_server` sur port `8080`).
   - Démarre le serveur WebSocket sécurisé (`start_ws` sur port `8765`).
   - Démarre l'orchestrateur d'IA / Voice (`start_ia`).
   - Démarre la détection Vision OCR en tâche de fond (`vision_ocr.JarvisVision`).
   - Lance le dev server Vite Frontend (`npm run dev` sur port `5173`).
2. **Point d'entrée Frontend Desktop :** `Jarvis Final - SITE/frontend/` (Vite, TypeScript, Three.js)
   - Port par défaut : `http://localhost:5173`
   - Build de production : `dist/index.html`
3. **Point d'entrée Client Mobile PWA :** `Jarvis Final - SITE/mobile/`
   - Port par défaut : `http://localhost:8080/index.html` (ou `/mobile/index.html`)
   - Fichiers clés : `index.html`, `app.js`, `sw.js`, `manifest.json`, `style.css`

---

### 2. Inventaire Détaillé des Sous-Systèmes (`alice_core/`)

| Sous-système | Module Python | Description Fonctionnelle | Statut Local |
|---|---|---|---|
| **Security & Auth** | `alice_core/security/rbac.py` | Contrôle d'accès à base de rôles (GUEST, MEMBER, ADMIN), principe fail-closed, vérification granulaire par action. | Prêt / Opérationnel |
| **Security & Auth** | `alice_core/security/vault.py` | Gestionnaire de coffre-fort de secrets et clés chiffrées localement. | Prêt / Opérationnel |
| **Security & Auth** | `alice_core/security/audit.py` | Journal d'audit de sécurité inviolable (logs d'accès, violations RBAC). | Prêt / Opérationnel |
| **API & Bridge** | `alice_core/api_bridge.py` | Routeur centralisant la réception et l'orchestration des actions des 30 fonctionnalités. | Prêt / Opérationnel |
| **Automation** | `alice_core/automation/agent_swarm.py` | Décomposition de requêtes et délégation d'agents autonomes. | Prêt / Opérationnel |
| **Automation** | `alice_core/automation/web_agent.py` | Agent Web protégé par SSRF Guard avec isolation DNS et filtrage des IP privées. | Prêt / Opérationnel |
| **Automation** | `alice_core/automation/daily_briefing.py` | Synthèse quotidienne prompte et planification d'agenda. | Prêt / Opérationnel |
| **Automation** | `alice_core/automation/jobs.py` | Gestionnaire de tâches asynchrones récurrentes et persistantes. | Prêt / Opérationnel |
| **Automation** | `alice_core/automation/webhooks.py` | Réception et validation de signaux webhooks entrants. | Prêt / Opérationnel |
| **Memory & Context** | `alice_core/memory/knowledge_graph.py` | Graphe de connaissances pour relier entités, préférences et contextes. | Prêt / Opérationnel |
| **Memory & Context** | `alice_core/memory/commitments.py` | Suivi et alertes des engagements et promesses pris par l'utilisateur. | Prêt / Opérationnel |
| **Memory & Context** | `alice_core/memory/watchdog.py` | Surveillance du hot-folder pour indexation documentaire automatique. | Prêt / Opérationnel |
| **Vision Intelligence** | `alice_core/vision/analyzer.py` | Analyse visuelle multimodale et OCR contextuel. | Prêt (avec Tesseract local) |
| **Vision Intelligence** | `alice_core/vision/ocr_receipts.py` | Détection et parsing de reçus et factures. | Prêt |
| **Vision Intelligence** | `alice_core/vision/safety_zones.py` | Détection de zones de sécurité et intrusions par flux caméra. | Prêt |
| **Vision Intelligence** | `alice_core/vision/video_sentinel.py` | Sentinelle vidéo analysant les anomalies visuelles. | Dépendance RTSP externe |
| **IoT & Domotique** | `alice_core/iot/ha_client.py` | Client d'intégration Home Assistant (API REST). | Prêt (émulé si HA hors ligne) |
| **IoT & Domotique** | `alice_core/iot/eco_manager.py` | Gestionnaire d'efficacité énergétique et délestage. | Prêt |
| **IoT & Domotique** | `alice_core/iot/presence.py` | Inférence de présence multi-capteurs. | Prêt |
| **IoT & Domotique** | `alice_core/iot/self_healing.py` | Mécanismes d'auto-réparation et reconnexion des nœuds IoT. | Prêt |
| **Voice & Speech** | `alice_core/voice/pipeline.py` | Pipeline de transcription et synthèse vocale. | Prêt |
| **Voice & Speech** | `alice_core/voice/voice_id.py` | Empreinte biométrique vocale pour authentification du locuteur. | Prêt (clé persistante) |
| **Voice & Speech** | `alice_core/voice/whisper_mode.py` | Mode chuchotement adaptatif selon l'énergie audio. | Prêt |
| **Observability** | `alice_core/ops/observability.py` | Métriques runtime, télémétrie, état des files de jobs et du RAG. | Prêt / Opérationnel |
| **RAG & Docs** | `Jarvis Final - SITE/alice_rag.py` | Moteur RAG local avec protection contre les bombes ZIP et path traversal. | Prêt / Opérationnel |
| **Web Guard** | `Jarvis Final - SITE/alice_web_guard.py` | Filtre anti-SSRF strict avec épinglage DNS (`pin_and_validate_url`). | Prêt / Opérationnel |

---

### 3. Matrice de Connectivité Réseau et Protocoles

| Protocole | Port par Défaut | Bind Address | Gestionnaire | Rôle |
|---|---|---|---|---|
| **HTTP / REST** | `8080` | `0.0.0.0` / `127.0.0.1` | `main2.py:MobileRequestHandler` | Interface Mobile PWA, API Pairing, API Synchronisation |
| **WebSocket** | `8765` | `0.0.0.0` / `127.0.0.1` | `main2.py:ws_handler` | Flux temps réel, messages chat, statut assistant, audio |
| **HTTP (Vite)** | `5173` | `localhost` | `vite dev` | Interface Desktop 3D WebGL (Three.js) |
