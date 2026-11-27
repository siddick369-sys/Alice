/**
 * A.L.I.C.E — Interface Mobile Multimodale & PWA Hors-Ligne (Mission 008)
 *
 * Sécurité P1 stricte :
 * - Manipulation DOM sécurisée via createElement / textContent uniquement (zéro injection HTML/JS)
 * - Aucun jeton d'authentification stocké dans localStorage
 * - Cookies sécurisés HttpOnly + X-CSRF-Token pour les mutations REST
 */

/**
 * Construit l'URL WebSocket de manière sûre et cohérente avec le routage proxy (FINDING-02).
 * - En HTTPS (production / reverse proxy) : wss://<host><basePath>/ws (jamais :8765 direct)
 * - En HTTP développement local uniquement : ws://<hostname>:<devWsPort>
 * - Refuse tout fallback silencieux vers ws:// en production ou si la configuration est absente.
 */
function buildWebSocketUrl(locationObj, configObj = {}) {
  if (!locationObj || !locationObj.protocol || !locationObj.hostname) {
    throw new Error("Configuration de localisation absente pour la construction de l'URL WebSocket.");
  }
  const protocol = String(locationObj.protocol).toLowerCase();
  const hostname = String(locationObj.hostname).trim();
  const host = String(locationObj.host || hostname).trim();
  const env = String((configObj && configObj.env) || "").toLowerCase();
  const isHttps = protocol === "https:";

  if (env === "production" && !isHttps) {
    throw new Error("Connexion WebSocket non chiffrée (ws://) interdite en production.");
  }
  if (protocol !== "https:" && protocol !== "http:") {
    throw new Error(`Protocole HTTP(S) invalide pour WebSocket : ${protocol}`);
  }

  if (isHttps) {
    let basePath = String((configObj && configObj.basePath) || locationObj.pathname || "/");
    basePath = basePath.replace(/\/[^/]*\.[^/]+$/, "");
    basePath = basePath.replace(/\/+$/, "");
    if (basePath === "/") basePath = "";
    const wsPath = `${basePath}/ws`.replace(/\/{2,}/g, "/");
    const safeHost = host.replace(/:8765$/, "");
    return `wss://${safeHost}${wsPath}`;
  }

  const devWsPort = Number((configObj && configObj.devWsPort) || 8765);
  return `ws://${hostname}:${devWsPort}`;
}

let WS_URL = null;
try {
  const aliceCfg = (typeof window !== "undefined" && window.ALICE_CONFIG) ? window.ALICE_CONFIG : {};
  WS_URL = buildWebSocketUrl(window.location, aliceCfg);
} catch (err) {
  console.error("[WS CONFIG ERROR]", err.message);
  WS_URL = null;
}
const RECONNECT_DELAY_MS = 2500;
const SPEECH_LANG = "fr-FR";

// ── DOM Refs ────────────────────────────────────────────────────────────────
const badgeEl       = document.getElementById("connection-badge");
const badgeLabelEl  = document.getElementById("connection-label");
const roleBadgeEl   = document.getElementById("role-badge");
const statusEl      = document.getElementById("status-text");
const userTextEl    = document.getElementById("user-text");
const jarvisTextEl  = document.getElementById("jarvis-text");
const micBtn        = document.getElementById("mic-btn");
const micIcon       = micBtn.querySelector(".mic-icon");
const stopIcon      = micBtn.querySelector(".stop-icon");
const micLabelEl    = document.getElementById("mic-label");
const stopJarvisBtn = document.getElementById("stop-jarvis-btn");

// ── DOM Refs Appairage & Confirmations ──────────────────────────────────────
const pairingModalEl      = document.getElementById("pairing-modal");
const pairingInputEl      = document.getElementById("pairing-code-input");
const pairingSubmitBtn    = document.getElementById("pairing-submit-btn");
const pairingErrorEl      = document.getElementById("pairing-error");
const commandStatusCardEl = document.getElementById("command-status-card");
const commandStatePillEl  = document.getElementById("command-state-pill");
const commandActionNameEl = document.getElementById("command-action-name");
const commandStatusDetailEl = document.getElementById("command-status-detail");
const actionConfirmModalEl= document.getElementById("action-confirm-modal");
const confirmModalPromptEl= document.getElementById("confirm-modal-prompt");
const confirmActionBtn    = document.getElementById("confirm-action-btn");
const cancelActionBtn     = document.getElementById("cancel-action-btn");

