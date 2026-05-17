# ⬡ Cursiv v3.0

> **An autonomous AI operating system built for one purpose: executing at the frontier.**
> Triple-model intelligence (xAI Grok · OpenAI GPT-4.1 · Anthropic Claude), live file tools, a 14-agent vault council, Guardian firewall, Obsidian live sync, and persistent session memory — all running locally on your machine.

<br>

---

## What Is This?

**Cursiv** is a self-contained AI workspace that wires together xAI, OpenAI, and Anthropic into a single local system. It's not a wrapper — it's a full operating environment:

- **Main Chat UI** — Sacred-aesthetic Gradio interface, streaming AI responses, image and file uploads, smart model routing
- **Terminal Chat** — Full-screen CLI with ANSI gold/lapis styling, paste-safe input, no browser needed
- **Nexus Panel** — 14-agent command council with live status, yin-yang balance tracking, and identity drift monitoring
- **File System Tools** — AI reads, writes, searches, and organizes your codebase autonomously
- **Confirm-Before-Write** — Every file write requires your approval before execution (toggleable)
- **Training Pipeline** — Save any conversation exchange to a JSONL training dataset with one click
- **PiForge Vault** — 14 phase-seeded agents loaded into every conversation as living system context
- **Obsidian Live Sync** — Every exchange streamed in real time to your Obsidian vault as structured Markdown
- **Persistent Session Memory** — System remembers prior sessions, greets you with context on every boot
- **Guardian Firewall** — Active 4-layer defense against probing, injection, and jailbreak attempts
- **System Vision** — Double-click `system_vision.html` for an 8K-quality animated node visualization of the entire framework

<br>

---

## Quick Start — One Click

**Prerequisites:** Python 3.10+ and pip installed.

### 1. Clone the repo
```bash
git clone https://github.com/joshua1993winkler-jpg/Cursiv-v2.1.5.git
cd Cursiv-v2.1.5
```

### 2. Run setup
Double-click **`Setup and Launch Cursiv.bat`**

*Installs all dependencies automatically — no manual pip commands needed.*

### 3. Add your API keys
Create a file called **`secrets.bat`** in the project root:
```bat
@echo off
set XAI_API_KEY=xai-your-key-here
set OPENAI_API_KEY=sk-your-key-here
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> **Get your keys:**
> - xAI Grok → [console.x.ai](https://console.x.ai)
> - OpenAI GPT-4.1 → [platform.openai.com](https://platform.openai.com)
> - Anthropic Claude → [console.anthropic.com](https://console.anthropic.com)

### 4. Launch
| What | How |
|------|-----|
| Everything at once | Double-click **`START CURSIV SYSTEM.bat`** |
| Terminal Chat only | Double-click **`Launch Chat CLI.bat`** |
| Gradio Web UI only | Double-click **`Launch Chat.bat`** → open `http://localhost:7860` |
| Nexus Panel only | Double-click **`Launch Nexus.bat`** → open `http://localhost:7861` |
| System visualization | Double-click **`system_vision.html`** (no server needed) |

### 5. Seed the PiForge vault (first time only)
Double-click **`Import PiForge.bat`** to load all 14 phase agents into the vault.
After seeding, every conversation carries the full agent council as context automatically.

<br>

---

## API Keys — Your Options

**Option A — `secrets.bat` *(recommended, git-ignored)***
Create `secrets.bat` in the project root. It loads automatically on every launch. Supports all three APIs.

**Option B — System environment variables**
Set `XAI_API_KEY`, `OPENAI_API_KEY`, and/or `ANTHROPIC_API_KEY` in Windows System Properties → Advanced → Environment Variables.

**Option C — Enter manually in the chat**
In Terminal Chat:
```
key xai-xxxxxxxx
openai sk-xxxxxxxx
anthropic sk-ant-xxxxxxxx
```
In the Gradio UI, paste into the key slots at the top of the page.

> `secrets.bat` is listed in `.gitignore` — it will **never** be committed or pushed. Your keys stay on your machine only.

<br>

---

## Triple-Model Smart Routing

Cursiv v3.0 automatically routes each message to the best model for the task:

```
User message
     │
     ▼
 Classify ─── code / creative / general
     │
     ├─ code  +  Anthropic key  →  Claude Sonnet (reasoning + code quality)
     ├─ code  +  OpenAI key     →  GPT-4.1       (code generation + review)
     │
     └─ general / creative      →  xAI Grok-3    (reasoning, plans, conversation)
                                        │
                                        └─ on write_file → GPT-4.1 rewrites to prod quality
```

