// Replay puzzles (SPEC.md, replay puzzles). Written from zero; CS2PracticeMod (MIT, CounterStrikeSharp)
// is the reference for restoring a player's position, angles and weapons, which PuzzleMode.cs does.
// Pure logic here, with no game types, so it can be tested without CS2.
using System.Text.Json;
using System.Text.Json.Serialization;

namespace CloneDirector.Core;

// The puzzle file format. The same JSON is read by match-service (puzzles.py), so names must match.
public sealed class PuzzleSample
{
    [JsonPropertyName("t")] public double T { get; set; }
    [JsonPropertyName("x")] public double X { get; set; }
    [JsonPropertyName("y")] public double Y { get; set; }
    [JsonPropertyName("z")] public double Z { get; set; }
    [JsonPropertyName("yaw")] public double Yaw { get; set; }
    [JsonPropertyName("pitch")] public double Pitch { get; set; }
    [JsonPropertyName("hp")] public int Hp { get; set; } = 100;
    [JsonPropertyName("weapon")] public string Weapon { get; set; } = "";
    [JsonPropertyName("fire")] public bool Fire { get; set; }
}

public sealed class PuzzleStart
{
    [JsonPropertyName("health")] public int Health { get; set; } = 100;
    [JsonPropertyName("armor")] public int Armor { get; set; }
    [JsonPropertyName("helmet")] public bool Helmet { get; set; }
    [JsonPropertyName("money")] public int Money { get; set; }
    [JsonPropertyName("weapons")] public List<string> Weapons { get; set; } = [];
}

public sealed class PuzzlePlayerData
{
    [JsonPropertyName("slot")] public int Slot { get; set; }
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("side")] public string Side { get; set; } = "CT";
    [JsonPropertyName("hero")] public bool Hero { get; set; }
    [JsonPropertyName("start")] public PuzzleStart Start { get; set; } = new();
    [JsonPropertyName("track")] public List<PuzzleSample> Track { get; set; } = [];
}

public sealed class PuzzleEventData
{
    [JsonPropertyName("t")] public double T { get; set; }
    [JsonPropertyName("type")] public string Type { get; set; } = "kill";
    [JsonPropertyName("attacker")] public string? Attacker { get; set; }
    [JsonPropertyName("victim")] public string? Victim { get; set; }
    [JsonPropertyName("weapon")] public string? Weapon { get; set; }
}

public sealed class PuzzleOriginal
{
    [JsonPropertyName("kills")] public int Kills { get; set; }
    [JsonPropertyName("died")] public bool Died { get; set; }
    [JsonPropertyName("killer")] public string? Killer { get; set; }
    [JsonPropertyName("weapon")] public string? Weapon { get; set; }
}

public sealed class PuzzleData
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("title")] public string Title { get; set; } = "";
    [JsonPropertyName("map")] public string Map { get; set; } = "de_mirage";
    [JsonPropertyName("source")] public string Source { get; set; } = "user";
    [JsonPropertyName("source_info")] public Dictionary<string, JsonElement> SourceInfo { get; set; } = [];
    [JsonPropertyName("created")] public string Created { get; set; } = "";
    [JsonPropertyName("window_seconds")] public double WindowSeconds { get; set; } = 10;
    [JsonPropertyName("players")] public List<PuzzlePlayerData> Players { get; set; } = [];
    [JsonPropertyName("events")] public List<PuzzleEventData> Events { get; set; } = [];
    [JsonPropertyName("original")] public PuzzleOriginal Original { get; set; } = new();
    [JsonPropertyName("tags")] public List<string> Tags { get; set; } = [];
    [JsonPropertyName("rating")] public double Rating { get; set; } = 1500;
    [JsonPropertyName("notes")] public string Notes { get; set; } = "";

    public static readonly JsonSerializerOptions Json = new() { WriteIndented = false, PropertyNameCaseInsensitive = true };

    public static PuzzleData Parse(string json)
    {
        var data = JsonSerializer.Deserialize<PuzzleData>(json, Json) ?? throw new InvalidDataException("Puzzle is empty.");
        if (data.Players.Count(p => p.Hero) != 1) throw new InvalidDataException("A puzzle needs exactly one hero.");
        if (data.Players.Any(p => p.Track.Count == 0)) throw new InvalidDataException("Every player needs a track.");
        if (data.Players.Any(p => p.Side is not ("CT" or "T"))) throw new InvalidDataException("Side must be CT or T.");
        return data;
    }

    public PuzzlePlayerData Hero => Players.Single(p => p.Hero);
}

