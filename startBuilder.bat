@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
pushd "%ROOT%"

set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "LAUNCHER=%ROOT%\tools\builder_launcher\launcher.py"

if not exist "%PYTHON%" (
  echo [startBuilder] Could not find %PYTHON%
  popd
  exit /b 1
)

if not exist "%LAUNCHER%" (
  echo [startBuilder] Could not find %LAUNCHER%
  popd
  exit /b 1
)

set "BUILDER_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":7777 .*LISTENING"') do (
  set "BUILDER_PID=%%P"
  goto :builder_pid_found
)

:builder_pid_found

if defined BUILDER_PID (
  echo [startBuilder] Existing builder server detected on port 7777 ^(PID %BUILDER_PID%^). Performing full restart...
  powershell -NoProfile -Command "Stop-Process -Id %BUILDER_PID% -Force"
) else (
  echo [startBuilder] No builder server detected on port 7777. Starting fresh...
)

call "%PYTHON%" "%LAUNCHER%"
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%