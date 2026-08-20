@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  Configurador Datacom - Compilar EXE
echo ================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno virtual.
    echo Ejecuta setup.bat primero.
    pause
    exit /b 1
)

if not exist "venv\Scripts\pyinstaller.exe" (
    echo [INFO] PyInstaller no esta instalado. Instalando dependencias de build...
    "venv\Scripts\python.exe" -m pip install -r requirements-build.txt
    if errorlevel 1 goto :error
)

echo [1/3] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/3] Compilando con PyInstaller...
"venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm "Configurador Datacom.spec"
if errorlevel 1 goto :error

echo [3/3] Verificando resultado...
if not exist "dist\Configurador Datacom.exe" (
    echo [ERROR] PyInstaller termino pero no se encontro el EXE esperado.
    pause
    exit /b 1
)

echo.
echo ================================================
echo  COMPILACION COMPLETADA
echo ================================================
echo EXE generado en:
echo "%CD%\dist\Configurador Datacom.exe"
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] La compilacion fallo. Revisa los mensajes anteriores.
pause
exit /b 1
