@echo off
title GANN-ASTRO v3.9 -- Schedule Daily 9:00 PM Update
cd /d "%~dp0"

echo ============================================================
echo   GANN-ASTRO v3.9 -- Automated Daily Scheduler Setup
echo ============================================================
echo.
echo  Configuring Windows Task Scheduler to run daily at 9:00 PM IST...
echo  (If your computer is OFF at 9:00 PM, it will automatically
echo   catch up as soon as you turn your computer back ON)
echo.

:: Detect Python executable path
for /f "tokens=*" %%p in ('where python') do (
    set PY_EXE=%%p
    goto :found_py
)

:found_py
if "%PY_EXE%"=="" (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

echo [OK] Using Python: %PY_EXE%
echo [OK] Target Script: %CD%\update_all.py

:: Use PowerShell to register task with missed-schedule catch-up enabled
powershell -NoProfile -ExecutionPolicy Bypass -Command "$action = New-ScheduledTaskAction -Execute '%PY_EXE%' -Argument 'update_all.py' -WorkingDirectory '%CD%'; $trigger = New-ScheduledTaskTrigger -Daily -At 9:00PM; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; Register-ScheduledTask -TaskName 'GANN-ASTRO-Daily-Update' -Action $action -Trigger $trigger -Settings $settings -Force"

if errorlevel 1 (
    echo [WARN] PowerShell registration failed. Trying schtasks fallback...
    schtasks /create /tn "GANN-ASTRO-Daily-Update" /tr "cmd.exe /c cd /d \"%CD%\" && \"%PY_EXE%\" update_all.py" /sc daily /st 21:00 /f
)

echo.
echo ============================================================
echo   [SUCCESS] Daily 9:00 PM IST Task Successfully Scheduled!
echo ============================================================
echo.
echo  Task Name  : GANN-ASTRO-Daily-Update
echo  Frequency  : Daily at 9:00 PM (21:00 IST)
echo  Catch-Up   : Enabled (runs immediately if laptop was OFF)
echo.
echo  To view or edit the task anytime:
echo    1. Press Win + R
echo    2. Type taskschd.msc and press Enter
echo.
if /i "%1"=="--silent" goto :skip_pause
if /i "%1"=="/silent" goto :skip_pause
pause
:skip_pause
