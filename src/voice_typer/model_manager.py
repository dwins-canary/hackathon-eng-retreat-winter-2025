"""Model status checking and background download management."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from voice_typer.config import AVAILABLE_MODELS, MODEL_CACHE_DIR


class ModelState(Enum):
    """State of a model download."""

    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about an available model."""

    model_id: str
    display_name: str
    description: str
    size_info: str
    state: ModelState = ModelState.NOT_DOWNLOADED
    download_progress: float = 0.0  # 0.0 to 1.0


def get_model_cache_path(model_id: str) -> Path:
    """Convert model_id to local cache path.

    Args:
        model_id: HuggingFace model ID (e.g., "mlx-community/whisper-turbo").

    Returns:
        Path to the model's cache directory.
    """
    return MODEL_CACHE_DIR / model_id.replace("/", "--")


def is_model_downloaded(model_id: str) -> bool:
    """Check if a model is fully downloaded.

    Looks for weights.npz in the model's cache directory.

    Args:
        model_id: HuggingFace model ID.

    Returns:
        True if the model is downloaded and ready to use.
    """
    cache_path = get_model_cache_path(model_id)
    weights_path = cache_path / "weights.npz"
    return weights_path.exists()


def get_all_models_status() -> list[ModelInfo]:
    """Query download status of all available models.

    Returns:
        List of ModelInfo with current state for each available model.
    """
    models = []
    for model_id, description in AVAILABLE_MODELS:
        # Parse display name and size from description
        # Format: "Whisper Turbo - Fast, good quality (~1.5GB)"
        parts = description.split(" - ")
        display_name = parts[0] if parts else model_id
        size_info = ""
        if "(" in description and ")" in description:
            size_info = description.split("(")[-1].rstrip(")")

        state = ModelState.DOWNLOADED if is_model_downloaded(model_id) else ModelState.NOT_DOWNLOADED

        models.append(
            ModelInfo(
                model_id=model_id,
                display_name=display_name,
                description=description,
                size_info=size_info,
                state=state,
                download_progress=1.0 if state == ModelState.DOWNLOADED else 0.0,
            )
        )

    return models


@dataclass
class BackgroundDownloader:
    """Manages background model downloads with progress reporting."""

    on_progress: Callable[[str, float], None] | None = None
    on_complete: Callable[[str, bool], None] | None = None

    _download_thread: threading.Thread | None = field(default=None, repr=False)
    _current_model: str | None = field(default=None, repr=False)
    _cancel_flag: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def is_downloading(self) -> bool:
        """Return True if a download is in progress."""
        with self._lock:
            return self._download_thread is not None and self._download_thread.is_alive()

    @property
    def current_model(self) -> str | None:
        """Return model_id being downloaded, or None."""
        with self._lock:
            return self._current_model

    def download(self, model_id: str) -> None:
        """Start background download. Cancels any existing download.

        Args:
            model_id: HuggingFace model ID to download.
        """
        # Cancel any existing download
        self.cancel()

        with self._lock:
            self._cancel_flag.clear()
            self._current_model = model_id
            self._download_thread = threading.Thread(
                target=self._download_worker,
                args=(model_id,),
                daemon=True,
            )
            self._download_thread.start()

    def cancel(self) -> None:
        """Cancel current download if any."""
        with self._lock:
            if self._download_thread is not None and self._download_thread.is_alive():
                self._cancel_flag.set()
                # Don't wait for thread - it will check flag and exit

    def _download_worker(self, model_id: str) -> None:
        """Worker function that runs in background thread."""
        success = False

        try:
            from huggingface_hub import snapshot_download

            cache_dir = MODEL_CACHE_DIR
            cache_dir.mkdir(parents=True, exist_ok=True)

            local_dir = str(cache_dir / model_id.replace("/", "--"))

            # Signal that download is starting (indeterminate progress)
            if self.on_progress:
                self.on_progress(model_id, 0.0)

            # Download the model
            # Note: tqdm_class customization is complex, so we use default progress
            # The UI will show "Downloading..." state without percentage
            snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
            )

            success = True

        except InterruptedError:
            print(f"Download of {model_id} was cancelled")
        except Exception as e:
            print(f"Error downloading {model_id}: {e}")

        finally:
            with self._lock:
                self._current_model = None

            if self.on_complete:
                self.on_complete(model_id, success)
