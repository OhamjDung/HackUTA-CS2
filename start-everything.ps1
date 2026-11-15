<#
.SYNOPSIS
  One command on the CS2 PC: update the code, install what is missing, and start the match service
  (with the death coach), CS2 in Bot Mode, and the website.
.DESCRIPTION
  Double-click start-everything.bat, or run from the repo folder:
    powershell -ExecutionPolicy Bypass -File .\start-everything.ps1
  Steps:
    1. git pull (skipped when there are local changes).
    2. Installs uv and Node.js with winget if missing; then `uv sync` and `npm install`.
    3. Checks match-service\.env (the Gemini and ElevenLabs keys and voice ids).
    4. Checks free memory and the Bot Mode file gameinfo.gi (restores it from backup\WithBots if the
       metamod line is gone and CS2 is closed).
    5. Opens a window running match-service\start-cs2.ps1 -Bots clone -Record off (installs the game state
       config and MatchBridge, starts the service; its log goes to data\logs\).
    6. Starts CS2 in Bot Mode (cs2.exe -steam -insecure -netconport 2121 -usercon) if it is not running.
       Anti-cheat is off: private matches only, never join an official or public server.
    7. Opens a window running the website (npm run dev) and opens http://localhost:3000.
  Send logs afterwards with:  powershell -ExecutionPolicy Bypass -File .\match-service\collect-logs.ps1
  Written on a Mac; not yet run on Windows.
.PARAMETER NoPull
  Do not run git pull.
.PARAMETER NoGame
  Do not start CS2 (for example when it is already open with the right launch options).
.PARAMETER Bots
  clone (default; CloneDirector clones, needed by the coach) or stand_in.
