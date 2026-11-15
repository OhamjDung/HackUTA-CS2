// Lifecycle and capability pattern adapted from CS2-Smarter-Bot and BotController TECH.md.
// AGPL-3.0-only; see THIRD_PARTY.md.
using System.Collections.Concurrent;
using System.Text.Json;
using BotControllerApi;
using CloneDirector.Core;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Core.Capabilities;
using CounterStrikeSharp.API.Modules.Commands;

namespace CloneDirector;

public sealed partial class CloneDirectorPlugin : BasePlugin
{
    public override string ModuleName => "CloneDirector";
    public override string ModuleVersion => "0.1.0";
    public override string ModuleAuthor => "Arjun";
    public override string ModuleDescription => "Apply recorded player purchases and routes to private-match bots.";

    private static readonly PluginCapability<IBotControllerApi> Capability = new("botcontroller:api");
    private IBotControllerApi? _api;
    private ProfileStore _profiles = null!;
    private readonly Dictionary<int, Binding> _bots = [];
    private readonly ConcurrentQueue<Action> _completed = new();
    private readonly Queue<PreparedClone> _waiting = new();
    private PendingAdd? _pending;
    private int _generation;
    private string _routeSource = "recorded";
    private bool _live;

    private sealed record PreparedClone(CloneProfile Profile, int Team, Dictionary<string, MotionRecording> Recordings);
    private sealed record PendingAdd(PreparedClone Prepared, HashSet<nint> Existing, float Deadline);
    private sealed class Binding(CCSPlayerController player, BotSession session, Dictionary<string, MotionRecording> recordings)
    {
        public CCSPlayerController Player { get; } = player;
        public BotSession Session { get; } = session;
        public Dictionary<string, MotionRecording> Recordings { get; } = recordings;
        public nint Pawn { get; set; }
        // Server time before which the jump quirk stays off (the bot is in or near a fight).
        public float QuietUntil { get; set; }
        // Burst quirk: shots in the current burst, its drawn limit (0 = none), and the last shot time.
        public int ShotsInBurst { get; set; }
        public int BurstLimit { get; set; }
        public float LastShot { get; set; } = float.NegativeInfinity;
        // Restless quirk: how long the bot has been alive and still this match, and since when.
        public long AliveTicks { get; set; }
        public long StillTicks { get; set; }
        public float StillSince { get; set; } = float.NaN;
        public bool NudgeLeft { get; set; }
        // Game sense (GameSenseMode.cs): where an enemy was last heard (blurred) and when; a hand-off waiting
        // for a pulled grenade; the next quiet-walk decision; route keys of recent rounds.
        public float[]? HeardAt { get; set; }
        public float HeardTime { get; set; } = float.NegativeInfinity;
        public string? PendingStop { get; set; }
        public float PendingStopUntil { get; set; }
        public float NextWalkDecision { get; set; }
        public Queue<string> RecentRoutes { get; } = new();
    }

    public override void Load(bool hotReload)
    {
        _profiles = new(Environment.GetEnvironmentVariable("CLONE_DIRECTOR_CLONES_DIR") ?? Path.Combine(ModuleDirectory, "clones"));
        AddCommand("clone_add", "clone_add <clone_id> <t|ct>", AddClone);
        AddCommand("clone_list", "List clone slots, routes, and hand-off reasons", ListClones);
        AddCommand("clone_routes", "clone_routes <recorded|generated|off>", SetRoutes);
        RegisterEventHandler<EventRoundStart>(RoundStart);
        RegisterEventHandler<EventRoundFreezeEnd>(FreezeEnd);
        RegisterEventHandler<EventRoundEnd>(RoundEnd);
        RegisterEventHandler<EventPlayerSpawn>(Spawn);
        RegisterEventHandler<EventPlayerHurt>(Hurt);
        RegisterEventHandler<EventPlayerDeath>(Death);
        RegisterEventHandler<EventWeaponFire>(WeaponFire);
        RegisterListener<Listeners.OnClientDisconnect>(Disconnect);
        RegisterListener<Listeners.OnMapEnd>(Reset);
        RegisterListener<Listeners.OnMapStart>(_ => Reset());
        RegisterListener<Listeners.OnTick>(Tick);
        PuzzleLoad();   // replay puzzles: PuzzleMode.cs
        GameSenseLoad();   // v2 game sense: GameSenseMode.cs
    }

    public override void OnAllPluginsLoaded(bool hotReload)
    {
        try { _api = Capability.Get(); }
        catch (KeyNotFoundException) { _api = null; }
        if (_api is null || _api.ApiVersion != 1)
        {
            _api = null;
            Log("BotController API version 1 is unavailable; clone_add is disabled.");
        }
    }

