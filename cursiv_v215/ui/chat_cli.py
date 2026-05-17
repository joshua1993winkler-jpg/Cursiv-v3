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
from pathlib import Path

# Force UTF-8 stdout — prevents surrogate/emoji crashes on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent.parent))

from cursiv_v215.ui.chat_app import (
    WRITE_SENTINEL,
    ROOT,
    chat,
    execute_tool,
)

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
GOLD  = "\033[38;5;220m"
LGOLD = "\033[38;5;179m"
LAPIS = "\033[38;5;68m"
CREAM = "\033[38;5;230m"
DIM   = "\033[2m"
RED   = "\033[38;5;196m"
GREEN = "\033[38;5;82m"
BOLD  = "\033[1m"
RESET = "\033[0m"

_ANSI = re.compile(r"\033\[[0-9;]*[mABCDEFGHJKST]")


def _vlen(s: str) -> int:
    return sum(_cwidth(c) for c in _ANSI.sub("", s))


def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - _vlen(s))


def _cols() -> int:
    return max(shutil.get_terminal_size((100, 30)).columns, 52)


# ── Box drawing ────────────────────────────────────────────────────────────

def _top(w: int, label: str) -> str:
    # avail = space for bars only: total width minus 2 corners, 2 spaces, label
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
    return f"  {DIM}{'·' * (w - 4)}{RESET}"


# ── Status header (printed at startup and when settings change) ────────────

def _print_header(cfg: dict) -> None:
    w      = _cols()
    xai_s  = f"{GREEN}xAI:OK{RESET}"     if cfg["api_key"]            else f"{DIM}xAI:--{RESET}"
    oai_s  = f"{GREEN}OpenAI:OK{RESET}"  if cfg["openai_key"]         else f"{DIM}OpenAI:--{RESET}"
    ant_s  = f"{GREEN}Claude:OK{RESET}"  if cfg.get("anthropic_key")  else f"{DIM}Claude:--{RESET}"
    fa_s   = f"{GREEN}files:ON{RESET}"   if cfg["file_access"]        else f"{DIM}files:OFF{RESET}"
    mode_s = (f"{RED}CONFIRM[!]{RESET}"  if cfg["confirm_mode"] == "confirm"
              else f"{DIM}AUTO{RESET}")
    grd_s  = f"{GREEN}Guardian:{_sfp()}{RESET}" if _CLI_GUARDIAN_OK else f"{DIM}Guardian:--{RESET}"
    obs_s  = (f"{GREEN}Obsidian:ON{RESET}" if cfg.get("obsidian_enabled")
              else f"{DIM}Obsidian:OFF{RESET}")
    status = (f"  {xai_s}  {oai_s}  {ant_s}  {fa_s}  "
              f"mode:{mode_s}  {grd_s}  {obs_s}  {DIM}'help'{RESET}")
    print(_top(w, "Cursiv v3.0"))
    print(_row(status, w))
    print(_bot(w))
    print()


# ── Message printing ───────────────────────────────────────────────────────

def _print_ai_msg(text: str) -> None:
    w      = _cols()
    wrap_w = max(w - 14, 20)
    pfx0   = f"  {GOLD}{BOLD}  ✦ AI{RESET}  "
    pfxN   = "          "
    first  = True
    for para in text.splitlines():
        if not para.strip():
            print()
            first = True
            continue
        for seg in textwrap.wrap(para, width=wrap_w) or [""]:
            pfx = pfx0 if first else pfxN
            print(f"{pfx}{GOLD}{seg}{RESET}")
            first = False


