"""Transcription module using MLX Whisper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


def get_model_path(model_id: str) -> str:
    """Get the local path for a model, downloading if needed.

    Args:
        model_id: HuggingFace model ID (e.g., "mlx-community/whisper-turbo").

    Returns:
        Local filesystem path to the model directory.
    """
    import os
    from pathlib import Path
    from huggingface_hub import snapshot_download

    # Use a non-hidden directory for the cache to avoid MLX path issues
    cache_dir = Path.home() / "Library" / "Caches" / "voice-typer" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Download to the non-hidden cache directory
    local_path = snapshot_download(
        repo_id=model_id,
        local_dir=str(cache_dir / model_id.replace("/", "--")),
    )

    print(f"Model path: {local_path}")

    # Test loading the model directly with mlx.core
    weights_path = os.path.join(local_path, "weights.npz")
    print(f"Weights path: {weights_path}")
    print(f"Weights exists: {os.path.exists(weights_path)}")

    try:
        import mlx.core as mx
        from pathlib import Path
        print(f"Attempting mx.load...")
        weights = mx.load(weights_path)
        print(f"mx.load SUCCESS! Keys: {list(weights.keys())[:2]}")

        # Test how pathlib converts the path
        path_obj = Path(local_path) / "weights.npz"
        path_str = str(path_obj)
        print(f"Path object: {path_obj}")
        print(f"Path str: {path_str}")
        print(f"Direct path: {weights_path}")
        print(f"Paths equal: {path_str == weights_path}")

        # Test load with pathlib path
        print(f"Testing mx.load with pathlib str...")
        weights2 = mx.load(path_str)
        print(f"mx.load with pathlib str SUCCESS!")

        # Test mlx_whisper.load_models.load_model directly
        print(f"Testing load_model directly...")
        from mlx_whisper.load_models import load_model
        model = load_model(local_path)
        print(f"load_model SUCCESS!")
    except Exception as e:
        import traceback
        print(f"FAILED: {e}")
        traceback.print_exc()

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
