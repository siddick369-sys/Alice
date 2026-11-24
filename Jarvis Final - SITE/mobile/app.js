/**
 * J.A.R.V.I.S — Interface Mobile
 *
 * Se connecte au backend Python via WebSocket dynamiquement (même IP que le serveur HTTP).
 * Utilise Web Speech API pour STT (voix → texte) et SpeechSynthesis pour TTS (texte → voix).
 *
 * États: "idle" | "listening" | "thinking" | "speaking"
 */

// ── Config ─────────────────────────────────────────────────────────────────
const isHttps = window.location.protocol === "https:";
const wsProtocol = isHttps ? "wss:" : "ws:";
const WS_URL = `${wsProtocol}//${window.location.hostname}:8765`;
const RECONNECT_DELAY_MS = 2500;
const SPEECH_LANG = "fr-FR";

// ── DOM Refs ────────────────────────────────────────────────────────────────
const badgeEl      = document.getElementById("connection-badge");
const badgeLabelEl = document.getElementById("connection-label");
const statusEl     = document.getElementById("status-text");
const userTextEl   = document.getElementById("user-text");
const jarvisTextEl = document.getElementById("jarvis-text");
const micBtn       = document.getElementById("mic-btn");
const micIcon      = micBtn.querySelector(".mic-icon");
const stopIcon     = micBtn.querySelector(".stop-icon");
const micLabelEl   = document.getElementById("mic-label");
const stopJarvisBtn= document.getElementById("stop-jarvis-btn");

// ── DOM Refs Appairage (SEC-04) ─────────────────────────────────────────────
const pairingModalEl   = document.getElementById("pairing-modal");
const pairingInputEl   = document.getElementById("pairing-code-input");
const pairingSubmitBtn = document.getElementById("pairing-submit-btn");
const pairingErrorEl   = document.getElementById("pairing-error");

// ── DOM Refs Cycle de Vie & Confirmation (LOT A / E) ────────────────────────
const commandStatusCardEl = document.getElementById("command-status-card");
const commandStatePillEl  = document.getElementById("command-state-pill");
const commandActionNameEl = document.getElementById("command-action-name");
const commandStatusDetailEl = document.getElementById("command-status-detail");
const actionConfirmModalEl= document.getElementById("action-confirm-modal");
const confirmModalPromptEl= document.getElementById("confirm-modal-prompt");
const confirmActionBtn    = document.getElementById("confirm-action-btn");
const cancelActionBtn     = document.getElementById("cancel-action-btn");

let pendingConfirmationCmdId = null;
let pendingConfirmationToken = null;
let statusCardTimer          = null;
let lastCommandTime          = 0;

// ── ORB 3D ──────────────────────────────────────────────────────────────────
let orb = null;
if (typeof createOrb === "function") {
  const canvas = document.getElementById("orb-canvas");
  if (canvas) {
    orb = createOrb(canvas);
  }
}

// ── HTTPS Warning ───────────────────────────────────────────────────────────
if (window.location.protocol !== "https:" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
  const warning = document.getElementById("https-warning");
  if (warning) {
    warning.style.display = "block";
    const closeBtn = document.getElementById("close-warning-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        warning.style.display = "none";
      });
    }
  }
}

// ── État de l'application ───────────────────────────────────────────────────
let currentState = "idle";
let ws           = null;
let isListening  = false;
let reconnectTimer = null;

// ── Gestion des états ───────────────────────────────────────────────────────
const STATE_LABELS = {
  idle:      "en attente",
  listening: "je vous écoute...",
  thinking:  "en réflexion...",
  speaking:  "jarvis répond...",
};

function applyState(state) {
  // Retirer l'ancien état du body
  document.body.classList.remove(
    "state-idle", "state-listening", "state-thinking", "state-speaking"
  );
  document.body.classList.add(`state-${state}`);
  currentState = state;
  statusEl.textContent = STATE_LABELS[state] || state;

  // Affichage du bouton Stop global seulement si ca parle
  if (state === "speaking") {
    stopJarvisBtn.style.display = "flex";
  } else {
    stopJarvisBtn.style.display = "none";
  }

  // Icône microphone
  if (state === "listening") {
    micIcon.style.display = "none";
    stopIcon.style.display = "block";
    micLabelEl.textContent = "APPUYER POUR ARRÊTER";
  } else {
    micIcon.style.display = "block";
    stopIcon.style.display = "none";
    micLabelEl.textContent = "APPUYER POUR PARLER";
  }

  // Mettre à jour l'état de l'orbe 3D
  if (orb) {
    orb.setState(state);
  }
}

applyState("idle");

let currentAudio = null;
let fakeVolumeInterval = null;

