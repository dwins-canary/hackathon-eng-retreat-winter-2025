"""Text injection module using macOS CGEvents."""

from __future__ import annotations

import time

from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventKeyboardSetUnicodeString,
    CGEventPost,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGHIDEventTap,
)



def type_text(text: str, delay: float = 0.01) -> None:
    """Type text at the current cursor position using CGEvents.

    This injects keyboard events at the system level, typing into
    whatever application currently has focus.

    Args:
        text: The text to type.
        delay: Delay between characters (seconds). Small delay helps
               ensure characters aren't dropped.
    """
    print(f"Typing text: {text}")
    if not text:
        return

    for char in text:
        _type_character(char)
        if delay > 0:
            time.sleep(delay)


def _type_character(char: str) -> None:
    """Type a single character using CGEvents.

    Args:
        char: Single character to type.
    """
    # Create a key down event (keycode 0 is placeholder, we set unicode directly)
    key_down = CGEventCreateKeyboardEvent(None, 0, True)
    key_up = CGEventCreateKeyboardEvent(None, 0, False)
    if key_down is None or key_up is None:
        raise RuntimeError("Failed to create keyboard event")

    # Set the unicode character to type
    CGEventKeyboardSetUnicodeString(key_down, len(char), char)
    CGEventKeyboardSetUnicodeString(key_up, len(char), char)

    # Post the events to the HID event tap
    CGEventPost(kCGHIDEventTap, key_down)
    CGEventPost(kCGHIDEventTap, key_up)


def type_text_fast(text: str) -> None:
    """Type text faster by batching characters.

    This types text in larger chunks which is faster but may be
    less reliable for some applications.

    Args:
        text: The text to type.
    """
    if not text:
        return

    # Type in chunks of up to 20 characters
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        _type_string_chunk(chunk)
        time.sleep(0.01)  # Small delay between chunks


def _type_string_chunk(text: str) -> None:
    """Type a string chunk using CGEvents.

    Args:
        text: String chunk to type (up to ~20 chars works reliably).
    """
    key_down = CGEventCreateKeyboardEvent(None, 0, True)
    key_up = CGEventCreateKeyboardEvent(None, 0, False)

    if key_down is None or key_up is None:
        raise RuntimeError("Failed to create keyboard event")

    CGEventKeyboardSetUnicodeString(key_down, len(text), text)
    CGEventKeyboardSetUnicodeString(key_up, len(text), text)

    CGEventPost(kCGHIDEventTap, key_down)
    CGEventPost(kCGHIDEventTap, key_up)
