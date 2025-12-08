"""Global hotkey listener using pynput."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from pynput import keyboard

# Mapping of friendly names to pynput key objects
KEY_MAP: dict[str, Any] = {
    # Function keys (for Karabiner Fn mapping)
    "f18": keyboard.Key.f18,
    "f17": keyboard.Key.f17,
    "f16": keyboard.Key.f16,
    "f15": keyboard.Key.f15,
    "f14": keyboard.Key.f14,
    "f13": keyboard.Key.f13,
    # Modifier keys
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "alt": keyboard.Key.alt,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl": keyboard.Key.ctrl,
    "cmd_r": keyboard.Key.cmd_r,
    "cmd_l": keyboard.Key.cmd_l,
    "cmd": keyboard.Key.cmd,
    "shift_r": keyboard.Key.shift_r,
    "shift_l": keyboard.Key.shift_l,
    "shift": keyboard.Key.shift,
    # Special keys
    "caps_lock": keyboard.Key.caps_lock,
    "space": keyboard.Key.space,
}


def parse_hotkey(hotkey_str: str) -> Any:
    """Parse a hotkey string into a pynput key.

    Args:
        hotkey_str: Key name like "f18", "alt_r", etc.

    Returns:
        pynput Key object.

    Raises:
        ValueError: If the key is not recognized.
    """
    key_lower = hotkey_str.lower().strip()

    if key_lower in KEY_MAP:
        return KEY_MAP[key_lower]

    # Try to parse as a character key
    if len(key_lower) == 1:
        return keyboard.KeyCode.from_char(key_lower)

    raise ValueError(
        f"Unknown hotkey: {hotkey_str}. "
        f"Valid options: {', '.join(sorted(KEY_MAP.keys()))}"
    )


class HotkeyListener:
    """Listens for a global hotkey and fires callbacks on press/release."""

    def __init__(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        """Initialize the hotkey listener.

        Args:
            hotkey: Key name (e.g., "f18", "alt_r").
            on_press: Callback when key is pressed.
            on_release: Callback when key is released.
        """
        self.target_key = parse_hotkey(hotkey)
        self.on_press_callback = on_press
        self.on_release_callback = on_release
        self._listener: keyboard.Listener | None = None
        self._pressed = False
        self._lock = threading.Lock()

    def _on_press(self, key: Any) -> None:
        """Handle key press events."""
        if key == self.target_key:
            with self._lock:
                if not self._pressed:
                    self._pressed = True
                    try:
                        self.on_press_callback()
                    except Exception as e:
                        print(f"Error in on_press callback: {e}")

    def _on_release(self, key: Any) -> None:
        """Handle key release events."""
        if key == self.target_key:
            with self._lock:
                if self._pressed:
                    self._pressed = False
                    try:
                        self.on_release_callback()
                    except Exception as e:
                        print(f"Error in on_release callback: {e}")

    def start(self) -> None:
        """Start listening for the hotkey."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def join(self) -> None:
        """Wait for the listener to finish."""
        if self._listener is not None:
            self._listener.join()

    def __enter__(self) -> HotkeyListener:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
