@echo off
echo ============================================
echo  Upwork Monitor - EXE Builder
echo ============================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Building EXE with PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "UpworkMonitor" ^
    --hidden-import=pystray ^
    --hidden-import=pystray._win32 ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageDraw ^
    --hidden-import=winotify ^
    --hidden-import=win10toast ^
    --hidden-import=plyer ^
    --hidden-import=plyer.platforms.win.notification ^
    --hidden-import=selenium ^
    --hidden-import=webdriver_manager ^
    --collect-all pystray ^
    --collect-all winotify ^
    upwork_monitor.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo Your EXE is ready at:  dist\UpworkMonitor.exe
echo.
echo Double-click it to run. It will appear in your system tray.
echo.
pause
