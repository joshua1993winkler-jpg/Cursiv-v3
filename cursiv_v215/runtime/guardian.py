"""
Evolutionary Runtime — guardian.
Storage watchdog: enforces the DB size cap and sends alerts when approaching limit.
Runs as a lightweight check inside the scheduler, not its own process.
"""
from __future__ import annotations

import logging
from datetime import datetime

from .config import config
from . import db
from .pruner import enforce_storage_cap, run_prune
from . import metrics

log = logging.getLogger("cursiv.guardian")

_WARN_PCT  = 80   # log warning at 80% of budget
_ALERT_PCT = 90   # force prune at 90% of budget


def check(*, force_if_over_pct: float = _ALERT_PCT) -> dict:
    """
    Inspect storage health and act if necessary.
    Returns a report dict.
    """
    health = metrics.storage_health()
    pct    = health["used_pct"]
    report = {**health, "action": "none", "checked_at": datetime.now().isoformat()}

    if pct >= _ALERT_PCT:
        log.warning(
            f"[Guardian] Storage at {pct}% — forcing emergency prune "
            f"({health['db_size_mb']:.1f}/{health['budget_mb']} MB)"
        )
        taken = enforce_storage_cap()
        if taken:
            report["action"] = "emergency_prune"
            metrics.record_value("guardian_emergency_prune", 1.0,
                                 f"triggered at {pct}%")
        else:
            report["action"] = "emergency_prune_noop"

    elif pct >= _WARN_PCT:
        log.warning(
            f"[Guardian] Storage at {pct}% of budget — consider running prune soon"
        )
        report["action"] = "warned"
        metrics.record_value("guardian_warning", pct, f"{health['db_size_mb']:.1f} MB")

    # Trim wisdom ledger if over cap
    _enforce_wisdom_cap()

    return report


def _enforce_wisdom_cap() -> None:
    """Delete lowest-quality wisdom entries if over wisdom_max_entries."""
    with db.get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM wisdom_ledger").fetchone()[0]
        if count <= config.wisdom_max_entries:
            return

        excess = count - config.wisdom_max_entries
        conn.execute(
            "DELETE FROM wisdom_ledger WHERE id IN ("
            "SELECT id FROM wisdom_ledger ORDER BY quality_score ASC, id ASC LIMIT ?)",
            (excess,),
        )
        log.info(f"[Guardian] Trimmed {excess} low-quality wisdom entries (cap={config.wisdom_max_entries})")
        metrics.record_value("wisdom_trimmed", float(excess))
