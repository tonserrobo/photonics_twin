# Keep this file ASCII-only: Windows PowerShell 5.1 decodes .ps1 as cp1252
# without a BOM, so stray UTF-8 punctuation breaks parsing.
#
# One-command Docker entry point. Builds and starts the compose stack, waits for
# the proxied health check, then opens the UI. Compose stays the single source of
# build and port config.
#
#   .\run.ps1                 # build + start + wait + open browser
#   .\run.ps1 -NoBuild        # start existing images only
#   .\run.ps1 -Logs           # follow logs
#   .\run.ps1 -Down           # stop and remove containers
[CmdletBinding()]
param(
    [string]$Tag,
    [switch]$Down,
    [switch]$Logs,
    [switch]$NoBuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot

try {
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker daemon is not running. Start Docker Desktop, then retry."
    }

    if ($Tag) { $env:TAG = $Tag }

    if ($Down) {
        & docker compose down
        if ($LASTEXITCODE -ne 0) { throw "docker compose down failed" }
        Write-Host "Photonics Twin stopped." -ForegroundColor Cyan
        return
    }

    if ($Logs) {
        & docker compose logs -f
        return
    }

    $upArgs = @('compose', 'up', '-d')
    if (-not $NoBuild) { $upArgs += '--build' }

    Write-Host "Starting photonics-twin..." -ForegroundColor Cyan
    & docker @upArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    $url = 'http://localhost:5173'
    $healthy = $false
    foreach ($i in 1..60) {
        try {
            Invoke-RestMethod "$url/healthz" -TimeoutSec 2 | Out-Null
            $healthy = $true
            break
        }
        catch { Start-Sleep -Seconds 2 }
    }

    if (-not $healthy) {
        & docker compose ps
        throw "Stack did not become healthy at $url/healthz. Run .\run.ps1 -Logs for details."
    }

    Write-Host "Photonics Twin is running at $url" -ForegroundColor Green
    Write-Host "Stop with .\run.ps1 -Down; follow logs with .\run.ps1 -Logs." -ForegroundColor DarkGray

    if (-not $NoBrowser) { Start-Process $url }
}
finally {
    Remove-Item Env:\TAG -ErrorAction SilentlyContinue
    Pop-Location
}
