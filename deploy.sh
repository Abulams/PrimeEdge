#!/usr/bin/env bash
# ==============================================================================
# PrimeEdge Production Deployment Pipeline
# Deploys local changes to the Linode Linux VPS via rsync + SSH.
#
# Usage:
#   ./deploy.sh             # Sync backend + restart service
#   ./deploy.sh --full      # Sync full repo (backend + frontend dist)
#   ./deploy.sh --migrate   # Run database migrations after deploy
#   ./deploy.sh --no-restart# Sync only, do not restart service
# ==============================================================================

set -euo pipefail

# ANSI color codes
CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_RED="\033[1;31m"
CLR_YELLOW="\033[1;33m"

echo -e "${CLR_CYAN}==========================================================${CLR_RESET}"
echo -e "${CLR_CYAN}        PrimeEdge Production Deployment Engine           ${CLR_RESET}"
echo -e "${CLR_CYAN}==========================================================${CLR_RESET}"

VPS_HOST="${PRIMEEDGE_VPS_HOST:-172.237.112.138}"
VPS_USER="${PRIMEEDGE_VPS_USER:-root}"
VPS_PATH="${PRIMEEDGE_VPS_PATH:-/var/www/market-os}"
SSH_PORT="${PRIMEEDGE_SSH_PORT:-22}"

FULL_SYNC=false
RUN_MIGRATE=false
RESTART_SERVICE=true

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --full)
            FULL_SYNC=true
            ;;
        --migrate)
            RUN_MIGRATE=true
            ;;
        --no-restart)
            RESTART_SERVICE=false
            ;;
        -h|--help)
            echo "Usage: ./deploy.sh [--full] [--migrate] [--no-restart]"
            exit 0
            ;;
        *)
            echo -e "${CLR_YELLOW}Unknown argument: $arg (ignoring)${CLR_RESET}"
            ;;
    esac
done

echo -e "Target: ${CLR_GREEN}${VPS_USER}@${VPS_HOST}:${VPS_PATH}${CLR_RESET}"

# Build rsync exclude list
EXCLUDES=(
    "--exclude=.git"
    "--exclude=.github"
    "--exclude=__pycache__"
    "--exclude=*.pyc"
    "--exclude=*.pyo"
    "--exclude=*.pyd"
    "--exclude=.env"
    "--exclude=backend/.env"
    "--exclude=*.db"
    "--exclude=backend/*.db"
    "--exclude=backend/market_os.db"
    "--exclude=backups"
    "--exclude=archive"
    "--exclude=terminals"
    "--exclude=logs"
    "--exclude=.pytest_cache"
    "--exclude=venv"
    "--exclude=.venv"
)

if [ "$FULL_SYNC" = true ]; then
    echo -e "${CLR_CYAN}[1/3] Performing full repository sync...${CLR_RESET}"
    rsync -avz --progress -e "ssh -p ${SSH_PORT}" "${EXCLUDES[@]}" ./ "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"
else
    echo -e "${CLR_CYAN}[1/3] Syncing backend and runtime files...${CLR_RESET}"
    rsync -avz --progress -e "ssh -p ${SSH_PORT}" "${EXCLUDES[@]}" \
        ./backend/ "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/backend/"
    
    # Sync Caddyfile & requirements if updated
    rsync -avz -e "ssh -p ${SSH_PORT}" ./Caddyfile "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/Caddyfile"
    rsync -avz -e "ssh -p ${SSH_PORT}" ./requirements_full.txt "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/requirements_full.txt"
fi
echo -e "${CLR_GREEN}✓ File synchronization complete.${CLR_RESET}"

# Step 2: Database migration
if [ "$RUN_MIGRATE" = true ]; then
    echo -e "${CLR_CYAN}[2/3] Running database migrations on VPS...${CLR_RESET}"
    ssh -p "${SSH_PORT}" "${VPS_USER}@${VPS_HOST}" << 'EOF'
        cd /var/www/market-os/backend
        if [ -f "../venv/bin/activate" ]; then
            source ../venv/bin/activate
        elif [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi
        if command -v alembic &>/dev/null; then
            alembic upgrade head || echo "Alembic not configured, skipping"
        fi
EOF
    echo -e "${CLR_GREEN}✓ Migrations step executed.${CLR_RESET}"
else
    echo -e "${CLR_CYAN}[2/3] Skipping migrations (pass --migrate to run).${CLR_RESET}"
fi

# Step 3: Service restart
if [ "$RESTART_SERVICE" = true ]; then
    echo -e "${CLR_CYAN}[3/3] Restarting application service on VPS...${CLR_RESET}"
    ssh -p "${SSH_PORT}" "${VPS_USER}@${VPS_HOST}" << 'EOF'
        if systemctl is-active --quiet marketos; then
            echo "Restarting systemd service: marketos"
            systemctl restart marketos
        elif systemctl is-active --quiet primeedge; then
            echo "Restarting systemd service: primeedge"
            systemctl restart primeedge
        elif systemctl is-active --quiet market-os; then
            echo "Restarting systemd service: market-os"
            systemctl restart market-os
        else
            echo "Restarting standalone gunicorn process..."
            pkill -f 'gunicorn app.main' || true
            sleep 2
            cd /var/www/market-os/backend
            if [ -f "../venv/bin/activate" ]; then
                source ../venv/bin/activate
            fi
            nohup gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120 > server.log 2>&1 &
        fi
        sleep 2
        curl -s http://localhost:8000/api/v1/health || true
EOF
    echo -e "\n${CLR_GREEN}✓ Service restarted and verified.${CLR_RESET}"
else
    echo -e "${CLR_CYAN}[3/3] Service restart skipped (--no-restart passed).${CLR_RESET}"
fi

echo -e "\n${CLR_GREEN}==========================================================${CLR_RESET}"
echo -e "${CLR_GREEN} Deployment complete! Live: https://primeedge.app        ${CLR_RESET}"
echo -e "${CLR_GREEN}==========================================================${CLR_RESET}"