    public override void Unload(bool hotReload) { Reset(); _api = null; }

    private static bool ConsoleOnly(CCSPlayerController? player, CommandInfo command)
    {
        if (player is null) return true;
        // On a listen server (Bot Mode: the game hosts the match) there is no separate server console.
        // Commands a plugin runs with Server.ExecuteCommand, such as MatchBridge's, arrive attributed to
        // the host player in slot 0. Seen on Tom's PC: without this, clone_add from MatchBridge was refused.
        if (player.Slot == 0 && !player.IsBot) return true;
        command.ReplyToCommand("[CloneDirector] Use the server console.");
        return false;
    }

    private void AddClone(CCSPlayerController? player, CommandInfo command)
    {
        if (!ConsoleOnly(player, command)) return;
        if (_api is null) { command.ReplyToCommand("BotController API is unavailable."); return; }
        if (Server.MapName != "de_mirage") { command.ReplyToCommand("Only de_mirage is supported."); return; }
        if (command.ArgCount != 3 || command.GetArg(2).ToLowerInvariant() is not ("t" or "ct"))
        { command.ReplyToCommand("Usage: clone_add <clone_id> <t|ct>"); return; }
        string id = command.GetArg(1);
        int team = command.GetArg(2).Equals("t", StringComparison.OrdinalIgnoreCase) ? 2 : 3;
        int generation = _generation;
        var store = _profiles;
        // File parsing never calls game/native APIs. Completion runs on the game thread.
        _ = Task.Run(() =>
        {
            try
            {
                var profile = store.Load(id);
                var recordings = profile.Routes.Values.SelectMany(r => r).Select(r => r.File).Distinct()
                    .ToDictionary(f => f, f => MotionStore.LoadFromFile(store.Resolve(f)));
                _completed.Enqueue(() =>
                {
                    if (generation != _generation) return;
                    _waiting.Enqueue(new(profile, team, recordings));
                });
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException or InvalidOperationException)
            {
                _completed.Enqueue(() => { if (generation == _generation) Log($"Cannot load {id}: {ex.Message}"); });
            }
        });
        command.ReplyToCommand($"[CloneDirector] Loading {id}; clone_list reports attached bots. Watch the console for failures.");
    }

    private void ListClones(CCSPlayerController? player, CommandInfo command)
    {
        if (!ConsoleOnly(player, command)) return;
        command.ReplyToCommand($"[CloneDirector] source={_routeSource}; bots={_bots.Count}; queued={_waiting.Count}; adding={_pending is not null}");
        foreach (var binding in _bots.Values)
        {
            var s = binding.Session;
            command.ReplyToCommand($"slot={s.Slot} clone={s.Profile.Id} side={Side(binding.Player.TeamNum)} route={s.LastRoute?.Label ?? "none"} source={s.LastRoute?.Source ?? "none"} reason={s.Reason}");
        }
    }

    private void SetRoutes(CCSPlayerController? player, CommandInfo command)
    {
        if (!ConsoleOnly(player, command)) return;
        if (command.ArgCount != 2 || command.GetArg(1) is not ("recorded" or "generated" or "off"))
        { command.ReplyToCommand("Usage: clone_routes <recorded|generated|off>"); return; }
        _routeSource = command.GetArg(1);
        foreach (var b in _bots.Values) b.Session.Stop("route mode changed");
        command.ReplyToCommand($"[CloneDirector] Routes: {_routeSource}. Playback begins next round.");
    }

