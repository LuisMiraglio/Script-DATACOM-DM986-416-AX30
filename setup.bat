@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  Configurador Datacom - Preparar entorno
echo ================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro el launcher de Python ^(py^).
    echo Instala Python 3.13 y marca "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    py -3.13 -m venv venv
    if errorlevel 1 goto :error
) else (
    echo [1/3] Entorno virtual existente.
)

echo [2/3] Actualizando pip...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/3] Instalando dependencias...
"venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo.
echo [OK] Entorno listo.
echo Para ejecutar: run.bat
echo Para compilar: build.bat
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] No se pudo preparar el entorno.
pause
exit /b 1
