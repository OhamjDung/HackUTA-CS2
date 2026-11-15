using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace CloneDirector.Core;

public sealed class CloneProfile
{
    [JsonPropertyName("clone_id")] public required string Id { get; init; }
    [JsonPropertyName("display_name")] public required string DisplayName { get; init; }
    [JsonPropertyName("stand_in_bot")] public string? StandInBot { get; init; }
    [JsonPropertyName("map")] public string Map { get; init; } = "de_mirage";
    [JsonPropertyName("buy_plan")] public Dictionary<string, Dictionary<string, PurchasePlan>> BuyPlan { get; init; } = [];
    [JsonPropertyName("routes")] public Dictionary<string, Route[]> Routes { get; init; } = [];
    [JsonPropertyName("route_shares")] public Dictionary<string, Dictionary<string, double>> RouteShares { get; init; } = [];
    // Optional. Written by clone_pipeline/quirks.py for learned-quirk clones such as "donkL".
    [JsonPropertyName("quirk_controls")] public Dictionary<string, QuirkControl> QuirkControls { get; init; } = [];

    public string Personality => StandInBot ?? DisplayName;
}

public sealed class QuirkControl
{
    // A number for most quirks. Unknown extra fields (applied_by, status) are ignored.
    [JsonPropertyName("value")] public double Value { get; init; }
}

public static class Quirks
{
    public const double MaxJumpsPerMinute = 60;
    // Only jump while running, so a jump never interrupts a held position.
    public const float MinRunSpeed = 150;
    // After damage or a nearby enemy shot, leave the bot base alone for this long.
    public const float QuietSecondsAfterFight = 5;

    /// <summary>Jumps per minute for this clone, or 0 when the profile has no such quirk.</summary>
    public static double JumpsPerMinute(CloneProfile profile) =>
        profile.QuirkControls.TryGetValue("jumps_per_min", out var control) ? control.Value : 0;

    /// <summary>True when a jump should start on this tick. draw is uniform in [0, 1).</summary>
    public static bool JumpNow(double jumpsPerMinute, double tickSeconds, double draw) =>
        jumpsPerMinute > 0 && draw < jumpsPerMinute / 60 * tickSeconds;
}

public sealed class PurchasePlan
{
    [JsonPropertyName("aliases")] public required string[] Aliases { get; init; }
}

public sealed class Route
{
    [JsonPropertyName("route_key")] public required string Key { get; init; }
    [JsonPropertyName("file")] public required string File { get; init; }
    [JsonPropertyName("label")] public string? Label { get; init; }
    [JsonPropertyName("start")] public required float[] Start { get; init; }
    [JsonPropertyName("source")] public string Source { get; init; } = "recorded";
    [JsonPropertyName("buy_type")] public string? BuyType { get; init; }
    [JsonPropertyName("share")] public double Share { get; init; } = 1;
}

