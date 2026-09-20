@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD_JTDX_SUPERHOUND_MSI.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo BUILD FAILED - sprawdz katalog LOGS
) else (
  echo BUILD OK - MSI znajduje sie w katalogu OUTPUT
)
pause
exit /b %RC%
