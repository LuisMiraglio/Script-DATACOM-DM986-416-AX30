@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno virtual.
    echo Ejecuta setup.bat primero.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" main.py
