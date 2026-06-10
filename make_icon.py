"""
Convert your image to a Windows .ico file for the app.

Place your image here (any one name):
    assets/app_icon.png
    assets/app_icon.jpg
    assets/icon.png

Then run:
    python make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing package. Run: pip install pillow")
    sys.exit(1)

ASSETS = Path(__file__).parent / "assets"
OUTPUT_ICO = ASSETS / "app_icon.ico"
OUTPUT_PNG = ASSETS / "app_icon.png"
SOURCE_NAMES = (
    "app_icon.png",
    "app_icon.jpg",
    "app_icon.jpeg",
    "app_icon.webp",
    "icon.png",
    "icon.jpg",
    "icon.jpeg",
)


def find_source_image() -> Path | None:
    ASSETS.mkdir(exist_ok=True)
    for name in SOURCE_NAMES:
        path = ASSETS / name
        if path.exists():
            return path
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"):
        matches = sorted(ASSETS.glob(pattern))
        if matches:
            return matches[0]
    return None


def square_crop(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return img.crop((left, top, left + side, top + side))


def main() -> int:
    source = find_source_image()
    if source is None:
        print("No image found.")
        print()
        print("Copy your image to:")
        print(f"  {ASSETS}\\app_icon.png")
        print()
        print("Then run this script again.")
        return 1

    image = square_crop(Image.open(source))
    image_256 = image.resize((256, 256), Image.Resampling.LANCZOS)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    image_256.save(OUTPUT_ICO, format="ICO", sizes=sizes)
    image_256.save(OUTPUT_PNG, format="PNG")

    print(f"Source : {source}")
    print(f"Created: {OUTPUT_ICO}")
    print(f"Created: {OUTPUT_PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
