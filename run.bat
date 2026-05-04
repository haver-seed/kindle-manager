@echo off
cd /d "%~dp0"

REM Search common Python install locations (pythonw = no console)
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%d\pythonw.exe" (
        start "" "%%d\pythonw.exe" -m kindle_manager.main
        goto :eof
    )
)

REM Check Program Files
for /d %%d in ("C:\Program Files\Python3*") do (
    if exist "%%d\pythonw.exe" (
        start "" "%%d\pythonw.exe" -m kindle_manager.main
        goto :eof
    )
)

REM Fallback: try pythonw on PATH (with console if not found)
start "" pythonw -m kindle_manager.main 2>nul || python -m kindle_manager.main 2>nul || (
    echo Python not found. Install: https://www.python.org/downloads/
    pause
)
