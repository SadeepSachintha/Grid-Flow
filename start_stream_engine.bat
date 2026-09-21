@echo off
title GridFlow Stream Engine & ML API [Port 8000]
echo =====================================================================
echo      GRIDFLOW: PYTHON FASTAPI STREAM ENGINE & ML INFERENCE
echo =====================================================================
echo Starting uvicorn on http://127.0.0.1:8000 ...
python -m uvicorn stream_engine.api:app --host 127.0.0.1 --port 8000 --reload
pause