    private void Tick()
    {
        while (_completed.TryDequeue(out var completion)) completion();
        PuzzleTick();
        if (_api is null) return;
        if (_pending is { } pending)
        {
            // Add requests are serialized. Never attach a pre-existing bot or a different named bot.
            var player = Utilities.GetPlayers().FirstOrDefault(p => p.IsValid && p.IsBot &&
                p.TeamNum == pending.Prepared.Team && !pending.Existing.Contains(p.Handle) &&
                !_bots.ContainsKey(p.Slot) && p.PlayerName == pending.Prepared.Profile.Personality);
            if (player is not null)
            {
                var session = new BotSession(player.Slot, pending.Prepared.Profile, new Driver(_api), Log);
                var binding = new Binding(player, session, pending.Prepared.Recordings);
                _bots.Add(player.Slot, binding);
                _pending = null;
                ApplyBuy(binding);
                Log($"Attached {session.Profile.Id} to slot {player.Slot}, personality={session.Profile.Personality}. Routes start next round.");
            }
            else if (Server.CurrentTime >= pending.Deadline)
            {
                Log($"clone_add {pending.Prepared.Profile.Id} timed out. Check team capacity and the installed personality '{pending.Prepared.Profile.Personality}'. No bot was attached.");
                _pending = null;
            }
        }
        if (_pending is null && _waiting.TryDequeue(out var next))
        {
            _pending = new(next, Utilities.GetPlayers().Select(p => p.Handle).ToHashSet(), Server.CurrentTime + 5);
            Server.ExecuteCommand($"bot_add_{(next.Team == 2 ? "t" : "ct")} \"{next.Profile.Personality}\"");
        }
        _tickCount++;
        foreach (var binding in _bots.Values.ToArray())
        {
            if (!binding.Player.IsValid || !binding.Player.IsBot) { Disconnect(binding.Session.Slot); continue; }
            var pawn = binding.Player.PlayerPawn.Value;
            if (binding.Session.Playing && (pawn is null || !pawn.IsValid || pawn.Handle != binding.Pawn || !binding.Player.PawnIsAlive))
                binding.Session.Stop("pawn changed or dead");
            // v2 clones turn this off: it ignores walls; sight_handoff uses the game's own visibility instead.
            if (binding.Session.Profile.GameSense.EnemyCloseHandoff && binding.Session.Playing &&
                pawn is not null && pawn.IsValid && EnemyClose(binding, pawn))
                HandOff(binding, "enemy close");
            GameSenseTick(binding, pawn);
            binding.Session.Poll();
            ApplyJumpQuirk(binding, pawn);
            ApplyRestlessQuirk(binding, pawn);
        }
    }

    // True when any living enemy is within Combat.EnemyContactRadius of the bot.
    private static bool EnemyClose(Binding b, CCSPlayerPawn pawn)
    {
        var me = pawn.AbsOrigin;
        if (me is null) return false;
        foreach (var other in Utilities.GetPlayers())
        {
            if (!other.IsValid || !other.PawnIsAlive || other.TeamNum is not (2 or 3) || other.TeamNum == b.Player.TeamNum) continue;
            var pos = other.PlayerPawn.Value?.AbsOrigin;
            if (pos is not null && Combat.EnemyClose(me.X, me.Y, me.Z, pos.X, pos.Y, pos.Z)) return true;
        }
        return false;
    }

    // Learned quirk: a player who rarely stands still. When the bot has stood still for a larger
    // share of its life than the player does, and for 2 seconds in a row, it takes a short sidestep.
    // Off during a recorded route and for 5 seconds after any fight.
    private void ApplyRestlessQuirk(Binding b, CCSPlayerPawn? pawn)
    {
        if (!_live || pawn is null || !pawn.IsValid || !b.Player.PawnIsAlive) { b.StillSince = float.NaN; return; }
        var v = pawn.AbsVelocity;
        if (v is null) return;
        bool still = v.X * v.X + v.Y * v.Y < Quirks.StillSpeed * Quirks.StillSpeed;
        b.AliveTicks++;
        if (!still) { b.StillSince = float.NaN; return; }
        b.StillTicks++;
        if (float.IsNaN(b.StillSince)) b.StillSince = Server.CurrentTime;
        if (b.Session.Playing || Server.CurrentTime < b.QuietUntil) return;
        if (!Quirks.NudgeNow(Quirks.Value(b.Session.Profile, "still_share"), b.StillTicks, b.AliveTicks,
                Server.CurrentTime - b.StillSince)) return;
        _api!.InjectUsercmd(b.Session.Slot, b.NudgeLeft ? Quirks.MoveLeft : Quirks.MoveRight, 350);
        b.NudgeLeft = !b.NudgeLeft;
        b.StillSince = float.NaN;
    }

    // Learned quirks at the trigger: burst length and crouching while shooting.
    private void ApplyShotQuirks(Binding b)
    {
        var profile = b.Session.Profile;
        float now = Server.CurrentTime;
        if (now - b.LastShot > Quirks.BurstGapSeconds)
        {
            b.ShotsInBurst = 0;
            b.BurstLimit = Quirks.BurstLength(Quirks.Value(profile, "single_shot_burst_share"),
                Quirks.Value(profile, "shots_per_burst"), Random.Shared.NextDouble(), Random.Shared.NextDouble());
            if (Quirks.CrouchThisBurst(Quirks.Value(profile, "crouched_shot_share"), Random.Shared.NextDouble()))
                _api!.InjectUsercmd(b.Session.Slot, Quirks.Duck, 600);
        }
        b.LastShot = now;
        if (b.BurstLimit > 0 && ++b.ShotsInBurst >= b.BurstLimit)
            _api!.SuppressUsercmd(b.Session.Slot, Quirks.Attack, 300);   // release the trigger briefly
    }

