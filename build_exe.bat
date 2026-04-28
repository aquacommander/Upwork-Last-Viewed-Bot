@echo off
setlocal enabledelayedexpansion
title Upwork Monitor - EXE Builder

echo.
echo ============================================================
echo   Upwork Monitor ^| EXE Builder
echo ============================================================
echo.

:: ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Download from https://www.python.org/downloads/
    echo         Make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found.

:: ── Upgrade pip silently ────────────────────────────────────
echo [..] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: ── Install all required packages ───────────────────────────
echo [..] Installing packages (this may take a minute)...
pip install ^
    selenium==4.20.0 ^
    webdriver-manager==4.0.1 ^
    pystray==0.19.5 ^
    Pillow==10.3.0 ^
    plyer==2.1.0 ^
    winotify==1.1.0 ^
    win10toast==0.9 ^
    pyinstaller==6.6.0 ^
    --quiet

if errorlevel 1 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)
echo [OK] All packages installed.

:: ── Clean previous build ────────────────────────────────────
echo [..] Cleaning previous build...
if exist build     rmdir /s /q build
if exist dist      rmdir /s /q dist
if exist UpworkMonitor.spec del /q UpworkMonitor.spec

:: ── Run PyInstaller ─────────────────────────────────────────
echo [..] Building EXE (this takes 1-3 minutes)...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "UpworkMonitor" ^
    --hidden-import=pystray ^
    --hidden-import=pystray._win32 ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageDraw ^
    --hidden-import=PIL.ImageFont ^
    --hidden-import=winotify ^
    --hidden-import=win10toast ^
    --hidden-import=plyer ^
    --hidden-import=plyer.platforms.win.notification ^
    --hidden-import=selenium ^
    --hidden-import=selenium.webdriver ^
    --hidden-import=selenium.webdriver.chrome ^
    --hidden-import=selenium.webdriver.chrome.service ^
    --hidden-import=selenium.webdriver.chrome.options ^
    --hidden-import=selenium.webdriver.support.ui ^
    --hidden-import=selenium.webdriver.support.expected_conditions ^
    --hidden-import=webdriver_manager ^
    --hidden-import=webdriver_manager.chrome ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.scrolledtext ^
    --collect-all pystray ^
    --collect-all winotify ^
    --collect-all plyer ^
    --noconfirm ^
    upwork_monitor.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)

:: ── Verify output ───────────────────────────────────────────
if not exist "dist\UpworkMonitor.exe" (
    echo [ERROR] EXE not found after build. Something went wrong.
    pause
    exit /b 1
)

:: ── Copy EXE to current folder ──────────────────────────────
copy /y "dist\UpworkMonitor.exe" "UpworkMonitor.exe" >nul
echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo   EXE location:  %CD%\UpworkMonitor.exe
echo.
echo   HOW TO USE:
echo   1. Double-click UpworkMonitor.exe
echo   2. Look for the icon in your system tray (bottom-right)
echo   3. Right-click the tray icon ^> Settings
echo   4. Enter your Upwork email + password
echo   5. Add Job IDs and click Start Monitoring
echo.
echo   The bot runs silently in the background and sends
echo   Windows notifications when a client views your job.
echo.
pause