#>
param(
    [switch]$NoPull,
    [switch]$NoGame,
    [ValidateSet("clone", "stand_in")]
    [string]$Bots = "clone",
    [string]$Cs2Dir = "",
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$service = Join-Path $repo "match-service"
$frontend = Join-Path $repo "frontend"

function Step($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Warn($text) { Write-Host "   ! $text" -ForegroundColor Yellow }
function Fail($text) { Write-Host "   X $text" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Need($command, $wingetId, $name) {
    if (Get-Command $command -ErrorAction SilentlyContinue) { return }
    Warn "$name is not installed. Installing with winget ($wingetId)..."
    winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Fail "$name still not found. Close this window, open a new one and run the script again."
    }
}
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
function Wait-Http($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { return Invoke-RestMethod -Uri $url -TimeoutSec 3 } catch { Start-Sleep -Seconds 2 }
    }
    return $null
}

# --- 1. code ---------------------------------------------------------------------------------------
Step "Updating the code"
Set-Location $repo
if ($NoPull) {
    Write-Host "   skipped (-NoPull)"
} else {
    # git refuses (and changes nothing) if a local change would be overwritten, so this is safe to try.
    if (git status --porcelain) { Warn "There are local changes; trying git pull anyway (git keeps them)." }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { Warn "git pull failed (a local change touches an updated file?); continuing with the code on disk." }
}
Write-Host "   commit $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)"

# --- 2. tools and packages -------------------------------------------------------------------------
Step "Installing tools and packages"
Need "uv" "astral-sh.uv" "uv"
Need "npm" "OpenJS.NodeJS.LTS" "Node.js"
Push-Location $service; uv sync; $uvOk = $LASTEXITCODE -eq 0; Pop-Location
if (-not $uvOk) { Fail "uv sync failed in match-service." }
Push-Location $frontend; npm install --no-audit --no-fund; $npmOk = $LASTEXITCODE -eq 0; Pop-Location
if (-not $npmOk) { Fail "npm install failed in frontend." }

# --- 3. keys ---------------------------------------------------------------------------------------
Step "Checking match-service\.env (values are not shown)"
$envFile = Join-Path $service ".env"
$wanted = "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_DONK", "ELEVENLABS_VOICE_BROKY"
if (-not (Test-Path $envFile)) {
    $template = @(
        "# Death coach settings (SPEC.md section 9.7). Git-ignored; never commit keys.",
        "GEMINI_API_KEY=",
        "ELEVENLABS_API_KEY=",
        "ELEVENLABS_VOICE_DONK=lV7P6Y2mGb44Kor32e4R",
        "ELEVENLABS_VOICE_BROKY=fHsClnnDBfxszcOczXEB"
    )
    Set-Content -Path $envFile -Value $template -Encoding UTF8
    Warn "Created $envFile. Put the two API keys in it, save, then run this script again."
    notepad $envFile
    Read-Host "Press Enter to close"
    exit 1
}
# Same rules as the service (coach.py): match-service\.env first, then the repo's .env, and other common key names.
$aliases = @{ "GEMINI_API_KEY" = @("GOOGLE_API_KEY", "GEMINI_KEY", "GOOGLE_GENAI_API_KEY");
              "ELEVENLABS_API_KEY" = @("ELEVEN_LABS_API_KEY", "ELEVENLABS_KEY", "ELEVEN_API_KEY", "XI_API_KEY") }
function Read-EnvValues {
    $v = @{}
    foreach ($file in @((Join-Path $repo ".env"), $envFile)) {
        if (-not (Test-Path $file)) { continue }
        foreach ($line in Get-Content $file) {
            if ($line -match '^\s*(?:export\s+)?([A-Za-z0-9_]+)\s*=\s*(.*)$') {
                $val = $Matches[2].Trim().Trim('"').Trim("'")
                if ($val) { $v[$Matches[1]] = $val }
            }
        }
    }
    foreach ($name in $aliases.Keys) {
        if (-not $v[$name]) { foreach ($o in $aliases[$name]) { if ($v[$o]) { $v[$name] = $v[$o]; break } } }
    }
    return $v
}
# Add any missing voice line, so a .env made by hand still gets the voices.
$voiceLines = @{ "ELEVENLABS_VOICE_DONK" = "lV7P6Y2mGb44Kor32e4R"; "ELEVENLABS_VOICE_BROKY" = "fHsClnnDBfxszcOczXEB" }
$values = Read-EnvValues
foreach ($name in $voiceLines.Keys) {
    if (-not $values[$name]) {
        Add-Content -Path $envFile -Value "$name=$($voiceLines[$name])" -Encoding UTF8
        Write-Host "   added $name to $envFile"
    }
}
$names = (Get-Content $envFile | Where-Object { $_ -match '^\s*([A-Za-z0-9_]+)\s*=' } | ForEach-Object { $Matches[1] }) -join ", "
Write-Host "   names in match-service\.env: $names"
$values = Read-EnvValues
if (-not $values["GEMINI_API_KEY"] -or -not $values["ELEVENLABS_API_KEY"]) {
    Warn "A key is missing. Notepad opens match-service\.env: put the keys after GEMINI_API_KEY= and ELEVENLABS_API_KEY=, save, close Notepad."
    if (-not (Select-String -Path $envFile -Pattern '^\s*GEMINI_API_KEY\s*=' -Quiet)) { Add-Content -Path $envFile -Value "GEMINI_API_KEY=" -Encoding UTF8 }
    if (-not (Select-String -Path $envFile -Pattern '^\s*ELEVENLABS_API_KEY\s*=' -Quiet)) { Add-Content -Path $envFile -Value "ELEVENLABS_API_KEY=" -Encoding UTF8 }
    Start-Process notepad -ArgumentList $envFile -Wait
    $values = Read-EnvValues
}
foreach ($name in $wanted) {
    if ($values[$name]) { Write-Host "   $name set" } else { Warn "$name is EMPTY or missing: that part of the coach stays off" }
}

# --- 4. the PC and Bot Mode files --------------------------------------------------------------------
Step "Checking the PC and CS2's Bot Mode files"
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $freeGiB = $os.FreePhysicalMemory / 1MB
    Write-Host ("   free memory: {0:N1} GiB" -f $freeGiB)
    if ($freeGiB -lt 4) { Warn "Under 4 GiB free. Close heavy apps (browsers, Discord) first: the service was once killed for low memory." }
} catch { Warn "Could not read free memory." }
if (-not $Cs2Dir) { $Cs2Dir = Find-Cs2 }
if (-not $Cs2Dir) { Fail "Could not find CS2. Run again with  -Cs2Dir ""<...\Counter-Strike Global Offensive>""" }
$csgo = Join-Path $Cs2Dir "game\csgo"
Write-Host "   CS2 folder: $Cs2Dir"
$cs2Running = [bool](Get-Process cs2 -ErrorAction SilentlyContinue)
$gameinfo = Join-Path $csgo "gameinfo.gi"
if (-not (Test-Path $gameinfo)) {
    Warn "gameinfo.gi not found at $gameinfo"
} elseif (-not (Select-String -Path $gameinfo -Pattern "addons/metamod" -Quiet)) {
    $backup = @((Join-Path $Cs2Dir "backup\WithBots\gameinfo.gi"), (Join-Path $csgo "backup\WithBots\gameinfo.gi"),
                (Join-Path $Cs2Dir "game\backup\WithBots\gameinfo.gi")) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cs2Running) {
        Warn "gameinfo.gi has no addons/metamod line, so no plugins or bots will load. Close CS2 and run this again."
    } elseif ($backup) {
        Copy-Item $gameinfo "$gameinfo.reverted-$(Get-Date -Format yyyyMMdd-HHmmss)"
        Copy-Item $backup $gameinfo -Force
        Write-Host "   gameinfo.gi had reverted; restored from $backup (old copy kept next to it)"
    } else {
        Warn "gameinfo.gi has no addons/metamod line and no backup\WithBots\gameinfo.gi was found. Fix it by hand (AGENTS.md section 7)."
    }
} else {
    Write-Host "   gameinfo.gi has the metamod line"
}
$cloneDirector = Join-Path $csgo "addons\counterstrikesharp\plugins\CloneDirector\CloneDirector.dll"
if ($Bots -eq "clone" -and -not (Test-Path $cloneDirector)) {
    Fail "CloneDirector is not installed ($cloneDirector). See clone-director\README.md, or run with -Bots stand_in (no coach)."
}