// Écouteur pour le bouton stop JARVIS
stopJarvisBtn.addEventListener("click", () => {
  window.speechSynthesis.cancel(); // Stoppe l'audio mobile (fallback)
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "stop_audio" })); // Stoppe l'audio PC
  }
  applyState("idle");
});

// ── Badge de connexion ──────────────────────────────────────────────────────
function setConnected(ok) {
  badgeEl.classList.toggle("connected", ok);
  badgeEl.classList.toggle("disconnected", !ok);
  badgeLabelEl.textContent = ok ? "connecté" : "reconnexion...";
}
setConnected(false);

// ── Appairage Sécurisé (SEC-04) ──────────────────────────────────────────────
function showPairingModal(errorMessage = "") {
  if (pairingModalEl) {
    pairingModalEl.style.display = "flex";
    if (pairingInputEl) {
      pairingInputEl.value = "";
      pairingInputEl.focus();
    }
    if (pairingErrorEl) {
      if (errorMessage) {
        pairingErrorEl.textContent = errorMessage;
        pairingErrorEl.style.display = "block";
      } else {
        pairingErrorEl.style.display = "none";
      }
    }
  }
}

function hidePairingModal() {
  if (pairingModalEl) {
    pairingModalEl.style.display = "none";
  }
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
      // Nettoyage impératif de tout token sensible dans localStorage (P1 / Hardening 006)
      localStorage.removeItem("jarvis_session_token");
      localStorage.removeItem("jarvis_session_id");
      sessionStorage.setItem("jarvis_session_id", result.session_id);
      if (result.csrf_token) {
        sessionStorage.setItem("jarvis_csrf_token", result.csrf_token);
      }
      hidePairingModal();
      connectWS();
    } else {
      if (pairingErrorEl) {
        pairingErrorEl.textContent = result.error || "Code invalide ou expiré.";
        pairingErrorEl.style.display = "block";
      }
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

if (pairingSubmitBtn) {
  pairingSubmitBtn.addEventListener("click", submitPairingCode);
}
if (pairingInputEl) {
  pairingInputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitPairingCode();
  });
}

// ── WebSocket (Hardening P1 / Cookies HttpOnly) ───────────────────────────────
function connectWS() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }

  // En P1 (Hardening 006), l'authentification prioritaire s'effectue automatiquement
  // par cookie sécurisé HttpOnly transmis par le navigateur lors du handshake WebSocket.
  // Les clés localStorage legacy sont uniquement utilisées en repli de transition.
  const legacySessionId = localStorage.getItem("jarvis_session_id");
  const legacyToken = localStorage.getItem("jarvis_session_token");

  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    console.log("[WS] Connecté à", WS_URL, "- En attente de validation handshake");
    // Si un ancien jeton legacy est présent et pas de cookie, on le transmet pour compatibilité
    if (legacySessionId && legacyToken) {
      ws.send(JSON.stringify({
        type: "auth",
        session_id: legacySessionId,
        token: legacyToken
      }));
    }
  });

  ws.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "auth_ok") {
        console.log("[WS] Authentification réussie (Session:", data.session_id, "Méthode:", data.auth_method || "token", ")");
        setConnected(true);
        hidePairingModal();
        return;
      }

      if (data.type === "command_lifecycle") {
        handleCommandLifecycle(data);
        return;
      }

      if (data.type === "auth_error") {
        console.warn("[WS] Erreur authentification :", data.message);
        localStorage.removeItem("jarvis_session_id");
        localStorage.removeItem("jarvis_session_token");
        sessionStorage.removeItem("jarvis_session_id");
        sessionStorage.removeItem("jarvis_csrf_token");
        setConnected(false);
        showPairingModal("Session invalide ou expirée. Veuillez saisir un nouveau code d'appairage.");
        try { ws.close(4001, "Auth error"); } catch(e) {}
        return;
      }

      // État de l'orbe (envoyé par le backend lors de ses propres actions)
      if (data.action === "set_state" && data.state) {
        // Ignorer les états de microphone local du PC ("listening", "active") car le mobile gère son propre micro
        if (data.state === "listening" || data.state === "active") return;
        // Si le mobile est en train d'écouter, on ne le force pas en idle non plus
        if (data.state === "idle" && isListening) return;

        // On ignore l'état "speaking" du PC uniquement si on utilise le TTS local (SpeechSynthesis).
        // Mais maintenant on joue l'audio distant, donc on peut accepter l'état speaking, bien qu'on l'applique localement au lancement de l'audio.
        if (data.state !== "speaking") {
          applyState(data.state);
        }
      }

      // Réponse textuelle de JARVIS destinée au mobile avec audio distant (même voix que web)
      if (data.action === "jarvis_audio" && data.audio_b64) {
        afficherReponseJarvis(data.text);
        jouerAudioBase64(data.audio_b64);
      }
      // Fallback ancienne méthode (sans audio)
      else if (data.action === "jarvis_response" && data.text) {
        afficherReponseJarvis(data.text);
        parleSynthese(data.text);
      }
    } catch (e) {
      console.error("[WS] Erreur parsing message :", e);
    }
  });

  ws.addEventListener("close", (event) => {
    console.log("[WS] Déconnecté (Code:", event.code, ").");
    setConnected(false);
    applyState("idle");

    if (event.code === 4001 || event.code === 4003) {
      // Rejet sécurité / session expirée : ne PAS relancer de boucle de reconnexion infinie !
      localStorage.removeItem("jarvis_session_id");
      localStorage.removeItem("jarvis_session_token");
      sessionStorage.removeItem("jarvis_session_id");
      sessionStorage.removeItem("jarvis_csrf_token");
      showPairingModal("Connexion refusée par le serveur. Veuillez réappairer l'appareil.");
      return;
    }

    scheduleReconnect();
  });

  ws.addEventListener("error", () => {
    setConnected(false);
  });
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWS();
  }, RECONNECT_DELAY_MS);
}