// ── DOM Refs Mission 008 (Whisper, Follow-Up, Quick Actions, Vision, Notes, Ops)
const whisperToggleBtn  = document.getElementById("whisper-toggle-btn");
const cameraBtn         = document.getElementById("camera-btn");
const cameraFileInput   = document.getElementById("camera-file-input");
const visionModalEl     = document.getElementById("vision-preview-modal");
const visionPreviewImg  = document.getElementById("vision-preview-img");
const visionQuestionEl  = document.getElementById("vision-question-input");
const visionReceiptEl   = document.getElementById("vision-receipt-mode");
const visionEphemeralEl = document.getElementById("vision-ephemeral");
const visionResultEl    = document.getElementById("vision-result-box");
const visionSendBtn     = document.getElementById("vision-send-btn");
const visionCloseBtn    = document.getElementById("vision-close-btn");
const followupPillEl    = document.getElementById("followup-pill");
const followupLabelEl   = document.getElementById("followup-label");
const followupCancelBtn = document.getElementById("followup-cancel-btn");
const quickActionsDock  = document.getElementById("quick-actions-dock");
const notesDrawerBtn    = document.getElementById("notes-drawer-btn");
const notesDrawerEl     = document.getElementById("notes-drawer");
const notesCloseBtn     = document.getElementById("notes-close-btn");
const notesSyncBtn      = document.getElementById("notes-sync-btn");
const noteTitleInput    = document.getElementById("note-title-input");
const noteContentInput  = document.getElementById("note-content-input");
const noteSaveBtn       = document.getElementById("note-save-btn");
const notesListEl       = document.getElementById("notes-list");
const syncStatusTextEl  = document.getElementById("sync-status-text");
const opsDrawerBtn      = document.getElementById("ops-drawer-btn");
const opsDrawerEl       = document.getElementById("ops-drawer");
const opsCloseBtn       = document.getElementById("ops-close-btn");
const opsRefreshBtn     = document.getElementById("ops-refresh-btn");
const opsMetricsBoxEl   = document.getElementById("ops-metrics-box");
const flagsListEl       = document.getElementById("flags-list");

let pendingConfirmationCmdId = null;
let pendingConfirmationToken = null;
let statusCardTimer          = null;
let lastCommandTime          = 0;
let whisperManualOn          = false;
let stagedImageBase64        = null;

// ── Enregistrement PWA Service Worker (Feature 26) ──────────────────────────
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

// ── Helper CSRF Cookie ──────────────────────────────────────────────────────
function getCsrfToken() {
  const m = document.cookie.match(/(?:^|;\s*)alice_csrf=([^;]+)/);
  if (m) return decodeURIComponent(m[1]);
  return sessionStorage.getItem("jarvis_csrf_token") || "";
}

async function apiFetch(url, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  if (options.method && options.method !== "GET") {
    headers["X-CSRF-Token"] = getCsrfToken();
  }
  const resp = await fetch(url, Object.assign({}, options, { headers, credentials: "same-origin" }));
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, data };
}

// ── Contexte d'identité multi-compte & IndexedDB isolé (F01 / Feature 26) ────
const LEGACY_IDB_NAME = "aliceOfflineDB";
const IDB_VER = 2;
let activeAccountId = sessionStorage.getItem("jarvis_account_id") || "";
let accountEpoch = 0;
let accountTransitionLock = false;

function getScopedDBName(ownerId) {
  const safeOwner = String(ownerId || "").replace(/[^a-zA-Z0-9_-]/g, "_");
  return safeOwner ? `aliceOfflineDB_${safeOwner}` : LEGACY_IDB_NAME;
}

