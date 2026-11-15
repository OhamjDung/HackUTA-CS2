using System.Text.Json.Serialization;

namespace CloneDirector.Core;

// Opt-in fantasy rules for authored Odyssey bots. Old player clones have no Odyssey section.
public sealed class OdysseySettings
{
    [JsonPropertyName("version")] public int Version { get; init; } = 1;
    [JsonPropertyName("difficulty")] public required string Difficulty { get; init; }
    [JsonPropertyName("invulnerable")] public bool Invulnerable { get; init; }
    [JsonPropertyName("damage_multiplier")] public double DamageMultiplier { get; init; } = 1;

    public void Validate(string id)
    {
        string expected = id switch
        {
            "poseidon" => "impossible", "odysseus" => "superhuman",
            "menelaus" or "melantho" => "medium", "telemachus" => "easy", _ => ""
        };
        if (Version != 1 || expected.Length == 0 || Difficulty != expected ||
            Invulnerable != (id == "poseidon") || !double.IsFinite(DamageMultiplier) ||
            Math.Abs(DamageMultiplier - (id == "odysseus" ? 1.08 : 1)) > .000001)
            throw new InvalidDataException("Invalid Odyssey identity, difficulty or fantasy rule.");
    }
}

public static class Odyssey
{
    public static bool IsPersona(string id) => id is "poseidon" or "odysseus" or "menelaus" or "telemachus" or "melantho";
    public sealed record DamageDecision(bool Block, float Damage);

    // Called BEFORE application, so a lethal shot cannot kill Poseidon before a health refill.
    // A human player is never passed a profile by the runtime binding lookup.
    public static DamageDecision Damage(OdysseySettings? victim, OdysseySettings? attacker, float damage, bool enemies)
    {
        if (victim?.Invulnerable == true) return new(true, 0);
        if (enemies && attacker is not null && float.IsFinite(damage) && damage > 0)
        {
            double scaled = damage * attacker.DamageMultiplier;
            if (scaled <= float.MaxValue) return new(false, (float)scaled);
        }
        return new(false, damage);
    }
}
