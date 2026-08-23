@echo off
title GANN-ASTRO v3.9
cd /d "%~dp0"

echo.
echo ============================================================
echo   GANN-ASTRO v3.9 -- NSE/BSE/MCX Trading Intelligence
echo ============================================================
echo.

:: ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    echo         Make sure "Add Python to PATH" is ticked during install.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: ── Clear stale Python cache ──────────────────────────────────────────────────
echo.
echo [SETUP] Clearing Python cache...
if exist __pycache__ rmdir /s /q __pycache__
if exist pages\__pycache__ rmdir /s /q pages\__pycache__
if exist core\__pycache__ rmdir /s /q core\__pycache__
if exist data\__pycache__ rmdir /s /q data\__pycache__
echo [OK] Cache cleared

:: ── Install / verify dependencies ────────────────────────────────────────────
echo.
echo [SETUP] Checking dependencies...
python -m pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo [WARN] pip install had warnings - continuing anyway
)
echo [OK] Dependencies ready

:: ── Check for market_data.db ─────────────────────────────────────────────────
echo.
if exist market_data.db (
    echo [OK] market_data.db found - your historical data will be loaded
) else (
    echo [INFO] No market_data.db found - a fresh database will be created
    echo        Run download_history.py after startup to fetch historical prices
)

:: ── Kill anything already on port 5050 (just in case) ────────────────────────
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5050 ^| findstr LISTENING') do (
    echo [SETUP] Killing process %%p on port 5050...
    taskkill /PID %%p /F >nul 2>&1
)

:: ── Run Automated Daily Updates (BACKGROUND) ─────────────────────────────────
echo.
echo [SETUP] Launching automated daily updates in the background...
echo         (A minimized window will open for the update and close when finished)
start "GANN-ASTRO Background Update" /MIN /LOW cmd /c "python update_all.py & echo. & echo Update Complete! & timeout 5"

:: ── Run OI Scraper (after market close snapshot) ───────────────────────────
echo [SETUP] Launching OI scraper in background (NSE option chain data)...
start "GANN-ASTRO OI Scraper" /MIN /LOW cmd /c "timeout 30 & python scrape_oi.py & echo. & echo OI Scrape Complete! & timeout 5"


:: ── Set port (avoids conflict with port 8080) ────────────────────────────────
set GANN_PORT=5050

echo.
echo [START] Launching GANN-ASTRO at http://localhost:5050
echo         ML model will auto-train in background (~60-90s after start)
echo         Press Ctrl+C to stop the server
echo.

:: Open a fresh browser window via PowerShell after 6 seconds
start "" powershell -WindowStyle Hidden -Command "Start-Sleep 6; Start-Process 'http://localhost:5050'"

:: ── Start server ─────────────────────────────────────────────────────────────
python app.py

:: If we get here the server stopped
echo.
echo [STOP] Server stopped.
pause