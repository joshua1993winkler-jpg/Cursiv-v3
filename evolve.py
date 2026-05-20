"""
Cursiv System Evolver
=====================
Reads each core source file, sends it through the configured LLM with
evolution instructions, and writes the improved version to TARGET.

Usage:
  python evolve.py                          # defaults below
  python evolve.py <source> <target>        # explicit paths
  python evolve.py --list                   # show file queue, don't run
  python evolve.py --resume                 # skip files already in target

API keys are read from environment:
  XAI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
Falls back to Ollama if no keys are set.

Ctrl+C safely stops after the current file is written.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_SOURCE = Path(__file__).parent
DEFAULT_TARGET = Path(r"C:\Users\joshu\OneDrive\Desktop\TEST")

# ── Priority file list (processed first, in order) ───────────────────────────
# Add paths relative to source root.  Glob patterns supported (*).
PRIORITY_FILES = [
    "cursiv_v215/core/strand_store.py",
    "cursiv_v215/core/strand_federation.py",
    "cursiv_v215/core/strand.py",
    "cursiv_v215/core/web_cache.py",
    "cursiv_v215/core/constitution.py",
    "cursiv_v215/core/rate_limiter.py",
    "cursiv_v215/agents/babel_agent.py",
    "cursiv_v215/agents/voice_agent.py",
    "cursiv_v215/agents/codex_agent.py",
    "cursiv_v215/agents/offline_queue.py",
    "cursiv_v215/council/agents.py",
    "cursiv_v215/council/deliberation.py",
    "cursiv_v215/council/council_memory.py",
    "cursiv_v215/memory/session_log.py",
    "cursiv_v215/ui/chat_app.py",
    "cursiv_v215/ui/chat_cli.py",
    "cursiv_v215/forge/funforge_meta.py",
    "cursiv_v215/academy/engine.py",
    "cursiv_v215/academy/scorer.py",
    "cursiv_v215/__init__.py",
]

# Files to skip entirely (guardian internals, compiled, test data)
SKIP_PATTERNS = [
    "*/__pycache__/*",
    "*/guardian/temple_guardian.py",   # sovereign — do not touch
    "*/guardian/obfuscation.py",       # sovereign — do not touch
    "*/guardian/access_gate.py",       # sovereign — do not touch
    "*/guardian/decoys.py",            # sovereign — do not touch
    "*/weave/sovereign.py",            # sovereign — do not touch
    "*.pyc",
    ".git/*",
]

# ── Evolution system prompt ───────────────────────────────────────────────────
EVOLUTION_SYSTEM = """You are a senior systems architect evolving the Cursiv AI operating system to its next version.

You will receive one Python source file at a time. Rewrite it as a meaningfully improved version.

MANDATORY CONSTRAINTS (non-negotiable):
  - Constitutional invariants stay unchanged:
      system_owner = "Joshua Winkler"
      local_first = True
      privacy = "no_consciousness_upload"
      air_gap_capable = True
  - Guardian files are never modified (you will not receive them)
  - Ollama speaks first and last in all council sessions — preserve this
  - Every feature must degrade gracefully when offline — no hard cloud deps
  - Strand archive is permanent — no auto-delete logic ever

IMPROVEMENTS TO APPLY WHERE APPLICABLE:
  1. Add  __version__ = "4.0.0"  at module level if not present
  2. Replace Jaccard similarity with TF-IDF where similarity search is used
  3. Standardize agent interfaces: run(input) -> dict with keys
       output, confidence, source_model, latency_ms
  4. Add configurable parameters for any hardcoded thresholds
  5. Improve docstrings: one-line summary + Args/Returns where missing
  6. Replace bare except with typed except where intent is clear
  7. Add type annotations to all public functions
  8. Remove any circular imports — every agent must be importable standalone
  9. Auto-strand important outputs: council, session summaries, voice transcripts
  10. Training data export must support JSONL and Alpaca format where applicable

WHAT NOT TO DO:
  - Do not change the module's public API (function names, signatures callers depend on)
  - Do not add features that require new third-party packages without a try/except fallback
  - Do not rewrite logic that is working correctly — improve, don't replace
  - Do not add comments that just restate what the code does
  - Do not truncate or summarize the file — output the complete evolved module

