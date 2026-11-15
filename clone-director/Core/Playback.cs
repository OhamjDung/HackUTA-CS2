// Adapted from XBribo/CS2-Bot-Controller MotionRecording.cs (AGPL-3.0-only).
// See ../THIRD_PARTY.md for the source revision and changes.
using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;
using BotControllerApi;

namespace CloneDirector.Core;

public sealed class MotionRecording
{
    public int FormatVersion { get; set; }
    public required int Tickrate { get; set; }
    public required ReplayTick[] Ticks { get; set; }
    public required SubtickMove[] Subticks { get; set; }
    public required ReplayCommandFrame[] Commands { get; set; }
    public byte[] InputHistory { get; set; } = [];
}

public static class MotionStore
{
    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        IncludeFields = true,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        TypeInfoResolver = new DefaultJsonTypeInfoResolver { Modifiers = { RequireRecordingFields } }
    };

    private static void RequireRecordingFields(JsonTypeInfo info)
    {
        if (info.Type != typeof(ReplayTick) && info.Type != typeof(MovementSnapshot) &&
            info.Type != typeof(SubtickMove) && info.Type != typeof(ReplayCommandFrame)) return;
        foreach (var property in info.Properties)
            property.IsRequired = !property.Name.StartsWith("Pad", StringComparison.Ordinal);
    }

    public static MotionRecording LoadFromFile(string path)
    {
        using var file = File.OpenRead(path);
        using var brotli = new BrotliStream(file, CompressionMode.Decompress);
        var recording = JsonSerializer.Deserialize<MotionRecording>(brotli, JsonOptions)
            ?? throw new InvalidDataException("Recording is empty.");
        if (recording.FormatVersion != 1 || recording.Tickrate != 64)
            throw new InvalidDataException("Only format version 1 at 64 ticks per second is supported.");
        if (recording.Ticks is null || recording.Subticks is null || recording.Commands is null ||
            recording.Ticks.Length == 0 || recording.Commands.Length != recording.Ticks.Length)
            throw new InvalidDataException("Recording buffers are empty or incomplete.");
        if (recording.Ticks.Sum(t => (long)t.NumSubtick) != recording.Subticks.Length)
            throw new InvalidDataException("Recording subtick counts do not match the buffer.");
        recording.InputHistory ??= [];
        return recording;
    }
}

// Pure session logic so hand-offs can be tested without loading CS2 native libraries.
public interface IBotDriver
{
    bool SetPawn(int slot, nint pawn);
    bool Load(int slot, MotionRecording recording);
    bool Start(int slot);
    bool Stop(int slot);
    bool IsPlaying(int slot);
    bool Buy(int slot, string[] aliases);
    bool ClearBuy(int slot);
}

public sealed class BotSession(int slot, CloneProfile profile, IBotDriver driver, Action<string> log)
{
    public int Slot { get; } = slot;
    public CloneProfile Profile { get; } = profile;
    public Route? LastRoute { get; private set; }
    public string Reason { get; private set; } = "added";
    public string BuyType { get; private set; } = "eco";
    public bool Playing { get; private set; }

    public void RoundStart(string side, int money, bool pistolRound)
    {
        Stop("round start");
        if (Playing) return;
        LastRoute = null;
        Reason = "round start";
        BuyType = Choices.BuyType(money, pistolRound);
        // Never leave the previous side/round's plan active when this profile lacks a plan.
        if (!driver.ClearBuy(Slot)) { Reason = "could not clear buy plan"; return; }
        if (Profile.BuyPlan.TryGetValue(side, out var plans) && plans.TryGetValue(BuyType, out var plan))
            Reason = driver.Buy(Slot, plan.Aliases) ? "purchases set" : "purchase plan rejected";
    }

    public void Begin(Route route, nint pawn, MotionRecording recording)
    {
        Stop("new route");
        if (Playing) return;
        LastRoute = route;
        if (!driver.SetPawn(Slot, pawn) || !driver.Load(Slot, recording) || !driver.Start(Slot))
        {
            // Start can fail after buffers/pawn have been accepted; always release replay state.
            driver.Stop(Slot);
            Reason = "playback rejected";
            log($"{Profile.Id} slot={Slot} route={route.Key} source={route.Source}: {Reason}");
            return;
        }
        Playing = true;
        Reason = "playing";
    }

    public void Stop(string reason)
    {
        // Later round/death events must not overwrite the reason we handed control back.
        if (!Playing)
        {
            if (LastRoute is null) Reason = reason;
            return;
        }
        if (Playing)
        {
            if (!driver.Stop(Slot))
            {
                Reason = $"stop rejected ({reason})";
                log($"{Profile.Id} slot={Slot}: {Reason}");
                return;
            }
            Playing = false;
            log($"{Profile.Id} slot={Slot} route={LastRoute?.Key} source={LastRoute?.Source}: {reason}");
        }
        Reason = reason;
    }

    public void Poll()
    {
        if (!Playing || driver.IsPlaying(Slot)) return;
        Playing = false;
        Reason = "segment ended";
        log($"{Profile.Id} slot={Slot} route={LastRoute?.Key} source={LastRoute?.Source}: {Reason}");
    }

    public void Release(string reason)
    {
        Stop(reason);
        driver.ClearBuy(Slot);
    }
}
