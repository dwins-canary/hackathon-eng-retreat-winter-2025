# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Collect all mlx data files (includes metallib)
mlx_datas = collect_data_files('mlx', include_py_files=False)
# Collect mlx_whisper assets (mel_filters.npz, tokenizer files)
mlx_whisper_datas = collect_data_files('mlx_whisper', include_py_files=False)

a = Analysis(
    ['src/voice_typer/main.py'],
    pathex=[],
    binaries=[],
    datas=mlx_datas + mlx_whisper_datas,
    hiddenimports=[
        'mlx._reprlib_fix',
        'mlx.core',
        'mlx.nn',
        'mlx.utils',
        'mlx_whisper',
        'mlx_whisper.audio',
        'mlx_whisper.decoding',
        'mlx_whisper.load_models',
        'mlx_whisper.tokenizer',
        'mlx_whisper.transcribe',
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
    [],
    exclude_binaries=True,
    name='Voice Typer',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Voice Typer',
)
app = BUNDLE(
    coll,
    name='Voice Typer.app',
    icon=None,
    bundle_identifier='com.voicetyper.app',
    info_plist={
        'CFBundleName': 'Voice Typer',
        'CFBundleDisplayName': 'Voice Typer',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSMicrophoneUsageDescription': 'Voice Typer needs microphone access to record speech.',
        'NSAccessibilityUsageDescription': 'Voice Typer needs Accessibility access to type text.',
        'LSUIElement': True,  # Menu bar app (no dock icon)
    },
)
