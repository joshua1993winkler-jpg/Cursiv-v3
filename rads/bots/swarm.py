"""
RADSSwarm — the master controller. Coordinates all 14 cohorts.

Responsibilities:
  - Receives inbound events from the ACE bridge and routes them
  - Handles cross-cohort coordination (reinforcement requests)
  - Maintains the global KOS list
  - Runs the economy tick (loot distribution, vendor pricing)
  - Logs world events to Obsidian and session memory
  - Reports status on demand

This is the brain. The cohorts are the hands.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from .bot import RADSBot, BotState
from .cohort import RADSCohort
from ..bridge.ace_bridge import ACEBridge
from ..bridge.protocol import (
    BotRole, ThreatLevel, InboundType, OutboundType,
    pack, unpack,
    PlayerEnterEvent, BotDeathEvent, TerritoryRaidEvent,
)
from ..intelligence.memory import ThreatMemory
from ..intelligence.threat import ThreatAssessor

log = logging.getLogger("rads.swarm")

ROOT     = Path(__file__).parent.parent.parent
LOG_FILE = ROOT / ".cursiv" / "rads" / "world_events.jsonl"

# Phase agent names — map to your 14 PiForge vault agents
AGENT_NAMES = [
    "Energy",       "Emergency",   "Grounding",  "Route",
    "Structure",    "Connectivity","FutureState", "Recovery",
    "Integration",  "Expansion",   "Refinement", "Mastery",
    "Transcendence","Sovereign",
]

# Default bots per cohort and role distribution
ROLE_DISTRIBUTION = {
    BotRole.HUNTER:  30,
    BotRole.SCOUT:   15,
    BotRole.GUARD:   12,
    BotRole.ELITE:    8,
    BotRole.CRAFTER:  4,
    BotRole.MONARCH:  1,
}


class RADSSwarm:
    """
    Master swarm controller. One instance per RADS server process.
    """

    def __init__(self, bridge: ACEBridge, territory_map: Optional[dict] = None):
        self._bridge   = bridge
        self._memory   = ThreatMemory()
        self._assessor = ThreatAssessor(self._memory)
        self._cohorts: dict[int, RADSCohort] = {}
        self._territory_map = territory_map or {}   # cohort_id → [landblocks]
        self._start_time    = time.time()
        self._event_count   = 0
        self._bot_counter   = 0

        self._init_cohorts()
        self._register_bridge_handlers()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _init_cohorts(self) -> None:
        for i in range(14):
            territory = self._territory_map.get(i, [])
            cohort    = RADSCohort(
                cohort_id  = i,
                agent_name = AGENT_NAMES[i],
                bridge     = self._bridge,
                territory  = territory,
            )
            # Populate with bots
            for role, count in ROLE_DISTRIBUTION.items():
                for j in range(count):
                    bot_id  = f"c{i:02d}_{role.value[:2]}_{j:03d}"
                    bot     = RADSBot(bot_id=bot_id, role=role, cohort_id=i, level=1)
                    cohort.register_bot(bot)
                    self._bot_counter += 1
            self._cohorts[i] = cohort
        log.info(f"[RADS Swarm] {len(self._cohorts)} cohorts initialized · {self._bot_counter} bots total")

    def _register_bridge_handlers(self) -> None:
        b = self._bridge
        b.on(InboundType.PLAYER_ENTER,   self._on_player_enter)
        b.on(InboundType.COMBAT_STARTED, self._on_combat_started)
        b.on(InboundType.BOT_DEATH,      self._on_bot_death)
        b.on(InboundType.TERRITORY_RAID, self._on_territory_raid)
        b.on(InboundType.BOT_LEVEL_UP,   self._on_bot_level_up)
        b.on(InboundType.BOT_LOOT,       self._on_bot_loot)
        b.on(InboundType.SERVER_TICK,    self._on_server_tick)
        b.on(InboundType.SPAWN_CONFIRM,  self._on_spawn_confirm)

    # ── Main run loop ─────────────────────────────────────────────────────────

    async def run(self) -> None:
        log.info("[RADS Swarm] Starting swarm brain...")
        await asyncio.gather(
            self._bridge.run(),
            self._maintenance_loop(),
        )

    async def _maintenance_loop(self) -> None:
        """Periodic tasks: KOS sync, dead bot respawn requests, compaction."""
        while True:
            await asyncio.sleep(60)
            try:
                await self._sync_kos_list()
                await self._request_dead_bot_respawns()
                if int(time.time()) % 3600 < 60:
                    self._memory.compact()
            except Exception as e:
                log.error(f"[RADS Swarm] Maintenance error: {e}")

    # ── Event handlers ────────────────────────────────────────────────────────

    async def _on_player_enter(self, msg: dict) -> None:
        evt = PlayerEnterEvent.from_dict(msg)
        if evt.is_bot:
            return

        cohort = self._cohort_for_landblock(evt.landblock)
        if cohort is None:
            return

        assessment = self._assessor.assess_player_enter(
            player_name  = evt.player_name,
            player_level = evt.player_level,
            allegiance   = evt.allegiance,
            zone_bots    = len(cohort.alive_bots),
        )

        self._log_event("player_enter", {
            "player": evt.player_name,
            "level":  evt.player_level,
            "threat": assessment.level.name,
            "reason": assessment.reason,
        })

        if assessment.level > ThreatLevel.NEUTRAL:
            deployed = await cohort.respond_to_threat(assessment)
            log.info(
                f"[RADS] {evt.player_name} (lvl {evt.player_level}) entered {evt.landblock} "
                f"→ {assessment.level.name} · {deployed} bots deployed"
            )

    async def _on_combat_started(self, msg: dict) -> None:
        attacker = msg.get("attacker_name", "unknown")
        level    = int(msg.get("attacker_level", 0))
        landblock = msg.get("landblock", "0000")

        assessment = self._assessor.assess_attack(attacker, level)
        cohort     = self._cohort_for_landblock(landblock)

        self._log_event("combat_started", {
            "attacker": attacker, "level": level,
            "response": assessment.level.name,
        })

        if cohort:
            deployed = await cohort.respond_to_threat(assessment)
            # If KOS, also pull from neighboring cohort
            if assessment.level >= ThreatLevel.SWARM:
                neighbor = self._nearest_cohort(landblock, exclude=cohort.cohort_id)
                if neighbor:
                    extra = await neighbor.respond_to_threat(assessment)
                    log.info(f"[RADS] Cross-cohort reinforcement: {extra} bots from cohort {neighbor.cohort_id}")

    async def _on_bot_death(self, msg: dict) -> None:
        evt    = BotDeathEvent.from_dict(msg)
        cohort = self._cohort_for_bot(evt.bot_id)
        bot    = cohort.get_bot(evt.bot_id) if cohort else None

        if bot:
            bot.set_dead()

        assessment = self._assessor.assess_bot_kill(
            killer_name  = evt.killer,
            killer_level = evt.bot_level,
            bot_role     = bot.role if bot else BotRole.HUNTER,
        )

        self._log_event("bot_death", {
            "bot_id": evt.bot_id, "killer": evt.killer,
            "retaliation": assessment.level.name,
        })

        if cohort:
            await cohort.respond_to_threat(assessment)
            # Request respawn after a short delay
            await asyncio.sleep(30)
            await self._bridge.send(pack(
                OutboundType.SPAWN_BOT,
                bot_type  = bot.role.value if bot else "hunter",
                cohort_id = cohort.cohort_id,
                landblock = evt.landblock,
            ))

    async def _on_territory_raid(self, msg: dict) -> None:
        evt = TerritoryRaidEvent.from_dict(msg)
        assessment = self._assessor.assess_territory_raid(
            attacker_names = evt.attacker_names,
            avg_level      = evt.avg_level,
            zone           = evt.zone,
        )

        self._log_event("territory_raid", {
            "zone": evt.zone, "attackers": evt.attacker_count,
            "response": assessment.level.name,
        })

        cohort = self._cohort_for_zone(evt.zone)
        if cohort:
            await cohort.respond_to_threat(assessment)

        if assessment.level >= ThreatLevel.OVERWHELMING:
            await self._broadcast_zone_alert(evt.zone, evt.attacker_count)
            # Pull in two neighboring cohorts
            neighbors = self._neighboring_cohorts(evt.zone, count=2)
            for nb in neighbors:
                await nb.respond_to_threat(assessment)

    async def _on_bot_level_up(self, msg: dict) -> None:
        bot_id    = msg.get("bot_id", "")
        new_level = int(msg.get("new_level", 0))
        cohort    = self._cohort_for_bot(bot_id)
        bot       = cohort.get_bot(bot_id) if cohort else None
        if bot:
            bot.level = new_level
            log.debug(f"[RADS] {bot_id} reached level {new_level}")

    async def _on_bot_loot(self, msg: dict) -> None:
        pass   # economy tick handles distribution

    async def _on_server_tick(self, msg: dict) -> None:
        self._event_count += 1
        if self._event_count % 12 == 0:   # every ~60s of ticks
            log.info(f"[RADS Status] {self.status_line()}")

    async def _on_spawn_confirm(self, msg: dict) -> None:
        bot_id    = msg.get("bot_id", "")
        cohort_id = int(msg.get("cohort_id", 0))
        role      = BotRole(msg.get("role", "hunter"))
        landblock = msg.get("landblock", "0000")
        level     = int(msg.get("level", 1))

        cohort = self._cohorts.get(cohort_id)
        if cohort:
            bot = RADSBot(
                bot_id=bot_id, role=role, cohort_id=cohort_id,
                level=level, landblock=landblock,
            )
            cohort.register_bot(bot)
            log.info(f"[RADS] Spawned {bot_id} in cohort {cohort_id} @ {landblock}")

    # ── Cross-cohort coordination ─────────────────────────────────────────────

    async def _sync_kos_list(self) -> None:
        kos = self._memory.kos_list()
        if kos:
            await self._bridge.send(pack(OutboundType.KOS_UPDATE, kos_list=kos))

    async def _request_dead_bot_respawns(self) -> None:
        for cohort in self._cohorts.values():
            dead = [b for b in cohort.bots if b.state == BotState.DEAD]
            for bot in dead:
                age = time.time() - bot.last_active
                if age > 120:   # dead for 2+ minutes → respawn
                    await self._bridge.send(pack(
                        OutboundType.SPAWN_BOT,
                        bot_type  = bot.role.value,
                        cohort_id = bot.cohort_id,
                        landblock = bot.landblock,
                    ))

    async def _broadcast_zone_alert(self, zone: str, attacker_count: int) -> None:
        msg = f"RADS territory violation in {zone} — {attacker_count} hostiles detected. Mobilizing."
        await self._bridge.send(pack(OutboundType.WORLD_MSG, zone=zone, text=msg))

    # ── Routing helpers ───────────────────────────────────────────────────────

    def _cohort_for_landblock(self, landblock: str) -> Optional[RADSCohort]:
        for cohort in self._cohorts.values():
            if landblock in cohort.territory:
                return cohort
        # fallback: cohort 0
        return self._cohorts.get(0)

    def _cohort_for_bot(self, bot_id: str) -> Optional[RADSCohort]:
        for cohort in self._cohorts.values():
            if cohort.get_bot(bot_id):
                return cohort
        return None

    def _cohort_for_zone(self, zone: str) -> Optional[RADSCohort]:
        return self._cohort_for_landblock(zone)

    def _nearest_cohort(self, landblock: str, exclude: int = -1) -> Optional[RADSCohort]:
        for cohort in self._cohorts.values():
            if cohort.cohort_id != exclude and cohort.available_bots:
                return cohort
        return None

    def _neighboring_cohorts(self, zone: str, count: int = 2) -> list[RADSCohort]:
        results = []
        for cohort in self._cohorts.values():
            if cohort.available_bots and len(results) < count:
                results.append(cohort)
        return results

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log_event(self, event_type: str, data: dict) -> None:
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            entry = {"ts": time.time(), "event": event_type, **data}
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # Live-stream to Obsidian if available
        try:
            from cursiv_v215.obsidian.exporter import livestream_exchange
            summary = f"[RADS/{event_type.upper()}] " + " · ".join(f"{k}={v}" for k, v in data.items())
            livestream_exchange("RADS System", summary, model="rads-swarm")
        except Exception:
            pass

    # ── Status ────────────────────────────────────────────────────────────────

    def status_line(self) -> str:
        total_alive    = sum(len(c.alive_bots) for c in self._cohorts.values())
        total_engaging = sum(
            len([b for b in c.bots if b.state == BotState.ENGAGING])
            for c in self._cohorts.values()
        )
        uptime_h = (time.time() - self._start_time) / 3600
        return (
            f"Uptime {uptime_h:.1f}h · {total_alive}/{self._bot_counter} bots alive "
            f"· {total_engaging} in combat · {self._memory.summary()}"
        )

    def full_status(self) -> dict:
        return {
            "uptime_h":   round((time.time() - self._start_time) / 3600, 2),
            "total_bots": self._bot_counter,
            "cohorts":    [c.status_summary() for c in self._cohorts.values()],
            "threats":    self._memory.summary(),
            "top_threats": [
                {"name": r.name, "score": r.threat_score, "kos": r.kos, "kills": r.kill_count}
                for r in self._memory.top_threats(5)
            ],
        }
