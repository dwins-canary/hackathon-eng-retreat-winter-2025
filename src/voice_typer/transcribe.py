"""Transcription module using MLX Whisper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

from voice_typer.config import MODEL_CACHE_DIR


def get_model_path(model_id: str) -> str:
    """Get the local path for a model, downloading if needed.

    Args:
        model_id: HuggingFace model ID (e.g., "mlx-community/whisper-turbo").

    Returns:
        Local filesystem path to the model directory.
    """
    from huggingface_hub import snapshot_download

    # Use the shared cache directory
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Download to the cache directory
    local_path = snapshot_download(
        repo_id=model_id,
        local_dir=str(MODEL_CACHE_DIR / model_id.replace("/", "--")),
    )

    return local_path


def download_model(model_id: str) -> str:
    """Download a model from HuggingFace Hub.

    This triggers the download and caches the model locally.
    If the download is interrupted, it will resume on next call.

    Args:
        model_id: HuggingFace model ID (e.g., "mlx-community/whisper-turbo").

    Returns:
        Local filesystem path to the model directory.
    """
    print(f"Downloading model: {model_id}")
    print("This may take a few minutes depending on your connection...")
    print("(You can cancel with Ctrl+C - download will resume next time)")
    print()

    local_path = get_model_path(model_id)

    print()
    print("Model downloaded successfully!")
    return local_path


class Transcriber:
    """Transcribes audio using MLX Whisper.

    The model is lazy-loaded on first transcription to avoid startup delay.
    """

    def __init__(
        self,
        model: str = "mlx-community/whisper-large-v3-turbo",
        language: str | None = None,
    ) -> None:
        """Initialize the transcriber.

        Args:
            model: HuggingFace model ID for MLX Whisper.
            language: Optional language code (e.g., "en"). If None, auto-detect.
        """
        self.model_id = model
        self.language = language
        self._local_path: str | None = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure the model is loaded (lazy loading)."""
        if not self._loaded:
            # Import here to defer loading until needed
            import mlx_whisper  # noqa: F401

            # Resolve the local path for the model (handles PyInstaller issues)
            if self._local_path is None:
                self._local_path = get_model_path(self.model_id)

            self._loaded = True

    def transcribe(self, audio: NDArray[np.float32], sample_rate: int = 16000) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio samples as float32 array (values in [-1, 1]).
            sample_rate: Sample rate of the audio (default 16kHz for Whisper).

        Returns:
            Transcribed text.
        """
        import mlx_whisper

        self._ensure_loaded()

        if len(audio) == 0:
            return ""

        # MLX Whisper expects audio at 16kHz
        # If sample_rate differs, we'd need to resample (not implemented yet)
        if sample_rate != 16000:
            raise ValueError(f"Expected 16kHz audio, got {sample_rate}Hz")

        # Use local path instead of HuggingFace repo ID to avoid path resolution issues
        # in PyInstaller bundles
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._local_path,
            language=self.language,
            verbose=False,
        )

        return result.get("text", "").strip()
