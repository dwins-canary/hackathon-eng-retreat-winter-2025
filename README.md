# Voice Typer

A macOS push-to-talk speech-to-text tool that transcribes your voice and types the result at the current cursor position.

## Features

- **Push-to-talk**: Hold a hotkey to record, release to transcribe
- **Local processing**: Uses MLX Whisper for fast, private transcription on Apple Silicon
- **Status bar icon**: Visual feedback showing recording/transcribing state
- **Configurable**: Custom hotkey, model selection, language settings

## Requirements

- macOS (Apple Silicon recommended)
- Python 3.11+
- Accessibility permissions (for global hotkey + text injection)
- Microphone access

## Installation

```bash
cd ~/projects/voice-typer
uv sync
```

## Usage

```bash
# Run with default settings (Right Option key)
uv run voice-typer

# Specify hotkey
uv run voice-typer --hotkey f18

# Use a different model
uv run voice-typer --model mlx-community/whisper-large-v3
```

## Fn Key Setup (via Karabiner-Elements)

The Fn key is hardware-level and requires Karabiner-Elements to remap:

1. Install: `brew install --cask karabiner-elements`
2. Add a rule to remap Fn to F18
3. Run with: `uv run voice-typer --hotkey f18`

## Configuration

Create `~/.config/voice-typer/config.toml`:

```toml
hotkey = "f18"  # or "alt_r", "ctrl_r", etc.
model = "mlx-community/whisper-large-v3-turbo"
language = "en"  # Optional: force language detection
```

## Permissions

On first run, you'll need to grant:

1. **Microphone Access**: System will prompt automatically
2. **Accessibility**: System Preferences → Privacy & Security → Accessibility → Add your terminal app

## License

MIT
