@echo off
title Market OS Production Server
cd /d %~dp0
start "Market OS Web API" "C:\Python311\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak >nul
start "Market OS MT5 Bridge" "C:\Python311\python.exe" app/execution/cloud_mt5_bridge.py
echo Services running! Open http://51.105.32.248:8000