public static class PuzzleRules
{
    /// More kills than the original clip, and at least one.
    public static int NeededKills(int originalKills) => Math.Max(1, originalKills + 1);
    public static bool Solved(bool survived, int kills, int originalKills) => survived && kills >= NeededKills(originalKills);
}

public static class PuzzleMath
{
    /// Where a track is at time t: linear position, shortest-way yaw, and the velocity (units per second)
    /// along the segment, so a teleported bot still plays its walking animation.
    public static (double X, double Y, double Z, double Yaw, double Pitch, double Vx, double Vy, double Vz, PuzzleSample Last) At(
        IReadOnlyList<PuzzleSample> track, double t)
    {
        if (track.Count == 1 || t <= track[0].T) { var s = track[0]; return (s.X, s.Y, s.Z, s.Yaw, s.Pitch, 0, 0, 0, s); }
        for (int i = 1; i < track.Count; i++)
        {
            if (track[i].T < t) continue;
            var a = track[i - 1]; var b = track[i];
            double span = b.T - a.T;
            double f = span > 0 ? (t - a.T) / span : 0;
            double dyaw = ((b.Yaw - a.Yaw + 540) % 360) - 180;   // shortest way round
            return (a.X + (b.X - a.X) * f, a.Y + (b.Y - a.Y) * f, a.Z + (b.Z - a.Z) * f,
                    a.Yaw + dyaw * f, a.Pitch + (b.Pitch - a.Pitch) * f,
                    span > 0 ? (b.X - a.X) / span : 0, span > 0 ? (b.Y - a.Y) / span : 0, span > 0 ? (b.Z - a.Z) / span : 0, a);
        }
        var e = track[^1];
        return (e.X, e.Y, e.Z, e.Yaw, e.Pitch, 0, 0, 0, e);
    }
}

/// Keeps the last KeepSeconds of every player's movement and the kills and throws, and cuts a puzzle from
/// them when a human dies. Time is the game's server time in seconds.
public sealed class PuzzleRecorder
{
    public const double SampleSeconds = 0.25;
    public const double KeepSeconds = 15;
    public const double MinWindowSeconds = 2;

    private sealed class Ring
    {
        public string Name = "";
        public string Side = "CT";
        public readonly List<(double Time, PuzzleSample Sample, PuzzleStart Loadout)> Frames = [];
    }

    private readonly Dictionary<int, Ring> _rings = [];
    private readonly List<(double Time, PuzzleEventData Event)> _events = [];
    private readonly HashSet<int> _fired = [];
    private double _lastSample = double.NegativeInfinity;

    public bool Due(double now) => now - _lastSample >= SampleSeconds || now < _lastSample;
    public void Clear() { _rings.Clear(); _events.Clear(); _fired.Clear(); _lastSample = double.NegativeInfinity; }

    /// Mark that this slot fired since the last sample.
    public void MarkFire(int slot) => _fired.Add(slot);

    public void Sample(double now, int slot, string name, string side, double x, double y, double z, double yaw, double pitch,
                       int hp, string weapon, PuzzleStart loadout)
    {
        _lastSample = now;
        if (!_rings.TryGetValue(slot, out var ring)) _rings[slot] = ring = new();
        ring.Name = name; ring.Side = side;
        ring.Frames.Add((now, new PuzzleSample { X = x, Y = y, Z = z, Yaw = yaw, Pitch = pitch, Hp = hp, Weapon = weapon,
                                                 Fire = _fired.Remove(slot) }, loadout));
        ring.Frames.RemoveAll(f => f.Time < now - KeepSeconds);
        _events.RemoveAll(e => e.Time < now - KeepSeconds);
    }

    public void AddEvent(double now, string type, string? attacker, string? victim, string? weapon) =>
        _events.Add((now, new PuzzleEventData { Type = type, Attacker = attacker, Victim = victim, Weapon = weapon }));

    /// Preserve the death even though dead players are no longer sampled.
    public void MarkDeath(double now, int slot)
    {
        if (!_rings.TryGetValue(slot, out var ring) || ring.Frames.Count == 0) return;
        var last = ring.Frames[^1];
        var sample = last.Sample;
        ring.Frames.Add((now, new PuzzleSample { X = sample.X, Y = sample.Y, Z = sample.Z,
            Yaw = sample.Yaw, Pitch = sample.Pitch, Hp = 0, Weapon = sample.Weapon }, last.Loadout));
    }

