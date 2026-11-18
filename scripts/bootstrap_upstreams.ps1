$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

git submodule sync --recursive
if ($LASTEXITCODE -ne 0) { throw "git submodule sync failed" }

git submodule update --init --recursive
if ($LASTEXITCODE -ne 0) { throw "git submodule update failed" }

$Pins = @(
    @{ Path = "third_party/upstream/crforge"; Sha = "fa5959055c590a493d62c8dbc804e602832d08a6" },
    @{ Path = "third_party/upstream/royalegym"; Sha = "278bcb06dae717b89194b992235a9fa8a5209084" },
    @{ Path = "third_party/upstream/royalesim"; Sha = "a849c29ae632e12f81442c45b0d9b2f2f99f15" }
)

foreach ($Pin in $Pins) {
    if (-not (Test-Path $Pin.Path)) {
        throw "Submodule path missing: $($Pin.Path)"
    }
    $Actual = (git -C $Pin.Path rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Could not read submodule revision: $($Pin.Path)" }
    if ($Actual -ne $Pin.Sha) {
        throw "$($Pin.Path) is at $Actual; expected pinned revision $($Pin.Sha)"
    }
    Write-Host "OK: $($Pin.Path) @ $Actual"
}

Write-Host "All upstream source pins verified."