function openOfflineDB(ownerId = activeAccountId) {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return reject(new Error("IndexedDB indisponible"));
    if (!ownerId) return reject(new Error("Identité compte absente : accès IndexedDB refusé."));
    const dbName = getScopedDBName(ownerId);
    const req = indexedDB.open(dbName, IDB_VER);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("notes")) {
        const ns = db.createObjectStore("notes", { keyPath: "item_id" });
        ns.createIndex("by_owner", "owner_id", { unique: false });
      }
      if (!db.objectStoreNames.contains("pending_ops")) {
        const ps = db.createObjectStore("pending_ops", { keyPath: "op_id" });
        ps.createIndex("by_owner", "owner_id", { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(storeName, obj, expectedOwner = activeAccountId, expectedEpoch = accountEpoch) {
  if (accountTransitionLock || !expectedOwner || expectedEpoch !== accountEpoch) {
    throw new Error("Opération IndexedDB annulée : transition de compte ou session invalide.");
  }
  const db = await openOfflineDB(expectedOwner);
  const scopedObj = { ...obj, owner_id: expectedOwner };
  return new Promise((resolve, reject) => {
    if (expectedEpoch !== accountEpoch || activeAccountId !== expectedOwner) {
      return reject(new Error("Callback tardif rejeté après changement de compte."));
    }
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).put(scopedObj);
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}

async function idbGetAll(storeName, expectedOwner = activeAccountId, expectedEpoch = accountEpoch) {
  if (accountTransitionLock || !expectedOwner || expectedEpoch !== accountEpoch) {
    return [];
  }
  const db = await openOfflineDB(expectedOwner);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = () => {
      if (expectedEpoch !== accountEpoch || activeAccountId !== expectedOwner) {
        return resolve([]);
      }
      const rows = (req.result || []).filter((r) => r && r.owner_id === expectedOwner);
      resolve(rows);
    };
    req.onerror = () => reject(req.error);
  });
}

async function idbClear(storeName, ownerId = activeAccountId) {
  if (!ownerId) return true;
  const db = await openOfflineDB(ownerId);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).clear();
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}

async function purgeOfflineAccountData(prevOwnerId) {
  try {
    if (prevOwnerId) {
      await idbClear("notes", prevOwnerId).catch(() => {});
      await idbClear("pending_ops", prevOwnerId).catch(() => {});
    }
    if (window.indexedDB && typeof indexedDB.deleteDatabase === "function") {
      try { indexedDB.deleteDatabase(LEGACY_IDB_NAME); } catch (_) {}
      if (prevOwnerId) {
        try { indexedDB.deleteDatabase(getScopedDBName(prevOwnerId)); } catch (_) {}
      }
    }
  } catch (_) {}
}

async function transitionAccountContext(newOwnerId) {
  accountTransitionLock = true;
  accountEpoch += 1;
  const prevOwner = activeAccountId;
  try {
    if (prevOwner && prevOwner !== newOwnerId) {
      await purgeOfflineAccountData(prevOwner);
    }
    if (!newOwnerId && prevOwner) {
      await purgeOfflineAccountData(prevOwner);
    }
    activeAccountId = newOwnerId || "";
    if (activeAccountId) {
      sessionStorage.setItem("jarvis_account_id", activeAccountId);
    } else {
      sessionStorage.removeItem("jarvis_account_id");
    }
    if (notesListEl) notesListEl.replaceChildren();
  } finally {
    accountTransitionLock = false;
  }
}

// ── ORB 3D ──────────────────────────────────────────────────────────────────
let orb = null;
if (typeof createOrb === "function") {
  const canvas = document.getElementById("orb-canvas");
  if (canvas) {
    try {
      orb = createOrb(canvas);
    } catch (err) {
      console.warn("[ORB] Erreur initialisation Orb:", err);
    }
  }
}

// ── HTTPS Warning ───────────────────────────────────────────────────────────
if (window.location.protocol !== "https:" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
  const warning = document.getElementById("https-warning");
  if (warning) {
    warning.style.display = "block";
    const closeBtn = document.getElementById("close-warning-btn");
    if (closeBtn) closeBtn.addEventListener("click", () => { warning.style.display = "none"; });
  }
}

// ── État de l'application ───────────────────────────────────────────────────
let currentState = "idle";
let ws = null;
let isListening = false;
let reconnectTimer = null;

const STATE_LABELS = {
  idle:      "en attente",
  listening: "je vous écoute...",
  thinking:  "en réflexion...",
  speaking:  "alice répond...",
};

function applyState(state) {
  document.body.classList.remove("state-idle", "state-listening", "state-thinking", "state-speaking");
  document.body.classList.add(`state-${state}`);
  currentState = state;
  statusEl.textContent = STATE_LABELS[state] || state;
  stopJarvisBtn.style.display = (state === "speaking") ? "flex" : "none";

  if (state === "listening") {
    micIcon.style.display = "none";
    stopIcon.style.display = "block";
    micLabelEl.textContent = "APPUYER POUR ARRÊTER";
  } else {
    micIcon.style.display = "block";
    stopIcon.style.display = "none";
    micLabelEl.textContent = "APPUYER POUR PARLER";
  }
  if (orb) orb.setState(state);
}
applyState("idle");

let currentAudio = null;
let fakeVolumeInterval = null;

function stopPlaybackNow() {
  window.speechSynthesis.cancel();
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (fakeVolumeInterval) {
    clearInterval(fakeVolumeInterval);
    fakeVolumeInterval = null;
  }
  if (orb) orb.setVolume(0);
}

// Barge-In temps réel (Feature 01)
stopJarvisBtn.addEventListener("click", () => {
  stopPlaybackNow();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "barge_in" }));
  }
  applyState("idle");
});

function setConnected(ok) {
  badgeEl.classList.toggle("connected", ok);
  badgeEl.classList.toggle("disconnected", !ok);
  badgeLabelEl.textContent = ok ? "connecté" : "hors-ligne";
  if (ok) syncOfflineNotes();
}
setConnected(false);

