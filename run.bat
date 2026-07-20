@echo off
cd /d "%~dp0"

if exist "dist\KindleManager.exe" (
    start "" "dist\KindleManager.exe"
    exit /b 0
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m kindle_manager.main
    exit /b 0
)

echo Kindle Manager needs a project virtual environment.
echo.
echo Run these commands first:
echo   py -3 -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -e .
echo.
pause
exit /b 1
