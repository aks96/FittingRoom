@echo off
setlocal
cd /d "%~dp0"
if not exist "local_ai\windows_setup.py" if exist "..\..\local_ai\windows_setup.py" cd /d "%~dp0..\.."
if not exist ".runtime\companion-device.json" goto missing
echo Internal Windows test candidate. Not a supported or signed release.
echo Run Test Windows.cmd first. No images leave this computer.
echo Selected GPU must pass checks. Explicit CPU testing may be very slow.
choice /c YN /n /m "Start experimental local worker? [Y/N] "
if errorlevel 2 exit /b 0
py -3.12 "local_ai\windows_start.py" --experimental-worker
set "YFR_RESULT=%ERRORLEVEL%"
echo The local companion stopped. No background service was installed.
pause
exit /b %YFR_RESULT%
:missing
echo Local AI setup is missing. Open Set up.cmd first.
pause
exit /b 1
