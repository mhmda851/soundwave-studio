# PyInstaller spec — build: pyinstaller audio_visualizer.spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

block_cipher = None
root = Path(SPECPATH)

datas = []
binaries = []
hiddenimports = []

icon_file = root / "app_icon.ico"

# Bundle app icon for window + exe
if icon_file.exists():
    datas.append((str(icon_file), "assets"))
    png_file = root / "assets" / "app_icon.png"
    if png_file.exists():
        datas.append((str(png_file), "assets"))

# Full bundle for numpy 2.x and sounddevice/portaudio
for package in ("numpy", "sounddevice", "_sounddevice_data"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# Pygame without pulling the entire tests suite into the exe
pygame_datas, pygame_binaries, pygame_hidden = collect_all("pygame")
datas += pygame_datas
binaries += pygame_binaries
hiddenimports += [h for h in pygame_hidden if not h.startswith("pygame.tests")]

try:
    datas += copy_metadata("sounddevice")
except Exception:
    pass

a = Analysis(
    ["audio_visualizer.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pygame.tests",
        "tkinter",
        "matplotlib",
        "cv2",
        "PIL",
        "IPython",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SoundWaveStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file.resolve()) if icon_file.exists() else None,
)
