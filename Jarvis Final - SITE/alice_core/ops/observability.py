#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 30 — OBSERVABILITY AND SELF-DIAGNOSTICS DASHBOARD (ALICE-OPS-030, Wave 1).
Fournit la télémétrie matérielle (CPU/RAM/Disque sans psutil obligatoire),
les histogrammes de latence (IA/STT/TTS/RAG/OCR/Barge-In), le taux de réussite des commandes,
la santé des intégrations et les alertes sur seuils sans exposer de secrets ni de conversations.
"""

import os
import sys
import time
import json
import math
import shutil
import ctypes
import threading
from collections import deque, defaultdict
from typing import Dict, Any, Optional, List
from alice_core.security.rbac import RBAC, UserPrincipal


class SystemTelemetryCollector:
    """Collecteur système multiplateforme sans dépendance obligatoire à psutil."""

    def __init__(self):
        self._prev_idle = None
        self._prev_kernel = None
        self._prev_user = None
        self._lock = threading.Lock()

    def _cpu_percent_win32(self) -> Optional[float]:
        if sys.platform != "win32":
            return None
        try:
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

            def _to_int(ft):
                return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

            idle_ft, kernel_ft, user_ft = FILETIME(), FILETIME(), FILETIME()
            if not ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle_ft), ctypes.byref(kernel_ft), ctypes.byref(user_ft)
            ):
                return None

            idle = _to_int(idle_ft)
            kernel = _to_int(kernel_ft)
            user = _to_int(user_ft)

            with self._lock:
                if self._prev_idle is None:
                    self._prev_idle, self._prev_kernel, self._prev_user = idle, kernel, user
                    # Court échantillonnage non bloquant pour fournir une vraie mesure initiale
                    time.sleep(0.05)
                    ctypes.windll.kernel32.GetSystemTimes(
                        ctypes.byref(idle_ft), ctypes.byref(kernel_ft), ctypes.byref(user_ft)
                    )
                    idle2, kernel2, user2 = _to_int(idle_ft), _to_int(kernel_ft), _to_int(user_ft)
                    d_idle = idle2 - idle
                    d_sys = (kernel2 - kernel) + (user2 - user)
                    self._prev_idle, self._prev_kernel, self._prev_user = idle2, kernel2, user2
                else:
                    d_idle = idle - self._prev_idle
                    d_sys = (kernel - self._prev_kernel) + (user - self._prev_user)
                    self._prev_idle, self._prev_kernel, self._prev_user = idle, kernel, user

            if d_sys <= 0:
                return 0.0
            usage = (1.0 - (d_idle / d_sys)) * 100.0
            return round(max(0.0, min(100.0, usage)), 1)
        except Exception:
            return None

    def _ram_stats_win32(self) -> Optional[Dict[str, Any]]:
        if sys.platform != "win32":
            return None
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
            avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
            return {
                "percent": float(stat.dwMemoryLoad),
                "total_gb": total_gb,
                "available_gb": avail_gb,
            }
        except Exception:
            return None

    def sample(self) -> Dict[str, Any]:
        """Retourne les métriques système réelles."""
        try:
            import psutil
            cpu = round(psutil.cpu_percent(interval=0.05), 1)
            vm = psutil.virtual_memory()
            ram = {
                "percent": round(vm.percent, 1),
                "total_gb": round(vm.total / (1024 ** 3), 2),
                "available_gb": round(vm.available / (1024 ** 3), 2),
            }
        except ImportError:
            cpu = self._cpu_percent_win32()
            if cpu is None:
                try:
                    load1, _, _ = os.getloadavg()
                    cpu = round(min(100.0, (load1 / (os.cpu_count() or 1)) * 100.0), 1)
                except Exception:
                    cpu = 0.0
            ram = self._ram_stats_win32() or {"percent": 0.0, "total_gb": 0.0, "available_gb": 0.0}

        disk_root = os.path.abspath(os.path.dirname(__file__))
        du = shutil.disk_usage(disk_root)
        disk_pct = round((du.used / du.total) * 100.0, 1) if du.total else 0.0

        return {
            "cpu_percent": cpu,
            "ram_percent": ram["percent"],
            "ram_total_gb": ram["total_gb"],
            "ram_available_gb": ram["available_gb"],
            "disk_percent": disk_pct,
            "disk_free_gb": round(du.free / (1024 ** 3), 2),
            "active_threads": threading.active_count(),
        }


class ObservabilityRegistry:
    """Registre central de télémétrie, latences et diagnostics non destructifs."""

    DEFAULT_METRICS = (
        "ia_latency_ms",
        "stt_latency_ms",
        "tts_latency_ms",
        "barge_in_latency_ms",
        "rag_search_ms",
        "ocr_latency_ms",
        "orchestrator_ms",
        "sync_latency_ms",
    )

    def __init__(self, max_samples: int = 500):
        self._lock = threading.RLock()
        self.start_time = time.time()
        self.telemetry = SystemTelemetryCollector()
        self._latencies: Dict[str, deque] = {m: deque(maxlen=max_samples) for m in self.DEFAULT_METRICS}
        self._command_counts: Dict[str, int] = defaultdict(int)
        self._integrations_health: Dict[str, Dict[str, Any]] = {}
        self._history: deque = deque(maxlen=120)
        self._thresholds = {
            "cpu_percent": 85.0,
            "ram_percent": 90.0,
            "disk_percent": 92.0,
            "failure_rate_percent": 25.0,
        }
        self._ws_clients_getter = lambda: 0
        self._jobs_depth_getter = lambda: {"queued": 0, "running": 0}
        self._rag_stats_getter = lambda: {"chunks": 0, "status": "unknown"}

    def bind_providers(self, ws_clients_fn=None, jobs_depth_fn=None, rag_stats_fn=None):
        if ws_clients_fn:
            self._ws_clients_getter = ws_clients_fn
        if jobs_depth_fn:
            self._jobs_depth_getter = jobs_depth_fn
        if rag_stats_fn:
            self._rag_stats_getter = rag_stats_fn

    def record_latency(self, metric_name: str, value_ms: float):
        if value_ms < 0:
            return
        with self._lock:
            if metric_name not in self._latencies:
                self._latencies[metric_name] = deque(maxlen=500)
            self._latencies[metric_name].append(round(float(value_ms), 3))

    def record_command_outcome(self, state: str):
        with self._lock:
            self._command_counts[state] += 1

    def set_integration_health(self, name: str, status: str, detail: str = ""):
        with self._lock:
            self._integrations_health[name] = {
                "status": status,  # HEALTHY, DEGRADED, UNAVAILABLE, AUTH_REQUIRED, UNKNOWN
                "detail": detail[:200],
                "updated_at": time.time(),
            }

    def set_threshold(self, key: str, value: float):
        if key in self._thresholds:
            self._thresholds[key] = float(value)

    @staticmethod
    def _percentiles(values: List[float]) -> Dict[str, Any]:
        if not values:
            return {"count": 0, "p50": None, "p95": None, "p99": None, "max": None}
        s = sorted(values)
        n = len(s)

        def pct(p: float) -> float:
            idx = min(n - 1, max(0, int(math.ceil((p / 100.0) * n)) - 1))
            return round(s[idx], 2)

        return {
            "count": n,
            "p50": pct(50),
            "p95": pct(95),
            "p99": pct(99),
            "max": round(s[-1], 2),
        }

    def get_snapshot(self, service_filter: Optional[str] = None) -> Dict[str, Any]:
        """Collecte l'instantané complet (sans données conversationnelles ni secrets)."""
        sys_metrics = self.telemetry.sample()
        with self._lock:
            lat_summary = {
                k: self._percentiles(list(v))
                for k, v in self._latencies.items()
                if not service_filter or service_filter.lower() in k.lower()
            }
            cmd_stats = dict(self._command_counts)
            total_done = cmd_stats.get("SUCCEEDED", 0) + cmd_stats.get("FAILED", 0)
            fail_rate = round((cmd_stats.get("FAILED", 0) / total_done) * 100.0, 2) if total_done > 0 else 0.0
            succ_rate = round((cmd_stats.get("SUCCEEDED", 0) / total_done) * 100.0, 2) if total_done > 0 else 100.0

            integrations = {
                k: v for k, v in self._integrations_health.items()
                if not service_filter or service_filter.lower() in k.lower()
            }
            alerts = []
            if sys_metrics["cpu_percent"] > self._thresholds["cpu_percent"]:
                alerts.append({"level": "WARN", "metric": "cpu_percent", "value": sys_metrics["cpu_percent"]})
            if sys_metrics["ram_percent"] > self._thresholds["ram_percent"]:
                alerts.append({"level": "WARN", "metric": "ram_percent", "value": sys_metrics["ram_percent"]})
            if sys_metrics["disk_percent"] > self._thresholds["disk_percent"]:
                alerts.append({"level": "CRITICAL", "metric": "disk_percent", "value": sys_metrics["disk_percent"]})
            if total_done >= 5 and fail_rate > self._thresholds["failure_rate_percent"]:
                alerts.append({"level": "WARN", "metric": "failure_rate_percent", "value": fail_rate})

            snap = {
                "timestamp": time.time(),
                "uptime_seconds": round(time.time() - self.start_time, 1),
                "system": sys_metrics,
                "websocket": {"connected_clients": int(self._ws_clients_getter())},
                "commands": {
                    "counts": cmd_stats,
                    "success_rate_percent": succ_rate,
                    "failure_rate_percent": fail_rate,
                },
                "latencies": lat_summary,
                "jobs_queue": self._jobs_depth_getter(),
                "rag": self._rag_stats_getter(),
                "integrations": integrations,
                "alerts": alerts,
                "thresholds": dict(self._thresholds),
            }
            self._history.append({
                "timestamp": snap["timestamp"],
                "cpu_percent": sys_metrics["cpu_percent"],
                "ram_percent": sys_metrics["ram_percent"],
                "failure_rate": fail_rate,
                "alerts_count": len(alerts),
            })
        return snap

    def get_authorized_dashboard(self, principal: UserPrincipal, service_filter: Optional[str] = None) -> Dict[str, Any]:
        """Exige impérativement un rôle OWNER ou ADMIN (sécurité ops:dashboard)."""
        ok, reason = RBAC.authorize(principal, "ops", "dashboard")
        if not ok:
            return {"authorized": False, "status": "FORBIDDEN", "error": reason}
        snap = self.get_snapshot(service_filter=service_filter)
        with self._lock:
            snap["history"] = list(self._history)[-30:]
        snap["authorized"] = True
        return snap

    def export_authorized(self, principal: UserPrincipal, fmt: str = "json") -> Dict[str, Any]:
        """Export contrôlé des métriques (rôle OWNER/ADMIN uniquement)."""
        ok, reason = RBAC.authorize(principal, "ops", "export")
        if not ok:
            return {"authorized": False, "status": "FORBIDDEN", "error": reason}
        snap = self.get_snapshot()
        with self._lock:
            snap["history"] = list(self._history)
        if fmt == "json":
            return {"authorized": True, "format": "json", "payload": json.dumps(snap, ensure_ascii=False, indent=2)}
        return {"authorized": True, "format": "dict", "payload": snap}

    def run_self_diagnostic(self) -> Dict[str, Any]:
        """Diagnostic non destructif pour remplacer l'ancien diagnostic_pc() dépendant de psutil."""
        sys_m = self.telemetry.sample()
        cpu = sys_m["cpu_percent"]
        ram = sys_m["ram_percent"]
        disk = sys_m["disk_percent"]
        issues = []
        if cpu > self._thresholds["cpu_percent"]:
            issues.append(f"CPU élevé ({cpu}%)")
        if ram > self._thresholds["ram_percent"]:
            issues.append(f"RAM critique ({ram}%)")
        if disk > self._thresholds["disk_percent"]:
            issues.append(f"Disque presque plein ({disk}%)")
        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "status": "ALERTE" if issues else "OK",
            "details": " ; ".join(issues) if issues else "Système sain.",
        }


OBSERVABILITY = ObservabilityRegistry()
