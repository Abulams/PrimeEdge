@echo off
title Market OS - Bloomberg Terminal x Quantitative Engine
echo ========================================================
echo   Starting Market OS Institutional Terminal in London
echo ========================================================
cd /d C:\Market-OS\backend
C:\Python311\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
