using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Nodes;
using BotControllerApi;
using CloneDirector.Core;
using Xunit;

namespace CloneDirector.Tests;

public sealed class DirectorTests
{
    private static readonly CloneProfile Profile = new()
    {
        Id = "test", DisplayName = "test",
        BuyPlan = new()
        {
            ["T"] = new() { ["eco"] = new() { Aliases = [] }, ["full"] = new() { Aliases = ["ak47", "vesthelm"] } },
            ["CT"] = new() { ["full"] = new() { Aliases = ["m4a1", "vesthelm"] } }
        },
        Routes = new()
        {
            ["T"] = [Route("mid", 100), Route("mid", 1), Route("a", 0), Route("generated", 0, "generated")],
            ["CT"] = [Route("b", 0)]
        },
        RouteShares = new() { ["T"] = new() { ["mid"] = .75, ["a"] = .25 } }
    };

    private static Route Route(string key, float x, string source = "recorded", string? buyType = null) => new()
        { Key = key, File = $"test/{key}_{x}.json.br", Start = [x, 0, 0], Source = source, BuyType = buyType };
    private static MotionRecording Recording() => new()
        { FormatVersion = 1, Tickrate = 64, Ticks = [new ReplayTick()], Subticks = [], Commands = [new ReplayCommandFrame()] };

    [Fact]
    public void RouteWeightBelongsToLabelThenNearestSpawnWins()
    {
        Assert.Equal(1, Choices.Pick(Profile, "T", "full", "recorded", [0, 0, 0], .74)!.Start[0]);
        Assert.Equal("a", Choices.Pick(Profile, "T", "full", "recorded", [0, 0, 0], .76)!.Key);
        Assert.Equal("b", Choices.Pick(Profile, "CT", "full", "recorded", [0, 0, 0], .5)!.Key);
        Assert.Equal("generated", Choices.Pick(Profile, "T", "full", "generated", [0, 0, 0], .5)!.Key);
        Assert.Null(Choices.Pick(Profile, "T", "full", "off", [0, 0, 0], .5));
    }

    [Fact]
    public void RouteSelectionDoesNotUseWrongEconomyOrZeroShare()
    {
        var p = new CloneProfile
        {
            Id = "p", DisplayName = "p", Routes = new() { ["T"] = [Route("a", 0, buyType: "pistol"), Route("b", 0, buyType: "full")] },
            RouteShares = new() { ["T"] = new() { ["a"] = 0, ["b"] = 1 } }
        };
        Assert.Null(Choices.Pick(p, "T", "pistol", "recorded", [0, 0, 0], 0));
        Assert.Null(Choices.Pick(p, "T", "eco", "recorded", [0, 0, 0], 0));
        Assert.Equal("b", Choices.Pick(p, "T", "full", "recorded", [0, 0, 0], .99)!.Key);
    }

    [Theory]
    [InlineData(800, true, "pistol")]
    [InlineData(800, false, "eco")]
    [InlineData(1999, false, "eco")]
    [InlineData(2000, false, "force")]
    [InlineData(3999, false, "force")]
    [InlineData(4000, false, "full")]
    public void PurchasesUseMoneyAndActualPistolRound(int money, bool pistol, string expected) =>
        Assert.Equal(expected, Choices.BuyType(money, pistol));

    [Fact]
    public void PlansClearAcrossSidesAndMissingTypesAndEmptyEcoMeansSkip()
    {
        var d = new FakeDriver();
        var s = new BotSession(2, Profile, d, _ => { });
        s.RoundStart("T", 5000, false);
        Assert.Equal("ak47 vesthelm", d.Plan);
        s.RoundStart("CT", 5000, false);
        Assert.Equal("m4a1 vesthelm", d.Plan);
        s.RoundStart("CT", 1500, false);
        Assert.Null(d.Plan);
        s.RoundStart("T", 1500, false);
        Assert.Equal("", d.Plan);
    }

    [Theory]
    [InlineData("hurt")]
    [InlineData("dealt damage")]
    [InlineData("enemy fired nearby")]
    [InlineData("death")]
    [InlineData("route mode changed")]
    [InlineData("round ended")]
    public void HandOffStopsPlaybackOnceAndRecordsReason(string reason)
    {
        var d = new FakeDriver();
        var log = new List<string>();
        var s = new BotSession(2, Profile, d, log.Add);
        s.Begin(Profile.Routes["T"][0], 42, Recording());
        Assert.True(s.Playing);
        Assert.Equal(new[] { "pawn", "load", "start" }, d.Calls);
        s.Stop(reason);
        s.Stop(reason);
        Assert.False(s.Playing);
        Assert.Equal(reason, s.Reason);
        s.Stop("round ended");
        Assert.Equal(reason, s.Reason);
        Assert.Equal(1, d.Calls.Count(c => c == "stop"));
        Assert.Contains(reason, Assert.Single(log));
    }

