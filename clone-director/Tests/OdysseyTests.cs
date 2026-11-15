using System.Text.Json;
using CloneDirector.Core;
using Xunit;

namespace CloneDirector.Tests;

public sealed class OdysseyTests
{
    private static string Root()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "SPEC.md"))) dir = dir.Parent;
        return dir?.FullName ?? throw new Exception("Repository root missing");
    }

    [Theory]
    [InlineData("poseidon", "impossible", true, 1)]
    [InlineData("odysseus", "superhuman", false, 1.08)]
    [InlineData("menelaus", "medium", false, 1)]
    [InlineData("melantho", "medium", false, 1)]
    [InlineData("telemachus", "easy", false, 1)]
    public void ActualPersonaProfilesLoadWithFourteenAuthoredQuirks(string id, string difficulty, bool immune, double damage)
    {
        var store = new ProfileStore(Path.Combine(Root(), "clones"));
        var p = store.Load(id);
        Assert.Equal(id, p.Personality);
        Assert.Equal(difficulty, p.Odyssey!.Difficulty);
        Assert.Equal(immune, p.Odyssey.Invulnerable);
        Assert.Equal(damage, p.Odyssey.DamageMultiplier);
        Assert.All(p.Routes.Values, routes => Assert.Empty(routes));
        using var j = JsonDocument.Parse(File.ReadAllText(store.Resolve(id + ".json")));
        Assert.Equal(14, j.RootElement.GetProperty("odyssey").GetProperty("quirks").GetArrayLength());
        Assert.Equal(JsonValueKind.Null, j.RootElement.GetProperty("model").ValueKind);
    }

    [Theory]
    [InlineData(5)]
    [InlineData(10000)]
    public void PoseidonBlocksEvenLethalDamageWithoutAnAttackerOrHealthRefill(float damage)
    {
        var p = new ProfileStore(Path.Combine(Root(), "clones")).Load("poseidon");
        var result = Odyssey.Damage(p.Odyssey, null, damage, false);
        Assert.True(result.Block);
        Assert.Equal(0, result.Damage);
    }

    [Fact]
    public void MythicAdvantageAppliesOnlyToEnemyDamageAndImmunityWins()
    {
        var store = new ProfileStore(Path.Combine(Root(), "clones"));
        var strategist = store.Load("odysseus").Odyssey;
        Assert.Equal(108f, Odyssey.Damage(null, strategist, 100, true).Damage);
        Assert.Equal(100f, Odyssey.Damage(null, strategist, 100, false).Damage);
        Assert.True(Odyssey.Damage(store.Load("poseidon").Odyssey, strategist, 100, true).Block);
        Assert.False(Odyssey.Damage(store.Load("menelaus").Odyssey, null, 10000, true).Block);
        Assert.False(Odyssey.Damage(store.Load("telemachus").Odyssey, null, 10000, true).Block);
        Assert.Equal(100f, Odyssey.Damage(null, null, 100, true).Damage);
    }

    [Fact]
    public void FantasyRulesCannotLeakIntoPlayerClonesOrSwapDifficulty()
    {
        var rules = new OdysseySettings { Difficulty = "impossible", Invulnerable = true };
        Assert.Throws<InvalidDataException>(() => rules.Validate("donk_v2"));
        Assert.Throws<InvalidDataException>(() => rules.Validate("telemachus"));
        new OdysseySettings { Difficulty = "medium" }.Validate("menelaus");
        Assert.Throws<InvalidDataException>(() => new OdysseySettings { Difficulty = "superhuman", DamageMultiplier = double.NaN }.Validate("odysseus"));
        Assert.Null(new ProfileStore(Path.Combine(Root(), "clones")).Load("donk_v2").Odyssey);
        Assert.Throws<InvalidDataException>(() => new ProfileStore(Path.Combine(Root(), "clones")).Validate(
            new CloneProfile { Id = "poseidon", DisplayName = "Poseidon" }));
    }
}