// ── Appairage Sécurisé (SEC-04) ──────────────────────────────────────────────
function showPairingModal(errorMessage = "") {
  if (!pairingModalEl) return;
  pairingModalEl.style.display = "flex";
  if (pairingInputEl) { pairingInputEl.value = ""; pairingInputEl.focus(); }
  if (pairingErrorEl) {
    pairingErrorEl.textContent = errorMessage || "";
    pairingErrorEl.style.display = errorMessage ? "block" : "none";
  }
}

function hidePairingModal() {
  if (pairingModalEl) pairingModalEl.style.display = "none";
}

async function submitPairingCode() {
  const code = pairingInputEl ? pairingInputEl.value.trim() : "";
  if (!code || code.length !== 6) {
    if (pairingErrorEl) {
      pairingErrorEl.textContent = "Le code doit comporter 6 chiffres.";
      pairingErrorEl.style.display = "block";
    }
    return;
  }
  try {
    if (pairingSubmitBtn) pairingSubmitBtn.disabled = true;
    const resp = await fetch("/api/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code })
    });
    const result = await resp.json();
    if (resp.ok && result.success && result.session_id) {
      localStorage.removeItem("jarvis_session_token");
      localStorage.removeItem("jarvis_session_id");
      sessionStorage.setItem("jarvis_session_id", result.session_id);
      if (result.csrf_token) sessionStorage.setItem("jarvis_csrf_token", result.csrf_token);
      const resolvedOwner = result.user_id || result.session_id;
      await transitionAccountContext(resolvedOwner);
      hidePairingModal();
      connectWS();
    } else if (pairingErrorEl) {
      pairingErrorEl.textContent = result.error || "Code invalide ou expiré.";
      pairingErrorEl.style.display = "block";
    }
  } catch (err) {
    if (pairingErrorEl) {
      pairingErrorEl.textContent = "Erreur réseau lors de l'appairage.";
      pairingErrorEl.style.display = "block";
    }
  } finally {
    if (pairingSubmitBtn) pairingSubmitBtn.disabled = false;
  }
}
if (pairingSubmitBtn) pairingSubmitBtn.addEventListener("click", submitPairingCode);
if (pairingInputEl) pairingInputEl.addEventListener("keydown", (e) => { if (e.key === "Enter") submitPairingCode(); });

// ── WebSocket ───────────────────────────────────────────────────────────────
function connectWS() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (!WS_URL) {
    setConnected(false);
    showPairingModal("Configuration WebSocket sécurisée invalide (HTTPS requis en production).");
    return;
  }
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    console.log("[WS] Connecté à", WS_URL);
  });

  ws.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "auth_ok") {
        setConnected(true);
        hidePairingModal();
        loadUserContextAndQuickActions();
        return;
      }
      if (data.type === "command_lifecycle") {
        handleCommandLifecycle(data);
        return;
      }
      if (data.type === "barge_in_stop" || data.action === "barge_in_stop") {
        stopPlaybackNow();
        applyState("listening");
        return;
      }
      if (data.type === "followup_state") {
        handleFollowUpState(data);
        return;
      }
      if (data.type === "job_notification") {
        jarvisTextEl.textContent = `[Tâche ${data.job_type}] Statut : ${data.status}`;
        return;
      }
      if (data.type === "auth_error") {
        sessionStorage.removeItem("jarvis_session_id");
        sessionStorage.removeItem("jarvis_csrf_token");
        transitionAccountContext("");
        setConnected(false);
        showPairingModal("Session invalide ou expirée. Veuillez saisir un nouveau code.");
        try { ws.close(4001, "Auth error"); } catch (e) {}
        return;
      }
      if (data.action === "set_state" && data.state) {
        if (data.state === "listening" || data.state === "active") return;
        if (data.state === "idle" && isListening) return;
        if (data.state !== "speaking") applyState(data.state);
      }
      if (data.action === "jarvis_audio" && data.audio_b64) {
        afficherReponseJarvis(data.text);
        jouerAudioBase64(data.audio_b64);
      } else if (data.action === "jarvis_response" && data.text) {
        afficherReponseJarvis(data.text);
        parleSynthese(data.text);
      }
    } catch (e) {
      console.error("[WS] Erreur parsing :", e);
    }
  });

  ws.addEventListener("close", (event) => {
    setConnected(false);
    applyState("idle");
    if (event.code === 4001 || event.code === 4003) {
      sessionStorage.removeItem("jarvis_session_id");
      sessionStorage.removeItem("jarvis_csrf_token");
      transitionAccountContext("");
      showPairingModal("Connexion refusée par le serveur. Veuillez réappairer l'appareil.");
      return;
    }
    scheduleReconnect();
  });

  ws.addEventListener("error", () => setConnected(false));
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => { reconnectTimer = null; connectWS(); }, RECONNECT_DELAY_MS);
}

