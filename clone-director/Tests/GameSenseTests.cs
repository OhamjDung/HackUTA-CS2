using System.Text.Json;
using CloneDirector.Core;
using Xunit;

namespace CloneDirector.Tests;

public sealed class GameSenseTests
{
    private static Route R(string key, float x) => new() { Key = key, File = $"t/{key}_{x}.json.br", Start = [x, 0, 0] };

    private static CloneProfile Profile(GameSenseSettings? s = null) => new()
    {
        Id = "v2", DisplayName = "v2",
        // Two mid routes from the same spawn spot (0 and 10), one from the neighbouring spot (100), one far away.
        Routes = new() { ["T"] = [R("mid", 0), R("mid", 10), R("mid", 100), R("mid", 5000), R("a", 0)] },
        RouteShares = new() { ["T"] = new() { ["mid"] = .5, ["a"] = .5 } },
        GameSense = s ?? new GameSenseSettings { RouteVariety = true },
    };

    private static string RepoClones()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, "clones"))) dir = dir.Parent;
        return Path.Combine(dir?.FullName ?? throw new DirectoryNotFoundException("clones folder"), "clones");
    }

    [Theory]
    [InlineData("donk_v2", true)]
    [InlineData("broky_v2", true)]
    [InlineData("donkLF", false)]
    [InlineData("brokyLF", false)]
    [InlineData("donk_v1", false)]
    public void RealProfilesLoadThroughTheLoader(string id, bool gameSense)
    {
        var store = new ProfileStore(RepoClones());
        var p = store.Load(id);
        Assert.Equal(id, p.Personality);
        Assert.Equal(gameSense, p.GameSense.HearHandoff && p.GameSense.SightHandoff && p.GameSense.GrenadeSafeHandoff &&
                                p.GameSense.RouteVariety && p.GameSense.QuietWalk);
        Assert.Equal(!gameSense, p.GameSense.EnemyCloseHandoff);
        if (gameSense)
        {
            Assert.True(Quirks.JumpsPerMinute(p) > 0);
            Assert.NotNull(Quirks.Value(p, "slow_share"));
            Assert.NotNull(Quirks.Value(p, "shots_per_burst"));
            Assert.NotNull(Quirks.Value(p, "single_shot_burst_share"));
        }
        // Every route file the profile names exists and decodes.
        foreach (var file in p.Routes.Values.SelectMany(r => r).Select(r => r.File).Distinct().Take(3))
            Assert.NotEmpty(MotionStore.LoadFromFile(store.Resolve(file)).Ticks);
    }

    [Fact]
    public void RulesAreOffUnlessTheProfileTurnsThemOn()
    {
        var s = JsonSerializer.Deserialize<CloneProfile>("""{"clone_id":"x","display_name":"x"}""")!.GameSense;
        Assert.False(s.HearHandoff || s.SightHandoff || s.GrenadeSafeHandoff || s.RouteVariety || s.QuietWalk);
        Assert.True(s.EnemyCloseHandoff);   // earlier clones keep the existing hand-off
    }

    [Fact]
    public void ProfileSectionIsReadAndValidated()
    {
        var p = JsonSerializer.Deserialize<CloneProfile>(
            """{"clone_id":"x","display_name":"x","game_sense":{"hear_handoff":true,"enemy_close_handoff":false,"footstep_units":900}}""")!;
        Assert.True(p.GameSense.HearHandoff);
        Assert.False(p.GameSense.EnemyCloseHandoff);
        Assert.Equal(900, p.GameSense.FootstepUnits);
        Assert.Throws<InvalidDataException>(() => new GameSenseSettings { QuietWalkShare = 1.5 }.Validate());
        Assert.Throws<InvalidDataException>(() => new GameSenseSettings { FootstepUnits = -1 }.Validate());
    }

    [Theory]
    [InlineData(Noise.Footstep, 1100, true)]
    [InlineData(Noise.Footstep, 1101, false)]
    [InlineData(Noise.Gunfire, 1999, true)]
    [InlineData(Noise.Gunfire, 2001, false)]
    [InlineData(Noise.Reload, 500, true)]
    public void HearingRangeDependsOnTheNoise(Noise kind, double distance, bool heard) =>
        Assert.Equal(heard, GameSense.Audible(kind, distance, new GameSenseSettings()));

    [Fact]
    public void HeardPositionIsBlurredByAtMostAFifthOfTheDistance()
    {
        for (double d1 = 0; d1 < 1; d1 += .1)
            for (double d2 = 0; d2 < 1; d2 += .1)
            {
                var p = GameSense.Blur([100, 200, 30], 1000, d1, d2);
                Assert.True(Math.Sqrt(Math.Pow(p[0] - 100, 2) + Math.Pow(p[1] - 200, 2)) <= 200.001);
                Assert.Equal(30, p[2]);
            }
    }

    [Theory]
    [InlineData("weapon_hegrenade", true)]
    [InlineData("weapon_flashbang", true)]
    [InlineData("weapon_molotov", true)]
    [InlineData("weapon_incgrenade", true)]
    [InlineData("weapon_smokegrenade", true)]
    [InlineData("weapon_decoy", true)]
    [InlineData("weapon_ak47", false)]
    [InlineData(null, false)]
    public void GrenadesAreRecognised(string? weapon, bool grenade) => Assert.Equal(grenade, GameSense.IsGrenade(weapon));

    [Fact]
    public void QuietWalkUsesThePlayersOwnSlowShareAndNeedsARecentNearbyNoise()
    {
        var s = new GameSenseSettings { QuietWalk = true };
        Assert.True(GameSense.QuietWalkNow(s, slowShare: .43, heardAgeSeconds: 1, heardDistance: 800, draw: .4));
        Assert.False(GameSense.QuietWalkNow(s, .43, 1, 800, .5));          // above his rate
        Assert.False(GameSense.QuietWalkNow(s, .43, 5, 800, 0));           // heard too long ago
        Assert.False(GameSense.QuietWalkNow(s, .43, 1, 2000, 0));          // too far
        Assert.False(GameSense.QuietWalkNow(new GameSenseSettings(), .43, 1, 800, 0));   // rule off
        Assert.True(GameSense.QuietWalkNow(new GameSenseSettings { QuietWalk = true, QuietWalkShare = .9 }, .1, 1, 800, .5));
    }

    [Fact]
    public void SpottedMaskIsReadBySlot()
    {
        uint[] mask = [1u << 3, 1u << 1];
        Assert.True(GameSense.SpottedBy(mask, 3));
        Assert.True(GameSense.SpottedBy(mask, 33));
        Assert.False(GameSense.SpottedBy(mask, 2));
        Assert.False(GameSense.SpottedBy(mask, 64));
        Assert.False(GameSense.SpottedBy(mask, -1));
    }

    [Fact]
    public void VariedPickDrawsAmongRoutesFromTheSameSpawnSpotOnly()
    {
        var p = Profile();
        // draw1 0.1 picks "mid"; draw2 picks among the mid routes within 32 units: the ones at 0 and 10.
        var seen = Enumerable.Range(0, 10).Select(i => GameSense.PickVaried(p, "T", "full", "recorded", [0, 0, 0], [], .1, i / 10.0)!)
            .ToArray();
        Assert.All(seen, r => Assert.Equal("mid", r.Key));
        Assert.Equal(new float[] { 0, 10 }, seen.Select(r => r.Start[0]).Distinct().OrderBy(x => x).ToArray());
    }

    [Fact]
    public void GunfireExcludesKnivesGrenadesAndTheBomb()
    {
        Assert.True(GameSense.IsGun("ak47"));
        Assert.True(GameSense.IsGun("weapon_awp"));
        foreach (var w in new[] { "knife", "weapon_knife_t", "bayonet", "hegrenade", "flashbang", "molotov", "decoy", "c4", "taser" })
            Assert.False(GameSense.IsGun(w));
        Assert.False(GameSense.IsGun(null));
    }

    [Fact]
    public void WalkIsButtonBit16AsInTheRecordedRoutes() => Assert.Equal(65536UL, GameSense.Walk);

    [Fact]
    public void VariedPickFallsBackToTheNearestWhenNoneIsNear()
    {
        var p = Profile();
        var r = GameSense.PickVaried(p, "T", "full", "recorded", [4000, 0, 0], [], .1, .5)!;
        Assert.Equal(5000, r.Start[0]);
    }

    [Fact]
    public void RecentDestinationsAreDownWeighted()
    {
        var p = Profile();
        // Without history mid and a share 50/50; with "mid" recent its weight drops to a quarter.
        int mid = 0, n = 1000;
        for (int i = 0; i < n; i++)
            if (GameSense.PickVaried(p, "T", "full", "recorded", [0, 0, 0], ["mid"], (i + .5) / n, .5)!.Key == "mid") mid++;
        Assert.InRange(mid, 190, 210);   // 0.125 / (0.125 + 0.5) = 20%
    }
}
