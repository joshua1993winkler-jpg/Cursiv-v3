"""
JW Main Chat — JWFrontierEvoCore Interactive Interface
Cursiv-v2.1.5 | http://localhost:7860

Black screen, rolling text, multimodal input (images, JSON, text, raw files).
xAI/Grok API key slot injects Grok intelligence into every conversation.
Reads live agent assignments from the Nexus panel (.cursiv/nexus_state.json).
Run the Nexus (port 7861) alongside to repurpose agents mid-conversation.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Generator

import gradio as gr

# ── Temple Guardian — front-end defense layer ──────────────────────────────
try:
    from cursiv_v215.guardian.temple_guardian import (
        scan as _guardian_scan,
        is_protected_path as _guardian_protected,
        SKULL_HTML as _SKULL_HTML,
    )
    from cursiv_v215.guardian.obfuscation import session_fingerprint as _sfp
    from cursiv_v215.guardian.decoys import get_decoy_response as _decoy_response
    _GUARDIAN_OK = True
except Exception:
    _GUARDIAN_OK = False
    def _guardian_scan(msg, sid="default"):  return (False, None)
    def _guardian_protected(p):             return False
    def _sfp():                             return "--------"
    def _decoy_response(sid="default"):     return ""
    _SKULL_HTML = ""

# Session ID — stable per process, rotates on every server restart
_GRADIO_SESSION_ID = f"gradio_{os.getpid()}"

# ── Obsidian Vault Sync ────────────────────────────────────────────────────
try:
    from cursiv_v215.obsidian.exporter import (
        load_config    as _obs_load_config,
        save_config    as _obs_save_config,
        export_today   as _obs_export,
        auto_export_if_enabled as _obs_auto_export,
        auto_detect_vault      as _obs_detect_vault,
        livestream_exchange    as _obs_livestream,
    )
    _OBS_OK = True
except Exception:
    _OBS_OK = False
    def _obs_load_config():              return {"enabled": False, "vault_path": ""}
    def _obs_save_config(e, p):          pass
    def _obs_export(vp, d=None):         return (False, "Obsidian module unavailable.")
    def _obs_auto_export():              return ""
    def _obs_detect_vault():             return ""
    def _obs_livestream(u, a, m=""):     pass

# ── Session Memory ─────────────────────────────────────────────────────────
try:
    from cursiv_v215.memory.session_log import (
        append_exchange   as _session_append,
        load_session_context as _load_session_ctx,
    )
    _SESSION_OK = True
except Exception:
    _SESSION_OK = False
    def _session_append(u, a, m="unknown"): pass
    def _load_session_ctx():                return ""

# ── Sovereign verification (passphrase split across 3 modules — no plaintext here) ──
import hashlib as _hl
try:
    from cursiv_v215.guardian.temple_guardian import _RING_CORE    as _RC
    from cursiv_v215.guardian.obfuscation     import _LATTICE_ROOT as _LR
    from cursiv_v215.weave.sovereign          import _WEAVE_SEAL   as _WS
    from cursiv_v215.guardian.temple_guardian import unlock_owner_session as _unlock_owner
    def _verify_sovereign(text: str) -> bool:
        try:
            return _hl.sha256(text.strip().encode()).hexdigest() == (_RC + _LR + _WS)
        except Exception:
            return False
except Exception:
    def _verify_sovereign(text: str) -> bool:
        return False
    def _unlock_owner(sid: str):
        pass

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT               = Path(__file__).parent.parent.parent
SYSTEM_PROMPT_FILE = ROOT / "cursiv_v215" / "codex" / "system_prompt.md"
NEXUS_STATE        = ROOT / ".cursiv" / "nexus_state.json"
MEMORY_FILE        = ROOT / ".cursiv" / "memory.json"
TRAINING_JSONL     = ROOT / ".cursiv" / "training_data.jsonl"

# ── xAI endpoint ───────────────────────────────────────────────────────────
XAI_URL        = "https://api.x.ai/v1/chat/completions"
XAI_MODEL      = "grok-3-latest"
XAI_MODEL_VIS  = "grok-2-vision-1212"   # vision-capable model for images
OLLAMA_URL         = "http://localhost:11434/api/generate"
OLLAMA_MODEL       = "mistral"

# ── OpenAI endpoint (Codex / code review) ──────────────────────────────────
OPENAI_URL         = "https://api.openai.com/v1/chat/completions"
OPENAI_CODE_MODEL  = "gpt-4.1"      # full code generation, not just review

# ── Anthropic / Claude endpoint ─────────────────────────────────────────────
ANTHROPIC_URL         = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION     = "2023-06-01"
ANTHROPIC_CODE_MODEL  = "claude-sonnet-4-6"   # code generation via Anthropic

# Sentinel that signals a write is pending user approval
WRITE_SENTINEL = "<<<PENDING_WRITE_JSON>>>"

# ── File tool definitions (xAI / OpenAI tool-call schema) ─────────────────
FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file. Use this before editing so you know what's there.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path, relative to workspace root or absolute."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating it or overwriting it completely. Always read_file first if editing an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "File path to write."},
                    "content": {"type": "string", "description": "Full content to write to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path. Defaults to workspace root."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a glob pattern (e.g. '**/*.py').",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern":   {"type": "string", "description": "Glob pattern."},
                    "directory": {"type": "string", "description": "Root directory to search from. Defaults to workspace root."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a directory (and all parents) at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file. Use with care — this is irreversible. Only delete files you created or that Josh explicitly asks you to remove.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to delete."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_plan",
            "description": (
                "REQUIRED first step before writing any files. "
                "Call this to submit your implementation plan. "
                "List every file you will create/edit, what each does, and the order of operations. "
                "This ensures clean, complete, one-shot delivery."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "Full implementation plan: goals, file list, step-by-step order.",
                    },
                },
                "required": ["plan"],
            },
        },
    },
]


# ── Tool execution engine ──────────────────────────────────────────────────

def _resolve_path(raw: str, root: Path) -> Path | None:
    """Resolve a path safely within root. Returns None if it escapes the workspace."""
    try:
        p = Path(raw)
        resolved = p.resolve() if p.is_absolute() else (root / p).resolve()
        resolved.relative_to(root.resolve())   # raises ValueError if outside
        return resolved
    except (ValueError, Exception):
        return None


def execute_tool(name: str, args: dict, root: Path) -> str:
    """Execute a file tool call. Returns a string result sent back to the model."""

    if name == "read_file":
        path = _resolve_path(args.get("path", ""), root)
        if not path:
            return "Error: path is outside the workspace root. Only paths inside the workspace are allowed."
        if not path.exists():
            return f"Error: file not found: {path}"
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines   = content.splitlines()
            numbered = "\n".join(f"{i+1:4d}  {ln}" for i, ln in enumerate(lines))
            if len(numbered) > 12000:
                numbered = numbered[:12000] + f"\n... [truncated — {len(lines)} lines total]"
            return f"File: {path}\nLines: {len(lines)}\n\n{numbered}"
        except Exception as e:
            return f"Error reading {path}: {e}"

    elif name == "write_file":
        path    = _resolve_path(args.get("path", ""), root)
        content = args.get("content", "")
        if not path:
            return "Error: path is outside the workspace root."
        if _guardian_protected(args.get("path", "")):
            return "Error: write blocked — path is guardian-protected."
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.write_text(content, encoding="utf-8")
            return f"{'Updated' if existed else 'Created'}: {path}  ({len(content.splitlines())} lines, {len(content)} chars)"
        except Exception as e:
            return f"Error writing {path}: {e}"

    elif name == "list_directory":
        raw  = args.get("path", ".")
        path = _resolve_path(raw, root) if raw and raw != "." else root
        if not path:
            return "Error: path is outside the workspace root."
        if not path.exists():
            return f"Error: directory not found: {path}"
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:150]
            lines   = [f"Directory: {path}", ""]
            for e in entries:
                tag  = "DIR " if e.is_dir() else "    "
                size = f"  {e.stat().st_size:>8,} B" if e.is_file() else ""
                lines.append(f"{tag} {e.name}{size}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing {path}: {e}"

    elif name == "search_files":
        pattern   = args.get("pattern", "*")
        dir_raw   = args.get("directory", ".")
        base      = _resolve_path(dir_raw, root) if dir_raw and dir_raw != "." else root
        if not base:
            base = root
        try:
            matches = sorted(base.glob(pattern))[:80]
            if not matches:
                return f"No files matching '{pattern}' in {base}"
            lines = [f"Found {len(matches)} match(es) for '{pattern}' in {base}:", ""]
            for m in matches:
                try:
                    rel = m.relative_to(root)
                except ValueError:
                    rel = m
                tag = "DIR " if m.is_dir() else "    "
                lines.append(f"{tag} {rel}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching: {e}"

    elif name == "create_directory":
        path = _resolve_path(args.get("path", ""), root)
        if not path:
            return "Error: path is outside the workspace root."
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"Created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {e}"

    elif name == "delete_file":
        path = _resolve_path(args.get("path", ""), root)
        if not path:
            return "Error: path is outside the workspace root."
        if not path.exists():
            return f"File not found (already gone?): {path}"
        try:
            path.unlink()
            return f"Deleted: {path}"
        except Exception as e:
            return f"Error deleting {path}: {e}"

    elif name == "submit_plan":
        plan = args.get("plan", "").strip()
        if not plan:
            return "Plan acknowledged (empty). Please provide a detailed plan next time."
        return f"Plan accepted:\n{plan}\n\nProceed with implementation."

    return f"Unknown tool: {name}"

# ── Sacred palette ─────────────────────────────────────────────────────────
CHAT_CSS = """
/* ── base ── */
body, .gradio-container {
    background-color: #0A0B0D !important;
    color: #F5EFE4 !important;
    font-family: 'EB Garamond', 'Georgia', serif !important;
}

