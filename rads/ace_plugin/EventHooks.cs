/*
 * RADS Event Hooks — wires ACEmulator's internal events to the RADS bridge.
 *
 * Call RADSEventHooks.Register() once during server startup (after WorldManager.Initialize).
 * From that point on, all relevant game events are automatically forwarded to Python.
 *
 * ACE events used:
 *   - PlayerManager.PlayerEnterWorld
 *   - Landblock.AddWorldObject (player enters landblock)
 *   - Creature.OnDeath
 *   - Player.OnAttackNotification
 *   - WorldManager.ServerTick (5s interval for heartbeat)
 *
 * RAID DETECTION: 5+ players in the same landblock within 10 seconds = territory raid event.
 */

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;

// TODO: add ACE using directives:
// using ACE.Server.Managers;
// using ACE.Server.WorldObjects;
// using ACE.Server.Network.GameMessages;

namespace RADS
{
    public static class RADSEventHooks
    {
        // Track recent landblock entries for raid detection
        private static readonly ConcurrentDictionary<string, List<(string name, int level, DateTime ts)>>
            _landblockActivity = new();

        private static DateTime _lastTickSent = DateTime.MinValue;

        // ── Registration ──────────────────────────────────────────────────────

        public static void Register()
        {
            // TODO: hook into ACE event system:
            //
            // PlayerManager.OnAddPlayer      += OnPlayerEnterWorld;
            // PlayerManager.OnRemovePlayer   += OnPlayerExitWorld;
            //
            // For combat events, hook inside Creature.DamageTarget or Player.TakeDamage:
            //   if (attacker is Player p && target is RADSBotCreature) OnBotAttacked(p, target);
            //   if (target  is Player p && killer is RADSBotCreature)  OnPlayerKilled(p, killer);
            //   if (killer  is Player p && target is RADSBotCreature)  OnBotKilled(target, p);
            //
            // For level-up:
            //   Creature.OnLevelUp += OnBotLevelUp;  // only for RADS bot creatures
            //
            // For server tick:
            //   WorldManager.ReallyLongUpdateBegan += OnServerTick;

            Console.WriteLine("[RADS] Event hooks registered.");
        }

        // ── Event handlers ────────────────────────────────────────────────────

        public static void OnPlayerEnterLandblock(
            string playerName, int playerLevel,
            string landblock,  string allegiance = "")
        {
            RADSBridgeServer.SendPlayerEnter(playerName, playerLevel, landblock, allegiance);
            TrackForRaidDetection(playerName, playerLevel, landblock);
        }

        public static void OnPlayerExitLandblock(string playerName, string landblock)
        {
            RADSBridgeServer.SendPlayerExit(playerName, landblock);
        }

        public static void OnBotAttacked(string attackerName, int attackerLevel, string landblock)
        {
            RADSBridgeServer.SendCombatStarted(attackerName, attackerLevel, landblock);
        }

        public static void OnBotKilled(string botId, string killerName, string landblock, int botLevel)
        {
            RADSBridgeServer.SendBotDeath(botId, killerName, landblock, botLevel);
        }

        public static void OnBotLevelUp(string botId, int newLevel)
        {
            RADSBridgeServer.SendBotLevelUp(botId, newLevel);
        }

        public static void OnServerTick()
        {
            // Throttle to once per 5 seconds
            if ((DateTime.UtcNow - _lastTickSent).TotalSeconds < 5) return;
            _lastTickSent = DateTime.UtcNow;

            // TODO: int onlinePlayers = PlayerManager.GetOnlinePlayers().Count();
            // TODO: int activeBots    = RADSBotRegistry.ActiveCount;
            RADSBotController.OnServerTick(0, 0);
        }

        // ── Raid detection ────────────────────────────────────────────────────

        private static void TrackForRaidDetection(string name, int level, string landblock)
        {
            var now  = DateTime.UtcNow;
            var list = _landblockActivity.GetOrAdd(landblock, _ => new List<(string, int, DateTime)>());

            lock (list)
            {
                list.RemoveAll(e => (now - e.ts).TotalSeconds > 10);
                list.Add((name, level, now));

                if (list.Count >= 5)
                {
                    var names   = list.Select(e => e.name).ToArray();
                    var avgLvl  = (int)list.Average(e => e.level);
                    RADSBridgeServer.SendTerritoryRaid(landblock, names, avgLvl);
                    list.Clear();
                }
            }
        }
    }
}
