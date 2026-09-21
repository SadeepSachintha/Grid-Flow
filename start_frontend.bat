@echo off
title GridFlow Vue 3 SCADA Dashboard [Port 5173]
echo =====================================================================
echo         GRIDFLOW: VUE 3 + VITE SCADA OPERATOR DASHBOARD
echo =====================================================================
cd /d "%~dp0frontend"
echo Starting Vite dev server on http://localhost:5173 ...
npm.cmd run dev
pause