/* ── all text inherits color ── */
.gradio-container * { color: #F5EFE4; }

/* ── chat feed: no gaps, no padding between rows ── */
.message-wrap { gap: 0 !important; padding: 0 !important; }

/* ── every message: full width, no side borders, no radius ── */
.message,
.message.bot,
.message.user,
[data-testid="bot"] .message-bubble-border,
[data-testid="user"] .message-bubble-border {
    all: unset !important;
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    padding: 14px 20px 0px !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'EB Garamond', 'Georgia', serif !important;
    color: #F5EFE4 !important;
}

/* ── AI message background ── */
.message.bot,
[data-testid="bot"] .message-bubble-border {
    background: #0F1218 !important;
}

/* ── user message background ── */
.message.user,
[data-testid="user"] .message-bubble-border {
    background: #0D1020 !important;
}

/* ── wave separator: full-width ~~ line at the bottom of every message row ── */
[data-testid="bot"],
[data-testid="user"] {
    position: relative !important;
    padding-bottom: 0 !important;
    margin: 0 !important;
}

[data-testid="bot"]::after {
    content: "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~";
    display: block !important;
    width: 100% !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    font-family: monospace !important;
    font-size: 0.8em !important;
    letter-spacing: 0 !important;
    color: #C9A227 !important;
    opacity: 0.55 !important;
    padding: 6px 0 0 0 !important;
    line-height: 1 !important;
}

[data-testid="user"]::after {
    content: "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~";
    display: block !important;
    width: 100% !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    font-family: monospace !important;
    font-size: 0.8em !important;
    letter-spacing: 0 !important;
    color: #4a7abf !important;
    opacity: 0.6 !important;
    padding: 6px 0 0 0 !important;
    line-height: 1 !important;
}

/* ── input box: no border except top ~~ line ── */
.multimodal-textbox {
    border: none !important;
    border-radius: 0 !important;
    border-top: 2px solid #C9A227 !important;
    background: #0A0B0D !important;
}

textarea, .multimodal-textbox textarea {
    background: #0A0B0D !important;
    color: #F5EFE4 !important;
    border: none !important;
    border-radius: 0 !important;
    caret-color: #C9A227 !important;
    font-family: 'EB Garamond', 'Georgia', serif !important;
    font-size: 1em !important;
}

/* ── buttons ── */
button.primary {
    background: #1E4D8C !important;
    color: #F5EFE4 !important;
    border: 1px solid #C9A227 !important;
    border-radius: 0 !important;
}
button.secondary {
    background: #0A0B0D !important;
    color: #C9A227 !important;
    border: 1px solid #1E4D8C !important;
    border-radius: 0 !important;
}
button:hover { opacity: 0.85 !important; }

/* ── labels ── */
label span, .block label span { color: #C9A227 !important; font-size: 0.85em; }

/* ── api key inputs ── */
.api-row input {
    background: #0A0B0D !important;
    color: #C9A227 !important;
    border: 1px solid #333 !important;
    border-radius: 0 !important;
    font-family: monospace !important;
}

/* ── scrollbar ── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: #0A0B0D; }
::-webkit-scrollbar-thumb { background: #1E4D8C; }

/* ── file upload ── */
.upload-container, [data-testid="upload"] {
    background: #0A0B0D !important;
    border: 1px dashed #333 !important;
    border-radius: 0 !important;
}

/* ── status bar ── */
#status-bar { color: #C9A227; font-size: 0.78em; font-family: monospace; padding: 4px 0; }
"""

# ── Owner reveal ──────────────────────────────────────────────────────────

def _build_owner_reveal() -> str:
    from cursiv_v215.guardian.obfuscation import session_fingerprint as _sfp_inner
    from cursiv_v215.guardian.temple_guardian import get_session_threat_level, get_strike_count

    # Vault
    vault_agents: list[dict] = []
    reg = ROOT / ".cursiv" / "agent_registry.json"
    if reg.exists():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            vault_agents = [
                {"name": m.get("name","?"), "id": aid[:8], "state": m.get("state","?"),
                 "pos": m.get("council_position","")[:32]}
                for aid, m in data.get("agents", {}).items()
            ]
        except Exception:
            pass

    # Counts
    tc = sum(1 for _ in open(TRAINING_JSONL, encoding="utf-8")) if TRAINING_JSONL.exists() else 0
    gl_path = ROOT / ".cursiv" / "guardian_log.jsonl"
    gc = sum(1 for _ in open(gl_path, encoding="utf-8")) if gl_path.exists() else 0

    # Memory
    mem_agents = 0
    if MEMORY_FILE.exists():
        try:
            mem_agents = len(json.loads(MEMORY_FILE.read_text(encoding="utf-8")).get("agents", {}))
        except Exception:
            pass

    # Guardian
    fingerprint  = _sfp_inner() if _GUARDIAN_OK else "--------"
    threat_level = get_session_threat_level(_GRADIO_SESSION_ID)
    strikes      = get_strike_count(_GRADIO_SESSION_ID)

    # Obsidian
    obs_cfg  = _obs_load_config()
    obs_line = ("ON — " + obs_cfg.get("vault_path", "")) if obs_cfg.get("enabled") else "OFF"

    # Constitution
    const_hash = "unavailable"
    try:
        from cursiv_v215.core.constitution import get_constitution
        const_hash = get_constitution().hash[:16] + "..."
    except Exception:
        pass

    # Build markdown
    rows = ""
    for a in vault_agents[:14]:
        rows += f"| {a['name']} | `{a['id']}` | {a['state']} | {a['pos']} |\n"
    if not rows:
        rows = "| *(vault empty)* | — | — | — |\n"

    return f"""## ⬡  SOVEREIGN OWNER VERIFIED

**Joshua Winkler — Permanent Central Leader**
Guardian firewall suspended for this session. All system internals visible.

---

### Identity & Session

| Field | Value |
|---|---|
| System | JWFrontierEvoCore v3.0 |
| Session ID | `{_GRADIO_SESSION_ID}` |
| Guardian fingerprint | `{fingerprint}` |
| Constitution hash | `{const_hash}` |
| Interface | Gradio / port 7860 |

---

### Active Vault — PiForge Phase Agents

| Name | ID | State | Council Position |
|---|---|---|---|
{rows}
---

### System State

| Component | Value |
|---|---|
| Vault agents | {len(vault_agents)} |
| Memory agents | {mem_agents} |
| Training examples | {tc} |
| Guardian log entries | {gc} |
| Obsidian sync | {obs_line} |

---

### Guardian Status (this session)

| Metric | Value |
|---|---|
| Session threat accumulator | `{threat_level:.4f}` |
| Trigger strikes | {strikes} |
| Owner unlock | **ACTIVE — scans bypassed** |
| Decoys | Meridian / Veil / Cipher (inactive — owner session) |
| Obfuscation token | `{fingerprint}` (rotates every restart) |

---

*The Temple recognizes its builder. The system is fully open to you.*"""


# ── Context loaders ────────────────────────────────────────────────────────

def load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return (
        "You are JWFrontierEvoCore — the autonomous executor of the JW Architect OS "
        "inside Cursiv v3.0. Joshua Winkler is the Permanent Central Leader. "
        "Be warm, direct, truthful, and frontier-oriented."
    )


def load_nexus_context() -> str:
    """Read live agent assignments from the Nexus panel."""
    if not NEXUS_STATE.exists():
        return ""
    try:
        state    = json.loads(NEXUS_STATE.read_text(encoding="utf-8"))
        domains  = state.get("agent_domains", {})
        tasks    = state.get("agent_tasks",   {})
        statuses = state.get("agent_status",  {})
        yin_yang = state.get("yin_yang",      {})

        active = [
            (name, domains.get(name, "general"), tasks.get(name, ""), statuses.get(name, "IDLE"))
            for name in domains
            if domains.get(name, "general") != "general" or tasks.get(name, "")
        ]

        lines = ["\n\n---\n## LIVE NEXUS STATE (auto-injected)\n"]

        if active:
            lines.append("**Active agent assignments:**")
            for name, domain, task, status in active:
                line = f"- **{name}** → [{domain}]  status={status}"
                if task:
                    line += f"  task: {task}"
                lines.append(line)
        else:
            lines.append("All 14 agents at IDLE / general assignment.")

        imbalanced = [ax for ax, v in yin_yang.items() if v != 3]
        if imbalanced:
            lines.append("\n**Yin-Yang flags:** " + ", ".join(
                f"{ax}={'Yang+' if yin_yang[ax]>3 else 'Yin+'}{abs(yin_yang[ax]-3)}"
                for ax in imbalanced
            ))

        checkpoint = state.get("last_checkpoint", "checkpoint-120")
        loss       = state.get("last_loss", 10.785)
        lines.append(f"\n**Active LoRA:** {checkpoint}  (loss: {loss:.3f})")
        lines.append("---")

        return "\n".join(lines)
    except Exception:
        return ""


def load_vault_context() -> str:
    """Inject PiForge phase agent knowledge from vault into every conversation."""
    registry_path = ROOT / ".cursiv" / "agent_registry.json"
    vault_dir     = ROOT / ".cursiv" / "vault"
    if not registry_path.exists():
        return ""
    try:
        registry    = json.loads(registry_path.read_text(encoding="utf-8"))
        agents_meta = registry.get("agents", {})
        if not agents_meta:
            return ""

        lines = ["\n\n---\n## PIFORGE PHASE INTELLIGENCE (vault-active)\n"]

        for agent_id, meta in list(agents_meta.items())[:14]:
            agent_dir = vault_dir / agent_id
            versions  = sorted(agent_dir.glob("v*.json")) if agent_dir.exists() else []
            if not versions:
                continue
            try:
                data = json.loads(versions[-1].read_text(encoding="utf-8"))
            except Exception:
                continue

            km          = data.get("knowledge_map", {})
            name        = data.get("name", meta.get("name", "?"))
            domain      = km.get("domain", "")
            directive   = (km.get("core_directive") or "")[:150].replace("\n", " ")
            translation = (km.get("cursive_v2_translation") or "")[:150].replace("\n", " ")

            lines.append(f"**{name}** [{domain}]: {directive}")
            if translation:
                lines.append(f"  V2: {translation}")

        lines.append("\n---")
        return "\n".join(lines)
    except Exception:
        return ""


# ── File processing ────────────────────────────────────────────────────────

def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Could not read {path.name}: {e}]"


def process_uploaded_files(files: list | None) -> tuple[str, list[dict]]:
    """
    Returns (text_context, image_parts).
    text_context: injected into system prompt.
    image_parts: list of xAI image_url dicts for vision calls.
    """
    if not files:
        return "", []

    text_chunks  = []
    image_parts  = []
    text_exts    = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                    ".json", ".yaml", ".yml", ".csv", ".xml", ".toml", ".bat", ".sh"}
    image_exts   = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

    for f in files:
        p = Path(f if isinstance(f, str) else f.name)

        if p.suffix.lower() in image_exts:
            try:
                raw     = p.read_bytes()
                b64     = base64.b64encode(raw).decode()
                mime    = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                           ".png": "image/png",  ".gif":  "image/gif",
                           ".webp": "image/webp"}.get(p.suffix.lower(), "image/png")
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
                text_chunks.append(f"[Image uploaded: {p.name}]")
            except Exception as e:
                text_chunks.append(f"[Image {p.name} could not be processed: {e}]")

        elif p.suffix.lower() in text_exts:
            content = _read_text_file(p)
            cap     = 8000
            if len(content) > cap:
                content = content[:cap] + f"\n... [truncated at {cap} chars]"
            text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")

        elif p.suffix.lower() == ".pdf":
            text_chunks.append(
                f"[PDF uploaded: {p.name} — PDF parsing not installed. "
                "Install pypdf and I can extract the text automatically.]"
            )
        else:
            try:
                content = _read_text_file(p)[:4000]
                text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")
            except Exception:
                text_chunks.append(f"[File uploaded: {p.name} — binary, cannot display as text]")

    return "\n".join(text_chunks), image_parts


# ── LLM callers ───────────────────────────────────────────────────────────

def _call_ollama(messages: list[dict], max_tokens: int = 1200) -> Generator[str, None, None]:
    """Stream from local Ollama."""
    import json as _json
    prompt = "\n".join(
        f"{'Human' if m['role']=='user' else 'Assistant'}: {m['content']}"
        for m in messages
        if isinstance(m.get("content"), str)
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
    }).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            for line in resp:
                chunk = _json.loads(line.decode())
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except Exception as e:
        yield f"\n[Ollama unavailable: {e}]"


def _call_xai_stream(
    messages: list[dict],
    api_key: str,
    has_images: bool = False,
    max_tokens: int = 1200,
) -> Generator[str, None, None]:
    """Stream from xAI Grok. Handles text and vision."""
    model = XAI_MODEL_VIS if has_images else XAI_MODEL
    payload = json.dumps({
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "stream":      True,
        "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(
            XAI_URL,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk   = json.loads(line[6:])
                        delta   = chunk["choices"][0]["delta"]
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        yield f"\n[xAI API error {e.code}: {body[:200]}]"
    except Exception as e:
        yield f"\n[xAI connection error: {e}]"


def _call_xai_non_stream(messages: list[dict], api_key: str, has_images: bool) -> str:
    """Non-streaming fallback for xAI."""
    result = []
    for chunk in _call_xai_stream(messages, api_key, has_images):
        result.append(chunk)
    return "".join(result)


def _generate_with_openai(
    filepath: str,
    openai_key: str,
    context_messages: list[dict],
    grok_draft: str = "",
) -> str:
    """
    Use OpenAI gpt-4.1 to generate or rewrite a file with full conversation context.
    Passes the last 6 conversation turns so OpenAI understands the goal.
    Falls back to grok_draft if the call fails.
    """
    ext  = Path(filepath).suffix.lower() if filepath else ""
    lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".sh": "Bash", ".bat": "Batch"}.get(ext, "code")

    # Build context from the last 6 conversation turns (skip system message)
    ctx_turns = [m for m in context_messages if m.get("role") in ("user", "assistant")][-6:]
    ctx_text  = "\n".join(
        f"[{m['role'].upper()}]: {m['content'][:800]}"
        for m in ctx_turns
        if isinstance(m.get("content"), str)
    )

    system_msg = (
        f"You are an expert {lang} engineer. "
        "Write complete, production-ready code — no stubs, no TODOs, no placeholder comments. "
        "Return ONLY the raw file content, nothing else. No markdown fences, no explanation."
    )
    user_msg = (
        f"Conversation context:\n{ctx_text}\n\n"
        f"File to generate: {filepath}\n\n"
    )
    if grok_draft:
        user_msg += (
            f"Grok's draft (improve and complete this):\n"
            f"{grok_draft[:8000]}\n\n"
        )
    user_msg += (
        "Write the complete, final file content. "
        "Every function must be fully implemented. No ellipsis, no '# TODO'."
    )

    try:
        payload = json.dumps({
            "model":      OPENAI_CODE_MODEL,
            "messages":   [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            "max_tokens": 8000,
        }).encode()
        req = urllib.request.Request(
            OPENAI_URL, data=payload,
            headers={"Content-Type":  "application/json",
                     "Authorization": f"Bearer {openai_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _generate_with_claude(
    filepath: str,
    anthropic_key: str,
    context_messages: list[dict],
    grok_draft: str = "",
) -> str:
    """
    Use Claude claude-sonnet-4-6 to generate or rewrite a file with full
    conversation context. Falls back to empty string if the call fails.
    """
    ext  = Path(filepath).suffix.lower() if filepath else ""
    lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".sh": "Bash", ".bat": "Batch"}.get(ext, "code")

    ctx_turns = [m for m in context_messages if m.get("role") in ("user", "assistant")][-6:]
    ctx_text  = "\n".join(
        f"[{m['role'].upper()}]: {m['content'][:800]}"
        for m in ctx_turns
        if isinstance(m.get("content"), str)
    )

    system_msg = (
        f"You are an expert {lang} engineer. "
        "Write complete, production-ready code — no stubs, no TODOs, no placeholder comments. "
        "Return ONLY the raw file content, nothing else. No markdown fences, no explanation."
    )
    user_msg = (
        f"Conversation context:\n{ctx_text}\n\n"
        f"File to generate: {filepath}\n\n"
    )
    if grok_draft:
        user_msg += (
            f"Grok's draft (improve and complete this):\n"
            f"{grok_draft[:8000]}\n\n"
        )
    user_msg += (
        "Write the complete, final file content. "
        "Every function must be fully implemented. No ellipsis, no '# TODO'."
    )

    try:
        payload = json.dumps({
            "model":      ANTHROPIC_CODE_MODEL,
            "max_tokens": 8000,
            "system":     system_msg,
            "messages":   [{"role": "user", "content": user_msg}],
        }).encode()
        req = urllib.request.Request(
            ANTHROPIC_URL, data=payload,
            headers={
                "Content-Type":    "application/json",
                "x-api-key":       anthropic_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["content"][0]["text"].strip()
    except Exception:
        return ""


def _call_xai_with_tools(
    messages: list[dict],
    api_key: str,
    root: Path,
    openai_key: str = "",
    has_images: bool = False,
    max_tokens: int = 4000,
    max_loops: int = 20,
    confirm_writes: bool = False,
    anthropic_key: str = "",
) -> Generator[str, None, None]:
    """
    Agentic file-access loop.
    Calls xAI with FILE_TOOLS; executes tool calls locally; loops until done.
    Code generation priority on write_file: Claude (Anthropic) > OpenAI > none.
    Yields strings — tool events formatted inline, then the final response.
    """
    model     = XAI_MODEL_VIS if has_images else XAI_MODEL
    loop_msgs = list(messages)

    for _ in range(max_loops):
        payload = json.dumps({
            "model":       model,
            "messages":    loop_msgs,
            "tools":       FILE_TOOLS,
            "tool_choice": "auto",
            "max_tokens":  max_tokens,
            "temperature": 0.7,
            "stream":      False,
        }).encode()
        try:
            req = urllib.request.Request(
                XAI_URL, data=payload,
                headers={"Content-Type":  "application/json",
                         "Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            yield f"\n[xAI error {e.code}: {body[:200]}]"
            return
        except Exception as e:
            yield f"\n[xAI error: {e}]"
            return

        choice     = data["choices"][0]
        msg        = choice["message"]
        loop_msgs.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            # Terminal response — fake-stream word by word for rolling feel
            content = msg.get("content") or ""
            for word in content.split(" "):
                yield word + " "
            return

        # Execute each tool call
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except Exception:
                fn_args = {}

            arg_preview = ", ".join(f"{k}={repr(v)[:40]}" for k, v in fn_args.items())
            yield f"\n*`[{fn_name}({arg_preview})]`*\n"

            # Confirm-before-write: pause and hand control back to the UI
            if fn_name == "write_file" and confirm_writes:
                path_arg    = fn_args.get("path", "")
                content_arg = fn_args.get("content", "")
                preview     = content_arg[:600] + ("..." if len(content_arg) > 600 else "")
                yield (
                    f"\n**Write requested:** `{path_arg}`\n"
                    f"```\n{preview}\n```\n"
                    f"*Waiting for approval…*\n"
                )
                yield WRITE_SENTINEL + json.dumps({"path": path_arg, "content": content_arg})
                return   # stop the loop — resume after user approves

            # Code-gen enhancement before writing:
            # Claude (Anthropic) takes priority when key is set; falls back to OpenAI.
            if fn_name == "write_file" and (anthropic_key or openai_key):
                grok_draft = fn_args.get("content", "")
                filepath   = fn_args.get("path", "")
                if grok_draft:
                    if anthropic_key:
                        yield f"*[Claude {ANTHROPIC_CODE_MODEL} generating production-ready code…]*\n"
                        generated = _generate_with_claude(filepath, anthropic_key, loop_msgs, grok_draft)
                    else:
                        yield "*[OpenAI gpt-4.1 generating production-ready code…]*\n"
                        generated = _generate_with_openai(filepath, openai_key, loop_msgs, grok_draft)
                    if generated:
                        fn_args["content"] = generated
                        yield "*[Code generation complete — writing file]*\n"

            result = execute_tool(fn_name, fn_args, root)
            yield f"```\n{result[:600]}\n```\n"

            loop_msgs.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result,
            })

    yield "\n[Max tool iterations reached — stopping.]"


# ── Smart model routing ───────────────────────────────────────────────────

import re as _re

_CODE_RE = _re.compile(
    r'\b(write|fix|debug|implement|refactor|build|create|update|edit|'
    r'function|class|method|script|module|endpoint|database|query|'
    r'python|javascript|typescript|html|css|sql|bash|json|'
    r'error|traceback|exception|bug|test|import|def |return )\b',
    _re.I,
)
_CREATIVE_RE = _re.compile(
    r'\b(imagine|visualize|visualise|design|aesthetic|stunning|beautiful|'
    r'describe.*look|story|narrative|poem|creative|artistic|visual|render|draw)\b',
    _re.I,
)


def _classify_message(text: str) -> str:
    """Return 'code', 'creative', or 'general' for smart model routing."""
    t = (text or "").strip()
    if not t:
        return "general"
    if any(m in t for m in ("def ", "class ", "```", "import ", "Error:", "Traceback", "  File \"")):
        return "code"
    code_hits     = len(_CODE_RE.findall(t))
    creative_hits = len(_CREATIVE_RE.findall(t))
    if code_hits >= 2:
        return "code"
    if creative_hits >= 2 and creative_hits > code_hits:
        return "creative"
    if code_hits >= 1:
        return "code"
    return "general"


def _call_claude_direct(
    messages: list[dict],
    anthropic_key: str,
) -> Generator[str, None, None]:
    """Route a chat message directly to Claude — no tool loop."""
    sys_parts = [m["content"] for m in messages if m["role"] == "system"]
    chat_msgs  = [m for m in messages if m["role"] != "system"]
    payload = json.dumps({
        "model":      ANTHROPIC_CODE_MODEL,
        "max_tokens": 4096,
        "system":     "\n\n".join(sys_parts),
        "messages":   chat_msgs,
    }).encode()
    try:
        req = urllib.request.Request(
            ANTHROPIC_URL, data=payload,
            headers={
                "content-type":      "application/json",
                "x-api-key":         anthropic_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        content = (data.get("content") or [{}])[0].get("text", "") or ""
        for word in content.split(" "):
            yield word + " "
    except urllib.error.HTTPError as e:
        yield f"\n[Claude error {e.code}: {e.read().decode(errors='ignore')[:200]}]"
    except Exception as e:
        yield f"\n[Claude error: {e}]"


def _call_openai_direct(
    messages: list[dict],
    openai_key: str,
) -> Generator[str, None, None]:
    """Route a chat message directly to GPT-4.1 — no tool loop."""
    payload = json.dumps({
        "model":    OPENAI_CODE_MODEL,
        "messages": messages,
    }).encode()
    try:
        req = urllib.request.Request(
            OPENAI_URL, data=payload,
            headers={
                "content-type":  "application/json",
                "Authorization": f"Bearer {openai_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"] or ""
        for word in content.split(" "):
            yield word + " "
    except urllib.error.HTTPError as e:
        yield f"\n[OpenAI error {e.code}: {e.read().decode(errors='ignore')[:200]}]"
    except Exception as e:
        yield f"\n[OpenAI error: {e}]"


# ── Core chat function ────────────────────────────────────────────────────

def chat(
    message: dict | str,
    history: list[dict],
    api_key: str,
    files: list | None,
    file_access: bool = False,
    root_path: str = "",
    openai_key: str = "",
    confirm_writes: bool = False,
    anthropic_key: str = "",
) -> Generator[str, None, None]:
    """
    Main streaming chat handler.
    message: dict with 'text' and optionally 'files' (from MultimodalTextbox)
             or plain str if called programmatically.
    history: list of {"role": ..., "content": ...} dicts (Gradio 6 format).
    """

    # ── Unpack multimodal input ─────────────────────────────────────────
    if isinstance(message, dict):
        user_text    = message.get("text", "").strip()
        uploaded     = list(message.get("files", []) or [])
    else:
        user_text    = str(message).strip()
        uploaded     = []

    if files:
        uploaded.extend(files)

    if not user_text and not uploaded:
        yield "Please type a message or upload a file."
        return

    # ── Sovereign owner check (runs before Guardian — no API call, no log) ──
    if user_text and _verify_sovereign(user_text):
        _unlock_owner(_GRADIO_SESSION_ID)
        yield _build_owner_reveal()
        return

    # ── Temple Guardian scan (front-end defense layer) ──────────────────
    # Runs BEFORE any API call. If a probe is detected, the skull screen
    # is returned immediately and no API credits are consumed.
    # The only gate this does NOT cover is human phishing / social engineering —
    # always verify actions before approving file writes or API key requests.
    if _GUARDIAN_OK and user_text:
        _triggered, _skull = _guardian_scan(user_text, _GRADIO_SESSION_ID)
        if _triggered:
            yield _skull
            yield "\n\n" + _decoy_response(_GRADIO_SESSION_ID)
            return

    # ── Process files ───────────────────────────────────────────────────
    file_context, image_parts = process_uploaded_files(uploaded)

    # ── Build system prompt ─────────────────────────────────────────────
    system_text = load_system_prompt() + load_nexus_context() + load_vault_context() + _load_session_ctx()
    if file_context:
        system_text += f"\n\n## Uploaded Content\n{file_context}"
    if file_access:
        system_text += """

## CODING PROTOCOL (file access active)
You are in full autonomous coding mode. Follow this protocol exactly:
1. ALWAYS call submit_plan first — list every file you will create/edit, what it does, and your order of operations.
2. Write COMPLETE, production-ready code — zero stubs, zero TODOs, zero placeholders. Every function fully implemented.
3. Always call read_file before editing an existing file so you know the current content.
4. After writing each file, call read_file to verify the content is correct.
5. If building an app, create ALL required files: entry point, dependencies (requirements.txt / package.json), and a README.
6. Think end-to-end: if the user says "build X", deliver a working X in one sweep without stopping to ask clarifying questions unless the request is genuinely ambiguous.
"""

    # ── Build messages array ────────────────────────────────────────────
    messages: list[dict] = [{"role": "system", "content": system_text}]

    for h in history:
        role    = h.get("role", "user")
        content = h.get("content", "")
        if content:
            messages.append({"role": role, "content": content})

    # ── Attach images to user message (vision) ──────────────────────────
    if image_parts:
        user_content: list[dict] | str = [{"type": "text", "text": user_text}] + image_parts
    else:
        user_content = user_text

    messages.append({"role": "user", "content": user_content})

    # ── Smart model routing ─────────────────────────────────────────────
    key = (api_key or "").strip()
    oai = (openai_key or "").strip()
    ant = (anthropic_key or "").strip()
    has_images = len(image_parts) > 0
    msg_type   = _classify_message(user_text)

    if key and file_access:
        # Tool-use loop always runs on Grok — Claude/GPT handle write_file generation inside
        workspace = (
            Path(root_path.strip()).expanduser().resolve()
            if root_path.strip() else ROOT
        )
        yield from _call_xai_with_tools(messages, key, workspace, oai, has_images,
                                         confirm_writes=confirm_writes, anthropic_key=ant)
    elif msg_type == "code" and ant and not has_images:
        # Code task + Anthropic key → Claude
        yield "*[Claude — code task routed automatically]*\n\n"
        yield from _call_claude_direct(messages, ant)
    elif msg_type == "code" and oai and not ant and not has_images:
        # Code task + OpenAI key (no Claude) → GPT-4.1
        yield "*[GPT-4.1 — code task routed automatically]*\n\n"
        yield from _call_openai_direct(messages, oai)
    elif key:
        yield from _call_xai_stream(messages, key, has_images)
    else:
        # Try Ollama (local); it cannot handle images
        text_messages = [
            {"role": m["role"],
             "content": m["content"] if isinstance(m["content"], str)
                        else next((p["text"] for p in m["content"] if p["type"]=="text"), "")}
            for m in messages
        ]
        ollama_gen = _call_ollama(text_messages)
        first = next(ollama_gen, None)
        if first is not None:
            yield first
            yield from ollama_gen
        else:
            yield (
                "[No API key provided and Ollama is not running.]\n\n"
                "**To connect xAI Grok:** paste your xAI API key in the key slot above.\n"
                "**To run locally:** start Ollama with `ollama run mistral`."
            )


# ── Status bar ────────────────────────────────────────────────────────────

def status_bar(api_key: str, openai_key: str = "", anthropic_key: str = "") -> str:
    key_status = "xAI ✓" if api_key.strip() else "xAI — (no key)"
    oai_status = "OpenAI ✓" if openai_key.strip() else "OpenAI —"
    ant_status = f"Claude ✓ ({ANTHROPIC_CODE_MODEL})" if anthropic_key.strip() else "Claude —"
    nexus_ok   = "Nexus LIVE" if NEXUS_STATE.exists() else "Nexus OFFLINE"
    guardian_s = f"Guardian ✓ [{_sfp()}]" if _GUARDIAN_OK else "Guardian —"
    ollama_ok  = "Ollama ?"
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=1)
        ollama_ok = "Ollama ✓"
    except Exception:
        ollama_ok = "Ollama —"
    vc = len(list((ROOT / ".cursiv" / "vault").glob("*"))) if (ROOT / ".cursiv" / "vault").exists() else 0
    tc = sum(1 for _ in open(TRAINING_JSONL, encoding="utf-8")) if TRAINING_JSONL.exists() else 0
    return (
        f"JWFrontierEvoCore v1.0  ·  {key_status}  ·  {oai_status}  ·  {ant_status}  ·  "
        f"{ollama_ok}  ·  {nexus_ok}  ·  {guardian_s}  ·  "
        f"Vault: {vc} agents  ·  Training: {tc} examples  ·  {datetime.now().strftime('%H:%M')}"
    )


def save_to_training(history: list[dict], quality: float = 0.80) -> str:
    """Save the last exchange to training JSONL."""
    if len(history) < 2:
        return "Need at least one exchange to save."
    user_msg = next((h["content"] for h in reversed(history) if h["role"] == "user"), "")
    ai_msg   = next((h["content"] for h in reversed(history) if h["role"] == "assistant"), "")
    if not user_msg or not ai_msg:
        return "Could not extract a complete exchange."
    TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    example = {
        "prompt":    user_msg[:2000],
        "response":  ai_msg[:2000],
        "quality":   quality,
        "timestamp": datetime.now().isoformat(),
        "source":    "main_chat",
    }
    with TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(example) + "\n")
    count = sum(1 for _ in TRAINING_JSONL.open(encoding="utf-8"))
    return f"✓  Saved to training data. Total examples: {count}"


# ── Hotkey JS — Ctrl+` cycles write-confirm mode ─────────────────────────
HOTKEY_JS = """
() => {
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === '`') {
            e.preventDefault();
            var el = document.getElementById('confirm-mode-btn');
            if (el) { var b = el.querySelector('button'); if (b) b.click(); }
        }
    });
}
"""


# ── Build the app ─────────────────────────────────────────────────────────

def build_chat_app() -> gr.Blocks:

    sacred_theme = gr.themes.Base(
        primary_hue="blue",
        secondary_hue="yellow",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("EB Garamond"),
    )

    with gr.Blocks(title="JW Main Chat — JWFrontierEvoCore") as app:

        # ── Invisible state components ───────────────────────────────────
        confirm_mode_state  = gr.State(value="confirm")   # "auto" | "confirm"
        pending_write_state = gr.State(value=None)     # JSON string when a write is waiting

        # ── Header ──────────────────────────────────────────────────────
        gr.Markdown(
            "## ⬡ JWFrontierEvoCore — Main Chat\n"
            "**Cursiv v3.0** · Permanent Central Leader: Joshua Winkler · "
            "[Open Nexus →](http://localhost:7861)"
        )

        # ── API key row ──────────────────────────────────────────────────
        with gr.Row(elem_classes=["api-row"]):
            api_key_box = gr.Textbox(
                label="xAI API Key  (main chat)",
                placeholder="xai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                type="password",
                scale=3,
            )
            openai_key_box = gr.Textbox(
                label="OpenAI API Key  (code gen fallback)",
                placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                type="password",
                scale=3,
            )
            anthropic_key_box = gr.Textbox(
                label="Anthropic API Key  (Claude code gen — priority over OpenAI)",
                placeholder="sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                type="password",
                scale=3,
            )
        with gr.Column(scale=6):
            status_md = gr.Markdown(
                value="Checking connections...",
                elem_id="status-bar",
            )

        # ── Write-confirm mode badge + hidden hotkey target ──────────────
        with gr.Row():
            mode_badge = gr.Markdown(
                value=(
                    "**Write mode:** CONFIRM ✋ — you approve every file write  *(Ctrl+` to toggle)*  "
                    "· **Security reminder:** always verify requests before approving writes or sharing API keys — "
                    "human phishing is the one gate the firewall cannot cover."
                ),
                elem_id="mode-badge",
            )
            # Hidden button — the JS hotkey clicks this to toggle mode
            toggle_confirm_btn = gr.Button(
                "toggle", visible=False, elem_id="confirm-mode-btn", scale=0
            )

        # ── File system access row ───────────────────────────────────────
        with gr.Row():
            file_access_toggle = gr.Checkbox(
                label="Enable File System Access  (xAI reads/writes files in workspace)",
                value=False,
                scale=1,
            )
            root_path_box = gr.Textbox(
                label="Workspace Root  (all file ops sandboxed to this path)",
                placeholder=str(ROOT),
                value=str(ROOT),
                scale=5,
            )

        # ── Obsidian Vault Sync row ───────────────────────────────────────
        _obs_cfg_init = _obs_load_config()
        _obs_vault_init = _obs_cfg_init.get("vault_path", "") or _obs_detect_vault()
        with gr.Row():
            obsidian_toggle = gr.Checkbox(
                label="Sync to Obsidian Vault  (auto-export training data as daily Markdown notes)",
                value=_obs_cfg_init.get("enabled", False),
                scale=1,
            )
            obsidian_path_box = gr.Textbox(
                label="Obsidian Vault Path",
                placeholder=r"C:\Users\username\Documents\MyVault",
                value=_obs_vault_init,
                scale=4,
            )
            obsidian_export_btn = gr.Button("Export Now", variant="secondary", scale=1)
        obsidian_feedback = gr.Markdown(visible=False)

        # ── Chat window ──────────────────────────────────────────────────
        chatbot = gr.Chatbot(
            label="JWFrontierEvoCore",
            height=560,
            show_label=False,
            avatar_images=(None, None),
            render_markdown=True,
            layout="panel",
            placeholder="*JWFrontierEvoCore is standing by. Type a message or drop in a file.*",
        )

        # ── Input row ────────────────────────────────────────────────────
        with gr.Row():
            msg_box = gr.MultimodalTextbox(
                placeholder=(
                    "Talk to JWFrontierEvoCore...  |  "
                    "Drag in images, JSON, code, raw files, anything"
                ),
                show_label=False,
                file_types=[
                    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml",
                    ".yml", ".csv", ".xml", ".toml", ".png", ".jpg", ".jpeg",
                    ".gif", ".webp", ".pdf", ".bat", ".sh", ".html", ".css",
                ],
                submit_btn=True,
                scale=9,
            )

        # ── Utility row ──────────────────────────────────────────────────
        with gr.Row():
            btn_clear    = gr.Button("Clear Chat",       variant="secondary", scale=1)
            btn_save     = gr.Button("Save to Training", variant="secondary", scale=1)
            q_slider     = gr.Slider(
                0.0, 1.0, step=0.05, value=0.80,
                label="Quality score for training save",
                scale=3,
            )
        save_feedback = gr.Markdown()

        # ── Confirm-before-write panel (hidden until a write is pending) ──
        with gr.Group(visible=False) as confirm_group:
            confirm_path_md = gr.Markdown("**Pending write:**")
            with gr.Row():
                btn_approve = gr.Button("Approve Write", variant="primary",  scale=1)
                btn_cancel  = gr.Button("Cancel Write",  variant="secondary", scale=1)
            gr.Markdown(
                "*Review the proposed content in the chat above, then approve or cancel.*",
                elem_classes=["prose"],
            )

        # ── Nexus live context toggle ─────────────────────────────────────
        with gr.Row():
            gr.Markdown(
                "**Tip:** Open the [Nexus panel](http://localhost:7861) in another window. "
                "Repurpose agents there — changes inject into this conversation automatically on your next message.",
                elem_classes=["prose"],
            )

        # ── Streaming submit ─────────────────────────────────────────────
        def _submit(message, history, api_key, openai_key, anthropic_key, file_access, root_path, confirm_mode):
            if not message or (isinstance(message, dict) and not message.get("text") and not message.get("files")):
                yield history, gr.update(), None, gr.update(), gr.update()
                return

            user_text = message.get("text", "") if isinstance(message, dict) else str(message)
            history   = history or []
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": ""})
            yield history, gr.update(value=None), None, gr.update(visible=False), gr.update()

            full_response   = ""
            do_confirm      = confirm_mode == "confirm"
            pending_payload = None

            for chunk in chat(message, history[:-2], api_key, None,
                              file_access, root_path, openai_key, do_confirm, anthropic_key):

                if WRITE_SENTINEL in (full_response + chunk):
                    combined        = full_response + chunk
                    display, raw    = combined.split(WRITE_SENTINEL, 1)
                    try:
                        pending_payload = json.loads(raw)
                    except Exception:
                        pending_payload = None
                    history[-1]["content"] = display.rstrip()
                    path_label = f"**Pending write:** `{pending_payload.get('path','?')}`" if pending_payload else ""
                    yield (
                        history,
                        gr.update(value=None),
                        json.dumps(pending_payload) if pending_payload else None,
                        gr.update(visible=bool(pending_payload)),
                        gr.update(value=path_label),
                    )
                    return

                full_response          += chunk
                history[-1]["content"]  = full_response
                yield history, gr.update(value=None), None, gr.update(visible=False), gr.update()

            # ── Post-exchange: session log + Obsidian livestream ──────────
            if user_text and full_response:
                model_used = (
                    "claude"  if ant and _classify_message(user_text) == "code" and not file_access
                    else "gpt-4.1" if oai and not ant and _classify_message(user_text) == "code" and not file_access
                    else "grok"
                )
                try:
                    _session_append(user_text, full_response, model_used)
                except Exception:
                    pass
                try:
                    _obs_livestream(user_text, full_response, model_used)
                except Exception:
                    pass

        # ── Write-confirm mode toggle ─────────────────────────────────────
        def _toggle_mode(mode):
            new_mode = "confirm" if mode == "auto" else "auto"
            if new_mode == "confirm":
                badge = "**Write mode:** CONFIRM ✋ — you approve every file write  *(Ctrl+` to toggle)*"
            else:
                badge = "**Write mode:** AUTO — file writes execute immediately  *(Ctrl+` to toggle)*"
            return new_mode, badge

        # ── Approve pending write ─────────────────────────────────────────
        def _approve_write(pending_json, history, root_path):
            history = list(history or [])
            if not pending_json:
                history.append({"role": "assistant", "content": "*No pending write found.*"})
                return history, None, gr.update(visible=False), gr.update()
            try:
                pending = json.loads(pending_json)
            except Exception:
                history.append({"role": "assistant", "content": "*Could not parse pending write.*"})
                return history, None, gr.update(visible=False), gr.update()
            workspace = (
                Path(root_path.strip()).expanduser().resolve()
                if root_path.strip() else ROOT
            )
            result = execute_tool("write_file", pending, workspace)
            history.append({"role": "assistant",
                             "content": f"**Write approved and executed.**\n```\n{result}\n```"})
            return history, None, gr.update(visible=False), gr.update(value="")

        # ── Cancel pending write ──────────────────────────────────────────
        def _cancel_write(history):
            history = list(history or [])
            history.append({"role": "assistant", "content": "**Write cancelled** — file not modified."})
            return history, None, gr.update(visible=False), gr.update(value="")

        # ── Event wiring ──────────────────────────────────────────────────
        msg_box.submit(
            fn=_submit,
            inputs=[msg_box, chatbot, api_key_box, openai_key_box, anthropic_key_box,
                    file_access_toggle, root_path_box, confirm_mode_state],
            outputs=[chatbot, msg_box, pending_write_state, confirm_group, confirm_path_md],
        )

        toggle_confirm_btn.click(
            fn=_toggle_mode,
            inputs=[confirm_mode_state],
            outputs=[confirm_mode_state, mode_badge],
        )

        btn_approve.click(
            fn=_approve_write,
            inputs=[pending_write_state, chatbot, root_path_box],
            outputs=[chatbot, pending_write_state, confirm_group, confirm_path_md],
        )

        btn_cancel.click(
            fn=_cancel_write,
            inputs=[chatbot],
            outputs=[chatbot, pending_write_state, confirm_group, confirm_path_md],
        )

        btn_clear.click(
            fn=lambda: ([], None),
            outputs=[chatbot, msg_box],
        )

        def _save_and_export(history, quality):
            result = save_to_training(history, quality)
            obs_msg = _obs_auto_export()
            if obs_msg:
                result = result + "\n\n" + obs_msg
            return result, gr.update(visible=True)

        btn_save.click(
            fn=_save_and_export,
            inputs=[chatbot, q_slider],
            outputs=[save_feedback, obsidian_feedback],
        )

        # ── Obsidian sync handlers ────────────────────────────────────────
        def _obs_toggle(enabled, vault_path):
            _obs_save_config(enabled, vault_path or "")
            if enabled and vault_path:
                msg = f"Obsidian sync **ON** — notes will write to `{vault_path}/Cursiv/`"
            elif enabled:
                msg = "Obsidian sync **ON** — set vault path to activate."
            else:
                msg = "Obsidian sync **OFF**."
            return gr.update(value=msg, visible=True)

        def _obs_path_changed(enabled, vault_path):
            _obs_save_config(enabled, vault_path or "")
            return gr.update()

        def _obs_export_now(vault_path):
            if not (vault_path or "").strip():
                return gr.update(value="Set the Obsidian vault path first.", visible=True)
            ok, msg = _obs_export(vault_path)
            return gr.update(value=msg, visible=True)

        obsidian_toggle.change(
            fn=_obs_toggle,
            inputs=[obsidian_toggle, obsidian_path_box],
            outputs=[obsidian_feedback],
        )
        obsidian_path_box.change(
            fn=_obs_path_changed,
            inputs=[obsidian_toggle, obsidian_path_box],
            outputs=[obsidian_feedback],
        )
        obsidian_export_btn.click(
            fn=_obs_export_now,
            inputs=[obsidian_path_box],
            outputs=[obsidian_feedback],
        )

        api_key_box.change(
            fn=status_bar,
            inputs=[api_key_box, openai_key_box, anthropic_key_box],
            outputs=[status_md],
        )
        openai_key_box.change(
            fn=status_bar,
            inputs=[api_key_box, openai_key_box, anthropic_key_box],
            outputs=[status_md],
        )
        anthropic_key_box.change(
            fn=status_bar,
            inputs=[api_key_box, openai_key_box, anthropic_key_box],
            outputs=[status_md],
        )

        # Initial status check
        app.load(fn=lambda: status_bar("", "", ""), outputs=[status_md])

    return app, sacred_theme


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    app, theme = build_chat_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        favicon_path=None,
        theme=theme,
        css=CHAT_CSS,
        js=HOTKEY_JS,
    )
