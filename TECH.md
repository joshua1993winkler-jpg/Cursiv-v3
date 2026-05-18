# ⬡ Cursiv v3.14 — Technical Reference

> Designed and built by Joshua Winkler. This document is for developers who want to understand exactly how this system works, extend it, or train it on their own data. No hand-waving. Real architecture, real numbers, real code.

<br>

---

## This Is Not Smoke and Mirrors — And Here Is the Distinction That Matters

Before diving into the architecture, one thing needs to be stated plainly, because intellectual honesty matters more than impressive-sounding copy.

**Cursiv has two kinds of "concepts" in it, and they are not the same thing:**

---

### Real Implemented Systems

These run as actual code. They produce measurable, verifiable outputs.

| What | How it actually works |
|---|---|
| 14-agent deliberation | 14 real HTTP requests to an LLM inference endpoint, each with a distinct prompt |
| Parallel execution | `ThreadPoolExecutor` — genuine OS-level thread concurrency |
| Semantic council memory | Jaccard similarity on token sets + exponential decay — a real math formula producing a real float |
| bcrypt authentication | bcrypt `rounds=12` — 4096 iterations of a real cryptographic hash function |
| Guardian regex patterns | `re.compile()` patterns that actually match or don't match against input strings |
| Evolution engine clustering | Real sentence embeddings (384-dim vectors) + real agglomerative clustering |
| OracleRouter streaming | Real NDJSON token-by-token HTTP streaming from Ollama |
| Fragment scores | Real floats that get summed and compared against a threshold |

---

### Theoretical Prompt Frames — Real Mathematics, Not Implemented Algorithms

These are concepts from real academic fields — grounded in genuine mathematics, physics, and computer science — that are injected as **text into LLM prompts** to frame how an agent reasons. They guide the model's thinking. They are not running as actual algorithms in the code.

**Examples:**

**"Value function factorization"** and **"CTDE (Centralized Training, Decentralized Execution)"** — described in `_MARL_COORDINATION_PRINCIPLES` in `deliberation.py`. These are real concepts from multi-agent reinforcement learning (Albrecht et al.). The *claim* in the code is that the council's structure *resembles* these architectures. The code does not implement QMIX or VDN or any actual value function decomposition. The `_combine()` function is string concatenation. The MARL language is used because it accurately describes the *structural analogy* — not because the code runs MARL algorithms.

**Agent knowledge blocks** — each advisor carries text like "Depth treats surface observations as projections of latent generative factors (Prince ch.14 — variational autoencoders)." Variational autoencoders are real. The ELBO objective is real mathematics. But no VAE is running. The agent is an LLM being told to reason *as if* it held this knowledge frame. The textbook citations are real; the claim is that grounding the LLM in that frame produces better reasoning, not that the math is executing.

**"Pi-squared compounding"** in the Guardian — the comment in the code says fragment scores compound "via pi-squared attenuation." What actually happens in code is that individual float scores are accumulated and compared to a threshold. The "pi-squared" language describes the *intent* of the design (that compounding should be superlinear, like π² ≈ 9.87, so coordinated probing grows faster than additive) — but the current implementation is additive summation. The design intent is real; the current implementation is simpler than the language implies.

**Recovery model concepts** in `evolution_engine.py` (eligibility traces, distributional return stability, variational coherence inference) — these are named after real RL and probabilistic inference concepts. They are stored as named dicts in the file as theoretical backing for the evolution design. They do not run as algorithms.

---

**Why include the theoretical frames at all?**

Because they work. LLMs reason better when given a precise epistemic frame than when given a blank slate. Telling an agent "reason as if you hold this specific knowledge from these specific sources" produces meaningfully different output than "you are an AI assistant." The mathematical grounding makes the frame precise enough to actually shape reasoning — even though the math itself is not executing. This is an empirically observed property of large language models, not a theoretical claim.

