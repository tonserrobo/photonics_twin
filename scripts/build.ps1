# Keep this file ASCII-only: without a BOM, Windows PowerShell 5.1 decodes .ps1 as
# cp1252, so a stray UTF-8 dash or quote becomes mojibake and fails to parse.
#
# Thin wrapper over `docker compose build`. The build context and Dockerfile paths
# stay defined once, in docker-compose.yml. This only adds the version tag and a
# summary, so there is no second copy of the build config to drift.
#
#   .\scripts\build.ps1                    # both images, tagged from pyproject.toml
#   .\scripts\build.ps1 -Service backend   # just one
#   .\scripts\build.ps1 -Tag dev -Smoke    # custom tag, then run the smoke test
[CmdletBinding()]
param(
    [string]$Tag,
    [ValidateSet('all', 'backend', 'frontend')][string]$Service = 'all',
    [switch]$NoCache,
    [switch]$Smoke
)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)

try {
    if (-not $Tag) {
        # Anchored to line start so tool.scikit-build's `cmake.version` can't match.
        $m = Select-String -Path pyproject.toml -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
        if (-not $m) { throw "no [project] version found in pyproject.toml - pass -Tag explicitly" }
        $Tag = $m.Matches[0].Groups[1].Value
    }
    $env:TAG = $Tag
    Write-Host "Building photonics-twin images at tag '$Tag'" -ForegroundColor Cyan

    $buildArgs = @('compose', 'build')
    if ($NoCache) { $buildArgs += '--no-cache' }
    if ($Service -ne 'all') { $buildArgs += $Service }

    & docker @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose build failed" }

    # Also move :latest, so `docker compose up` and the smoke test work with TAG unset.
    foreach ($s in @('backend', 'frontend')) {
        if ($Service -ne 'all' -and $Service -ne $s) { continue }
        & docker tag "photonics-twin-${s}:$Tag" "photonics-twin-${s}:latest"
        if ($LASTEXITCODE -ne 0) { throw "failed to tag photonics-twin-${s}" }
    }

    Write-Host "`nImages:" -ForegroundColor Cyan
    & docker images --filter 'reference=photonics-twin-*' `
        --format '  {{.Repository}}:{{.Tag}}  {{.Size}}'

    if ($Smoke) {
        Write-Host "`nSmoke test:" -ForegroundColor Cyan
        & "$PSScriptRoot\smoke_docker.ps1"
        if ($LASTEXITCODE -ne 0) { throw "smoke test failed" }
    }
}
finally {
    Remove-Item Env:\TAG -ErrorAction SilentlyContinue
    Pop-Location
}
