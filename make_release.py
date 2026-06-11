"""Package desktop exe + mobile zip into release/ install folder."""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
RELEASE = ROOT / "release"
MOBILE = ROOT / "mobile"
DESKTOP_NAMES = ("SoundWaveStudio.exe", "AudioVisualizer.exe")


def copy_mobile_zip(target: Path) -> Path | None:
    src = ROOT / "soundwave-mobile.zip"
    if not src.exists():
        return None
    dst = target / "soundwave-mobile.zip"
    shutil.copy2(src, dst)
    return dst


def build_mobile_zip() -> Path:
    out = ROOT / "soundwave-mobile.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(MOBILE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(MOBILE).as_posix())
    return out


def find_desktop_exe() -> Path | None:
    for name in DESKTOP_NAMES:
        path = ROOT / "dist" / name
        if path.exists():
            return path
    return None


def write_install_guide(folder: Path) -> None:
    text = """SoundWave Studio — دليل التثبيت
================================

■ تثبيت على Android (ملف APK)
---------------------------------
1. انسخ الملف: release\SoundWaveStudio.apk
2. أرسله لهاتف Android (USB / WhatsApp / Drive)
3. افتح الملف على الهاتف واضغط «تثبيت»
4. إذا طُلب: فعّل «السماح بالتثبيت من مصادر غير معروفة»
5. عند أول تشغيل: اسمح بالوصول للميكروفون

■ تثبيت على الكمبيوتر (Windows)
---------------------------------
1. شغّل الملف: SoundWaveStudio.exe
2. لا يحتاج تثبيت Python
3. للاختصار: انسخ الملف إلى سطح المكتب

■ تثبيت على الموبايل (Android / iPhone)
---------------------------------------
الطريقة 1 — عبر الإنترنت (GitHub Pages):
  افتح: https://mhmda851.github.io/soundwave-studio/
  ثم ثبّت من المتصفح على الشاشة الرئيسية

الطريقة 2 — عبر Netlify:
  1. افتح: https://app.netlify.com/drop
  2. اسحب ملف: soundwave-mobile.zip
  3. افتح الرابط الذي يظهر على الموبايل

  Android Chrome: القائمة > إضافة إلى الشاشة الرئيسية
  iPhone Safari:  مشاركة > Add to Home Screen

■ تجربة محلية على الموبايل (نفس الواي فاي)
-------------------------------------------
  python serve_mobile.py
  وافتح الرابط على الهاتف

■ الاختصارات (الكمبيوتر)
------------------------
  Tab / 1 / 2  التبديل بين المحلل والمسجّل
  R            بدء/إيقاف التسجيل
  M            تبديل أعمدة/موجات
  F            ملء الشاشة
  ESC          خروج
"""
    (folder / "INSTALL_AR.txt").write_text(text, encoding="utf-8")


def main() -> int:
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir()

    desktop = find_desktop_exe()
    if desktop:
        shutil.copy2(desktop, RELEASE / "SoundWaveStudio.exe")
        print(f"Desktop: {desktop.name}")
    else:
        print("Desktop: SKIPPED (run build.bat first)")

    apk = ROOT / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if apk.exists():
        shutil.copy2(apk, RELEASE / "SoundWaveStudio.apk")
        print(f"Android: SoundWaveStudio.apk ({apk.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("Android: SKIPPED (run build_apk.bat first)")

    build_mobile_zip()
    mobile_zip = copy_mobile_zip(RELEASE)
    if mobile_zip:
        print(f"Mobile:  {mobile_zip.name} ({mobile_zip.stat().st_size / 1024:.1f} KB)")

    write_install_guide(RELEASE)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    bundle = ROOT / f"SoundWave-Release-{stamp}.zip"
    if bundle.exists():
        bundle.unlink()
    shutil.make_archive(str(bundle.with_suffix("")), "zip", RELEASE)
    print(f"Bundle:  {bundle.name}")
    print(f"Folder:  {RELEASE}")
    return 0 if desktop else 1


if __name__ == "__main__":
    raise SystemExit(main())
