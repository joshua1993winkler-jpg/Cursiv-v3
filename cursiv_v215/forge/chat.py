"""
Chat interface — query an agent with memory and council deliberation.

The chat layer sits between the user and the agent:
  1. Load agent from vault
  2. Retrieve relevant memories
  3. Route query through Oracle Router
  4. Optionally run council deliberation
  5. Record to memory
"""

from __future__ import annotations

from typing import Any

from ..core.agent import CursivAgent
from ..core.memory import get_memory
from ..council.deliberation import CouncilDeliberation
from ..dugout.vault import AgentVault
from .router import OracleRouter, default_router


class AgentChat:
    def __init__(
        self,
        router: OracleRouter | None = None,
        vault: AgentVault | None = None,
        use_council: bool = True,
    ) -> None:
        self._router = router or default_router()
        self._vault = vault or AgentVault()
        self._memory = get_memory()
        self._council = CouncilDeliberation(self._router.call) if use_council else None
        self._use_council = use_council

    def chat(self, agent_id: str, query: str, escalation_threshold: float = 0.35) -> dict[str, Any]:
        """Send a query to an agent. Returns response dict."""
        agent = self._vault.load(agent_id)
        if agent is None:
            return {"error": f"Agent {agent_id} not found in vault"}

        if agent.check_drift_abort():
            return {"error": f"Agent {agent.name} has drifted beyond abort threshold. Reverting."}

        memories = self._memory.get_relevant_memories(query, top_k=3)
        memory_context = self._format_memories(memories)

        if self._use_council and self._council:
            council_result = self._council.deliberate(
                query,
                agent_context={
                    "name": agent.name,
                    "domain": agent.knowledge_map.get("domain", ""),
                    "identity_anchor": agent.knowledge_map.get("identity_anchor", ""),
                    "capabilities": agent.capabilities,
                    "council_position": agent.council_position,
                },
            )
            response_text = council_result["combined"]
            council_data = council_result
        else:
            response_text = self._direct_query(agent, query, memory_context)
            council_data = {}

        quality = self._estimate_quality(response_text)
        self._memory.record_run(agent_id, query, response_text, quality)
        self._memory.increment_run_count(agent_id)
        self._memory.save()

        return {
            "agent": agent.name,
            "response": response_text,
            "quality": quality,
            "provider": self._router.active_provider,
            "council": council_data,
            "memory_hits": len(memories),
        }

    def _direct_query(self, agent: CursivAgent, query: str, memory_context: str) -> str:
        prompt = f"""You are {agent.name}.

Your identity: {agent.knowledge_map.get("identity_anchor", "")}
Your purpose (above): {agent.above}
Your operation (beneath): {agent.beneath}
Your self-reflection: {agent.self_reflection}

Relevant memory context:
{memory_context}

Query: {query}

Respond in your authentic voice. Be specific, grounded, and useful."""
        return self._router.call(prompt)

    def _format_memories(self, memories: list[dict]) -> str:
        if not memories:
            return "No relevant prior conversations."
        lines = []
        for m in memories:
            lines.append(f"- [{m['agent_id'][:8]}] Q: {m['query'][:60]} → {m['response_preview'][:80]}")
        return "\n".join(lines)

    def _estimate_quality(self, response: str) -> float:
        if not response or response.startswith("["):
            return 0.2
        word_count = len(response.split())
        if word_count < 10:
            return 0.3
        if word_count > 50:
            return min(0.95, 0.5 + word_count / 1000)
        return 0.6
