@echo off
set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
if defined DRAWGEN_NX_RUN_JOURNAL (
  set "RUN_JOURNAL=%DRAWGEN_NX_RUN_JOURNAL%"
) else (
  set "RUN_JOURNAL=%UGII_BASE_DIR%\NXBIN\run_journal.exe"
)
rem Remove an earlier result so a failed launch cannot show stale output.
if exist "%REPO_ROOT%\runs\ping\status.json" del "%REPO_ROOT%\runs\ping\status.json"
"%RUN_JOURNAL%" "%REPO_ROOT%\nx_worker\main.py" -args "%REPO_ROOT%\nx_worker\jobs\ping.json"
if exist "%REPO_ROOT%\runs\ping\status.json" (
  type "%REPO_ROOT%\runs\ping\status.json"
) else (
  echo No status.json was written. run_journal did not start the worker.
  exit /b 1
)
