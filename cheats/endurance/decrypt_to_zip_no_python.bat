@echo off
setlocal EnableExtensions
title Forest of the Blue Skin - Descifrar project.json a ZIP
if "%~1"=="" (
    echo Arrastra el project.json CIFRADO encima de este .bat.
    echo No necesita Python ni instalaciones adicionales en Windows 10/11.
    pause
    exit /b 2
)
if not exist "%~dp0decrypt_to_zip_no_python.ps1" (
    echo ERROR: falta decrypt_to_zip_no_python.ps1 junto a este .bat.
    pause
    exit /b 3
)
set "IN=%~f1"
set "OUT=%~dp1project_data.zip"
echo Analizando y comprimiendo: "%IN%"
echo Salida: "%OUT%"
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0decrypt_to_zip_no_python.ps1" -InputFile "%IN%" -OutputFile "%OUT%"
if errorlevel 1 (
    echo.
    echo ERROR: descifrado fallido. El original permanece intacto.
    pause
    exit /b 1
)
echo.
echo LISTO: "%OUT%"
echo Sube project_data.zip a la Release de GitHub.
pause
exit /b 0