- Code keywords (`def`, `class`, backtick blocks, `Error:`, `Traceback`, etc.) trigger code routing
- Claude is prioritized for code when your Anthropic key is present (superior reasoning)
- GPT-4.1 intercepts every file write for production-quality output regardless of routing
- Falls back to local **Ollama** (Mistral) if no API keys are configured

<br>

---

## Terminal Chat — Commands

Once inside the terminal chat:

| Command | What it does |
|---------|-------------|
| `key xai-xxx` | Set xAI Grok API key |
| `openai sk-xxx` | Set OpenAI API key |
| `anthropic sk-ant-xxx` | Set Anthropic Claude API key |
| `files on` / `files off` | Enable / disable file system access |
| `workspace <path>` | Set the sandbox root for file operations |
| `mode` | Toggle write mode: CONFIRM ✋ ↔ AUTO ⚡ |
| `obsidian on` / `obsidian off` | Toggle Obsidian vault sync |
| `obsidian path <path>` | Set your Obsidian vault path |
| `obsidian export` | Export today's training data to Obsidian now |
| `obsidian status` | Show Obsidian sync config |
| `status` | Show full current config |
| `clear` | Wipe conversation history |
| `help` | List all commands |
| `exit` / `Ctrl+C` | Quit |

> Tip: Paste multi-line prompts freely — the terminal uses `prompt_toolkit` for paste-safe input. Your entire paste lands as one message.

<br>

---

## File System Tools

When `files on` is active, the AI has access to these tools:

| Tool | Description |
|------|-------------|
| `submit_plan` | AI submits a full build plan before writing anything |
| `read_file` | Read any file in the workspace |
| `write_file` | Create or overwrite a file |
| `list_directory` | List files and folders |
| `search_files` | Glob pattern search (e.g. `**/*.py`) |
| `create_directory` | Create a directory tree |
| `delete_file` | Delete a file |

All file operations are **sandboxed** to the workspace root. Path traversal is structurally blocked at the resolver before any I/O occurs.

**Write modes:**
- ✋ **CONFIRM** *(default)* — AI shows you the file content and waits for `y/n`
- ⚡ **AUTO** — Writes execute immediately. Toggle with `mode` in terminal.

<br>

---

## Obsidian Live Sync

Turn on Obsidian sync and every exchange is appended to your vault in real time:

- **Live streaming** — each completed exchange appears in `{vault}/Cursiv/YYYY-MM-DD.md` immediately after the AI responds
- **Training export** — on-demand export of the day's training data as a structured Markdown note with YAML frontmatter (Dataview-compatible), summary table, and blockquote pairs
- **Auto-detect** — the system scans your Documents, OneDrive, and Desktop for an Obsidian vault (`.obsidian/` folder) automatically
- Notes include quality scores, model labels, and source metadata for every exchange

In the Gradio UI: check the **Obsidian sync** checkbox → paste vault path → click **Export Now**.
In the terminal: `obsidian on` → `obsidian path <your-vault-path>`.

<br>

---

## Persistent Session Memory

The system logs every exchange to `.cursiv/sessions/YYYY-MM-DD.jsonl` and uses it across restarts:

- On boot, the CLI greets you with a summary of the last session — date, exchange count, last model used, and recent topics
- The last 4 exchanges are injected into the system prompt so the AI has continuity across restarts
- Session files are labeled "today (earlier)" vs. the prior date so the AI knows the recency of context
- No personal data leaves your machine — session logs stay local in `.cursiv/sessions/`

<br>

---

## The Nexus Panel

The Nexus (`http://localhost:7861`) is your command center:

- **14-Agent Council** — Assign agents to domains and tasks; assignments inject into the main chat automatically
- **Yin-Yang Balance** — 7 axes tracked in real time (depth/speed, structure/flow, individual/civilization, and more)
- **Identity Drift Monitor** — Constitutional guardrails with a 3% abort threshold and verified invariants
- **Training Dashboard** — View, manage, and export your conversation training dataset
- **Full Cycle** — Run all 8 JW Architect phases (Energy → Emergency → Grounding → Route → Structure → Connectivity → Future State → Recovery)

<br>

---

## System Visualization

Open **`system_vision.html`** in any browser (no server required):

- Animated 3D node graph of the full Cursiv architecture
- 420 seeded stars with individual twinkle at realistic depth
- Hexagonal ⬡ core with rotating multi-ring glow
- Particle trails flowing between nodes with source-node colors
- Depth-based edge opacity — deeper connections fade gracefully
- Layered nebula backdrop, per-node pulse animations

<br>

---

## Guardian Firewall

Cursiv v3.0 includes a four-layer active defense system wired into both the Gradio front-end and the CLI.

