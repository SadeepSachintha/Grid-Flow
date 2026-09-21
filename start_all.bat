@echo off
title GridFlow Microgrid Platform - Master Launcher
echo =====================================================================
echo           GRIDFLOW: SMART GRID & RENEWABLE ENERGY PLATFORM
echo                     Master System Launcher
echo =====================================================================
echo.
echo [1/3] Starting Python Stream & ML Inference Engine (Port 8000)...
start "GridFlow Stream Engine [Port 8000]" cmd /k "python -m uvicorn stream_engine.api:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/3] Starting Laravel 12 CMMS Backend (Port 8080)...
start "GridFlow Laravel Backend [Port 8080]" cmd /k "cd /d backend && php artisan serve --port 8080"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Vue 3 SCADA Dashboard (Port 5173)...
start "GridFlow SCADA Frontend [Port 5173]" cmd /k "cd /d frontend && npm.cmd run dev"

timeout /t 3 /nobreak >nul

echo.
echo =====================================================================
echo All services launched!
echo - SCADA UI:       http://localhost:5173
echo - Stream API:     http://localhost:8000/docs
echo - Laravel API:    http://localhost:8080/api/plants
echo =====================================================================
echo Opening SCADA Dashboard in default browser...
start http://localhost:5173
pause
