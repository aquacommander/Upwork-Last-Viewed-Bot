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
    echo         Tick "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found.

:: ── Upgrade pip ─────────────────────────────────────────────
echo [..] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: ── Install packages ────────────────────────────────────────
echo [..] Installing packages (may take a minute)...
pip install ^
    selenium==4.20.0 ^
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

:: ── NOTE: webdriver-manager is intentionally NOT installed ──
:: Selenium 4.10+ has selenium-manager built in.
:: It auto-downloads the correct Windows chromedriver at runtime.
:: This prevents the WinError 193 "not a valid Win32 application" error
:: that happens when a Linux chromedriver gets bundled into the EXE.

:: ── Clean previous build ────────────────────────────────────
echo [..] Cleaning previous build...
if exist build              rmdir /s /q build
if exist dist               rmdir /s /q dist
if exist UpworkMonitor.spec del /q UpworkMonitor.spec

:: ── Build EXE ───────────────────────────────────────────────
echo [..] Building EXE (1-3 minutes)...
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
    --hidden-import=selenium.webdriver.common.by ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.scrolledtext ^
    --collect-all pystray ^
    --collect-all winotify ^
    --collect-all plyer ^
    --collect-all selenium ^
    --exclude-module webdriver_manager ^
    --noconfirm ^
    upwork_monitor.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause
    exit /b 1
)

:: ── Verify and copy ─────────────────────────────────────────
if not exist "dist\UpworkMonitor.exe" (
    echo [ERROR] EXE not found after build.
    pause
    exit /b 1
)

copy /y "dist\UpworkMonitor.exe" "UpworkMonitor.exe" >nul

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo   EXE:  %CD%\UpworkMonitor.exe
echo.
echo   FIRST RUN NOTE:
echo   On first launch, the bot will download the correct
echo   ChromeDriver for your Windows Chrome version (~10 MB).
echo   This only happens once. After that it starts instantly.
echo.
echo   HOW TO USE:
echo   1. Double-click UpworkMonitor.exe
echo   2. Find the icon in your system tray (bottom-right)
echo   3. Right-click icon ^> Settings
echo   4. Enter Upwork email + password
echo   5. Add Job IDs ^> Start Monitoring
echo.
pause