    [Fact]
    public void NaturalCompletionAndRejectedStartDoNotClaimPlaybackIsActive()
    {
        var d = new FakeDriver();
        var s = new BotSession(2, Profile, d, _ => { });
        s.Begin(Profile.Routes["T"][0], 42, Recording());
        d.Active = false;
        s.Poll();
        Assert.Equal("segment ended", s.Reason);
        Assert.False(s.Playing);
        d.AcceptStart = false;
        s.Begin(Profile.Routes["T"][0], 42, Recording());
        Assert.False(s.Playing);
        Assert.Equal("playback rejected", s.Reason);
        Assert.Equal("stop", d.Calls.Last());
        s.Release("disconnect");
        Assert.Null(d.Plan);
    }

    [Fact]
    public void FailedStopDoesNotStartAnotherRouteOrChangePurchases()
    {
        var d = new FakeDriver();
        var s = new BotSession(2, Profile, d, _ => { });
        s.Begin(Profile.Routes["T"][0], 42, Recording());
        d.AcceptStop = false;
        s.Stop("hurt");
        Assert.True(s.Playing);
        Assert.Equal("stop rejected (hurt)", s.Reason);
        s.Begin(Profile.Routes["T"][1], 42, Recording());
        Assert.Equal(1, d.Calls.Count(c => c == "load"));
        s.RoundStart("CT", 5000, false);
        Assert.Null(d.Plan);
        Assert.True(s.Playing);
    }

    [Fact]
    public void NearbyShotsUseThreeDimensionalDistance()
    {
        Assert.True(Combat.Nearby(0, 0, 0, 1200, 0, 0));
        Assert.False(Combat.Nearby(0, 0, 0, 1201, 0, 0));
        Assert.False(Combat.Nearby(0, 0, 0, 900, 900, 0));
        Assert.False(Combat.Nearby(0, 0, 0, 0, 0, 1201));
    }

    [Fact]
    public void PathsAndPersonalityNamesCannotEscapeOrInjectCommands()
    {
        var store = new ProfileStore(Path.GetTempPath());
        Assert.Throws<InvalidDataException>(() => store.Resolve("../outside.json.br"));
        Assert.Throws<InvalidDataException>(() => store.Resolve(Path.GetFullPath("outside.json.br")));
        Assert.Throws<InvalidDataException>(() => store.Load("../outside"));
        Assert.Throws<InvalidDataException>(() => store.Validate(new() { Id = "bad", DisplayName = "donk\";quit" }));
    }

    [Fact]
    public void RealPipelineProfileAndAllEightyRecordingsLoadInCSharp()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "SPEC.md"))) dir = dir.Parent;
        Assert.NotNull(dir);
        var store = new ProfileStore(Path.Combine(dir!.FullName, "clones"));
        var profile = store.Load("donk_v1");
        Assert.Equal("donk", profile.Personality);
        Assert.Contains("ak47", profile.BuyPlan["T"]["full"].Aliases);
        var routes = profile.Routes.Values.SelectMany(r => r).ToArray();
        Assert.Equal(80, routes.Length);
        foreach (var route in routes)
        {
            var recording = MotionStore.LoadFromFile(store.Resolve(route.File));
            Assert.Equal(recording.Ticks.Length, recording.Commands.Length);
            Assert.InRange(Math.Abs(route.Start[0] - recording.Ticks[0].Pre.OriginX), 0, .11);
        }
    }

    [Theory]
    [InlineData("missing frame field")]
    [InlineData("command count")]
    [InlineData("subtick count")]
    [InlineData("tickrate")]
    [InlineData("version")]
    public void CorruptRecordingsAreRejectedBeforeNativeCalls(string fault)
    {
        var json = JsonSerializer.SerializeToNode(Recording(), MotionStore.JsonOptions)!;
        switch (fault)
        {
            case "missing frame field": json["Ticks"]![0]!["Pre"]!.AsObject().Remove("Buttons1"); break;
            case "command count": json["Commands"] = new JsonArray(); break;
            case "subtick count": json["Ticks"]![0]!["NumSubtick"] = 1; break;
            case "tickrate": json["Tickrate"] = 128; break;
            case "version": json["FormatVersion"] = 2; break;
        }
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".json.br");
        try
        {
            using (var f = File.Create(path))
            using (var b = new BrotliStream(f, CompressionLevel.Fastest)) JsonSerializer.Serialize(b, json);
            if (fault == "missing frame field") Assert.Throws<JsonException>(() => MotionStore.LoadFromFile(path));
            else Assert.Throws<InvalidDataException>(() => MotionStore.LoadFromFile(path));
        }
        finally { File.Delete(path); }
    }

    private sealed class FakeDriver : IBotDriver
    {
        public readonly List<string> Calls = [];
        public string? Plan;
        public bool Active;
        public bool AcceptStart = true;
        public bool AcceptStop = true;
        public bool SetPawn(int slot, nint pawn) { Calls.Add("pawn"); return true; }
        public bool Load(int slot, MotionRecording recording) { Calls.Add("load"); return true; }
        public bool Start(int slot) { Calls.Add("start"); Active = AcceptStart; return AcceptStart; }
        public bool Stop(int slot) { Calls.Add("stop"); if (AcceptStop) Active = false; return AcceptStop; }
        public bool IsPlaying(int slot) => Active;
        public bool Buy(int slot, string[] aliases) { Plan = string.Join(' ', aliases); return true; }
        public bool ClearBuy(int slot) { Plan = null; return true; }
    }
}
