# Market OS Windows VPS 1-Click Setup Script
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Market OS Cloud MT5 Worker Setup (VPS) " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Verify Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python 3.11+ is required. Please install Python." -ForegroundColor Red
    Exit 1
}

# 2. Install requirements
Write-Host "[1/3] Installing worker dependencies..." -ForegroundColor Yellow
pip install psutil requests MetaTrader5 cryptography --quiet

# 3. Environment configuration
Write-Host "[2/3] Configuring worker environment..." -ForegroundColor Yellow
$env:WORKER_ID = "vps-lon-worker-1"
$env:WORKER_KEY = "wkey_master_cloud_london"
$env:MARKETOS_CLOUD_URL = "http://127.0.0.1:8000"

# 4. Launch worker service
Write-Host "[3/3] Launching Market OS Cloud Worker..." -ForegroundColor Green
python marketos_worker.py

