"""macOS permission checking for Accessibility and Input Monitoring."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class PermissionStatus:
    """Status of required macOS permissions."""

    accessibility: bool
    input_monitoring: bool

    @property
    def all_granted(self) -> bool:
        """Return True if all permissions are granted."""
        return self.accessibility and self.input_monitoring


def check_accessibility_permission() -> bool:
    """Check if Accessibility permission is granted.

    Uses AXIsProcessTrusted() as primary method, with CGEventTapCreate
    fallback for reliability on newer macOS versions.

    Returns:
        True if Accessibility permission is granted.
    """
    # Try HIServices.AXIsProcessTrusted first
    try:
        import HIServices

        if HIServices.AXIsProcessTrusted():
            return True
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: Try creating an event tap (more reliable on Ventura+)
    try:
        from Quartz import (
            CGEventTapCreate,
            kCGEventTapOptionDefault,
            kCGHeadInsertEventTap,
            kCGSessionEventTap,
        )

        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            0,  # events mask
            lambda *args: None,  # callback
            None,  # refcon
        )
        return tap is not None
    except Exception:
        pass

    return False


def check_input_monitoring_permission() -> bool:
    """Check if Input Monitoring permission is granted.

    Uses IOHIDCheckAccess from IOKit framework (macOS 10.15+).

    Returns:
        True if Input Monitoring permission is granted.
    """
    try:
        import ctypes

        # Load IOKit framework
        IOKit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")

        # IOHIDCheckAccess(IOHIDRequestType type) -> IOHIDAccessType
        # kIOHIDRequestTypeListenEvent = 1 (for Input Monitoring)
        # Returns: 0 = granted, 1 = denied, 2 = unknown
        kIOHIDRequestTypeListenEvent = 1

        IOKit.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        IOKit.IOHIDCheckAccess.restype = ctypes.c_uint32

        result = IOKit.IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)

        # kIOHIDAccessTypeGranted = 0
        return result == 0
    except Exception:
        # Fallback: assume granted if we can't check
        return True


def get_permission_status() -> PermissionStatus:
    """Get the current status of all required permissions.

    Returns:
        PermissionStatus with current state of each permission.
    """
    return PermissionStatus(
        accessibility=check_accessibility_permission(),
        input_monitoring=check_input_monitoring_permission(),
    )


def open_accessibility_settings() -> None:
    """Open System Settings to the Accessibility privacy pane."""
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
        check=False,
    )


def open_input_monitoring_settings() -> None:
    """Open System Settings to the Input Monitoring privacy pane."""
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"],
        check=False,
    )


def get_permission_instructions() -> str:
    """Get instructions for granting permissions.

    Returns:
        Human-readable instructions for granting required permissions.
    """
    return """Voice Typer requires the following permissions:

1. **Accessibility** - Required to type transcribed text
   Go to: System Settings > Privacy & Security > Accessibility
   Add and enable Voice Typer (or your terminal app)

2. **Input Monitoring** - Required for hotkey detection
   Go to: System Settings > Privacy & Security > Input Monitoring
   Add and enable Voice Typer (or your terminal app)

After granting permissions, you may need to restart the app."""
