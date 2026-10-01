# Build-green is not run-green: the materials-path bug passed every build and only
# surfaced on a real /simulate call. This drives the stack through nginx, as the UI does.
$ErrorActionPreference = 'Stop'

function Fail($msg) { Write-Host "FAIL: $msg" -ForegroundColor Red; docker compose logs --tail=30; docker compose down -v *>$null; exit 1 }

docker compose build
if ($LASTEXITCODE -ne 0) { Fail "compose build" }

try {
    # Frontend alone, no backend to resolve. nginx used to die here with "host not
    # found in upstream", killing the static UI too. It must boot and serve the UI,
    # degrading only the proxied routes.
    docker compose up -d --no-deps frontend
    $solo = $false
    foreach ($i in 1..20) {
        # -UseBasicParsing is required on Windows PowerShell 5.1: the default HTML
        # parser needs Internet Explorer, which no longer exists on Windows 11.
        try { Invoke-WebRequest http://localhost:5173/ -UseBasicParsing -TimeoutSec 2 | Out-Null; $solo = $true; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $solo) { Fail "nginx did not serve the UI without a backend" }

    try {
        Invoke-WebRequest http://localhost:5173/healthz -UseBasicParsing -TimeoutSec 5 | Out-Null
        Fail "expected /healthz to fail with no backend running"
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -ne 502 -and $code -ne 504) { Fail "expected 502/504 with no backend, got '$code'" }
    }
    Write-Host "  ok: nginx survives a missing backend" -ForegroundColor DarkGray

    docker compose up -d
    if ($LASTEXITCODE -ne 0) { Fail "compose up" }

    # compose gates on the backend healthcheck; nginx still needs a moment to bind.
    $up = $false
    foreach ($i in 1..30) {
        try { Invoke-RestMethod http://localhost:5173/healthz -TimeoutSec 2 | Out-Null; $up = $true; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $up) { Fail "healthz never came up" }

    # The real check: a simulation that must load data/materials/*.json.
    $payload = @{
        component = 'bragg_grating'
        params    = @{ material_high = 'Si'; material_low = 'SiO2'; centre_nm = 1550; periods = 10 }
        sweep     = @{ start_nm = 1400; stop_nm = 1700; n_points = 11 }
    } | ConvertTo-Json

    $res = Invoke-RestMethod -Uri http://localhost:5173/simulate/tmm/sweep -Method Post `
        -ContentType 'application/json' -Body $payload
    if (-not $res.reflectance) { Fail "simulate returned no reflectance" }

    # WebSocket is the UI's live path, and uvicorn[standard] is now its only ws provider
    # since the image stopped installing dev extras. ClientWebSocket ships with PS7.
    $ws  = [System.Net.WebSockets.ClientWebSocket]::new()
    $cts = [System.Threading.CancellationTokenSource]::new(10000)
    $ws.ConnectAsync('ws://localhost:5173/ws/sim?component=bragg_grating', $cts.Token).Wait()

    $msg = (@{ type = 'simulate'; params = $payload | ConvertFrom-Json | ForEach-Object { $_.params }
               sweep = $payload | ConvertFrom-Json | ForEach-Object { $_.sweep } } | ConvertTo-Json -Depth 5)
    $out = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($out), 'Text', $true, $cts.Token).Wait()

    $buf  = [byte[]]::new(1MB)
    $recv = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $recv.Wait()
    $reply = [System.Text.Encoding]::UTF8.GetString($buf, 0, $recv.Result.Count)
    if ($reply -notmatch '"reflectance"') { Fail "websocket reply had no reflectance: $reply" }
    $ws.Dispose()

    # UI must actually be served, not just the proxied endpoints.
    if ((Invoke-WebRequest http://localhost:5173/ -UseBasicParsing).Content -notmatch 'id="root"') { Fail "UI not served" }

    Write-Host "PASS: healthz, simulate (materials loaded), websocket, UI served" -ForegroundColor Green
}
finally { docker compose down -v *>$null }
