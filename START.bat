@echo off
title GANN-ASTRO v3.9 – One-Click Starter
setlocal EnableDelayedExpansion

:: --------------------------------------------------------------
:: 0️⃣  Basic sanity checks
:: --------------------------------------------------------------
cd /d "%~dp0"

:: Ensure we are running from a user-writable folder
if not "%~dp0"=="%USERPROFILE%\" (
    echo [INFO] It is recommended to extract the package into a folder you own (e.g., %USERPROFILE%\VProfitables) for write permissions.
)

:: --------------------------------------------------------------
:: 1️⃣  Portable Python detection
:: --------------------------------------------------------------
if exist python\python.exe (
    set PYEXE=python\python.exe
) else (
    echo [ERROR] Portable Python not found. Please re-download the full package which includes the embedded Python interpreter.
    pause
    exit /b 1
)

:: --------------------------------------------------------------
:: 2️⃣  Install Visual C++ Runtime if missing
:: --------------------------------------------------------------
where vcruntime140.dll >nul 2>&1
if errorlevel 1 (
    if exist vc_redist.x64.exe (
        echo [SETUP] Installing Visual C++ 2015-2022 Redistributable...
        vc_redist.x64.exe /quiet /norestart
    ) else (
        echo [WARN] VC++ runtime not found and installer missing. Some packages may fail to import.
    )
)

:: --------------------------------------------------------------
:: 3️⃣  Detect internet connectivity
:: --------------------------------------------------------------
set OFFLINE=0
ping -n 1 8.8.8.8 >nul 2>&1
if errorlevel 1 set OFFLINE=1

:: --------------------------------------------------------------
:: 4️⃣  Install Python dependencies from offline wheel cache
:: --------------------------------------------------------------
echo [SETUP] Installing Python dependencies (offline)...
%PYEXE% -m pip install --no-index --find-links=wheels -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check logs.
    pause
    exit /b 1
)

:: --------------------------------------------------------------
:: 5️⃣  Download ML models if missing and we have internet
:: --------------------------------------------------------------
if not exist models\direction_model.pkl (
    if "%OFFLINE%"=="0" (
        echo [SETUP] Downloading ML models from CDN...
        %PYEXE% download_models.py
        if errorlevel 1 (
            echo [ERROR] Model download failed.
            pause
            exit /b 1
        )
    ) else (
        echo [WARN] Offline mode – stub models will be used (functionality limited).
    )
)

:: --------------------------------------------------------------
:: 6️⃣  Ensure SQLite database exists
:: --------------------------------------------------------------
if not exist market_data_v2.db (
    echo [SETUP] Creating fresh SQLite database...
    %PYEXE% -c "from core.paths import initialize_database; initialize_database()"
)

:: --------------------------------------------------------------
:: 7️⃣  Optional cloud sync (only if online)
:: --------------------------------------------------------------
if "%OFFLINE%"=="0" (
    echo [SETUP] Pulling latest market_data_v2.db from cloud...
    %PYEXE% cloud_sync.py --download
)

:: --------------------------------------------------------------
:: 8️⃣  Find a free port (5050-5060)
:: --------------------------------------------------------------
set PORT=5050
:PORTCHK
netstat -ano | findstr :!PORT! >nul 2>&1
if not errorlevel 1 (
    set /a PORT+=1
    if !PORT! leq 5060 goto PORTCHK
    echo [ERROR] No free port available between 5050-5060.
    pause
    exit /b 1
)
set GANN_PORT=!PORT!

:: --------------------------------------------------------------
:: 9️⃣  Register Windows Scheduler (user context fallback)
:: --------------------------------------------------------------
schtasks /query /tn "GANN-ASTRO-Daily-Update" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Registering daily 9:00 PM IST update task...
    call setup_scheduler.bat --silent
    if errorlevel 1 (
        echo [WARN] Could not create Windows scheduled task. A background updater will run instead.
    )
) else (
    echo [OK] Daily scheduler already present.
)

:: --------------------------------------------------------------
:: 🔟  Quick sanity‑check of the AI engine
:: --------------------------------------------------------------
%PYEXE% run_daily_tracker_desk.py --quick-check
if errorlevel 1 (
    echo [ERROR] Engine sanity check failed. See logs.
    pause
    exit /b 1
)

:: --------------------------------------------------------------
:: 1️⃣1️⃣ Launch background daily‑update & OI scraper
:: --------------------------------------------------------------
start "GANN-ASTRO Background Update" /MIN cmd /c "timeout 20 & %PYEXE% update_all.py"
start "GANN-ASTRO OI Scraper" /MIN cmd /c "timeout 30 & %PYEXE% scrape_oi.py"

:: --------------------------------------------------------------
:: 1️⃣2️⃣ Verify frontend JavaScript integrity
:: --------------------------------------------------------------
%PYEXE% -X utf8 tests\test_js_integrity.py
if errorlevel 1 (
    echo [ERROR] Frontend script syntax error detected!
    pause
    exit /b 1
)

:: --------------------------------------------------------------
:: 1️⃣3️⃣ Open browser after brief delay
:: --------------------------------------------------------------
start "" "http://localhost:!GANN_PORT!"

:: --------------------------------------------------------------
:: 1️⃣4️⃣ Start the server
:: --------------------------------------------------------------
echo [START] Launching GANN‑ASTRO on http://localhost:!GANN_PORT!
%PYEXE% -X utf8 app.py

:: --------------------------------------------------------------
:: If we get here the server stopped
:: --------------------------------------------------------------
echo [STOP] Server stopped.
pause