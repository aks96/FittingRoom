@echo off
setlocal
cd /d "%~dp0"
if not exist "local_ai\windows_setup.py" if exist "..\..\local_ai\windows_setup.py" cd /d "%~dp0..\.."
echo Stop Start AI.cmd before this test. No personal photos or downloads are used.
echo Tests configured NVIDIA, AMD, Intel or CPU backend inside the restricted worker.
py -3.12 "local_ai\windows_entry.py" test
set "YFR_RESULT=%ERRORLEVEL%"
echo Review .runtime\windows-validation\report.json. Full generation still needs testing.
pause
exit /b %YFR_RESULT%
