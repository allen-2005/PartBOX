# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("xlrd") + collect_submodules("openpyxl")

a = Analysis(
    ["run_partbox.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("assets/partbox.ico", "assets"),
        ("assets/partbox-wordmark-v1.png", "assets"),
        ("assets/partbox-chinese-wordmark-v1.png", "assets"),
        ("src/partbox/ui/forms/main_window.ui", "partbox/ui/forms"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytestqt", "matplotlib", "IPython", "notebook"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PartBOX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/partbox.ico",
    onefile=True,
)
