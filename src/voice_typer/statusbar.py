"""Menu bar status icon using rumps."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

import rumps

from voice_typer.config import AVAILABLE_MODELS, DEFAULT_MODEL


def show_model_selection_dialog() -> str | None:
    """Show a dialog to select a model.

    Returns:
        Selected model ID, or None if cancelled.
    """
    # Build options list with short names
    options = []
    model_map = {}
    for model_id, description in AVAILABLE_MODELS:
        short_name = description.split(" - ")[0]
        size_info = description.split("(")[-1].rstrip(")")
        display_name = f"{short_name} ({size_info})"
        options.append(display_name)
        model_map[display_name] = model_id

    # Show alert with dropdown
    response = rumps.Window(
        title="Welcome to Voice Typer!",
        message="Select a speech recognition model to download:",
        default_text="",
        ok="Download",
        cancel="Use Default",
        dimensions=(0, 0),  # No text input
    ).run()

    if response.clicked:
        # User clicked Download - show selection window
        # Since rumps.Window doesn't support dropdowns, use a simple alert
        # with multiple buttons for model selection
        pass

    # Fallback: Use a simpler approach with rumps.alert
    message = "Select a model:\n\n"
    for i, (model_id, description) in enumerate(AVAILABLE_MODELS, 1):
        message += f"{i}. {description}\n"

    response = rumps.Window(
        title="Voice Typer - Model Selection",
        message=message,
        default_text="2",  # Default to Whisper Turbo
        ok="Download",
        cancel="Cancel",
    ).run()

    if response.clicked and response.text:
        try:
            choice = int(response.text.strip())
            if 1 <= choice <= len(AVAILABLE_MODELS):
                return AVAILABLE_MODELS[choice - 1][0]
        except ValueError:
            pass

    # Return default model if cancelled or invalid
    return DEFAULT_MODEL if response.clicked else None


class AppState(Enum):
    """Application states with corresponding icons."""

    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


# Unicode icons for each state
STATE_ICONS: dict[AppState, str] = {
    AppState.IDLE: "\U0001F3A4",  # Microphone emoji
    AppState.RECORDING: "\U0001F534",  # Red circle
    AppState.TRANSCRIBING: "\u231B",  # Hourglass
}

STATE_LABELS: dict[AppState, str] = {
    AppState.IDLE: "Ready",
    AppState.RECORDING: "Recording...",
    AppState.TRANSCRIBING: "Transcribing...",
}


class StatusBarApp(rumps.App):
    """macOS menu bar status icon for Voice Typer."""

    def __init__(
        self,
        on_quit: Callable[[], None] | None = None,
        on_model_select: Callable[[str], None] | None = None,
        current_model: str | None = None,
    ) -> None:
        """Initialize the status bar app.

        Args:
            on_quit: Optional callback when user clicks Quit.
            on_model_select: Optional callback when user selects a model.
            current_model: Currently selected model ID.
        """
        super().__init__(
            name="Voice Typer",
            title=STATE_ICONS[AppState.IDLE],
            quit_button=None,  # We'll add our own
        )
        self._state = AppState.IDLE
        self._on_quit = on_quit
        self._on_model_select = on_model_select
        self._current_model = current_model

        # Add menu items
        self._status_item = rumps.MenuItem("Status: Ready")
        self._status_item.set_callback(None)  # Not clickable

        # Create model selection submenu
        self._model_menu = rumps.MenuItem("Select Model")
        self._model_items: dict[str, rumps.MenuItem] = {}
        for model_id, description in AVAILABLE_MODELS:
            # Extract short name from description
            short_name = description.split(" - ")[0]
            item = rumps.MenuItem(short_name, callback=self._handle_model_select)
            item.model_id = model_id  # Store model ID on the item
            if model_id == current_model:
                item.state = 1  # Checkmark
            self._model_items[model_id] = item
            self._model_menu.add(item)

        self.menu = [
            self._status_item,
            None,  # Separator
            self._model_menu,
            None,  # Separator
            rumps.MenuItem("Quit", callback=self._handle_quit),
        ]

    def _handle_model_select(self, sender: Any) -> None:
        """Handle model selection from menu."""
        model_id = sender.model_id
        if model_id == self._current_model:
            return  # Already selected

        # Update checkmarks
        for mid, item in self._model_items.items():
            item.state = 1 if mid == model_id else 0

        self._current_model = model_id

        if self._on_model_select:
            self._on_model_select(model_id)

    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state

    def set_state(self, state: AppState) -> None:
        """Update the application state and icon.

        Args:
            state: New state to display.
        """
        self._state = state
        self.title = STATE_ICONS[state]
        self._status_item.title = f"Status: {STATE_LABELS[state]}"

    def _handle_quit(self, sender: Any) -> None:
        """Handle quit menu item click."""
        if self._on_quit:
            self._on_quit()
        rumps.quit_application()


class StatusBar:
    """Wrapper to run StatusBarApp on the main thread.

    macOS requires all AppKit/UI operations to run on the main thread.
    This class provides the interface for the status bar and must have
    its run() method called from the main thread.
    """

    def __init__(
        self,
        on_quit: Callable[[], None] | None = None,
        on_model_select: Callable[[str], None] | None = None,
        current_model: str | None = None,
    ) -> None:
        """Initialize the status bar wrapper.

        Args:
            on_quit: Optional callback when user clicks Quit.
            on_model_select: Optional callback when user selects a model.
            current_model: Currently selected model ID.
        """
        self._app: StatusBarApp | None = None
        self._on_quit = on_quit
        self._on_model_select = on_model_select
        self._current_model = current_model

    def start(self) -> None:
        """Initialize the status bar app (does not block).

        Call run() on the main thread to start the event loop.
        """
        if self._app is not None:
            return

        self._app = StatusBarApp(
            on_quit=self._on_quit,
            on_model_select=self._on_model_select,
            current_model=self._current_model,
        )

    def run(self) -> None:
        """Run the rumps application event loop.

        This MUST be called from the main thread and will block until
        the application quits.
        """
        if self._app:
            self._app.run()

    def set_state(self, state: AppState) -> None:
        """Update the status bar state.

        Args:
            state: New state to display.
        """
        if self._app:
            # rumps is not thread-safe, but title updates seem to work
            self._app.set_state(state)

    def set_idle(self) -> None:
        """Set state to idle."""
        self.set_state(AppState.IDLE)

    def set_recording(self) -> None:
        """Set state to recording."""
        self.set_state(AppState.RECORDING)

    def set_transcribing(self) -> None:
        """Set state to transcribing."""
        self.set_state(AppState.TRANSCRIBING)

    def stop(self) -> None:
        """Stop the status bar."""
        if self._app:
            rumps.quit_application()
