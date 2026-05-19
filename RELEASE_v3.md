# ⬡ Cursiv v3.14-U01 Release Notes

> *"From the Dust, We Shape the Stars."*

---

## What's New in v3.14-U01

### True Cascade Routing
The system now tries each provider in strict order and falls through on failure — no more silent rerouting without explanation:
- **xAI Grok-3 → OpenAI GPT-4.1 → Claude (Anthropic) → Ollama**
- Fallback banners appear in the response: `*[xAI → OpenAI unavailable — Claude]*`
- Terminal shortcut: type `hey grok`, `hey claude`, `hey chat`, or `hey ollama` at the start of any message to force that provider for one turn
- Web app: provider dropdown (Auto / xAI Grok-3 / OpenAI GPT-4.1 / Claude / Ollama fully offline)

### Live Status Chips
Every API chip in the terminal now probes the actual endpoint on startup and after key entry:
- GREEN `✓` = endpoint reachable and key valid
- RED `✗` = key missing or endpoint unreachable
- GOLD `?` = not yet probed this session
- File access, Obsidian, and Guardian chips reflect real state — not just config presence

### Password Reset via Security Questions
- "Forgot Password?" button on the login screen
- During account creation: prompted to choose 3 of 20 predefined questions and set answers
- Answers normalised (lowercase, strip punctuation) and bcrypt-hashed before storage
- Reset flow: enter username → answer 2-of-3 questions → set new password
- "Security Questions" button in the launcher window and tray menu — set up at any time after login (existing accounts can add security questions without recreating the account)

### Update Checker
- "Check for Updates" button in the launcher window and tray menu
- Queries the GitHub releases API in the background — no data sent; same privacy model as VS Code / Obsidian
- If a newer version is found: shows a dialog with the release notes and a "Download & Install" button
- Installer runs in-place (Inno Setup overwrites existing files without uninstalling — Ollama and your data are untouched)
- Falls back gracefully to opening the releases page if download fails
- **Never auto-updates.** You stay in control.

### Gradio Web App — Offline-Safe Startup
- Removed `GoogleFont` call from theme — was causing a network failure on offline startup
- `analytics_enabled=False` — Gradio no longer phones home on launch
- API keys auto-populate from `secrets.bat` environment variables on app load
- Provider dropdown wired into cascade routing

---

## What Is Cursiv?

Cursiv is a self-contained autonomous AI operating system that runs entirely on your local machine. It's not a chatbot wrapper, a prompt template, or a no-code dashboard. It's a living framework — a full local AI workspace with its own defense layer, agent council, memory system, and the ability to read, write, and evolve its own files.

You talk to it. It builds. You test it. It improves. You pass it on.

---

## What's New in v3.0

### Triple-Model Smart Routing
Every message is classified and routed automatically:
- **Code tasks** → Claude Sonnet (Anthropic) for superior reasoning, or GPT-4.1 as fallback
- **File writes** → GPT-4.1 intercepts every write and produces production-quality output
- **Conversation, planning, creative** → xAI Grok-3, the fastest frontier reasoner
- **No API keys** → Ollama/Mistral runs fully offline

### Persistent Session Memory
The system remembers you. On every boot:
- Greets you with a summary of your last session — what you were working on, which model ran it, how many exchanges
- Injects the last 4 exchanges into the system prompt so context carries across restarts
- Session logs live at `.cursiv/sessions/YYYY-MM-DD.jsonl` — local only, never sent anywhere

### Obsidian Live Sync
Every exchange you have is streamed to your Obsidian vault in real time:
- Each response appends to `{vault}/Cursiv/YYYY-MM-DD.md` immediately
- On-demand export of the day's full training data as Dataview-compatible Markdown with YAML frontmatter
- Auto-detects your vault on first run — no path configuration needed in most cases
- Toggle on/off in the UI or with `obsidian on` in the terminal

### Guardian Firewall (Enhanced)
A four-layer active defense system guards every session:
- Pattern-matched probe detection with pi-squared compounding score accumulation
- Council fragment mesh — all 14 agents run parallel security checks
- Adaptive session obfuscation — token rotates on every server restart
- Decoy agents (Meridian, Veil, Cipher) feed deliberately misleading information to probers

