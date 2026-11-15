// SPDX-License-Identifier: AGPL-3.0-or-later
//
// MatchBridge: lets the match service run console commands inside CS2.
//
// It listens on 127.0.0.1 only (this PC), on the port in matchbridge.json (default 27100).
// Protocol, one line each way per step:
//   client: auth <token>          plugin: ok | denied
//   client: <console command>     plugin: ok     (the command runs on the game's next frame)
//   client: matchbridge_ping      plugin: pong
// It also adds the console command `matchbridge_jointeam <1|2|3>`, which moves the human player
// at this PC to spectator (1), T (2) or CT (3).
//
// Written from zero: no existing CounterStrikeSharp plugin did this (SPEC.md section 4.2).
// Not yet built or run in CS2.

using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Modules.Commands;
using CounterStrikeSharp.API.Modules.Utils;

namespace MatchBridge;

public sealed class MatchBridgeConfig
{
    public int Port { get; set; } = 27100;
    public string Token { get; set; } = "";
}

public sealed class MatchBridgePlugin : BasePlugin
{
    public override string ModuleName => "MatchBridge";
    public override string ModuleVersion => "0.1.0";
    public override string ModuleAuthor => "HackUTA CS2 team";
    public override string ModuleDescription => "Runs console commands sent by the match service over a local TCP port.";

    private readonly CancellationTokenSource _stop = new();
    private MatchBridgeConfig _config = new();
    private TcpListener? _listener;

    public override void Load(bool hotReload)
    {
        AddCommand("matchbridge_jointeam", "Move the human player at this PC: 1 spectator, 2 T, 3 CT", OnJoinTeam);

        var path = Path.Combine(ModuleDirectory, "matchbridge.json");
        if (File.Exists(path))
        {
            _config = JsonSerializer.Deserialize<MatchBridgeConfig>(
                File.ReadAllText(path), new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new();
        }
        if (string.IsNullOrWhiteSpace(_config.Token))
        {
            Console.WriteLine($"[MatchBridge] No token in {path}. Not listening.");
            return;
        }

        _listener = new TcpListener(IPAddress.Loopback, _config.Port);
        _listener.Start();
        Console.WriteLine($"[MatchBridge] Listening on 127.0.0.1:{_config.Port}");
        _ = Task.Run(() => AcceptLoop(_stop.Token));
    }

    public override void Unload(bool hotReload)
    {
        _stop.Cancel();
        _listener?.Stop();
    }

    private async Task AcceptLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            TcpClient client;
            try
            {
                client = await _listener!.AcceptTcpClientAsync(ct);
            }
            catch (Exception) when (ct.IsCancellationRequested)
            {
                return;
            }
            catch (SocketException)
            {
                continue;
            }
            _ = Task.Run(() => Handle(client, ct), ct);
        }
    }

    private async Task Handle(TcpClient client, CancellationToken ct)
    {
        try
        {
            using (client)
            {
                var stream = client.GetStream();
                using var reader = new StreamReader(stream, Encoding.UTF8);
                using var writer = new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };

                var first = await reader.ReadLineAsync(ct);
                if (first?.Trim() != $"auth {_config.Token}")
                {
                    await writer.WriteLineAsync("denied");
                    return;
                }
                await writer.WriteLineAsync("ok");

                string? line;
                while ((line = await reader.ReadLineAsync(ct)) != null)
                {
                    var command = line.Trim();
                    if (command.Length == 0)
                    {
                        continue;
                    }
                    if (command == "matchbridge_ping")
                    {
                        await writer.WriteLineAsync("pong");
                        continue;
                    }
                    // Game functions must run on the main thread; NextFrame queues the command there.
                    Server.NextFrame(() => Server.ExecuteCommand(command));
                    await writer.WriteLineAsync("ok");
                }
            }
        }
        catch (Exception ex) when (ex is IOException or OperationCanceledException or ObjectDisposedException)
        {
            // The match service closed the connection, or the plugin is unloading.
        }
    }

    private void OnJoinTeam(CCSPlayerController? caller, CommandInfo info)
    {
        if (!int.TryParse(info.GetArg(1), out var team) || team < 1 || team > 3)
        {
            info.ReplyToCommand("Usage: matchbridge_jointeam <1 spectator | 2 T | 3 CT>");
            return;
        }
        var human = Utilities.GetPlayers().FirstOrDefault(p => p is { IsValid: true, IsBot: false, IsHLTV: false });
        if (human == null)
        {
            info.ReplyToCommand("No human player in the game.");
            return;
        }
        human.ChangeTeam((CsTeam)team);
    }
}
