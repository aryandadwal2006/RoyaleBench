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
$PytestReportPath = Join-Path $ValidationRoot "pytest-junit.xml"

Write-Host "=== RoyaleBench v1 integrated validation ==="
Write-Host "Repository: $Root"
$PythonVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0) { throw "Python is not available." }
$VersionParts = $PythonVersion.Split(".")
if ([int]$VersionParts[0] -lt 3 -or ([int]$VersionParts[0] -eq 3 -and [int]$VersionParts[1] -lt 11)) {
    throw "RoyaleBench requires Python 3.11 or newer; found $PythonVersion"
}
$JavaOutput = & cmd.exe /d /c "java -version 2>&1"
$JavaExitCode = $LASTEXITCODE
$JavaVersion = $JavaOutput | Select-Object -First 1
if ($JavaExitCode -ne 0 -or $JavaVersion -notmatch '"21\.') {
    throw "Java 21 is required. Detected: $JavaVersion"
}

# JPype needs the JVM shared library, not only java.exe. Resolve the JDK
# corresponding to Java 21 on PATH and expose it to all child Python processes.
$JavaHomeCandidates = New-Object System.Collections.ArrayList
$JavaApplications = @(Get-Command java.exe -CommandType Application -All -ErrorAction SilentlyContinue)
foreach ($JavaApplication in $JavaApplications) {
    $JavaPaths = @()
    foreach ($PropertyName in @("Path", "Source")) {
        $Property = $JavaApplication.PSObject.Properties[$PropertyName]
        if ($null -ne $Property -and -not [string]::IsNullOrWhiteSpace([string]$Property.Value)) {
            $JavaPaths += [string]$Property.Value
        }
    }

    foreach ($JavaPath in $JavaPaths) {
        $ResolvedJavaPaths = @($JavaPath)
        try {
            $JavaFile = Get-Item -LiteralPath $JavaPath -ErrorAction Stop
            $TargetProperty = $JavaFile.PSObject.Properties["Target"]
            if ($null -ne $TargetProperty) {
                foreach ($TargetPath in @($TargetProperty.Value)) {
                    if ([string]::IsNullOrWhiteSpace([string]$TargetPath)) { continue }
                    if (-not [System.IO.Path]::IsPathRooted([string]$TargetPath)) {
                        $TargetPath = Join-Path (Split-Path -Parent $JavaPath) ([string]$TargetPath)
                    }
                    $ResolvedJavaPaths += [System.IO.Path]::GetFullPath([string]$TargetPath)
                }
            }
        }
        catch {
            # The original PATH entry is still checked below.
        }

        foreach ($ResolvedJavaPath in $ResolvedJavaPaths) {
            if (-not (Test-Path -LiteralPath $ResolvedJavaPath -PathType Leaf)) { continue }
            $CandidateHome = Split-Path -Parent (Split-Path -Parent $ResolvedJavaPath)
            if (-not [string]::IsNullOrWhiteSpace($CandidateHome)) {
                $CandidateHome = [System.IO.Path]::GetFullPath($CandidateHome).TrimEnd("\")
                if (-not $JavaHomeCandidates.Contains($CandidateHome)) {
                    [void]$JavaHomeCandidates.Add($CandidateHome)
                }
            }
        }
    }
}

# Keep JAVA_HOME as a fallback for installations where java.exe is exposed
# through a launcher that does not reveal its target path.
if (-not [string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
    $ConfiguredJavaHome = $env:JAVA_HOME.Trim().Trim('"')
    if (Test-Path -LiteralPath $ConfiguredJavaHome -PathType Container) {
        $ConfiguredJavaHome = [System.IO.Path]::GetFullPath($ConfiguredJavaHome).TrimEnd("\")
        if (-not $JavaHomeCandidates.Contains($ConfiguredJavaHome)) {
            [void]$JavaHomeCandidates.Add($ConfiguredJavaHome)
        }
    }
}

$JavaHome = $null
$JvmDllCandidate = $null
foreach ($CandidateHome in $JavaHomeCandidates) {
    $CandidateJvmDlls = @(
        (Join-Path $CandidateHome "bin\server\jvm.dll"),
        (Join-Path $CandidateHome "jre\bin\server\jvm.dll"),
        (Join-Path $CandidateHome "bin\client\jvm.dll")
    )
    $CandidateJvmDll = $CandidateJvmDlls |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace([string]$CandidateJvmDll)) { continue }

    $CandidateJavaExe = Join-Path $CandidateHome "bin\java.exe"
    if (-not (Test-Path -LiteralPath $CandidateJavaExe -PathType Leaf)) { continue }
    $CandidateJavaOutput = & cmd.exe /d /c ('"' + $CandidateJavaExe + '" -version 2>&1')
    $CandidateJavaExitCode = $LASTEXITCODE
    $CandidateJavaVersion = [string]($CandidateJavaOutput | Select-Object -First 1)
    if ($CandidateJavaExitCode -ne 0 -or $CandidateJavaVersion -notmatch '"21\.') { continue }

    $JavaHome = $CandidateHome
    $JvmDllCandidate = [string]$CandidateJvmDll
    break
}

if ([string]::IsNullOrWhiteSpace($JavaHome)) {
    throw @"
Java 21 is available, but its JDK home and jvm.dll could not be resolved.
JPype requires the JVM shared library. Set JAVA_HOME to the root of your
Java 21 JDK (the directory containing bin\java.exe and bin\server\jvm.dll),
then rerun this script.
"@
}
$env:JAVA_HOME = $JavaHome

Write-Host "Python: $PythonVersion"
Write-Host "Java: $JavaVersion"
Write-Host "JAVA_HOME: $env:JAVA_HOME"
Write-Host "JVM library: $JvmDllCandidate"

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

$ExpectedCrforgeCommit = "fa5959055c590a493d62c8dbc804e602832d08a6"
$ActualCrforgeCommit = & git -C $CrforgeRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the pinned CRForge submodule commit."
}
if ($ActualCrforgeCommit.Trim() -ne $ExpectedCrforgeCommit) {
    throw "CRForge commit mismatch. Expected $ExpectedCrforgeCommit, found $($ActualCrforgeCommit.Trim())."
}

& $Python -m pip install -e (Join-Path $Root "third_party\upstream\crforge\python")
if ($LASTEXITCODE -ne 0) { throw "Could not install the pinned crforge-env package." }

# Verify JPype can resolve the exact JVM before the native adapter tests start.
$JvmPathOutput = & $Python -c "import jpype; print(jpype.getDefaultJVMPath())"
$JvmPathExitCode = $LASTEXITCODE
if ($JvmPathExitCode -ne 0) {
    throw "JPype could not locate or load the JVM shared-library path. JAVA_HOME=$env:JAVA_HOME"
}
$ResolvedJvmPath = [string]($JvmPathOutput | Select-Object -Last 1)
if (-not (Test-Path -LiteralPath $ResolvedJvmPath -PathType Leaf)) {
    throw "JPype returned a JVM path that does not exist: $ResolvedJvmPath"
}
Write-Host "JPype JVM preflight: $ResolvedJvmPath"

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

# :env:test builds and tests CRForge, but it does not create the installDist
# distribution consumed by the headless Python adapter.
$CrforgeInstall = Join-Path $CrforgeRoot "env\build\install\env"
$CrforgeLib = Join-Path $CrforgeInstall "lib"
$CrforgeJars = @(Get-ChildItem -Path $CrforgeLib -Filter "*.jar" -File -ErrorAction SilentlyContinue)
$CrforgeTables = Join-Path $HOME ".crforge\tables\16.635.8"
$NativeTestReport = Join-Path $CrforgeRoot "env\build\reports\tests\test\index.html"

if (-not (Test-Path $NativeTestReport)) {
    throw "CRForge Gradle test report is missing at $NativeTestReport."
}
if (-not (Test-Path $CrforgeInstall) -or $CrforgeJars.Count -eq 0) {
    throw @"
CRForge's headless runtime distribution is missing or contains no JARs:
  $CrforgeLib
The -SkipBuild switch skips :env:installDist, which creates this distribution.
Run .\scripts\validate_v1.ps1 without -SkipBuild, or run
.\scripts\build_engine.ps1 -Python $Python before using -SkipBuild.
"@
}
if (-not (Test-Path $CrforgeTables)) {
    throw "CRForge game tables are missing at $CrforgeTables. Run .\scripts\build_engine.ps1 -Python $Python."
}
Write-Host "CRForge runtime: $CrforgeInstall ($($CrforgeJars.Count) JAR files)"
Write-Host "CRForge game tables: $CrforgeTables"
Write-Host "CRForge native test report: $NativeTestReport"

New-Item -ItemType Directory -Force -Path $ValidationRoot | Out-Null

Write-Host "=== Python tests ==="
& $Python -m pytest --junitxml $PytestReportPath
if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }
[xml]$PytestXml = Get-Content $PytestReportPath -Raw
$NativePythonCases = $PytestXml.SelectNodes("//testcase[contains(@classname, 'test_crforge_native')]")
$NativePythonSkips = $PytestXml.SelectNodes("//testcase[contains(@classname, 'test_crforge_native')]/skipped")
if ($NativePythonCases.Count -lt 3) {
    throw "Expected at least three CRForge native adapter tests, found $($NativePythonCases.Count)."
}
if ($NativePythonSkips.Count -gt 0) {
    throw "CRForge native adapter tests must execute without skips; found $($NativePythonSkips.Count) skipped test(s)."
}
Write-Host "CRForge native adapter tests: $($NativePythonCases.Count) collected, 0 skipped."

