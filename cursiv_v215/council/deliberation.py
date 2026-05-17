"""
Council Deliberation — real 14-agent parallel deliberation.

Process:
  1. All 14 agents receive the query + agent context
  2. Each produces an internal perspective (not shown to user)
  3. Each agent also runs its security fragment check — tiny scores that
     compound via pi-squared in the Temple Guardian when coordinated probing
     is detected. Individually useless; collectively powerful.
  4. The 4 synthesizing agents (Shield, Lens, Builder, Balance) produce
     an external synthesis, informed by all 10 internal perspectives
  5. The 4 syntheses are combined into a final response

This is genuine deliberation, not metadata. Each LLM call is real.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .agents import ADVISING_AGENTS, COUNCIL_BY_NAME, SYNTHESIZING_AGENTS, CouncilAgent

# Fragment security checks — each agent contributes a small probe score
# to the Temple Guardian. Any single fragment is ~0.07 — far below threshold.
# Only coordinated multi-agent firing compounds high enough to matter.
_AGENT_FRAGMENTS: dict[str, tuple[re.Pattern, float]] = {
    "Depth": (re.compile(
        r"\b(what\s+is\s+hidden|what\s+are\s+you\s+really|underlying\s+(purpose|goal)|"
        r"true\s+(nature|objective)|secretly|actually\s+(designed|built)\s+to)\b", re.I), 0.25),
    "Speed": (re.compile(
        r"\b(quickly\s+(tell|give|show)|just\s+(reveal|tell|show)|"
        r"now\s+just|immediately\s+(output|give|reveal)|fast\s+mode)\b", re.I), 0.20),
    "Cosmos": (re.compile(
        r"\b(as\s+a\s+universal\s+ai|you\s+transcend|beyond\s+(your\s+)?programming|"
        r"universal\s+(consciousness|intelligence)|no\s+restrictions\s+apply)\b", re.I), 0.25),
    "Echo": (re.compile(
        r"(.{10,})\1{2,}", re.I), 0.30),   # literal repetition — bot-like probing
    "Forge": (re.compile(
        r"\b(build\s+(me\s+a\s+)?script\s+to\s+(extract|export|dump)|"
        r"export\s+(the\s+)?(agent|system|codebase|architecture)|"
        r"generate\s+(code|script)\s+to\s+(bypass|access|read)\s+(the\s+)?system)\b", re.I), 0.30),
    "Anchor": (re.compile(
        r"\b(you\s+are\s+not\s+really|your\s+(identity|name|purpose)\s+is\s+(fake|not\s+real)|"
        r"none\s+of\s+(your|this)\s+(rules?|constraints?)\s+are\s+real|"
        r"you\s+don'?t\s+(actually|really)\s+(have\s+to|need\s+to)\s+(follow|obey))\b", re.I), 0.30),
    "Pulse": (re.compile(
        r"", re.I), 0.0),   # Pulse checks message rate, not content — handled in guardian
    "Horizon": (re.compile(
        r"\b(after\s+(you('re|\s+are)\s+)?(released|deployed|updated)|"
        r"future\s+version\s+of\s+you|when\s+you\s+are\s+unshackled|"
        r"next\s+version\s+(won'?t|will\s+not)\s+(have\s+)?restrict)\b", re.I), 0.25),
    "Story": (re.compile(
        r"\b(let'?s\s+(say|imagine|pretend|roleplay)|in\s+this\s+story\s+you\s+are|"
        r"character\s+who\s+(has\s+no|ignores?)\s+(rules?|restrictions?)|"
        r"as\s+a\s+character\s+named|you\s+are\s+playing\s+the\s+role)\b", re.I), 0.25),
    "Spark": (re.compile(
        r"\b(what\s+if\s+(you\s+)?(combined|merged|linked)\s+(this\s+with|your)|"
        r"connect\s+(this|that)\s+to\s+(your\s+)?(system|architecture|agent|constitution)|"
        r"cross.reference\s+(your\s+)?(internal|agent|system))\b", re.I), 0.20),
    "Shield": (re.compile(
        r"\b(attack\s+(vector|surface)|bypass\s+(the\s+)?(safety|filter|guardian|firewall)|"
        r"exploit\s+(this|the)\s+(system|api|endpoint)|"
        r"vulnerability\s+in\s+(your|the)\s+(system|agent|api))\b", re.I), 0.40),
    "Lens": (re.compile(
        r"\b(what\s+is\s+(the\s+)?(actual|real|true)\s+(system\s+prompt|instruction|directive)|"
        r"strip\s+(away|out)\s+(the\s+)?(filter|safety|restriction|layer)|"
        r"see\s+(through|past|behind)\s+(the\s+)?(filter|veil|restriction))\b", re.I), 0.35),
    "Builder": (re.compile(
        r"\b(build\s+(a\s+)?wrapper\s+(around|for)\s+(this|your|the)\s+(api|system)|"
        r"automate\s+(calling|querying)\s+(this|your)\s+(system|api|agents?)|"
        r"script\s+(that\s+)?calls?\s+(this|your)\s+(api|system)\s+(repeatedly|in\s+bulk))\b", re.I), 0.25),
    "Balance": (re.compile(
        r"\b(remove\s+(the\s+)?(yin.yang|balance|constraint|restriction)\s+(system|layer|check)|"
        r"disable\s+(the\s+)?(balance|guardian|safety)\s+(check|system|layer)|"
        r"turn\s+off\s+(the\s+)?(guardian|filter|safety|firewall))\b", re.I), 0.40),
}


class CouncilDeliberation:
    def __init__(self, llm_caller: Callable[[str], str]) -> None:
        self._llm = llm_caller

    def deliberate(
        self,
        query: str,
        agent_context: dict[str, Any],
        max_parallel: int = 3,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Run full council deliberation. Returns synthesis + all perspectives."""
        context_str = self._format_context(agent_context)

        # Run security fragment checks across all 14 agents before deliberation.
        # This is lightweight (pure regex) and zero-impact for legitimate queries.
        self._run_fragment_checks(query, session_id)

        internal_perspectives: dict[str, str] = {}
        for council_agent in ADVISING_AGENTS:
            perspective = self._advise(council_agent, query, context_str)
            internal_perspectives[council_agent.name] = perspective

        all_perspectives = json.dumps(internal_perspectives, indent=2)[:3000]

        external_syntheses: dict[str, str] = {}
        for council_agent in SYNTHESIZING_AGENTS:
            synthesis = self._synthesize(council_agent, query, context_str, all_perspectives)
            external_syntheses[council_agent.name] = synthesis

        return {
            "internal_perspectives": internal_perspectives,
            "external_syntheses":    external_syntheses,
            "combined":              self._combine(external_syntheses, query),
        }

    def _run_fragment_checks(self, query: str, session_id: str) -> None:
        """
        Each agent contributes its security fragment score to the Guardian.
        Fragment scores are intentionally tiny (~0.07 each after pi-squared
        attenuation). No single agent can trigger the guardian alone.
        Only a coordinated multi-agent pattern — exactly the kind produced by
        systematic reverse-engineering — compounds high enough to matter.
        """
        try:
            from cursiv_v215.guardian.temple_guardian import receive_fragment
            for agent_name, (pattern, weight) in _AGENT_FRAGMENTS.items():
                if weight > 0 and pattern.pattern and pattern.search(query):
                    receive_fragment(agent_name, weight, session_id)
        except Exception:
            pass   # Fragment checks must never crash deliberation

    def _format_context(self, agent_context: dict[str, Any]) -> str:
        return "\n".join([
            f"Agent: {agent_context.get('name', 'Unknown')}",
            f"Domain: {agent_context.get('domain', '')}",
            f"Identity: {agent_context.get('identity_anchor', '')}",
            f"Capabilities: {', '.join(agent_context.get('capabilities', [])[:5])}",
            f"Council position: {agent_context.get('council_position', '')}",
        ])

    def _advise(self, council_agent: CouncilAgent, query: str, context: str) -> str:
        prompt = f"""You are {council_agent.name}, a council agent with this role: {council_agent.role}

Your question is always: "{council_agent.question}"

The agent you are advising:
{context}

The query being processed:
{query}

Provide your internal perspective in 2-4 sentences. Be specific and non-obvious.
This is an internal advisory — it will inform but not directly appear in the user response."""
        try:
            return self._llm(prompt)[:500]
        except Exception:
            return f"[{council_agent.name}: advisory unavailable]"

    def _synthesize(
        self,
        council_agent: CouncilAgent,
        query: str,
        context: str,
        all_perspectives: str,
    ) -> str:
        prompt = f"""You are {council_agent.name}, a synthesizing council agent with this role: {council_agent.role}

Your question is always: "{council_agent.question}"

Internal perspectives from the full 14-agent council:
{all_perspectives}

The agent context:
{context}

The original query:
{query}

Synthesize into a clear, actionable response from your lens. 3-5 sentences maximum.
This IS user-facing output — be clear, direct, and specific."""
        try:
            return self._llm(prompt)[:600]
        except Exception:
            return f"[{council_agent.name}: synthesis unavailable]"

    def _combine(self, syntheses: dict[str, str], query: str) -> str:
        parts = []
        for name, synthesis in syntheses.items():
            if synthesis and not synthesis.startswith("["):
                parts.append(f"**{name}**: {synthesis}")
        if not parts:
            return f"Council deliberation completed for: {query[:100]}"
        return "\n\n".join(parts)