    // Learned quirk: press jump at the player's measured rate, only while the bot runs outside a fight
    // and no recorded route is playing. IN_JUMP is engine button bit 2.
    private void ApplyJumpQuirk(Binding b, CCSPlayerPawn? pawn)
    {
        double rate = Quirks.JumpsPerMinute(b.Session.Profile);
        if (rate <= 0 || !_live || b.Session.Playing || pawn is null || !pawn.IsValid || !b.Player.PawnIsAlive) return;
        if (Server.CurrentTime < b.QuietUntil) return;
        var v = pawn.AbsVelocity;
        if (v is null || v.X * v.X + v.Y * v.Y < Quirks.MinRunSpeed * Quirks.MinRunSpeed) return;
        if (Quirks.JumpNow(rate, 1.0 / 64, Random.Shared.NextDouble()))
            _api!.InjectUsercmd(b.Session.Slot, Quirks.Jump, 0);
    }

    private HookResult RoundStart(EventRoundStart e, GameEventInfo info)
    {
        _live = false;
        if (_phase == PuzzlePhase.Idle) _recorder.Clear();   // a puzzle window never crosses a round
        foreach (var b in _bots.Values) ApplyBuy(b);
        return HookResult.Continue;
    }

    private void ApplyBuy(Binding b)
    {
        if (!b.Player.IsValid) return;
        var rules = Utilities.FindAllEntitiesByDesignerName<CCSGameRulesProxy>("cs_gamerules").FirstOrDefault()?.GameRules;
        // Competitive MR12 and wingman MR8, using configured half length; overtime has no pistol.
        int half = CounterStrikeSharp.API.Modules.Cvars.ConVar.Find("mp_maxrounds")?.GetPrimitiveValue<int>() / 2 ?? 12;
        int played = rules?.TotalRoundsPlayed ?? -1;
        b.Session.RoundStart(Side(b.Player.TeamNum), b.Player.InGameMoneyServices?.Account ?? 0,
            played == 0 || (half > 0 && played == half));
    }

    private HookResult Spawn(EventPlayerSpawn e, GameEventInfo info)
    {
        var player = e.Userid;
        if (player is not null && _bots.TryGetValue(player.Slot, out var b))
        {
            b.Session.Stop("spawn");
            if (!_live) ApplyBuy(b);
        }
        return HookResult.Continue;
    }

    private HookResult FreezeEnd(EventRoundFreezeEnd e, GameEventInfo info)
    {
        _live = true;
        PuzzleOnFreezeEnd();
        foreach (var b in _bots.Values)
        {
            var pawn = b.Player.PlayerPawn.Value;
            var pos = pawn?.AbsOrigin;
            if (!b.Player.IsValid || !b.Player.PawnIsAlive || pawn is null || pos is null) continue;
            var profile = b.Session.Profile;
            var route = profile.GameSense.RouteVariety
                ? GameSense.PickVaried(profile, Side(b.Player.TeamNum), b.Session.BuyType, _routeSource, [pos.X, pos.Y, pos.Z],
                    b.RecentRoutes, Random.Shared.NextDouble(), Random.Shared.NextDouble())
                : Choices.Pick(profile, Side(b.Player.TeamNum), b.Session.BuyType, _routeSource,
                    [pos.X, pos.Y, pos.Z], Random.Shared.NextDouble());
            if (route is null) { b.Session.Stop("no matching route"); continue; }
            b.RecentRoutes.Enqueue(route.Key);
            while (b.RecentRoutes.Count > Math.Max(0, profile.GameSense.RecentRoutes)) b.RecentRoutes.Dequeue();
            b.HeardAt = null;
            b.PendingStop = null;
            if (b.Session.Profile.Map != Server.MapName) { b.Session.Stop("map mismatch"); continue; }
            b.Pawn = pawn.Handle;
            b.Session.Begin(route, pawn.Handle, b.Recordings[route.File]);
        }
        return HookResult.Continue;
    }