    /// Cut the window ending at `now` for the player in `heroSlot`. Null when the hero has too little history.
    public PuzzleData? Build(double now, int heroSlot, string id, string title, string map, string created, double window,
                             double heroX, double heroY, double heroZ, double heroYaw, double heroPitch)
    {
        if (!_rings.TryGetValue(heroSlot, out var heroRing) || heroRing.Frames.Count == 0) return null;
        double start = Math.Max(now - window, heroRing.Frames[0].Time);
        if (now - start < MinWindowSeconds) return null;

        var killEvent = _events.LastOrDefault(e => e.Time <= now + 1e-6 && e.Event.Type == "kill" && e.Event.Victim == heroRing.Name);
        var players = new List<PuzzlePlayerData>();
        var used = new HashSet<string>();
        foreach (var (slot, ring) in _rings.OrderBy(r => r.Value.Name, StringComparer.Ordinal))
        {
            var frames = ring.Frames.Where(f => f.Time >= start && f.Time <= now + 1e-6).ToList();
            if (frames.Count == 0) continue;
            string name = ring.Name;
            for (int n = 2; !used.Add(name); n++) name = $"{ring.Name}#{n}";
            var track = frames.Select(f => new PuzzleSample
            {
                T = Math.Round(f.Time - start, 2), X = Math.Round(f.Sample.X, 1), Y = Math.Round(f.Sample.Y, 1),
                Z = Math.Round(f.Sample.Z, 1), Yaw = Math.Round(f.Sample.Yaw, 1), Pitch = Math.Round(f.Sample.Pitch, 1),
                Hp = f.Sample.Hp, Weapon = f.Sample.Weapon, Fire = f.Sample.Fire
            }).ToList();
            if (slot == heroSlot)   // the death itself: the last sample, health zero, at the position of death
                track.Add(new PuzzleSample { T = Math.Round(now - start, 2), X = Math.Round(heroX, 1), Y = Math.Round(heroY, 1),
                    Z = Math.Round(heroZ, 1), Yaw = Math.Round(heroYaw, 1), Pitch = Math.Round(heroPitch, 1), Hp = 0,
                    Weapon = frames[^1].Sample.Weapon });
            players.Add(new PuzzlePlayerData
            {
                Slot = players.Count + 1, Name = name, Side = ring.Side, Hero = slot == heroSlot,
                Start = frames[0].Loadout, Track = track
            });
        }
        var events = _events.Where(e => e.Time >= start && e.Time <= now + 1e-6)
            .Select(e => new PuzzleEventData { T = Math.Round(e.Time - start, 2), Type = e.Event.Type,
                Attacker = e.Event.Attacker, Victim = e.Event.Victim, Weapon = e.Event.Weapon }).ToList();
        int kills = events.Count(e => e.Type == "kill" && e.Attacker == heroRing.Name && e.Victim != heroRing.Name);
        return new PuzzleData
        {
            Id = id, Title = title, Map = map, Source = "user", Created = created, WindowSeconds = Math.Round(now - start, 1),
            Players = players, Events = events,
            Original = new PuzzleOriginal { Kills = kills, Died = true, Killer = killEvent.Event?.Attacker, Weapon = killEvent.Event?.Weapon },
            Tags = [map.Replace("de_", "")]
        };
    }
}

/// Drives the recorded players during a puzzle: which bots still follow their track, and the result.
public sealed class PuzzleRun(PuzzleData data)
{
    public PuzzleData Data { get; } = data;
    public int Kills { get; private set; }
    public bool Finished { get; private set; }
    public bool Survived { get; private set; }
    public readonly HashSet<string> HandedOff = [];

    /// This recorded player stops following the track and plays as a normal bot from now on.
    public void HandOff(string name) => HandedOff.Add(name);

    /// A kill by the hero (not of the hero). Ignored after the run ends.
    public void HeroGotKill() { if (!Finished) Kills++; }

    public void Finish(bool survived) { if (Finished) return; Finished = true; Survived = survived; }

    public bool Solved => Finished && PuzzleRules.Solved(Survived, Kills, Data.Original.Kills);
}