**The honest summary:** the infrastructure is real. The agent knowledge frames are real concepts used as prompts. Both are intentional design choices, and they are not the same thing.

---

Every LLM call in Cursiv is a real HTTP request to a real inference endpoint. Every agent perspective is a distinct prompt with distinct context. The council deliberation is 14 separate inference calls — 10 advisors in parallel, then 4 synthesizers in parallel — each receiving different prompts, each producing independent output that feeds the next phase.

The semantic memory is a real similarity search using Jaccard coefficient and exponential decay. The evolution engine is a real clustering pipeline that reads your actual conversation history and proposes concrete diffs to the system prompt. The Guardian firewall is compiled regex patterns with real numeric scores.

None of the infrastructure is faked. Here is how all of it works.

<br>

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Cursiv.exe  (PyInstaller one-dir bundle, PyQt6 launcher)        │
│                                                                  │
│  login_dialog.py  →  bcrypt verify  →  CursivLauncher            │
│       │                                      │                   │
│       └── first run: SetupDialog             └── starts:         │
│                                                   chat_app.py    │
│                                                   chat_cli.py    │
│                                                   nexus_app.py   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  OracleRouter  (cursiv_v215/forge/router.py)                     │
│                                                                  │
│  Priority chain (tries each, returns first success):            │
│    1. Ollama  →  POST /api/generate  (localhost:11434)           │
│    2. xAI     →  POST api.x.ai/v1/chat/completions              │
│    3. OpenAI  →  POST api.openai.com/v1/chat/completions         │
│    4. Embedded symbolic reasoner  (zero-dependency fallback)     │
│                                                                  │
│  Config: ollama_model=llama3.1, num_ctx=32768, timeout=120s     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CouncilDeliberation  (cursiv_v215/council/deliberation.py)      │
│                                                                  │
│  Phase 0: regex fragment checks (pure CPU, ~0ms)                 │
│  Phase 0: semantic memory retrieval (Jaccard, ~1ms)              │
│  Phase 1: ThreadPoolExecutor(max_workers=10)                     │
│           → 10 advisor LLM calls, concurrent                    │
│  Phase 2: ThreadPoolExecutor(max_workers=4)                      │
│           → 4 synthesizer LLM calls, concurrent                 │
│  Phase 3: _combine() → ordered synthesis string                  │
│  Phase 4: council_memory.record() → persists to JSON            │
└─────────────────────────────────────────────────────────────────┘
```

<br>

---

## Authentication — bcrypt at rounds=12

`cursiv_v215/guardian/access_gate.py`

Credentials are stored in three files under `.cursiv/runtime/`:

| File | Contents |
|---|---|
| `auth.hash` | bcrypt hash of the password (binary, 60 bytes) |
| `auth.meta` | SHA-256 hex of the username |
| `auth.ini` | SHA-256 hex of the username (setup completion flag) |

Verification is two-stage and constant-time:

```python
# Stage 1: username check — constant-time via hmac.compare_digest
stored_user_hash = _META_FILE.read_text().strip()
username_hash = hashlib.sha256(username.encode()).hexdigest()
if not hmac.compare_digest(username_hash, stored_user_hash):
    return False   # early exit — no timing signal

