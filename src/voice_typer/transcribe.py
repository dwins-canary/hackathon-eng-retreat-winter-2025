"""Transcription module using MLX Whisper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


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
        self.model_path = model
        self.language = language
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure the model is loaded (lazy loading)."""
        if not self._loaded:
            # Import here to defer loading until needed
            import mlx_whisper  # noqa: F401

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

        # Transcribe
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_path,
            language=self.language,
            verbose=False,
        )

        return result.get("text", "").strip()
