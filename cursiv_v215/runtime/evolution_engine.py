"""
Evolutionary Runtime — evolution engine.
Orchestrates the full Capture → Compress → Evolve → Prune cycle.

Cycle steps:
  1. Capture   — ingest new session exchanges via session_bridge
  2. Compress  — embed any un-embedded summaries
  3. Evolve    — cluster embeddings, generate delta proposals
  4. Prune     — enforce retention and storage caps
  5. Metrics   — snapshot health data
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import config
from . import db
from .session_bridge import ingest_all
from .embedder import embed_pending_summaries
from .pattern_detector import detect_patterns
from .delta_generator import generate_deltas, save_deltas
from .pruner import run_prune, enforce_storage_cap
from . import metrics

log = logging.getLogger("cursiv.engine")


class CycleResult:
    def __init__(self):
        self.started_at:    str   = datetime.now().isoformat()
        self.finished_at:   str   = ""
        self.ingested:      int   = 0
        self.embedded:      int   = 0
        self.clusters:      int   = 0
        self.deltas:        int   = 0
        self.wisdom_added:  int   = 0
        self.pruned:        int   = 0
        self.error:         Optional[str] = None

    def finish(self):
        self.finished_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    def __repr__(self):
        return (
            f"<CycleResult ingested={self.ingested} embedded={self.embedded} "
            f"clusters={self.clusters} deltas={self.deltas} "
            f"wisdom={self.wisdom_added} pruned={self.pruned}>"
        )


def run_cycle(
    dry_run_prune: bool = False,
    max_ingest_files: int = 30,
) -> CycleResult:
    """
    Execute one full evolution cycle. Returns a CycleResult.
    Failures in individual steps are caught and logged; the cycle continues.
    """
    db.init_db()
    result = CycleResult()
    log.info("[Engine] ── Evolution cycle starting ──")

    # ── Step 1: Capture ────────────────────────────────────────────────────────
    try:
        ingest = ingest_all(max_files=max_ingest_files)
        result.ingested     = ingest.get("new_interactions", 0)
        result.wisdom_added = ingest.get("wisdom_added", 0)
        log.info(f"[Engine] Capture: {result.ingested} new interactions, "
                 f"{result.wisdom_added} wisdom entries")
    except Exception as e:
        log.error(f"[Engine] Capture failed: {e}")
        result.error = f"capture: {e}"

    # ── Step 2: Compress ───────────────────────────────────────────────────────
    try:
        result.embedded = embed_pending_summaries(batch_size=100)
        log.info(f"[Engine] Compress: {result.embedded} summaries embedded")
    except Exception as e:
        log.error(f"[Engine] Compress failed: {e}")

    # ── Step 3: Evolve ─────────────────────────────────────────────────────────
    try:
        clusters = detect_patterns(min_quality=config.min_quality_score)
        result.clusters = len(clusters)
        if clusters:
            deltas = generate_deltas(clusters)
            ids    = save_deltas(deltas)
            result.deltas = len(ids)
            log.info(f"[Engine] Evolve: {result.clusters} clusters → {result.deltas} delta proposals")
        else:
            log.info("[Engine] Evolve: no clusters detected — skipping delta generation")
    except Exception as e:
        log.error(f"[Engine] Evolve failed: {e}")

    # ── Step 4: Prune ──────────────────────────────────────────────────────────
    try:
        prune_result = run_prune(dry_run=dry_run_prune)
        result.pruned = (
            prune_result.get("low_quality_deleted", 0) +
            prune_result.get("high_quality_deleted", 0)
        )
        enforce_storage_cap()
        log.info(f"[Engine] Prune: {result.pruned} summaries removed")
    except Exception as e:
        log.error(f"[Engine] Prune failed: {e}")

    # ── Step 5: Metrics ────────────────────────────────────────────────────────
    try:
        storage = metrics.storage_health()
        metrics.record_cycle(
            ingested         = result.ingested,
            embedded         = result.embedded,
            clusters_found   = result.clusters,
            deltas_generated = result.deltas,
            wisdom_added     = result.wisdom_added,
            pruned           = result.pruned,
            db_size_bytes    = storage["db_size_bytes"],
        )
        drift = metrics.quality_drift()
        if drift is not None:
            metrics.record_value("quality_drift", drift)
    except Exception as e:
        log.error(f"[Engine] Metrics snapshot failed: {e}")

    result.finish()
    elapsed = _elapsed(result.started_at, result.finished_at)
    log.info(
        f"[Engine] ── Cycle complete in {elapsed}s · "
        f"ingested={result.ingested} deltas={result.deltas} pruned={result.pruned} ──"
    )
    return result


def run_cycle_safe(**kwargs) -> CycleResult:
    """Wrapper that guarantees a CycleResult even on unhandled exception."""
    try:
        return run_cycle(**kwargs)
    except Exception as e:
        log.critical(f"[Engine] Unhandled cycle failure: {e}", exc_info=True)
        r = CycleResult()
        r.error = str(e)
        r.finish()
        return r


def _elapsed(start: str, end: str) -> str:
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        return str(round((e - s).total_seconds(), 2))
    except Exception:
        return "?"
