@echo off
title GridFlow Automated Test Suite
echo =====================================================================
echo               GRIDFLOW: FULL AUTOMATED TEST SUITE
echo =====================================================================
echo Running 34 unit tests across all 10 engineering modules...
python -m unittest discover stream_engine/tests -v
echo.
echo =====================================================================
pause
