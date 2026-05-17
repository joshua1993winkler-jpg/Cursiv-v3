"""
Sovereign Systems Manager — higher-order system composition.

Manages relationships between agents, creates agent networks,
and enforces the system owner invariant across all compositions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from ..core.agent import CursivAgent
from ..core.constitution import SYSTEM_OWNER, get_constitution
from ..dugout.vault import AgentVault

_WEAVE_SEAL = "0d7f1c208104d1be59fac3"


@dataclass
class SovereignSystem:
    name: str
    leader: str = SYSTEM_OWNER
    agent_ids: list[str] = field(default_factory=list)
    relationships: list[dict[str, str]] = field(default_factory=list)
    constitution_hash: str = ""
    created_at: float = field(default_factory=time.time)
    active: bool = True

    def add_agent(self, agent_id: str, role: str = "member") -> None:
        if agent_id not in self.agent_ids:
            self.agent_ids.append(agent_id)
            self.relationships.append({"agent": agent_id, "role": role, "leader": self.leader})

    def verify_leader(self) -> bool:
        return self.leader == SYSTEM_OWNER


class SovereignManager:
    def __init__(self, vault: AgentVault | None = None) -> None:
        self._vault = vault or AgentVault()
        self._constitution = get_constitution()
        self._systems: dict[str, SovereignSystem] = {}

    def create_system(self, name: str) -> SovereignSystem:
        """Create a new agent system under the system owner."""
        system = SovereignSystem(
            name=name,
            leader=SYSTEM_OWNER,
            constitution_hash=self._constitution.hash,
        )
        self._systems[name] = system
        return system

    def compose(self, system_name: str, *agent_ids: str) -> SovereignSystem:
        """Compose multiple agents into a sovereign system."""
        system = self._systems.get(system_name) or self.create_system(system_name)
        for agent_id in agent_ids:
            agent = self._vault.load(agent_id)
            if agent:
                role = agent.council_position or "member"
                system.add_agent(agent_id, role)
        return system

    def route_query(self, system_name: str, query: str, context: str = "") -> dict[str, Any]:
        """Route a query through a sovereign system — finds best agent to handle it."""
        system = self._systems.get(system_name)
        if not system:
            return {"error": f"System {system_name} not found"}

        scored: list[tuple[float, str]] = []
        for agent_id in system.agent_ids:
            agent = self._vault.load(agent_id)
            if not agent:
                continue
            score = self._relevance_score(query, agent)
            scored.append((score, agent_id))

        if not scored:
            return {"error": "No agents available in system"}

        scored.sort(reverse=True)
        best_id = scored[0][1]
        best_agent = self._vault.load(best_id)
        return {
            "system": system_name,
            "selected_agent": best_id,
            "agent_name": best_agent.name if best_agent else "unknown",
            "score": scored[0][0],
            "leader": system.leader,
        }

    def _relevance_score(self, query: str, agent: CursivAgent) -> float:
        query_lower = query.lower()
        score = 0.0
        domain = agent.knowledge_map.get("domain", "").lower()
        if domain and domain in query_lower:
            score += 0.5
        for cap in agent.capabilities:
            if any(w in query_lower for w in cap.lower().split()):
                score += 0.1
        return min(score, 1.0)

    def list_systems(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "leader": s.leader,
                "agent_count": len(s.agent_ids),
                "active": s.active,
            }
            for s in self._systems.values()
        ]
