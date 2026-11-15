<#
.SYNOPSIS
  Collect the logs needed to debug a CS2 run (coach, match service, CloneDirector) into one zip.
.DESCRIPTION
  Run it from the match-service folder, while the service is still running if possible:
    powershell -ExecutionPolicy Bypass -File .\collect-logs.ps1
  It writes data\logs\send-<time>.zip (data\ is git-ignored) and prints the path. Send that zip.
  What goes in: the newest service logs, the last lines of the newest CounterStrikeSharp logs (CloneDirector,
  MatchBridge), the newest saved deaths, /health, /coach and /matches from the running service, the git
  commit, and which .env names are set or empty. Never the .env values, the API keys or the GSI token.
  Written on a Mac; not yet run on Windows.
#>
param(
    [string]$Cs2Dir = "",
    [int]$Port = 8000,
    [int]$CssLines = 4000
)
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logs = Join-Path $repo "data\logs"
$out = Join-Path $logs "send-$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null

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

$notes = New-Object System.Collections.Generic.List[string]
$notes.Add("collected: $(Get-Date -Format o)")

# --- the repo -------------------------------------------------------------------------------------
Push-Location $repo
$notes.Add("git commit: $(git rev-parse --short HEAD 2>&1)")
$notes.Add("git branch: $(git rev-parse --abbrev-ref HEAD 2>&1)")
$notes.Add("git status:")
git status --short 2>&1 | ForEach-Object { $notes.Add("  $_") }
Pop-Location

# --- .env: names only -----------------------------------------------------------------------------
$envFile = Join-Path $here ".env"
if (Test-Path $envFile) {
    $notes.Add(".env (values hidden):")
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') {
            $state = if ($Matches[2].Trim().Length -gt 0) { "set" } else { "EMPTY" }
            $notes.Add("  $($Matches[1]) = $state")
        }
    }
} else {
    $notes.Add(".env: MISSING ($envFile)")
}

# --- the PC ---------------------------------------------------------------------------------------
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $notes.Add(("free memory: {0:N1} GiB of {1:N1} GiB" -f ($os.FreePhysicalMemory / 1MB), ($os.TotalVisibleMemorySize / 1MB)))
} catch { $notes.Add("free memory: unknown ($_)") }
$cs2 = Get-Process cs2 -ErrorAction SilentlyContinue
$notes.Add("cs2 running: $([bool]$cs2)")

# --- the running service --------------------------------------------------------------------------
foreach ($path in @("health", "coach", "matches", "deaths")) {
    $file = Join-Path $out "service-$path.json"
    try {
        Invoke-RestMethod -Uri "http://localhost:$Port/$path" -TimeoutSec 5 | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $file
    } catch {
        "not reachable: $_" | Set-Content -Encoding UTF8 $file
    }
}

# --- service logs ---------------------------------------------------------------------------------
Get-ChildItem -Path $logs -Filter "match-service-*.log" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3 |
    ForEach-Object { Copy-Item $_.FullName $out }

# --- CS2 side -------------------------------------------------------------------------------------
if (-not $Cs2Dir) { $Cs2Dir = Find-Cs2 }
if ($Cs2Dir) {
    $csgo = Join-Path $Cs2Dir "game\csgo"
    $notes.Add("cs2 folder: $Cs2Dir")
    $gameinfo = Join-Path $csgo "gameinfo.gi"
    $hasMetamod = (Test-Path $gameinfo) -and (Select-String -Path $gameinfo -Pattern "addons/metamod" -Quiet)
    $notes.Add("gameinfo.gi has addons/metamod: $hasMetamod")
    $plugins = Join-Path $csgo "addons\counterstrikesharp\plugins"
    foreach ($name in @("CloneDirector", "MatchBridge")) {
        $dll = Join-Path $plugins "$name\$name.dll"
        if (Test-Path $dll) {
            $notes.Add("$name.dll: $((Get-Item $dll).LastWriteTime.ToString('s'))")
        } else {
            $notes.Add("$name.dll: MISSING")
        }
    }
    $cssLogs = Join-Path $csgo "addons\counterstrikesharp\logs"
    Get-ChildItem -Path $cssLogs -Filter "log-all*.txt" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 2 |
        ForEach-Object { Get-Content $_.FullName -Tail $CssLines | Set-Content -Encoding UTF8 (Join-Path $out "css-$($_.Name)") }
    $deaths = Join-Path $plugins "CloneDirector\deaths"
    $deathFiles = Get-ChildItem -Path $deaths -Filter "*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    $notes.Add("death files: $(@($deathFiles).Count) in $deaths")
    if ($deathFiles) {
        $deathOut = Join-Path $out "deaths"
        New-Item -ItemType Directory -Force -Path $deathOut | Out-Null
        $deathFiles | Select-Object -First 5 | ForEach-Object { Copy-Item $_.FullName $deathOut }
    }
} else {
    $notes.Add("cs2 folder: NOT FOUND (pass -Cs2Dir)")
}

$notes | Set-Content -Encoding UTF8 (Join-Path $out "summary.txt")
$zip = "$out.zip"
Compress-Archive -Path (Join-Path $out "*") -DestinationPath $zip -Force
Write-Host ""
Get-Content (Join-Path $out "summary.txt") | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Send this file: $zip" -ForegroundColor Green