# --- 5. match service ----------------------------------------------------------------------------------
Step "Starting the match service (new window)"
$existing = Wait-Http "http://localhost:$Port/health" 2
if ($existing) {
    Warn "A match service already answers on port $Port; leaving it running. Close its window and run again to restart it."
} else {
    $launch = "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
            "Set-Location '$service'; `$host.UI.RawUI.WindowTitle = 'Match service'; & '.\start-cs2.ps1' -Bots $Bots -Record off -Port $Port"
    Start-Process powershell -ArgumentList $launch
    if (-not (Wait-Http "http://localhost:$Port/health" 90)) {
        Fail "The match service did not answer within 90 s. Read the 'Match service' window."
    }
}
Write-Host "   match service up: http://localhost:$Port/health"

# --- 6. CS2 ----------------------------------------------------------------------------------------
Step "CS2 in Bot Mode"
if ($NoGame) {
    Write-Host "   skipped (-NoGame)"
} elseif ($cs2Running) {
    Write-Host "   CS2 is already running. If you did not start it with  -insecure -netconport 2121 -usercon  (not from the Steam library), close it and run this again."
} else {
    $exe = Join-Path $Cs2Dir "game\bin\win64\cs2.exe"
    if (-not (Test-Path $exe)) { Fail "cs2.exe not found at $exe" }
    Write-Host "   Starting $exe (anti-cheat off: private matches only)"
    Start-Process -FilePath $exe -ArgumentList "-steam", "-insecure", "-netconport", "2121", "-usercon" -WorkingDirectory (Split-Path $exe)
    Write-Host "   Waiting for CS2's console (up to 3 minutes)..."
    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 5
        $health = Wait-Http "http://localhost:$Port/health" 3
    } until (($health -and $health.console.reachable) -or (Get-Date) -gt $deadline)
    if ($health -and $health.console.reachable) { Write-Host "   CS2 console reachable" } else { Warn "CS2's console did not answer yet; check http://localhost:$Port/health later." }
}

# --- 7. website --------------------------------------------------------------------------------------
Step "Starting the website (new window)"
$launch = "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location '$frontend'; `$host.UI.RawUI.WindowTitle = 'Website'; npm run dev"
Start-Process powershell -ArgumentList $launch
if (Wait-Http "http://localhost:3000" 120) { Start-Process "http://localhost:3000" } else { Warn "The website did not answer within 2 minutes; read the 'Website' window." }

# --- done --------------------------------------------------------------------------------------------
Step "Ready"
$coach = Wait-Http "http://localhost:$Port/coach" 5
if ($coach) {
    Write-Host ("   coach: gemini {0}, voice {1}, voices [{2}], chat {3}" -f $coach.gemini, $coach.voice, ($coach.voices -join ", "), $coach.chat)
}
Write-Host "   Website:        http://localhost:3000"
Write-Host "   Service health: http://localhost:$Port/health"
Write-Host "   Hear the voices without playing:"
Write-Host "     Invoke-RestMethod -Method Post http://localhost:$Port/coach/puzzles/pro_2393226_r7_donk"
Write-Host "   In game: start a match with a donk or broky clone, die, and listen."
Write-Host ""
Write-Host "   Send logs when done (or when something breaks):" -ForegroundColor Green
Write-Host "     powershell -ExecutionPolicy Bypass -File .\match-service\collect-logs.ps1" -ForegroundColor Green
