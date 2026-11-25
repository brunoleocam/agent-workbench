# Second medium round: workbench and lean after the PR 20 changes (spec-first check, multi-process rule).
# Baseline is not re-run: it does not depend on the plugin. Needs CLAUDE_CODE_OAUTH_TOKEN in this shell.
$ErrorActionPreference = "Stop"
if (-not $env:CLAUDE_CODE_OAUTH_TOKEN) { throw "set CLAUDE_CODE_OAUTH_TOKEN first (claude setup-token)" }
Set-Location (Split-Path $PSScriptRoot)
foreach ($round in 1, 2, 3) {
    foreach ($arm in "workbench", "lean") {
        python benchmark/runner/run.py --project medium --arm $arm --round $round --runs-dir benchmark/runs-v2
        python benchmark/runner/score.py --run "benchmark/runs-v2/medium-$arm-r$round"
    }
}