def _print_user_msg(text: str) -> None:
    w = _cols()
    print(f"\n  {LAPIS}{BOLD}You  ❯{RESET}  {CREAM}{text}{RESET}")
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
    print(f"  {DIM}The Temple recognizes its builder. System is fully open.{RESET}")
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
    w      = _cols()
    inner  = w - 6
    mode_s = (f"{RED}CONFIRM[!]{RESET}" if cfg["confirm_mode"] == "confirm"
              else f"{DIM}AUTO{RESET}")
    hint   = _pad(f"  mode:{mode_s}  ·  Ctrl+C to exit", inner)

    print(f"\n  {LGOLD}╭{'─' * inner}╮{RESET}")
    print(f"  {LGOLD}│{RESET}{hint}{LGOLD}│{RESET}")
    print(f"  {LGOLD}├{'─' * inner}┤{RESET}")

    # The prompt prefix printed before the cursor
    prefix_ansi = f"  {LGOLD}│{RESET}  {LAPIS}{BOLD}❯{RESET}  "

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

    print(f"  {LGOLD}╰{'─' * inner}╯{RESET}")
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
  {LGOLD}obsidian on / off{RESET}         enable / disable Obsidian vault sync
  {LGOLD}obsidian path <vault-path>{RESET}  set Obsidian vault folder
  {LGOLD}obsidian export{RESET}           export today's training data to vault now
  {LGOLD}obsidian status{RESET}           show Obsidian sync config
  {LGOLD}clear{RESET}                     wipe conversation history
  {LGOLD}status{RESET}                    show current config
  {LGOLD}help{RESET}                      this list
  {LGOLD}exit{RESET}                      quit"""


def _status_str(cfg: dict) -> str:
    ant_label = "Claude (priority)" if cfg.get("anthropic_key") else "not set"
    oai_label = "set" if cfg["openai_key"] else ("fallback — not set" if not cfg.get("anthropic_key") else "set (overridden by Claude)")
    obs_path  = cfg.get("obsidian_path", "") or "(not set)"
    return (
        f"  xAI key       : {'set' if cfg['api_key']    else 'not set'}\n"
        f"  OpenAI key    : {oai_label}\n"
        f"  Anthropic key : {ant_label}\n"
        f"  File access   : {'ON'   if cfg['file_access'] else 'OFF'}\n"
        f"  Write mode    : {cfg['confirm_mode'].upper()}\n"
        f"  Workspace     : {cfg['workspace']}\n"
        f"  Obsidian sync : {'ON'  if cfg.get('obsidian_enabled') else 'OFF'}\n"
        f"  Obsidian vault: {obs_path}"
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    _obs_cfg_boot = _obs_load_config()
    _obs_vault_boot = _obs_cfg_boot.get("vault_path", "") or _obs_detect_vault()

    cfg: dict = {
        "api_key":          os.environ.get("XAI_API_KEY",       ""),
        "openai_key":       os.environ.get("OPENAI_API_KEY",    ""),
        "anthropic_key":    os.environ.get("ANTHROPIC_API_KEY", ""),
        "file_access":      False,
        "confirm_mode":     "confirm",
        "workspace":        str(ROOT),
        "obsidian_enabled": _obs_cfg_boot.get("enabled", False),
        "obsidian_path":    _obs_vault_boot,
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

    history: list[dict] = []

    _print_header(cfg)

    # ── Boot session summary ──────────────────────────────────────────────
    _boot = _session_boot_summary()
    if _boot:
        _label = "earlier today" if _boot.get("is_today") else _boot.get("date", "?")
        print(f"  {GOLD}Last session ({_label}) — {_boot.get('count', 0)} exchanges  "
              f"· last model: {_boot.get('last_model', '?')}{RESET}")
        for t in _boot.get("last_topics", [])[-2:]:
            print(f"  {DIM}  · {t[:90]}{RESET}")
        print()

    hints = []
    if not cfg["api_key"]:
        hints.append(f"  No xAI key.    Type:  {LGOLD}key xai-xxxxxxxx{RESET}  (console.x.ai)")
    if not cfg["openai_key"]:
        hints.append(f"  No OpenAI key. Type:  {LGOLD}openai sk-xxxxxxxx{RESET}  (platform.openai.com)")
    hints.append(f"  {RED}Write mode: CONFIRM  -- you must approve every file write.{RESET}")
    hints.append(f"  {DIM}Type 'mode' to switch to AUTO (writes without asking).{RESET}")
    hints.append(f"  {DIM}Scroll up to read history.  'help' for all commands.{RESET}")
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

        elif cmd.startswith("key "):
            new_key = raw[4:].strip()
            if new_key.startswith("sk-") or new_key.startswith("sk_"):
                cfg["openai_key"] = new_key
                print(f"  {DIM}That's an OpenAI key — routed to the OpenAI slot. ✓{RESET}")
                print(f"  {DIM}xAI keys start with  xai-  (console.x.ai){RESET}")
            else:
                cfg["api_key"] = new_key
                print(f"  {GREEN}xAI key set. ✓{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("openai "):
            new_key = raw[7:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                print(f"  {DIM}That's an xAI key — routed to the xAI slot. ✓{RESET}")
                print(f"  {DIM}OpenAI keys start with  sk-  (platform.openai.com){RESET}")
            elif new_key.startswith("sk-ant-"):
                cfg["anthropic_key"] = new_key
                print(f"  {DIM}That's an Anthropic key — routed to the Anthropic slot. ✓{RESET}")
            else:
                cfg["openai_key"] = new_key
                print(f"  {GREEN}OpenAI key set. ✓{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("anthropic "):
            new_key = raw[10:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                print(f"  {DIM}That's an xAI key — routed to the xAI slot. ✓{RESET}")
            elif new_key.startswith("sk-") and not new_key.startswith("sk-ant-"):
                cfg["openai_key"] = new_key
                print(f"  {DIM}That's an OpenAI key — routed to the OpenAI slot. ✓{RESET}")
            else:
                cfg["anthropic_key"] = new_key
                print(f"  {GREEN}Anthropic key set. ✓  Claude {RESET}is ready for code generation.")
            _print_header(cfg)
            continue

        elif cmd.startswith("workspace "):
            cfg["workspace"] = raw[10:].strip()
            print(f"  Workspace → {cfg['workspace']}")
            continue

        elif cmd in ("files on", "files off"):
            cfg["file_access"] = cmd == "files on"
            print(f"  File access → {'ON' if cfg['file_access'] else 'OFF'}")
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

        # ── Sovereign owner check (before Guardian — silent, no log) ────────
        if _verify_sovereign_cli(raw):
            _unlock_cli(_CLI_SESSION_ID)
            _print_owner_reveal(cfg)
            continue

        # ── System Guardian scan (back-end CLI defense layer) ────────────
        if _CLI_GUARDIAN_OK:
            _trig, _skull_ansi = _guardian_scan_cli(raw, _CLI_SESSION_ID)
            if _trig:
                print(_skull_ansi)
                continue   # block the message; do not send to API

        # ── Send to model ────────────────────────────────────────────────
        history.append({"role": "user", "content": raw})
        _print_user_msg(raw)

        # AI prefix — stream tokens directly below it
        w     = _cols()
        pfx0  = f"  {GOLD}{BOLD}  ✦ AI{RESET}  "
        pfxN  = "          "
        sys.stdout.write(pfx0)
        sys.stdout.flush()

        full_response   = ""
        pending_payload = None
        line_len        = 0          # visible chars on the current output line
        wrap_w          = max(w - 14, 20)
        first_line      = True

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
            ):
                combined = full_response + chunk
                if WRITE_SENTINEL in combined:
                    display, raw_json = combined.split(WRITE_SENTINEL, 1)
                    # Print whatever came before the sentinel
                    leftover = display[len(full_response):]
                    if leftover:
                        sys.stdout.write(f"{GOLD}{leftover}{RESET}")
                        sys.stdout.flush()
                    full_response   = display
                    pending_payload = raw_json
                    break

                # Simple direct streaming — terminal wraps naturally
                sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                sys.stdout.flush()
                full_response = combined

        except KeyboardInterrupt:
            full_response = full_response or "(interrupted)"

        print()   # newline after streamed response
        print()

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