    private HookResult Hurt(EventPlayerHurt e, GameEventInfo info)
    {
        PuzzleOnHurt(e);
        StopFor(e.Userid, "hurt");
        StopFor(e.Attacker, "dealt damage");
        return HookResult.Continue;
    }
    private HookResult Death(EventPlayerDeath e, GameEventInfo info)
    {
        PuzzleOnDeath(e);
        // Say how a clone died: weapon "world" with no attacker is a fall, "planted_c4" the bomb, "inferno" fire.
        // Logged before the route is stopped, so the reason shows whether it was still playing.
        if (e.Userid is { } victim && _bots.TryGetValue(victim.Slot, out var dead))
        {
            var at = victim.PlayerPawn.Value?.AbsOrigin;
            var killer = e.Attacker is { IsValid: true } a ? (a.Slot == victim.Slot ? "self" : a.PlayerName) : "none";
            Log($"DEATH {dead.Session.Profile.Id} slot={victim.Slot} by={killer} weapon={e.Weapon} " +
                $"route={(dead.Session.Playing ? "playing" : "stopped")} last_reason={dead.Session.Reason} " +
                $"pos=({at?.X:F0},{at?.Y:F0},{at?.Z:F0})");
        }
        StopFor(e.Userid, "death");
        return HookResult.Continue;
    }
    private void StopFor(CCSPlayerController? p, string reason)
    {
        if (p is not null && _bots.TryGetValue(p.Slot, out var b))
        {
            b.Session.Stop(reason);
            b.QuietUntil = Server.CurrentTime + Quirks.QuietSecondsAfterFight;
        }
    }

    private HookResult WeaponFire(EventWeaponFire e, GameEventInfo info)
    {
        PuzzleOnFire(e);
        var shooter = e.Userid;
        var shot = shooter?.PlayerPawn.Value?.AbsOrigin;
        if (shooter is null || !shooter.IsValid || shooter.TeamNum is not (2 or 3) || shot is null) return HookResult.Continue;
        if (_api is not null && _bots.TryGetValue(shooter.Slot, out var own) && own.Player.Handle == shooter.Handle &&
            !e.Weapon.Contains("knife") && !e.Weapon.Contains("grenade") && !e.Weapon.Contains("flashbang") &&
            !e.Weapon.Contains("molotov") && !e.Weapon.Contains("decoy") && !e.Weapon.Contains("bayonet"))
            ApplyShotQuirks(own);
        if (GameSense.IsGun(e.Weapon)) OnNoise(shooter, Noise.Gunfire);   // game sense (v2 clones): heard gunfire
        foreach (var b in _bots.Values)
        {
            if (!b.Player.IsValid || b.Player.TeamNum == shooter.TeamNum) continue;
            var pos = b.Player.PlayerPawn.Value?.AbsOrigin;
            if (pos is null || !Combat.Nearby(shot.X, shot.Y, shot.Z, pos.X, pos.Y, pos.Z)) continue;
            b.QuietUntil = Server.CurrentTime + Quirks.QuietSecondsAfterFight;
            HandOff(b, "enemy fired nearby");
        }
        return HookResult.Continue;
    }

    private HookResult RoundEnd(EventRoundEnd e, GameEventInfo info)
    {
        _live = false;
        foreach (var b in _bots.Values) b.Session.Stop("round ended");
        return HookResult.Continue;
    }
    private void Disconnect(int slot)
    {
        if (_bots.Remove(slot, out var binding)) binding.Session.Release("disconnect");
    }
    private void Reset()
    {
        EndPuzzleMode(restoreCvars: false);
        _recorder.Clear();
        ++_generation;
        _live = false;
        foreach (var b in _bots.Values) b.Session.Release("map change or unload");
        _bots.Clear();
        _waiting.Clear();
        _pending = null;
        _completed.Clear();
    }
    private static string Side(int team) => team == 2 ? "T" : team == 3 ? "CT" : "spectator";
    private static void Log(string message) => Server.PrintToConsole($"[CloneDirector] {message}");

    private sealed class Driver(IBotControllerApi api) : IBotDriver
    {
        public bool SetPawn(int slot, nint pawn) => api.SetReplayPawn(slot, pawn);
        public bool Load(int slot, MotionRecording r) => api.LoadReplay(slot, r.Ticks, r.Subticks, r.Commands, r.InputHistory);
        public bool Start(int slot) => api.StartReplay(slot);
        public bool Stop(int slot) => api.StopReplay(slot);
        public bool IsPlaying(int slot) => api.IsReplaying(slot);
        public bool Buy(int slot, string[] aliases) => aliases.Length == 0 ? api.SetBuySkip(slot) : api.SetBuyPlan(slot, string.Join(' ', aliases));
        public bool ClearBuy(int slot) => api.ClearBuyPlan(slot);
    }
}
