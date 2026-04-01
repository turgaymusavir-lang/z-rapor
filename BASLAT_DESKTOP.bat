@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\run_desktop.ps1"
if errorlevel 1 (
  echo.
  echo Uygulama baslatilirken hata olustu.
  pause
)
endlocal
