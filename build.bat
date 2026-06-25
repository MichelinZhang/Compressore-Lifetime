@echo off
REM Compressor Lifetime Rev 3.2.6 - one-click Nuitka build
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_nuitka.ps1" %*
if errorlevel 1 (
    echo.
    echo Build FAILED.
    pause
    exit /b 1
)
echo.
echo Build OK.
pause
