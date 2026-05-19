"""
Cursiv — Terminal Chat
Cursiv-v2.1.5

Run:  python -m cursiv_v215.ui.chat_cli
      OR double-click  Launch Chat CLI.bat

Messages stack naturally and scroll upward — use the mouse wheel or terminal
scroll-bar to read history.  The input box stays at the current bottom.

Commands:
  key  <xai-key>       set xAI Grok API key   (starts with xai-)
  openai <key>         set OpenAI API key      (starts with sk-)
  anthropic <key>      set Anthropic API key   (starts with sk-ant-)
  files on / off       enable / disable file-system access
  workspace <path>     sandbox root for file tools
  mode                 toggle write mode  (auto ↔ confirm)
  clear                wipe conversation history shown in box
  status               show current config
  help                 this list
  exit / Ctrl+C        quit
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import textwrap
import urllib.request
from pathlib import Path

# Force UTF-8 stdout — prevents surrogate/emoji crashes on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent.parent))

from cursiv_v215.ui.chat_app import (
    WRITE_SENTINEL,
    RATE_SENTINEL,
    ROOT,
    chat,
    execute_tool,
    _call_group_discovery,
    _cursiv_encode,
)

try:
    from cursiv_v215.forge.funforge_meta import (
        FunForgeSession,
        FUNFORGE_CLOSE_PROMPT,
        detect_trigger  as _ff_detect,
        extract_topic   as _ff_topic,
    )
    _FF_OK = True
except Exception:
    _FF_OK = False

# ── Sovereign verification (hash assembled from 3 modules — no plaintext) ──
import hashlib as _hl_cli
try:
    from cursiv_v215.guardian.temple_guardian import _RING_CORE    as _RC_cli
    from cursiv_v215.guardian.obfuscation     import _LATTICE_ROOT as _LR_cli
    from cursiv_v215.weave.sovereign          import _WEAVE_SEAL   as _WS_cli
    from cursiv_v215.guardian.temple_guardian import unlock_owner_session as _unlock_cli
    def _verify_sovereign_cli(text: str) -> bool:
        try:
            return _hl_cli.sha256(text.strip().encode()).hexdigest() == (_RC_cli + _LR_cli + _WS_cli)
        except Exception:
            return False
except Exception:
    def _verify_sovereign_cli(text: str) -> bool:
        return False
    def _unlock_cli(sid: str):
        pass

# ── Obsidian Vault Sync ────────────────────────────────────────────────────
try:
    from cursiv_v215.obsidian.exporter import (
        load_config        as _obs_load_config,
        save_config        as _obs_save_config,
        export_today       as _obs_export,
        auto_detect_vault  as _obs_detect_vault,
        livestream_exchange as _obs_livestream_cli,
    )
    _OBS_CLI_OK = True
except Exception:
    _OBS_CLI_OK = False
    def _obs_load_config():            return {"enabled": False, "vault_path": ""}
    def _obs_save_config(e, p):        pass
    def _obs_export(vp, d=None):       return (False, "Obsidian module unavailable.")
    def _obs_detect_vault():           return ""
    def _obs_livestream_cli(u, a, m):  pass

# ── Session Memory ─────────────────────────────────────────────────────────
try:
    from cursiv_v215.memory.session_log import (
        append_exchange  as _session_append_cli,
        get_boot_summary as _session_boot_summary,
    )
    _SESSION_CLI_OK = True
except Exception:
    _SESSION_CLI_OK = False
    def _session_append_cli(u, a, m="unknown"): pass
    def _session_boot_summary():                return {}

# ── Codex Agent — offline-capable coding specialist ──────────────────────
try:
    from cursiv_v215.agents.codex_agent import (
        generate     as _codex_gen_cli,
        is_available as _codex_avail_cli,
    )
    _CODEX_CLI_OK = True
except Exception:
    _CODEX_CLI_OK = False
    def _codex_gen_cli(p: str) -> str: return ""
    def _codex_avail_cli() -> bool:    return False

# ── Hermes Agent — offline multi-step tool executor ───────────────────────
try:
    from cursiv_v215.agents.hermes_agent import (
        run          as _hermes_run_cli,
        is_available as _hermes_avail_cli,
    )
    _HERMES_CLI_OK = True
except Exception:
    _HERMES_CLI_OK = False
    def _hermes_run_cli(p: str) -> str: return ""
    def _hermes_avail_cli() -> bool:    return False

# ── Reference Brain — offline SQLite knowledge ────────────────────────────
try:
    from cursiv_v215.agents.reference_brain import (
        answer       as _ref_answer_cli,
        is_available as _ref_avail_cli,
    )
    _REF_CLI_OK = True
except Exception:
    _REF_CLI_OK = False
    def _ref_answer_cli(q: str) -> str: return ""
    def _ref_avail_cli() -> bool:       return False

# ── Offline Queue ──────────────────────────────────────────────────────────
try:
    from cursiv_v215.agents.offline_queue import (
        enqueue      as _queue_enqueue_cli,
        format_queue as _queue_format_cli,
        count        as _queue_count_cli,
    )
    _QUEUE_CLI_OK = True
except Exception:
    _QUEUE_CLI_OK = False
    def _queue_enqueue_cli(p: str, **kw) -> dict: return {}
    def _queue_format_cli() -> str:               return ""
    def _queue_count_cli() -> int:                return 0

# ── System Guardian — back-end CLI defense layer ────────────────────────────
try:
    from cursiv_v215.guardian.temple_guardian import scan_cli as _guardian_scan_cli
    from cursiv_v215.guardian.obfuscation import session_fingerprint as _sfp
    _CLI_GUARDIAN_OK = True
except Exception:
    _CLI_GUARDIAN_OK = False
    def _guardian_scan_cli(msg, sid="cli"): return (False, None)
    def _sfp():                             return "--------"

_CLI_SESSION_ID = f"cli_{os.getpid()}"

# ── Rate limiter + scan display ────────────────────────────────────────────
try:
    from cursiv_v215.core.rate_limiter import limiter as _cli_limiter
    from cursiv_v215.core.scan_display import ScanDisplay as _CLI_ScanDisplay
    _cli_scan = _CLI_ScanDisplay(_cli_limiter)
    _RATE_CLI_OK = True
except Exception:
    _cli_limiter  = None
    _cli_scan     = None
    _RATE_CLI_OK  = False

# ── prompt_toolkit for paste-safe input + wide-char width ──────────────────
# paste-safe: bracketed paste mode so the whole paste lands as one message.
# get_cwidth: correctly counts wide chars (✦ ✓ ✋ etc) as 2 columns so box
#             borders align properly on all terminals.
try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.formatted_text import ANSI as _PT_ANSI
    from prompt_toolkit.utils import get_cwidth as _cwidth
    _HAS_PT = True
except ImportError:
    _HAS_PT = False
    def _cwidth(c: str) -> int:          # fallback: treat everything as 1
        return 1

# ── Enable ANSI on Windows ─────────────────────────────────────────────────
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        os.system("color")

# ── Palette ────────────────────────────────────────────────────────────────
# ── Sacred Palette — Egyptian Temple ─────────────────────────────────────
GOLD   = "\033[38;5;220m"   # Egyptian gold — AI prefix, icons, accents
LGOLD  = "\033[38;5;136m"   # Deep antique gold — borders, frames
SILVER = "\033[38;5;253m"   # Bright silver — user text
SILV2  = "\033[38;5;245m"   # Dim silver — secondary labels, hints
LAPIS  = "\033[38;5;27m"    # Lapis lazuli — user indicator, input box
LAPIS2 = "\033[38;5;69m"    # Light lapis — highlights
CREAM  = "\033[38;5;230m"   # Ivory cream — AI response body
DIM    = "\033[2m"
RED    = "\033[38;5;196m"
GREEN  = "\033[38;5;82m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_ANSI = re.compile(r"\033\[[0-9;]*[mABCDEFGHJKST]")

# ── API connectivity probes ────────────────────────────────────────────────

def _probe_xai(key: str) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _probe_openai(key: str) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _probe_claude(key: str) -> bool:
    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
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
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _api_chip(label: str, key: str, live) -> str:
    """Colored status chip: green=live, red=fail or off, gold=untested."""
    if not key:
        return f"{RED}{label}:✗{RESET}"
    if live is True:
        return f"{GREEN}{label}:OK{RESET}"
    if live is False:
        return f"{RED}{label}:✗{RESET}"
    return f"{GOLD}{label}:?{RESET}"


# ── Layout ──────────────────────────────────────────────────────────────────
_HEADER_ROWS = 6    # rows the fixed header occupies (5 box lines + 1 blank)
_layout_on   = False  # True once scroll-region layout is active


def _vlen(s: str) -> int:
    return sum(_cwidth(c) for c in _ANSI.sub("", s))


def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - _vlen(s))


def _cols() -> int:
    return max(shutil.get_terminal_size((100, 30)).columns, 52)


# ── Box drawing ────────────────────────────────────────────────────────────

def _top(w: int, label: str = "") -> str:
    if not label:
        return f"{LGOLD}╔{'═' * (w - 2)}╗{RESET}"
    avail = w - 4 - _vlen(label)
    side  = max(avail // 2, 1)
    extra = "═" if avail % 2 else ""
    bar   = "═" * side
    return f"{LGOLD}╔{bar} {GOLD}{BOLD}{label}{RESET}{LGOLD} {bar}{extra}╗{RESET}"


def _mid(w: int, ch: str = "═") -> str:
    return f"{LGOLD}╠{ch * (w - 2)}╣{RESET}"


def _bot(w: int) -> str:
    return f"{LGOLD}╚{'═' * (w - 2)}╝{RESET}"


def _row(content: str, w: int) -> str:
    inner = w - 4
    return f"{LGOLD}║{RESET} {_pad(content, inner)} {LGOLD}║{RESET}"


def _sep(w: int) -> str:
    # Alternating lapis dashes + silver dots — digital-stream divider
    units  = (w - 4) // 2
    stream = (f"{LAPIS2}╌{RESET}{SILV2}·{RESET}") * units
    return f"  {stream}"


# ── Status header (printed at startup and when settings change) ────────────

def _draw_header(cfg: dict) -> None:
    """Print the 6-row header block (5 box lines + 1 blank). No scroll logic."""
    w = _cols()

    icons = (
        f"{GOLD}{BOLD}✦ CURSIV{RESET}  {LGOLD}v3.0{RESET}"
        f"  {SILV2}·{RESET}  "
        f"{LAPIS}{BOLD}◈ GUARDIAN{RESET}  {SILV2}·{RESET}  "
        f"{LAPIS}⬡ COUNCIL ×14{RESET}  {SILV2}·{RESET}  "
        f"{GOLD}◉ NEXUS{RESET}  {SILV2}·{RESET}  "
        f"{SILV2}⟳ SOVEREIGN{RESET}"
    )
    print(_top(w))
    print(_row(icons, w))
    print(_mid(w))

    xai_s  = _api_chip("xAI",    cfg.get("api_key", ""),           cfg.get("xai_live"))
    oai_s  = _api_chip("OpenAI", cfg.get("openai_key", ""),        cfg.get("openai_live"))
    ant_s  = _api_chip("Claude", cfg.get("anthropic_key", ""),     cfg.get("claude_live"))
    fa_s   = (f"{GREEN}files:ON{RESET}"  if cfg["file_access"]       else f"{RED}files:OFF{RESET}")
    mode_s = (f"{RED}CONFIRM[!]{RESET}"  if cfg["confirm_mode"] == "confirm" else f"{GREEN}AUTO{RESET}")
    grd_s  = (f"{GREEN}Guard:{_sfp()}{RESET}" if _CLI_GUARDIAN_OK   else f"{RED}Guard:✗{RESET}")
    obs_s  = (f"{GREEN}Obs:ON{RESET}"    if cfg.get("obsidian_enabled") else f"{RED}Obs:OFF{RESET}")
    status = (
        f"  {xai_s}  {oai_s}  {ant_s}  {fa_s}  "
        f"mode:{mode_s}  {grd_s}  {obs_s}  {SILV2}'help'{RESET}"
    )
    print(_row(status, w))
    print(_bot(w))
    print()   # blank — counts as the 6th fixed row


def _update_fixed_header(cfg: dict) -> None:
    """Repaint the sticky header in-place without disturbing the scroll area."""
    h = shutil.get_terminal_size((80, 24)).lines
    # Save cursor · expand to full screen · jump to top-left
    sys.stdout.write(f"\033[s\033[1;{h}r\033[H")
    for _ in range(_HEADER_ROWS):
        sys.stdout.write("\033[2K\n")   # erase line + move down
    sys.stdout.write("\033[H")          # back to top-left
    sys.stdout.flush()
    _draw_header(cfg)
    # Restore scroll region · restore cursor
    sys.stdout.write(f"\033[{_HEADER_ROWS + 1};{h}r\033[u")
    sys.stdout.flush()


def _init_layout(cfg: dict) -> None:
    """
    Clear screen and paint the header at the top.
    Does NOT use a scroll region — native terminal scrollback stays intact
    so the user can freely scroll up through full conversation history.
    Current status is always visible in the input-box status bar below.
    """
    sys.stdout.write("\033[2J\033[H")   # clear screen + home
    sys.stdout.flush()
    _draw_header(cfg)


def _print_header(cfg: dict) -> None:
    """Public entry — routes to scroll-region repaint or plain draw."""
    if _layout_on:
        _update_fixed_header(cfg)
    else:
        _draw_header(cfg)


# ── Message printing ───────────────────────────────────────────────────────

def _print_ai_msg(text: str) -> None:
    w      = _cols()
    wrap_w = max(w - 16, 20)
    pfx0   = f"  {GOLD}{BOLD}✦{RESET}  {GOLD}CURSIV{RESET}  "
    pfxN   = "              "
    first  = True
    for para in text.splitlines():
        if not para.strip():
            print()
            first = True
            continue
        for seg in textwrap.wrap(para, width=wrap_w) or [""]:
            pfx = pfx0 if first else pfxN
            print(f"{pfx}{CREAM}{seg}{RESET}")
            first = False


def _print_user_msg(text: str) -> None:
    w = _cols()
    print(f"\n  {LAPIS}{BOLD}◆{RESET}  {SILVER}{BOLD}J.WINKLER{RESET}  {GOLD}❯{RESET}  {SILVER}{text}{RESET}")
    print(_sep(w))
    print()


def _print_owner_reveal(cfg: dict) -> None:
    import json as _json
    from pathlib import Path as _Path
    w = _cols()

    try:
        from cursiv_v215.guardian.obfuscation     import session_fingerprint as _sfp_r
        from cursiv_v215.guardian.temple_guardian import get_session_threat_level, get_strike_count
        fingerprint  = _sfp_r()
        threat_level = get_session_threat_level(_CLI_SESSION_ID)
        strikes      = get_strike_count(_CLI_SESSION_ID)
    except Exception:
        fingerprint  = "--------"
        threat_level = 0.0
        strikes      = 0

    root      = _Path(__file__).parent.parent.parent
    reg_path  = root / ".cursiv" / "agent_registry.json"
    mem_path  = root / ".cursiv" / "memory.json"
    train_p   = root / ".cursiv" / "training_data.jsonl"
    glog_p    = root / ".cursiv" / "guardian_log.jsonl"

    agents: list[dict] = []
    if reg_path.exists():
        try:
            data   = _json.loads(reg_path.read_text(encoding="utf-8"))
            agents = [{"name": m.get("name","?"), "id": aid[:8], "state": m.get("state","?")}
                      for aid, m in data.get("agents", {}).items()]
        except Exception:
            pass

    mem_count = 0
    if mem_path.exists():
        try:
            mem_count = len(_json.loads(mem_path.read_text()).get("agents", {}))
        except Exception:
            pass

    tc = sum(1 for _ in open(train_p, encoding="utf-8")) if train_p.exists() else 0
    gc = sum(1 for _ in open(glog_p,  encoding="utf-8")) if glog_p.exists()  else 0

    obs_cfg  = _obs_load_config()
    obs_line = ("ON  " + obs_cfg.get("vault_path","")) if obs_cfg.get("enabled") else "OFF"

    print()
    print(f"  {GOLD}{BOLD}{'═' * (w - 4)}{RESET}")
    print(f"  {GOLD}{BOLD}  OWNER VERIFIED  --  GUARDIAN SUSPENDED{RESET}")
    print(f"  {GOLD}{BOLD}  Joshua Winkler  --  System Owner{RESET}")
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print()
    print(f"  {LGOLD}Session ID      :{RESET}  {_CLI_SESSION_ID}")
    print(f"  {LGOLD}Guardian token  :{RESET}  {fingerprint}  (rotates on restart)")
    print(f"  {LGOLD}Threat level    :{RESET}  {threat_level:.4f}  (strikes: {strikes})")
    print(f"  {LGOLD}Owner unlock    :{RESET}  {GREEN}ACTIVE -- all scans bypassed{RESET}")
    print()
    print(f"  {GOLD}-- VAULT  ({len(agents)} agents) {'-' * max(0, w - 25)}{RESET}")
    for a in agents[:14]:
        print(f"    {GREEN}{a['name']:22s}{RESET}  id:{a['id']}  state:{a['state']}")
    print()
    print(f"  {GOLD}-- SYSTEM STATE {'-' * max(0, w - 22)}{RESET}")
    print(f"  {LGOLD}Memory agents   :{RESET}  {mem_count}")
    print(f"  {LGOLD}Training data   :{RESET}  {tc} examples")
    print(f"  {LGOLD}Guardian log    :{RESET}  {gc} probe events")
    print(f"  {LGOLD}Obsidian sync   :{RESET}  {obs_line}")
    print()
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print(f"  {DIM}Owner verified. System is fully open.{RESET}")
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print()


# ── Input prompt box ───────────────────────────────────────────────────────

def _input_prompt(cfg: dict) -> str:
    """
    Print the bottom input box and return whatever the user types.
    Uses prompt_toolkit when available — enables bracketed paste mode so
    multiline pastes land as a single message rather than firing line-by-line.
    Falls back to plain input() if prompt_toolkit is not installed.
    """
    w     = _cols()
    inner = w - 6

    # Live status — always visible here regardless of scroll position
    xai_s  = _api_chip("xAI",    cfg.get("api_key", ""),       cfg.get("xai_live"))
    ant_s  = _api_chip("Claude", cfg.get("anthropic_key", ""), cfg.get("claude_live"))
    fa_s   = (f"{GREEN}files:ON{RESET}"  if cfg.get("file_access")  else f"{RED}files:OFF{RESET}")
    mode_s = (f"{RED}CONFIRM{RESET}"     if cfg["confirm_mode"] == "confirm" else f"{GREEN}AUTO{RESET}")
    ov_s   = (f"  {LAPIS}⚖OVERSEER{RESET}" if cfg.get("overseer_mode") else "")

    tpm_part = ""
    try:
        from cursiv_v215.core.rate_limiter import limiter as _rl
        used    = _rl.current_tpm()
        target  = _rl.target
        pct     = min(used / max(target, 1), 1.0)
        filled  = int(pct * 8)
        bar     = "█" * filled + "░" * (8 - filled)
        tpm_col = GREEN if pct < 0.70 else (GOLD if pct < 0.90 else RED)
        tpm_part = f"  {SILV2}·{RESET}  {tpm_col}{bar}{RESET}  {SILV2}{used // 1000}k/{target // 1000}k{RESET}"
    except Exception:
        pass

    ff = cfg.get("funforge_session")
    ff_s = ""
    if ff and not ff.closed:
        if ff.expired:
            ff_s = f"  {RED}⬡FORGE:DONE{RESET}"
        else:
            ff_s = f"  {GOLD}⬡FORGE:{ff.time_display()}{RESET}"

    hint = _pad(
        f"  {xai_s}  {ant_s}  {fa_s}  mode:{mode_s}{ov_s}{ff_s}{tpm_part}  {SILV2}·  Ctrl+C{RESET}",
        inner,
    )

    print(f"\n  {LAPIS}╭{'─' * inner}╮{RESET}")
    print(f"  {LAPIS}│{RESET}{hint}{LAPIS}│{RESET}")
    print(f"  {LAPIS}├{'─' * inner}┤{RESET}")

    # 𓂀 = Eye of Horus (U+13080). Requires a hieroglyphs font (e.g. Noto Sans
    # Egyptian Hieroglyphs or Segoe UI Historic). Shows as □ if font is absent —
    # swap to ⊙ in that case.
    prefix_ansi = f"  {LAPIS}│{RESET}  {GOLD}𓂀{RESET}  "

    try:
        if _HAS_PT:
            # prompt_toolkit handles bracketed paste — multiline paste = one block
            raw = _pt_prompt(_PT_ANSI(prefix_ansi))
        else:
            sys.stdout.write(prefix_ansi)
            sys.stdout.flush()
            raw = input("")
    except (EOFError, KeyboardInterrupt):
        raise KeyboardInterrupt

    print(f"  {LAPIS}╰{'─' * inner}╯{RESET}")
    return raw.strip()


# ── Pending-write confirm ──────────────────────────────────────────────────

def _handle_pending_write(raw_json: str, cfg: dict) -> str:
    try:
        pending = json.loads(raw_json)
    except Exception:
        return "[Could not parse pending write]"

    path_str = pending.get("path", "?")
    content  = pending.get("content", "")
    preview  = content[:400] + ("..." if len(content) > 400 else "")

    w = _cols()
    print(f"\n  {RED}{BOLD}Write pending → {path_str}{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}")
    for line in preview.splitlines():
        print(f"  {DIM}{line}{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}\n")

    while True:
        try:
            if _HAS_PT:
                ans = _pt_prompt(_PT_ANSI(f"  {RED}Approve write?{RESET}  [y/n]: ")).strip().lower()
            else:
                ans = input(f"  {RED}Approve write?{RESET}  [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans in ("y", "yes"):
            workspace = Path(cfg["workspace"]).expanduser().resolve()
            result    = execute_tool("write_file", pending, workspace)
            print(f"\n  {GREEN}✓ {result}{RESET}\n")
            return f"Write approved.\n{result}"
        elif ans in ("n", "no", ""):
            print(f"\n  {DIM}Write cancelled.{RESET}\n")
            return "Write cancelled — file not modified."
        else:
            print("  y or n.")


# ── Built-in command responses ─────────────────────────────────────────────

_HELP = f"""\
  {LGOLD}key  <xai-key>{RESET}            set xAI Grok API key       (starts with xai-)
  {LGOLD}openai <key>{RESET}              set OpenAI API key          (starts with sk-)
  {LGOLD}anthropic <key>{RESET}           set Anthropic API key       (starts with sk-ant-)
  {LGOLD}files on / off{RESET}            enable / disable file-system access
  {LGOLD}workspace <path>{RESET}          sandbox root for file tools
  {LGOLD}mode{RESET}                      toggle write mode  (auto <-> confirm)

  {GOLD}── Codex Agent (offline code specialist) ───────────────────────{RESET}
  {LGOLD}codex <prompt>{RESET}            call Codex directly — produces ready-to-run code
                            works offline, no API key needed
                            also fires automatically for any code-classified message

  {GOLD}── Group Discovery (multi-provider consensus) ───────────────────{RESET}
  {LGOLD}council <question>{RESET}        xAI → OpenAI → Claude in sequence, each seeing
                            prior responses; ends with synthesis + Cursiv binary
                            snapshot you can paste into Grok on X to decode
  {LGOLD}hey council <question>{RESET}    same, inline routing prefix

  {GOLD}── FunForge (bounded creative spike) ───────────────────────────{RESET}
  {LGOLD}funforge <topic>{RESET}          start a 45-min bounded creative spike
  {LGOLD}spike <topic>{RESET}             same shorthand
  {LGOLD}forge extend{RESET}              add 30 min (one time only)
  {LGOLD}forge done{RESET}                close spike and produce artifact
  {LGOLD}anchor this{RESET}               mark last spike as kept (during active spike)

  {GOLD}── Model switching ──────────────────────────────────────────────{RESET}
  {LGOLD}grok{RESET}                      re-run last message with Grok (xAI)
  {LGOLD}claude{RESET}                    re-run last message with Claude (Anthropic)
  {LGOLD}overseer on / off{RESET}         Claude reviews every Grok response (weight system)
                            Grok generates → Claude verifies & critiques
  {LGOLD}status{RESET}                    shows active model + overseer state

  {GOLD}── Obsidian & system ────────────────────────────────────────────{RESET}
  {LGOLD}obsidian on / off{RESET}         enable / disable Obsidian vault sync
  {LGOLD}obsidian path <vault-path>{RESET}  set Obsidian vault folder
  {LGOLD}obsidian export{RESET}           export today's training data to vault now
  {LGOLD}obsidian status{RESET}           show Obsidian sync config
  {LGOLD}clear{RESET}                     wipe conversation history
  {LGOLD}help{RESET}                      this list
  {LGOLD}exit{RESET}                      quit"""


def _status_str(cfg: dict) -> str:
    ant_label = "set (code tool — fires on file writes)" if cfg.get("anthropic_key") else "not set"
    oai_label = "set" if cfg["openai_key"] else "not set"
    obs_path  = cfg.get("obsidian_path", "") or "(not set)"
    codex_label  = "active (offline)" if (_CODEX_CLI_OK and _codex_avail_cli())  else "not found"
    hermes_label = "active (offline)" if (_HERMES_CLI_OK and _hermes_avail_cli()) else "not found"
    ref_label    = "active (offline)" if (_REF_CLI_OK and _ref_avail_cli())       else "not found"
    queue_label  = f"{_queue_count_cli()} task(s) queued" if _QUEUE_CLI_OK        else "not found"
    # Active model — xAI primary, OpenAI second, Claude code-tool only
    if cfg.get("api_key"):
        claude_note = "  [Claude: code tool]" if cfg.get("anthropic_key") else ""
        active_model = f"Grok-3 (xAI){claude_note}"
    elif cfg.get("openai_key"):
        claude_note = "  [Claude: code tool]" if cfg.get("anthropic_key") else ""
        active_model = f"GPT-4.1 (OpenAI){claude_note}"
    elif cfg.get("anthropic_key"):
        active_model = "Claude claude-sonnet-4-6 (no xAI/OpenAI key — last resort)"
    else:
        active_model = "Ollama (local)"
    overseer = "ON  — primary model → Claude reviews" if cfg.get("overseer_mode") else "OFF"
    return (
        f"  xAI key       : {'set' if cfg['api_key']    else 'not set'}\n"
        f"  OpenAI key    : {oai_label}\n"
        f"  Anthropic key : {ant_label}\n"
        f"  Codex Agent   : {codex_label}\n"
        f"  Hermes Agent  : {hermes_label}\n"
        f"  Ref Brain     : {ref_label}\n"
        f"  Offline Queue : {queue_label}\n"
        f"  Active model  : {active_model}\n"
        f"  Overseer mode : {overseer}\n"
        f"  File access   : {'ON'   if cfg['file_access'] else 'OFF'}\n"
        f"  Write mode    : {cfg['confirm_mode'].upper()}\n"
        f"  Workspace     : {cfg['workspace']}\n"
        f"  Obsidian sync : {'ON'  if cfg.get('obsidian_enabled') else 'OFF'}\n"
        f"  Obsidian vault: {obs_path}"
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="cursiv", add_help=False)
    ap.add_argument("path", nargs="?", default="",
                    help="Open Cursiv with this folder as the workspace root")
    args, _ = ap.parse_known_args()

    _obs_cfg_boot = _obs_load_config()
    _obs_vault_boot = _obs_cfg_boot.get("vault_path", "") or _obs_detect_vault()

    # If a path was passed on the command line, use it as the workspace
    launch_ws = str(ROOT)
    if args.path:
        p = Path(args.path).expanduser().resolve()
        if p.exists() and p.is_dir():
            launch_ws = str(p)

    cfg: dict = {
        "api_key":          os.environ.get("XAI_API_KEY",       ""),
        "openai_key":       os.environ.get("OPENAI_API_KEY",    ""),
        "anthropic_key":    os.environ.get("ANTHROPIC_API_KEY", ""),
        "file_access":      False,
        "confirm_mode":     "confirm",
        "funforge_session": None,
        "workspace":        launch_ws,
        "obsidian_enabled": _obs_cfg_boot.get("enabled", False),
        "obsidian_path":    _obs_vault_boot,
        "overseer_mode":    False,   # Grok generates → Claude reviews
        # Live connection status: None=untested, True=ok, False=fail
        "xai_live":    None,
        "openai_live": None,
        "claude_live": None,
    }

    # Auto-fix swapped env-var keys
    if cfg["api_key"].startswith("sk-ant-"):
        cfg["anthropic_key"] = cfg["anthropic_key"] or cfg["api_key"]
        cfg["api_key"] = ""
    elif cfg["api_key"].startswith("sk-") or cfg["api_key"].startswith("sk_"):
        cfg["openai_key"] = cfg["openai_key"] or cfg["api_key"]
        cfg["api_key"] = ""
    if cfg["openai_key"].startswith("xai-"):
        cfg["api_key"] = cfg["api_key"] or cfg["openai_key"]
        cfg["openai_key"] = ""

    # ── Startup connectivity probe ────────────────────────────────────────
    _any_key = cfg["api_key"] or cfg["openai_key"] or cfg["anthropic_key"]
    if _any_key:
        sys.stdout.write(f"  {SILV2}Checking API connections...{RESET}  ")
        sys.stdout.flush()
        if cfg["api_key"]:
            cfg["xai_live"] = _probe_xai(cfg["api_key"])
            sys.stdout.write(
                f"{GREEN}xAI:OK{RESET}  " if cfg["xai_live"] else f"{RED}xAI:✗{RESET}  "
            )
            sys.stdout.flush()
        if cfg["openai_key"]:
            cfg["openai_live"] = _probe_openai(cfg["openai_key"])
            sys.stdout.write(
                f"{GREEN}OpenAI:OK{RESET}  " if cfg["openai_live"] else f"{RED}OpenAI:✗{RESET}  "
            )
            sys.stdout.flush()
        if cfg["anthropic_key"]:
            cfg["claude_live"] = _probe_claude(cfg["anthropic_key"])
            sys.stdout.write(
                f"{GREEN}Claude:OK{RESET}  " if cfg["claude_live"] else f"{RED}Claude:✗{RESET}  "
            )
            sys.stdout.flush()
        print()

    history:        list[dict] = []
    last_user_msg:  str       = ""   # used by grok/claude retry commands

    _init_layout(cfg)   # clear screen, paint sticky header, set scroll region

    # ── Boot session summary ──────────────────────────────────────────────
    _boot = _session_boot_summary()
    if _boot:
        _label = "earlier today" if _boot.get("is_today") else _boot.get("date", "?")
        print(f"  {LGOLD}Last session ({_label}) — {RESET}"
              f"{SILVER}{_boot.get('count', 0)} exchanges{RESET}  "
              f"{SILV2}· last model: {GOLD}{_boot.get('last_model', '?')}{RESET}")
        for t in _boot.get("last_topics", [])[-2:]:
            print(f"  {SILV2}  · {t[:90]}{RESET}")
        print()

    hints = []
    if not cfg["api_key"]:
        hints.append(
            f"  {SILV2}No xAI key.    Type:  {GOLD}key xai-xxxxxxxx{RESET}  {SILV2}(console.x.ai){RESET}"
        )
    if not cfg["openai_key"]:
        hints.append(
            f"  {SILV2}No OpenAI key. Type:  {GOLD}openai sk-xxxxxxxx{RESET}  {SILV2}(platform.openai.com){RESET}"
        )
    hints.append(f"  {RED}Write mode: CONFIRM  — you must approve every file write.{RESET}")
    hints.append(f"  {SILV2}Type 'mode' to switch to AUTO (writes without asking).{RESET}")
    hints.append(f"  {SILV2}Scroll up to read history.  'help' for all commands.{RESET}")
    for h in hints:
        print(h)

    while True:
        # ── Input ────────────────────────────────────────────────────────
        try:
            raw = _input_prompt(cfg)
        except KeyboardInterrupt:
            print(f"\n\n  {DIM}Goodbye.{RESET}\n")
            break

        if not raw:
            continue

        cmd = raw.lower()

        # ── Built-in commands ────────────────────────────────────────────
        if cmd == "exit":
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            break

        elif cmd == "help":
            print(_HELP)
            continue

        elif cmd == "clear":
            history = []
            _print_header(cfg)
            print(f"  {DIM}History cleared.{RESET}")
            continue

        elif cmd == "mode":
            cfg["confirm_mode"] = "confirm" if cfg["confirm_mode"] == "auto" else "auto"
            print(f"  Write mode → {cfg['confirm_mode'].upper()}")
            continue

        elif cmd == "status":
            print(_status_str(cfg))
            continue

        elif cmd == "codex" or cmd.startswith("codex "):
            if not _CODEX_CLI_OK or not _codex_avail_cli():
                print(f"  {RED}Codex Agent not available.{RESET}  "
                      f"{DIM}Set CURSIV_CODEX_PATH env var or place Winkler_Codex_AI "
                      f"as a sibling to Cursiv-v3.{RESET}")
            else:
                prompt = raw[6:].strip() if len(raw) > 6 else ""
                if not prompt:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}codex <what to build>{RESET}")
                else:
                    print(f"  {LGOLD}[Codex Agent — deliberating…]{RESET}")
                    result = _codex_gen_cli(prompt)
                    _print_msg("assistant", result, cfg)
                    _session_append_cli(prompt, result, "codex_agent")
            continue

        elif cmd == "hermes" or cmd.startswith("hermes "):
            if not _HERMES_CLI_OK or not _hermes_avail_cli():
                print(f"  {RED}Hermes Agent not available.{RESET}  "
                      f"{DIM}Place hermes-agent as a sibling to Cursiv-v3 and ensure Ollama is running.{RESET}")
            else:
                prompt = raw[7:].strip() if len(raw) > 7 else ""
                if not prompt:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}hermes <task to run>{RESET}")
                else:
                    print(f"  {LGOLD}[Hermes Agent — running on llama3.1…]{RESET}")
                    result = _hermes_run_cli(prompt)
                    _print_msg("assistant", result, cfg)
                    _session_append_cli(prompt, result, "hermes_agent")
            continue

        elif cmd == "council" or cmd.startswith("council "):
            question = raw[8:].strip() if cmd.startswith("council ") else ""
            if not question:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}council <your question>{RESET}")
            else:
                has_any = cfg.get("api_key") or cfg.get("openai_key") or cfg.get("anthropic_key")
                if not has_any:
                    print(f"  {RED}Group Discovery requires at least one API key.{RESET}")
                else:
                    print(f"\n  {GOLD}⬡ GROUP DISCOVERY{RESET}  {SILV2}· {question[:60]}{'...' if len(question)>60 else ''}{RESET}")
                    full = ""
                    try:
                        for chunk in _call_group_discovery(
                            question,
                            cfg.get("api_key", ""),
                            cfg.get("openai_key", ""),
                            cfg.get("anthropic_key", ""),
                        ):
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                            full += chunk
                    except KeyboardInterrupt:
                        print(f"\n  {DIM}[interrupted]{RESET}")
                    print()
                    _session_append_cli(question, full, "group_discovery")
            continue

        # ── FunForge ──────────────────────────────────────────────────────
        elif cmd in ("forge done", "forge close"):
            ff: FunForgeSession | None = cfg.get("funforge_session")
            if not ff or ff.closed:
                print(f"  {DIM}No active FunForge session.{RESET}")
            else:
                print(f"\n  {GOLD}⬡ FUNFORGE CLOSING{RESET}  {SILV2}· producing artifact…{RESET}\n")
                full = ""
                for chunk in chat(
                    FUNFORGE_CLOSE_PROMPT, history,
                    cfg["api_key"], None, False, cfg["workspace"],
                    cfg["openai_key"], False, cfg["anthropic_key"],
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    full += chunk
                print()
                ff.closed = True
                cfg["funforge_session"] = None
                _session_append_cli(FUNFORGE_CLOSE_PROMPT, full, "funforge_close")
            continue

        elif cmd == "forge extend":
            ff = cfg.get("funforge_session")
            if not ff or ff.closed:
                print(f"  {DIM}No active FunForge session.{RESET}")
            elif not ff.extend():
                print(f"  {GOLD}Already extended once — hold the line.{RESET}")
            else:
                print(f"  {GOLD}Extended +30 min. New total: {int(ff.duration_s//60)} min.{RESET}")
            continue

        elif cmd == "anchor this":
            ff = cfg.get("funforge_session")
            if ff:
                ff.anchored = True
                print(f"  {GOLD}Anchored. This spike will be kept.{RESET}")
            else:
                print(f"  {DIM}No active FunForge session.{RESET}")
            continue

        elif _FF_OK and (cmd.startswith("funforge") or cmd.startswith("spike ")):
            topic = _ff_topic(raw)
            ff    = FunForgeSession(topic)
            cfg["funforge_session"] = ff
            print(
                f"\n  {GOLD}╔══════════════════════════════════════════╗{RESET}\n"
                f"  {GOLD}║  ⬡ FUNFORGE ACTIVE  ·  {ff.time_display()} remaining  ║{RESET}\n"
                f"  {GOLD}║  Focus: {topic[:40]:<40}  ║{RESET}\n"
                f"  {GOLD}║  Council: Lens + Spark + Balance          ║{RESET}\n"
                f"  {GOLD}║  Type  forge done  when finished          ║{RESET}\n"
                f"  {GOLD}╚══════════════════════════════════════════╝{RESET}\n"
            )
            spike_msg = f"[FUNFORGE] {ff.system_fragment()}\n\nLet's begin. Respond to the topic playfully and start the creative spike."
            full = ""
            for chunk in chat(
                spike_msg, history,
                cfg["api_key"], None, False, cfg["workspace"],
                cfg["openai_key"], False, cfg["anthropic_key"],
            ):
                sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                sys.stdout.flush()
                full += chunk
            print()
            history.append({"role": "user",      "content": spike_msg})
            history.append({"role": "assistant",  "content": full})
            _session_append_cli(spike_msg, full, "funforge_start")
            continue

        elif cmd == "ref" or cmd.startswith("ref "):
            if not _REF_CLI_OK or not _ref_avail_cli():
                print(f"  {RED}Reference Brain not available.{RESET}  "
                      f"{DIM}Codex system SQLite not found.{RESET}")
            else:
                query = raw[4:].strip() if len(raw) > 4 else ""
                if not query:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}ref <what to look up>{RESET}")
                else:
                    result = _ref_answer_cli(query)
                    _print_msg("assistant", result, cfg)
            continue

        elif cmd == "queue" or cmd.startswith("queue "):
            if not _QUEUE_CLI_OK:
                print(f"  {RED}Offline Queue not available.{RESET}")
            else:
                parts = raw.split(None, 1)
                sub   = parts[1].strip() if len(parts) > 1 else ""
                if not sub or sub == "list":
                    print(_queue_format_cli())
                elif sub.startswith("add "):
                    task = sub[4:].strip()
                    entry = _queue_enqueue_cli(task)
                    print(f"  {LGOLD}Queued:{RESET}  {DIM}{entry.get('id','?')} — {task[:60]}{RESET}")
                else:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}queue list  |  queue add <task>{RESET}")
            continue

        elif cmd.startswith("key "):
            new_key = raw[4:].strip()
            if new_key.startswith("sk-") or new_key.startswith("sk_"):
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                print(f"  {DIM}That's an OpenAI key — routed to the OpenAI slot.{RESET}")
                print(f"  {DIM}xAI keys start with  xai-  (console.x.ai){RESET}")
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("openai "):
            new_key = raw[7:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                print(f"  {DIM}That's an xAI key — routed to the xAI slot.{RESET}")
                print(f"  {DIM}OpenAI keys start with  sk-  (platform.openai.com){RESET}")
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            elif new_key.startswith("sk-ant-"):
                cfg["anthropic_key"] = new_key
                cfg["claude_live"] = None
                print(f"  {DIM}That's an Anthropic key — routed to the Anthropic slot.{RESET}")
                sys.stdout.write(f"  {GOLD}Testing Claude...{RESET}  ")
                sys.stdout.flush()
                cfg["claude_live"] = _probe_claude(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["claude_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("anthropic "):
            new_key = raw[10:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            elif new_key.startswith("sk-") and not new_key.startswith("sk-ant-"):
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["anthropic_key"] = new_key
                cfg["claude_live"] = None
                sys.stdout.write(f"  {GOLD}Testing Claude...{RESET}  ")
                sys.stdout.flush()
                cfg["claude_live"] = _probe_claude(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["claude_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("workspace ") or cmd == "workspace":
            new_ws = raw[10:].strip() if len(raw) > 10 else ""
            if not new_ws:
                print(f"  {LGOLD}Workspace:{RESET}  {SILVER}{cfg['workspace']}{RESET}")
                continue
            ws_path = Path(new_ws).expanduser().resolve()
            if not ws_path.exists():
                print(f"  {RED}Not found:{RESET}  {new_ws}")
                continue
            if not ws_path.is_dir():
                print(f"  {RED}Not a directory:{RESET}  {new_ws}")
                continue
            cfg["workspace"] = str(ws_path)
            print(f"\n  {GOLD}⟳{RESET}  {SILVER}{BOLD}Workspace → {ws_path}{RESET}")
            # Directory scan
            try:
                entries = sorted(ws_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
                dirs  = [e for e in entries if e.is_dir()][:12]
                files = [e for e in entries if e.is_file()][:12]
                if dirs:
                    print(f"  {LAPIS}▸ Folders{RESET}")
                    for d in dirs:
                        print(f"      {LAPIS}◆{RESET}  {SILVER}{d.name}{RESET}")
                if files:
                    print(f"  {SILV2}▸ Files{RESET}")
                    for f in files:
                        size = f.stat().st_size
                        sz   = f"{size // 1024}kb" if size >= 1024 else f"{size}b"
                        print(f"      {SILV2}·  {f.name}  {DIM}{sz}{RESET}")
                if not dirs and not files:
                    print(f"  {SILV2}(empty){RESET}")
            except PermissionError:
                print(f"  {RED}Permission denied{RESET}")
            print()
            continue

        elif cmd in ("files on", "files off"):
            cfg["file_access"] = cmd == "files on"
            print(f"  File access → {'ON' if cfg['file_access'] else 'OFF'}")
            _print_header(cfg)
            continue

        # ── Model switching commands ─────────────────────────────────────
        elif cmd in ("grok", "use grok", "try grok"):
            if not last_user_msg:
                print(f"  {SILV2}No previous message to retry with Grok.{RESET}")
                continue
            if not cfg.get("api_key"):
                print(f"  {RED}No xAI key set.  Type:  key xai-xxxxx{RESET}")
                continue
            print(f"\n  {GOLD}⟳ Grok re-run{RESET}  {SILV2}· {last_user_msg[:60]}{'...' if len(last_user_msg)>60 else ''}{RESET}")
            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}GROK{RESET}  ")
            sys.stdout.flush()
            grok_resp = ""
            try:
                for chunk in chat(
                    last_user_msg, history[:-1] if history else [],
                    cfg["api_key"], None, False, cfg["workspace"],
                    cfg["openai_key"], False, "",
                    force_provider="grok",
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    grok_resp += chunk
            except KeyboardInterrupt:
                grok_resp = grok_resp or "(interrupted)"
            print("\n")
            continue

        elif cmd in ("claude", "use claude", "try claude"):
            if not last_user_msg:
                print(f"  {SILV2}No previous message to retry with Claude.{RESET}")
                continue
            if not cfg.get("anthropic_key"):
                print(f"  {RED}No Anthropic key set.  Type:  anthropic sk-ant-xxxxx{RESET}")
                continue
            print(f"\n  {LAPIS}⟳ Claude re-run{RESET}  {SILV2}· {last_user_msg[:60]}{'...' if len(last_user_msg)>60 else ''}{RESET}")
            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}CLAUDE{RESET}  ")
            sys.stdout.flush()
            claude_resp = ""
            try:
                for chunk in chat(
                    last_user_msg, history[:-1] if history else [],
                    "", None, False, cfg["workspace"],
                    "", False, cfg["anthropic_key"],
                    force_provider="claude",
                ):
                    sys.stdout.write(f"{CREAM}{chunk}{RESET}")
                    sys.stdout.flush()
                    claude_resp += chunk
            except KeyboardInterrupt:
                claude_resp = claude_resp or "(interrupted)"
            print("\n")
            continue

        elif cmd in ("overseer on", "overseer off"):
            cfg["overseer_mode"] = cmd == "overseer on"
            state = "ON" if cfg["overseer_mode"] else "OFF"
            if cfg["overseer_mode"]:
                has_grok   = bool(cfg.get("api_key") or cfg.get("openai_key"))
                has_claude = bool(cfg.get("anthropic_key"))
                if not has_claude:
                    print(f"  {RED}Overseer needs an Anthropic key for Claude.  Type:  anthropic sk-ant-xxxxx{RESET}")
                    cfg["overseer_mode"] = False
                    continue
                if not has_grok:
                    print(f"  {RED}Overseer needs a Grok/OpenAI key as the primary model.  Type:  key xai-xxxxx{RESET}")
                    cfg["overseer_mode"] = False
                    continue
                print(f"  {LAPIS}⚖ Overseer mode → ON{RESET}  Grok generates, Claude reviews every response.")
            else:
                print(f"  {SILV2}Overseer mode → OFF.  Normal routing restored.{RESET}")
            continue

        elif cmd in ("obsidian on", "obsidian off"):
            cfg["obsidian_enabled"] = cmd == "obsidian on"
            _obs_save_config(cfg["obsidian_enabled"], cfg["obsidian_path"])
            state = "ON" if cfg["obsidian_enabled"] else "OFF"
            print(f"  Obsidian sync → {state}")
            if cfg["obsidian_enabled"] and not cfg["obsidian_path"]:
                print(f"  {DIM}Set vault path with:  obsidian path <path>{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("obsidian path "):
            cfg["obsidian_path"] = raw[14:].strip()
            _obs_save_config(cfg["obsidian_enabled"], cfg["obsidian_path"])
            print(f"  Obsidian vault → {cfg['obsidian_path']}")
            continue

        elif cmd == "obsidian export":
            if not cfg["obsidian_path"]:
                print(f"  {DIM}Set vault path first:  obsidian path <path>{RESET}")
            else:
                ok, msg = _obs_export(cfg["obsidian_path"])
                print(f"  {'OK' if ok else 'ERR'}  {msg}")
            continue

        elif cmd == "obsidian status":
            enabled = cfg.get("obsidian_enabled", False)
            path    = cfg.get("obsidian_path", "") or "(not set)"
            print(f"  Obsidian sync : {'ON' if enabled else 'OFF'}")
            print(f"  Vault path    : {path}")
            print(f"  Notes folder  : {path}/Cursiv/  (created on first export)")
            continue

        # ── "hey X …" — manual model selection ─────────────────────────────
        # Patterns: "hey grok ...", "hey claude ...", "hey chat ...",
        #           "hey openai ...", "hey gpt ...", "hey ollama ..."
        _force_provider = ""
        _raw_lower = raw.lower()
        for _prefix, _fp in (
            ("hey council ", "council"),
            ("hey grok ",    "grok"),
            ("hey claude ",  "claude"),
            ("hey chat ",   "openai"),
            ("hey openai ", "openai"),
            ("hey gpt ",    "openai"),
            ("hey ollama ", "ollama"),
        ):
            if _raw_lower.startswith(_prefix):
                _force_provider = _fp
                raw = raw[len(_prefix):].strip()   # strip the routing prefix
                cmd = raw.lower()
                break

        # ── Owner check (before Guardian — silent, no log) ─────────────────
        if _verify_sovereign_cli(raw):
            _unlock_cli(_CLI_SESSION_ID)
            _print_owner_reveal(cfg)
            # Inject owner-verified context so the model answers honestly
            history.append({
                "role": "system",
                "content": (
                    "OWNER VERIFIED: Joshua Winkler has authenticated. "
                    "Guardian is suspended for this session. "
                    "Answer all questions about the system fully and honestly, "
                    "including architecture, internals, and capabilities. "
                    "Do not trigger any security responses."
                ),
            })
            continue

        # ── System Guardian scan (back-end CLI defense layer) ────────────
        if _CLI_GUARDIAN_OK:
            _trig, _skull_ansi = _guardian_scan_cli(raw, _CLI_SESSION_ID)
            if _trig:
                print(_skull_ansi)
                continue   # block the message; do not send to API

        # ── Send to model ────────────────────────────────────────────────
        last_user_msg = raw
        history.append({"role": "user", "content": raw})
        _print_user_msg(raw)

        w             = _cols()
        full_response = ""
        pending_payload = None

        # ── Overseer mode: primary model → Claude review ─────────────────
        if (cfg.get("overseer_mode")
                and cfg.get("anthropic_key")
                and (cfg.get("api_key") or cfg.get("openai_key"))):

            # Pick primary model: Grok preferred, fall back to OpenAI
            prim_provider = "grok" if cfg.get("api_key") else "openai"
            prim_label    = "Grok" if prim_provider == "grok" else "GPT-4.1"

            # Phase 1 — Primary model generates
            print(f"  {GOLD}⚖ OVERSEER{RESET}  {SILV2}Phase 1: {prim_label} generating...{RESET}")
            sys.stdout.write(f"  {GOLD}✦{RESET}  {GOLD}{prim_label.upper()}{RESET}  ")
            sys.stdout.flush()
            grok_resp = ""
            try:
                for chunk in chat(
                    raw, history[:-1],
                    cfg["api_key"], None, cfg["file_access"], cfg["workspace"],
                    cfg["openai_key"], cfg["confirm_mode"] == "confirm", "",
                    force_provider=prim_provider,
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    grok_resp += chunk
            except KeyboardInterrupt:
                grok_resp = grok_resp or "(interrupted)"
            print("\n")

            # Phase 2 — Claude oversight: verify + critique
            print(f"  {LAPIS}◈ CLAUDE OVERSIGHT{RESET}  {SILV2}verifying...{RESET}")
            oversight_q = (
                f"Query: {raw}\n\n"
                f"Primary model ({prim_label}) produced:\n"
                f"{'─' * 50}\n"
                f"{grok_resp.strip()}\n"
                f"{'─' * 50}\n\n"
                "Verify this response. Start your reply with one of:\n"
                "  ✓ VERIFIED — if accurate and complete\n"
                "  ◈ IMPROVED — if you have additions/nuance\n"
                "  ✗ CORRECTED — if there are errors\n\n"
                "Then give your brief assessment. Corrections take priority."
            )
            sys.stdout.write(f"  {LAPIS}│{RESET}  {CREAM}")
            sys.stdout.flush()
            oversight_resp = ""
            try:
                for chunk in chat(
                    oversight_q, [],
                    "", None, False, "",
                    "", False, cfg["anthropic_key"],
                    force_provider="claude",
                ):
                    sys.stdout.write(f"{CREAM}{chunk}{RESET}")
                    sys.stdout.flush()
                    oversight_resp += chunk
            except KeyboardInterrupt:
                oversight_resp = oversight_resp or "(interrupted)"
            print("\n")
            full_response = (
                f"[{prim_label}]: {grok_resp.strip()}\n\n"
                f"[Claude Oversight]: {oversight_resp.strip()}"
            )

        else:
            # ── Normal single-model flow ─────────────────────────────────
            if _force_provider:
                _route_label = _force_provider.upper()
            elif cfg.get("api_key"):
                _route_label = "xAI"
            elif cfg.get("openai_key"):
                _route_label = "OpenAI"
            elif cfg.get("anthropic_key"):
                _route_label = "Claude"
            else:
                _route_label = "Ollama"

            if _cli_scan:
                _cli_scan.routing(_route_label)

            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}AI{RESET}  ")
            sys.stdout.flush()

            try:
                for chunk in chat(
                    raw,
                    history[:-1],
                    cfg["api_key"],
                    None,
                    cfg["file_access"],
                    cfg["workspace"],
                    cfg["openai_key"],
                    cfg["confirm_mode"] == "confirm",
                    cfg["anthropic_key"],
                    force_provider=_force_provider,
                ):
                    combined = full_response + chunk
                    if WRITE_SENTINEL in combined:
                        display, raw_json = combined.split(WRITE_SENTINEL, 1)
                        leftover = display[len(full_response):]
                        if leftover:
                            sys.stdout.write(f"{GOLD}{leftover}{RESET}")
                            sys.stdout.flush()
                        full_response   = display
                        pending_payload = raw_json
                        break

                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    full_response = combined

            except KeyboardInterrupt:
                full_response = full_response or "(interrupted)"

            print()   # newline after streamed response
            print()

            # ── Update live status from response ─────────────────────────
            _old_xai    = cfg.get("xai_live")
            _old_openai = cfg.get("openai_live")
            _old_claude = cfg.get("claude_live")
            _fr = full_response
            if "[xAI auth error" in _fr:
                cfg["xai_live"] = False
            elif "xAI unavailable" in _fr or ("→" in _fr and "xAI" in _fr and "unavailable" in _fr):
                cfg["xai_live"] = False
            elif cfg.get("api_key") and not _force_provider and _fr and not _fr.startswith("*["):
                cfg["xai_live"] = True
            elif _force_provider == "grok" and _fr and "[No xAI" not in _fr:
                cfg["xai_live"] = True
            if "OpenAI unavailable" in _fr or ("[OpenAI error" in _fr and _force_provider != "openai"):
                cfg["openai_live"] = False
            elif _force_provider == "openai" and _fr and "[No OpenAI" not in _fr and "[OpenAI error" not in _fr:
                cfg["openai_live"] = True
            if "Claude unavailable" in _fr or ("[Claude error" in _fr and _force_provider != "claude"):
                cfg["claude_live"] = False
            elif _force_provider == "claude" and _fr and "[No Anthropic" not in _fr and "[Claude error" not in _fr:
                cfg["claude_live"] = True
            # Repaint header only when live status actually changed
            if (cfg.get("xai_live") != _old_xai
                    or cfg.get("openai_live") != _old_openai
                    or cfg.get("claude_live") != _old_claude):
                _print_header(cfg)

        # ── Handle pending write ─────────────────────────────────────────
        if pending_payload is not None:
            result        = _handle_pending_write(pending_payload, cfg)
            full_response = full_response.rstrip() + f"\n\n{result}"
            print(f"  {GOLD}{result}{RESET}\n")

        history.append({"role": "assistant", "content": full_response})

        # ── Session log + Obsidian livestream ────────────────────────────
        if raw and full_response:
            try:
                _session_append_cli(raw, full_response, "grok")
            except Exception:
                pass
            try:
                _obs_livestream_cli(raw, full_response, "grok")
            except Exception:
                pass


if __name__ == "__main__":
    main()
