using System.Text.Json.Serialization;

namespace CloneDirector.Core;

// Rule-based game sense for v2 clones (.plans/v2-quirks-gamesense-plan.md). Every rule is off unless the
// profile's "game_sense" section turns it on, so earlier clones behave exactly as before.
// Inputs are only what a player could know: noises the game reports, the game's own "spotted" state,
// and the bot's own weapon. True hidden enemy positions are never used to trigger a rule.
// Starting distances are historical CS1.6 bot values (clone-model/research/cs2-game-sense.md), not
// verified CS2 audibility; they are settings so they can be tuned without a rebuild.
public sealed class GameSenseSettings
{
    [JsonPropertyName("hear_handoff")] public bool HearHandoff { get; init; }
    [JsonPropertyName("sight_handoff")] public bool SightHandoff { get; init; }
    [JsonPropertyName("enemy_close_handoff")] public bool EnemyCloseHandoff { get; init; } = true;
    [JsonPropertyName("grenade_safe_handoff")] public bool GrenadeSafeHandoff { get; init; }
    [JsonPropertyName("route_variety")] public bool RouteVariety { get; init; }
    [JsonPropertyName("quiet_walk")] public bool QuietWalk { get; init; }

    [JsonPropertyName("footstep_units")] public double FootstepUnits { get; init; } = 1100;
    [JsonPropertyName("gunfire_units")] public double GunfireUnits { get; init; } = 2000;
    [JsonPropertyName("reload_units")] public double ReloadUnits { get; init; } = 1100;
    [JsonPropertyName("heard_memory_seconds")] public double HeardMemorySeconds { get; init; } = 3;
    [JsonPropertyName("quiet_walk_units")] public double QuietWalkUnits { get; init; } = 1500;
    // Chance per decision (once a second) to walk silently while a heard enemy is near. Null: use the
    // player's measured slow_share quirk.
    [JsonPropertyName("quiet_walk_share")] public double? QuietWalkShare { get; init; }
    [JsonPropertyName("grenade_wait_seconds")] public double GrenadeWaitSeconds { get; init; } = 1;
    [JsonPropertyName("route_spawn_units")] public double RouteSpawnUnits { get; init; } = 600;
    [JsonPropertyName("recent_routes")] public int RecentRoutes { get; init; } = 2;
    [JsonPropertyName("recent_route_weight")] public double RecentRouteWeight { get; init; } = 0.25;

    public void Validate()
    {
        foreach (var (name, v) in new[] { ("footstep_units", FootstepUnits), ("gunfire_units", GunfireUnits),
                     ("reload_units", ReloadUnits), ("quiet_walk_units", QuietWalkUnits), ("route_spawn_units", RouteSpawnUnits) })
            if (!double.IsFinite(v) || v < 0 || v > 20000) throw new InvalidDataException($"game_sense.{name} must be 0 to 20000.");
        foreach (var (name, v) in new[] { ("heard_memory_seconds", HeardMemorySeconds), ("grenade_wait_seconds", GrenadeWaitSeconds) })
            if (!double.IsFinite(v) || v < 0 || v > 30) throw new InvalidDataException($"game_sense.{name} must be 0 to 30.");
        if (QuietWalkShare is double share && (!double.IsFinite(share) || share < 0 || share > 1))
            throw new InvalidDataException("game_sense.quiet_walk_share must be 0 to 1.");
        if (RecentRoutes is < 0 or > 10) throw new InvalidDataException("game_sense.recent_routes must be 0 to 10.");
        if (!double.IsFinite(RecentRouteWeight) || RecentRouteWeight < 0 || RecentRouteWeight > 1)
            throw new InvalidDataException("game_sense.recent_route_weight must be 0 to 1.");
    }
}

public enum Noise { Footstep, Gunfire, Reload }

public static class GameSense
{
    // Engine button bit for walking (Source IN_SPEED, the shift key).
    public const ulong Walk = 1UL << 17;

