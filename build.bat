@echo off
echo ============================================
echo   Building Audio Visualizer for Desktop
echo ============================================
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo.
echo Rebuilding Windows icon...
python rebuild_icon.py
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo Building executable (with icon)...
if exist dist\audio_visualizer.exe del /f /q dist\audio_visualizer.exe
if exist dist\AudioVisualizer.exe del /f /q dist\AudioVisualizer.exe
python -m PyInstaller --noconfirm --clean audio_visualizer.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD SUCCESS
echo ============================================
echo.
echo App location:
echo   dist\AudioVisualizer.exe
echo.
echo Tip: run copy_to_desktop.bat to copy a fresh copy to Desktop
echo.
echo Copy AudioVisualizer.exe to any Windows PC and double-click to run.
echo No Python installation required on the target computer.
echo.
pause