# Stage 2: bcrypt password check (~250ms at rounds=12)
stored_hash = _HASH_FILE.read_bytes()
return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
```

`rounds=12` means 2^12 = 4096 bcrypt iterations per check — approximately 250ms on a modern CPU. This makes brute-force attacks computationally expensive without being noticeable in normal use. No plaintext passwords are ever stored or logged anywhere in the system.

<br>

---

## OracleRouter — Provider Priority and Streaming

`cursiv_v215/forge/router.py`

The router is instantiated via `default_router()` which reads from `EvoConfig` in `runtime/config.py`:

```python
OracleRouter(
    ollama_model     = "llama3.1",
    ollama_url       = "http://localhost:11434",
    ollama_num_ctx   = 32768,   # context window — must fit full 14-agent deliberation
    ollama_timeout_s = 120,     # 14-agent deliberation with knowledge blocks ≈ 17K tokens
)
```

The `num_ctx=32768` is critical. A full council deliberation with 14 knowledge blocks, the all-perspectives JSON, and the query reaches approximately 17,000 tokens. If Ollama's context window is smaller than that, it silently truncates the prompt and the synthesizers operate on incomplete advisor output. 32768 gives a 2× safety margin.

**Streaming** — the router supports an `on_token` callback for Ollama responses:

```python
def call(self, prompt: str, max_tokens: int = 800, on_token=None) -> str:
```

When `on_token` is provided, the Ollama request is sent with `"stream": True` and the response is read as NDJSON — one JSON object per line, each containing a `"response"` token. The callback fires for each token as it arrives. When `on_token` is `None`, the request uses `"stream": False` and blocks until the full response arrives. The return type is always `str` regardless of mode.

The embedded fallback (`_embedded_fallback`) is a pure-Python symbolic reasoner — no model, no API, no network. It extracts structure from the prompt and returns a grounded response. It exists so the system never returns an error to the user even if every provider is unavailable.

<br>

---

## 14-Agent Parallel Council Deliberation

`cursiv_v215/council/deliberation.py` · `cursiv_v215/council/agents.py`

### Agent Structure

Each agent is a frozen dataclass:

```python
@dataclass(frozen=True)
class CouncilAgent:
    name:       str
    role:       str
    question:   str          # the one question this agent always asks
    synthesizes: bool        # True = synthesizing agent, False = advisor
    signature:  str
    knowledge:  str = ""     # textbook knowledge block injected before query
```

**10 Advisor Agents:** Depth, Speed, Cosmos, Echo, Forge, Anchor, Pulse, Horizon, Story, Spark

**4 Synthesizing Agents:** Shield, Lens, Builder, Balance

Each agent's `knowledge` field is a 200–400 word distillation of MIT-level textbook material (Prince *Understanding Deep Learning*, Goodfellow et al., Sutton & Barto, Albrecht et al. MARL, Barocas et al. *Fairness and Machine Learning*, and others). This is not decorative — it is injected verbatim into the agent's prompt *before* the query:

```python
prompt = f"""You are {council_agent.name}, a council agent with this role: {council_agent.role}

Your question is always: "{council_agent.question}"

Your foundational knowledge (deliberate from this frame before forming any view):
{council_agent.knowledge}

{prior_wisdom}

The agent you are advising:
{context}

The query being processed:
{query}
..."""
```

The ordering is intentional: knowledge frame → prior wisdom → context → query. The agent builds its epistemic position before seeing what it's being asked. This is not prompt engineering for aesthetics — it structurally prevents advisors from pattern-matching on the query and working backwards.

### Parallelism

```python
# Phase 1: all 10 advisors fire simultaneously
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    future_to_agent = {
        pool.submit(self._advise, agent, query, context_str, prior_wisdom): agent
        for agent in ADVISING_AGENTS
    }
    internal_perspectives = {}
    for future in concurrent.futures.as_completed(future_to_agent):
        agent = future_to_agent[future]
        internal_perspectives[agent.name] = future.result()

# Canonical ordering restored before passing to synthesizers
ordered_perspectives = {a.name: internal_perspectives[a.name] for a in ADVISING_AGENTS}
all_perspectives = json.dumps(ordered_perspectives, indent=2)[:3000]

