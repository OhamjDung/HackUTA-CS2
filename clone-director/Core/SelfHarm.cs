namespace CloneDirector.Core;

// Guardrail (2026-11-15, Arjun): a clone bot must never kill itself. Testers saw clones die with no
// enemy involved; the cause is not confirmed (handoffs/tom-self-kill-diagnosis.md lists the suspects:
// own grenade, own fire, falls, a plugin slay). Instead of fixing one suspect, every hit on a clone bot
// is checked before the game applies it, and the hits below are refused. SPEC.md section 6.2.
public static class SelfHarm
{
    // Who caused one hit on a clone bot.
    public enum Source
    {
        Enemy,      // a player on the other team: allowed
        Teammate,   // a player on the bot's own team (friendly fire): allowed
        Self,       // the bot itself: its own HE grenade, its own molotov or incendiary fire
        NoPlayer,   // nobody: a fall, the world, a map hazard (and the bomb, see IsBomb)
    }

    public static Source Classify(bool fromPlayer, bool fromVictim, bool sameTeam) =>
        !fromPlayer ? Source.NoPlayer : fromVictim ? Source.Self : sameTeam ? Source.Teammate : Source.Enemy;

    // The planted bomb's explosion. It is a round objective, not self-harm, so it can still kill a clone
    // (Arjun's choice, 2026-11-15). Checked on both the inflictor and the attacker, because which entity
    // the game names for the explosion is not confirmed.
    public static bool IsBomb(string? inflictor, string? attacker) => inflictor == "planted_c4" || attacker == "planted_c4";

    // True: refuse the hit. Damage from the bot itself or from no player, except the bomb.
    public static bool Blocks(Source source, bool bomb) => !bomb && (source is Source.Self or Source.NoPlayer);

    // Console commands that make a player kill itself. Refused for clone bots.
    public static bool IsSuicideCommand(string command) =>
        command.Equals("kill", StringComparison.OrdinalIgnoreCase) || command.Equals("explode", StringComparison.OrdinalIgnoreCase);
}
