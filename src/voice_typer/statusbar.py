"""Menu bar status icon using rumps."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

import rumps

from voice_typer.config import AVAILABLE_MODELS, DEFAULT_MODEL
from voice_typer.model_manager import ModelInfo, ModelState
from voice_typer.permissions import PermissionStatus, get_permission_instructions


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
    DOWNLOADING = "downloading"


# Unicode icons for each state
STATE_ICONS: dict[AppState, str] = {
    AppState.IDLE: "\U0001f3a4",  # Microphone emoji
    AppState.RECORDING: "\U0001f534",  # Red circle
    AppState.TRANSCRIBING: "\u231b",  # Hourglass
    AppState.DOWNLOADING: "\u2b07",  # Down arrow
}

STATE_LABELS: dict[AppState, str] = {
    AppState.IDLE: "Ready",
    AppState.RECORDING: "Recording...",
    AppState.TRANSCRIBING: "Transcribing...",
    AppState.DOWNLOADING: "Downloading...",
}

# Permission status icons
PERMISSION_OK = "\u2705"  # Green checkmark
PERMISSION_MISSING = "\u26a0\ufe0f"  # Warning sign

# Menu bar icons for different states
MENUBAR_ICON_READY = "\U0001f3a4"  # Microphone
MENUBAR_ICON_WARNING = "\u26a0\ufe0f"  # Warning (permissions missing)
MENUBAR_ICON_RECORDING = "\U0001f534"  # Red circle
MENUBAR_ICON_TRANSCRIBING = "\u231b"  # Hourglass
MENUBAR_ICON_DOWNLOADING = "\u2b07"  # Down arrow


class StatusBarApp(rumps.App):
    """macOS menu bar status icon for Voice Typer."""

    def __init__(
        self,
        on_quit: Callable[[], None] | None = None,
        on_model_select: Callable[[str], None] | None = None,
        current_model: str | None = None,
        permission_status: PermissionStatus | None = None,
        models_status: list[ModelInfo] | None = None,
        on_open_accessibility: Callable[[], None] | None = None,
        on_open_input_monitoring: Callable[[], None] | None = None,
        on_open_microphone: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the status bar app.

        Args:
            on_quit: Optional callback when user clicks Quit.
            on_model_select: Optional callback when user selects a model.
            current_model: Currently selected model ID.
            permission_status: Current permission status.
            models_status: List of model info with download states.
            on_open_accessibility: Callback to open Accessibility settings.
            on_open_input_monitoring: Callback to open Input Monitoring settings.
            on_open_microphone: Callback to open Microphone settings.
        """
        # Determine initial icon based on permissions
        initial_icon = MENUBAR_ICON_READY
        if permission_status and not permission_status.all_granted:
            initial_icon = MENUBAR_ICON_WARNING

        super().__init__(
            name="Voice Typer",
            title=initial_icon,
            quit_button=None,  # We'll add our own
        )
        self._state = AppState.IDLE
        self._on_quit = on_quit
        self._on_model_select = on_model_select
        self._current_model = current_model
        self._permission_status = permission_status or PermissionStatus(True, True, True)
        self._models_status = models_status or []
        self._on_open_accessibility = on_open_accessibility
        self._on_open_input_monitoring = on_open_input_monitoring
        self._on_open_microphone = on_open_microphone
        self._is_downloading = False

        # Build menu
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the complete menu structure."""
        # Status item
        self._status_item = rumps.MenuItem("Status: Ready")
        self._status_item.set_callback(None)  # Not clickable

        # Permissions submenu
        self._permissions_menu = rumps.MenuItem("Permissions")
        self._accessibility_item = self._create_permission_item(
            "Accessibility",
            self._permission_status.accessibility,
            self._handle_open_accessibility,
        )
        self._input_monitoring_item = self._create_permission_item(
            "Input Monitoring",
            self._permission_status.input_monitoring,
            self._handle_open_input_monitoring,
        )
        self._microphone_item = self._create_permission_item(
            "Microphone",
            self._permission_status.microphone,
            self._handle_open_microphone,
        )
        self._permissions_menu.add(self._accessibility_item)
        self._permissions_menu.add(self._input_monitoring_item)
        self._permissions_menu.add(self._microphone_item)

        # Add instructions item if any permission is missing
        if not self._permission_status.all_granted:
            self._permissions_menu.add(None)  # Separator
            instructions_item = rumps.MenuItem(
                "How to Grant Permissions...",
                callback=self._show_permission_instructions,
            )
            self._permissions_menu.add(instructions_item)

        # Model Status section
        self._model_status_menu = rumps.MenuItem("Model Status")
        self._model_status_items: dict[str, rumps.MenuItem] = {}
        self._update_model_status_menu()

        # Model selection submenu
        self._model_menu = rumps.MenuItem("Select Model")
        self._model_items: dict[str, rumps.MenuItem] = {}
        for model_id, description in AVAILABLE_MODELS:
            # Extract short name from description
            short_name = description.split(" - ")[0]
            item = rumps.MenuItem(short_name, callback=self._handle_model_select)
            item.model_id = model_id  # Store model ID on the item
            if model_id == self._current_model:
                item.state = 1  # Checkmark
            self._model_items[model_id] = item
            self._model_menu.add(item)

        self.menu = [
            self._status_item,
            None,  # Separator
            self._permissions_menu,
            None,  # Separator
            self._model_status_menu,
            None,  # Separator
            self._model_menu,
            None,  # Separator
            rumps.MenuItem("Quit", callback=self._handle_quit),
        ]

    def _create_permission_item(
        self,
        name: str,
        granted: bool,
        callback: Callable[[Any], None] | None,
    ) -> rumps.MenuItem:
        """Create a permission menu item with status icon.

        Args:
            name: Permission name.
            granted: Whether permission is granted.
            callback: Callback when clicked (only if not granted).

        Returns:
            MenuItem with status icon.
        """
        icon = PERMISSION_OK if granted else PERMISSION_MISSING
        title = f"{name}: {icon}"
        item = rumps.MenuItem(title)
        if not granted and callback:
            item.set_callback(callback)
        else:
            item.set_callback(None)
        return item

    def _update_model_status_menu(self) -> None:
        """Update the model status submenu with current states."""
        # Clear existing items only if menu is already initialized
        # (rumps menus can't be cleared before they're attached to the app)
        if hasattr(self._model_status_menu, "_menu") and self._model_status_menu._menu is not None:
            self._model_status_menu.clear()

        self._model_status_items.clear()

        for model_info in self._models_status:
            title = self._format_model_status_title(model_info)
            item = rumps.MenuItem(title)
            item.set_callback(None)  # Status items are not clickable
            self._model_status_items[model_info.model_id] = item
            self._model_status_menu.add(item)

        # If no models, show placeholder
        if not self._models_status:
            placeholder = rumps.MenuItem("No models configured")
            placeholder.set_callback(None)
            self._model_status_menu.add(placeholder)

    def _format_model_status_title(self, model_info: ModelInfo) -> str:
        """Format model status for menu display.

        Args:
            model_info: Model information.

        Returns:
            Formatted title string.
        """
        name = model_info.display_name
        size = f"({model_info.size_info})" if model_info.size_info else ""

        if model_info.state == ModelState.DOWNLOADED:
            status = "\u2705"  # Green checkmark
            if model_info.model_id == self._current_model:
                status += " (current)"
        elif model_info.state == ModelState.DOWNLOADING:
            if model_info.download_progress > 0:
                progress_pct = int(model_info.download_progress * 100)
                status = f"\u2b07 {progress_pct}%"  # Down arrow with percentage
            else:
                status = "\u2b07 Downloading..."  # Down arrow, indeterminate
        elif model_info.state == ModelState.ERROR:
            status = "\u274c"  # Red X
        else:
            status = "Not downloaded"

        return f"{name} {size}: {status}"

    def _handle_open_accessibility(self, sender: Any) -> None:
        """Handle click on Accessibility permission item."""
        if self._on_open_accessibility:
            self._on_open_accessibility()

    def _handle_open_input_monitoring(self, sender: Any) -> None:
        """Handle click on Input Monitoring permission item."""
        if self._on_open_input_monitoring:
            self._on_open_input_monitoring()

    def _handle_open_microphone(self, sender: Any) -> None:
        """Handle click on Microphone permission item."""
        if self._on_open_microphone:
            self._on_open_microphone()

    def _show_permission_instructions(self, sender: Any) -> None:
        """Show dialog with permission instructions."""
        rumps.alert(
            title="Permission Instructions",
            message=get_permission_instructions(),
            ok="OK",
        )

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
        self._update_title_icon()
        self._status_item.title = f"Status: {STATE_LABELS[state]}"

    def _update_title_icon(self) -> None:
        """Update menu bar icon based on current state."""
        if self._state == AppState.RECORDING:
            self.title = MENUBAR_ICON_RECORDING
        elif self._state == AppState.TRANSCRIBING:
            self.title = MENUBAR_ICON_TRANSCRIBING
        elif self._is_downloading:
            self.title = MENUBAR_ICON_DOWNLOADING
        elif not self._permission_status.all_granted:
            self.title = MENUBAR_ICON_WARNING
        else:
            self.title = MENUBAR_ICON_READY

    def update_permission_status(self, status: PermissionStatus) -> None:
        """Update permission indicators in menu.

        Args:
            status: New permission status.
        """
        self._permission_status = status

        # Update menu items
        acc_icon = PERMISSION_OK if status.accessibility else PERMISSION_MISSING
        self._accessibility_item.title = f"Accessibility: {acc_icon}"
        if status.accessibility:
            self._accessibility_item.set_callback(None)

        inp_icon = PERMISSION_OK if status.input_monitoring else PERMISSION_MISSING
        self._input_monitoring_item.title = f"Input Monitoring: {inp_icon}"
        if status.input_monitoring:
            self._input_monitoring_item.set_callback(None)

        mic_icon = PERMISSION_OK if status.microphone else PERMISSION_MISSING
        self._microphone_item.title = f"Microphone: {mic_icon}"
        if status.microphone:
            self._microphone_item.set_callback(None)

        # Update menu bar icon
        self._update_title_icon()

    def update_model_status(self, models: list[ModelInfo]) -> None:
        """Update model status section.

        Args:
            models: Updated list of model info.
        """
        self._models_status = models
        self._update_model_status_menu()

        # Check if any model is downloading
        self._is_downloading = any(m.state == ModelState.DOWNLOADING for m in models)
        self._update_title_icon()

    def update_download_progress(self, model_id: str, progress: float) -> None:
        """Update download progress for a specific model.

        Args:
            model_id: Model being downloaded.
            progress: Progress from 0.0 to 1.0.
        """
        # Find and update the model info
        for model_info in self._models_status:
            if model_info.model_id == model_id:
                model_info.state = ModelState.DOWNLOADING
                model_info.download_progress = progress
                break

        # Update the specific menu item
        if model_id in self._model_status_items:
            for model_info in self._models_status:
                if model_info.model_id == model_id:
                    self._model_status_items[model_id].title = self._format_model_status_title(
                        model_info
                    )
                    break

        # Update menu bar icon if needed
        if not self._is_downloading:
            self._is_downloading = True
            self._update_title_icon()

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
        permission_status: PermissionStatus | None = None,
        models_status: list[ModelInfo] | None = None,
        on_open_accessibility: Callable[[], None] | None = None,
        on_open_input_monitoring: Callable[[], None] | None = None,
        on_open_microphone: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the status bar wrapper.

        Args:
            on_quit: Optional callback when user clicks Quit.
            on_model_select: Optional callback when user selects a model.
            current_model: Currently selected model ID.
            permission_status: Current permission status.
            models_status: List of model info with download states.
            on_open_accessibility: Callback to open Accessibility settings.
            on_open_input_monitoring: Callback to open Input Monitoring settings.
            on_open_microphone: Callback to open Microphone settings.
        """
        self._app: StatusBarApp | None = None
        self._on_quit = on_quit
        self._on_model_select = on_model_select
        self._current_model = current_model
        self._permission_status = permission_status
        self._models_status = models_status
        self._on_open_accessibility = on_open_accessibility
        self._on_open_input_monitoring = on_open_input_monitoring
        self._on_open_microphone = on_open_microphone

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
            permission_status=self._permission_status,
            models_status=self._models_status,
            on_open_accessibility=self._on_open_accessibility,
            on_open_input_monitoring=self._on_open_input_monitoring,
            on_open_microphone=self._on_open_microphone,
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

    def update_permission_status(self, status: PermissionStatus) -> None:
        """Update permission indicators in menu.

        Args:
            status: New permission status.
        """
        if self._app:
            self._app.update_permission_status(status)

    def update_model_status(self, models: list[ModelInfo]) -> None:
        """Update model status section.

        Args:
            models: Updated list of model info.
        """
        if self._app:
            self._app.update_model_status(models)

    def update_download_progress(self, model_id: str, progress: float) -> None:
        """Update download progress for a specific model.

        Args:
            model_id: Model being downloaded.
            progress: Progress from 0.0 to 1.0.
        """
        if self._app:
            self._app.update_download_progress(model_id, progress)

    def stop(self) -> None:
        """Stop the status bar."""
        if self._app:
            rumps.quit_application()