function sendCommand(text) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn("[WS] WebSocket non connecté, commande ignorée.");
    return false;
  }
  const now = Date.now();
  if (now - lastCommandTime < 800) {
    console.warn("[WS] Anti-rebond : commande soumise trop rapidement.");
    return false;
  }
  lastCommandTime = now;
  const cmdId = "cmd_" + now + "_" + Math.random().toString(36).substr(2, 6);
  ws.send(JSON.stringify({ type: "mobile_command", text, command_id: cmdId }));
  return true;
}

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

  if (commandActionNameEl) {
    commandActionNameEl.textContent = data.action ? `[${data.action}]` : "";
  }

  if (commandStatusDetailEl) {
    if (state === "REQUIRES_CONFIRMATION") {
      commandStatusDetailEl.textContent = "Action sensible en attente d'accord.";
      showActionConfirmModal(data.command_id, data.confirmation_token, data.confirmation_prompt);
    } else if (state === "RUNNING") {
      commandStatusDetailEl.textContent = "Exécution de l'action en cours...";
    } else if (state === "SUCCEEDED") {
      const resMsg = typeof data.result === "string" ? data.result : "Action réussie et confirmée.";
      commandStatusDetailEl.textContent = resMsg;
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
  if (confirmModalPromptEl) {
    confirmModalPromptEl.textContent = prompt || "Une action sensible requiert votre confirmation.";
  }
  if (actionConfirmModalEl) {
    actionConfirmModalEl.style.display = "flex";
  }
}

function hideActionConfirmModal() {
  if (actionConfirmModalEl) {
    actionConfirmModalEl.style.display = "none";
  }
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
      ws.send(JSON.stringify({
        type: "confirm_action",
        command_id: pendingConfirmationCmdId,
        confirmation_token: pendingConfirmationToken,
        confirmed: true
      }));
    }
    hideActionConfirmModal();
  });
}

if (cancelActionBtn) {
  cancelActionBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN && pendingConfirmationCmdId) {
      ws.send(JSON.stringify({
        type: "confirm_action",
        command_id: pendingConfirmationCmdId,
        confirmed: false
      }));
    }
    hideActionConfirmModal();
  });
}

// ── Affichage dialogue ──────────────────────────────────────────────────────
function afficherTexteUtilisateur(text) {
  userTextEl.textContent = `"${text}"`;
  jarvisTextEl.textContent = "";
}

function afficherReponseJarvis(text) {
  // Nettoyer les éventuels blocs JSON de la réponse pour l'affichage
  const textePropre = text
    .replace(/\{[^}]*\}/gs, "")        // supprimer blocs JSON
    .replace(/\s{2,}/g, " ")           // normaliser espaces
    .trim();
  jarvisTextEl.textContent = textePropre || text;
}

function jouerAudioBase64(base64) {
  if (currentAudio) {
    currentAudio.pause();
  }
  window.speechSynthesis.cancel();
  
  applyState("speaking");
  
  currentAudio = new Audio("data:audio/mp3;base64," + base64);
  currentAudio.play().catch(e => console.error("[AUDIO] Erreur lecture :", e));
  
  // Fake volume for ORB
  if (fakeVolumeInterval) clearInterval(fakeVolumeInterval);
  fakeVolumeInterval = setInterval(() => {
    if (orb) {
      const t = Date.now() / 50;
      const vol = 0.4 + 0.3 * Math.sin(t) + 0.2 * Math.sin(t * 0.5);
      orb.setVolume(Math.max(0.1, Math.min(1.0, vol + (Math.random() * 0.2 - 0.1))));
    }
  }, 50);

  currentAudio.addEventListener("ended", () => {
    applyState("idle");
    if (fakeVolumeInterval) {
      clearInterval(fakeVolumeInterval);
      fakeVolumeInterval = null;
    }
    if (orb) orb.setVolume(0);
    currentAudio = null;
  });
  
  currentAudio.addEventListener("pause", () => {
    if (currentState === "speaking") {
      applyState("idle");
    }
    if (fakeVolumeInterval) {
      clearInterval(fakeVolumeInterval);
      fakeVolumeInterval = null;
    }
    if (orb) orb.setVolume(0);
  });
}

