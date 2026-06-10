@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   لماذا الرابط لا يعمل؟
echo ============================================================
echo   المستودع soundwave-studio غير موجود على GitHub بعد!
echo   لذلك الرابط يعطي خطأ 404.
echo.
echo ============================================================
echo   الحل الأسهل — رفع من موقع GitHub مباشرة (بدون أوامر)
echo ============================================================
echo.
echo  الخطوة 1: أنشئ المستودع
echo  -------------------------
echo  افتح هذا الرابط وسجّل الدخول بحساب mhmda851:
echo  https://github.com/new?name=soundwave-studio
echo.
echo  - اختر Public
echo  - لا تضف README
echo  - اضغط Create repository
echo.
pause
echo.
echo  الخطوة 2: ارفع ملفات التطبيق
echo  -------------------------
echo  في صفحة المستودع الجديد اضغط:
echo  "uploading an existing file"
echo.
echo  اسحب كل محتويات هذا المجلد إلى الصفحة:
echo  %~dp0mobile\
echo.
echo  (index.html  app.js  style.css  manifest.json  sw.js  icons\)
echo.
echo  اكتب رسالة: Add mobile app
echo  اضغط Commit changes
echo.
pause
echo.
echo  الخطوة 3: فعّل GitHub Pages
echo  -------------------------
echo  افتح:
echo  https://github.com/mhmda851/soundwave-studio/settings/pages
echo.
echo  اختر:
echo   Source = Deploy from a branch
echo   Branch = main
echo   Folder = / (root)
echo  اضغط Save
echo.
pause
echo.
echo  الخطوة 4: انتظر 2-3 دقائق ثم افتح على الموبايل:
echo  https://mhmda851.github.io/soundwave-studio/
echo.
echo ============================================================
echo  سأفتح الروابط المطلوبة الآن...
echo ============================================================
start https://github.com/new?name=soundwave-studio
timeout /t 3 >nul
explorer "%~dp0mobile"
echo.
pause
