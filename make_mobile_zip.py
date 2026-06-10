"""Create soundwave-mobile.zip for Netlify drag-and-drop deploy."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).parent / "mobile"
OUT = Path(__file__).parent / "soundwave-mobile.zip"

SKIP = {".DS_Store", "Thumbs.db"}


def main():
    if OUT.exists():
        OUT.unlink()

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path.name not in SKIP:
                zf.write(path, path.relative_to(ROOT).as_posix())

    print(f"Created: {OUT}")
    print(f"Size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