| Layer | What it does |
|---|---|
| **Robot Language Filter** | Pattern-matched probe detection with pi-squared compounding. Triggers on jailbreaks, system prompt dumps, agent enumeration, credential probing, and prompt injection. |
| **Council Fragment Mesh** | All 14 council agents run a lightweight security fragment check. Individual scores are sub-threshold; only coordinated multi-pattern probing compounds to matter. |
| **Adaptive Obfuscation** | On every launch, a 256-bit session token from `os.urandom + PID + time` reshuffles internal route labels. Makes session-to-session log correlation impossible. |
| **Decoy Agents** | Three isolated fake agents (Meridian, Veil, Cipher) activate only under probing — feeding plausible but deliberately misleading technical information. |

When a probe is detected: the skull screen fires before any API call, the message is blocked, and the attempt is logged to `.cursiv/guardian_log.jsonl` with session ID, pattern labels, compound score, and message preview.

<br>

---

## PiForge Vault — Phase Agents

The vault contains 14 living agents seeded across the JW Architect phase cycle. Run **`Import PiForge.bat`** once to seed them from the desktop JSON packets. After seeding:

- Each agent's `knowledge_map` is loaded into the system prompt of every conversation
- The Nexus panel shows real-time agent status and allows domain/task reassignment
- Agents can be queried directly through the Sovereign routing system

<br>

---

## Project Structure

```
Cursiv-v2.1.5/
├── cursiv_v215/
│   ├── ui/
│   │   ├── chat_app.py        # Gradio main chat (port 7860)
│   │   ├── chat_cli.py        # Terminal chat (full-screen CLI)
│   │   ├── nexus_app.py       # Nexus command panel (port 7861)
│   │   └── app.py             # Sacred UI (Streamlit, port 8501)
│   ├── core/                  # Agent, memory, constitution engine
│   ├── council/               # 14-agent deliberation system
│   ├── forge/                 # Training data forge + factory
│   ├── academy/               # Scoring and LoRA pipeline
│   ├── dugout/                # Agent vault
│   ├── guardian/              # System Guardian firewall + obfuscation + decoys
│   ├── weave/                 # Sovereign + transitionary weave
│   ├── memory/                # Session logger + boot context loader
│   ├── obsidian/              # Obsidian vault exporter + livestream
│   └── nexus/                 # Command router
├── system_vision.html         # ← Open this for the system visualization
├── START CURSIV SYSTEM.bat    # ← Launch everything at once
├── Launch Chat CLI.bat        # Terminal chat launcher
├── Launch Chat.bat            # Gradio web UI launcher
├── Launch Nexus.bat           # Nexus panel launcher
├── Import PiForge.bat         # Seed the vault (run once)
├── Setup and Launch Cursiv.bat
├── secrets.bat                # YOUR KEYS — create this (git-ignored)
├── requirements.txt
└── .gitignore
```

<br>

---

## Requirements

```
Python 3.10+
gradio >= 4.44.0
prompt_toolkit >= 3.0.0
```

Optional:
- **Ollama** — fully offline operation without API keys (`ollama pull mistral`)
- **pypdf** — PDF file reading and upload support
- **streamlit** — Sacred UI (port 8501)

<br>

---

## Security Model

- All file operations are sandboxed to the configured workspace root using `Path.relative_to()` — path traversal is structurally impossible
- API keys are read from environment variables only — never logged, stored in history, or sent anywhere except the respective API endpoint
- `secrets.bat` is explicitly excluded from git via `.gitignore` and will never appear in commits or pushes
- CONFIRM write mode is the default — no file is ever modified without your explicit `y` approval
- A hidden sovereign owner command exists deep in the codebase — known only to the builder — that disables the Guardian and reveals full system internals

<br>

---

## Offline Mode

No API keys? Run fully locally with Ollama:

```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull the model
ollama pull mistral
# 3. Launch the chat — it falls back to Mistral automatically
```

<br>

---

## What Can You Do With It?

Talk to the system inside the terminal chat. Ask it to:
- Read and edit your files, build new apps, write scripts, create plugins
- Design systems, plan features, reason through architecture decisions
- Evolve its own agents, update its own codex, extend its own tools
- Analyze data, generate training sets, score and curate conversation quality
- Livestream everything to your Obsidian vault as structured knowledge

Test it. Break it. Evolve it. Pass it on.

*From the Dust, We Shape the Stars.*

<br>

---

## License & Copyright

Copyright © 2026 Joshua Winkler. All rights reserved.

This software is released under the MIT License. See [LICENSE](LICENSE) for full terms.

<br>

---

*Built by Joshua Winkler · Cursiv v3.0*
