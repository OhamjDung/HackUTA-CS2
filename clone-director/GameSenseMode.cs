// Rule-based game sense for v2 clones: hand the bot back to the bot base's own AI when it hears or sees an
// enemy, never while a grenade is pulled, vary routes, and walk silently near a heard enemy at the player's
// own rate. Pure decisions live in Core/GameSense.cs (tested); this file only reads game state and acts.
// Every rule is off unless the clone profile's "game_sense" section turns it on.
using CloneDirector.Core;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;

namespace CloneDirector;

public sealed partial class CloneDirectorPlugin
{
    private const int SightCheckEveryTicks = 8;      // 8 of 64 ticks: an eighth of a second
    private const float QuietWalkDecisionSeconds = 1;
    private long _tickCount;

    private void GameSenseLoad()
    {
        RegisterEventHandler<EventPlayerFootstep>((e, _) => { OnNoise(e.Userid, Noise.Footstep); return HookResult.Continue; });
        RegisterEventHandler<EventWeaponReload>((e, _) => { OnNoise(e.Userid, Noise.Reload); return HookResult.Continue; });
    }

    // A noise the game reports from a player: every clone bot on the other team that is in hearing range
    // remembers roughly where it came from and, if a route is playing, hands control back.
    private void OnNoise(CCSPlayerController? source, Noise kind)
    {
        if (!_live || source is null || !source.IsValid || source.TeamNum is not (2 or 3)) return;
        var from = source.PlayerPawn.Value?.AbsOrigin;
        if (from is null) return;
        foreach (var b in _bots.Values)
        {
            var s = b.Session.Profile.GameSense;
            if (!(s.HearHandoff || s.QuietWalk) || !b.Player.IsValid || b.Player.TeamNum == source.TeamNum || !b.Player.PawnIsAlive) continue;
            var me = b.Player.PlayerPawn.Value?.AbsOrigin;
            if (me is null) continue;
            double distance = Math.Sqrt(Math.Pow(from.X - me.X, 2) + Math.Pow(from.Y - me.Y, 2) + Math.Pow(from.Z - me.Z, 2));
            if (!GameSense.Audible(kind, distance, s)) continue;
            // Quiet walking keys on footsteps and reloads only: gunfire means a fight, where the bot base fights.
            if (kind != Noise.Gunfire)
            {
                b.HeardAt = GameSense.Blur([from.X, from.Y, from.Z], distance, Random.Shared.NextDouble(), Random.Shared.NextDouble());
                b.HeardTime = Server.CurrentTime;
            }
            if (s.HearHandoff && b.Session.Playing) HandOff(b, $"heard enemy {kind.ToString().ToLowerInvariant()}");
        }
    }

    // Stop the route and give the bot to the bot base's AI. With grenade_safe_handoff, wait while a grenade
    // is pulled (until it changes weapon or grenade_wait_seconds pass): stopping mid-throw is the leading
    // suspect for the self-kills.
    private void HandOff(Binding b, string reason)
    {
        if (!b.Session.Playing) return;
        if (b.Session.Profile.GameSense.GrenadeSafeHandoff && HoldsGrenade(b))
        {
            if (b.PendingStop is null)
            {
                b.PendingStop = reason;
                b.PendingStopUntil = Server.CurrentTime + (float)b.Session.Profile.GameSense.GrenadeWaitSeconds;
            }
            return;
        }
        b.PendingStop = null;
        b.Session.Stop(reason);
        b.QuietUntil = Server.CurrentTime + Quirks.QuietSecondsAfterFight;
    }

    private static bool HoldsGrenade(Binding b) =>
        GameSense.IsGrenade(b.Player.PlayerPawn.Value?.WeaponServices?.ActiveWeapon.Value?.DesignerName);

    // Called once per bot per tick from Tick().
    private void GameSenseTick(Binding b, CCSPlayerPawn? pawn)
    {
        var s = b.Session.Profile.GameSense;
        if (b.PendingStop is { } waiting && (!b.Session.Playing || !HoldsGrenade(b) || Server.CurrentTime >= b.PendingStopUntil))
        {
            b.PendingStop = null;
            if (b.Session.Playing)
            {
                b.Session.Stop(waiting + " (after grenade)");
                b.QuietUntil = Server.CurrentTime + Quirks.QuietSecondsAfterFight;
            }
        }
        if (pawn is null || !pawn.IsValid || !b.Player.PawnIsAlive) return;
        if (s.SightHandoff && b.Session.Playing && _tickCount % SightCheckEveryTicks == 0 && SeesEnemy(b))
            HandOff(b, "saw enemy");
        // Never during or just after a fight (QuietUntil), so walking cannot weaken the bot base's fighting.
        if (s.QuietWalk && _live && !b.Session.Playing && Server.CurrentTime >= b.QuietUntil && Server.CurrentTime >= b.NextWalkDecision)
        {
            b.NextWalkDecision = Server.CurrentTime + QuietWalkDecisionSeconds;
            var me = pawn.AbsOrigin;
            if (b.HeardAt is { } heard && me is not null)
            {
                double distance = Math.Sqrt(Math.Pow(heard[0] - me.X, 2) + Math.Pow(heard[1] - me.Y, 2));
                if (GameSense.QuietWalkNow(s, Quirks.Value(b.Session.Profile, "slow_share"), Server.CurrentTime - b.HeardTime,
                        distance, Random.Shared.NextDouble()))
                    _api!.InjectUsercmd(b.Session.Slot, GameSense.Walk, (int)(QuietWalkDecisionSeconds * 1000));
            }
        }
    }

    // The game's own visibility: an enemy whose spotted-by mask includes this bot's slot.
    // Assumed, not yet seen in CS2: the mask is indexed by player slot.
    private bool SeesEnemy(Binding b)
    {
        foreach (var other in AllPlayers())
        {
            if (!other.IsValid || !other.PawnIsAlive || other.TeamNum is not (2 or 3) || other.TeamNum == b.Player.TeamNum) continue;
            var enemy = other.PlayerPawn.Value;
            if (enemy is null || !enemy.IsValid) continue;
            if (GameSense.SpottedBy(enemy.EntitySpottedState.SpottedByMask, b.Player.Slot)) return true;
        }
        return false;
    }
}
