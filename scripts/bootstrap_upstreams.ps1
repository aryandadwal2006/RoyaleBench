$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

git submodule sync --recursive
if ($LASTEXITCODE -ne 0) { throw "git submodule sync failed" }

git submodule update --init --recursive
if ($LASTEXITCODE -ne 0) { throw "git submodule update failed" }

$Submodules = @(
    "third_party/upstream/crforge",
    "third_party/upstream/royalegym",
    "third_party/upstream/royalesim"
)

foreach ($SubmodulePath in $Submodules) {
    if (-not (Test-Path $SubmodulePath)) {
        throw "Submodule path missing: $SubmodulePath"
    }

    # Read the expected object ID from the superproject's gitlink. This is the
    # authoritative pin and avoids duplicating commit IDs in this script.
    $GitlinkLine = & git ls-tree HEAD -- $SubmodulePath
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read the pinned gitlink for $SubmodulePath"
    }
    $GitlinkText = [string]($GitlinkLine | Select-Object -Last 1)
    $GitlinkMatch = [regex]::Match($GitlinkText, '^160000 commit (?<sha>[0-9a-fA-F]{40})\s')
    if (-not $GitlinkMatch.Success) {
        throw "No submodule commit pin found in HEAD for $SubmodulePath. Git returned: '$GitlinkText'"
    }
    $ExpectedSha = $GitlinkMatch.Groups['sha'].Value.ToLowerInvariant()

    $RevisionOutput = & git -C $SubmodulePath rev-parse --verify 'HEAD^{commit}'
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read submodule revision: $SubmodulePath"
    }
    $ActualSha = [string]($RevisionOutput | Select-Object -Last 1)
    $ActualSha = $ActualSha.Trim().ToLowerInvariant()
    if ($ActualSha -notmatch '^[0-9a-f]{40}$') {
        throw "Invalid revision returned for $SubmodulePath: '$ActualSha' (length $($ActualSha.Length))"
    }

    if (-not [string]::Equals($ActualSha, $ExpectedSha, [System.StringComparison]::Ordinal)) {
        throw "$SubmodulePath is at '$ActualSha'; the superproject pins '$ExpectedSha'. Run git submodule update --init --recursive."
    }
    Write-Host "OK: $SubmodulePath @ $ActualSha"
}
Write-Host "All upstream source pins verified."
