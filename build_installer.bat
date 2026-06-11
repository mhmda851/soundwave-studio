@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   SoundWave Studio — بناء ملفات التثبيت
echo ============================================================
echo.

echo [1/4] تثبيت المتطلبات...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if %ERRORLEVEL% NEQ 0 goto :fail

echo [2/4] بناء أيقونة Windows...
python rebuild_icon.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo [3/4] بناء ملف الكمبيوتر (.exe) — قد يستغرق دقائق...
if exist dist\SoundWaveStudio.exe del /f /q dist\SoundWaveStudio.exe
if exist dist\AudioVisualizer.exe del /f /q dist\AudioVisualizer.exe
python -m PyInstaller --noconfirm --clean audio_visualizer.spec
if %ERRORLEVEL% NEQ 0 goto :fail

echo [4/4] تجميع حزمة التثبيت...
python make_release.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo.
echo ============================================================
echo   تم البناء بنجاح
echo ============================================================
echo.
echo  ملفات التثبيت في:
echo    release\SoundWaveStudio.exe     (كمبيوتر Windows)
echo    release\soundwave-mobile.zip    (موبايل / Netlify)
echo    release\INSTALL_AR.txt          (دليل التثبيت)
echo.
echo  حزمة كاملة: SoundWave-Release-*.zip
echo.
explorer release
pause
exit /b 0

:fail
echo.
echo فشل البناء. راجع الرسائل أعلاه.
pause
exit /b 1
