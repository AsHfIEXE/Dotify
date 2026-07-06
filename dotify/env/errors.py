import logging
from typing import Optional

from .paths import DotifyPaths
from .checks import HealthCheck, CheckStatus

logger = logging.getLogger(__name__)


class DotifyErrorHandler:
    """Enhanced error handler with helpful messages and fix suggestions."""

    def __init__(self, paths: Optional[DotifyPaths] = None) -> None:
        self.paths = paths or DotifyPaths()
        self.health_check = HealthCheck(self.paths)

    def handle_missing_cookies(self) -> str:
        """Handle missing cookies file error."""
        return (
            "Cookies file not found or invalid.\n"
            f"Expected location: {self.paths.default_cookies_path}\n"
            f"Or use --cookies-path to specify a different location.\n\n"
            "To fix:\n"
            "1. Install 'Get cookies.txt LOCALLY' extension\n"
            "2. Go to open.spotify.com and log in\n"
            "3. Export cookies to cookies.txt\n"
            "4. Place the file in ~/.dotify/ or use --cookies-path\n"
            "5. Run 'dotify doctor' to verify"
        )

    def handle_missing_wvd(self) -> str:
        """Handle missing Widevine key error."""
        return (
            "Widevine key file not found.\n"
            f"Expected location: {self.paths.default_wvd_path}\n"
            f"Or use --wvd-path to specify a different location.\n\n"
            "To fix:\n"
            "1. Use KeyDive on an Android device\n"
            "2. Extract the device.wvd file\n"
            "3. Place it in ~/.dotify/keys/ or use --wvd-path\n"
            "4. Run 'dotify doctor' to verify\n\n"
            "Note: WVD is required for AAC decryption. "
            "Use --disable-wvd to download in Vorbis format instead."
        )

    def handle_missing_ffmpeg(self) -> str:
        """Handle missing FFmpeg error."""
        return (
            "FFmpeg not found in PATH.\n\n"
            "To fix:\n"
            "Windows: Download from https://www.animemusic.info/2024/02/ffmpeg-builds-static-shared.html\n"
            "Linux: Download from https://johnvansickle.com/ffmpeg/\n"
            "Add FFmpeg to your system PATH and restart.\n"
            "Run 'dotify doctor' to verify."
        )

    def handle_missing_binary(self, binary_name: str, purpose: str) -> str:
        """Handle missing optional binary error."""
        return (
            f"{binary_name} not found in PATH.\n"
            f"Required for: {purpose}\n\n"
            f"To fix:\n"
            f"Install {binary_name} and add it to your system PATH.\n"
            f"Run 'dotify doctor --verbose' to check all dependencies."
        )

    def handle_authentication_error(self) -> str:
        """Handle authentication error."""
        return (
            "Authentication failed. Your cookies may be expired or invalid.\n\n"
            "To fix:\n"
            "1. Export fresh cookies from open.spotify.com\n"
            "2. Ensure you're logged in to your Spotify account\n"
            "3. Replace the old cookies.txt with the new one\n"
            "4. Run 'dotify doctor' to verify"
        )

    def handle_premium_required(self) -> str:
        """Handle premium account required error."""
        return (
            "Premium account required for this feature.\n\n"
            "To fix:\n"
            "1. Upgrade to Spotify Premium\n"
            "2. Use --force-premium to bypass this check (may not work)\n"
            "3. Or use --disable-wvd to download in Vorbis format instead"
        )

    def handle_download_error(self, error: Exception) -> str:
        """Handle general download error."""
        error_msg = str(error)

        if "cookies" in error_msg.lower() or "sp_dc" in error_msg.lower():
            return self.handle_missing_cookies()
        elif "wvd" in error_msg.lower() or "widevine" in error_msg.lower():
            return self.handle_missing_wvd()
        elif "ffmpeg" in error_msg.lower():
            return self.handle_missing_ffmpeg()
        else:
            return (
                f"Download error: {error_msg}\n\n"
                "Run 'dotify doctor' to check your environment setup."
            )

    def get_suggestion(self, error_type: str) -> str:
        """Get a suggestion for a specific error type."""
        suggestions = {
            "cookies": self.handle_missing_cookies(),
            "wvd": self.handle_missing_wvd(),
            "ffmpeg": self.handle_missing_ffmpeg(),
            "auth": self.handle_authentication_error(),
        }
        return suggestions.get(error_type, "Run 'dotify doctor' for diagnostics.")

    def log_error_with_fix(self, error: Exception, context: str = "") -> None:
        """Log an error with helpful fix suggestion."""
        error_msg = str(error)

        logger.error(f"{context}: {error_msg}")

        if "cookies" in error_msg.lower() or "sp_dc" in error_msg.lower():
            logger.error(f"\n{self.handle_missing_cookies()}")
        elif "wvd" in error_msg.lower() or "widevine" in error_msg.lower():
            logger.error(f"\n{self.handle_missing_wvd()}")
        elif "ffmpeg" in error_msg.lower():
            logger.error(f"\n{self.handle_missing_ffmpeg()}")
        else:
            logger.error("\nRun 'dotify doctor' for diagnostics.")