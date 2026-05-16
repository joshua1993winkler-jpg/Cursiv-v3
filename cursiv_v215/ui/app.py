"""
Cursiv v2.1.5 — Sacred UI

Streamlit skin over the original Cursiv-v2 backend.
All backend logic is unchanged from cursiv.webapp —
weave_payload, chat_payload, sovereign_payload, suggested_prompts.
Only the presentation layer is new.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).parent.parent.parent          # Cursiv-v2.1.5/
_CURSIV_V2 = _REPO_ROOT.parent / "Cursiv-v2"             # ../Cursiv-v2/
for _p in [str(_REPO_ROOT), str(_CURSIV_V2)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import streamlit as st
except ImportError:
    print("Streamlit not installed. Run: pip install streamlit")
    sys.exit(1)

# ── Import original Cursiv backend (no changes to these) ─────────────────────
try:
    from cursiv.webapp import (
        chat_payload,
        sovereign_payload,
        suggested_prompts,
        weave_payload,
    )
    _BACKEND_OK = True
    _BACKEND_ERR = ""
except Exception as _e:
    _BACKEND_OK = False
    _BACKEND_ERR = str(_e)


# ── Sacred Color Palette ──────────────────────────────────────────────────────
SACRED = {
    "void":       "#0A0B0D",
    "rose_gold":  "#C9A227",
    "gold":       "#D4AF37",
    "lapis":      "#1E4D8C",
    "lapis_glow": "#2E6DC7",
    "cream":      "#F5EFE4",
    "deep":       "#12131A",
    "surface":    "#1A1B23",
}

EYE_SVG = """<svg viewBox="0 0 100 50" xmlns="http://www.w3.org/2000/svg" width="120" height="60">
  <ellipse cx="50" cy="25" rx="48" ry="22" fill="none" stroke="#C9A227" stroke-width="1.5"/>
  <circle cx="50" cy="25" r="14" fill="none" stroke="#1E4D8C" stroke-width="1.5"/>
  <circle cx="50" cy="25" r="8" fill="#1E4D8C" opacity="0.8"/>
  <circle cx="50" cy="25" r="4" fill="#2E6DC7"/>
  <circle cx="46" cy="22" r="2" fill="white" opacity="0.6"/>
  <line x1="2" y1="25" x2="22" y2="25" stroke="#C9A227" stroke-width="0.8" opacity="0.6"/>
  <line x1="78" y1="25" x2="98" y2="25" stroke="#C9A227" stroke-width="0.8" opacity="0.6"/>
</svg>"""

SACRED_CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap');

  .stApp {{
    background-color: {SACRED['void']};
    color: {SACRED['cream']};
  }}
  .stSidebar {{
    background-color: {SACRED['deep']} !important;
    border-right: 1px solid {SACRED['rose_gold']}44;
  }}
  h1, h2, h3 {{
    font-family: 'Cinzel', serif !important;
    color: {SACRED['rose_gold']} !important;
    letter-spacing: 0.05em;
  }}
  p, li, label, .stMarkdown {{
    font-family: 'EB Garamond', serif !important;
    color: {SACRED['cream']} !important;
    font-size: 1.05rem;
  }}
  .stButton > button {{
    background: linear-gradient(135deg, {SACRED['lapis']}, {SACRED['lapis_glow']});
    color: {SACRED['cream']};
    border: 1px solid {SACRED['rose_gold']}88;
    border-radius: 4px;
    font-family: 'Cinzel', serif;
    letter-spacing: 0.08em;
    transition: all 0.3s ease;
  }}
  .stButton > button:hover {{
    border-color: {SACRED['rose_gold']};
    box-shadow: 0 0 12px {SACRED['lapis_glow']}66;
  }}
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea,
  .stNumberInput > div > div > input {{
    background-color: {SACRED['surface']};
    color: {SACRED['cream']};
    border: 1px solid {SACRED['rose_gold']}44;
    font-family: 'EB Garamond', serif;
    border-radius: 4px;
  }}
  .stSelectbox > div > div,
  .stMultiSelect > div > div {{
    background-color: {SACRED['surface']};
    color: {SACRED['cream']};
    border: 1px solid {SACRED['rose_gold']}44;
  }}
  [data-baseweb="tab"] {{
    font-family: 'Cinzel', serif !important;
    color: {SACRED['cream']}88 !important;
    letter-spacing: 0.05em;
  }}
  [aria-selected="true"] {{
    color: {SACRED['rose_gold']} !important;
    border-bottom: 2px solid {SACRED['rose_gold']} !important;
  }}
  .stDownloadButton > button {{
    background: linear-gradient(135deg, #2d1f00, #4a3000);
    color: {SACRED['rose_gold']};
    border: 1px solid {SACRED['rose_gold']}88;
    font-family: 'Cinzel', serif;
  }}
  .stChatMessage {{
    background-color: {SACRED['surface']} !important;
    border: 1px solid {SACRED['rose_gold']}22 !important;
    border-radius: 6px !important;
  }}
  .stChatMessage [data-testid="chatAvatarIcon-user"] {{
    background-color: {SACRED['lapis']} !important;
  }}
  .stChatMessage [data-testid="chatAvatarIcon-assistant"] {{
    background-color: #3d2800 !important;
  }}
  .step-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
    font-family: 'EB Garamond', serif;
  }}
  .step-done  {{ color: #4CAF50; }}
  .step-active {{ color: {SACRED['rose_gold']}; font-weight: bold; }}
  .step-wait  {{ color: {SACRED['cream']}44; }}
  .seal {{
    font-family: monospace;
    font-size: 0.78rem;
    color: {SACRED['rose_gold']}aa;
    word-break: break-all;
  }}
  .divider {{
    border: none;
    border-top: 1px solid {SACRED['rose_gold']}22;
    margin: 1.5rem 0;
  }}
  .warning-box {{
    background: #1a0a00;
    border: 1px solid {SACRED['rose_gold']}66;
    border-radius: 6px;
    padding: 1rem;
    font-family: 'EB Garamond', serif;
    color: {SACRED['cream']}cc;
    font-size: 0.95rem;
  }}
</style>
"""