    /// <summary>True when a noise of this kind at this distance is in hearing range.</summary>
    public static bool Audible(Noise kind, double distance, GameSenseSettings s) => kind switch
    {
        Noise.Footstep => distance <= s.FootstepUnits,
        Noise.Gunfire => distance <= s.GunfireUnits,
        Noise.Reload => distance <= s.ReloadUnits,
        _ => false,
    };

    /// <summary>
    /// Where the bot believes a heard noise came from: the source moved by up to 0.2 x distance in a random
    /// horizontal direction, as the original bot blurs heard positions. Draws are uniform in [0, 1).
    /// </summary>
    public static float[] Blur(float[] source, double distance, double draw1, double draw2)
    {
        double r = 0.2 * distance * draw1, a = 2 * Math.PI * draw2;
        return [(float)(source[0] + r * Math.Cos(a)), (float)(source[1] + r * Math.Sin(a)), source[2]];
    }

    /// <summary>True for a grenade weapon. Stopping a route while one is pulled can kill the bot.</summary>
    public static bool IsGrenade(string? designerName) => designerName is { } n &&
        (n.Contains("grenade") || n.Contains("flashbang") || n.Contains("molotov") || n.Contains("decoy"));

    /// <summary>True when the bot should walk silently for the next second.</summary>
    public static bool QuietWalkNow(GameSenseSettings s, double? slowShare, double heardAgeSeconds, double heardDistance, double draw)
    {
        double share = s.QuietWalkShare ?? slowShare ?? 0;
        return s.QuietWalk && heardAgeSeconds <= s.HeardMemorySeconds && heardDistance <= s.QuietWalkUnits && draw < share;
    }

    /// <summary>True when this bot's slot is set in the enemy's spotted-by mask (the game's own visibility).</summary>
    public static bool SpottedBy(ReadOnlySpan<uint> spottedByMask, int slot) =>
        slot >= 0 && slot / 32 < spottedByMask.Length && (spottedByMask[slot / 32] & (1u << (slot % 32))) != 0;

    /// <summary>
    /// Route choice with variety. Destinations are drawn by the player's shares, with a destination used in
    /// the last few rounds down-weighted; then any route of that destination starting near the bot's spawn
    /// is drawn at random (the nearest one if none is near). Draws are uniform in [0, 1).
    /// </summary>
    public static Route? PickVaried(CloneProfile profile, string side, string buyType, string source, float[] spawn,
        IReadOnlyCollection<string> recentKeys, double draw1, double draw2)
    {
        var s = profile.GameSense;
        if (source == "off" || !profile.Routes.TryGetValue(side, out var routes)) return null;
        var groups = routes.Where(r => r.Source == source && (r.BuyType is null || r.BuyType == buyType))
            .GroupBy(r => r.Key).Select(g =>
            {
                double weight = profile.RouteShares.TryGetValue(side, out var shares) && shares.TryGetValue(g.Key, out var share)
                    ? share : g.First().Share;
                if (recentKeys.Contains(g.Key)) weight *= s.RecentRouteWeight;
                return (Routes: g.ToArray(), Weight: weight);
            }).Where(g => g.Weight > 0).ToArray();
        if (groups.Length == 0) return null;
        double target = Math.Clamp(draw1, 0, Math.BitDecrement(1d)) * groups.Sum(g => g.Weight);
        var chosen = groups[^1];
        foreach (var group in groups)
        {
            target -= group.Weight;
            if (target < 0) { chosen = group; break; }
        }
        double Distance(Route r) => Math.Sqrt(Enumerable.Range(0, 3).Sum(i => Math.Pow(r.Start[i] - spawn[i], 2)));
        var near = chosen.Routes.Where(r => Distance(r) <= s.RouteSpawnUnits).ToArray();
        if (near.Length == 0) return chosen.Routes.MinBy(Distance);
        return near[(int)(Math.Clamp(draw2, 0, Math.BitDecrement(1d)) * near.Length)];
    }
}
