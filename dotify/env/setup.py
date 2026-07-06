import logging
from pathlib import Path
from typing import Optional

from .paths import DotifyPaths
from .checks import HealthCheck

logger = logging.getLogger(__name__)


class DotifySetup:
    """Setup automation for Dotify environment."""

    def __init__(self, paths: Optional[DotifyPaths] = None) -> None:
        self.paths = paths or DotifyPaths()
        self.health_check = HealthCheck(self.paths)

    def setup_all(self, skip_sensitive: bool = True) -> bool:
        """Run complete setup process."""
        logger.info("Setting up Dotify environment...")

        success = True

        success &= self._setup_directories()
        success &= self._setup_config_file()

        if not skip_sensitive:
            success &= self._setup_sensitive_files()

        if success:
            logger.info("✓ Setup completed successfully")
        else:
            logger.warning("⚠ Setup completed with some issues")

        return success

    def _setup_directories(self) -> bool:
        """Create all required directories."""
        try:
            directories = [
                self.paths.config_dir,
                self.paths.keys_dir,
                self.paths.temp_dir,
                self.paths.logs_dir,
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {directory}")

            logger.info("✓ Directories created")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create directories: {e}")
            return False

    def _setup_config_file(self) -> bool:
        """Create default config file if it doesn't exist."""
        try:
            config_file = self.paths.config_file

            if not config_file.exists():
                config_file.write_text(
                    "[dotify]\n"
                    "# Dotify configuration file\n"
                    "# Run 'dotify doctor' to check your setup\n"
                    "# Run 'dotify setup' to reconfigure\n"
                    "\n"
                    "# Paths\n"
                    "cookies_path = cookies.txt\n"
                    "wvd_path = device.wvd\n"
                    "output_path = Spotify\n"
                    "temp_path = temp\n"
                    "\n"
                    "# Download settings\n"
                    "wait_interval = 5\n"
                    "audio_quality = aac-medium\n"
                    "\n"
                    "# Logging\n"
                    "log_level = INFO\n"
                )
                logger.info(f"✓ Created config file: {config_file}")
            else:
                logger.info(f"✓ Config file exists: {config_file}")

            return True
        except Exception as e:
            logger.error(f"✗ Failed to create config file: {e}")
            return False

    def _setup_sensitive_files(self) -> bool:
        """
        Setup sensitive files (cookies and wvd).
        This is skipped by default as these require user action.
        """
        logger.info("ℹ Sensitive files require manual setup:")
        logger.info(f"  - Place cookies.txt in: {self.paths.config_dir}")
        logger.info(f"  - Place device.wvd in: {self.paths.keys_dir}")
        return True

    def create_placeholder_files(self) -> bool:
        """Create placeholder files for sensitive data."""
        try:
            cookies_placeholder = self.paths.default_cookies_path.with_suffix(".txt.example")
            wvd_placeholder = self.paths.default_wvd_path.with_suffix(".wvd.example")

            if not cookies_placeholder.exists():
                cookies_placeholder.write_text(
                    "# Place your exported cookies.txt file here\n"
                    "# Rename this file to cookies.txt\n"
                    "#\n"
                    "# To get cookies:\n"
                    "# 1. Install 'Get cookies.txt LOCALLY' extension\n"
                    "# 2. Go to open.spotify.com and log in\n"
                    "# 3. Export cookies to this file\n"
                )
                logger.info(f"✓ Created cookies placeholder: {cookies_placeholder}")

            if not wvd_placeholder.exists():
                wvd_placeholder.write_text(
                    "# Place your device.wvd file here\n"
                    "# Rename this file to device.wvd\n"
                    "#\n"
                    "# To get wvd file:\n"
                    "# 1. Use KeyDive on an Android device\n"
                    "# 2. Extract the device.wvd file\n"
                    "# 3. Place it in this directory\n"
                )
                logger.info(f"✓ Created wvd placeholder: {wvd_placeholder}")

            return True
        except Exception as e:
            logger.error(f"✗ Failed to create placeholder files: {e}")
            return False

    def verify_setup(self) -> bool:
        """Verify that setup is complete."""
        logger.info("Verifying setup...")

        results = self.health_check.check_all(skip_optional=True)

        failed = [r for r in results if r.status.value == "fail"]
        warnings = [r for r in results if r.status.value == "warn"]

        if not failed and not warnings:
            logger.info("✓ Setup is complete and healthy")
            return True
        elif failed:
            logger.error(f"✗ Setup has {len(failed)} critical issue(s)")
            for result in failed:
                logger.error(f"  - {result}")
            return False
        else:
            logger.warning(f"⚠ Setup has {len(warnings)} warning(s)")
            for result in warnings:
                logger.warning(f"  - {result}")
            return True