"""
Reference Brain — Offline knowledge lookup (zero model required)

Taps the 382MB SQLite knowledge base from Winkler_Codex_AI:
  - Webster dictionary definitions
  - Thesaurus / wording alternatives
  - Survival field knowledge
  - Medical field notes
  - Science & factbook data

No LLM needed. Pure SQLite. Always available offline.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

_CURSIV_ROOT = Path(__file__).resolve().parent.parent.parent

_CODEX_ROOT: Optional[Path] = None
for _candidate in [
    Path(os.environ["CURSIV_CODEX_PATH"]) if os.environ.get("CURSIV_CODEX_PATH") else None,
    _CURSIV_ROOT.parent / "Winkler_Codex_AI",
]:
    if _candidate and (_candidate / "Wrapped-System" / "knowledge_brain.py").exists():
        _CODEX_ROOT = _candidate
        break

_AVAILABLE = False
_brain: Any = None

if _CODEX_ROOT:
    _wrapped_path = str(_CODEX_ROOT / "Wrapped-System")
    if _wrapped_path not in sys.path:
        sys.path.insert(0, _wrapped_path)
    try:
        from knowledge_brain import ReferenceBrain  # type: ignore
        _db = _CODEX_ROOT / "Wrapped-System" / "data" / "reference_brain.sqlite"
        _brain = ReferenceBrain(db_path=str(_db))
        _AVAILABLE = _db.exists()
    except Exception:
        pass


def is_available() -> bool:
    return _AVAILABLE


def search(query: str, limit: int = 6) -> str:
    """
    Search the local reference brain. Returns formatted results as a string.
    Covers: dictionary, thesaurus, survival, medical, science, factbook.
    No model or internet needed.
    """
    if not _AVAILABLE or _brain is None:
        return "[Reference Brain unavailable — SQLite not found or Codex system not installed]"
    if not query or not query.strip():
        return "[Reference Brain] No query provided."
    try:
        result = _brain.context_block(query.strip(), limit=limit)
        if not result:
            return f"[Reference Brain] No results found for: {query}"
        return f"[Reference Brain — offline]\n{result}"
    except Exception as e:
        return f"[Reference Brain error: {e}]"


def answer(query: str) -> str:
    """Full grounded answer with intent classification (define / medical / survival / general)."""
    if not _AVAILABLE or _brain is None:
        return "[Reference Brain unavailable]"
    try:
        result = _brain.answer_from_references(query.strip())
        return result if result else f"[Reference Brain] No results for: {query}"
    except Exception as e:
        return f"[Reference Brain error: {e}]"


def status() -> dict[str, Any]:
    base: dict[str, Any] = {"available": _AVAILABLE}
    if not _AVAILABLE:
        return {**base, "path": str(_CODEX_ROOT) if _CODEX_ROOT else "not found"}
    try:
        return {**base, **_brain.status()}
    except Exception as e:
        return {**base, "error": str(e)}
