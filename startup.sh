#!/bin/bash
# Market OS Azure App Service Startup Script

cd /home/site/wwwroot

# Install Python dependencies with error handling
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "Failed to install Python dependencies"
    exit 1
fi

# Ensure Stripe is installed
echo "Ensuring Stripe is installed..."
pip install stripe --quiet

# Skip frontend build (already done in deployment workflow)
# Frontend is already built and copied to backend/static/

# Start the FastAPI server
echo "Starting FastAPI server..."
cd backend
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120 --access-logfile '-' --error-logfile '-'
