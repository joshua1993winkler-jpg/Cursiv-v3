"""
Strand Store — persistent Strand archive.

Every anchored exchange, high-quality council synthesis, or human-rated
response becomes a Strand: a versioned, territory-tagged atom of
compounding personal memory that persists across all sessions.

Unlike session logs (ephemeral, per-day JSONL), Strands are permanent,
retrievable by semantic similarity, and feed directly into the LoRA
training queue as the highest-quality signal source.

Uses the existing core/strand.py codec — no new dependencies.
Similarity search mirrors council_memory.py (Jaccard + recency decay)
for architectural consistency.

Storage:
  .cursiv/strands.jsonl      — one JSON line per strand
  .cursiv/territories.json   — user-owned territory definitions (human-editable)
"""
from __future__ import annotations

import json
import math
import re
import time
import uuid
from pathlib import Path
from typing import Any

from cursiv_v215.core.strand import encode as _strand_encode

ROOT              = Path(__file__).parent.parent.parent
CURSIV_DIR        = ROOT / ".cursiv"
STRANDS_FILE      = CURSIV_DIR / "strands.jsonl"
TERRITORIES_FILE  = CURSIV_DIR / "territories.json"

_DEFAULT_TERRITORIES: dict[str, dict] = {
    "coding":       {"description": "Software builds, Codex sessions, architecture decisions"},
    "recovery":     {"description": "Health protocols, grounding, stop-stabilize-rebuild"},
    "architecture": {"description": "System design, Cursiv evolution, infrastructure bets"},
    "creative":     {"description": "FunForge spikes, music theory, novel ideas"},
    "worldmodel":   {"description": "Research, council insights, external observations"},
    "general":      {"description": "Uncategorized strands — default territory"},
}

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of", "and",
    "or", "but", "for", "with", "this", "that", "what", "how", "why",
    "when", "where", "who", "can", "do", "did", "be", "was", "are",
    "not", "no", "yes", "i", "you", "we", "they", "he", "she",
    "my", "your", "their", "its", "me", "him", "her", "us",
})


# ── Internal helpers ────────────────────────────────────────────────────────

def _tokenize(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return frozenset(w for w in words if w not in _STOPWORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _decay(timestamp: float, half_life_days: float = 30.0) -> float:
    hours = (time.time() - timestamp) / 3600
    half_life_h = half_life_days * 24
    return math.exp(-math.log(2) * hours / half_life_h)


def _load_all() -> list[dict[str, Any]]:
    if not STRANDS_FILE.exists():
        return []
    strands: list[dict] = []
    try:
        with STRANDS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        strands.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return strands


# ── Territories ─────────────────────────────────────────────────────────────

def load_territories() -> dict[str, dict]:
    """Load user territory definitions, creating defaults on first run."""
    if TERRITORIES_FILE.exists():
        try:
            return json.loads(TERRITORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    _write_default_territories()
    return _DEFAULT_TERRITORIES.copy()


def _write_default_territories() -> None:
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    TERRITORIES_FILE.write_text(
        json.dumps(_DEFAULT_TERRITORIES, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Core API ─────────────────────────────────────────────────────────────────

def save_strand(
    query: str,
    synthesis: str,
    *,
    tags: list[str] | None = None,
    score: float = 0.70,
    territory_tag: str = "general",
    source: str = "anchor",
    model: str = "unknown",
) -> str:
    """Encode and persist a Strand. Returns the 8-char strand_id."""
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    strand_id = str(uuid.uuid4())[:8]
    knowledge = {
        "query":     query,
        "synthesis": synthesis,
        "territory": territory_tag,
    }
    encoded = _strand_encode(knowledge)

    entry: dict[str, Any] = {
        "id":            strand_id,
        "strand":        encoded,
        "query":         query.strip()[:500],
        "synthesis":     synthesis.strip()[:1000],
        "tags":          tags or [],
        "score":         round(float(score), 3),
        "timestamp":     time.time(),
        "territory_tag": territory_tag,
        "source":        source,
        "model":         model,
    }
    with STRANDS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return strand_id


def get_strand(strand_id: str) -> dict[str, Any] | None:
    for s in _load_all():
        if s.get("id") == strand_id:
            return s
    return None


def list_strands(
    territory: str | None = None,
    min_score: float = 0.0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return strands most-recent-first, optionally filtered by territory and score."""
    all_s = _load_all()
    if territory:
        all_s = [s for s in all_s if s.get("territory_tag") == territory]
    if min_score > 0:
        all_s = [s for s in all_s if s.get("score", 0) >= min_score]
    all_s.sort(key=lambda s: s.get("timestamp", 0), reverse=True)
    return all_s[:limit]


def search_strands(
    query: str,
    top_k: int = 3,
    min_score: float = 0.10,
) -> list[dict[str, Any]]:
    """Jaccard + recency-decay semantic search. No external deps."""
    q_tokens = _tokenize(query)
    scored: list[tuple[float, dict]] = []
    for s in _load_all():
        e_tokens = _tokenize(s.get("query", "") + " " + s.get("synthesis", ""))
        sim      = _jaccard(q_tokens, e_tokens)
        decay    = _decay(s.get("timestamp", 0))
        combined = 0.70 * sim + 0.30 * decay
        if combined >= min_score:
            scored.append((combined, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_k]]


def strand_count() -> int:
    return len(_load_all())


def territory_counts() -> dict[str, int]:
    """Return strand count per territory."""
    counts: dict[str, int] = {}
    for s in _load_all():
        t = s.get("territory_tag", "general")
        counts[t] = counts.get(t, 0) + 1
    return counts


# ── Display ──────────────────────────────────────────────────────────────────

def format_strand_list(strands: list[dict[str, Any]]) -> str:
    if not strands:
        return "  No strands found."
    lines = []
    for s in strands:
        age_h   = (time.time() - s.get("timestamp", 0)) / 3600
        age_str = f"{int(age_h)}h ago" if age_h < 48 else f"{int(age_h / 24)}d ago"
        src     = s.get("source", "?")
        terr    = s.get("territory_tag", "general")
        sc      = s.get("score", 0)
        lines.append(
            f"  [{s.get('id','?')}]  {terr:<13} score:{sc:.2f}  {src:<14}  {age_str}\n"
            f"    {s.get('query','')[:72]}"
        )
    return "\n".join(lines)
