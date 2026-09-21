@echo off
title GridFlow Laravel 12 Backend [Port 8080]
echo =====================================================================
echo           GRIDFLOW: LARAVEL 12 CMMS & SCADA BACKEND
echo =====================================================================
cd /d "%~dp0backend"
echo Starting php artisan serve on http://127.0.0.1:8080 ...
php artisan serve --port 8080
pause
