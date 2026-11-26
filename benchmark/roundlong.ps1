# Long task: 3 sessions per run. -Pilot runs only round 1 of baseline and workbench to calibrate cost and time.
# Needs CLAUDE_CODE_OAUTH_TOKEN in this shell (no spaces; claude setup-token).
param([switch]$Pilot)
$ErrorActionPreference = "Stop"
if (-not $env:CLAUDE_CODE_OAUTH_TOKEN) { throw "set CLAUDE_CODE_OAUTH_TOKEN first (claude setup-token)" }
if ($env:CLAUDE_CODE_OAUTH_TOKEN -match "\s") { throw "the token has whitespace; remove it" }
Set-Location (Split-Path $PSScriptRoot)
$rounds = if ($Pilot) { 1 } else { 1, 2, 3 }
foreach ($round in $rounds) {
    $arms = if ($round % 2 -eq 1) { "baseline", "workbench", "lean" } else { "workbench", "lean", "baseline" }
    if ($Pilot) { $arms = "baseline", "workbench" }
    foreach ($arm in $arms) {
        if (Test-Path "benchmark/runs-long/long-$arm-r$round") { Write-Host "skip long-$arm-r$round (already run)"; continue }
        python benchmark/runner/run_long.py --arm $arm --round $round
        foreach ($k in 1, 2, 3) {
            $scoreArgs = @("--run", "benchmark/runs-long/long-$arm-r$round/s$k")
            if ($k -lt 3) { $scoreArgs += "--skip-mutation" }
            if (Test-Path "benchmark/runs-long/long-$arm-r$round/s$k") {
                python benchmark/runner/score.py @scoreArgs
            }
        }
    }
}
python benchmark/runner/report_long.py
