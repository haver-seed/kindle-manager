# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['kindle_manager/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/style.qss', 'resources'),
    ],
    hiddenimports=[
        'ebooklib',
        'ebooklib.epub',
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
