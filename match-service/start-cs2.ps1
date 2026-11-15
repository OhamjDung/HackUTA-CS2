<#
.SYNOPSIS
  Start the match service in CS2 mode on the Windows PC that runs CS2.

.DESCRIPTION
  1. Finds the CS2 folder (or use -Cs2Dir).
  2. Installs the game state config file into game\csgo\cfg, with the token and this service's address.
  3. With -Console plugin: builds and installs the MatchBridge plugin (needs the .NET SDK, version 8 or newer).
  4. Starts the service on http://localhost:8000. Open /health to check the connection to CS2.

  Run it from the match-service folder:
    powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1
    powershell -ExecutionPolicy Bypass -File .\start-cs2.ps1 -Console plugin

  Not yet run on Windows.

.PARAMETER Listen
  Address the service listens on. Default 127.0.0.1: only this PC can reach it. Use 0.0.0.0 only
  when another machine (for example the lobby on a teammate's laptop) must reach it, because then
  anyone on the same network can create and stop matches.

.PARAMETER Console
  How to send commands to CS2: netcon (default; needs -netconport 2121 in CS2's launch options),
  rcon (needs rcon_password in CS2), or plugin (the MatchBridge plugin).
#>
param(
    [ValidateSet("netcon", "rcon", "plugin")]
    [string]$Console = "netcon",
    [string]$Cs2Dir = "",
    [string]$Token = "",
    [string]$ConsolePassword = "",
    [int]$Port = 8000,
    [string]$Listen = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Cs2 {
    $roots = @()
    $steam = (Get-ItemProperty -Path "HKCU:\Software\Valve\Steam" -ErrorAction SilentlyContinue).SteamPath
    if ($steam) {
        $roots += $steam
        $libraries = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $libraries) {
            foreach ($m in [regex]::Matches((Get-Content $libraries -Raw), '"path"\s+"([^"]+)"')) {
                $roots += $m.Groups[1].Value -replace '\\\\', '\'
            }
        }
    }
    $roots += "C:\Program Files (x86)\Steam"
    foreach ($root in $roots) {
        $dir = Join-Path $root "steamapps\common\Counter-Strike Global Offensive"
        if (Test-Path (Join-Path $dir "game\csgo")) { return $dir }
    }
    return $null
}

# --- uv ---------------------------------------------------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it with:  winget install --id=astral-sh.uv -e" -ForegroundColor Red
    Write-Host "then open a new PowerShell window and run this script again."
    exit 1
}

# --- CS2 folder -------------------------------------------------------------------------------
if (-not $Cs2Dir) { $Cs2Dir = Find-Cs2 }
if (-not $Cs2Dir -or -not (Test-Path (Join-Path $Cs2Dir "game\csgo"))) {
    Write-Host "Could not find CS2. Pass its folder, for example:" -ForegroundColor Red
    Write-Host '  .\start-cs2.ps1 -Cs2Dir "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive"'
    exit 1
}
$csgo = Join-Path $Cs2Dir "game\csgo"
Write-Host "CS2 folder: $Cs2Dir"

# --- Game state config ------------------------------------------------------------------------
# Keep the token that is already installed, because CS2 only reads this file when it starts.
$gsiTarget = Join-Path $csgo "cfg\gamestate_integration_matchservice.cfg"
if (-not $Token -and (Test-Path $gsiTarget)) {
    $found = [regex]::Match((Get-Content $gsiTarget -Raw), '"token"\s+"([^"]+)"')
    if ($found.Success) { $Token = $found.Groups[1].Value }
}
$firstInstall = -not (Test-Path $gsiTarget)
if (-not $Token -or $Token -eq "change-me") { $Token = [guid]::NewGuid().ToString("N").Substring(0, 16) }

$gsi = Get-Content (Join-Path $here "gsi\gamestate_integration_matchservice.cfg") -Raw
$gsi = $gsi -replace '"token"\s+"[^"]*"', "`"token`"`t`"$Token`""
$gsi = $gsi -replace '"uri"\s+"[^"]*"', "`"uri`"`t`t`"http://127.0.0.1:$Port/gsi`""
Set-Content -Path $gsiTarget -Value $gsi -Encoding ASCII
Write-Host "Game state config installed: $gsiTarget"
if ($firstInstall) {
    Write-Host "First install: restart CS2 so it reads the game state config." -ForegroundColor Yellow
}

# --- Console channel --------------------------------------------------------------------------
if (-not $ConsolePassword) { $ConsolePassword = $Token }
switch ($Console) {
    "netcon" {
        Write-Host "Console: netcon. CS2's launch options must include  -netconport 2121"
    }
    "rcon" {
        Write-Host "Console: rcon. CS2's launch options must include  -usercon"
        Write-Host "and in CS2's console run:  rcon_password $ConsolePassword"
    }
    "plugin" {
        $project = Join-Path $here "plugin\MatchBridge"
        $dll = Join-Path $project "bin\Release\net8.0\MatchBridge.dll"
        if (Get-Command dotnet -ErrorAction SilentlyContinue) {
            Write-Host "Building the MatchBridge plugin..."
            dotnet build $project -c Release | Out-Host
            if ($LASTEXITCODE -ne 0) { Write-Host "Plugin build failed." -ForegroundColor Red; exit 1 }
        }
        if (-not (Test-Path $dll)) {
            Write-Host "MatchBridge.dll is not built, and the .NET SDK is not installed." -ForegroundColor Red
            Write-Host "Install it with:  winget install Microsoft.DotNet.SDK.10   then run this script again."
            Write-Host "(SDK 10 builds both MatchBridge and CloneDirector.)"
            exit 1
        }
        $pluginsDir = Join-Path $csgo "addons\counterstrikesharp\plugins"
        if (-not (Test-Path $pluginsDir)) {
            Write-Host "CounterStrikeSharp is not installed in CS2 ($pluginsDir). Install CS2-Bot-Improver first." -ForegroundColor Red
            exit 1
        }
        $target = Join-Path $pluginsDir "MatchBridge"
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        Copy-Item $dll $target -Force
        @{ port = 27100; token = $ConsolePassword } | ConvertTo-Json | Set-Content (Join-Path $target "matchbridge.json") -Encoding ASCII
        Write-Host "MatchBridge plugin installed: $target"
        Write-Host "Restart CS2 (or run  css_plugins reload MatchBridge  in its console) to load it." -ForegroundColor Yellow
    }
}

# --- Start the service ------------------------------------------------------------------------
$env:MATCH_BACKEND = "cs2"
$env:CS2_CONSOLE = $Console
$env:CS2_CONSOLE_PASSWORD = $ConsolePassword
$env:GSI_TOKEN = $Token
$env:CS2_DEMO_DIR = $csgo
$env:PUBLIC_URL = "http://localhost:$Port"

Write-Host ""
Write-Host "Starting the match service. Check the connection at  http://localhost:$Port/health" -ForegroundColor Green
Write-Host "API docs: http://localhost:$Port/docs    Stop with Ctrl+C."
Set-Location $here
uv sync
if ($Listen -ne "127.0.0.1") {
    Write-Host "Listening on $Listen : anyone on this network can create and stop matches." -ForegroundColor Yellow
}
uv run uvicorn match_service.main:app --host $Listen --port $Port
