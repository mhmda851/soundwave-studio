@echo off
chcp 65001 >nul
setlocal

echo.
echo ====================================================
echo   SoundWave — رفع المشروع إلى GitHub Pages
echo ====================================================
echo.

set GH_USER=mhmda851
echo اسم المستخدم: %GH_USER%
echo (ملاحظة: اسم المستخدم ليس البريد الإلكتروني)
echo.

set REPO=soundwave-studio
set GIT=git -c safe.directory=F:/soundwaveprgram

echo.
echo 1) إنشاء المستودع على GitHub...
echo    افتح هذا الرابط وأنشئ مستودعاً باسم %REPO%:
echo    https://github.com/new?name=%REPO%^&description=SoundWave+Mobile+PWA
echo.
echo    مهم: لا تضف README ولا .gitignore — اتركه فارغاً.
echo.
pause

echo.
echo 2) ربط المستودع ورفع الملفات...
cd /d "%~dp0"

%GIT% remote remove origin 2>nul
%GIT% remote add origin https://github.com/%GH_USER%/%REPO%.git
%GIT% branch -M main
%GIT% push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo فشل الرفع. جرّب تسجيل الدخول عبر:
    echo   https://github.com/login
    echo ثم أعد تشغيل هذا الملف.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   تم الرفع بنجاح!
echo ====================================================
echo.
echo 3) فعّل GitHub Pages:
echo    https://github.com/%GH_USER%/%REPO%/settings/pages
echo    Source: GitHub Actions
echo.
echo 4) بعد 1-2 دقيقة افتح على الموبايل:
echo    https://%GH_USER%.github.io/%REPO%/
echo.
echo 5) ثبّت التطبيق من المتصفح على الشاشة الرئيسية.
echo.
pause
