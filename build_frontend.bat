@echo off
title GridFlow Frontend Production Build
echo =====================================================================
echo              GRIDFLOW: FRONTEND PRODUCTION BUNDLE BUILD
echo =====================================================================
cd /d "%~dp0frontend"
npm.cmd run build
echo.
echo =====================================================================
pause