public sealed class ProfileStore(string root)
{
    public string Root { get; } = Path.GetFullPath(root);
    public static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = false };

    public CloneProfile Load(string id)
    {
        if (!Regex.IsMatch(id, @"\A[a-zA-Z0-9_-]+\z"))
            throw new InvalidDataException("Clone ID must contain only letters, numbers, _ or -.");
        var profile = JsonSerializer.Deserialize<CloneProfile>(System.IO.File.ReadAllText(Resolve(id + ".json")), JsonOptions)
            ?? throw new InvalidDataException("Empty clone profile.");
        if (profile.Id != id) throw new InvalidDataException("clone_id does not match the file name.");
        Validate(profile);
        return profile;
    }

    public string Resolve(string relative)
    {
        if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative))
            throw new InvalidDataException("Clone files must use relative paths.");
        // Extended Windows paths (\\?\...) do not normalize forward slashes for us.
        relative = relative.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
        var full = Path.GetFullPath(Path.Combine(Root, relative));
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (!full.StartsWith(Root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, comparison))
            throw new InvalidDataException("Clone file is outside the clones folder.");
        return full;
    }

    public void Validate(CloneProfile profile)
    {
        if (profile.BuyPlan is null || profile.Routes is null || profile.RouteShares is null)
            throw new InvalidDataException("Clone collections cannot be null.");
        if (string.IsNullOrWhiteSpace(profile.DisplayName) || string.IsNullOrWhiteSpace(profile.Personality) ||
            !Regex.IsMatch(profile.Personality, @"\A[a-zA-Z0-9_ .-]+\z"))
            throw new InvalidDataException("Invalid bot personality name.");
        if (profile.Map != "de_mirage") throw new InvalidDataException("Only de_mirage is supported.");
        if (profile.QuirkControls is null || profile.QuirkControls.Values.Any(c => c is null || !double.IsFinite(c.Value)))
            throw new InvalidDataException("Invalid quirk control.");
        if (Quirks.JumpsPerMinute(profile) is < 0 or > Quirks.MaxJumpsPerMinute)
            throw new InvalidDataException("jumps_per_min must be between 0 and 60.");
        foreach (var (side, plans) in profile.BuyPlan)
        {
            CheckSide(side);
            if (plans is null) throw new InvalidDataException("Purchase plans cannot be null.");
            foreach (var (kind, plan) in plans)
            {
                if (kind is not ("pistol" or "eco" or "force" or "full"))
                    throw new InvalidDataException($"Unknown buy type: {kind}.");
                if (plan is null || plan.Aliases is null || plan.Aliases.Any(a => a is null || !Regex.IsMatch(a, @"\A[a-z0-9_]+\z")))
                    throw new InvalidDataException("Invalid purchase alias.");
            }
        }
        foreach (var (side, routes) in profile.Routes)
        {
            CheckSide(side);
            if (routes is null) throw new InvalidDataException("Routes cannot be null.");
            foreach (var route in routes)
            {
                if (route is null || string.IsNullOrWhiteSpace(route.Key) || route.Start is null || route.Start.Length != 3 || route.Start.Any(v => !float.IsFinite(v)) ||
                    !double.IsFinite(route.Share) || route.Share < 0 || route.Source is not ("recorded" or "generated") ||
                    route.BuyType is not (null or "pistol" or "eco" or "force" or "full"))
                    throw new InvalidDataException("Invalid route metadata.");
                if (route.File is null || !route.File.EndsWith(".json.br", StringComparison.Ordinal))
                    throw new InvalidDataException("Route files must end in .json.br.");
                Resolve(route.File);
            }
        }
        foreach (var (side, shares) in profile.RouteShares)
        {
            CheckSide(side);
            if (shares is null || shares.Values.Any(v => !double.IsFinite(v) || v < 0))
                throw new InvalidDataException("Invalid route share.");
        }
    }

    private static void CheckSide(string side)
    {
        if (side is not ("T" or "CT")) throw new InvalidDataException("Side must be T or CT.");
    }
}

public static class Choices
{
    // Money is available before buying; equipment value is not. Tune these on the game machine.
    public static string BuyType(int money, bool pistolRound) => pistolRound ? "pistol" : money < 2000 ? "eco" : money < 4000 ? "force" : "full";

    public static Route? Pick(CloneProfile profile, string side, string buyType, string source, float[] spawn, double draw)
    {
        if (source == "off" || !profile.Routes.TryGetValue(side, out var routes)) return null;
        var groups = routes.Where(r => r.Source == source && (r.BuyType is null || r.BuyType == buyType))
            .GroupBy(r => r.Key).Select(g => new
            {
                Routes = g.ToArray(),
                Weight = profile.RouteShares.TryGetValue(side, out var shares) && shares.TryGetValue(g.Key, out var share)
                    ? share : g.First().Share
            }).Where(g => g.Weight > 0).ToArray();
        if (groups.Length == 0) return null;
        var total = groups.Sum(g => g.Weight);
        if (!double.IsFinite(total)) throw new InvalidDataException("Route shares overflow.");
        var target = Math.Clamp(draw, 0, Math.BitDecrement(1d)) * total;
        var chosen = groups[^1];
        foreach (var group in groups)
        {
            target -= group.Weight;
            if (target < 0) { chosen = group; break; }
        }
        return chosen.Routes.MinBy(r => Enumerable.Range(0, 3).Sum(i => Math.Pow(r.Start[i] - spawn[i], 2)));
    }
}