function sendCommand(text) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  const now = Date.now();
  if (now - lastCommandTime < 800) return false;
  lastCommandTime = now;
  const cmdId = "cmd_" + now + "_" + Math.random().toString(36).slice(2, 8);
  ws.send(JSON.stringify({ type: "mobile_command", text, command_id: cmdId }));
  return true;
}

// ── Follow-Up Listen (Feature 05) ───────────────────────────────────────────
function handleFollowUpState(data) {
  if (!followupPillEl) return;
  if (data.active) {
    followupPillEl.style.display = "flex";
    if (followupLabelEl) followupLabelEl.textContent = `Écoute continue (${data.window_seconds || 5}s)...`;
  } else {
    followupPillEl.style.display = "none";
  }
}
if (followupCancelBtn) {
  followupCancelBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "followup_cancel" }));
    }
    if (followupPillEl) followupPillEl.style.display = "none";
  });
}

// ── Whisper Mode Toggle (Feature 04) ────────────────────────────────────────
if (whisperToggleBtn) {
  whisperToggleBtn.addEventListener("click", () => {
    whisperManualOn = !whisperManualOn;
    whisperToggleBtn.classList.toggle("active", whisperManualOn);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "whisper_mode", mode: whisperManualOn ? "manual_on" : "auto" }));
    }
  });
}

// ── Quick Actions & Profil RBAC (Features 27 & 28) ──────────────────────────
async function loadUserContextAndQuickActions() {
  const me = await apiFetch("/api/me");
  if (me.ok && roleBadgeEl) {
    roleBadgeEl.textContent = me.data.role || "";
  }
  const qa = await apiFetch("/api/quick_actions");
  if (qa.ok && Array.isArray(qa.data.actions) && quickActionsDock) {
    quickActionsDock.replaceChildren();
    qa.data.actions.forEach((act) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "qa-chip" + (act.allowed === false ? " qa-disabled" : "");
      btn.textContent = `${act.icon || "⚡"} ${act.label}`;
      btn.disabled = (act.allowed === false);
      btn.addEventListener("click", () => {
        if (act.id === "qa_quick_note") {
          openNotesDrawer();
        } else {
          afficherTexteUtilisateur(act.command);
          applyState("thinking");
          sendCommand(act.command);
        }
      });
      quickActionsDock.appendChild(btn);
    });
  }
}

// ── Vision Capture -> Prévisualisation -> Confirmation -> OCR (Features 16/17)
if (cameraBtn && cameraFileInput) {
  cameraBtn.addEventListener("click", () => cameraFileInput.click());
  cameraFileInput.addEventListener("change", () => {
    const file = cameraFileInput.files && cameraFileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result || "");
      stagedImageBase64 = dataUrl.split(",")[1] || "";
      if (visionPreviewImg) visionPreviewImg.src = dataUrl;
      if (visionResultEl) visionResultEl.textContent = "";
      if (visionModalEl) visionModalEl.style.display = "flex";
    };
    reader.readAsDataURL(file);
    cameraFileInput.value = "";
  });
}
if (visionCloseBtn) {
  visionCloseBtn.addEventListener("click", () => {
    stagedImageBase64 = null;
    if (visionModalEl) visionModalEl.style.display = "none";
  });
}
if (visionSendBtn) {
  visionSendBtn.addEventListener("click", async () => {
    if (!stagedImageBase64) return;
    visionSendBtn.disabled = true;
    visionResultEl.textContent = "Traitement en cours...";
    try {
      if (visionReceiptEl && visionReceiptEl.checked) {
        const res = await apiFetch("/api/vision/receipt", {
          method: "POST",
          body: JSON.stringify({ image_b64: stagedImageBase64, confirmed: true })
        });
        if (res.ok) {
          const d = res.data;
          visionResultEl.textContent = `${d.commercant || "Commerçant"} | TTC: ${d.montant_ttc ?? "?"} ${d.devise || "EUR"} | Statut: ${d.validation_status}`;
        } else {
          visionResultEl.textContent = res.data.error || "Erreur OCR.";
        }
      } else {
        const q = visionQuestionEl ? visionQuestionEl.value.trim() : "";
        const policy = (visionEphemeralEl && visionEphemeralEl.checked) ? "ephemeral" : "keep_24h";
        const st = await apiFetch("/api/vision/stage", {
          method: "POST",
          body: JSON.stringify({ image_b64: stagedImageBase64, question: q, retention_policy: policy })
        });
        if (!st.ok) {
          visionResultEl.textContent = st.data.error || "Capture invalide.";
        } else {
          const cf = await apiFetch("/api/vision/confirm", {
            method: "POST",
            body: JSON.stringify({ preview_id: st.data.preview_id, confirmed: true })
          });
          visionResultEl.textContent = cf.ok ? (cf.data.analysis || cf.data.status) : (cf.data.error || "Erreur analyse.");
        }
      }
    } finally {
      visionSendBtn.disabled = false;
    }
  });
}

