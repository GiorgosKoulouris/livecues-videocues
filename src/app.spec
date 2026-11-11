# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — build the Windows executable.

Run on a Windows machine (PyInstaller does not cross-compile):

    pip install -r requirements.txt pyinstaller
    pyinstaller app.spec

Output: dist/VideoCues.exe  (one-file build)

We explicitly collect PySide6's QtMultimedia data/plugins/binaries so the
FFmpeg media backend ships with the app; without it, video playback fails on
machines that don't have the full Qt runtime.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Bundle the assets folder (default idle placeholder, etc.).
datas += [("assets", "assets")]

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    # ``mido`` loads its backend dynamically by name (importlib), so PyInstaller
    # can't see ``mido.backends.rtmidi`` statically — without listing it here the
    # frozen .exe fails at runtime with "No module named 'mido.backends.rtmidi'"
    # even though the ``rtmidi`` C extension itself is bundled.
    hiddenimports=hiddenimports + ["rtmidi", "mido.backends.rtmidi"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VideoCues",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # avoid UPX corrupting Qt/FFmpeg DLLs in the one-file exe
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI app: no console window
    icon="assets/app.ico",  # bundled LiveCues VideoCues app icon
)
