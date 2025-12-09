# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voice Typer is a macOS push-to-talk speech-to-text tool that uses MLX Whisper for local transcription on Apple Silicon. It runs as a menu bar app, listens for a hotkey, records audio, transcribes it, and types the result at the current cursor position.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run voice-typer
uv run voice-typer --hotkey f18
uv run voice-typer --model mlx-community/whisper-large-v3

# Build macOS .app bundle
./scripts/build_app.sh

# Lint
uv run ruff check src/
uv run ruff format src/
```

## Architecture

The application has a clear modular structure in `src/voice_typer/`:

- **main.py** - CLI entry point, orchestrates all components. Handles first-run setup (model selection/download), initializes recorder/transcriber/hotkey listener, and runs the main event loop.

- **audio.py** - `AudioRecorder` class using sounddevice. Captures 16kHz mono audio into a buffer via callback. Thread-safe start/stop with lock protection.

- **hotkey.py** - `HotkeyListener` using pynput. Maps friendly key names (f18, alt_r, etc.) to pynput keys. Fires callbacks on press/release.

- **transcribe.py** - `Transcriber` class wrapping MLX Whisper. Lazy-loads model on first use. Downloads models to `~/Library/Caches/voice-typer/models/` to avoid hidden path issues with MLX.

- **typer.py** - Text injection using macOS CGEvents (Quartz framework). Types text character-by-character at system level into any focused application.

- **statusbar.py** - Menu bar UI using rumps. Shows state icons (idle/recording/transcribing), model selection menu. Must run on main thread due to AppKit requirements.

- **config.py** - Configuration dataclass with TOML persistence at `~/.config/voice-typer/config.toml`. Supports CLI overrides.

## Key Technical Details

- Audio must be 16kHz mono (Whisper requirement)
- Models are cached in non-hidden directory to work around MLX path resolution issues
- Status bar runs on main thread (macOS AppKit requirement); hotkey listener runs in background thread
- Text injection requires Accessibility permissions
- PyInstaller spec file (`Voice Typer.spec`) includes hidden imports for MLX and collects data files for model assets
