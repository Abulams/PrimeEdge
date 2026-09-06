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

# 1. Kill any existing instances on port 8000 & stale worker processes
Write-Host '[1/3] Checking port 8000 and stale workers...' -ForegroundColor Yellow
$portProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portProcess) {
    Write-Host ('Stopping existing process on port 8000 (PID: ' + $portProcess.OwningProcess + ')...') -ForegroundColor DarkYellow
    Stop-Process -Id $portProcess.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "marketos_worker.py" } | ForEach-Object {
    Write-Host ("Stopping stale worker process (PID: $($_.ProcessId))...") -ForegroundColor DarkYellow
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# 2. Start FastAPI Production Backend
Write-Host '[2/3] Launching FastAPI Backend on port 8000...' -ForegroundColor Yellow
$BackendVenv = Join-Path $RootPath 'backend\venv\Scripts\uvicorn.exe'
if (-not (Test-Path $BackendVenv)) { $BackendVenv = 'uvicorn' }

$BackendProcess = Start-Process -FilePath $BackendVenv `
    -ArgumentList 'app.main:app', '--host', '0.0.0.0', '--port', '8000' `
    -WorkingDirectory (Join-Path $RootPath 'backend') `
    -PassThru -WindowStyle Minimized

Write-Host ('  -> Backend launched with PID: ' + $BackendProcess.Id) -ForegroundColor Green

# Wait for backend to be healthy
Write-Host 'Verifying backend health...' -ForegroundColor Yellow
$Healthy = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/auth/me' -Method Get -ErrorAction SilentlyContinue | Out-Null
        $Healthy = $true; break
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 401) { $Healthy = $true; break }
        Start-Sleep -Seconds 1
    }
}
if ($Healthy) {
    Write-Host '  -> Backend is healthy and responding!' -ForegroundColor Green
} else {
    Write-Host '  -> Warning: Backend health check timed out, proceeding anyway...' -ForegroundColor DarkYellow
}

# 3. Start 24/7 Cloud MT5 Worker Daemon
Write-Host '[3/3] Launching Market OS Cloud MT5 Worker Service...' -ForegroundColor Yellow
$WorkerLog = Join-Path $RootPath 'worker.log'
$WorkerErr = Join-Path $RootPath 'worker_err.log'
$PythonExe = 'C:\Python311\python.exe'
if (-not (Test-Path $PythonExe)) { $PythonExe = 'python' }

$WorkerProcess = Start-Process -FilePath $PythonExe `
    -ArgumentList (Join-Path $RootPath 'worker\marketos_worker.py') `
    -WorkingDirectory (Join-Path $RootPath 'worker') `
    -RedirectStandardOutput $WorkerLog `
    -RedirectStandardError $WorkerErr `
    -PassThru -WindowStyle Minimized

Write-Host ('  -> Worker daemon launched with PID: ' + $WorkerProcess.Id) -ForegroundColor Green

Write-Host '=====================================================' -ForegroundColor Green
Write-Host '  MARKET OS IS LIVE AT:' -ForegroundColor Green
Write-Host '  http://51.105.32.248:8000' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Green
Write-Host 'Services running in background.' -ForegroundColor Gray
