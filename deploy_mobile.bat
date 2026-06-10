@echo off
chcp 65001 >nul
echo.
echo ====================================================
echo   SoundWave Mobile — نشر التطبيق على الإنترنت
echo ====================================================
echo.

python make_mobile_zip.py
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo ----------------------------------------------------
echo  الطريقة 1 — Netlify (الأسهل، بدون Git)
echo ----------------------------------------------------
echo  1. افتح: https://app.netlify.com/drop
echo  2. اسحب الملف: soundwave-mobile.zip
echo  3. انتظر حتى يظهر رابط مثل: https://xxxxx.netlify.app
echo  4. افتح الرابط على الموبايل وثبّت التطبيق:
echo     Android Chrome  ^> القائمة ^> إضافة للشاشة الرئيسية
echo     iPhone Safari   ^> مشاركة ^> Add to Home Screen
echo.

echo ----------------------------------------------------
echo  الطريقة 2 — GitHub Pages (مجاني دائماً)
echo ----------------------------------------------------
echo  1. أنشئ حساباً على https://github.com
echo  2. أنشئ مستودعاً جديداً باسم: soundwave-studio
echo  3. في هذا المجلد نفّذ:
echo       git init
echo       git add .
echo       git commit -m "Add SoundWave mobile PWA"
echo       git branch -M main
echo       git remote add origin https://github.com/YOUR_USER/soundwave-studio.git
echo       git push -u origin main
echo  4. من GitHub: Settings ^> Pages ^> Source: GitHub Actions
echo  5. بعد دقيقتين الرابط:
echo       https://YOUR_USER.github.io/soundwave-studio/
echo.

echo ----------------------------------------------------
echo  تجربة محلية على الموبايل (نفس الواي فاي)
echo ----------------------------------------------------
echo  شغّل: python serve_mobile.py
echo  وافتح الرابط الذي يظهر على هاتفك.
echo.
echo ====================================================
pause
