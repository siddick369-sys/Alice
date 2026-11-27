/**
 * J.A.R.V.I.S — Interface Web avec Orbe Three.js
 *
 * Se connecte au backend Python via WebSocket (ws://localhost:8765),
 * recoit les changements d'etat et pilote l'orbe en consequence.
 *
 * Etats: "idle" | "listening" | "thinking" | "speaking"
 */

import { createOrb, type OrbState } from "./orb";
import { injectVisionButton, captureFrame } from "./screen_capture";
import "./style.css";

// ── Config ────────────────────────────────────────────────────────────────────
const WS_URL = "ws://localhost:8765";
const RECONNECT_INTERVAL_MS = 2_000;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById("orb-canvas") as HTMLCanvasElement;
const statusEl = document.getElementById("status-text") as HTMLDivElement;
const errorEl = document.getElementById("error-text") as HTMLDivElement;
const badgeEl = document.getElementById("connection-badge") as HTMLDivElement;
const badgeLabelEl = document.getElementById(
  "connection-label"
) as HTMLSpanElement;
const muteButtonEl = document.getElementById("mute-button") as HTMLButtonElement;
const commandInputEl = document.getElementById("command-input") as HTMLInputElement;
const commandSendEl = document.getElementById("command-send") as HTMLButtonElement;
const commandContainerEl = document.getElementById("command-container") as HTMLDivElement;
const uploadButtonEl = document.getElementById("upload-button") as HTMLButtonElement;
const fileUploadEl = document.getElementById("file-upload") as HTMLInputElement;

// ── Orb ───────────────────────────────────────────────────────────────────────
const orb = createOrb(canvas);

// ── State labels (French) ────────────────────────────────────────────────────
const STATE_LABELS: Record<OrbState, string> = {
  idle: "",
  listening: "ecoute...",
  thinking: "reflexion...",
  speaking: "",
};

function applyState(state: OrbState): void {
  orb.setState(state);
  statusEl.textContent = STATE_LABELS[state];
}

function setMuted(muted: boolean): void {
  muteButtonEl.classList.toggle("is-muted", muted);
  muteButtonEl.setAttribute("aria-pressed", String(muted));
  muteButtonEl.textContent = muted ? "unmute" : "mute";
}

// ── Error toast ───────────────────────────────────────────────────────────────
let errorTimer: ReturnType<typeof setTimeout> | null = null;

function showError(msg: string): void {
  errorEl.textContent = msg;
  errorEl.style.opacity = "1";
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(() => {
    errorEl.style.opacity = "0";
  }, 4_000);
}

// ── Connection badge ──────────────────────────────────────────────────────────
function setConnected(ok: boolean): void {
  badgeEl.classList.toggle("connected", ok);
  badgeEl.classList.toggle("disconnected", !ok);
  badgeLabelEl.textContent = ok ? "connecte" : "reconnexion";
  muteButtonEl.disabled = !ok;
}

// ── WebSocket with auto-reconnect ─────────────────────────────────────────────
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function connect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    // F013-01: Ne pas déclarer connecté sur simple ouverture de socket transport.
    // L'état 'connecte' exige la confirmation applicative auth_ok du serveur.
    badgeLabelEl.textContent = "authentification...";
  });

  ws.addEventListener("message", async (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data as string) as {
        type?: string;
        state?: string;
        action?: string;
        muted?: boolean;
        volume?: number;
        id?: string;
        active?: boolean;
        window_seconds?: number;
        error?: string;
      };

      if (data.type === "auth_ok") {
        setConnected(true);
        statusEl.textContent = "pret";
        return;
      }

      if (data.type === "auth_error") {
        setConnected(false);
        statusEl.textContent = "erreur d'authentification";
        return;
      }

      if (data.type === "command_lifecycle" && data.state) {
        statusEl.textContent = data.action
          ? `[${data.action}] ${data.state.toLowerCase()}`
          : data.state.toLowerCase();
        return;
      }

      if (data.type === "followup_state") {
        statusEl.textContent = data.active
          ? `ecoute continue (${data.window_seconds ?? 5}s)...`
          : "";
        return;
      }

      if (data.type === "barge_in_stop" || data.action === "barge_in_stop") {
        applyState("listening");
        return;
      }

      if (data.action === "request_screen_capture") {
        const frame = await captureFrame();
        if (frame && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "screen_frame",
            id: data.id,
            data: frame,
          }));
        } else if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "screen_frame",
            id: data.id,
            error: "no_stream",
          }));
        }
        return;
      }

      if (data.action === "demo") {
        orb.triggerDemo();
        return;
      }
      if (data.action === "set_volume" && typeof data.volume === "number") {
        orb.setVolume(data.volume);
        return;
      }
      if (data.state) {
        applyState(data.state as OrbState);
      }
      if (typeof data.volume === "number") {
        orb.setVolume(data.volume);
      }
      if (typeof data.muted === "boolean") {
        setMuted(data.muted);
      }
    } catch {
      // ignore malformed messages
    }
  });

  ws.addEventListener("close", () => {
    setConnected(false);
    applyState("idle");
    scheduleReconnect();
  });

  ws.addEventListener("error", () => {
    setConnected(false);
  });
}

function scheduleReconnect(): void {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_INTERVAL_MS);
}

// ── Events ──────────────────────────────────────────────────────────────────
muteButtonEl.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  // Envoi du signal barge-in / stop au backend
  ws.send(JSON.stringify({ type: "barge_in" }));

  // Feedback immédiat sur l'orbe
  applyState("idle");
});

// ── Command Input Actions ───────────────────────────────────────────────────
function sendCommand(): void {
  const text = commandInputEl.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

  // Send as mobile_command so the backend processes it the same way
  ws.send(JSON.stringify({ type: "mobile_command", text }));
  
  // Clear input
  commandInputEl.value = "";
  applyState("thinking");
}

commandSendEl.addEventListener("click", sendCommand);
commandInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendCommand();
  }
});

// ── File Upload Actions ─────────────────────────────────────────────────────
uploadButtonEl.addEventListener("click", () => {
  fileUploadEl.click();
});

fileUploadEl.addEventListener("change", async () => {
  const file = fileUploadEl.files?.[0];
  if (!file || !ws || ws.readyState !== WebSocket.OPEN) return;

  const reader = new FileReader();
  reader.onload = () => {
    const base64Data = (reader.result as string).split(",")[1];
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "file_upload",
        name: file.name,
        content: base64Data
      }));
      applyState("thinking");
      statusEl.textContent = `analyse de ${file.name}...`;
    }
  };
  reader.readAsDataURL(file);

  // Reset input so the same file can be uploaded again if needed
  fileUploadEl.value = "";
});

// ── Boot ──────────────────────────────────────────────────────────────────────
setConnected(false);
applyState("idle");
setMuted(false);
injectVisionButton();
connect();

// Silence unused-import warning for showError
void showError;
