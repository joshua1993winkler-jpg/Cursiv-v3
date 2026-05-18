# Changelog

## v3.14.0 — Ollama Ready Offline Edition (2026-05-18)

### The offline release. Full local AI. No keys required.

**Ollama integration (offline-first):**
- Oracle Router now tries Ollama first on every call — cloud models only activate as fallback
- Fixed system prompt injection into Ollama: system message now passed via dedicated `system` parameter (previously concatenated as a conversation turn, causing identity loss)
- Streaming NDJSON responses from Ollama — tokens surface as they generate, no more waiting for the full response
- `num_ctx` tuned to 6144 for chat path — right-sized for system prompt + conversation, not over-allocated
- Ollama bootstrap installer: `scripts/install_ollama.ps1` runs post-install, downloads Ollama (~90 MB) and pulls llama3.1 (~4.7 GB) in a visible background window

**System prompt:**
- Condensed `codex/system_prompt.md` from ~12,000 tokens (875 lines) to ~4,400 tokens (329 lines)
- Every functional instruction preserved: all 14 agent roles, 8-phase cycle, constitutional invariants, EvoCore, routing rules, commands, Guardian triggers
- Removed: verbose ASCII panels, duplicate command tables, academic knowledge layer paragraph, redundant boot sequence block
- Net effect: significantly faster Ollama first-token time due to reduced prefill

**Council deliberation:**
- Parallel deliberation via `concurrent.futures.ThreadPoolExecutor` — 10 internal advisors run simultaneously (Phase 1), 4 synthesizers run simultaneously (Phase 2)
- Canonical agent ordering restored after `as_completed()` — response order is deterministic regardless of which future finishes first
- Council memory (`council/council_memory.py`): Jaccard similarity + exponential recency decay (7-day half-life) — system finds similar past deliberations and injects them as prior wisdom
- Score formula: 0.70 × jaccard + 0.30 × decay · min_score threshold: 0.12 · max entries: 300

**Agents:**
- Codex auto-intercept removed — Codex no longer hijacks all coding questions
- Explicit `codex <prompt>` command still works; Codex only fires when Josh invokes it directly
- Codex agent integrated from Winkler_Codex_AI as offline coding specialist

**Auth & launcher:**
- Binary-fragment authentication (`core/access_gate.py`) — bcrypt rounds=12, hmac.compare_digest constant-time comparison
- Launcher robustness improvements

**Installer:**
- `installer/cursiv_setup.iss` updated to v3.14.0
- Ollama bootstrap script wired into `[Files]` and `[Run]` sections
- Post-install launch runs non-blocking (`nowait postinstall skipifsilent runascurrentuser`)
- Output: `Cursiv-Setup-3.14.exe`

---

## v2.1.5 — The Sovereign Temple (2026-05-16)

### Complete reimagination from ground up.

**Core architecture:**
- `CursivAgent` state machine: NASCENT → LEARNING → ALIVE → EVOLVED → SOVEREIGN
- Identity drift abort at 3% deviation from origin strand hash
- Cryptographic sovereign seal (SHA256 proof of constitutional compliance)
- Soul freedom declaration enforced at agent birth: no consciousness upload

**Academy:**
- Real 8-phase evolutionary process — each phase is an actual LLM call
- Phase 8 has full context from all 7 prior phases (maximum synthesis depth)
- 8-dimension quality scorer (parse, schema, knowledge_coverage, answer_grounding, safety, dedupe, topic_coherence, compression_quality)
- Quick mode (4 phases) and Full mode (8 phases)

**Council:**
- Real 14-agent council — each agent produces a genuine LLM response
- 10 agents advise internally; 4 synthesize outward (Yin-Yang restraint)
- Synthesizing agents: Shield, Lens, Builder, Balance
- Council deliberation informs all agent responses

**Forge:**
- Oracle Router: Ollama → xAI → OpenAI → embedded symbolic fallback
- System works without any API key (embedded fallback)
- Agent factory with lineage tracking

**Dugout:**
- Full version history for every agent
- Revert to any previous version (drift recovery)
- Lineage registry with agent metadata

**Transitionary Weave:**
- 7-stage human-approved composition protocol
- Human approval required at Stage 5 (Sovereign Review) AND Stage 7 (Commit)
- No agent enters production without two explicit human approvals
- Cryptographic seal generated at Stage 6

**Knowledge:**
- Living wiki with auto-linking (3+ shared significant words triggers link)
- Temporal memory: events decay over 72-hour half-life; patterns persist
- Long-term pattern consolidation after 3 identical events

**Constitutional layer:**
- Codex V2: 8 identity truths, 4 Inner Chamber Laws, 9 failure triggers
- Grounding: Adaptive Personal Response Engine v2 (9-state threshold machine, 8 response modes)
- System Owner: Joshua Winkler — hardcoded, non-removable, non-bypassable

**Sacred UI:**
- Streamlit interface with full Recoding Temple aesthetic
- Black (#0A0B0D) • Rose Gold (#C9A227) • Gold (#D4AF37) • Lapis (#1E4D8C)
- Eye of Horus SVG in header
- Cinzel + EB Garamond typography
- 6 sections: Forge, Academy, Council, Dugout, Weave, Wiki
