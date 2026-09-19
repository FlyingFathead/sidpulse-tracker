@echo off
setlocal DisableDelayedExpansion
rem run.ps1 handles setup, the versioned console banner, and launching the tracker.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
exit /b %errorlevel%
