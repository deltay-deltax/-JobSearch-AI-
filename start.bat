@echo off
echo ========================================================
echo   Starting JobSearch AI (Backend + Frontend)
echo ========================================================

start "JobSearch AI - FastAPI Backend" cmd /k "python -m src.api.main"
start "JobSearch AI - React Frontend" cmd /k "npm --prefix frontend run dev"

echo.
echo Both servers are launching:
echo   - Backend API: http://localhost:8000 (Swagger docs at /docs)
echo   - Frontend UI: http://localhost:5173
echo.
echo Press any key to close this launcher window...
pause >nul
