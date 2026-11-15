using CloneDirector.Core;
using Xunit;

namespace CloneDirector.Tests;

public sealed class PuzzleTests
{
    private static PuzzleStart Loadout(params string[] weapons) => new() { Health = 100, Armor = 100, Helmet = true, Money = 800, Weapons = [.. weapons] };

    // Hero (CT, slot 1) walks east, an enemy (T, slot 2) stands still; sampled every 0.25 s for 12 s, hero dies at 12.
    private static PuzzleRecorder Recorded(out double deathTime)
    {
        var r = new PuzzleRecorder();
        double t = 100;
        for (int i = 0; i <= 48; i++, t += 0.25)
        {
            r.Sample(t, 1, "hero", "CT", 100 + i * 10, 0, 0, 0, 0, 100, "ak47", Loadout("ak47", "flashbang"));
            r.Sample(t, 2, "enemy", "T", 900, 0, 0, 180, 0, 100, "awp", Loadout("awp"));
            if (i == 20) r.MarkFire(1);
        }
        deathTime = t - 0.25;
        r.AddEvent(deathTime - 5, "kill", "hero", "bystander", "ak47");
        r.AddEvent(deathTime, "kill", "enemy", "hero", "awp");
        return r;
    }

    [Fact]
    public void BuildCutsTheTenSecondsBeforeTheDeath()
    {
        var r = Recorded(out double death);
        var p = r.Build(death, 1, "d1", "Death", "de_mirage", "2026-11-15T00:00:00+00:00", 10, 580, 0, 0, 0, 0)!;
        Assert.Equal(10, p.WindowSeconds);
        Assert.Equal(2, p.Players.Count);
        var hero = p.Hero;
        Assert.Equal("hero", hero.Name);
        Assert.Equal(0, hero.Track[0].T);
        Assert.Equal(10, hero.Track[^1].T);
        Assert.Equal(0, hero.Track[^1].Hp);                       // the death sample
        Assert.Equal(new[] { "ak47", "flashbang" }, hero.Start.Weapons);
        Assert.Equal(1, p.Original.Kills);                        // the bystander, 5 s before the death
        Assert.Equal("enemy", p.Original.Killer);
        Assert.Equal("awp", p.Original.Weapon);
        Assert.Contains(hero.Track, s => s.Fire);
        Assert.All(p.Events, e => Assert.InRange(e.T, 0, 10));
    }

    [Fact]
    public void ShortHistoryIsNotSaved()
    {
        var r = new PuzzleRecorder();
        r.Sample(10, 1, "hero", "CT", 0, 0, 0, 0, 0, 100, "ak47", Loadout());
        r.Sample(10.25, 1, "hero", "CT", 0, 0, 0, 0, 0, 100, "ak47", Loadout());
        Assert.Null(r.Build(10.25, 1, "d", "t", "de_mirage", "", 10, 0, 0, 0, 0, 0));
        Assert.Null(r.Build(10.25, 99, "d", "t", "de_mirage", "", 10, 0, 0, 0, 0, 0));
    }

    [Fact]
    public void BotKilledBeforeHeroKeepsItsDeathInTheRewind()
    {
        var recorder = new PuzzleRecorder();
        for (int i = 0; i <= 20; i++)
        {
            double time = i * 0.25;
            recorder.Sample(time, 1, "hero", "CT", 0, 0, 0, 0, 0, 100, "ak47", Loadout("ak47"));
            if (time <= 2)
                recorder.Sample(time, 2, "enemy", "T", 100, 0, 0, 0, 0, 100, "awp", Loadout("awp"));
        }
        recorder.MarkDeath(2.1, 2);
        var puzzle = recorder.Build(5, 1, "d", "Death", "de_mirage", "", 10, 0, 0, 0, 0, 0)!;
        var enemy = Assert.Single(puzzle.Players, player => player.Name == "enemy");
        Assert.Equal(0, enemy.Track[^1].Hp);
        Assert.Equal(2.1, enemy.Track[^1].T);
    }

