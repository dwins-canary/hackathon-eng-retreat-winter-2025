# 🎙️ Voice Typer

A macOS push-to-talk speech-to-text tool. Hold a hotkey to record, release to transcribe and type at your cursor position. Uses MLX Whisper for fast, private, local transcription on Apple Silicon.

## 📦 Installation

Download the latest `.dmg` from [Releases](https://github.com/anthropics/hackathon-eng-retreat-winter-2025/releases) and drag Voice Typer to Applications.

## 🚀 Usage

1. Launch Voice Typer from Applications
2. Grant **Microphone** 🎤 and **Accessibility** ♿ permissions when prompted
3. Select a Whisper model on first run (it will download automatically)
4. Hold the hotkey (default: Right Option) to record, release to transcribe

The menu bar icon shows the current state: 😴 idle, 🔴 recording, or ⏳ transcribing.

## ⚙️ Configuration

Right-click the menu bar icon to:
- 🔑 Change the hotkey
- 🤖 Switch Whisper models
- 🌍 Set language preferences

Settings are saved to `~/.config/voice-typer/config.toml`.

## 🛠️ Development

```bash
git clone https://github.com/anthropics/hackathon-eng-retreat-winter-2025.git
cd hackathon-eng-retreat-winter-2025
uv sync
uv run voice-typer
```

## 📄 License

MIT
