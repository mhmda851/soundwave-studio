@echo off
set SRC=f:\soundwaveprgram\dist\AudioVisualizer.exe
set DST=%USERPROFILE%\Desktop\AudioVisualizer.exe

if not exist "%SRC%" (
    echo Build the app first: build.bat
    pause
    exit /b 1
)

copy /Y "%SRC%" "%DST%"
echo.
echo Copied to Desktop:
echo   %DST%
echo.
echo Double-click AudioVisualizer.exe on your Desktop.
pause