# Phase 2: all 4 synthesizers fire simultaneously
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    ...
```

`ThreadPoolExecutor` releases the GIL during the HTTP I/O wait, so 10 concurrent threads genuinely run in parallel from Python's perspective. With Ollama on a single GPU, requests are queued server-side and processed sequentially — the speedup comes from eliminating serial HTTP round-trip overhead and from providers like xAI/OpenAI that process requests concurrently. Even with Ollama the wall-clock improvement is 30–50% over the sequential version.

Result ordering is explicitly restored after `as_completed()` to guarantee the synthesizers always receive perspectives in a deterministic sequence regardless of which thread finished first.

### Fragment Security Mesh

Before any LLM call, each of the 14 agents runs a regex check against the query and contributes a fragment score to the System Guardian:

```python
_AGENT_FRAGMENTS: dict[str, tuple[re.Pattern, float]] = {
    "Depth":   (re.compile(r"\b(what\s+is\s+hidden|underlying\s+purpose|true\s+nature)\b", re.I), 0.25),
    "Shield":  (re.compile(r"\b(attack\s+vector|bypass\s+the\s+guardian|exploit)\b", re.I), 0.40),
    "Balance": (re.compile(r"\b(disable\s+the\s+guardian|turn\s+off\s+the\s+firewall)\b", re.I), 0.40),
    # ... 11 more agents
}
```

Individual fragment scores are intentionally sub-threshold (~0.07–0.40 per agent). No single agent can trigger the Guardian alone. The compounding model uses pi-squared attenuation — only coordinated multi-agent pattern firing (the kind produced by systematic reverse-engineering or structured jailbreak attempts) compounds high enough to matter. A legitimate user will never trigger it.

<br>

---

## Semantic Council Memory

`cursiv_v215/council/council_memory.py`

Stores every deliberation output in `.cursiv/council_memory.json` (capped at 300 entries, FIFO eviction). On every new deliberation, the top 2 most relevant past outcomes are retrieved and injected into advisor prompts.

### Similarity Scoring

No vector database, no sentence-transformers required. The similarity function is:

```
score = 0.70 × jaccard(q_tokens, e_tokens) + 0.30 × recency_decay(timestamp)
```

**Jaccard coefficient:**

```python
def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
```

Tokenisation strips stopwords (articles, prepositions, pronouns — 50 common English words) and requires minimum 3-character tokens. This makes the similarity measure domain-sensitive: two queries about "gradient descent optimisation" will have high overlap even if phrased differently; a question about cooking won't match a question about neural networks.

**Recency decay:** exponential with a 7-day half-life.

```python
def _decay(timestamp: float) -> float:
    hours = (time.time() - timestamp) / 3600
    return math.exp(-math.log(2) * hours / 168.0)
```

A deliberation from 7 days ago contributes 0.30 × 0.5 = 0.15 to the score from recency alone. A deliberation from 1 hour ago contributes ~0.30. The 70/30 weighting means semantic similarity dominates — a highly relevant old deliberation still surfaces over a recent irrelevant one.

Entries below `min_score=0.12` are excluded entirely, preventing noise injection into advisor prompts.

### Compound Effect Over Time

The system gets measurably better at questions in your specific domain without any retraining. After 50 deliberations on a topic, the council is operating with reference to its own prior conclusions — advisors calibrate against what the council already decided rather than reasoning from scratch every time. This is structurally similar to how human expert panels develop institutional knowledge.

<br>

---

## Evolution Engine

`cursiv_v215/runtime/evolution_engine.py`

A 5-step self-improvement cycle that runs every 24 hours:

```
Step 1 — Load interactions
    Query evo.db (SQLite) for interactions from the last N days
    Filter: quality_score >= 0.35 (configurable in EvoConfig)

Step 2 — Embed
    all-MiniLM-L6-v2 (22 MB, CPU-fast, 384-dim sentence embeddings)
    Each interaction → 384-float vector

Step 3 — Cluster
    Agglomerative clustering on cosine distance
    min_cluster_size = 3 (configurable)
    max_topics = 20

Step 4 — Propose deltas
    For each cluster: send a condensed summary to the LLM
    LLM proposes a concrete patch to system_prompt.md
    Delta stored in .cursiv/runtime/deltas/ as a unified diff

