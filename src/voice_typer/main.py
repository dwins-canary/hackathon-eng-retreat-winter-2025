"""Main CLI entry point for Voice Typer."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from typing import NoReturn

from voice_typer.audio import AudioRecorder
from voice_typer.config import AVAILABLE_MODELS, Config, DEFAULT_CONFIG_PATH, DEFAULT_MODEL
from voice_typer.hotkey import KEY_MAP, HotkeyListener
from voice_typer.model_manager import (
    BackgroundDownloader,
    get_all_models_status,
    is_model_downloaded,
    ModelState,
)
from voice_typer.permissions import (
    get_permission_status,
    open_accessibility_settings,
    open_input_monitoring_settings,
)
from voice_typer.statusbar import show_model_selection_dialog, StatusBar
from voice_typer.transcribe import download_model, Transcriber
from voice_typer.typer import type_text


def is_running_in_terminal() -> bool:
    """Check if running in a terminal with stdin available."""
    import sys
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


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


def first_run_setup_terminal() -> Config:
    """Run first-time setup in terminal mode.

    Returns:
        Config instance with selected model.
    """
    print("=" * 50)
    print("Welcome to Voice Typer!")
    print("=" * 50)
    print()
    print("First, let's download a speech recognition model.")
    print("Choose a model based on your needs:")
    print()

    # Display available models
    for i, (model_id, description) in enumerate(AVAILABLE_MODELS, 1):
        print(f"  {i}. {description}")
    print()

    # Get user selection
    while True:
        try:
            choice = input(f"Enter your choice (1-{len(AVAILABLE_MODELS)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_MODELS):
                break
            print(f"Please enter a number between 1 and {len(AVAILABLE_MODELS)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

    selected_model, _ = AVAILABLE_MODELS[choice_num - 1]
    return _download_and_save_model(selected_model)


def first_run_setup_gui() -> Config:
    """Run first-time setup with GUI dialog.

    Returns:
        Config instance with selected model.
    """
    selected_model = show_model_selection_dialog()

    if selected_model is None:
        # User cancelled - use default
        selected_model = DEFAULT_MODEL

    return _download_and_save_model(selected_model)


def _download_and_save_model(model_id: str) -> Config:
    """Download model and save config.

    Args:
        model_id: Model ID to download.

    Returns:
        Config instance with selected model.
    """
    print(f"Selected model: {model_id}")

    # Download the model
    try:
        download_model(model_id)
    except KeyboardInterrupt:
        print("\nDownload interrupted. Run voice-typer again to resume.")
        sys.exit(0)

    # Create and save config
    config = Config(model=model_id)
    config.save()
    print(f"Configuration saved to {DEFAULT_CONFIG_PATH}")

    return config


def first_run_setup() -> Config:
    """Run first-time setup: model selection and download.

    Uses GUI dialog when not running in terminal, otherwise uses terminal input.

    Returns:
        Config instance with selected model.
    """
    if is_running_in_terminal():
        return first_run_setup_terminal()
    else:
        return first_run_setup_gui()


def main() -> NoReturn:
    """Main entry point."""
    args = parse_args()

    # Check for first run (no config file exists)
    if not DEFAULT_CONFIG_PATH.exists():
        config = first_run_setup()
    else:
        config = Config.load()

    # Apply CLI overrides
    config = config.override(
        hotkey=args.hotkey,
        model=args.model,
        language=args.language,
        verbose=args.verbose,
    )

    if config.verbose:
        print(f"Configuration: {config}")

    # Check permissions at startup (non-blocking)
    permission_status = get_permission_status()
    if not permission_status.all_granted:
        print("Warning: Some permissions are missing. App will start but may not function fully.")
        if not permission_status.accessibility:
            print("  - Accessibility permission required for typing text")
        if not permission_status.input_monitoring:
            print("  - Input Monitoring permission required for hotkey detection")

    # Get initial model status
    models_status = get_all_models_status()

    # Initialize components
    print(f"Using model: {config.model}")
    transcriber = Transcriber(model=config.model, language=config.language)

    recorder = AudioRecorder(sample_rate=config.sample_rate)
    status_bar: StatusBar | None = None

    # Track pending model switch (when download completes)
    pending_model_switch: str | None = None

    def cleanup() -> None:
        """Clean up resources."""
        nonlocal downloader
        downloader.cancel()
        listener.stop()
        recorder.close()
        if status_bar:
            status_bar.stop()
        print("Goodbye!")

    def on_quit() -> None:
        """Handle quit from status bar."""
        cleanup()
        sys.exit(0)

    def switch_to_model(model_id: str) -> None:
        """Switch to a model that is already downloaded."""
        nonlocal config, transcriber

        # Update config and save
        config = config.override(model=model_id)
        config.save()

        # Create new transcriber with new model
        transcriber = Transcriber(model=model_id, language=config.language)
        print(f"Now using model: {model_id}")

        # Update model status in menu to reflect current model
        if status_bar:
            status_bar.update_model_status(get_all_models_status())

    def on_download_complete(model_id: str, success: bool) -> None:
        """Handle download completion."""
        nonlocal pending_model_switch, models_status

        if success:
            print(f"Model {model_id} downloaded successfully")

            # Update model status
            models_status = get_all_models_status()
            if status_bar:
                status_bar.update_model_status(models_status)

            # If this was the pending model switch, do it now
            if pending_model_switch == model_id:
                pending_model_switch = None
                switch_to_model(model_id)
        else:
            print(f"Failed to download model {model_id}")
            # Update status to show error
            models_status = get_all_models_status()
            if status_bar:
                status_bar.update_model_status(models_status)

        pending_model_switch = None

    def on_download_progress(model_id: str, progress: float) -> None:
        """Handle download progress updates."""
        if status_bar:
            status_bar.update_download_progress(model_id, progress)

    # Create background downloader
    downloader = BackgroundDownloader(
        on_progress=on_download_progress,
        on_complete=on_download_complete,
    )

    def on_model_select(model_id: str) -> None:
        """Handle model selection from status bar menu."""
        nonlocal pending_model_switch

        if model_id == config.model:
            return  # Same model, nothing to do

        print(f"Switching to model: {model_id}")

        # Check if model is already downloaded
        if is_model_downloaded(model_id):
            # Model ready - switch immediately
            switch_to_model(model_id)
        else:
            # Need to download first - start background download
            print(f"Model not downloaded. Starting download...")
            pending_model_switch = model_id
            downloader.download(model_id)

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
        status_bar = StatusBar(
            on_quit=on_quit,
            on_model_select=on_model_select,
            current_model=config.model,
            permission_status=permission_status,
            models_status=models_status,
            on_open_accessibility=open_accessibility_settings,
            on_open_input_monitoring=open_input_monitoring_settings,
        )
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
    # Required for PyInstaller multiprocessing support on macOS
    import multiprocessing
    multiprocessing.freeze_support()
    main()
