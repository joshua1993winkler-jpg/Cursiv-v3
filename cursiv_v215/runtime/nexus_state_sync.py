"""
Evolutionary Runtime — Nexus state sync.
Keeps nexus_state.json up to date with evolution metrics so the Nexus UI
and chat_app can surface live status without importing runtime modules directly.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .config import CURSIV_DIR
from . import metrics

log = logging.getLogger("cursiv.sync")

NEXUS_STATE_PATH = CURSIV_DIR / "nexus_state.json"


def push_evo_status() -> None:
    """Write evolution metrics into nexus_state.json (merge, not overwrite)."""
    report = metrics.full_report()

    state = _load()
    state["evolution"] = {
        "updated_at":    datetime.now().isoformat(),
        "counts":        report["counts"],
        "storage":       report["storage"],
        "wisdom":        report["wisdom"],
        "drift":         report["drift"],
        "drift_direction": report["drift_direction"],
    }
    _save(state)
    log.debug("[Sync] nexus_state.json updated with evo metrics")


def read_evo_status() -> dict:
    """Read back the evolution section from nexus_state.json."""
    return _load().get("evolution", {})


def push_wisdom_preview(n: int = 5) -> None:
    """Inject the top-N wisdom entries into nexus_state for the chat UI."""
    from . import db
    entries = db.get_wisdom(limit=n)
    state   = _load()
    state.setdefault("evolution", {})["wisdom_preview"] = [
        {"text": e["text"], "quality": e["quality_score"]}
        for e in entries
    ]
    _save(state)


def push_pending_deltas() -> None:
    """Sync count of pending approval deltas into nexus_state."""
    from . import db
    pending = db.get_pending_deltas()
    state   = _load()
    state.setdefault("evolution", {})["pending_deltas"] = len(pending)
    _save(state)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if NEXUS_STATE_PATH.exists():
        try:
            return json.loads(NEXUS_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(state: dict) -> None:
    NEXUS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEXUS_STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
