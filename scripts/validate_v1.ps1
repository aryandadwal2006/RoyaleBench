param(
    [string]$Python = "python",
    [switch]$SkipBuild,
    [string]$Seeds = "11,22,33",
    [ValidateSet("fast-250ms-v1", "llm-api-1s-v1")]
    [string]$Profile = "fast-250ms-v1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Started = Get-Date
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$ValidationRoot = Join-Path $Root ("results\validation-" + $RunId)
$TournamentRoot = Join-Path $ValidationRoot "tournament"
$ExternalTournamentRoot = Join-Path $ValidationRoot "external-agent-tournament"
$DatasetRoot = Join-Path $ValidationRoot "trajectory_dataset"
$ForecastReportPath = Join-Path $ValidationRoot "forecast-persistence.json"

Write-Host "=== RoyaleBench v1 integrated validation ==="
Write-Host "Repository: $Root"
$PythonVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0) { throw "Python is not available." }
$VersionParts = $PythonVersion.Split(".")
if ([int]$VersionParts[0] -lt 3 -or ([int]$VersionParts[0] -eq 3 -and [int]$VersionParts[1] -lt 11)) {
    throw "RoyaleBench requires Python 3.11 or newer; found $PythonVersion"
}
$JavaVersion = & java -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or $JavaVersion -notmatch '"21\.') {
    throw "Java 21 is required. Detected: $JavaVersion"
}
Write-Host "Python: $PythonVersion"
Write-Host "Java: $JavaVersion"

$CrforgeRoot = Join-Path $Root "third_party\upstream\crforge"
$CrforgeGradle = Join-Path $CrforgeRoot "gradlew.bat"
if (-not (Test-Path $CrforgeGradle)) {
    throw "Pinned CRForge submodule is missing at $CrforgeRoot"
}

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot "bootstrap_upstreams.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Upstream bootstrap failed." }
    & (Join-Path $PSScriptRoot "build_engine.ps1") -Python $Python
    if ($LASTEXITCODE -ne 0) { throw "CRForge environment build failed." }
}
else {
    & $Python -m pip install -e ".[dev,engine]"
    if ($LASTEXITCODE -ne 0) { throw "Could not install RoyaleBench dependencies." }
}

& $Python -m pip install -e (Join-Path $Root "third_party\upstream\crforge\python")
if ($LASTEXITCODE -ne 0) { throw "Could not install the pinned crforge-env package." }

Write-Host "=== Pinned CRForge native environment tests ==="
Push-Location $CrforgeRoot
try {
    & .\gradlew.bat :env:test "-Pcrforge.assetSource=cdn" --no-daemon
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned CRForge native environment tests failed."
    }
}
finally {
    Pop-Location
}

Write-Host "=== Python tests ==="
& $Python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }

Write-Host "=== Ruff ==="
& $Python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw "Ruff checks failed." }

Write-Host "=== Configuration ==="
& $Python -m royalebench config-check
if ($LASTEXITCODE -ne 0) { throw "V1 configuration validation failed." }

New-Item -ItemType Directory -Force -Path $ValidationRoot | Out-Null

Write-Host "=== Headless paired tournament ==="
& $Python -m royalebench tournament --profile $Profile --agents "random-legal-v1,hog-cycle-rules-v1" --seeds $Seeds --output $TournamentRoot
if ($LASTEXITCODE -ne 0) { throw "One or more tournament matches failed." }

Write-Host "=== External JSONL agent integration tournament ==="
$WorkerCommand = ConvertTo-Json -Compress @($Python, "examples/agents/hog_cycle_jsonl.py")
& $Python -m royalebench tournament --profile $Profile --agents "random-legal-v1,external-hog" --external-agent-name "external-hog" --external-agent-command $WorkerCommand --external-agent-cwd $Root --seeds $Seeds --output $ExternalTournamentRoot
if ($LASTEXITCODE -ne 0) { throw "External JSONL agent tournament failed." }

Write-Host "=== Automatic trajectory dataset ==="
& $Python -m royalebench dataset --matches (Join-Path $TournamentRoot "matches") --output $DatasetRoot
if ($LASTEXITCODE -ne 0) { throw "Trajectory dataset export failed." }

Write-Host "=== Held-out forecasting baseline ==="
& $Python -m royalebench forecast-eval --split (Join-Path $DatasetRoot "test.jsonl.gz") --horizons "1,2,4" --output $ForecastReportPath
if ($LASTEXITCODE -ne 0) { throw "Held-out forecasting baseline failed." }

$TournamentJson = Get-Content (Join-Path $TournamentRoot "tournament.json") -Raw | ConvertFrom-Json
$ExternalTournamentJson = Get-Content (Join-Path $ExternalTournamentRoot "tournament.json") -Raw | ConvertFrom-Json
$DatasetJson = Get-Content (Join-Path $DatasetRoot "dataset_manifest.json") -Raw | ConvertFrom-Json
$ForecastJson = Get-Content $ForecastReportPath -Raw | ConvertFrom-Json
$Report = [ordered]@{
    status = "passed"
    started_at = $Started.ToString("o")
    completed_at = (Get-Date).ToString("o")
    python = $PythonVersion
    java = $JavaVersion
    profile = $Profile
    native_engine_tests = "passed"
    native_engine_test_report = (Join-Path $CrforgeRoot "env\build\reports\tests\test\index.html")
    tournament = @{
        total_matches = $TournamentJson.total_matches
        completed_matches = $TournamentJson.completed_matches
        failed_matches = $TournamentJson.void_or_failed_matches
    }
    external_agent_tournament = @{
        total_matches = $ExternalTournamentJson.total_matches
        completed_matches = $ExternalTournamentJson.completed_matches
        failed_matches = $ExternalTournamentJson.void_or_failed_matches
    }
    dataset = @{
        total_matches = $DatasetJson.total_matches
        splits = $DatasetJson.splits
    }
    forecasting = @{
        forecaster = $ForecastJson.forecaster
        horizons = $ForecastJson.horizons
        dataset_provenance = $ForecastJson.dataset_provenance
    }
    output = @{
        tournament = $TournamentRoot
        external_agent_tournament = $ExternalTournamentRoot
        dataset = $DatasetRoot
        forecast_report = $ForecastReportPath
    }
}
$ReportPath = Join-Path $ValidationRoot "validation_report.json"
$Report | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $ReportPath

Write-Host ""
Write-Host "VALIDATION PASSED"
Write-Host "Report: $ReportPath"
Write-Host "Tournament: $TournamentRoot"
Write-Host "Dataset: $DatasetRoot"
