"""Main CLI entry point for Voice Typer."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from typing import NoReturn

from voice_typer.audio import AudioRecorder
from voice_typer.config import Config
from voice_typer.hotkey import KEY_MAP, HotkeyListener
from voice_typer.statusbar import StatusBar
from voice_typer.transcribe import Transcriber
from voice_typer.typer import type_text


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Push-to-talk speech-to-text for macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  voice-typer                    # Use default settings
  voice-typer --hotkey f18       # Use F18 key (for Karabiner Fn mapping)
  voice-typer --hotkey alt_r     # Use Right Option key
  voice-typer --model mlx-community/whisper-large-v3

Available hotkeys: {', '.join(sorted(KEY_MAP.keys()))}
""",
    )
    parser.add_argument(
        "--hotkey",
        "-k",
        type=str,
        help="Hotkey to trigger recording (default: alt_r)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        help="MLX Whisper model to use (default: mlx-community/whisper-large-v3-turbo)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        help="Force language detection (e.g., 'en', 'es')",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-statusbar",
        action="store_true",
        help="Disable menu bar status icon",
    )
    return parser.parse_args()


def main() -> NoReturn:
    """Main entry point."""
    args = parse_args()

    # Load config and apply CLI overrides
    config = Config.load().override(
        hotkey=args.hotkey,
        model=args.model,
        language=args.language,
        verbose=args.verbose,
    )

    if config.verbose:
        print(f"Configuration: {config}")

    # Initialize components
    print(f"Loading model: {config.model}")
    print("(First run will download the model, ~3GB)")
    transcriber = Transcriber(model=config.model, language=config.language)

    recorder = AudioRecorder(sample_rate=config.sample_rate)
    status_bar: StatusBar | None = None

    def cleanup() -> None:
        """Clean up resources."""
        listener.stop()
        recorder.close()
        if status_bar:
            status_bar.stop()
        print("Goodbye!")

    def on_quit() -> None:
        """Handle quit from status bar."""
        cleanup()
        sys.exit(0)

    # Recording state
    is_recording = False

    def on_press() -> None:
        """Handle hotkey press - start recording."""
        nonlocal is_recording
        if is_recording:
            return

        is_recording = True
        recorder.start()
        if status_bar:
            status_bar.set_recording()
        if config.verbose:
            print("Recording...")

    def on_release() -> None:
        """Handle hotkey release - stop recording and transcribe."""
        nonlocal is_recording
        if not is_recording:
            return

        is_recording = False

        # Stop recording and get audio
        audio = recorder.stop()

        if len(audio) == 0:
            if config.verbose:
                print("No audio recorded")
            if status_bar:
                status_bar.set_idle()
            return

        duration = len(audio) / config.sample_rate
        if config.verbose:
            print(f"Recorded {duration:.1f}s of audio")

        # Transcribe
        if status_bar:
            status_bar.set_transcribing()
        if config.verbose:
            print("Transcribing...")

        try:
            text = transcriber.transcribe(audio, sample_rate=config.sample_rate)
        except Exception as e:
            print(f"Transcription error: {e}")
            if status_bar:
                status_bar.set_idle()
            return

        if status_bar:
            status_bar.set_idle()

        if not text:
            if config.verbose:
                print("No text transcribed")
            return

        # Type the text
        if config.verbose:
            print(f"Typing: {text}")
        else:
            print(f"> {text}")

        type_text(text, delay=config.type_delay)

    # Set up hotkey listener
    listener = HotkeyListener(
        hotkey=config.hotkey,
        on_press=on_press,
        on_release=on_release,
    )

    # Handle shutdown signals
    def signal_handler(signum: int, frame) -> None:
        print("\nShutting down...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start listening
    print(f"Ready! Hold [{config.hotkey}] to record, release to transcribe.")
    print("Press Ctrl+C to quit.")

    listener.start()

    # Start status bar if enabled (must run on main thread for macOS)
    if not args.no_statusbar:
        status_bar = StatusBar(on_quit=on_quit)
        status_bar.start()
        # This blocks until the app quits
        status_bar.run()
    else:
        # No status bar - just wait forever
        shutdown_event = threading.Event()
        try:
            shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        cleanup()

    sys.exit(0)


if __name__ == "__main__":
    main()