Output ONLY the Python source code. No markdown fences, no explanation, no preamble."""

# ── ANSI palette ─────────────────────────────────────────────────────────────
GOLD  = "\033[38;5;220m"
LGOLD = "\033[38;5;136m"
GREEN = "\033[38;5;82m"
RED   = "\033[38;5;196m"
DIM   = "\033[2m"
RESET = "\033[0m"
BOLD  = "\033[1m"

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Force UTF-8 on Windows so box-drawing and ANSI work
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _cols() -> int:
    return max(shutil.get_terminal_size((100, 30)).columns, 60)


def _bar(label: str, current: int, total: int) -> str:
    w     = _cols() - 30
    pct   = current / max(total, 1)
    filled = int(pct * w)
    return (f"  {GOLD}[{current:>3}/{total}]{RESET}  "
            f"{GREEN}{'█' * filled}{DIM}{'░' * (w - filled)}{RESET}  "
            f"{label[:40]}")


# ── LLM call (streaming, no external deps) ───────────────────────────────────

def _call_anthropic(messages: list[dict], key: str) -> str:
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "system": messages[0]["content"] if messages[0]["role"] == "system" else "",
        "messages": [m for m in messages if m["role"] != "system"],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read())
    return body["content"][0]["text"]


def _call_xai(messages: list[dict], key: str) -> str:
    payload = json.dumps({
        "model": "grok-3",
        "max_tokens": 8192,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=payload,
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read())
    return body["choices"][0]["message"]["content"]


def _call_openai(messages: list[dict], key: str) -> str:
    payload = json.dumps({
        "model": "gpt-4.1",
        "max_tokens": 8192,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read())
    return body["choices"][0]["message"]["content"]


def _call_ollama(messages: list[dict]) -> str:
    payload = json.dumps({
        "model": "llama3.1",
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 8192},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.loads(r.read())
    return body["message"]["content"]


def _evolve_file(source_code: str, filename: str, provider: str, key: str) -> tuple[str, str]:
    """Send file to LLM for evolution. Returns (evolved_code, provider_used)."""
    messages = [
        {"role": "system", "content": EVOLUTION_SYSTEM},
        {"role": "user",   "content": f"# File: {filename}\n\n{source_code}"},
    ]
    if provider == "claude" and key:
        return _call_anthropic(messages, key), "Claude"
    if provider == "xai" and key:
        return _call_xai(messages, key), "xAI Grok"
    if provider == "openai" and key:
        return _call_openai(messages, key), "OpenAI"
    return _call_ollama(messages), "Ollama"


# ── File collection ───────────────────────────────────────────────────────────

def _should_skip(rel_path: str) -> bool:
    import fnmatch
    for pat in SKIP_PATTERNS:
        if fnmatch.fnmatch(rel_path.replace("\\", "/"), pat):
            return True
    return False


def _collect_files(source: Path) -> list[Path]:
    """Return ordered list: PRIORITY_FILES first, then remaining .py files."""
    seen   = set()
    result = []

    # Priority first
    for rel in PRIORITY_FILES:
        p = source / rel
        if p.exists():
            result.append(p)
            seen.add(p.resolve())

    # Remaining .py files
    for p in sorted(source.rglob("*.py")):
        if p.resolve() not in seen and not _should_skip(
            str(p.relative_to(source)).replace("\\", "/")
        ):
            result.append(p)
            seen.add(p.resolve())

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args      = sys.argv[1:]
    list_only = "--list" in args
    resume    = "--resume" in args
    args      = [a for a in args if not a.startswith("--")]

    source = Path(args[0]) if len(args) > 0 else DEFAULT_SOURCE
    target = Path(args[1]) if len(args) > 1 else DEFAULT_TARGET

    source = source.resolve()
    target = target.resolve()

    if not source.exists():
        print(f"{RED}Source not found: {source}{RESET}")
        sys.exit(1)

    # Detect provider
    ant_key = os.environ.get("ANTHROPIC_API_KEY", "")
    xai_key = os.environ.get("XAI_API_KEY", "")
    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if ant_key:
        provider, key, pname = "claude",  ant_key, "Claude"
    elif xai_key:
        provider, key, pname = "xai",     xai_key, "xAI Grok"
    elif oai_key:
        provider, key, pname = "openai",  oai_key, "OpenAI"
    else:
        provider, key, pname = "ollama",  "",      "Ollama (local)"

    files = _collect_files(source)

    w = _cols()
    print(f"\n{GOLD}{'═' * w}{RESET}")
    print(f"  {GOLD}{BOLD}CURSIV SYSTEM EVOLVER{RESET}")
    print(f"  {DIM}Source : {source}{RESET}")
    print(f"  {DIM}Target : {target}{RESET}")
    print(f"  {DIM}Model  : {pname}{RESET}")
    print(f"  {DIM}Files  : {len(files)}{RESET}")
    print(f"{GOLD}{'═' * w}{RESET}\n")

    if list_only:
        for i, f in enumerate(files, 1):
            rel = f.relative_to(source)
            print(f"  {LGOLD}{i:>3}.{RESET}  {rel}")
        return

    target.mkdir(parents=True, exist_ok=True)
    manifest_lines: list[str] = [
        "# Cursiv Evolution Manifest\n",
        f"Source: {source}\n",
        f"Target: {target}\n",
        f"Model:  {pname}\n\n",
        "| # | File | Status | Notes |\n",
        "|---|------|--------|-------|\n",
    ]

    written = 0
    skipped = 0
    errors  = 0

    try:
        for idx, src_path in enumerate(files, 1):
            rel        = src_path.relative_to(source)
            dest_path  = target / rel
            rel_str    = str(rel).replace("\\", "/")

            print(_bar(rel_str, idx, len(files)))

            if resume and dest_path.exists():
                print(f"  {DIM}  skip (already evolved){RESET}")
                manifest_lines.append(f"| {idx} | `{rel_str}` | SKIPPED | already in target |\n")
                skipped += 1
                continue

            try:
                source_code = src_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  {RED}  read error: {e}{RESET}")
                manifest_lines.append(f"| {idx} | `{rel_str}` | ERROR | read: {e} |\n")
                errors += 1
                continue

            print(f"  {LGOLD}  evolving via {pname}…{RESET}", end="", flush=True)
            t0 = time.time()
            try:
                evolved, used = _evolve_file(source_code, rel_str, provider, key)
            except Exception as e:
                print(f"\r  {RED}  failed: {e}{RESET}")
                manifest_lines.append(f"| {idx} | `{rel_str}` | ERROR | evolve: {e} |\n")
                errors += 1
                continue

            elapsed = time.time() - t0

            # Strip markdown fences if LLM wrapped the output
            evolved = re.sub(r"^```python\s*\n?", "", evolved.strip())
            evolved = re.sub(r"\n?```\s*$", "", evolved)

            # Write
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(evolved, encoding="utf-8")

            lines_orig   = source_code.count("\n")
            lines_evolved = evolved.count("\n")
            delta = lines_evolved - lines_orig
            delta_str = f"+{delta}" if delta >= 0 else str(delta)

            print(f"\r  {GREEN}  done{RESET}  {DIM}{lines_orig}→{lines_evolved} lines ({delta_str})  {elapsed:.1f}s  via {used}{RESET}")
            manifest_lines.append(
                f"| {idx} | `{rel_str}` | OK | {lines_orig}→{lines_evolved} lines, {elapsed:.1f}s |\n"
            )
            written += 1

    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Stopped by user — progress saved to target.{RESET}")

    # Write MANIFEST.md
    manifest_path = target / "MANIFEST.md"
    manifest_lines += [
        f"\n---\n",
        f"Written: {written}  Skipped: {skipped}  Errors: {errors}\n",
    ]
    manifest_path.write_text("".join(manifest_lines), encoding="utf-8")

    print(f"\n{GOLD}{'═' * _cols()}{RESET}")
    print(f"  {GREEN}Written : {written}{RESET}  "
          f"{DIM}Skipped: {skipped}  Errors: {errors}{RESET}")
    print(f"  {LGOLD}Manifest: {manifest_path}{RESET}")
    print(f"{GOLD}{'═' * _cols()}{RESET}\n")


if __name__ == "__main__":
    main()
