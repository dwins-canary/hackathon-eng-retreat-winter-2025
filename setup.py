"""py2app setup for Voice Typer."""

import sys

# Increase recursion limit for modulegraph analyzing complex packages like mlx
sys.setrecursionlimit(5000)

from setuptools import setup

APP = ["src/voice_typer/main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Voice Typer",
        "CFBundleDisplayName": "Voice Typer",
        "CFBundleIdentifier": "com.voicetyper.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "NSMicrophoneUsageDescription": "Voice Typer needs microphone access to record speech.",
        "NSAccessibilityUsageDescription": "Voice Typer needs Accessibility access to type text into other applications.",
        "LSUIElement": True,  # Menu bar app (no dock icon)
    },
    "packages": [
        "mlx",
        "mlx_whisper",
        "sounddevice",
        "numpy",
        "pynput",
        "rumps",
        "huggingface_hub",
    ],
    "includes": ["voice_typer"],
    "excludes": ["tkinter", "_tkinter", "Tkinter"],
}

setup(
    app=APP,
    name="Voice Typer",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
