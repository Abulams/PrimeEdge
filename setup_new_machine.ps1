# ==============================================================================
# Market-OS Automated Setup Script for New Machine / VPS
# ==============================================================================
# Run this in an Administrator PowerShell console on your new machine.
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    Market-OS New Machine Provisioning & Setup            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$targetDir = "C:\Market-OS"
if (!(Test-Path $targetDir)) {
    Write-Host "[INFO] Creating directory: $targetDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (!$pythonExe) {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.11 from https://www.python.org/downloads/windows/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add python.exe to PATH' during installation." -ForegroundColor Red
    exit 1
} else {
    $pyVer = python --version
    Write-Host "[OK] Found Python: $pyVer at $pythonExe" -ForegroundColor Green
}

Write-Host "`n[2/5] Creating directories..." -ForegroundColor Yellow
@("logs", "backups", "terminals", "backend", "worker") | ForEach-Object {
    $dir = Join-Path $targetDir $_
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "[OK] Directory structure ready." -ForegroundColor Green

Write-Host "`n[3/5] Installing Python packages..." -ForegroundColor Yellow
if (Test-Path "$targetDir\requirements_full.txt") {
    pip install -r "$targetDir\requirements_full.txt"
} elseif (Test-Path "$targetDir\backend\requirements.txt") {
    pip install -r "$targetDir\backend\requirements.txt"
    pip install metatrader5 psutil requests cryptography
} else {
    pip install fastapi uvicorn[standard] sqlalchemy pandas numpy pydantic pydantic-settings yfinance metatrader5 psutil requests cryptography
}
Write-Host "[OK] Python dependencies installed." -ForegroundColor Green

Write-Host "`n[4/5] Checking MetaTrader 5 base installation..." -ForegroundColor Yellow
$mt5Paths = @(
    "C:\Program Files\MetaTrader 5\terminal64.exe",
    "C:\Program Files (x86)\MetaTrader 5\terminal64.exe"
)
$mt5Found = $false
foreach ($p in $mt5Paths) {
    if (Test-Path $p) {
        Write-Host "[OK] Found MetaTrader 5 base terminal at: $p" -ForegroundColor Green
        $mt5Found = $true
        break
    }
}
if (!$mt5Found) {
    Write-Host "[NOTICE] MetaTrader 5 base terminal not found in default Program Files." -ForegroundColor Yellow
    Write-Host "Please download and install standard MT5 from your broker or MetaQuotes:" -ForegroundColor Yellow
    Write-Host "https://www.metatrader5.com/en/download" -ForegroundColor Cyan
}

Write-Host "`n[5/5] Checking configuration files..." -ForegroundColor Yellow
if (Test-Path "$targetDir\backend\market_os.db") {
    Write-Host "[OK] Database found: $targetDir\backend\market_os.db" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Database not found at $targetDir\backend\market_os.db!" -ForegroundColor Red
    Write-Host "Please copy market_os.db from your backup into $targetDir\backend\" -ForegroundColor Yellow
}

if (Test-Path "$targetDir\backend\.env") {
    Write-Host "[OK] Configuration (.env) found: $targetDir\backend\.env" -ForegroundColor Green
} else {
    Write-Host "[WARNING] .env not found at $targetDir\backend\.env!" -ForegroundColor Red
    Write-Host "Please copy .env from your backup into $targetDir\backend\" -ForegroundColor Yellow
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "Setup Completed! To start Market-OS supervisor, run:" -ForegroundColor Green
Write-Host "  python C:\Market-OS\watchdog.py" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
