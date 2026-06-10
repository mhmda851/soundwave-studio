"""Rebuild Windows-optimized app_icon.ico from assets/app_icon.png."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Run: pip install pillow")
    sys.exit(1)

ROOT = Path(__file__).parent
SOURCE = ROOT / "assets" / "app_icon.png"
OUTPUT = ROOT / "app_icon.ico"


def square_crop(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def main() -> int:
    if not SOURCE.exists():
        print(f"Missing source image: {SOURCE}")
        return 1

    img = square_crop(Image.open(SOURCE))
    img256 = img.resize((256, 256), Image.Resampling.LANCZOS)

    # Standard Windows icon sizes for .exe files
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img256.save(OUTPUT, format="ICO", sizes=sizes)

    # Keep assets copy in sync
    assets_ico = ROOT / "assets" / "app_icon.ico"
    assets_ico.write_bytes(OUTPUT.read_bytes())
    img256.save(ROOT / "assets" / "app_icon.png", format="PNG")

    data = OUTPUT.read_bytes()
    count = struct.unpack("<H", data[4:6])[0] if data[:4] == b"\x00\x00\x01\x00" else 0
    print(f"Created: {OUTPUT}")
    print(f"Images in ICO: {count}")
    print(f"Size: {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
