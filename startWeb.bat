@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
pushd "%ROOT%"

set "EVENNIA=%ROOT%\.venv\Scripts\evennia.exe"

if not exist "%EVENNIA%" (
  echo [startWeb] Could not find %EVENNIA%
  popd
  exit /b 1
)

set "WEB_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":4001 .*LISTENING"') do (
  set "WEB_PID=%%P"
  goto :web_pid_found
)

:web_pid_found

if defined WEB_PID (
  echo [startWeb] Existing game server detected on port 4001 ^(PID %WEB_PID%^). Performing full restart...
  call "%EVENNIA%" stop
) else (
  echo [startWeb] No game server detected on port 4001. Starting fresh...
)

call "%EVENNIA%" start
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%