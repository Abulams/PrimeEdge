#!/bin/bash
# ==============================================================================
# PrimeEdge VPS In-Place Deploy & Restart Script (Run on VPS)
# ==============================================================================

set -e

APP_DIR="${1:-/var/www/market-os}"

echo "=========================================================="
echo "  PrimeEdge Local VPS Rebuild & Service Restart Engine   "
echo "=========================================================="
echo "Target directory: $APP_DIR"

cd "$APP_DIR/backend"

# 1. Restart Service
if systemctl is-active --quiet marketos; then
    echo "Restarting marketos systemd service..."
    sudo systemctl restart marketos
elif systemctl is-active --quiet primeedge; then
    echo "Restarting primeedge systemd service..."
    sudo systemctl restart primeedge
elif systemctl is-active --quiet market-os; then
    echo "Restarting market-os systemd service..."
    sudo systemctl restart market-os
else
    echo "Restarting Gunicorn / Uvicorn processes..."
    pkill -f 'uvicorn app.main' || true
    pkill -f 'gunicorn app.main' || true
    sleep 2
    nohup gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120 > server.log 2>&1 &
fi

echo "Verifying local API response..."
sleep 3
curl -s http://localhost:8000/api/v1/dashboard/watchlist | head -c 250 || true
echo -e "\nServer successfully restarted with updated PrimeEdge engine!"