# ── Page setup ────────────────────────────────────────────────────────────────

def setup_page() -> None:
    st.set_page_config(
        page_title="Cursiv — The Sovereign Temple",
        page_icon="👁",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(SACRED_CSS, unsafe_allow_html=True)


def render_header() -> None:
    col1, col2 = st.columns([1, 10])
    with col1:
        st.markdown(EYE_SVG, unsafe_allow_html=True)
    with col2:
        st.markdown("# Cursiv v2.1.5")
        st.markdown(
            f'<p style="color:{SACRED["rose_gold"]}88; font-style:italic; margin-top:-0.5rem;">'
            "The Sovereign Agent Temple — Black • Rose Gold • Glowing Lapis Eye"
            "</p>",
            unsafe_allow_html=True,
        )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if not _BACKEND_OK:
        st.error(
            f"**Backend unavailable.** Could not import from Cursiv-v2.\n\n"
            f"Expected path: `{_CURSIV_V2}`\n\n`{_BACKEND_ERR}`"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uploaded_to_webapp_files(uploaded_files) -> list[dict]:
    """Convert Streamlit UploadedFile objects to the format webapp.py expects."""
    result = []
    for f in (uploaded_files or []):
        try:
            content = f.read().decode("utf-8-sig")
        except Exception:
            content = ""
        result.append({
            "name": f.name,
            "relative_path": getattr(f, "name", f.name),
            "content": content,
        })
    return result


def _steps_html(labels: list[str], complete: int) -> str:
    rows = []
    for i, label in enumerate(labels):
        if i < complete:
            css, icon = "step-done", "✓"
        elif i == complete:
            css, icon = "step-active", "▶"
        else:
            css, icon = "step-wait", "○"
        rows.append(f'<div class="step-row {css}">{icon} {label}</div>')
    return "".join(rows)


# ── Tab 1: The Forge (Create & Chat) ─────────────────────────────────────────

def render_forge() -> None:
    st.markdown("## The Forge")
    st.markdown("> *JSON / JSONL → binary strand → living agent capsule. Every agent begins as raw strand.*")

    # ── Inputs ──
    col_in, col_out = st.columns([3, 2])

    with col_in:
        st.markdown("### Create Agent")
        agent_name = st.text_input("Agent name", value="browser_json_agent", key="forge_name")
        c1, c2 = st.columns(2)
        with c1:
            council_size = st.number_input("Council size", min_value=0, max_value=14, value=14, key="forge_council")
        with c2:
            generations = st.number_input("Evolve (generations)", min_value=0, max_value=10, value=2, key="forge_gen")

        uploaded_files = st.file_uploader(
            "JSON / JSONL files — select one, many, or Ctrl+A for whole folder",
            type=["json", "jsonl"],
            accept_multiple_files=True,
            key="forge_files",
        )

        if uploaded_files:
            n = len(uploaded_files)
            st.caption(f"{n} file{'s' if n != 1 else ''} selected: " + ", ".join(f"`{f.name}`" for f in uploaded_files[:6]) + (f" +{n-6} more" if n > 6 else ""))

        inline_json = st.text_area(
            "Inline JSON (optional)",
            height=120,
            placeholder='{"agent": "inline", "mission": "become a Cursiv agent"}',
            key="forge_inline",
        )

        weave_btn = st.button("Weave Agent", key="forge_weave", disabled=not _BACKEND_OK)

    with col_out:
        st.markdown("### Agent Output")
        save_zip = st.checkbox("Download capsule zip after weaving", value=True, key="forge_save")
        steps_placeholder = st.empty()
        result_placeholder = st.empty()
        download_placeholder = st.empty()

    # ── Weave action ──
    if weave_btn:
        if not uploaded_files and not inline_json.strip():
            st.warning("Choose JSON files or paste inline JSON first.")
        else:
            steps_placeholder.markdown(
                _steps_html(["Reading input", "Sending to Cursiv", "Interpreting binary strand", "Exporting capsule"], 0),
                unsafe_allow_html=True,
            )
            try:
                webapp_files = _uploaded_to_webapp_files(uploaded_files)
                steps_placeholder.markdown(
                    _steps_html(["Reading input", "Sending to Cursiv", "Interpreting binary strand", "Exporting capsule"], 1),
                    unsafe_allow_html=True,
                )

                payload = {
                    "name": agent_name or "browser_json_agent",
                    "council_size": int(council_size),
                    "generations": int(generations),
                    "inline_json": inline_json.strip(),
                    "files": webapp_files,
                }

                with tempfile.TemporaryDirectory() as tmpdir:
                    result = weave_payload(payload, workspace=tmpdir)

                steps_placeholder.markdown(
                    _steps_html(["Reading input", "Sending to Cursiv", "Interpreting binary strand", "Exporting capsule"], 4),
                    unsafe_allow_html=True,
                )

                # Store session for chat
                st.session_state["session_id"] = result.summary.get("session_id", "")
                st.session_state["agent_name_display"] = result.summary.get("agent", {}).get("name", agent_name)
                st.session_state["suggested_prompts"] = result.summary.get("suggested_prompts", [])
                st.session_state["chat_messages"] = [
                    {"role": "assistant", "content": result.summary.get("participation_event", {}).get("response", f"{agent_name} is awake.")}
                ]
                st.session_state["archive_bytes"] = result.archive_bytes
                st.session_state["archive_name"] = result.archive_name

                # Show result summary
                s = result.summary
                agent_info = s.get("agent", {})
                result_placeholder.markdown(
                    f"""
**Agent:** `{agent_info.get('name', '')}` (id: `{agent_info.get('id', '')[:12]}...`)

**Records:** {s.get('records', 0)} · **Binary bits:** {s.get('binary_strand_bits', 0)} · **Generation:** {s.get('generation', 0)}

<span class="seal">Capsule: {s.get('output', {}).get('capsule_json', '—')}</span>
""",
                    unsafe_allow_html=True,
                )

                if save_zip and result.archive_bytes:
                    download_placeholder.download_button(
                        label=f"Download {result.archive_name}",
                        data=result.archive_bytes,
                        file_name=result.archive_name,
                        mime="application/zip",
                        key="forge_dl",
                    )

            except Exception as e:
                steps_placeholder.markdown(
                    _steps_html(["Stopped"], 0),
                    unsafe_allow_html=True,
                )
                result_placeholder.error(f"**Could not weave agent.** {e}")

    # ── Chat section ──
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    session_id = st.session_state.get("session_id", "")
    agent_display = st.session_state.get("agent_name_display", "")

    if session_id and agent_display:
        st.markdown(f"### Talk To The Agent — *{agent_display}*")

        # Suggested prompt buttons
        prompts = st.session_state.get("suggested_prompts", [])
        if prompts:
            prompt_cols = st.columns(min(len(prompts), 4))
            for i, prompt in enumerate(prompts[:4]):
                with prompt_cols[i]:
                    if st.button(prompt, key=f"prompt_{i}"):
                        st.session_state["prefill_chat"] = prompt

        # Chat log
        messages = st.session_state.get("chat_messages", [])
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Chat input
        prefill = st.session_state.pop("prefill_chat", "")
        question = st.chat_input("Ask the agent about its source knowledge...", key="forge_chat_input")
        if not question and prefill:
            question = prefill

        if question and _BACKEND_OK:
            st.session_state["chat_messages"].append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)
            try:
                chat_result = chat_payload({"session_id": session_id, "question": question})
                response = chat_result.get("response", "")
                reflections = chat_result.get("self_reflection_count", 0)
                full_response = f"{response}\n\n*Reflections: {reflections}*"
                st.session_state["chat_messages"].append({"role": "assistant", "content": full_response})
                st.session_state["suggested_prompts"] = chat_result.get("suggested_prompts", prompts)
                with st.chat_message("assistant"):
                    st.write(full_response)
            except Exception as e:
                st.error(f"Chat error: {e}")

        # Re-download button if zip is in state
        if st.session_state.get("archive_bytes"):
            st.download_button(
                label=f"Re-download {st.session_state.get('archive_name', 'capsule.zip')}",
                data=st.session_state["archive_bytes"],
                file_name=st.session_state.get("archive_name", "capsule.zip"),
                mime="application/zip",
                key="forge_redl",
            )
    else:
        st.markdown(
            f'<p style="color:{SACRED["cream"]}44; font-style:italic;">Weave an agent above to begin the conversation.</p>',
            unsafe_allow_html=True,
        )


# ── Tab 2: Sovereign Wrapper ──────────────────────────────────────────────────

def render_sovereign() -> None:
    st.markdown("## Sovereign Wrapper")
    st.markdown("> *Commit agents to the evolutionary process. Package them as a standalone sovereign AI system.*")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        system_name = st.text_input("System name", value="sovereign_cursiv_system", key="sov_name")

        use_current = st.checkbox(
            "Use current web-created agent (if available)",
            value=True,
            key="sov_use_current",
        )

        agent_files = st.file_uploader(
            "Agent capsule JSON(s) — or a folder of agents",
            type=["json"],
            accept_multiple_files=True,
            key="sov_files",
        )
        if agent_files:
            st.caption(f"{len(agent_files)} agent file{'s' if len(agent_files) != 1 else ''} selected")

        st.markdown(
            '<div class="warning-box">'
            "<strong>Committing to the evolutionary process is not quick.</strong><br>"
            "Training can take several hours to days depending on hardware. The process is worth it.<br><br>"
            "Minimal setup: modern laptop, 16GB RAM. NVIDIA GPU with CUDA strongly recommended. "
            "CPU-only: expect 4–24+ hours. GPU: 1–8 hours."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        ack = st.checkbox(
            "I understand the training time and hardware requirements.",
            value=False,
            key="sov_ack",
        )
        wrap_btn = st.button(
            "Wrap into Sovereign AI System",
            key="sov_wrap",
            disabled=(not ack or not _BACKEND_OK),
        )

    with col_right:
        st.markdown("### Evo Training Flow")
        training_steps_ph = st.empty()
        training_steps_ph.markdown(
            _steps_html(["Waiting for acknowledgment"], 0),
            unsafe_allow_html=True,
        )
        progress_bar = st.progress(0)
        result_ph = st.empty()
        dl_ph = st.empty()

    if wrap_btn:
        training_labels = [
            "Long Evo training session",
            "Accuracy follow-up training session",
            "Packaging local system",
        ]

        import time

        phases = [
            (0, 62, 0),
            (62, 88, 1),
            (88, 100, 2),
        ]
        for start, end, step_idx in phases:
            training_steps_ph.markdown(
                _steps_html(training_labels, step_idx),
                unsafe_allow_html=True,
            )
            for pct in range(start, end, 4):
                progress_bar.progress(pct / 100)
                time.sleep(0.05)

        training_steps_ph.markdown(
            _steps_html(training_labels, len(training_labels)),
            unsafe_allow_html=True,
        )
        progress_bar.progress(1.0)

        try:
            webapp_files = _uploaded_to_webapp_files(agent_files)
            current_session = st.session_state.get("session_id", "") if use_current else ""

            payload = {
                "system_name": system_name or "sovereign_cursiv_system",
                "session_id": current_session,
                "files": webapp_files,
            }

            with tempfile.TemporaryDirectory() as tmpdir:
                result = sovereign_payload(payload, workspace=tmpdir)

            sov_sum = result.summary
            result_ph.markdown(
                f"**Sovereign system ready.**\n\n"
                f"Agents wrapped: **{sov_sum.get('agent_count', 0)}**\n\n"
                f"System: `{sov_sum.get('system_name', '')}`",
            )
            dl_ph.download_button(
                label=f"Download Sovereign System Zip",
                data=result.archive_bytes,
                file_name=result.archive_name,
                mime="application/zip",
                key="sov_dl",
            )
        except Exception as e:
            result_ph.error(f"**Could not wrap system.** {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    setup_page()
    render_header()

    forge_tab, sovereign_tab = st.tabs(["The Forge — Create & Chat", "Sovereign Wrapper"])

    with forge_tab:
        render_forge()

    with sovereign_tab:
        render_sovereign()


if __name__ == "__main__":
    main()
