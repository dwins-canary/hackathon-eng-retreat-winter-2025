"""Audio capture module using sounddevice."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

if TYPE_CHECKING:
    from numpy.typing import NDArray


class AudioRecorder:
    """Records audio from the microphone.

    Whisper expects 16kHz mono audio, so we capture at that rate.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._buffer: list[NDArray[np.float32]] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False

    def _audio_callback(
        self,
        indata: NDArray[np.float32],
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Called by sounddevice for each audio chunk."""
        if status:
            print(f"Audio status: {status}")
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            self._buffer = []
            self._recording = True

        if self._stream is None:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            self._stream.start()

    def stop(self) -> NDArray[np.float32]:
        """Stop recording and return the captured audio.

        Returns:
            Audio data as a 1D numpy array of float32 samples.
        """
        with self._lock:
            self._recording = False
            if self._buffer:
                audio = np.concatenate(self._buffer, axis=0)
                # Flatten to 1D if needed (whisper expects 1D)
                if audio.ndim > 1:
                    audio = audio.flatten()
            else:
                audio = np.array([], dtype=np.float32)
            self._buffer = []

        return audio

    def close(self) -> None:
        """Close the audio stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def __enter__(self) -> AudioRecorder:
        return self

    def __exit__(self, *args) -> None:
        self.close()