// ── TTS Web (Speech Synthesis) ──────────────────────────────────────────────
let synthVoice = null;

function chargerVoix() {
  const voices = window.speechSynthesis.getVoices();
  // Chercher une voix française de bonne qualité
  synthVoice =
    voices.find(v => v.lang === "fr-FR" && v.name.includes("Google")) ||
    voices.find(v => v.lang === "fr-FR") ||
    voices.find(v => v.lang.startsWith("fr")) ||
    null;
  console.log("[TTS] Voix sélectionnée :", synthVoice?.name || "par défaut");
}

window.speechSynthesis.addEventListener("voiceschanged", chargerVoix);
chargerVoix();

function parleSynthese(texte) {
  // Annuler toute synthèse en cours
  window.speechSynthesis.cancel();

  // Nettoyer le texte (enlever JSON pour ne lire que la partie conversationnelle)
  const textePropre = texte
    .replace(/\{[^}]*\}/gs, "")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!textePropre) return;

  applyState("speaking");

  const utterance = new SpeechSynthesisUtterance(textePropre);
  utterance.lang = SPEECH_LANG;
  utterance.rate = 0.95;
  utterance.pitch = 0.9;
  utterance.volume = 1.0;

  if (synthVoice) {
    utterance.voice = synthVoice;
  }

  utterance.addEventListener("end", () => {
    applyState("idle");
  });

  utterance.addEventListener("error", (e) => {
    console.warn("[TTS] Erreur synthèse :", e.error);
    applyState("idle");
  });

  window.speechSynthesis.speak(utterance);
}

// ── STT Web Speech API ──────────────────────────────────────────────────────
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang           = SPEECH_LANG;
  recognition.continuous     = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.addEventListener("start", () => {
    isListening = true;
    applyState("listening");
    userTextEl.textContent  = "";
    jarvisTextEl.textContent = "";
    console.log("[STT] Écoute démarrée.");
  });

  recognition.addEventListener("result", (event) => {
    let interim   = "";
    let final_txt = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        final_txt += transcript;
      } else {
        interim += transcript;
      }
    }

    // Affichage en temps réel des résultats intermédiaires
    userTextEl.textContent = `"${final_txt || interim}"`;

    if (final_txt) {
      console.log("[STT] Résultat final :", final_txt);
    }
  });

  recognition.addEventListener("end", () => {
    isListening = false;
    const texteCapture = userTextEl.textContent.replace(/^"|"$/g, "").trim();
    console.log("[STT] Fin écoute. Texte :", texteCapture);

    if (texteCapture) {
      applyState("thinking");
      const envoyé = sendCommand(texteCapture);
      if (!envoyé) {
        applyState("idle");
        userTextEl.textContent = "⚠ Non connecté à JARVIS";
      }
    } else {
      applyState("idle");
    }
  });

  recognition.addEventListener("error", (event) => {
    console.warn("[STT] Erreur :", event.error);
    isListening = false;
    applyState("idle");

    if (event.error === "not-allowed") {
      userTextEl.textContent =
        "⚠ Micro non autorisé. Activez le dans chrome://flags";
    } else if (event.error === "no-speech") {
      userTextEl.textContent = "";
    } else {
      userTextEl.textContent = `⚠ Erreur micro : ${event.error}`;
    }
  });

} else {
  // SpeechRecognition non supporté
  micBtn.disabled = true;
  statusEl.textContent = "micro non supporté sur ce navigateur";
  console.error("[STT] SpeechRecognition non disponible.");
}

// ── Bouton microphone ───────────────────────────────────────────────────────
micBtn.addEventListener("click", () => {
  if (!recognition) return;

  // Bloquer si JARVIS pense ou parle
  if (currentState === "thinking" || currentState === "speaking") return;

  if (isListening) {
    // Arrêter l'écoute
    recognition.stop();
  } else {
    // Annuler TTS en cours si nécessaire
    window.speechSynthesis.cancel();
    try {
      recognition.start();
    } catch (e) {
      console.warn("[STT] Impossible de démarrer :", e);
    }
  }
});

// ── Démarrage ───────────────────────────────────────────────────────────────
connectWS();
console.log("[JARVIS MOBILE] Interface initialisée. WebSocket :", WS_URL);
