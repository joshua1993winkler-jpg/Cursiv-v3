"""
RADS — Rogue Autonomous Defense System
Entry point. Run this to start the swarm.

Usage:
    python -m rads                     # connect to live ACE plugin on :9001
    python -m rads --sim               # simulation mode (no ACE needed)
    python -m rads --status            # print current threat memory and exit
    python -m rads --sim --bots 100    # sim with custom bot count per cohort
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(name)-22s  %(levelname)-8s  %(message)s",
    datefmt = "%H:%M:%S",
)
log = logging.getLogger("rads.main")


def _print_banner() -> None:
    print("""
  ██████╗  █████╗ ██████╗ ███████╗
  ██╔══██╗██╔══██╗██╔══██╗██╔════╝
  ██████╔╝███████║██║  ██║███████╗
  ██╔══██╗██╔══██║██║  ██║╚════██║
  ██║  ██║██║  ██║██████╔╝███████║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝

  Rogue Autonomous Defense System
  Cursiv Swarm Controller
  ──────────────────────────────────
""")


def _load_territory_map() -> dict:
    """Load cohort→landblock territory assignments from config if it exists."""
    cfg_path = Path(__file__).parent / "territory.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Default: empty — bots will be assigned landblocks dynamically by ACE
    return {str(i): [] for i in range(14)}


async def _run_swarm(sim: bool = False, bots_per_cohort: int = 70) -> None:
    from .bridge.ace_bridge import ACEBridge
    from .bots.swarm import RADSSwarm, ROLE_DISTRIBUTION
    import rads.bots.swarm as swarm_module

    # Adjust bot count if overridden
    if bots_per_cohort != 70:
        total = bots_per_cohort
        swarm_module.ROLE_DISTRIBUTION = {
            k: max(1, int(v * total / 70))
            for k, v in ROLE_DISTRIBUTION.items()
        }

    territory_map_raw = _load_territory_map()
    territory_map     = {int(k): v for k, v in territory_map_raw.items()}

    bridge = ACEBridge()
    if sim:
        bridge.enable_simulation()

    swarm = RADSSwarm(bridge=bridge, territory_map=territory_map)

    log.info(f"[RADS] Swarm initialized — {swarm._bot_counter} bots across 14 cohorts")
    log.info(f"[RADS] Mode: {'SIMULATION' if sim else 'LIVE (ACE:9001)'}")
    log.info(f"[RADS] Threat memory: {swarm._memory.summary()}")
    log.info("[RADS] Swarm is running. Press Ctrl+C to stop.")

    try:
        await swarm.run()
    except KeyboardInterrupt:
        log.info("[RADS] Swarm shutting down.")


def _print_status() -> None:
    from .intelligence.memory import ThreatMemory
    mem = ThreatMemory()
    print("\n" + "═" * 60)
    print("  RADS Threat Memory Status")
    print("═" * 60)
    print(f"  {mem.summary()}")
    print()
    top = mem.top_threats(10)
    if top:
        print(f"  {'Name':<20} {'Score':>6}  {'KOS':>4}  {'Kills':>6}  {'Attacks':>8}")
        print("  " + "─" * 52)
        for r in top:
            kos_str = " KOS" if r.kos else "    "
            print(f"  {r.name:<20} {r.threat_score:>6.2f} {kos_str}  {r.kill_count:>6}  {r.attack_count:>8}")
    else:
        print("  No threat records yet.")
    print("═" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="RADS — Rogue Autonomous Defense System")
    parser.add_argument("--sim",    action="store_true", help="Run in simulation mode (no ACE)")
    parser.add_argument("--status", action="store_true", help="Print threat memory status and exit")
    parser.add_argument("--bots",   type=int, default=70, help="Bots per cohort (default 70)")
    args = parser.parse_args()

    _print_banner()

    if args.status:
        _print_status()
        return

    asyncio.run(_run_swarm(sim=args.sim, bots_per_cohort=args.bots))


if __name__ == "__main__":
    main()
