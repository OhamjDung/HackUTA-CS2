// Based on CounterStrikeSharp's documented OnEntityTakeDamagePre listener (API1.0.378).
// No global god mode, health inflation, enemy-location lookup or native damage-function offset.
using CloneDirector.Core;
using CounterStrikeSharp.API.Core;

namespace CloneDirector;

public sealed partial class CloneDirectorPlugin
{
    private void OdysseyLoad() => RegisterListener<Listeners.OnEntityTakeDamagePre>(OdysseyDamage);

    private HookResult OdysseyDamage(CBaseEntity entity, CTakeDamageInfo info)
    {
        if (!entity.IsValid || !_bots.Values.Any(b => b.Session.Profile.Odyssey is not null)) return HookResult.Continue;
        // Match live pawn handles, never a stale slot or a display-name substring.
        var victim = _bots.Values.FirstOrDefault(b => b.Player.IsValid && b.Player.IsBot && b.Player.PawnIsAlive &&
            b.Player.PlayerPawn.Value is { IsValid: true } p && p.Handle == entity.Handle);
        // Poseidon can also shoot humans; they have no clone binding but are valid damage recipients.
        var target = victim?.Player ?? AllPlayers().FirstOrDefault(p => p.IsValid && p.PawnIsAlive &&
            p.PlayerPawn.Value is { IsValid: true } pawn && pawn.Handle == entity.Handle);
        if (target is null || target.TeamNum is not (2 or 3)) return HookResult.Continue;
        var source = info.Attacker.Value;
        var attacker = source is { IsValid: true } ? _bots.Values.FirstOrDefault(b => b.Player.IsValid &&
            b.Player.IsBot && b.Player.PlayerPawn.Value is { IsValid: true } p &&
            p.Handle == source.Handle) : null;
        var decision = Odyssey.Damage(victim?.Session.Profile.Odyssey, attacker?.Session.Profile.Odyssey,
            info.Damage, attacker is not null && attacker.Player.TeamNum is 2 or 3 && attacker.Player.TeamNum != target.TeamNum);
        if (decision.Block)
        {
            if (victim is not null) victim.BlockedDamageEvents++;
            return HookResult.Handled;
        }
        if (attacker is not null && decision.Damage != info.Damage) attacker.BoostedDamageEvents++;
        info.Damage = decision.Damage;
        return HookResult.Continue;
    }
}
