# ==============================================================================
# PrimeEdge VPS Deployment Script (PowerShell)
# Transfers updated engine files and rebuilt signatures to Linode VPS
# ==============================================================================

param(
    [string]$HostIP = "172.237.112.138",
    [string]$User = "root",
    [string]$RemoteDir = "/var/www/market-os"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PrimeEdge VPS Deployment: Deploying Fixed Engine & DB  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target: $User@$HostIP : $RemoteDir" -ForegroundColor Yellow

$SourceBase = "C:\Market-OS-Recovered\Market-OS"

# 1. Test SSH Connection
Write-Host "`n[Step 1/4] Testing SSH Connectivity..." -ForegroundColor Green
$sshTest = ssh -o ConnectTimeout=5 "$User@$HostIP" "echo CONNECTION_OK" 2>$null
if ($sshTest -match "CONNECTION_OK") {
    Write-Host "SSH connection established successfully!" -ForegroundColor Green
} else {
    Write-Host "Password prompt or key authentication required." -ForegroundColor Yellow
}

# 2. Upload Core Modified Engine Files
Write-Host "`n[Step 2/4] Uploading updated Python engine and signature builder..." -ForegroundColor Green
scp "$SourceBase\backend\app\signature_builder.py" "$User@$HostIP`:$RemoteDir/backend/app/signature_builder.py"
scp "$SourceBase\backend\app\engine.py" "$User@$HostIP`:$RemoteDir/backend/app/engine.py"
scp "$SourceBase\backend\app\main.py" "$User@$HostIP`:$RemoteDir/backend/app/main.py"

# 3. Upload Re-Anchored Database
Write-Host "`n[Step 3/4] Uploading re-anchored MarketSignature database..." -ForegroundColor Green
scp "$SourceBase\backups\market_os_backup_20260927_224911.db" "$User@$HostIP`:$RemoteDir/backend/market_os.db"

# 4. Restart Services on VPS
Write-Host "`n[Step 4/4] Restarting FastAPI / Gunicorn service on Linode VPS..." -ForegroundColor Green
ssh "$User@$HostIP" @"
    if systemctl is-active --quiet marketos; then
        echo 'Restarting marketos systemd service...'
        systemctl restart marketos
    elif systemctl is-active --quiet primeedge; then
        echo 'Restarting primeedge systemd service...'
        systemctl restart primeedge
    elif docker ps -q --filter 'name=market-os' | grep -q .; then
        echo 'Restarting market-os Docker container...'
        docker restart market-os
    else
        echo 'Restarting via pkill gunicorn/uvicorn...'
        pkill -f 'uvicorn app.main' || true
        pkill -f 'gunicorn app.main' || true
        sleep 2
        cd $RemoteDir/backend && nohup gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120 > server.log 2>&1 &
    fi
    echo 'Remote deployment complete! Verifying status...'
    curl -s http://localhost:8000/api/v1/dashboard/watchlist | head -c 200 || true
"@

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  Deployment finished! Refresh https://primeedge.app now! " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
