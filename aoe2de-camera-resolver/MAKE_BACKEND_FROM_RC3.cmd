@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "RC3ZIP=AoE2DE_P3O_VIKING_SAGAS_54800_MIGRATION_RC3_FIXEDPOINT.zip"
set "TMP=%TEMP%\AoE2DE_P3O_RC10_BACKEND_%RANDOM%_%RANDOM%"

if not exist "%RC3ZIP%" (
  echo ERROR: No se encontro "%RC3ZIP%" junto a este archivo.
  echo Copia el ZIP RC3_FIXEDPOINT aqui y vuelve a ejecutar este CMD.
  pause
  exit /b 2
)

if exist "%TMP%" rmdir /s /q "%TMP%"
mkdir "%TMP%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: No se pudo crear el directorio temporal.
  pause
  exit /b 3
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%CD%\%RC3ZIP%' -DestinationPath '%TMP%' -Force"
if errorlevel 1 goto :extract_fail

set "BACKEND_SRC="
for /r "%TMP%" %%F in (version.dll) do if not defined BACKEND_SRC set "BACKEND_SRC=%%~fF"
if not defined BACKEND_SRC (
  echo ERROR: El ZIP RC3 no contiene version.dll.
  goto :fail
)

copy /y "%BACKEND_SRC%" "%CD%\P3OBackend.dll" >nul
if errorlevel 1 (
  echo ERROR: No se pudo crear P3OBackend.dll.
  goto :fail
)

set "INI_SRC="
for /r "%TMP%" %%F in (AoE2DE_P3N.ini) do if not defined INI_SRC set "INI_SRC=%%~fF"
if defined INI_SRC copy /y "%INI_SRC%" "%CD%\AoE2DE_P3N.ini" >nul

for %%F in ("%CD%\P3OBackend.dll") do echo P3OBackend.dll creado: %%~zF bytes
if exist "%CD%\AoE2DE_P3N.ini" echo AoE2DE_P3N.ini preparado.
rmdir /s /q "%TMP%" >nul 2>&1
echo.
echo OK: RC3_FIXEDPOINT queda como backend visual exacto.
echo NO renombres P3OBackend.dll a version.dll: version.dll debe seguir siendo el bridge RC10.
pause
exit /b 0

:extract_fail
echo ERROR: Fallo Expand-Archive.
:fail
rmdir /s /q "%TMP%" >nul 2>&1
pause
exit /b 4