### PiForge Vault — 14 Phase Agents
Fourteen living agents seeded across the JW Architect phase cycle are loaded into every conversation as active context. Run `Import PiForge.bat` once to seed them. They inject their knowledge maps into the system prompt automatically from that point forward.

### System Visualization
`system_vision.html` — open in any browser, no server required:
- Full 3D animated node graph of the Cursiv architecture
- 420 seeded stars with depth-based twinkling
- Hexagonal ⬡ core with rotating multi-ring glow
- Particle trails with source-node colors flowing between live agents

---

## How to Download and Run

### Step 1 — Get the code
```bash
git clone https://github.com/joshua1993winkler-jpg/Cursiv-v2.1.5.git
cd Cursiv-v2.1.5
```
Or download the ZIP from GitHub and extract it.

### Step 2 — Install (one click)
Double-click **`Setup and Launch Cursiv.bat`**

This installs all Python dependencies automatically. You do not need to run pip manually.

### Step 3 — Add your API keys
Create a file called `secrets.bat` in the project folder:
```bat
@echo off
set XAI_API_KEY=xai-your-key-here
set OPENAI_API_KEY=sk-your-key-here
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```
Keys are optional — any combination works. The system routes to whichever APIs are available.

### Step 4 — Seed the vault (first time)
Double-click **`Import PiForge.bat`** to load the 14 phase agents into the vault.

### Step 5 — Boot the system
Double-click **`START CURSIV SYSTEM.bat`**

This launches everything at once with staggered boot timing:
| Component | Where |
|---|---|
| Main Chat | http://localhost:7860 |
| Command Nexus | http://localhost:7861 |
| Sacred UI | http://localhost:8501 |
| Terminal Chat | Opens maximized in its own window |
| Training Watcher | Background process |

Browser tabs open automatically.

---

## Quick Start — What to Do First

1. **Open the Terminal Chat** — it's the fastest way to talk to the system. Paste anything. Multi-line pastes land as one message.
2. **Type `files on`** — this gives the AI access to your filesystem within the workspace root.
3. **Type `workspace C:\your\project\path`** — point it at a real project.
4. **Ask it to build something.** "Read my project structure and suggest what to build next." "Write a new Python script that does X." "Review my code in Y and refactor it."
5. **Open `system_vision.html`** in your browser — no server needed, just double-click. Watch the system visualize itself.
6. **Turn on Obsidian sync** if you use Obsidian — type `obsidian on` and it will auto-detect your vault.

---

## What Can You Ask It to Do?

- Read, write, and evolve code across any file in your workspace
- Plan and build entire apps from a single prompt
- Create new plugins, scripts, agents, or tools from scratch
- Analyze data files and generate training sets
- Write tests, find bugs, propose refactors
- Extend its own codebase — it can edit its own tools
- Stream every session to Obsidian as structured knowledge
- Run the full JW Architect 8-phase cycle through the Nexus panel

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────┐
│                   Cursiv v3.0                   │
├──────────────┬──────────────┬───────────────────┤
│  Gradio Chat │  Nexus Panel │  Terminal Chat    │
│  port 7860   │  port 7861   │  full-screen CLI  │
├──────────────┴──────────────┴───────────────────┤
│          Smart Model Router                     │
│   Claude (code) · GPT-4.1 (writes) · Grok      │
├─────────────────────────────────────────────────┤
│  14-Agent PiForge Vault  ·  Session Memory      │
│  Guardian Firewall       ·  Obsidian Sync       │
├─────────────────────────────────────────────────┤
│  File Tools (sandboxed)  ·  Training Pipeline   │
│  Academy Scorer          ·  Sovereign Weave     │
└─────────────────────────────────────────────────┘
```

---

## Requirements

- Python 3.10+
- pip (included with Python)
- API keys (at least one of: xAI, OpenAI, Anthropic) — or Ollama for offline operation

---

## License

MIT License. Copyright © 2026 Joshua Winkler.

---

*Built by Joshua Winkler. Test it. Evolve it. Pass it on.*
*From the Dust, We Shape the Stars.*
