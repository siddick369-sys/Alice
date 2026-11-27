#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 24 — LONG-RUNNING JOBS (ALICE-AUTO-024, Wave 5).
File persistante SQLite isolée par utilisateur :
QUEUED -> RUNNING -> SUCCEEDED / FAILED / CANCELLED / UNKNOWN.
Gère idempotence, limite de concurrence, timeout, backoff exponentiel,
reprise sûre après redémarrage, RBAC à l'exécution et push post-confirmation.
"""

import os
import json
import time
import uuid
import sqlite3
import asyncio
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Callable, Awaitable
from alice_core.security.rbac import RBAC
from alice_core.ops.observability import OBSERVABILITY


JOB_QUEUED = "QUEUED"
JOB_RUNNING = "RUNNING"
JOB_SUCCEEDED = "SUCCEEDED"
JOB_FAILED = "FAILED"
JOB_CANCELLED = "CANCELLED"
JOB_UNKNOWN = "UNKNOWN"


class PersistentJobManager:
    """Gestionnaire de tâches asynchrones persistantes avec récupération après crash."""

    def __init__(self, db_path: Optional[str] = None, max_concurrency: int = 3):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = db_path or os.path.join(base_dir, "alice_outputs", "jobs_store.db")
        self.max_concurrency = max_concurrency
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any], Callable[[int], None]], Awaitable[Any]]] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._push_notifier: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
        self._init_db()

    @contextmanager
    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT,
                    owner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    required_action TEXT,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 1,
                    timeout_seconds REAL NOT NULL DEFAULT 30.0,
                    idempotent_retryable INTEGER NOT NULL DEFAULT 1,
                    result_json TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def register_handler(self, job_type: str, handler_fn):
        self._handlers[job_type] = handler_fn

    def set_push_notifier(self, fn: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        self._push_notifier = fn

    def recover_interrupted_jobs(self) -> Dict[str, int]:
        """
        À la reprise après redémarrage :
        - Si idempotent_retryable == 1 -> repasse en QUEUED
        - Sinon (effet externe incertain) -> bascule en UNKNOWN
        """
        now = time.time()
        requeued = 0
        marked_unknown = 0
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT job_id, idempotent_retryable FROM jobs WHERE status = ?", (JOB_RUNNING,)).fetchall()
            for r in rows:
                if r["idempotent_retryable"]:
                    conn.execute(
                        "UPDATE jobs SET status = ?, updated_at = ?, error = ? WHERE job_id = ?",
                        (JOB_QUEUED, now, "Récupéré après arrêt serveur : remis en file.", r["job_id"]),
                    )
                    requeued += 1
                else:
                    conn.execute(
                        "UPDATE jobs SET status = ?, updated_at = ?, error = ? WHERE job_id = ?",
                        (JOB_UNKNOWN, now, "Interruption serveur pendant opération non idempotente.", r["job_id"]),
                    )
                    marked_unknown += 1
            conn.commit()
        return {"requeued": requeued, "marked_unknown": marked_unknown}

    def enqueue(
        self,
        owner_id: str,
        session_id: str,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        required_action: Optional[str] = None,
        max_retries: int = 1,
        timeout_seconds: float = 30.0,
        idempotent_retryable: bool = True,
    ) -> Dict[str, Any]:
        now = time.time()
        with self._lock, self._connect() as conn:
            if idempotency_key:
                existing = conn.execute(
                    "SELECT * FROM jobs WHERE owner_id = ? AND idempotency_key = ? AND status IN (?, ?, ?)",
                    (owner_id, idempotency_key, JOB_QUEUED, JOB_RUNNING, JOB_SUCCEEDED),
                ).fetchone()
                if existing:
                    return self._row_to_dict(existing)

            job_id = f"job_{int(now * 1000)}_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, idempotency_key, owner_id, session_id, job_type,
                    required_action, payload_json, status, progress, attempts,
                    max_retries, timeout_seconds, idempotent_retryable, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, idempotency_key, owner_id, session_id, job_type,
                    required_action, json.dumps(payload, ensure_ascii=False),
                    JOB_QUEUED, max_retries, timeout_seconds,
                    1 if idempotent_retryable else 0, now, now
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_dict(row)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["payload"] = json.loads(d.pop("payload_json", "{}"))
        res_raw = d.pop("result_json", None)
        d["result"] = json.loads(res_raw) if res_raw else None
        return d

    def get_job(self, job_id: str, requester_owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not row:
                return None
            if requester_owner_id and row["owner_id"] != requester_owner_id and requester_owner_id != "owner_local":
                raise PermissionError("Isolation utilisateur : ce job appartient à un autre compte.")
            return self._row_to_dict(row)

    def _update_job(self, job_id: str, **fields):
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [job_id]
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {cols} WHERE job_id = ?", vals)
            conn.commit()

    def cancel_job(self, job_id: str, owner_id: str) -> Dict[str, Any]:
        job = self.get_job(job_id, requester_owner_id=owner_id)
        if not job:
            raise KeyError("Job introuvable.")
        if job["status"] in (JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED):
            return job
        task = self._running_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        self._update_job(job_id, status=JOB_CANCELLED, error="Annulé par l'utilisateur.")
        return self.get_job(job_id)

    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """Exécute un job avec contrôle RBAC dynamique, timeout, backoff et push post-confirmation."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)

        job = self.get_job(job_id)
        if not job:
            raise KeyError(f"Job inconnu : {job_id}")
        if job["status"] == JOB_CANCELLED:
            return job

        # Vérification des permissions RBAC au moment effectif de l'exécution
        if job.get("required_action"):
            ok, reason = RBAC.check_action(job["session_id"], job["required_action"], context=job["payload"])
            if not ok:
                self._update_job(job_id, status=JOB_FAILED, error=f"RBAC refusé à l'exécution : {reason}")
                return self.get_job(job_id)

        handler = self._handlers.get(job["job_type"])
        if not handler:
            self._update_job(job_id, status=JOB_FAILED, error=f"Aucun handler pour '{job['job_type']}'")
            return self.get_job(job_id)

        def _set_progress(pct: int):
            self._update_job(job_id, progress=max(0, min(100, int(pct))))

        async with self._semaphore:
            max_attempts = 1 + int(job.get("max_retries", 0))
            last_error = None
            for attempt in range(1, max_attempts + 1):
                cur = self.get_job(job_id)
                if cur["status"] == JOB_CANCELLED:
                    return cur

                self._update_job(job_id, status=JOB_RUNNING, attempts=attempt)
                try:
                    t0 = time.perf_counter()
                    coro = handler(job["payload"], _set_progress)
                    if asyncio.iscoroutine(coro):
                        res = await asyncio.wait_for(coro, timeout=float(job["timeout_seconds"]))
                    else:
                        res = coro

                    if isinstance(res, dict) and res.get("status") == "UNKNOWN":
                        self._update_job(job_id, status=JOB_UNKNOWN, result_json=json.dumps(res, ensure_ascii=False), error="Résultat externe non confirmé.")
                        final_job = self.get_job(job_id)
                        await self._notify_push(final_job)
                        return final_job

                    self._update_job(
                        job_id, status=JOB_SUCCEEDED, progress=100,
                        result_json=json.dumps(res, ensure_ascii=False), error=None
                    )
                    OBSERVABILITY.record_latency("job_execution_ms", (time.perf_counter() - t0) * 1000.0)
                    final_job = self.get_job(job_id)
                    await self._notify_push(final_job)
                    return final_job

                except asyncio.CancelledError:
                    self._update_job(job_id, status=JOB_CANCELLED, error="Exécution interrompue.")
                    return self.get_job(job_id)
                except asyncio.TimeoutError:
                    last_error = f"Timeout dépassé ({job['timeout_seconds']}s)."
                except Exception as e:
                    last_error = str(e)

                if attempt < max_attempts:
                    # Backoff exponentiel borné (0.1s, 0.2s, 0.4s...)
                    await asyncio.sleep(min(2.0, 0.1 * (2 ** (attempt - 1))))

            self._update_job(job_id, status=JOB_FAILED, error=last_error)
            final_job = self.get_job(job_id)
            await self._notify_push(final_job)
            return final_job

    async def _notify_push(self, job: Dict[str, Any]):
        """N'émet une notification mobile qu'après confirmation du statut réel terminal."""
        if self._push_notifier and job["status"] in (JOB_SUCCEEDED, JOB_FAILED, JOB_UNKNOWN):
            try:
                await self._push_notifier(job["session_id"], {
                    "type": "job_notification",
                    "job_id": job["job_id"],
                    "job_type": job["job_type"],
                    "status": job["status"],
                    "progress": job["progress"],
                    "error": job.get("error"),
                })
            except Exception:
                pass

    def cleanup_old_jobs(self, max_age_seconds: float = 86400.0 * 7) -> int:
        cutoff = time.time() - max_age_seconds
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM jobs WHERE status IN (?, ?, ?, ?) AND updated_at < ?",
                (JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED, JOB_UNKNOWN, cutoff),
            )
            conn.commit()
            return cur.rowcount

    def get_queue_stats(self) -> Dict[str, int]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status").fetchall()
            stats = {r["status"]: r["cnt"] for r in rows}
            return {
                "queued": stats.get(JOB_QUEUED, 0),
                "running": stats.get(JOB_RUNNING, 0),
                "succeeded": stats.get(JOB_SUCCEEDED, 0),
                "failed": stats.get(JOB_FAILED, 0),
                "unknown": stats.get(JOB_UNKNOWN, 0),
            }


JOB_MANAGER = PersistentJobManager()
