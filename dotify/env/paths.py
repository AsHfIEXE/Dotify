import platform
from pathlib import Path
from typing import Optional


class DotifyPaths:
    """Manages all Dotify-related paths and directories."""

    def __init__(self, custom_config_dir: Optional[Path] = None) -> None:
        self._system = platform.system()
        self._config_dir = self._get_config_dir(custom_config_dir)
        self._ensure_directories()

    def _get_config_dir(self, custom_dir: Optional[Path]) -> Path:
        """Get the configuration directory based on the operating system."""
        if custom_dir:
            return custom_dir

        if self._system == "Windows":
            return Path.home() / ".dotify"
        elif self._system == "Darwin":
            return Path.home() / ".dotify"
        else:
            return Path.home() / ".dotify"

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.config_dir,
            self.keys_dir,
            self.temp_dir,
            self.logs_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def config_dir(self) -> Path:
        """Main configuration directory."""
        return self._config_dir

    @property
    def config_file(self) -> Path:
        """Main configuration file."""
        return self._config_dir / "config.ini"

    @property
    def keys_dir(self) -> Path:
        """Directory for Widevine keys."""
        return self._config_dir / "keys"

    @property
    def default_wvd_path(self) -> Path:
        """Default path for device.wvd file."""
        return self.keys_dir / "device.wvd"

    @property
    def default_cookies_path(self) -> Path:
        """Default path for cookies.txt file."""
        return self._config_dir / "cookies.txt"

    @property
    def temp_dir(self) -> Path:
        """Temporary directory for downloads."""
        return self._config_dir / "temp"

    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        return self._config_dir / "logs"

    @property
    def database_file(self) -> Path:
        """Default path for SQLite database."""
        return self._config_dir / "downloads.db"

    def get_binary_path(self, binary_name: str) -> Path:
        """Get the path for a binary in the config directory."""
        return self._config_dir / "bin" / binary_name

    def ensure_binary_dir(self) -> Path:
        """Ensure the binary directory exists and return it."""
        bin_dir = self._config_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        return bin_dir