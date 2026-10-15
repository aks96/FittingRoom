@echo off
setlocal
cd /d "%~dp0"
if not exist "local_ai\windows_setup.py" if exist "..\..\local_ai\windows_setup.py" cd /d "%~dp0..\.."
echo yourFittingRoom Windows x64 internal test - no admin rights needed.
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)"
if errorlevel 1 goto missing
py -3.12 "local_ai\windows_hardware.py"
echo 1. NVIDIA GPU - CUDA (experimental)
echo 2. AMD GPU - ROCm (Windows 11; supported models only; large download)
echo 3. Intel GPU - XPU (Windows 11; supported Arc models only)
echo 4. Intel or AMD CPU - slow testing without GPU acceleration
echo 5. Cancel
choice /c 12345 /n /m "Choose 1, 2, 3, 4 or 5: "
if errorlevel 5 exit /b 0
if errorlevel 4 goto cpu
if errorlevel 3 goto intel
if errorlevel 2 goto amd
set "YFR_COMPUTE=cuda"
goto setup
:amd
set "YFR_COMPUTE=rocm"
goto setup
:intel
set "YFR_COMPUTE=xpu"
goto setup
:cpu
set "YFR_COMPUTE=cpu"
:setup
py -3.12 "local_ai\windows_setup.py" --compute %YFR_COMPUTE%
set "YFR_RESULT=%ERRORLEVEL%"
echo Models are shared; each compute backend has its own local Python environment.
pause
exit /b %YFR_RESULT%
:missing
echo Install 64-bit Python 3.12 per-user with the Python launcher from python.org, then retry.
pause
exit /b 1
