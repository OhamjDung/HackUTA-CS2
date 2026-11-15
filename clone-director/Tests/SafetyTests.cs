using CloneDirector.Core;
using Xunit;

namespace CloneDirector.Tests;

// The no-self-kill guardrail's rule (Core/SelfHarm.cs). The game side (SafetyMode.cs) only works out who
// caused a hit; these cases are the whole decision.
public sealed class SafetyTests
{
    [Theory]
    [InlineData(true, true, true, SelfHarm.Source.Self)]        // own HE grenade or own fire
    [InlineData(false, false, false, SelfHarm.Source.NoPlayer)] // a fall, the world, a map hazard
    [InlineData(true, false, true, SelfHarm.Source.Teammate)]
    [InlineData(true, false, false, SelfHarm.Source.Enemy)]
    public void ClassifiesWhoCausedTheHit(bool fromPlayer, bool fromVictim, bool sameTeam, SelfHarm.Source expected) =>
        Assert.Equal(expected, SelfHarm.Classify(fromPlayer, fromVictim, sameTeam));

    [Fact]
    public void ABotsOwnGrenadeOrFireAndFallsAreRefused()
    {
        Assert.True(SelfHarm.Blocks(SelfHarm.Source.Self, bomb: false));
        Assert.True(SelfHarm.Blocks(SelfHarm.Source.NoPlayer, bomb: false));
    }

    [Fact]
    public void EnemiesAndTeammatesCanStillKillAClone()
    {
        Assert.False(SelfHarm.Blocks(SelfHarm.Source.Enemy, bomb: false));
        Assert.False(SelfHarm.Blocks(SelfHarm.Source.Teammate, bomb: false));
    }

    [Theory]
    [InlineData("planted_c4", null)]
    [InlineData(null, "planted_c4")]
    [InlineData("planted_c4", "player")]
    public void TheBombCanStillKillAClone(string? inflictor, string? attacker)
    {
        bool bomb = SelfHarm.IsBomb(inflictor, attacker);
        Assert.True(bomb);
        // Whether the game names the planter or nobody as the attacker, the bomb is never refused.
        Assert.False(SelfHarm.Blocks(SelfHarm.Source.NoPlayer, bomb));
        Assert.False(SelfHarm.Blocks(SelfHarm.Source.Self, bomb));
    }

    [Theory]
    [InlineData("hegrenade_projectile", "player")]
    [InlineData("inferno", "player")]
    [InlineData("worldspawn", "worldspawn")]
    [InlineData(null, null)]
    public void OtherInflictorsAreNotTheBomb(string? inflictor, string? attacker) =>
        Assert.False(SelfHarm.IsBomb(inflictor, attacker));

    [Theory]
    [InlineData("kill", true)]
    [InlineData("KILL", true)]
    [InlineData("explode", true)]
    [InlineData("killvector", false)]
    [InlineData("say", false)]
    public void SuicideCommandsAreRecognised(string command, bool expected) =>
        Assert.Equal(expected, SelfHarm.IsSuicideCommand(command));
}