Write-Host "=== Ruff ==="
& $Python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw "Ruff checks failed." }

Write-Host "=== Configuration ==="
& $Python -m royalebench config-check
if ($LASTEXITCODE -ne 0) { throw "V1 configuration validation failed." }

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

foreach ($Tournament in @($TournamentJson, $ExternalTournamentJson)) {
    if ($Tournament.total_matches -lt 1 -or $Tournament.completed_matches -ne $Tournament.total_matches) {
        throw "Tournament acceptance requires every scheduled match to complete."
    }
}
foreach ($SplitName in @("train", "validation", "test")) {
    $SplitProperty = $DatasetJson.splits.PSObject.Properties[$SplitName]
    if ($null -eq $SplitProperty) {
        throw "Dataset manifest is missing the $SplitName split."
    }
    $Split = $SplitProperty.Value
    if ($Split.match_count -lt 1 -or $Split.transition_count -lt 1 -or [string]::IsNullOrWhiteSpace($Split.sha256)) {
        throw "Dataset $SplitName split must contain matches, transitions and a SHA-256."
    }
}
foreach ($Horizon in @("1", "2", "4")) {
    $HorizonProperty = $ForecastJson.horizons.PSObject.Properties[$Horizon]
    if ($null -eq $HorizonProperty -or $HorizonProperty.Value.examples -lt 1) {
        throw "Forecast evaluation is missing examples for horizon $Horizon."
    }
}
if ($ForecastJson.input_contract -ne "source_observation_plus_intervening_actions_only") {
    throw "Forecast report does not declare the required action-conditioned input contract."
}
$Report = [ordered]@{
    status = "passed"
    started_at = $Started.ToString("o")
    completed_at = (Get-Date).ToString("o")
    python = $PythonVersion
    java = $JavaVersion
    java_home = $env:JAVA_HOME
    jvm_library = $ResolvedJvmPath
    crforge_commit = $ActualCrforgeCommit.Trim()
    game_data_version = "16.635.8"
    game_data_content_sha = "062a11e0500c03cc041f123413b1ef1846b539a4"
    profile = $Profile
    native_engine_tests = "passed"
    native_engine_test_report = $NativeTestReport
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
        pytest_junit_report = $PytestReportPath
    }
}
$ReportPath = Join-Path $ValidationRoot "validation_report.json"
$Report | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $ReportPath

Write-Host ""
Write-Host "VALIDATION PASSED"
Write-Host "Report: $ReportPath"
Write-Host "Tournament: $TournamentRoot"
Write-Host "Dataset: $DatasetRoot"
