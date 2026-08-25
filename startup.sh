#!/bin/bash
# Market OS Azure App Service Startup Script

cd /home/site/wwwroot

# Install Python dependencies
pip install -r backend/requirements.txt

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Start the FastAPI server
cd backend
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120 --access-logfile '-' --error-logfile '-'