// ── Notes Hors-Ligne PWA + Synchronisation Idempotente (Feature 26) ─────────
async function renderNotesList() {
  if (!notesListEl) return;
  notesListEl.replaceChildren();
  const notes = await idbGetAll("notes").catch(() => []);
  notes.forEach((n) => {
    const row = document.createElement("div");
    row.className = "drawer-item";
    const titleEl = document.createElement("strong");
    titleEl.textContent = n.title || "Note";
    const bodyEl = document.createElement("span");
    bodyEl.textContent = ` — ${n.content || ""} (v${n.version || 0})`;
    row.appendChild(titleEl);
    row.appendChild(bodyEl);
    notesListEl.appendChild(row);
  });
}

function openNotesDrawer() {
  if (notesDrawerEl) {
    notesDrawerEl.style.display = "flex";
    renderNotesList();
  }
}
if (notesDrawerBtn) notesDrawerBtn.addEventListener("click", openNotesDrawer);
if (notesCloseBtn) notesCloseBtn.addEventListener("click", () => { if (notesDrawerEl) notesDrawerEl.style.display = "none"; });

if (noteSaveBtn) {
  noteSaveBtn.addEventListener("click", async () => {
    if (!activeAccountId || accountTransitionLock) return;
    const myOwner = activeAccountId;
    const myEpoch = accountEpoch;
    const title = noteTitleInput ? noteTitleInput.value.trim() : "";
    const content = noteContentInput ? noteContentInput.value.trim() : "";
    if (!title && !content) return;
    const now = Date.now();
    const itemId = "note_" + now;
    const opId = "op_" + now + "_" + Math.random().toString(36).slice(2, 6);
    await idbPut("notes", { item_id: itemId, title, content, version: 0, updated_at: now }, myOwner, myEpoch);
    await idbPut("pending_ops", { op_id: opId, item_id: itemId, item_type: "note", title, content, base_version: 0 }, myOwner, myEpoch);
    if (myEpoch !== accountEpoch || activeAccountId !== myOwner) return;
    if (noteTitleInput) noteTitleInput.value = "";
    if (noteContentInput) noteContentInput.value = "";
    await renderNotesList();
    if (navigator.onLine) await syncOfflineNotes();
  });
}

async function syncOfflineNotes() {
  if (!activeAccountId || accountTransitionLock) return;
  const myOwner = activeAccountId;
  const myEpoch = accountEpoch;
  const rawOps = await idbGetAll("pending_ops", myOwner, myEpoch).catch(() => []);
  const ops = rawOps.filter((op) => op && op.owner_id === myOwner);
  if (!navigator.onLine) {
    if (syncStatusTextEl) syncStatusTextEl.textContent = `Hors-ligne (${ops.length} en attente)`;
    return;
  }
  const res = await apiFetch("/api/sync/notes", {
    method: "POST",
    body: JSON.stringify({ ops })
  });
  if (myEpoch !== accountEpoch || activeAccountId !== myOwner) {
    return; // Callback tardif après logout ou changement de compte : strictement ignoré
  }
  if (res.ok && res.data.success) {
    if ((res.data.conflicts || []).length > 0) {
      if (syncStatusTextEl) syncStatusTextEl.textContent = `Conflit détecté (${res.data.conflicts.length}) : révision requise.`;
    } else {
      await idbClear("pending_ops", myOwner).catch(() => {});
      for (const it of (res.data.items || [])) {
        if (myEpoch !== accountEpoch || activeAccountId !== myOwner) return;
        await idbPut("notes", it, myOwner, myEpoch).catch(() => {});
      }
      if (syncStatusTextEl) syncStatusTextEl.textContent = "Synchronisé";
      await renderNotesList();
    }
  }
}
if (notesSyncBtn) notesSyncBtn.addEventListener("click", syncOfflineNotes);

