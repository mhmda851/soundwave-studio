"""Patch Android manifest with microphone permissions for WebView audio."""

from pathlib import Path

MANIFEST = Path(__file__).parent / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
PERMS = (
    '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n'
    '    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />\n'
)


def main() -> int:
    if not MANIFEST.exists():
        print(f"Missing: {MANIFEST}")
        print("Run: npx cap add android")
        return 1

    text = MANIFEST.read_text(encoding="utf-8")
    if "RECORD_AUDIO" in text:
        print("Microphone permissions already present.")
        return 0

    marker = "<manifest"
    idx = text.find(">", text.find(marker))
    if idx == -1:
        print("Could not parse AndroidManifest.xml")
        return 1

    updated = text[: idx + 1] + "\n" + PERMS + text[idx + 1 :]
    MANIFEST.write_text(updated, encoding="utf-8")
    print("Added RECORD_AUDIO permissions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
