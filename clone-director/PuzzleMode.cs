// Replay puzzles in the game (SPEC.md, replay puzzles): save the last 10 seconds when a human dies, and
// play a saved moment back. Written from zero. The restore calls (RemoveWeapons, GiveNamedItem, Teleport)
// follow the pattern in CS2PracticeMod (MIT, CounterStrikeSharp).
//
// NOT YET RUN IN CS2 (compiled only). The first things to check in the game are in SPEC.md, replay puzzles.
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using CloneDirector.Core;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Modules.Commands;
using CounterStrikeSharp.API.Modules.Cvars;
using CounterStrikeSharp.API.Modules.Utils;

namespace CloneDirector;

public sealed partial class CloneDirectorPlugin
{
    private enum PuzzlePhase { Idle, FillingBots, WaitingRound, Running }

    private static readonly Regex PuzzleIdPattern = new("^[A-Za-z0-9_-]{1,64}$");
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(3) };
    // Cvars a puzzle changes; their values are put back by puzzle_stop.
    private static readonly string[] PuzzleCvars = ["mp_ignore_round_win_conditions", "mp_freezetime", "mp_limitteams", "mp_autoteambalance", "bot_quota", "bot_stop"];

    private readonly PuzzleRecorder _recorder = new();
    private readonly Dictionary<string, int> _savedCvars = [];
    private string? _savedQuotaMode;   // bot_quota_mode is a string cvar, so it is kept apart

    private static bool IsPuzzleHuman(CCSPlayerController p) => p.IsValid && !p.IsHLTV && !p.IsBot;
    private static bool IsPuzzleBot(CCSPlayerController p) => p.IsValid && !p.IsHLTV && p.IsBot;
    private readonly Dictionary<int, PuzzlePlayerData> _driven = [];   // game slot -> the recorded player it follows
    private string _puzzleDir = "", _deathDir = "", _serviceUrl = "";
    private PuzzlePhase _phase = PuzzlePhase.Idle;
    private PuzzleData? _puzzle;
    private PuzzleRun? _run;
    private CCSPlayerController? _hero;
    private bool _scene;
    private float _phaseDeadline, _runStart;

    private void PuzzleLoad()
    {
        _puzzleDir = Environment.GetEnvironmentVariable("CLONE_DIRECTOR_PUZZLE_DIR") ?? Path.Combine(ModuleDirectory, "puzzles");
        _deathDir = Environment.GetEnvironmentVariable("CLONE_DIRECTOR_DEATH_DIR") ?? Path.Combine(ModuleDirectory, "deaths");
        _serviceUrl = (Environment.GetEnvironmentVariable("CLONE_DIRECTOR_SERVICE_URL") ?? "http://127.0.0.1:8000").TrimEnd('/');
        AddCommand("puzzle_load", "puzzle_load <id>: replay a saved moment; you play the hero", PuzzleLoadCommand);
        AddCommand("scene_load", "scene_load <id>: watch all recorded players", SceneLoadCommand);
        AddCommand("puzzle_stop", "Leave puzzle mode and put the changed cvars back", PuzzleStopCommand);
        AddCommand("puzzle_status", "Say what puzzle mode is doing", PuzzleStatusCommand);
    }

    // ---- recording ---------------------------------------------------------------------------------

    private static string ItemName(string? designer) =>
        (designer ?? "").StartsWith("weapon_", StringComparison.Ordinal) ? designer![7..] : designer ?? "";

    private void PuzzleSampleAll()
    {
        double now = Server.CurrentTime;
        foreach (var p in AllPlayers())
        {
            if (!p.IsValid || p.IsHLTV || p.TeamNum is not (2 or 3) || !p.PawnIsAlive) continue;
            var pawn = p.PlayerPawn.Value;
            var pos = pawn?.AbsOrigin;
            if (pawn is null || !pawn.IsValid || pos is null) continue;
            var weapons = new List<string>();
            if (pawn.WeaponServices is { } ws)
                foreach (var handle in ws.MyWeapons)
                    if (handle.Value is { IsValid: true } w) weapons.Add(ItemName(w.DesignerName));
            var angles = pawn.EyeAngles;
            var loadout = new PuzzleStart { Health = pawn.Health, Armor = pawn.ArmorValue, Helmet = p.PawnHasHelmet,
                Money = p.InGameMoneyServices?.Account ?? 0, Weapons = weapons };
            _recorder.Sample(now, p.Slot, p.PlayerName, Side(p.TeamNum), pos.X, pos.Y, pos.Z, angles.Y, angles.X, pawn.Health,
                ItemName(pawn.WeaponServices?.ActiveWeapon.Value?.DesignerName), loadout);
        }
    }

    private void PuzzleOnDeath(EventPlayerDeath e)
    {
        var victim = e.Userid;
        if (victim is null || !victim.IsValid) return;
        double now = Server.CurrentTime;
        string? attackerName = e.Attacker is { IsValid: true } a && a.Slot != victim.Slot ? a.PlayerName : null;
        _recorder.AddEvent(now, "kill", attackerName, victim.PlayerName, ItemName(e.Weapon));
        _recorder.MarkDeath(now, victim.Slot);

        if (_run is { Finished: false } run && _hero is not null)
        {
            if (victim.Slot == _hero.Slot) FinishPuzzle(false);
            else if (e.Attacker is { IsValid: true } k && k.Slot == _hero.Slot && victim.TeamNum != _hero.TeamNum) run.HeroGotKill();
        }

        if (!IsPuzzleHuman(victim)) return;   // only a human's death is saved
        var at = victim.PlayerPawn.Value?.AbsOrigin;
        var ang = victim.PlayerPawn.Value?.EyeAngles;
        if (at is null || ang is null) return;
        long ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var puzzle = _recorder.Build(now, victim.Slot, $"death_{ms}", $"Death on {Server.MapName.Replace("de_", "")}", Server.MapName,
            DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:sszzz"), 10, at.X, at.Y, at.Z, ang.Y, ang.X);
        if (puzzle is null) { Log("Death not saved: less than 2 seconds of history."); return; }
        string json = JsonSerializer.Serialize(puzzle, PuzzleData.Json);
        string dir = _deathDir;
        _ = Task.Run(() =>
        {
            try
            {
                Directory.CreateDirectory(dir);
                string final = Path.Combine(dir, puzzle.Id + ".json"), tmp = final + ".tmp";
                File.WriteAllText(tmp, json);
                File.Move(tmp, final, true);   // the service only ever sees a whole file
                _completed.Enqueue(() => Log($"DEATH saved {puzzle.Id} ({puzzle.Players.Count} players, {puzzle.WindowSeconds}s, hero kills {puzzle.Original.Kills})"));
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                _completed.Enqueue(() => Log($"Could not save the death: {ex.Message}"));
            }
        });
    }

    private void PuzzleOnFire(EventWeaponFire e)
    {
        var shooter = e.Userid;
        if (shooter is null || !shooter.IsValid) return;
        _recorder.MarkFire(shooter.Slot);
        string weapon = ItemName(e.Weapon);
        if (weapon is "flashbang" or "smokegrenade" or "hegrenade" or "molotov" or "incgrenade" or "decoy")
            _recorder.AddEvent(Server.CurrentTime, "throw", shooter.PlayerName, null, weapon);
        // During a puzzle, a recorded player near the hero's shot stops following its track and fights.
        if (_phase == PuzzlePhase.Running && _hero is not null && shooter.Slot == _hero.Slot && _run is { Finished: false } run)
        {
            var shot = shooter.PlayerPawn.Value?.AbsOrigin;
            if (shot is null) return;
            foreach (var (slot, data) in _driven)
            {
                var other = Utilities.GetPlayerFromSlot(slot)?.PlayerPawn.Value?.AbsOrigin;
                if (other is not null && Combat.Nearby(shot.X, shot.Y, shot.Z, other.X, other.Y, other.Z)) run.HandOff(data.Name);
            }
        }
    }

    private void PuzzleOnHurt(EventPlayerHurt e)
    {
        if (_scene) return;
        if (_run is not { Finished: false } run) return;
        foreach (var c in new[] { e.Userid, e.Attacker })
            if (c is not null && _driven.TryGetValue(c.Slot, out var data)) run.HandOff(data.Name);
    }

    // ---- commands ----------------------------------------------------------------------------------

    private void PuzzleLoadCommand(CCSPlayerController? player, CommandInfo command)
        => LoadMoment(player, command, scene: false);

    private void SceneLoadCommand(CCSPlayerController? player, CommandInfo command)
        => LoadMoment(player, command, scene: true);

    private void LoadMoment(CCSPlayerController? player, CommandInfo command, bool scene)
    {
        if (!ConsoleOnly(player, command)) return;
        if (command.ArgCount != 2 || !PuzzleIdPattern.IsMatch(command.GetArg(1))) { command.ReplyToCommand("Usage: puzzle_load <id>"); return; }
        PuzzleData data;
        try { data = PuzzleData.Parse(File.ReadAllText(Path.Combine(_puzzleDir, command.GetArg(1) + ".json"))); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException or InvalidDataException)
        { command.ReplyToCommand($"[CloneDirector] Cannot load puzzle: {ex.Message}"); return; }
        if (data.Map != Server.MapName) { command.ReplyToCommand($"[CloneDirector] Puzzle is for {data.Map}; this is {Server.MapName}."); return; }
        var hero = AllPlayers().FirstOrDefault(IsPuzzleHuman);
        if (hero is null) { command.ReplyToCommand("[CloneDirector] No human player is in the game. Join the match first."); return; }
        StartPuzzle(data, hero, scene);
        command.ReplyToCommand($"[CloneDirector] Puzzle {data.Id}: preparing bots, then the round restarts. {PuzzleStatus()}");
    }

    private void PuzzleStopCommand(CCSPlayerController? player, CommandInfo command)
    {
        if (!ConsoleOnly(player, command)) return;
        EndPuzzleMode();
        command.ReplyToCommand("[CloneDirector] Puzzle mode off; cvars put back.");
    }

    private void PuzzleStatusCommand(CCSPlayerController? player, CommandInfo command)
    {
        if (!ConsoleOnly(player, command)) return;
        command.ReplyToCommand("[CloneDirector] " + PuzzleStatus());
        // Every player the plugin sees, to check bot detection in the game.
        command.ReplyToCommand("[CloneDirector] players: " + string.Join(", ", AllPlayers().Select(p =>
            $"{p.Slot}:{p.PlayerName} bot={p.IsBot} team={p.TeamNum}")));
    }

    private string PuzzleStatus() => _phase == PuzzlePhase.Idle
        ? $"puzzle mode off; recorder keeps the last {PuzzleRecorder.KeepSeconds:0} s"
        : $"puzzle={_puzzle?.Id} phase={_phase} driven={_driven.Count} handed_off={_run?.HandedOff.Count ?? 0} kills={_run?.Kills ?? 0} finished={_run?.Finished}";

    // ---- starting a puzzle -------------------------------------------------------------------------

    private void StartPuzzle(PuzzleData data, CCSPlayerController hero, bool scene = false)
    {
        EndPuzzleMode(restoreCvars: false);
        foreach (var b in _bots.Values) b.Session.Release("puzzle");   // clones must not fight the recorded players
        _bots.Clear(); _waiting.Clear(); _pending = null;
        foreach (var name in PuzzleCvars)
            if (!_savedCvars.ContainsKey(name) && CvarAsInt(name) is int value) _savedCvars[name] = value;
        _puzzle = data; _hero = hero; _scene = scene; _run = null; _driven.Clear(); _recorder.Clear();
        int others = data.Players.Count - (scene ? 0 : 1);
        // Bots come from the bot quota (random bots). They are moved to the sides the puzzle needs next.
        _savedQuotaMode ??= ConVar.Find("bot_quota_mode")?.StringValue;
        // "normal": bot_quota is the number of bots. In "fill" (the bot base's setting) it counts the human too.
        foreach (var cmd in new[] { "mp_ignore_round_win_conditions 1", "mp_freezetime 0", "mp_limitteams 0", "mp_autoteambalance 0", "bot_quota_mode normal", $"bot_quota {others}" })
            Server.ExecuteCommand(cmd);
        if (scene) Server.ExecuteCommand("bot_stop 1");
        hero.ChangeTeam(scene ? CsTeam.Spectator : data.Hero.Side == "T" ? CsTeam.Terrorist : CsTeam.CounterTerrorist);
        _phase = PuzzlePhase.FillingBots;
        _phaseDeadline = Server.CurrentTime + 25;
    }

    // Some of these cvars are Bool (mp_autoteambalance, mp_ignore_round_win_conditions), and
    // GetPrimitiveValue<int> throws on a Bool: that exception stopped every puzzle_load in CS2.
    private static int? CvarAsInt(string name)
    {
        var cvar = ConVar.Find(name);
        if (cvar is null) return null;
        return cvar.Type == ConVarType.Bool ? (cvar.GetPrimitiveValue<bool>() ? 1 : 0) : cvar.GetPrimitiveValue<int>();
    }

    private void EndPuzzleMode(bool restoreCvars = true)
    {
        _phase = PuzzlePhase.Idle; _run = null; _puzzle = null; _hero = null; _scene = false; _driven.Clear();
        if (!restoreCvars) return;
        if (_savedQuotaMode is { } mode && Regex.IsMatch(mode, "^[a-z]{1,16}$"))
            Server.ExecuteCommand($"bot_quota_mode {mode}");
        _savedQuotaMode = null;
        foreach (var (name, value) in _savedCvars) Server.ExecuteCommand($"{name} {value}");
        _savedCvars.Clear();
    }

    private void PuzzleTick()
    {
        double now = Server.CurrentTime;
        switch (_phase)
        {
            case PuzzlePhase.Idle:
                if (_recorder.Due(now)) PuzzleSampleAll();
                break;
            case PuzzlePhase.FillingBots: PrepareBots(); break;
            case PuzzlePhase.WaitingRound:
                if (now > _phaseDeadline) { Log("Puzzle: the round did not start in time; giving up. Run puzzle_load again."); EndPuzzleMode(); }
                break;
            case PuzzlePhase.Running:
                if (_recorder.Due(now)) PuzzleSampleAll();
                RunPuzzle();
                break;
        }
    }

    // Wait for exactly as many bots as the puzzle has other players, then move each to the side it needs.
    private void PrepareBots()
    {
        if (_puzzle is null) { _phase = PuzzlePhase.Idle; return; }
        var bots = AllPlayers().Where(IsPuzzleBot).ToList();
        int needed = _puzzle.Players.Count - (_scene ? 0 : 1);
        if (bots.Count != needed)
        {
            if (Server.CurrentTime > _phaseDeadline)
            {
                var seen = string.Join(", ", AllPlayers().Select(p =>
                    $"{p.Slot}:{p.PlayerName} bot={p.IsBot} team={p.TeamNum} state={p.Connected}"));
                Log($"Puzzle: found {bots.Count} bots, need {needed}. Giving up. Players: {seen}");
                EndPuzzleMode();
            }
            return;
        }
        // How many bots each side needs. A bot already on a side that still needs one stays; the rest move.
        var need = new Dictionary<string, int>
        {
            ["CT"] = _puzzle.Players.Count(p => (_scene || !p.Hero) && p.Side == "CT"),
            ["T"] = _puzzle.Players.Count(p => (_scene || !p.Hero) && p.Side == "T")
        };
        var movers = new List<CCSPlayerController>();
        foreach (var bot in bots)
        {
            string side = Side(bot.TeamNum);
            if (need.TryGetValue(side, out int left) && left > 0) need[side] = left - 1;
            else movers.Add(bot);
        }
        foreach (var bot in movers)
        {
            string side = need["CT"] > 0 ? "CT" : "T";
            need[side]--;
            bot.ChangeTeam(side == "T" ? CsTeam.Terrorist : CsTeam.CounterTerrorist);
        }
        Server.ExecuteCommand("mp_restartgame 1");
        _phase = PuzzlePhase.WaitingRound;
        _phaseDeadline = Server.CurrentTime + 20;
    }

    private void PuzzleOnFreezeEnd()
    {
        if (_phase != PuzzlePhase.WaitingRound || _puzzle is null || _hero is null) return;
        var data = _puzzle;
        // One frame later, so every player has spawned before weapons are taken and positions set.
        Server.NextFrame(() =>
        {
            if (_phase != PuzzlePhase.WaitingRound || _puzzle != data || _hero is not { IsValid: true } hero) return;
            var bots = AllPlayers().Where(p => IsPuzzleBot(p) && p.TeamNum is 2 or 3).OrderBy(p => p.Slot).ToList();
            _driven.Clear();
            foreach (var other in data.Players.Where(p => _scene || !p.Hero))
            {
                var bot = bots.FirstOrDefault(b => Side(b.TeamNum) == other.Side && !_driven.ContainsKey(b.Slot));
                if (bot is null) { Log($"Puzzle: no bot on {other.Side} for {other.Name}; skipped."); continue; }
                _driven[bot.Slot] = other;
                RestorePlayer(bot, other);
            }
            if (!_scene) RestorePlayer(hero, data.Hero);
            _run = new PuzzleRun(data);
            _runStart = Server.CurrentTime;
            _recorder.Clear();
            _phase = PuzzlePhase.Running;
            hero.PrintToChat(_scene ? $" [Scene] {data.Title}: spectating recorded movement." : $" [Puzzle] {data.Title}: survive {data.WindowSeconds:0} s and get {PuzzleRules.NeededKills(data.Original.Kills)} kill(s).");
            Log($"Puzzle {data.Id} running with {_driven.Count} recorded players.");
        });
    }

    // Put one player back as it was at the start of the window: weapons, armor, health, money, position, view.
    private static void RestorePlayer(CCSPlayerController c, PuzzlePlayerData data)
    {
        var pawn = c.PlayerPawn.Value;
        if (!c.IsValid || pawn is null || !pawn.IsValid) return;
        var s = data.Start;
        c.RemoveWeapons();
        foreach (var w in s.Weapons.Where(w => w is not ("c4" or "")).Distinct()) c.GiveNamedItem("weapon_" + w);
        if (s.Armor > 0) c.GiveNamedItem(s.Helmet ? "item_assaultsuit" : "item_kevlar");
        pawn.Health = Math.Max(1, s.Health);
        Utilities.SetStateChanged(pawn, "CBaseEntity", "m_iHealth");
        pawn.ArmorValue = s.Armor;
        Utilities.SetStateChanged(pawn, "CCSPlayerPawn", "m_ArmorValue");
        if (c.InGameMoneyServices is { } money)
        {
            money.Account = s.Money;
            Utilities.SetStateChanged(c, "CCSPlayerController_InGameMoneyServices", "m_iAccount");
        }
        var first = data.Track[0];
        pawn.Teleport(new Vector((float)first.X, (float)first.Y, (float)first.Z), new QAngle((float)first.Pitch, (float)first.Yaw, 0), new Vector(0, 0, 0));
    }

    // ---- playing the moment ------------------------------------------------------------------------

    private void RunPuzzle()
    {
        if (_run is not { Finished: false } run || _puzzle is null || _hero is null) return;
        double t = Server.CurrentTime - _runStart;
        var heroPos = _hero.IsValid ? _hero.PlayerPawn.Value?.AbsOrigin : null;
        foreach (var (slot, data) in _driven)
        {
            if (run.HandedOff.Contains(data.Name)) continue;
            var c = Utilities.GetPlayerFromSlot(slot);
            var pawn = c?.PlayerPawn.Value;
            if (c is null || !c.IsValid || !c.PawnIsAlive || pawn is null || !pawn.IsValid) continue;
            var at = PuzzleMath.At(data.Track, t);
            if (_scene && at.Last.Hp <= 0) { c.CommitSuicide(false, true); continue; }
            // A recorded player stops following its track when its recorded self died, when the hero is
            // close enough to fight (not a line-of-sight test), or after damage or a nearby shot (events above).
            var me = pawn.AbsOrigin;
            bool heroClose = heroPos is not null && me is not null && data.Side != _puzzle.Hero.Side &&
                Combat.EnemyClose(me.X, me.Y, me.Z, heroPos.X, heroPos.Y, heroPos.Z);
            if (!_scene && (at.Last.Hp <= 0 || heroClose)) { run.HandOff(data.Name); continue; }
            pawn.Teleport(new Vector((float)at.X, (float)at.Y, (float)at.Z), new QAngle((float)at.Pitch, (float)at.Yaw, 0),
                new Vector((float)at.Vx, (float)at.Vy, (float)at.Vz));
        }
        if (t >= _puzzle.WindowSeconds) FinishPuzzle(_scene || (_hero.IsValid && _hero.PawnIsAlive));
    }

    private void FinishPuzzle(bool survived)
    {
        if (_run is not { Finished: false } run || _puzzle is null) return;
        run.Finish(survived);
        var puzzle = _puzzle;
        int need = PuzzleRules.NeededKills(puzzle.Original.Kills);
        string text = _scene ? "Scene finished." : run.Solved ? $"Solved: {run.Kills} kill(s), alive."
            : survived ? $"Alive, but {run.Kills} of {need} kill(s)."
            : "You died.";
        if (_hero is { IsValid: true } hero) hero.PrintToChat($" [Puzzle] {text} Puzzle finished; normal settings restored.");
        Log($"Puzzle {puzzle.Id} finished: survived={survived} kills={run.Kills} need={need} solved={run.Solved}");
        string url = $"{_serviceUrl}/puzzles/{puzzle.Id}/result";
        string body = JsonSerializer.Serialize(new { survived, kills = run.Kills });
        EndPuzzleMode();
        _ = Task.Run(async () =>
        {
            try { using var content = new StringContent(body, Encoding.UTF8, "application/json"); (await Http.PostAsync(url, content)).EnsureSuccessStatusCode(); }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
            { _completed.Enqueue(() => Log($"Could not send the puzzle result to {url}: {ex.Message}")); }
        });
    }
}