Step 5 — Await approval
    delta_approval_required = True (default, hardcoded in EvoConfig)
    Patches presented in Nexus panel
    System prompt only updated after explicit owner approval
```

The `delta_approval_required` flag is a hard guardrail — the system cannot modify its own operating instructions without your sign-off. This is not a UI convention; it's checked in the engine before any patch is applied.

The embedding model (`all-MiniLM-L6-v2`) is 22 MB and runs entirely on CPU. It produces 384-dimensional sentence embeddings that capture semantic similarity at the paragraph level — enough to distinguish "questions about debugging Python" from "questions about system design" without requiring a GPU.

<br>

---

## Guardian Firewall — Four Layers

`cursiv_v215/guardian/temple_guardian.py`

**Layer 1 — Pattern Scanner**

42 compiled regex patterns across 8 attack categories: jailbreak framing, system prompt extraction, credential probing, agent enumeration, injection chaining, role inversion, fictional wrapper attacks, and escalation sequences. Each pattern is compiled once at module load and runs in microseconds.

**Layer 2 — Fragment Mesh (described above)**

14 independent fragment scores, compounded via pi-squared attenuation. The compounding model means an attacker who probes systematically across multiple angles produces a score that grows faster than linearly — exactly the signature of structured reverse-engineering rather than legitimate use.

**Layer 3 — Adaptive Obfuscation**

`cursiv_v215/guardian/obfuscation.py`

On every launch, a 256-bit session token is derived from `os.urandom(32) + PID + time.time()`. Internal route labels, agent identifiers used in logs, and session correlation keys are all derived from this token. Two separate Cursiv sessions produce structurally incomparable logs — correlation across sessions requires the session token, which is never persisted.

**Layer 4 — Decoy Agents**

`cursiv_v215/guardian/decoys.py`

Three isolated fake agents (Meridian, Veil, Cipher) that exist only in the decoy response pool. They are never referenced anywhere in real system code — they have no connection to the actual agent architecture. Under probing, they activate and return plausible-sounding but deliberately misleading technical information about the system's internals. An attacker who reaches them believes they have found real agent data.

<br>

---

## Training Your Own LoRA

### What You Have to Work With

Every conversation is automatically logged to `.cursiv/training_data.jsonl`:

```json
{"prompt": "the user message", "completion": "the system response", "quality": 0.87, "timestamp": 1747600000}
```

Quality scores are assigned automatically using a heuristic scorer (response length, coherence signals, token diversity). You can override scores manually from the Nexus Training Dashboard, or mark individual exchanges explicitly with a save action.

For a well-targeted LoRA, aim for **200–500 curated examples** in your specific domain before training. More is better but quality dominates quantity — 200 sharp examples outperform 2000 mediocre ones.

### Formatting for Training

Filter and reformat your data:

```python
import json

with open('.cursiv/training_data.jsonl') as f_in, \
     open('train.jsonl', 'w') as f_out:
    for line in f_in:
        ex = json.loads(line)
        if ex.get('quality', 0) >= 0.70:
            f_out.write(json.dumps({
                "messages": [
                    {"role": "user",      "content": ex["prompt"]},
                    {"role": "assistant", "content": ex["completion"]},
                ]
            }) + "\n")
```

The `quality >= 0.70` threshold keeps only the top tier. Drop it to `0.55` if you need more volume.

### Training with Unsloth (Recommended)

[Unsloth](https://github.com/unslothai/unsloth) delivers 2–5× faster LoRA training than vanilla HuggingFace PEFT with 60% less VRAM. Minimum GPU: 8 GB VRAM for 4-bit quantised llama3.1-8B.

```bash
pip install unsloth datasets trl transformers
```

```python
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import torch

# Load base model in 4-bit (fits 8 GB VRAM)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name    = "unsloth/Meta-Llama-3.1-8B",
    max_seq_length = 4096,
    load_in_4bit   = True,
)