// ── Observabilité & Feature Flags (Feature 30) ──────────────────────────────
async function loadOpsDrawer() {
  if (!opsMetricsBoxEl || !flagsListEl) return;
  opsMetricsBoxEl.textContent = "Chargement...";
  flagsListEl.replaceChildren();
  const met = await apiFetch("/api/ops/metrics");
  if (!met.ok) {
    opsMetricsBoxEl.textContent = met.data.error || "Accès administrateur requis (RBAC).";
    return;
  }
  const sys = met.data.system || {};
  opsMetricsBoxEl.textContent = `CPU: ${sys.cpu_percent}% | RAM: ${sys.ram_percent}% | Disque: ${sys.disk_percent}% | Clients WS: ${(met.data.websocket || {}).connected_clients || 0}`;

  const fl = await apiFetch("/api/flags");
  if (fl.ok && fl.data.flags) {
    Object.entries(fl.data.flags).forEach(([fname, spec]) => {
      const row = document.createElement("div");
      row.className = "drawer-item";
      const label = document.createElement("span");
      label.textContent = `${fname} (${spec.risk_level})`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "flag-btn";
      btn.textContent = spec.enabled ? "ACTIF" : "INACTIF";
      btn.addEventListener("click", async () => {
        await apiFetch("/api/flags", { method: "POST", body: JSON.stringify({ flag: fname, enabled: !spec.enabled }) });
        loadOpsDrawer();
      });
      row.appendChild(label);
      row.appendChild(btn);
      flagsListEl.appendChild(row);
    });
  }
}
if (opsDrawerBtn) opsDrawerBtn.addEventListener("click", () => { if (opsDrawerEl) { opsDrawerEl.style.display = "flex"; loadOpsDrawer(); } });
if (opsCloseBtn) opsCloseBtn.addEventListener("click", () => { if (opsDrawerEl) opsDrawerEl.style.display = "none"; });
if (opsRefreshBtn) opsRefreshBtn.addEventListener("click", loadOpsDrawer);

// ── Cycle de Vie des Commandes & Modale Confirmation (LOT A / E) ─────────────
function handleCommandLifecycle(data) {
  if (!commandStatusCardEl) return;
  if (statusCardTimer) { clearTimeout(statusCardTimer); statusCardTimer = null; }
  commandStatusCardEl.style.display = "block";
  const state = (data.state || "UNKNOWN").toUpperCase();

  if (commandStatePillEl) {
    commandStatePillEl.textContent = state;
    commandStatePillEl.className = "state-pill pill-" + state.toLowerCase();
  }
  if (commandActionNameEl) commandActionNameEl.textContent = data.action ? `[${data.action}]` : "";
  if (commandStatusDetailEl) {
    if (state === "REQUIRES_CONFIRMATION") {
      commandStatusDetailEl.textContent = "Action sensible en attente d'accord.";
      showActionConfirmModal(data.command_id, data.confirmation_token, data.confirmation_prompt);
    } else if (state === "RUNNING") {
      commandStatusDetailEl.textContent = "Exécution de l'action en cours...";
    } else if (state === "SUCCEEDED") {
      commandStatusDetailEl.textContent = typeof data.result === "string" ? data.result : "Action réussie et confirmée.";
      scheduleStatusCardHide(4500);
    } else if (state === "FAILED") {
      commandStatusDetailEl.textContent = data.error || "Échec de l'action demandée.";
      scheduleStatusCardHide(5000);
    } else if (state === "CANCELLED") {
      commandStatusDetailEl.textContent = "Commande annulée par l'utilisateur.";
      scheduleStatusCardHide(3500);
    } else if (state === "UNKNOWN") {
      commandStatusDetailEl.textContent = data.error || "État physique du matériel non confirmé.";
      scheduleStatusCardHide(5000);
    } else {
      commandStatusDetailEl.textContent = "Traitement en cours...";
    }
  }
}

function showActionConfirmModal(cmdId, token, prompt) {
  pendingConfirmationCmdId = cmdId;
  pendingConfirmationToken = token;
  if (confirmModalPromptEl) confirmModalPromptEl.textContent = prompt || "Une action sensible requiert votre confirmation.";
  if (actionConfirmModalEl) actionConfirmModalEl.style.display = "flex";
}

function hideActionConfirmModal() {
  if (actionConfirmModalEl) actionConfirmModalEl.style.display = "none";
  pendingConfirmationCmdId = null;
  pendingConfirmationToken = null;
}

function scheduleStatusCardHide(delayMs) {
  if (statusCardTimer) clearTimeout(statusCardTimer);
  statusCardTimer = setTimeout(() => {
    if (commandStatusCardEl) commandStatusCardEl.style.display = "none";
    statusCardTimer = null;
  }, delayMs);
}

