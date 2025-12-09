# Voice Typer UX Improvements: Permissions & Model Management

## Summary
Streamline the first-run and ongoing UX by adding permission status checking and better model management in the menu bar.

## Requirements
1. **Permissions**: Check Accessibility & Input Monitoring on startup, show status in menu, provide instructions if missing (non-blocking - app starts anyway)
2. **Model Status**: Separate menu section showing all 4 models with download state
3. **Background Downloads**: When user selects undownloaded model, download in background with progress in menu bar

---

## Implementation Plan

### Phase 1: Create `src/voice_typer/permissions.py` (new file)

```python
@dataclass
class PermissionStatus:
    accessibility: bool
    input_monitoring: bool

def check_accessibility_permission() -> bool
    # Primary: HIServices.AXIsProcessTrusted()
    # Fallback: CGEventTapCreate() test

def check_input_monitoring_permission() -> bool
    # Use pynput.keyboard.Listener, check IS_TRUSTED attribute

def get_permission_status() -> PermissionStatus

def open_accessibility_settings() -> None
    # subprocess: open x-apple.systempreferences:...?Privacy_Accessibility

def open_input_monitoring_settings() -> None
    # subprocess: open x-apple.systempreferences:...?Privacy_ListenEvent
```

### Phase 2: Create `src/voice_typer/model_manager.py` (new file)

```python
class ModelState(Enum):
    NOT_DOWNLOADED, DOWNLOADING, DOWNLOADED, ERROR

@dataclass
class ModelInfo:
    model_id: str
    display_name: str
    size_info: str
    state: ModelState
    download_progress: float  # 0.0 to 1.0

CACHE_DIR = Path.home() / "Library" / "Caches" / "voice-typer" / "models"

def is_model_downloaded(model_id: str) -> bool
    # Check for weights.npz in cache_dir / model_id.replace("/", "--")

def get_all_models_status() -> list[ModelInfo]
    # Query all AVAILABLE_MODELS

class BackgroundDownloader:
    def __init__(on_progress, on_complete): ...
    def download(model_id): ...  # threaded, uses huggingface_hub
    def cancel(): ...
```

### Phase 3: Modify `src/voice_typer/statusbar.py`

**New menu structure:**
```
[Status: Ready]
---
[Permissions]
  > Accessibility: ✅ / ⚠️ (clickable if warning → opens settings)
  > Input Monitoring: ✅ / ⚠️
  > Instructions... (if any missing → shows dialog)
---
[Model Status]
  > Whisper Tiny (75MB): Downloaded ✓
  > Whisper Turbo (1.5GB): Downloading 45%
  > Whisper Large v3 Turbo (3GB): Not downloaded
  > Whisper Large v3 (3GB): Not downloaded
---
[Select Model]
  > (existing model selection with checkmark on current)
---
[Quit]
```

**StatusBarApp changes:**
- New constructor params: `permission_status`, `models_status`, `on_open_accessibility`, `on_open_input_monitoring`
- New methods: `update_permission_status()`, `update_model_status()`, `update_download_progress()`, `show_permission_instructions()`
- Menu bar icon shows warning if permissions missing

### Phase 4: Modify `src/voice_typer/main.py`

At startup (before StatusBar creation):
```python
# Check permissions (non-blocking)
permission_status = get_permission_status()
if not permission_status.all_granted:
    print("Warning: Some permissions missing...")

# Get initial model status
models_status = get_all_models_status()

# Create background downloader with callbacks
downloader = BackgroundDownloader(
    on_progress=lambda mid, p: status_bar.update_download_progress(mid, p),
    on_complete=on_download_complete,
)
```

Update `on_model_select()`:
- If model not downloaded → start background download, don't switch yet
- If downloaded → switch immediately

Add `on_download_complete()`:
- Update model status in menu
- Switch to model if it was the pending selection

Pass new params to StatusBar constructor.

### Phase 5: Minor updates to `src/voice_typer/config.py`

Add: `MODEL_CACHE_DIR = Path.home() / "Library" / "Caches" / "voice-typer" / "models"`

### Phase 6: Update `src/voice_typer/transcribe.py`

Use `MODEL_CACHE_DIR` from config instead of hardcoded path.

---

## Files to Modify
- `src/voice_typer/permissions.py` - **NEW**
- `src/voice_typer/model_manager.py` - **NEW**
- `src/voice_typer/statusbar.py` - Major changes (menu structure, new methods)
- `src/voice_typer/main.py` - Integration (permission check, downloader setup)
- `src/voice_typer/config.py` - Add MODEL_CACHE_DIR constant
- `src/voice_typer/transcribe.py` - Use shared cache constant

## Key Technical Notes
- Use `rumps.Timer` for thread-safe menu updates from background download thread
- Override tqdm class in `snapshot_download` for progress callbacks
- Permission checks are fast and non-blocking
- huggingface_hub supports download resume automatically