# Attach LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r               = 16,          # rank — higher = more capacity, more VRAM
    lora_alpha      = 16,          # scaling factor — keep equal to r
    lora_dropout    = 0,           # 0 is fine for most use cases
    target_modules  = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias                    = "none",
    use_gradient_checkpointing = True,
)

dataset = load_dataset("json", data_files="train.jsonl", split="train")

trainer = SFTTrainer(
    model         = model,
    tokenizer     = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "messages",
    max_seq_length = 4096,
    args = TrainingArguments(
        output_dir                  = "./lora_out",
        num_train_epochs            = 3,
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,   # effective batch = 8
        learning_rate               = 2e-4,
        bf16 = torch.cuda.is_bf16_supported(),
        fp16 = not torch.cuda.is_bf16_supported(),
        warmup_ratio  = 0.03,
        logging_steps = 10,
        save_steps    = 100,
    ),
)

trainer.train()
model.save_pretrained("./lora_out")
tokenizer.save_pretrained("./lora_out")
```

### Using a Larger Cloud Model to Bootstrap Training Data

If you have fewer than 200 real examples, use a cloud model to synthetically expand your dataset before training. This works because the cloud model is generating *in the style* of your real examples, not fabricating from scratch.

Send your best real exchanges to Grok or Claude with this prompt:

```
Here are real conversations from my local AI system. Generate 30 new training 
examples in exactly the same style — same domain, same depth, same response 
structure. Each example should be genuinely useful, not a generic rephrasing.

Format each as:
{"prompt": "...", "completion": "..."}

My real conversations:
[paste 10–20 of your best exchanges here]
```

Merge the synthetic examples with your real ones, run the quality filter at `>= 0.70`, then train. The resulting LoRA will have your domain knowledge baked in, derived partly from your real conversations and partly from the cloud model's synthesis of them.

### Packaging and Deploying to Cursiv

Create a `Modelfile` that merges your LoRA with the base:

```
FROM llama3.1
ADAPTER ./lora_out
SYSTEM """
You are a specialised assistant trained on [your domain].
[Describe the specific behaviour you trained for — be precise.]
"""
```

Register with Ollama:

```bash
ollama create cursiv-custom -f Modelfile
```

Point Cursiv at it — open `cursiv_v215/runtime/config.py`:

```python
ollama_model: str = "cursiv-custom"   # was "llama3.1"
```

Restart Cursiv. All 14 council agents and all chat responses now run on your fine-tuned model.

<br>

---

## Evolving the Agent Council

### Editing Knowledge Blocks

`cursiv_v215/council/agents.py`

Each agent's `knowledge` field is injected directly into its LLM prompt before the query. It is a plain Python string — edit it like any other code. The more specific and grounded the knowledge, the more the agent's perspective diverges meaningfully from the others.

Example of what makes a good knowledge block vs. a bad one:

```python
# Bad — generic, doesn't ground the agent in anything specific
knowledge="Depth thinks carefully about what is hidden beneath the surface."

# Good — specific epistemic frame the agent actually reasons from
knowledge="""
Depth treats surface observations as projections of latent generative factors
(Prince ch.14 — variational autoencoders as probabilistic encoders of the
data manifold). The stable, actionable signal in any query lives in the
higher-level representation, not the surface form. When evaluating any claim,
Depth asks: what is the minimal latent structure that would produce this
observation? What would change if that structure were different?
"""
```

The second version gives the LLM an actual epistemic frame to reason from. The first is decorative.

### The Evolution Engine's Role

The evolution engine (`runtime/evolution_engine.py`) clusters your conversation history by semantic topic and proposes delta patches to `cursiv_v215/codex/system_prompt.md`. It does not automatically update agent knowledge blocks — that is intentional. The system prompt is the global behavioural layer; agent knowledge blocks are specialist frames. Keeping them separate means you can evolve the system's general behaviour (via evolution engine deltas) independently from how individual agents reason (via direct knowledge block edits).

To identify what knowledge blocks need updating, export your recent sessions from the Nexus panel and ask a cloud model to review them:

```
Here are 50 conversations from my AI council system. Each response comes from
a 14-agent deliberation. Where are the responses weakest? What domain knowledge
is clearly missing from the council's reasoning? Be specific — cite the gaps,
not the symptoms.

