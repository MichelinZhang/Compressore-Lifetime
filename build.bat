@echo off
REM Compressor Lifetime Rev 3.2.7 - one-click Nuitka build
REM Includes: compressor_lifetime_3_2_6.py + daq_device_manager.py
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_nuitka.ps1" %*
if errorlevel 1 (
    echo.
    echo Build FAILED.
    pause
    exit /b 1
)
echo.
echo Build OK. Output: dist\CompressorLifetime\CompressorLifetime.dist\
pause
