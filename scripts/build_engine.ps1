param(
    [ValidateSet("cdn")]
    [string]$AssetSource = "cdn",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Upstream = Join-Path $Root "third_party\upstream\crforge"

if (-not (Test-Path (Join-Path $Upstream "gradlew.bat"))) {
    throw "CRForge submodule is missing. Run .\scripts\bootstrap_upstreams.ps1 first."
}

$ExpectedCommit = "fa5959055c590a493d62c8dbc804e602832d08a6"
$ActualCommit = & git -C $Upstream rev-parse HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the CRForge submodule commit."
}
if ($ActualCommit.Trim() -ne $ExpectedCommit) {
    throw "CRForge commit mismatch. Expected $ExpectedCommit, found $($ActualCommit.Trim())."
}

Push-Location $Upstream
try {
    & .\gradlew.bat :env:installDist :tables:dataVersionTables "-Pcrforge.assetSource=$AssetSource"
    if ($LASTEXITCODE -ne 0) {
        throw "CRForge env distribution or game-table build failed."
    }
}
finally {
    Pop-Location
}

Set-Location $Root
& $Python -m pip install -e ".[dev,engine]"
if ($LASTEXITCODE -ne 0) { throw "Could not install RoyaleBench dependencies." }

& $Python -m pip install -e (Join-Path $Upstream "python")
if ($LASTEXITCODE -ne 0) { throw "Could not install the pinned crforge-env Python package." }

$Install = Join-Path $Upstream "env\build\install\env"
$InstallLib = Join-Path $Install "lib"
$Jars = @(Get-ChildItem -Path $InstallLib -Filter "*.jar" -File -ErrorAction SilentlyContinue)
$Tables = Join-Path $HOME ".crforge\tables\16.635.8"
if (-not (Test-Path $Install) -or $Jars.Count -eq 0) {
    throw "CRForge env distribution is missing or has no JARs under $InstallLib"
}
if (-not (Test-Path $Tables)) { throw "CRForge game tables not found at $Tables" }

Write-Host ""
Write-Host "CRForge environment ready."
Write-Host "Install: $Install ($($Jars.Count) JAR files)"
Write-Host "Tables:  $Tables"
Write-Host "Next: .\scripts\validate_v1.ps1 -SkipBuild"