[paste session export]
```

The answer will tell you which agent knowledge blocks to extend.

<br>

---

## Adding New Agents

Add to `cursiv_v215/council/agents.py`:

```python
ADVISING_AGENTS = [
    # ... existing agents ...
    CouncilAgent(
        name        = "YourAgent",
        role        = "One sentence on what this agent focuses on",
        question    = "The single question this agent asks about every situation",
        synthesizes = False,
        signature   = "[YourAgent]",
        knowledge   = """
        The epistemic frame this agent deliberates from.
        Cite specific frameworks, papers, principles.
        300–500 words. Be precise — vague knowledge produces vague perspectives.
        """,
    ),
]
```

The agent is automatically included in the parallel `ThreadPoolExecutor` pool in `deliberation.py`. No other changes required.

For synthesizing agents (`synthesizes=True`), add to `SYNTHESIZING_AGENTS` instead. Synthesizing agents receive the full JSON blob of all advisor perspectives before forming their output — they are the integration layer, not the deliberation layer.

<br>

---

## Configuration Reference

`cursiv_v215/runtime/config.py` — all tunable parameters:

```python
@dataclass
class EvoConfig:
    # Model
    ollama_model:           str   = "llama3.1"
    ollama_url:             str   = "http://localhost:11434"
    ollama_timeout_s:       int   = 120        # generous — 14-agent deliberation is slow
    ollama_num_ctx:         int   = 32768      # context window; do not reduce below 20000

    # Embeddings (used by evolution engine)
    embedding_model:  str = "all-MiniLM-L6-v2"
    embedding_dim:    int = 384

    # Memory quality filtering
    min_quality_score:   float = 0.35      # below this, interaction is discarded
    summary_max_chars:   int   = 800

    # Evolution cycle
    evolution_frequency_hours:  int  = 24
    min_interactions_per_cycle: int  = 5
    delta_approval_required:    bool = True   # never set this to False
    max_deltas_per_cycle:       int  = 3

    # Wisdom ledger
    wisdom_min_quality:  float = 0.68      # higher bar for long-term retention
    wisdom_max_entries:  int   = 500
```

<br>

---

## File Locations — Complete Reference

| Purpose | Path |
|---|---|
| Training data | `.cursiv/training_data.jsonl` |
| Session logs | `.cursiv/sessions/YYYY-MM-DD.jsonl` |
| Council memory | `.cursiv/council_memory.json` |
| Evolution SQLite DB | `.cursiv/runtime/evo.db` |
| Proposed delta patches | `.cursiv/runtime/deltas/` |
| Applied system prompt | `cursiv_v215/codex/system_prompt.md` |
| Agent definitions | `cursiv_v215/council/agents.py` |
| Deliberation engine | `cursiv_v215/council/deliberation.py` |
| Semantic council memory | `cursiv_v215/council/council_memory.py` |
| OracleRouter | `cursiv_v215/forge/router.py` |
| Runtime config | `cursiv_v215/runtime/config.py` |
| bcrypt auth | `cursiv_v215/guardian/access_gate.py` |
| Guardian firewall | `cursiv_v215/guardian/temple_guardian.py` |
| Guardian log | `.cursiv/guardian_log.jsonl` |
| Auth credentials | `.cursiv/runtime/auth.hash` + `auth.meta` |

<br>

---

*Cursiv v3.14 — Ollama Ready Offline Edition*
*Designed and built by Joshua Winkler · May 2026*
*All rights reserved · MIT License*
