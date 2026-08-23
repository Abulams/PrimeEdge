# ==============================================================================
# MARKET OS — Automatic Service Supervisor
# ==============================================================================
# Usage: powershell -ExecutionPolicy Bypass -File .\start_market_os.ps1
# ==============================================================================

$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootPath

Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host '  MARKET OS — Starting Core Services' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Cyan

# 1. Kill any existing instances on port 8000
Write-Host '
[1/3] Checking port 8000...' -ForegroundColor Yellow
$portProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portProcess) {
    Write-Host 'Stopping existing process on port 8000 (PID: ' $portProcess.OwningProcess ')...' -ForegroundColor DarkYellow
    Stop-Process -Id $portProcess.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 2. Start FastAPI Production Backend
Write-Host '[2/3] Launching FastAPI Backend on port 8000...' -ForegroundColor Yellow
$BackendVenv = Join-Path $RootPath 'backend\venv\Scripts\uvicorn.exe'
if (-not (Test-Path $BackendVenv)) {
    $BackendVenv = 'uvicorn'
}

$BackendProcess = Start-Process -FilePath $BackendVenv 
    -ArgumentList 'app.main:app', '--host', '0.0.0.0', '--port', '8000' 
    -WorkingDirectory (Join-Path $RootPath 'backend') 
    -PassThru 
    -WindowStyle Minimized

Write-Host '  -> Backend launched with PID: ' $BackendProcess.Id -ForegroundColor Green

# 3. Wait for backend to be healthy
Write-Host '
Verifying backend health...' -ForegroundColor Yellow
$Healthy = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $res = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/auth/me' -Method Get -ErrorAction SilentlyContinue
        $Healthy = $true
        break
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 401) {
            $Healthy = $true
            break
        }
        Start-Sleep -Seconds 1
    }
}

if ($Healthy) {
    Write-Host '  -> Backend is healthy and responding!' -ForegroundColor Green
} else {
    Write-Host '  -> Warning: Backend health check timed out, proceeding anyway...' -ForegroundColor DarkYellow
}

# 4. Start Cloudflare Tunnel
Write-Host '
[3/3] Launching Cloudflare Tunnel on port 8000...' -ForegroundColor Yellow
$TunnelLog = Join-Path $RootPath 'tunnel.log'

$TunnelProcess = Start-Process -FilePath 'npx.cmd' 
    -ArgumentList '--yes', 'cloudflared', 'tunnel', '--url', 'http://localhost:8000' 
    -WorkingDirectory $RootPath 
    -RedirectStandardOutput $TunnelLog 
    -RedirectStandardError $TunnelLog 
    -PassThru 
    -WindowStyle Minimized

Write-Host '  -> Tunnel process started (PID: ' $TunnelProcess.Id ')' -ForegroundColor Green
Write-Host '  -> Waiting for public URL...' -ForegroundColor Yellow

Start-Sleep -Seconds 8

$UrlFound = $false
for ($j = 0; $j -lt 15; $j++) {
    if (Test-Path $TunnelLog) {
        $logContent = Get-Content $TunnelLog -Raw -ErrorAction SilentlyContinue
        if ($logContent -match 'https://[a-zA-Z0-9-]+\.trycloudflare\.com') {
            $publicUrl = $matches[0]
            Write-Host '
=====================================================' -ForegroundColor Green
            Write-Host '  MARKET OS IS LIVE AT:' -ForegroundColor Green
            Write-Host ('  ' + $publicUrl) -ForegroundColor Cyan
            Write-Host '=====================================================' -ForegroundColor Green
            $UrlFound = $true
            break
        }
    }
    Start-Sleep -Seconds 2
}

if (-not $UrlFound) {
    Write-Host '  -> Check ' $TunnelLog ' for your tunnel URL.' -ForegroundColor Yellow
}

Write-Host '
Services running in background.' -ForegroundColor Gray
