"""Configuration management."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "voice-typer" / "config.toml"
DEFAULT_HOTKEY = "alt_r"
DEFAULT_MODEL = "mlx-community/whisper-turbo"

# Available models for first-run selection
AVAILABLE_MODELS = [
    ("mlx-community/whisper-tiny", "Whisper Tiny - Fastest, lower accuracy (~75MB)"),
    ("mlx-community/whisper-turbo", "Whisper Turbo - Fast, good quality (~1.5GB)"),
    ("mlx-community/whisper-large-v3-turbo", "Whisper Large v3 Turbo - Best balance (~3GB)"),
    ("mlx-community/whisper-large-v3", "Whisper Large v3 - Highest accuracy (~3GB)"),
]


@dataclass
class Config:
    """Application configuration."""

    hotkey: str = DEFAULT_HOTKEY
    model: str = DEFAULT_MODEL
    language: str | None = None
    verbose: bool = False
    # Internal settings
    sample_rate: int = field(default=16000, repr=False)
    type_delay: float = field(default=0.01, repr=False)

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load configuration from a TOML file.

        Args:
            path: Path to config file. If None, uses default location.

        Returns:
            Config instance with loaded values.
        """
        config_path = path or DEFAULT_CONFIG_PATH

        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()

        return cls(
            hotkey=data.get("hotkey", DEFAULT_HOTKEY),
            model=data.get("model", DEFAULT_MODEL),
            language=data.get("language"),
            verbose=data.get("verbose", False),
        )

    def override(
        self,
        hotkey: str | None = None,
        model: str | None = None,
        language: str | None = None,
        verbose: bool | None = None,
    ) -> Config:
        """Create a new config with overridden values.

        Args:
            hotkey: Override hotkey if provided.
            model: Override model if provided.
            language: Override language if provided.
            verbose: Override verbose if provided.

        Returns:
            New Config instance with overrides applied.
        """
        return Config(
            hotkey=hotkey if hotkey is not None else self.hotkey,
            model=model if model is not None else self.model,
            language=language if language is not None else self.language,
            verbose=verbose if verbose is not None else self.verbose,
            sample_rate=self.sample_rate,
            type_delay=self.type_delay,
        )

    def save(self, path: Path | None = None) -> None:
        """Save configuration to a TOML file.

        Args:
            path: Path to config file. If None, uses default location.
        """
        config_path = path or DEFAULT_CONFIG_PATH

        # Create parent directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build TOML content
        lines = [
            f'model = "{self.model}"',
            f'hotkey = "{self.hotkey}"',
        ]
        if self.language:
            lines.append(f'language = "{self.language}"')
        if self.verbose:
            lines.append("verbose = true")

        content = "\n".join(lines) + "\n"

        with open(config_path, "w") as f:
            f.write(content)