    [Fact]
    public void OldFramesAreDropped()
    {
        var r = Recorded(out double death);
        var p = r.Build(death, 1, "d", "t", "de_mirage", "", 30, 0, 0, 0, 0, 0)!;
        Assert.True(p.WindowSeconds <= PuzzleRecorder.KeepSeconds + 0.3);
    }

    [Fact]
    public void SameNamesGetSuffixes()
    {
        var r = new PuzzleRecorder();
        for (int i = 0; i < 20; i++)
        {
            r.Sample(i * .25, 1, "me", "CT", 0, 0, 0, 0, 0, 100, "", Loadout());
            r.Sample(i * .25, 2, "bot", "T", 0, 0, 0, 0, 0, 100, "", Loadout());
            r.Sample(i * .25, 3, "bot", "T", 0, 0, 0, 0, 0, 100, "", Loadout());
        }
        var p = r.Build(4.75, 1, "d", "t", "de_mirage", "", 10, 0, 0, 0, 0, 0)!;
        Assert.Equal(new[] { "bot", "bot#2", "me" }, p.Players.Select(x => x.Name).Order().ToArray());
    }

    [Fact]
    public void BuiltPuzzleSurvivesAJsonRoundTrip()
    {
        var r = Recorded(out double death);
        var built = r.Build(death, 1, "d1", "Death", "de_mirage", "2026-11-15T00:00:00+00:00", 10, 580, 0, 0, 0, 0)!;
        var back = PuzzleData.Parse(System.Text.Json.JsonSerializer.Serialize(built, PuzzleData.Json));
        Assert.Equal(built.Players.Count, back.Players.Count);
        Assert.Equal(built.Hero.Track.Count, back.Hero.Track.Count);
        Assert.Contains("\"window_seconds\"", System.Text.Json.JsonSerializer.Serialize(built, PuzzleData.Json));
    }

    [Fact]
    public void ParseRefusesBadPuzzles()
    {
        Assert.Throws<InvalidDataException>(() => PuzzleData.Parse("{\"players\":[]}"));
        string noHero = "{\"players\":[{\"slot\":1,\"name\":\"a\",\"side\":\"CT\",\"track\":[{\"t\":0,\"x\":0,\"y\":0}]}]}";
        Assert.Throws<InvalidDataException>(() => PuzzleData.Parse(noHero));
    }

    [Fact]
    public void RulesMatchTheServicesRules()
    {
        Assert.Equal(1, PuzzleRules.NeededKills(0));
        Assert.Equal(3, PuzzleRules.NeededKills(2));
        Assert.True(PuzzleRules.Solved(true, 2, 1));
        Assert.False(PuzzleRules.Solved(true, 1, 1));    // a tie fails
        Assert.False(PuzzleRules.Solved(false, 5, 1));   // died
    }

    [Fact]
    public void PlaybackInterpolatesPositionYawAndVelocity()
    {
        PuzzleSample S(double t, double x, double yaw) => new() { T = t, X = x, Yaw = yaw };
        var track = new[] { S(0, 0, 350), S(1, 100, 10), S(2, 100, 10) };
        var mid = PuzzleMath.At(track, 0.5);
        Assert.Equal(50, mid.X, 3);
        Assert.Equal(360, mid.Yaw, 3);                    // 350 -> 10 turns the short way, through 0/360
        Assert.Equal(100, mid.Vx, 3);                     // units per second
        Assert.Equal(0, PuzzleMath.At(track, -1).X);
        Assert.Equal(100, PuzzleMath.At(track, 99).X);
        Assert.Equal(0, PuzzleMath.At(track, 99).Vx);
    }

    [Fact]
    public void RunCountsKillsAndNeedsBothSurvivalAndKills()
    {
        var data = new PuzzleData { Original = new PuzzleOriginal { Kills = 1 } };
        var run = new PuzzleRun(data);
        run.HeroGotKill();
        run.Finish(true);
        Assert.False(run.Solved);                         // one kill ties the original
        var again = new PuzzleRun(data);
        again.HeroGotKill(); again.HeroGotKill();
        again.Finish(true);
        again.HeroGotKill();                              // after the end: ignored
        Assert.Equal(2, again.Kills);
        Assert.True(again.Solved);
    }
}
