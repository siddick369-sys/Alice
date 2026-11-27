#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 13 — HOT-FOLDER WATCHDOG (ALICE-MEM-013, Wave 2).
Surveille un dossier documentaire local (PDF, XLSX, DOCX, MD, EPUB),
vérifie la stabilité du fichier avant lecture, déduplique par SHA-256,
traite les gros fichiers via une file asynchrone et synchronise les suppressions.
"""

import os
import time
import asyncio
import hashlib
import threading
from collections import deque
from typing import Dict, Any, Optional, Set
from alice_rag import RAG_ENGINE, AliceRAGEngine
from alice_core.ops.observability import OBSERVABILITY


class HotFolderWatchdog:
    """Surveillance sécurisée de dossier avec file pour fichiers volumineux."""

    TARGET_EXTS = {".pdf", ".xlsx", ".docx", ".md", ".txt", ".epub", ".csv"}

    def __init__(
        self,
        watch_dir: Optional[str] = None,
        rag_engine: Optional[AliceRAGEngine] = None,
        large_file_bytes: int = 512 * 1024,
        stability_delay: float = 0.15,
    ):
        self.rag = rag_engine or RAG_ENGINE
        self.watch_dir = os.path.realpath(watch_dir or self.rag.knowledge_dir)
        self.large_file_bytes = large_file_bytes
        self.stability_delay = stability_delay
        self._lock = threading.RLock()
        self._known_files: Dict[str, str] = {}  # realpath -> sha256
        self._file_status: Dict[str, Dict[str, Any]] = {}
        self.large_queue: deque = deque()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _is_safe_path(self, path: str) -> bool:
        try:
            real = os.path.realpath(path)
            return real.startswith(self.watch_dir + os.sep) or real == self.watch_dir
        except Exception:
            return False

    def _wait_stable(self, path: str) -> bool:
        """Vérifie que la taille du fichier est stabilisée avant lecture."""
        try:
            st1 = os.stat(path)
            if self.stability_delay > 0:
                time.sleep(self.stability_delay)
            st2 = os.stat(path)
            return (st1.st_size == st2.st_size) and (st1.st_mtime_ns == st2.st_mtime_ns)
        except OSError:
            return False

    def scan_once(self) -> Dict[str, Any]:
        """Effectue une passe de détection, déduplication, ingestion et nettoyage."""
        if not os.path.exists(self.watch_dir):
            return {"processed": 0, "queued_large": 0, "removed": 0, "skipped_dedup": 0}

        found_paths: Set[str] = set()
        processed = 0
        queued_large = 0
        skipped_dedup = 0

        for root, _, files in os.walk(self.watch_dir):
            for fname in files:
                if fname.startswith("rag_index") or fname.endswith(".tmp"):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.TARGET_EXTS:
                    continue
                fpath = os.path.realpath(os.path.join(root, fname))
                if not self._is_safe_path(fpath):
                    continue
                found_paths.add(fpath)

        # Détecter suppressions et nettoyer l'index
        removed = 0
        with self._lock:
            deleted = [p for p in list(self._known_files.keys()) if p not in found_paths]
            for dpath in deleted:
                self._known_files.pop(dpath, None)
                self._file_status[dpath] = {"status": "DELETED", "updated_at": time.time()}
                self.rag.remove_document(dpath)
                removed += 1

        # Traiter nouveaux fichiers ou modifiés
        for fpath in sorted(found_paths):
            if not self._wait_stable(fpath):
                self._file_status[fpath] = {"status": "UNSTABLE_DEFERRED", "updated_at": time.time()}
                continue
            try:
                fhash = self.rag._compute_hash(fpath)
                with self._lock:
                    if self._known_files.get(fpath) == fhash:
                        skipped_dedup += 1
                        continue

                size = os.path.getsize(fpath)
                if size > self.large_file_bytes:
                    with self._lock:
                        if fpath not in self.large_queue:
                            self.large_queue.append(fpath)
                            self._file_status[fpath] = {"status": "QUEUED_LARGE", "size": size, "updated_at": time.time()}
                            queued_large += 1
                    continue

                t0 = time.perf_counter()
                res = self.rag.ingest_file(fpath, owner_id="shared", visibility="shared")
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                OBSERVABILITY.record_latency("rag_index_ms", elapsed_ms)

                with self._lock:
                    self._known_files[fpath] = fhash
                    self._file_status[fpath] = {
                        "status": "INDEXED" if res.get("success") else "ERROR",
                        "chunks": res.get("chunks", 0),
                        "latency_ms": elapsed_ms,
                        "updated_at": time.time(),
                    }
                processed += 1
            except Exception as e:
                with self._lock:
                    self._file_status[fpath] = {"status": "ERROR", "error": str(e), "updated_at": time.time()}

        return {
            "processed": processed,
            "queued_large": queued_large,
            "removed": removed,
            "skipped_dedup": skipped_dedup,
        }

    def process_large_queue_step(self) -> Optional[Dict[str, Any]]:
        """Traite un document volumineux en attente dans la file dédiée."""
        with self._lock:
            if not self.large_queue:
                return None
            fpath = self.large_queue.popleft()
        if not os.path.exists(fpath) or not self._is_safe_path(fpath):
            return {"status": "MISSING_OR_UNSAFE", "path": fpath}
        t0 = time.perf_counter()
        res = self.rag.ingest_file(fpath, owner_id="shared", visibility="shared")
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        fhash = self.rag._compute_hash(fpath)
        with self._lock:
            self._known_files[fpath] = fhash
            self._file_status[fpath] = {
                "status": "INDEXED_LARGE" if res.get("success") else "ERROR",
                "chunks": res.get("chunks", 0),
                "latency_ms": elapsed_ms,
                "updated_at": time.time(),
            }
        return self._file_status[fpath]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "watch_dir": self.watch_dir,
                "tracked_files": len(self._known_files),
                "large_queue_len": len(self.large_queue),
                "files": dict(self._file_status),
            }

    def start(self, interval: float = 2.0):
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                try:
                    self.scan_once()
                    self.process_large_queue_step()
                except Exception:
                    pass
                time.sleep(interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.5)


HOT_FOLDER_WATCHDOG = HotFolderWatchdog()
