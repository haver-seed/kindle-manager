# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['kindle_manager/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/style.qss', 'resources'),
        ('resources/app_icon.svg', 'resources'),
    ],
    hiddenimports=[
        'sqlite3',
        'shutil',
        'subprocess',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt 6.11 uses the Windows system ICU shim. A developer machine with Conda on
# PATH may trick PyInstaller into bundling Conda's incompatible ICU 73 DLLs,
# which makes QtWidgets fail at startup on otherwise clean machines.
_incompatible_icu = {'icuuc.dll', 'icudt73.dll'}
a.binaries = [entry for entry in a.binaries if entry[0].lower() not in _incompatible_icu]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KindleManager',
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
    icon=None,
)
