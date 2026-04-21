@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
pushd "%ROOT%"

where git >nul 2>nul
if errorlevel 1 (
  echo [gitpush] Git is not available on PATH.
  popd
  exit /b 1
)

for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%B"
if not defined BRANCH (
  echo [gitpush] This directory is not a git repository.
  popd
  exit /b 1
)

git add -A
if errorlevel 1 (
  echo [gitpush] Failed while staging changes.
  popd
  exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
  set /p "COMMIT_MSG=[gitpush] Enter commit message: "
  if "!COMMIT_MSG!"=="" (
    echo [gitpush] Commit message is required when changes are present.
    popd
    exit /b 1
  )

  git commit -m "!COMMIT_MSG!"
  if errorlevel 1 (
    echo [gitpush] Commit failed.
    popd
    exit /b 1
  )
) else (
  echo [gitpush] No local changes to commit. Pushing current branch only...
)

git push origin %BRANCH%
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE%==0 (
  echo [gitpush] Push complete for branch %BRANCH%.
) else (
  echo [gitpush] Push failed.
)

popd
exit /b %EXIT_CODE%