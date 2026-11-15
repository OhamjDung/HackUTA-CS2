// No-self-kill guardrail for clone bots (SPEC.md section 6.2). Uses the same documented
// OnEntityTakeDamagePre listener as OdysseyMode.cs (CounterStrikeSharp API 1.0.378) and
// BasePlugin.AddCommandListener. Written from zero. NOT YET COMPILED OR RUN: written on a PC without the
// .NET SDK or BotControllerApi.dll; Tom builds and installs it.
using CloneDirector.Core;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Modules.Commands;

namespace CloneDirector;

public sealed partial class CloneDirectorPlugin
{
    private void SafetyLoad()
    {
        // A plugin or the bot base could make a bot run `kill`; that path never goes through damage.
        AddCommandListener("kill", RefuseCloneSuicide, HookMode.Pre);
        AddCommandListener("explode", RefuseCloneSuicide, HookMode.Pre);
    }

    // Called from DamagePre (OdysseyMode.cs) for every hit on a living clone bot, before it is applied.
    // True: the hit is refused and the bot's health does not change.
    private bool BlockSelfHarm(Binding victim, CBaseEntity victimPawn, CTakeDamageInfo info)
    {
        var attacker = info.Attacker.Value;
        var inflictor = info.Inflictor.Value;
        // The player behind the hit: the attacker, else the grenade or fire entity, else whoever owns it.
        // Looking this far keeps an enemy's grenade from ever counting as "no player".
        var who = PlayerBehind(attacker) ?? PlayerBehind(inflictor) ?? PlayerBehind(inflictor?.OwnerEntity.Value);
        var source = SelfHarm.Classify(who is not null, who?.Pawn == victimPawn.Handle, who?.Team == victim.Player.TeamNum);
        string? inflictorName = inflictor is { IsValid: true } ? inflictor.DesignerName : null;
        string? attackerName = attacker is { IsValid: true } ? attacker.DesignerName : null;
        if (!SelfHarm.Blocks(source, SelfHarm.IsBomb(inflictorName, attackerName))) return false;
        victim.SelfHarmBlocked++;
        // Fire hurts several times a second, so log at most once a second per bot. The log line says what
        // the guardrail caught, which is the evidence the self-kill diagnosis still needs.
        if (Server.CurrentTime - victim.LastSelfHarmLog >= 1)
        {
            victim.LastSelfHarmLog = Server.CurrentTime;
            Log($"SELF-HARM blocked {victim.Session.Profile.Id} slot={victim.Session.Slot} source={source} " +
                $"attacker={attackerName ?? "none"} inflictor={inflictorName ?? "none"} damage={info.Damage:F0} " +
                $"route={(victim.Session.Playing ? "playing" : "stopped")} total={victim.SelfHarmBlocked}");
        }
        return true;
    }

    private sealed record DamagePlayer(nint Pawn, int Team);

    // A damage source that is a player: a pawn ("player") or its controller. Null for the world, the bomb,
    // map hazards and anything else.
    private static DamagePlayer? PlayerBehind(CBaseEntity? source)
    {
        if (source is not { IsValid: true }) return null;
        if (source.DesignerName == "player") return new(source.Handle, source.TeamNum);
        if (source.DesignerName != "cs_player_controller") return null;
        var controller = new CCSPlayerController(source.Handle);
        var pawn = controller.PlayerPawn.Value;
        return pawn is { IsValid: true } ? new(pawn.Handle, controller.TeamNum) : null;
    }

    private HookResult RefuseCloneSuicide(CCSPlayerController? player, CommandInfo command)
    {
        if (player is not { IsValid: true, IsBot: true } || !_bots.TryGetValue(player.Slot, out var b) ||
            b.Player.Handle != player.Handle || !SelfHarm.IsSuicideCommand(command.GetArg(0)))
            return HookResult.Continue;
        b.SelfHarmBlocked++;
        Log($"SELF-HARM refused '{command.GetArg(0)}' for {b.Session.Profile.Id} slot={player.Slot} total={b.SelfHarmBlocked}");
        return HookResult.Handled;
    }
}
