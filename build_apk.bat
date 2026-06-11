@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "SDK=%LOCALAPPDATA%\Android\Sdk"
if not exist "%SDK%" (
    echo Android SDK not found.
    echo Install Android Studio: https://developer.android.com/studio
    pause
    exit /b 1
)
set "ANDROID_HOME=%SDK%"
set "ANDROID_SDK_ROOT=%SDK%"

echo.
echo ============================================================
echo   SoundWave Studio — Build Android APK
echo ============================================================
echo.

echo [1/5] Installing npm packages...
call npm install
if %ERRORLEVEL% NEQ 0 goto :fail

if not exist android (
    echo [2/5] Creating Android project...
    call npx cap add android
    if %ERRORLEVEL% NEQ 0 goto :fail
) else (
    echo [2/5] Android project exists — skipping add
)

echo [3/5] Syncing web app to Android...
call npx cap sync android
if %ERRORLEVEL% NEQ 0 goto :fail

echo [4/5] Adding microphone permissions...
python patch_android_manifest.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo [5/5] Building debug APK (may take several minutes)...
cd android
call gradlew.bat assembleDebug
if %ERRORLEVEL% NEQ 0 goto :fail
cd ..

set "APK=android\app\build\outputs\apk\debug\app-debug.apk"
if not exist "%APK%" goto :fail

if not exist release mkdir release
copy /Y "%APK%" "release\SoundWaveStudio.apk" >nul

echo.
echo ============================================================
echo   APK READY
echo ============================================================
echo.
echo   release\SoundWaveStudio.apk
echo.
echo   Copy this file to your phone and open it to install.
echo   You may need to allow "Install from unknown sources".
echo.
explorer release
pause
exit /b 0

:fail
echo.
echo Build failed. If this is the first time, install Android Studio
echo and open SDK Manager to install Android SDK Platform 34+.
echo.
pause
exit /b 1