if (confirmActionBtn) {
  confirmActionBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN && pendingConfirmationCmdId) {
      ws.send(JSON.stringify({ type: "confirm_action", command_id: pendingConfirmationCmdId, confirmation_token: pendingConfirmationToken, confirmed: true }));
    }
    hideActionConfirmModal();
  });
}
if (cancelActionBtn) {
  cancelActionBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN && pendingConfirmationCmdId) {
      ws.send(JSON.stringify({ type: "confirm_action", command_id: pendingConfirmationCmdId, confirmed: false }));
    }
    hideActionConfirmModal();
  });
}

// ── Affichage & Audio TTS ───────────────────────────────────────────────────
function afficherTexteUtilisateur(text) {
  userTextEl.textContent = `"${text}"`;
  jarvisTextEl.textContent = "";
}

function afficherReponseJarvis(text) {
  const textePropre = text.replace(/\{[^}]*\}/gs, "").replace(/\s{2,}/g, " ").trim();
  jarvisTextEl.textContent = textePropre || text;
}

function jouerAudioBase64(base64) {
  stopPlaybackNow();
  applyState("speaking");
  currentAudio = new Audio("data:audio/mp3;base64," + base64);
  currentAudio.play().catch(e => console.error("[AUDIO] Erreur lecture :", e));

  fakeVolumeInterval = setInterval(() => {
    if (orb) {
      const t = Date.now() / 50;
      const vol = 0.4 + 0.3 * Math.sin(t) + 0.2 * Math.sin(t * 0.5);
      orb.setVolume(Math.max(0.1, Math.min(1.0, vol + (Math.random() * 0.2 - 0.1))));
    }
  }, 50);

  currentAudio.addEventListener("ended", () => { stopPlaybackNow(); applyState("idle"); });
  currentAudio.addEventListener("pause", () => { if (currentState === "speaking") applyState("idle"); stopPlaybackNow(); });
}

let synthVoice = null;
function chargerVoix() {
  const voices = window.speechSynthesis.getVoices();
  synthVoice = voices.find(v => v.lang === "fr-FR" && v.name.includes("Google")) || voices.find(v => v.lang === "fr-FR") || voices.find(v => v.lang.startsWith("fr")) || null;
}
window.speechSynthesis.addEventListener("voiceschanged", chargerVoix);
chargerVoix();

function parleSynthese(texte) {
  window.speechSynthesis.cancel();
  const textePropre = texte.replace(/\{[^}]*\}/gs, "").replace(/\s{2,}/g, " ").trim();
  if (!textePropre) return;
  applyState("speaking");
  const utterance = new SpeechSynthesisUtterance(textePropre);
  utterance.lang = SPEECH_LANG;
  utterance.rate = whisperManualOn ? 0.85 : 0.95;
  utterance.volume = whisperManualOn ? 0.35 : 1.0;
  if (synthVoice) utterance.voice = synthVoice;
  utterance.addEventListener("end", () => applyState("idle"));
  utterance.addEventListener("error", () => applyState("idle"));
  window.speechSynthesis.speak(utterance);
}

// ── STT Web Speech API ──────────────────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = SPEECH_LANG;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.addEventListener("start", () => {
    isListening = true;
    applyState("listening");
    userTextEl.textContent = "";
    jarvisTextEl.textContent = "";
  });

  recognition.addEventListener("result", (event) => {
    let interim = "";
    let final_txt = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const tr = event.results[i][0].transcript;
      if (event.results[i].isFinal) final_txt += tr;
      else interim += tr;
    }
    userTextEl.textContent = `"${final_txt || interim}"`;
  });

  recognition.addEventListener("end", () => {
    isListening = false;
    const texteCapture = userTextEl.textContent.replace(/^"|"$/g, "").trim();
    if (texteCapture) {
      applyState("thinking");
      if (!sendCommand(texteCapture)) {
        applyState("idle");
        userTextEl.textContent = "⚠ Non connecté à ALICE";
      }
    } else {
      applyState("idle");
    }
  });

  recognition.addEventListener("error", (event) => {
    isListening = false;
    applyState("idle");
    if (event.error === "not-allowed") userTextEl.textContent = "⚠ Micro non autorisé. Activez le dans chrome://flags";
    else if (event.error === "no-speech") userTextEl.textContent = "";
    else userTextEl.textContent = `⚠ Erreur micro : ${event.error}`;
  });
} else {
  micBtn.disabled = true;
  statusEl.textContent = "micro non supporté sur ce navigateur";
}

micBtn.addEventListener("click", () => {
  if (!recognition) return;
  if (currentState === "speaking") {
    stopPlaybackNow();
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "barge_in" }));
  }
  if (currentState === "thinking") return;
  if (isListening) recognition.stop();
  else {
    window.speechSynthesis.cancel();
    try { recognition.start(); } catch (e) {}
  }
});

connectWS();
console.log("[ALICE MOBILE] Interface PWA initialisée. WebSocket :", WS_URL);
