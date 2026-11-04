@echo off
setlocal
set "INPUT=%~1"
if "%INPUT%"=="" (
  echo Arrastra el project.json cifrado encima de este .bat.
  echo Se creara project_data.zip al lado del JSON original.
  pause
  exit /b 2
)
set "OUT=%~dp1project_data.zip"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0decrypt_to_zip.py" "%INPUT%" --output "%OUT%"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: necesitas Python 3 instalado para ejecutar este archivo.
    pause
    exit /b 3
  )
  python "%~dp0decrypt_to_zip.py" "%INPUT%" --output "%OUT%"
)
if errorlevel 1 (
  echo Fallo la conversion. El JSON original permanece intacto.
  pause
  exit /b 1
)
echo.
echo LISTO: %OUT%
echo Adjunta project_data.zip a una GitHub Release.
pause
