"""Menu bar status icon using rumps."""

from __future__ import annotations

import threading
from collections.abc import Callable
from enum import Enum
from typing import Any

import rumps


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

    def __init__(self, on_quit: Callable[[], None] | None = None) -> None:
        """Initialize the status bar app.

        Args:
            on_quit: Optional callback when user clicks Quit.
        """
        super().__init__(
            name="Voice Typer",
            title=STATE_ICONS[AppState.IDLE],
            quit_button=None,  # We'll add our own
        )
        self._state = AppState.IDLE
        self._on_quit = on_quit

        # Add menu items
        self._status_item = rumps.MenuItem("Status: Ready")
        self._status_item.set_callback(None)  # Not clickable

        self.menu = [
            self._status_item,
            None,  # Separator
            rumps.MenuItem("Quit", callback=self._handle_quit),
        ]

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

    def __init__(self, on_quit: Callable[[], None] | None = None) -> None:
        """Initialize the status bar wrapper.

        Args:
            on_quit: Optional callback when user clicks Quit.
        """
        self._app: StatusBarApp | None = None
        self._on_quit = on_quit

    def start(self) -> None:
        """Initialize the status bar app (does not block).

        Call run() on the main thread to start the event loop.
        """
        if self._app is not None:
            return

        self._app = StatusBarApp(on_quit=self._on_quit)

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
